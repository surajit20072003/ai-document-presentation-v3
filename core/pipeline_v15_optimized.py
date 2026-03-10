"""
Pipeline v1.5 Optimized - Combined Agent Architecture

LLM Optimization: Reduces 7+ LLM calls to 3-4 by combining agents:
- ContentCreator: NarrationWriter + VisualSpecArtist (2 calls → 1 per section)
- SpecialSectionsAgent: MemoryAgent + RecapAgent (2 calls → 1)

Pipeline Flow (Optimized):
1. SmartChunker → topics (unchanged)
2. SectionPlanner → section_blueprints[] (unchanged)
3. FOR EACH blueprint: ContentCreator(blueprint) → narration + visuals
   - IF renderer != 'none': RendererSpecAgent (unchanged)
4. SpecialSectionsAgent → memory + recap (single call)
5. MergeStep (unchanged - produces same presentation.json)
6. PARALLEL: TTS + Manim Code Generation
7. PARALLEL: Manim Rendering + WAN Video Generation

Key improvements:
- ~50% fewer LLM calls (cost savings)
- Coupled visual+narration ensures sync
- Parallel TTS and renderer execution for speed
- Same presentation.json schema for player compatibility
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.smart_chunker import call_smart_chunker, ChunkerError, parse_content_blocks
from core.agents import (
    SectionPlannerAgent,
    RendererSpecAgent,
    AgentError
)
from core.agents.content_creator import ContentCreatorAgent
from core.agents.special_sections import SpecialSectionsAgent
from core.agents.manim_code_generator import (
    ManimCodeGenerator,
    build_manim_section_data,
    integrate_manim_code_into_section
)
from core.merge_step_v15 import merge_agent_outputs
from core.tts_duration import update_durations_from_tts, update_durations_simplified, TTSProvider
from core.analytics import AnalyticsTracker, create_tracker
from core.renderer_executor import render_all_topics, enforce_renderer_policy

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "1.5-opt"

# ISS-211: Content batching thresholds to prevent token limit truncation
# ISS-220: Disabled batching - modern LLMs handle large contexts, batching inflates output
MAX_QA_PAIRS_PER_BATCH = 999  # Effectively disabled - was 4
MAX_SOURCE_BLOCKS_PER_BATCH = 999  # Effectively disabled - was 6
BATCH_SIZE_ON_TRUNCATION = 999  # Effectively disabled - was 3


def _estimate_content_density(section_type: str, quiz_questions: List, source_blocks: List) -> Dict:
    """
    ISS-211: Estimate content density to determine if batching is needed.
    
    Returns:
        {
            "needs_batching": bool,
            "qa_count": int,
            "block_count": int,
            "recommended_batch_size": int,
            "num_batches": int
        }
    """
    qa_count = len(quiz_questions) if quiz_questions else 0
    block_count = len(source_blocks) if source_blocks else 0
    
    needs_batching = False
    batch_size = 0
    num_batches = 1
    
    if section_type == "quiz" and qa_count > MAX_QA_PAIRS_PER_BATCH:
        needs_batching = True
        batch_size = MAX_QA_PAIRS_PER_BATCH
        num_batches = (qa_count + batch_size - 1) // batch_size
    elif section_type in ["content", "example"] and block_count > MAX_SOURCE_BLOCKS_PER_BATCH:
        needs_batching = True
        batch_size = MAX_SOURCE_BLOCKS_PER_BATCH
        num_batches = (block_count + batch_size - 1) // batch_size
    
    return {
        "needs_batching": needs_batching,
        "qa_count": qa_count,
        "block_count": block_count,
        "recommended_batch_size": batch_size,
        "num_batches": num_batches
    }


def _merge_batched_outputs(batched_outputs: List[Dict], section_id: str, section_type: str) -> Dict:
    """
    ISS-211: Merge multiple ContentCreator batch outputs into a single section output.
    
    Combines:
    - narration.segments (concatenated, re-indexed)
    - narration.full_text (concatenated)
    - visual_beats (concatenated, re-indexed)
    - segment_enrichments (concatenated, re-indexed)
    
    Preserves all other metadata fields from first batch (derived_renderer, timing_guidance, etc.)
    """
    if not batched_outputs:
        raise PipelineError("No batched outputs to merge", phase="content_batching")
    
    if len(batched_outputs) == 1:
        return batched_outputs[0]
    
    # Start with a deep copy of the first batch to preserve all metadata fields
    import copy
    merged = copy.deepcopy(batched_outputs[0])
    
    # Override with correct section info
    merged["section_id"] = section_id
    merged["section_type"] = section_type
    
    # Reset arrays for re-indexing
    merged["narration"] = {
        "full_text": "",
        "segments": []
    }
    merged["visual_beats"] = []
    merged["segment_enrichments"] = []
    
    segment_offset = 0
    
    for batch_idx, batch_output in enumerate(batched_outputs):
        narration = batch_output.get("narration", {})
        
        # Merge full_text
        batch_text = narration.get("full_text", "")
        if merged["narration"]["full_text"]:
            merged["narration"]["full_text"] += "\n\n"
        merged["narration"]["full_text"] += batch_text
        
        # Merge segments with re-indexed IDs
        segments = narration.get("segments", [])
        for seg in segments:
            new_seg = copy.deepcopy(seg)
            old_id = new_seg.get("segment_id", 1)
            new_seg["segment_id"] = segment_offset + old_id
            merged["narration"]["segments"].append(new_seg)
        
        # Merge visual_beats with re-indexed segment_ids
        beats = batch_output.get("visual_beats", [])
        for beat in beats:
            new_beat = copy.deepcopy(beat)
            old_seg_id = new_beat.get("segment_id", 1)
            new_beat["segment_id"] = segment_offset + old_seg_id
            new_beat["beat_id"] = f"beat_{len(merged['visual_beats']) + 1}"
            merged["visual_beats"].append(new_beat)
        
        # Merge segment_enrichments with re-indexed segment_ids
        enrichments = batch_output.get("segment_enrichments", [])
        for enrich in enrichments:
            new_enrich = copy.deepcopy(enrich)
            old_seg_id = new_enrich.get("segment_id", 1)
            new_enrich["segment_id"] = segment_offset + old_seg_id
            merged["segment_enrichments"].append(new_enrich)
        
        segment_offset += len(segments)
    
    logger.info(f"[Pipeline v1.5-opt] Merged {len(batched_outputs)} batches into {len(merged['narration']['segments'])} segments")
    return merged


def _process_batch_with_retry(
    content_creator: 'ContentCreatorAgent',
    blueprint: Dict,
    source_content: str,
    items: List,
    images_list: str,
    is_quiz: bool,
    batch_num: int,
    total_batches: int,
    output_dir: Optional[Path] = None,
    section_id: str = "unknown"
) -> List[Dict]:
    """
    ISS-211: Process a batch with iterative size reduction on truncation.
    
    Tries progressively smaller batch sizes until success or single-item batches.
    Returns list of outputs from successful sub-batches.
    """
    import copy
    
    current_items = items
    current_size = len(items)
    min_size = 1  # Minimum batch size to try
    
    while current_size >= min_size:
        outputs = []
        success = True
        
        for sub_idx in range(0, len(current_items), current_size):
            sub_batch = current_items[sub_idx:sub_idx + current_size]
            sub_num = (sub_idx // current_size) + 1
            
            batch_blueprint = copy.copy(blueprint)
            batch_blueprint["_batch_info"] = f"Batch {batch_num}.{sub_num} of {total_batches} (size={current_size})"
            
            try:
                if is_quiz:
                    sub_output = content_creator.run(
                        section_blueprint=batch_blueprint,
                        source_markdown=source_content,
                        quiz_questions=json.dumps(sub_batch),
                        images_list=images_list
                    )
                else:
                    sub_content = "\n\n".join(b.get("verbatim_content", "") for b in sub_batch)
                    sub_output = content_creator.run(
                        section_blueprint=batch_blueprint,
                        source_markdown=sub_content,
                        quiz_questions="None",
                        images_list=images_list
                    )
                outputs.append(sub_output)
                
                if output_dir:
                    _save_artifact(output_dir, f"{section_id}_batch_{batch_num}_{sub_num}.json", sub_output)
                    
            except AgentError as e:
                error_str = str(e).lower()
                if "unterminated string" in error_str or "truncat" in error_str or "json" in error_str:
                    logger.warning(f"[Pipeline v1.5-opt] Batch {batch_num}.{sub_num} truncated at size {current_size}")
                    success = False
                    break
                else:
                    raise
        
        if success:
            return outputs
        
        # Reduce batch size and retry
        current_size = max(1, current_size // 2)
        logger.info(f"[Pipeline v1.5-opt] Reducing batch size to {current_size}")
    
    # If we get here with size=1 and still failing, raise clear error
    raise PipelineError(
        f"ContentCreator batch processing failed even with batch size 1. Content may be too complex.",
        phase="content_batching"
    )


def _run_content_creator_with_batching(
    content_creator: 'ContentCreatorAgent',
    blueprint: Dict,
    source_content: str,
    quiz_questions: List,
    images_list: str,
    content_blocks: List,
    tracker: AnalyticsTracker,
    log_func,
    output_dir: Optional[Path] = None
) -> Dict:
    """
    ISS-211: Run ContentCreator with automatic batching for large content.
    
    If content exceeds thresholds, splits into batches and merges results.
    On truncation error, automatically reduces batch size and retries.
    """
    section_type = blueprint.get("section_type", "content")
    section_id = blueprint.get("section_id", "unknown")
    
    density = _estimate_content_density(section_type, quiz_questions, content_blocks)
    
    if not density["needs_batching"]:
        # Normal single-call path - but still handle truncation
        try:
            return content_creator.run(
                section_blueprint=blueprint,
                source_markdown=source_content,
                quiz_questions=json.dumps(quiz_questions) if quiz_questions else "None",
                images_list=images_list
            )
        except AgentError as e:
            error_str = str(e).lower()
            if "unterminated string" in error_str or "truncat" in error_str or "json" in error_str:
                # Force batching even though we didn't predict we needed it
                logger.warning(f"[Pipeline v1.5-opt] Unexpected truncation for {section_id}, forcing batching")
                density["needs_batching"] = True
                density["recommended_batch_size"] = 2
            else:
                raise
    
    # Batching needed
    logger.info(f"[Pipeline v1.5-opt] Section {section_id} needs batching: {density}")
    
    batched_outputs = []
    batch_size = density["recommended_batch_size"]
    
    if section_type == "quiz":
        # Split quiz questions into batches
        for batch_idx in range(0, len(quiz_questions), batch_size):
            batch_qa = quiz_questions[batch_idx:batch_idx + batch_size]
            batch_num = (batch_idx // batch_size) + 1
            total_batches = density["num_batches"]
            
            logger.info(f"[Pipeline v1.5-opt] Processing quiz batch {batch_num}/{total_batches} ({len(batch_qa)} Q&A pairs)")
            
            batch_results = _process_batch_with_retry(
                content_creator=content_creator,
                blueprint=blueprint,
                source_content=source_content,
                items=batch_qa,
                images_list=images_list,
                is_quiz=True,
                batch_num=batch_num,
                total_batches=total_batches,
                output_dir=output_dir,
                section_id=section_id
            )
            batched_outputs.extend(batch_results)
    
    else:
        # Split content blocks into batches (for content/example sections)
        for batch_idx in range(0, len(content_blocks), batch_size):
            batch_blocks = content_blocks[batch_idx:batch_idx + batch_size]
            batch_num = (batch_idx // batch_size) + 1
            total_batches = density["num_batches"]
            
            logger.info(f"[Pipeline v1.5-opt] Processing content batch {batch_num}/{total_batches} ({len(batch_blocks)} blocks)")
            
            batch_results = _process_batch_with_retry(
                content_creator=content_creator,
                blueprint=blueprint,
                source_content=source_content,
                items=batch_blocks,
                images_list=images_list,
                is_quiz=False,
                batch_num=batch_num,
                total_batches=total_batches,
                output_dir=output_dir,
                section_id=section_id
            )
            batched_outputs.extend(batch_results)
    
    return _merge_batched_outputs(batched_outputs, section_id, section_type)


def _json_serializer(obj):
    """Custom JSON serializer for non-serializable objects."""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        return str(obj)
    return str(obj)


def _save_artifact(output_dir: Optional[Path], filename: str, data: Dict) -> None:
    """Save agent output as artifact for debugging."""
    if not output_dir:
        return
    
    try:
        artifacts_dir = Path(output_dir) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        artifact_path = artifacts_dir / filename
        with open(artifact_path, "w") as f:
            json.dump(data, f, indent=2, default=_json_serializer)
        logger.debug(f"[Artifacts] Saved {filename}")
    except Exception as e:
        logger.warning(f"[Artifacts] Failed to save {filename}: {e}")


class PipelineError(Exception):
    """Error raised when pipeline fails."""
    def __init__(self, message: str, phase: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.phase = phase
        self.details = details or {}


def _save_analytics(
    tracker: AnalyticsTracker, 
    presentation: Optional[Dict], 
    output_dir: Optional[Path],
    qa_pair_count: int = 0,
    page_count: int = 0,
    table_count: int = 0,
    image_count: int = 0
) -> None:
    """Save analytics data to analytics.json in the job folder.
    
    ISS-207: Added page_count
    ISS-208: Added qa_pair_count
    ISS-209/210: Added table_count, image_count
    """
    if not output_dir:
        return
        
    try:
        if presentation:
            sections = presentation.get("sections", [])
            total_sections = len(sections)
            total_segments = 0
            section_types: Dict[str, int] = {}
            manim_count = 0
            wan_count = 0
            static_count = 0
            
            for section in sections:
                section_type = section.get("section_type", "content")
                section_types[section_type] = section_types.get(section_type, 0) + 1
                
                narration = section.get("narration", {})
                segments = narration.get("segments", [])
                total_segments += len(segments)
                
                renderer = section.get("renderer", "none")
                if renderer == "manim":
                    manim_count += 1
                elif renderer in ("wan", "wan_video", "video"):
                    wan_count += 1
                else:
                    static_count += 1
            
            tracker.set_content_metrics(
                total_sections=total_sections,
                total_segments=total_segments,
                total_slides=total_sections,
                section_types=section_types,
                page_count=page_count,
                qa_pair_count=qa_pair_count,
                table_count=table_count,
                image_count=image_count
            )
            
            tracker.set_renderer_metrics(
                manim_videos=manim_count,
                wan_videos=wan_count,
                static_slides=static_count
            )
        
        analytics_path = output_dir / "analytics.json"
        tracker.save_to_file(str(analytics_path))
        logger.info(f"[Analytics] Saved to {analytics_path}")
        
    except Exception as e:
        logger.warning(f"[Analytics] Failed to save analytics: {e}")


def _extract_source_content(markdown_content: str, source_blocks: List[int]) -> str:
    """Extract relevant markdown content for a section based on source blocks."""
    lines = markdown_content.split('\n')
    if not source_blocks:
        return markdown_content[:3000]
    
    block_num = 0
    extracted = []
    current_block = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#') or (stripped and not current_block):
            if current_block and block_num in source_blocks:
                extracted.extend(current_block)
            current_block = [line]
            block_num += 1
        else:
            current_block.append(line)
    
    if current_block and block_num in source_blocks:
        extracted.extend(current_block)
    
    return '\n'.join(extracted) if extracted else markdown_content[:3000]


def _extract_images_list(markdown_content: str) -> str:
    """Extract image references from markdown content."""
    import re
    images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', markdown_content)
    if not images:
        return "No images available"
    return "\n".join([f"IMAGE_{i+1}: {path} ({alt})" for i, (alt, path) in enumerate(images)])


def _enhance_content_creator_output(output: Dict, source_markdown: str, content_blocks: Optional[List[Dict]] = None) -> Dict:
    """Post-process ContentCreator output to ensure content_type is set deterministically."""
    if content_blocks is None:
        content_blocks = parse_content_blocks(source_markdown) if source_markdown else []
    
    block_lookup = {block.get("block_id"): block for block in content_blocks}
    
    enrichments = output.get("segment_enrichments", [])
    for i, enrichment in enumerate(enrichments):
        vc = enrichment.get("visual_content", {})
        source_block_ids = enrichment.get("source_block_ids", [])
        
        if source_block_ids and block_lookup:
            block_id = source_block_ids[0] if isinstance(source_block_ids[0], str) else str(source_block_ids[0])
            block = block_lookup.get(block_id) or block_lookup.get(int(block_id) if block_id.isdigit() else block_id)
            
            if block:
                block_type = block.get("block_type", "paragraph")
                verbatim = block.get("verbatim_content", "")
                
                if block_type == "unordered_list":
                    vc["content_type"] = "bullet_list"
                    if block.get("items"):
                        vc["items"] = block["items"]
                    vc["verbatim_content"] = verbatim
                elif block_type == "ordered_list":
                    vc["content_type"] = "ordered_list"
                    if block.get("items"):
                        vc["items"] = block["items"]
                elif block_type == "formula":
                    vc["content_type"] = "formula"
                    vc["formula"] = verbatim
                else:
                    if not vc.get("content_type"):
                        vc["content_type"] = "paragraph"
                    vc["verbatim_content"] = verbatim
                
                enrichment["visual_content"] = vc
                continue
        
        if not vc.get("content_type"):
            if vc.get("items"):
                vc["content_type"] = "bullet_list"
            elif vc.get("formula"):
                vc["content_type"] = "formula"
            elif vc.get("question") and vc.get("answer"):
                vc["content_type"] = "flashcard"
            else:
                vc["content_type"] = "paragraph"
        
        enrichment["visual_content"] = vc
    
    output["segment_enrichments"] = enrichments
    return output


def _convert_content_creator_to_artifacts(output: Dict, blueprint: Dict) -> Dict:
    """Convert ContentCreator output to the artifact format expected by MergeStep.
    
    MergeStep expects:
    - artifact["narration"]["narration"]["segments"] with integer segment_ids
    - artifact["visuals"]["segment_enrichments"] with integer segment_ids and display_directives
    - artifact["visuals"]["visual_beats"] with beat_id strings and integer segment_ids
    """
    narration_data = output.get("narration", {})
    segments = narration_data.get("segments", [])
    for i, seg in enumerate(segments):
        seg_id = seg.get("segment_id")
        if isinstance(seg_id, str):
            if not seg_id.isdigit():
                raise PipelineError(
                    f"Invalid segment_id '{seg_id}' in segment {i} - must be integer",
                    phase="content_creator_conversion"
                )
            seg["segment_id"] = int(seg_id)
        elif not isinstance(seg_id, int):
            seg["segment_id"] = i + 1
        if "gesture_hint" not in seg:
            seg["gesture_hint"] = "explaining"
    
    narration_output = {
        "section_id": output.get("section_id"),
        "narration": narration_data
    }
    
    enrichments = output.get("segment_enrichments", [])
    for i, enrich in enumerate(enrichments):
        seg_id = enrich.get("segment_id")
        if isinstance(seg_id, str):
            if not seg_id.isdigit():
                raise PipelineError(
                    f"Invalid segment_id '{seg_id}' in enrichment {i} - must be integer",
                    phase="content_creator_conversion"
                )
            enrich["segment_id"] = int(seg_id)
        elif not isinstance(seg_id, int):
            enrich["segment_id"] = i + 1
        
        if "display_directives" not in enrich:
            enrich["display_directives"] = {
                "text_layer": "hide",
                "visual_layer": "show",
                "avatar_layer": "show"
            }
        else:
            dd = enrich["display_directives"]
            if dd.get("avatar_layer") == "hide":
                dd["avatar_layer"] = "show"
    
    visual_beats = output.get("visual_beats", [])
    for i, beat in enumerate(visual_beats):
        if "beat_id" not in beat:
            beat["beat_id"] = f"beat_{i+1}"
        seg_id = beat.get("segment_id")
        if isinstance(seg_id, str):
            if not seg_id.isdigit():
                raise PipelineError(
                    f"Invalid segment_id '{seg_id}' in visual_beat {i} - must be integer",
                    phase="content_creator_conversion"
                )
            beat["segment_id"] = int(seg_id)
        elif not isinstance(seg_id, int):
            beat["segment_id"] = i + 1
    
    visuals_output = {
        "section_id": output.get("section_id"),
        "visual_beats": visual_beats,
        "segment_enrichments": enrichments
    }
    
    return {
        "blueprint": blueprint,
        "narration": narration_output,
        "visuals": visuals_output,
        "render_spec": None
    }


def _convert_special_sections_output(output: Dict) -> Tuple[Dict, Dict]:
    """Convert SpecialSectionsAgent output to memory_output and recap_output format.
    
    Ensures:
    - Memory narration segments have display_directives with avatar_layer="show"
    - Recap narration segments have display_directives with avatar_layer="show"
    - All segment_ids are integers
    """
    memory_section = output.get("memory_section", {})
    memory_narration = memory_section.get("narration", {})
    
    memory_segments = memory_narration.get("segments", [])
    for i, seg in enumerate(memory_segments):
        seg_id = seg.get("segment_id")
        if isinstance(seg_id, str):
            if not seg_id.isdigit():
                raise PipelineError(
                    f"Invalid segment_id '{seg_id}' in memory segment {i} - must be integer",
                    phase="special_sections_conversion"
                )
            seg["segment_id"] = int(seg_id)
        elif not isinstance(seg_id, int):
            seg["segment_id"] = i + 1
        if "gesture_hint" not in seg:
            seg["gesture_hint"] = "explaining"
        if "display_directives" not in seg:
            seg["display_directives"] = {
                "text_layer": "hide",
                "visual_layer": "show",
                "avatar_layer": "show"
            }
        else:
            dd = seg["display_directives"]
            if dd.get("avatar_layer") == "hide":
                dd["avatar_layer"] = "show"
    
    memory_narration["segments"] = memory_segments
    
    memory_output = {
        "section_id": memory_section.get("section_id", "memory"),
        "section_type": "memory",
        "title": memory_section.get("title", "3 Keys to Remember"),
        "flashcards": memory_section.get("flashcards", []),
        "narration": memory_narration
    }
    
    recap_section = output.get("recap_section", {})
    recap_narration = recap_section.get("narration", {})
    
    recap_segments = recap_narration.get("segments", [])
    for i, seg in enumerate(recap_segments):
        seg_id = seg.get("segment_id")
        if isinstance(seg_id, str):
            if not seg_id.isdigit():
                raise PipelineError(
                    f"Invalid segment_id '{seg_id}' in recap segment {i} - must be integer",
                    phase="special_sections_conversion"
                )
            seg["segment_id"] = int(seg_id)
        elif not isinstance(seg_id, int):
            seg["segment_id"] = i + 1
        if "gesture_hint" not in seg:
            seg["gesture_hint"] = "explaining"
        if "display_directives" not in seg:
            seg["display_directives"] = {
                "text_layer": "hide",
                "visual_layer": "show",
                "avatar_layer": "show"
            }
        else:
            dd = seg["display_directives"]
            if dd.get("avatar_layer") == "hide":
                dd["avatar_layer"] = "show"
    
    recap_narration["segments"] = recap_segments
    
    recap_output = {
        "section_id": recap_section.get("section_id", "recap"),
        "section_type": "recap",
        "title": recap_section.get("title", "Mental Movie"),
        "video_prompts": recap_section.get("video_prompts", []),
        "narration": recap_narration
    }
    
    return memory_output, recap_output


def _validate_section_order(blueprints: List[Dict]) -> Tuple[bool, List[str]]:
    """Validate section order: intro → summary → content(s) → memory → recap.
    
    Returns (is_valid, errors) tuple.
    """
    errors = []
    
    section_types = [b.get("section_type") for b in blueprints]
    
    if not section_types:
        errors.append("No sections found in blueprints")
        return False, errors
    
    if section_types[0] != "intro":
        errors.append(f"First section must be 'intro', got '{section_types[0]}'")
    
    if len(section_types) > 1 and section_types[1] != "summary":
        errors.append(f"Second section must be 'summary', got '{section_types[1]}'")
    
    memory_idx = None
    recap_idx = None
    
    for i, st in enumerate(section_types):
        if st == "memory":
            memory_idx = i
        elif st == "recap":
            recap_idx = i
    
    if memory_idx is not None and recap_idx is not None:
        if recap_idx < memory_idx:
            errors.append("'recap' section must come after 'memory' section")
    
    return len(errors) == 0, errors


def _enforce_avatar_visibility(presentation: Dict) -> Dict:
    """Ensure avatar is always visible (never 'hide') in all segments.
    
    Fixes any avatar_layer='hide' to 'show'.
    """
    for section in presentation.get("sections", []):
        narration = section.get("narration", {})
        segments = narration.get("segments", [])
        
        for seg in segments:
            dd = seg.get("display_directives", {})
            if dd.get("avatar_layer") == "hide":
                dd["avatar_layer"] = "show"
                seg["display_directives"] = dd
        
        display_directives = section.get("display_directives", [])
        for dd in display_directives:
            if dd.get("avatar_layer") == "hide":
                dd["avatar_layer"] = "show"
    
    return presentation


def process_markdown_optimized(
    markdown_content: str,
    subject: str,
    grade: str,
    job_id: str,
    update_status_callback=None,
    generate_tts: bool = True,
    output_dir: Optional[Path] = None,
    tts_provider: TTSProvider = "edge_tts",
    dry_run: bool = False,
    skip_wan: bool = False,
    parallel_execution: bool = True,
    video_provider: str = "kie"
) -> Tuple[Dict, AnalyticsTracker]:
    """
    V1.5 Optimized Pipeline: Process markdown using combined agents.
    
    LLM Call Reduction:
    - ContentCreator replaces NarrationWriter + VisualSpecArtist (2→1 per section)
    - SpecialSectionsAgent replaces MemoryAgent + RecapAgent (2→1)
    
    Parallel Execution (when enabled):
    - TTS generation runs in parallel with Manim code generation
    - Manim rendering runs in parallel with WAN video generation
    
    Pipeline Flow:
    1. SmartChunker → topics
    2. SectionPlanner(topics) → section_blueprints[]
    3. FOR EACH blueprint (excluding memory/recap):
       - ContentCreator(blueprint) → narration + visuals (COMBINED)
       - IF renderer != 'none': RendererSpecAgent
    4. SpecialSectionsAgent(markdown) → memory + recap (COMBINED)
    5. MergeStep(all_outputs) → presentation.json (UNCHANGED)
    6. TTS + ManimCodeGen (PARALLEL if enabled)
    7. Manim + WAN Rendering (PARALLEL if enabled)
    
    Returns same presentation.json format for player compatibility.
    """
    logger.info(f"[Pipeline v1.5-opt] Starting for job {job_id}")
    
    tracker = create_tracker(job_id)
    tracker.start_pipeline()
    
    def update_status(phase: str, message: str):
        if update_status_callback:
            update_status_callback(job_id, phase, message)
        logger.info(f"[{phase}] {message}")
    
    def log(msg: str):
        logger.info(msg)
    
    try:
        update_status("chunker", "Analyzing content structure...")
        chunker_output = call_smart_chunker(
            markdown_content=markdown_content,
            subject=subject,
            tracker=tracker,
            max_retries=2
        )
        topics = chunker_output.get("topics", [])
        logger.info(f"[Pipeline v1.5-opt] Extracted {len(topics)} topics")
        
        _save_artifact(output_dir, "01_chunker.json", chunker_output)
        
        quiz_questions = chunker_output.get("quiz_questions", [])
        qa_pair_count = len(quiz_questions)
        logger.info(f"[Pipeline v1.5-opt] Extracted {qa_pair_count} quiz questions")
        
        # ISS-209/210: Count table and image blocks
        content_blocks = parse_content_blocks(markdown_content)
        table_count = sum(1 for b in content_blocks if b.get("block_type") == "table")
        image_count = sum(1 for b in content_blocks if b.get("block_type") == "image")
        logger.info(f"[Pipeline v1.5-opt] Block types: {table_count} tables, {image_count} images")
        
        update_status("section_planner", "Planning section structure...")
        section_planner = SectionPlannerAgent(tracker=tracker, log_func=log)
        
        # ISS-213: Pass density analysis to SectionPlanner for smart section counts
        content_density_analysis = chunker_output.get("content_density_analysis", {})
        topic_grouping_hints = chunker_output.get("topic_grouping_hints", [])
        
        if content_density_analysis:
            rec_sections = content_density_analysis.get("recommended_content_sections", "N/A")
            logger.info(f"[Pipeline v1.5-opt] Density analysis: {content_density_analysis.get('total_concepts', 0)} concepts, recommends {rec_sections} content sections")
        
        planner_output = section_planner.run(
            topics=topics,
            subject=subject,
            grade=grade,
            quiz_questions=quiz_questions,
            content_density_analysis=json.dumps(content_density_analysis, indent=2) if content_density_analysis else "{}",
            topic_grouping_hints=json.dumps(topic_grouping_hints, indent=2) if topic_grouping_hints else "[]"
        )
        blueprints = planner_output.get("sections", [])
        logger.info(f"[Pipeline v1.5-opt] Planned {len(blueprints)} sections")
        
        valid, order_errors = _validate_section_order(blueprints)
        if not valid:
            logger.warning(f"[Pipeline v1.5-opt] Section order issues: {order_errors}")
            critical_errors = [e for e in order_errors if "must be" in e]
            if critical_errors:
                raise PipelineError(
                    f"Section order validation failed: {critical_errors}",
                    phase="section_planner"
                )
        
        _save_artifact(output_dir, "02_planner.json", planner_output)
        
        section_artifacts = []
        manim_failed_sections = []
        images_list = _extract_images_list(markdown_content)
        
        # ISS-213 FIX: Use chunker's content_blocks instead of re-parsing
        # This prevents creating 163 tiny blocks from dense content
        all_content_blocks = chunker_output.get("content_blocks", [])
        if not all_content_blocks:
            all_content_blocks = parse_content_blocks(markdown_content)
        logger.info(f"[Pipeline v1.5-opt] Using {len(all_content_blocks)} content blocks from chunker")
        
        for i, blueprint in enumerate(blueprints):
            section_type = blueprint.get("section_type")
            section_id = blueprint.get("section_id")
            
            if section_type in ["memory", "recap"]:
                continue
            
            update_status("content_creator", f"Creating content for {section_id}...")
            
            source_topics = blueprint.get("source_topics", [])
            topic_blocks = []
            for topic in topics:
                if topic.get("topic_id") in source_topics:
                    topic_blocks.extend(topic.get("source_blocks", []))
            source_content = _extract_source_content(markdown_content, topic_blocks)
            
            section_quiz_questions = quiz_questions if section_type == "quiz" else []
            
            # ISS-213 FIX: Filter chunker's content_blocks by topic source_blocks
            # instead of re-parsing markdown (which creates too many tiny blocks)
            if topic_blocks:
                content_blocks = [
                    b for b in all_content_blocks 
                    if b.get("block_id") in topic_blocks
                ]
                logger.info(f"[Pipeline v1.5-opt] {section_id}: filtered to {len(content_blocks)} blocks from {len(topic_blocks)} topic_blocks")
            else:
                # Fallback for sections without topic mappings (intro/summary/quiz)
                content_blocks = parse_content_blocks(source_content) if source_content else []
            content_blocks_json = json.dumps(content_blocks, indent=2) if content_blocks else "[]"
            
            # ISS-211: Use batching for large content sections
            content_creator = ContentCreatorAgent(tracker=tracker, log_func=log)
            content_output = _run_content_creator_with_batching(
                content_creator=content_creator,
                blueprint=blueprint,
                source_content=source_content,
                quiz_questions=section_quiz_questions,
                images_list=images_list,
                content_blocks=content_blocks,
                tracker=tracker,
                log_func=log,
                output_dir=output_dir
            )
            
            content_output = _enhance_content_creator_output(content_output, source_content, content_blocks)
            
            render_spec = None
            renderer = blueprint.get("suggested_renderer", "none")
            
            if renderer == "video":
                update_status("renderer_spec", f"Creating {renderer} spec for {section_id}...")
                
                visual_beats = content_output.get("visual_beats", [])
                narration_summary = content_output.get("narration", {}).get("full_text", "")[:500]
                
                try:
                    renderer_agent = RendererSpecAgent(
                        renderer_type=renderer,
                        tracker=tracker,
                        log_func=log
                    )
                    render_spec = renderer_agent.run(
                        section_id=section_id,
                        visual_beats=visual_beats,
                        narration_summary=narration_summary,
                        is_recap=False
                    )
                except AgentError as e:
                    logger.warning(f"[Pipeline v1.5-opt] RendererSpec failed for {section_id}: {e}")
                    render_spec = None
            
            artifact = _convert_content_creator_to_artifacts(content_output, blueprint)
            artifact["render_spec"] = render_spec
            section_artifacts.append(artifact)
            
            artifact_idx = len(section_artifacts) + 2
            _save_artifact(output_dir, f"{artifact_idx:02d}_{section_id}_content.json", content_output)
            if render_spec:
                _save_artifact(output_dir, f"{artifact_idx:02d}_{section_id}_render_spec.json", render_spec)
        
        update_status("special_sections", "Creating memory + recap sections...")
        
        key_concepts = []
        for topic in topics:
            key_concepts.extend(topic.get("key_terms", []))
        key_concepts = key_concepts[:10]
        
        special_agent = SpecialSectionsAgent(tracker=tracker, log_func=log)
        special_output = special_agent.run(
            source_markdown=markdown_content,
            subject=subject,
            key_concepts=json.dumps(key_concepts)
        )
        
        _save_artifact(output_dir, "special_sections.json", special_output)
        
        memory_output, recap_output = _convert_special_sections_output(special_output)
        
        _save_artifact(output_dir, "memory.json", memory_output)
        _save_artifact(output_dir, "recap.json", recap_output)
        
        video_prompts = recap_output.get("video_prompts", [])
        for i, vp in enumerate(video_prompts):
            prompt = vp.get("prompt", "") if isinstance(vp, dict) else str(vp)
            char_count = len(prompt)
            word_count = len(prompt.split()) if prompt else 0
            if char_count > 800:
                raise PipelineError(
                    f"Recap prompt {i+1} exceeds 800 char limit ({char_count} chars).",
                    phase="recap_validation"
                )
            if word_count < 80:
                raise PipelineError(
                    f"Recap prompt {i+1} has only {word_count} words (minimum 80).",
                    phase="recap_validation"
                )
            logger.info(f"[Pipeline v1.5-opt] Recap prompt {i+1}: {word_count} words, {char_count} chars - VALID")
        
        update_status("merge", "Combining all components...")
        presentation = merge_agent_outputs(
            section_artifacts=section_artifacts,
            memory_output=memory_output,
            recap_output=recap_output,
            subject=subject,
            grade=grade
        )
        
        logger.info(f"[Pipeline v1.5-opt] Merged {len(presentation.get('sections', []))} sections")
        
        presentation = _enforce_avatar_visibility(presentation)
        logger.info("[Pipeline v1.5-opt] Avatar visibility enforced (no 'hide' values)")
        
        if parallel_execution and generate_tts:
            update_status("parallel_tts_manim", "Generating TTS and Manim code in parallel...")
            
            with ThreadPoolExecutor(max_workers=2) as executor:
                tts_future = executor.submit(
                    update_durations_simplified,
                    presentation=presentation,
                    output_dir=output_dir,
                    production_provider=tts_provider,
                    update_status_callback=update_status
                )


                
                manim_results = {}
                manim_future = executor.submit(
                    _generate_all_manim_code,
                    presentation=presentation,
                    tracker=tracker
                )
                
                presentation = tts_future.result()
                manim_results = manim_future.result()
                
                for section_id, result in manim_results.items():
                    for i, section in enumerate(presentation.get("sections", [])):
                        if section.get("section_id") == section_id:
                            if result.get("code"):
                                section = integrate_manim_code_into_section(section, result["code"])
                                presentation["sections"][i] = section
                            elif result.get("error"):
                                manim_failed_sections.append({
                                    "section_id": section_id,
                                    "error": result["error"]
                                })
                            break
        else:
            if generate_tts:
                update_status("tts_duration", f"Generating TTS audio...")
                presentation = update_durations_simplified(
                    presentation=presentation,
                    output_dir=output_dir,
                    production_provider=tts_provider,
                    update_status_callback=update_status
                )

            
            update_status("manim_code", "Generating Manim code with actual TTS timing...")
            manim_results = _generate_all_manim_code(presentation, tracker)
            
            for section_id, result in manim_results.items():
                for i, section in enumerate(presentation.get("sections", [])):
                    if section.get("section_id") == section_id:
                        if result.get("code"):
                            section = integrate_manim_code_into_section(section, result["code"])
                            presentation["sections"][i] = section
                        elif result.get("error"):
                            manim_failed_sections.append({
                                "section_id": section_id,
                                "error": result["error"]
                            })
                        break
        
        if manim_failed_sections:
            _save_artifact(output_dir, "manim_failed_sections.json", {
                "failed_count": len(manim_failed_sections),
                "sections": manim_failed_sections
            })
        
        if output_dir and not dry_run:
            update_status("render_execute", "Rendering videos...")
            videos_dir = Path(output_dir) / "videos"
            videos_dir.mkdir(parents=True, exist_ok=True)
            
            presentation = enforce_renderer_policy(presentation)
            
            render_start = time.time()
            rendered_videos = render_all_topics(
                presentation=presentation,
                output_dir=str(videos_dir),
                dry_run=dry_run,
                skip_wan=skip_wan,
                output_dir_base=str(output_dir),
                video_provider=video_provider
            )
            render_duration = time.time() - render_start
            
            manim_count = 0
            wan_count = 0
            static_count = 0
            failed_renders = 0

            for result in rendered_videos:
                section_id_result = result.get("topic_id")
                status = result.get("status")
                renderer = result.get("renderer")
                
                # Update counts
                if status == "success":
                    if renderer == "manim": manim_count += 1
                    elif renderer in ["wan", "wan_video"]: wan_count += 1
                elif status == "skipped":
                    static_count += 1
                else:
                    failed_renders += 1

                # Record Per-Section Details
                tracker.add_render_detail(
                    section_id=str(section_id_result),
                    section_type=result.get("section_type", "unknown"),
                    renderer=renderer,
                    duration=result.get("duration_seconds", 0.0),
                    status=status,
                    metadata={
                        "error": result.get("error"),
                        "compilation_errors": result.get("compilation_errors"),
                        "source": "LLM Generated" if result.get("v12_specs_used") == False else "Pre-compiled"
                    }
                )

                video_path = result.get("video_path")
                beat_videos = result.get("beat_videos", [])
                recap_video_paths = result.get("recap_video_paths", [])
                
                for section in presentation.get("sections", []):
                    if section.get("section_id") == section_id_result:
                        if video_path:
                            rel_path = Path(video_path).name if "/" in str(video_path) else video_path
                            section["video_path"] = f"videos/{rel_path}"
                        if beat_videos:
                            section["beat_videos"] = [f"videos/{Path(p).name}" for p in beat_videos]
                            visual_beats = section.get("visual_beats", [])
                            for idx, beat_path in enumerate(beat_videos):
                                if idx < len(visual_beats):
                                    visual_beats[idx]["video_asset"] = f"videos/{Path(beat_path).name}"
                            section["visual_beats"] = visual_beats
                        if recap_video_paths:
                            section["recap_video_paths"] = [f"videos/{Path(p).name}" for p in recap_video_paths]
                        break
            
            tracker.set_renderer_metrics(
                manim_videos=manim_count,
                wan_videos=wan_count,
                static_slides=static_count,
                render_time=render_duration,
                failed_renders=failed_renders
            )
            logger.info(f"[Pipeline v1.5-opt] Rendering complete: {success_count} success, {fail_count} failed")
        
        tracker.end_pipeline(status="completed")
        _save_analytics(
            tracker, presentation, output_dir,
            qa_pair_count=qa_pair_count,
            table_count=table_count,
            image_count=image_count
        )
        
        logger.info(f"[Pipeline v1.5-opt] Completed successfully for job {job_id}")
        
        return presentation, tracker
        
    except ChunkerError as e:
        tracker.end_pipeline(status="failed", error=str(e))
        _save_analytics(tracker, None, output_dir)
        raise PipelineError(f"Chunker failed: {e}", phase="chunker")
        
    except AgentError as e:
        tracker.end_pipeline(status="failed", error=str(e))
        _save_analytics(tracker, None, output_dir)
        raise PipelineError(f"Agent failed: {e}", phase=e.agent_name)
        
    except Exception as e:
        tracker.end_pipeline(status="failed", error=str(e))
        _save_analytics(tracker, None, output_dir)
        logger.exception(f"[Pipeline v1.5-opt] Unexpected error: {e}")
        raise PipelineError(f"Pipeline error: {e}", phase="unknown")


def _generate_all_manim_code(presentation: Dict, tracker: AnalyticsTracker) -> Dict[str, Dict]:
    """Generate Manim code for all sections that need it."""
    results = {}
    manim_generator = ManimCodeGenerator()
    
    for i, section in enumerate(presentation.get("sections", [])):
        renderer = section.get("renderer", "none")
        section_id = section.get("section_id", f"section_{i}")
        
        if renderer == "manim":
            logger.info(f"[Pipeline v1.5-opt] Generating Manim code for {section_id}")
            
            narration = section.get("narration", {})
            segments = narration.get("segments", []) or section.get("segments", [])
            visual_beats = section.get("visual_beats", [])
            segment_enrichments = section.get("segment_enrichments", [])
            
            manim_input = build_manim_section_data(
                section=section,
                narration_segments=segments,
                visual_beats=visual_beats,
                segment_enrichments=segment_enrichments
            )
            
            try:
                gen_start = time.time()
                manim_code, validation_errors = manim_generator.generate(manim_input)
                gen_duration = time.time() - gen_start
                
                if manim_code and len(manim_code) > 50:
                    results[section_id] = {"code": manim_code, "errors": validation_errors}
                    logger.info(f"[Pipeline v1.5-opt] Manim code generated for {section_id} in {gen_duration:.1f}s")
                    
                    # Track this as a phase for timing
                    tracker.add_llm_call(
                        phase=f"manim_code_{section_id}",
                        model=manim_generator.model,
                        prompt_tokens=0, # Tokens not easily accessible
                        completion_tokens=len(manim_code) // 4 # Rough estimate
                    ).duration_seconds = gen_duration
                else:
                    results[section_id] = {"error": "Empty or too short code", "errors": validation_errors}
                    logger.warning(f"[Pipeline v1.5-opt] Manim code empty/short for {section_id}")
                    
            except Exception as e:
                results[section_id] = {"error": str(e)}
                logger.error(f"[Pipeline v1.5-opt] Manim code generation failed for {section_id}: {e}")
    
    return results

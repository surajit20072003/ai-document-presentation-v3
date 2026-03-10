"""
Pipeline v1.5 - Split Agent Architecture

Orchestrates the complete V1.5 pipeline with focused agents:
- Pass 0: Smart Chunker (topic extraction) - REUSED from V1.4
- Pass 1: SectionPlanner (section blueprints)
- Pass 2: Per-section loop: NarrationWriter → VisualSpecArtist → RendererSpecAgent (video only)
- Pass 3: MemoryFlashcardAgent + RecapSceneAgent
- Merge Step: Combine all agent outputs into presentation.json
- Pass 4: TTS Duration (generate audio, measure actual duration)
- Pass 5: ManimCodeGenerator (post-TTS, uses actual audio duration for timing)
- Pass 6: Renderers execution (Manim/WAN)

Key improvements:
- Each agent outputs 5-15 fields (vs 50+), enabling per-agent retries
- Manim code generated AFTER TTS with actual audio timing (not estimates)
- Uses Claude Sonnet 4.5 for direct Python code generation with validation
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.smart_chunker import call_smart_chunker, ChunkerError, parse_content_blocks
from core.agents import (
    SectionPlannerAgent,
    NarrationWriterAgent,
    VisualSpecArtistAgent,
    RendererSpecAgent,
    MemoryFlashcardAgent,
    RecapSceneAgent,
    AgentError
)
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

PIPELINE_VERSION = "1.5"


def _enhance_visual_content_types(visuals_output: Dict, source_markdown: str, content_blocks: Optional[List[Dict]] = None) -> Dict:
    """
    ISS-160: Post-process VisualSpecArtist output to ensure content_type is set deterministically.
    ISS-164 FIX: ALWAYS use verbatim_content from source blocks when source_block_ids are provided.
    Uses source_block_ids from LLM output to map segments to correct content blocks.
    Multiple segments can reference the same block for multi-beat fidelity.
    """
    if content_blocks is None:
        content_blocks = parse_content_blocks(source_markdown) if source_markdown else []
    
    # Build block lookup by block_id
    block_lookup = {block.get("block_id"): block for block in content_blocks}
    
    # Enhance segment_enrichments with content_type if not set
    enrichments = visuals_output.get("segment_enrichments", [])
    for i, enrichment in enumerate(enrichments):
        vc = enrichment.get("visual_content", {})
        
        # ISS-164 FIX: Check if we have source_block_ids - if so, ALWAYS use verbatim content
        source_block_ids = enrichment.get("source_block_ids", [])
        
        if source_block_ids and block_lookup:
            # ISS-164: Use verbatim_content from source blocks - override any LLM summaries
            block_id = source_block_ids[0]
            block = block_lookup.get(block_id)
            
            if block:
                block_type = block.get("block_type", "paragraph")
                verbatim = block.get("verbatim_content", "")
                
                if block_type == "unordered_list":
                    vc["content_type"] = "bullet_list"
                    # Use items from source, not LLM summaries
                    if block.get("items"):
                        vc["bullet_points"] = [{"level": 1, "text": item} for item in block["items"]]
                    vc["verbatim_source"] = verbatim
                elif block_type == "ordered_list":
                    vc["content_type"] = "ordered_list"
                    if block.get("items"):
                        vc["ordered_list"] = block["items"]
                    vc["verbatim_source"] = verbatim
                elif block_type == "formula":
                    vc["content_type"] = "formula"
                    vc["formula"] = verbatim  # Use exact LaTeX from source
                elif block_type == "table":
                    vc["content_type"] = "table"
                    vc["verbatim_text"] = verbatim  # Preserve table markdown
                    vc["has_inline_latex"] = block.get("has_inline_latex", False)
                else:
                    # Paragraph - use verbatim text
                    vc["content_type"] = "paragraph"
                    vc["verbatim_text"] = verbatim
                    vc["has_inline_latex"] = block.get("has_inline_latex", False)
                
                enrichment["visual_content"] = vc
                continue
        
        # Fallback: No source_block_ids - use LLM output as-is but set content_type
        if vc.get("bullet_points"):
            vc["content_type"] = "bullet_list"
        elif vc.get("ordered_list"):
            vc["content_type"] = "ordered_list"
        elif vc.get("formula") or vc.get("formulas"):
            vc["content_type"] = "formula"
        elif content_blocks:
            # ISS-164: Sequential mapping fallback when no source_block_ids
            block_idx = i % len(content_blocks)
            block = content_blocks[block_idx]
            block_type = block.get("block_type", "paragraph")
            verbatim = block.get("verbatim_content", "")
            
            if block_type == "unordered_list":
                vc["content_type"] = "bullet_list"
                if block.get("items"):
                    vc["bullet_points"] = [{"level": 1, "text": item} for item in block["items"]]
            elif block_type == "ordered_list":
                vc["content_type"] = "ordered_list"
                if block.get("items"):
                    vc["ordered_list"] = block["items"]
            elif block_type == "formula":
                vc["content_type"] = "formula"
                vc["formula"] = verbatim
            else:
                vc["content_type"] = "paragraph"
                vc["verbatim_text"] = verbatim
                vc["has_inline_latex"] = block.get("has_inline_latex", False)
        else:
            # No blocks available - default to paragraph
            vc["content_type"] = "paragraph"
        
        enrichment["visual_content"] = vc
    
    visuals_output["segment_enrichments"] = enrichments
    return visuals_output


def _json_serializer(obj):
    """Custom JSON serializer for non-serializable objects."""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        return str(obj)
    return str(obj)


def _save_artifact(output_dir: Optional[Path], filename: str, data: Dict) -> None:
    """Save agent output as artifact for debugging (ISS-149).
    
    Uses safe serialization with fallback to str() for non-serializable objects.
    Failures are logged but do not crash the pipeline.
    """
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


def _save_analytics(tracker: AnalyticsTracker, presentation: Optional[Dict], output_dir: Optional[Path]) -> None:
    """Save analytics data to analytics.json in the job folder."""
    if not output_dir:
        logger.warning("[Analytics] No output directory provided, skipping analytics save")
        return
        
    try:
        # Collect content metrics from presentation if available
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
                elif renderer in ("wan", "wan_video"):
                    wan_count += 1
                else:
                    static_count += 1
            
            tracker.set_content_metrics(
                total_sections=total_sections,
                total_segments=total_segments,
                total_slides=total_sections,
                section_types=section_types
            )
            
            tracker.set_renderer_metrics(
                manim_videos=manim_count,
                wan_videos=wan_count,
                static_slides=static_count
            )
        
        # Save analytics to file
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


def process_markdown_to_presentation_v15(
    markdown_content: str,
    subject: str,
    grade: str,
    job_id: str,
    update_status_callback=None,
    generate_tts: bool = True,
    output_dir: Optional[Path] = None,
    tts_provider: TTSProvider = "edge_tts",
    dry_run: bool = False,
    skip_wan: bool = False
) -> Tuple[Dict, AnalyticsTracker]:
    """
    V1.5 Pipeline: Process markdown to presentation.json using split agents.
    
    Pipeline Flow:
    1. SmartChunker → topics
    2. SectionPlanner(topics) → section_blueprints[]
    3. FOR EACH blueprint:
       - NarrationWriter(blueprint) → narration
       - VisualSpecArtist(blueprint, narration) → visuals
       - IF renderer != 'none': RendererSpecAgent(visuals) → render_spec
    4. MemoryFlashcardAgent(markdown) → memory_section
    5. RecapSceneAgent(markdown, concepts) → recap_section
    6. MergeStep(all_outputs) → presentation.json
    7. TTS(presentation) → audio files + updated durations
    
    Args:
        markdown_content: Raw markdown content from document
        subject: Subject area (e.g., "Biology", "Physics")
        grade: Grade level (e.g., "Grade 10")
        job_id: Unique job identifier
        update_status_callback: Optional callback for status updates
        generate_tts: Whether to generate TTS audio
        output_dir: Output directory for assets
        tts_provider: TTS provider - "edge_tts" (default), "narakeet", "estimate"
        
    Returns:
        Tuple of (presentation dict, analytics tracker)
        
    Raises:
        PipelineError: If any pipeline phase fails
    """
    logger.info(f"[Pipeline v1.5] Starting for job {job_id}")
    
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
        logger.info(f"[Pipeline v1.5] Extracted {len(topics)} topics")
        
        _save_artifact(output_dir, "01_chunker.json", chunker_output)
        
        quiz_questions = chunker_output.get("quiz_questions", [])
        logger.info(f"[Pipeline v1.5] Extracted {len(quiz_questions)} quiz questions")
        
        update_status("section_planner", "Planning section structure...")
        section_planner = SectionPlannerAgent(tracker=tracker, log_func=log)
        planner_output = section_planner.run(
            topics=topics,
            subject=subject,
            grade=grade,
            quiz_questions=quiz_questions
        )
        blueprints = planner_output.get("sections", [])
        logger.info(f"[Pipeline v1.5] Planned {len(blueprints)} sections")
        
        _save_artifact(output_dir, "02_planner.json", planner_output)
        
        section_artifacts = []
        manim_failed_sections = []
        
        for i, blueprint in enumerate(blueprints):
            section_type = blueprint.get("section_type")
            section_id = blueprint.get("section_id")
            
            if section_type in ["memory", "recap"]:
                continue
            
            update_status("narration", f"Writing narration for {section_id}...")
            
            source_topics = blueprint.get("source_topics", [])
            topic_blocks = []
            for topic in topics:
                if topic.get("topic_id") in source_topics:
                    topic_blocks.extend(topic.get("source_blocks", []))
            source_content = _extract_source_content(markdown_content, topic_blocks)
            
            section_quiz_questions = quiz_questions if section_type == "quiz" else []
            
            narration_writer = NarrationWriterAgent(tracker=tracker, log_func=log)
            narration_output = narration_writer.run(
                section_blueprint=blueprint,
                source_markdown=source_content,
                quiz_questions=section_quiz_questions
            )
            
            update_status("visuals", f"Designing visuals for {section_id}...")
            
            # ISS-160: Parse content blocks for source fidelity mapping
            content_blocks = parse_content_blocks(source_content) if source_content else []
            content_blocks_json = json.dumps(content_blocks, indent=2) if content_blocks else "[]"
            
            visual_artist = VisualSpecArtistAgent(tracker=tracker, log_func=log)
            visuals_output = visual_artist.run(
                section_blueprint=blueprint,
                narration=narration_output.get("narration", {}),
                source_markdown=source_content,
                content_blocks=content_blocks_json
            )
            
            # ISS-160: Post-process to ensure content_type is set deterministically using block IDs
            visuals_output = _enhance_visual_content_types(visuals_output, source_content, content_blocks)
            
            render_spec = None
            renderer = blueprint.get("suggested_renderer", "none")
            
            if renderer == "video":
                update_status("renderer_spec", f"Creating {renderer} spec for {section_id}...")
                
                visual_beats = visuals_output.get("visual_beats", [])
                narration_summary = narration_output.get("narration", {}).get("full_text", "")[:500]
                
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
                    logger.warning(f"[Pipeline v1.5] RendererSpec failed for {section_id}: {e}")
                    render_spec = None
            
            artifact = {
                "blueprint": blueprint,
                "narration": narration_output,
                "visuals": visuals_output,
                "render_spec": render_spec
            }
            section_artifacts.append(artifact)
            
            artifact_idx = len(section_artifacts) + 2
            _save_artifact(output_dir, f"{artifact_idx:02d}_{section_id}_narration.json", narration_output)
            _save_artifact(output_dir, f"{artifact_idx:02d}_{section_id}_visuals.json", visuals_output)
            if render_spec:
                _save_artifact(output_dir, f"{artifact_idx:02d}_{section_id}_render_spec.json", render_spec)
        
        update_status("memory", "Creating memory section with narration...")
        
        memory_blueprint = {
            "section_id": "memory",
            "section_type": "memory",
            "title": f"{subject} - Key Flashcards",
            "learning_goals": ["Review key concepts", "Test your understanding"],
            "suggested_renderer": "none",
            "avatar_visibility": "always",
            "avatar_position": "right",
            "avatar_width_percent": 52
        }
        
        memory_narration_writer = NarrationWriterAgent(tracker=tracker, log_func=log)
        memory_narration_output = memory_narration_writer.run(
            section_blueprint=memory_blueprint,
            source_markdown=markdown_content[:2000]
        )
        _save_artifact(output_dir, "memory_narration.json", memory_narration_output)
        
        memory_agent = MemoryFlashcardAgent(tracker=tracker, log_func=log)
        memory_output = memory_agent.run(
            source_markdown=markdown_content,
            subject=subject
        )
        memory_output["narration"] = memory_narration_output.get("narration", {})
        
        _save_artifact(output_dir, "memory.json", memory_output)
        
        key_concepts = [f.get("front", "") for f in memory_output.get("flashcards", [])]
        
        update_status("recap", "Creating recap section with narration...")
        
        recap_blueprint = {
            "section_id": "recap",
            "section_type": "recap",
            "title": f"{subject} - Chapter Recap",
            "learning_goals": ["Review all major concepts", "Reinforce learning with video"],
            "suggested_renderer": "video",
            "avatar_visibility": "always",
            "avatar_position": "right",
            "avatar_width_percent": 52
        }
        
        # ISS-166 FIX: Generate video prompts FIRST, then narration that matches them
        recap_agent = RecapSceneAgent(tracker=tracker, log_func=log)
        recap_output = recap_agent.run(
            source_markdown=markdown_content,
            subject=subject,
            key_concepts=key_concepts
        )
        _save_artifact(output_dir, "recap.json", recap_output)
        
        # Extract video prompt summaries for narration alignment
        video_prompts = recap_output.get("video_prompts", [])
        video_summaries = []
        for i, vp in enumerate(video_prompts):
            prompt = vp.get("prompt", "") if isinstance(vp, dict) else str(vp)
            # Extract first 50 words as summary for narration context
            words = prompt.split()[:50]
            video_summaries.append(f"Scene {i+1}: {' '.join(words)}...")
        
        # Add video summaries to blueprint for narration alignment
        recap_blueprint["video_scenes"] = video_summaries
        recap_blueprint["segment_count"] = 5  # Must match 5 videos
        
        recap_narration_writer = NarrationWriterAgent(tracker=tracker, log_func=log)
        recap_narration_output = recap_narration_writer.run(
            section_blueprint=recap_blueprint,
            source_markdown=markdown_content[:3000]
        )
        _save_artifact(output_dir, "recap_narration.json", recap_narration_output)
        
        recap_output["narration"] = recap_narration_output.get("narration", {})
        
        video_prompts = recap_output.get("video_prompts", [])
        for i, vp in enumerate(video_prompts):
            prompt = vp.get("prompt", "") if isinstance(vp, dict) else str(vp)
            char_count = len(prompt)
            word_count = len(prompt.split()) if prompt else 0
            if char_count > 800:
                raise PipelineError(
                    f"Recap prompt {i+1} exceeds 800 char limit ({char_count} chars). "
                    f"LLM must generate within limits.",
                    phase="recap_validation"
                )
            if word_count < 80:
                raise PipelineError(
                    f"Recap prompt {i+1} has only {word_count} words (minimum 80). "
                    f"Preview: '{prompt[:100]}...'",
                    phase="recap_validation"
                )
            logger.info(f"[Pipeline v1.5] Recap prompt {i+1}: {word_count} words, {char_count} chars - VALID")
        
        _save_artifact(output_dir, "recap.json", recap_output)
        
        update_status("merge", "Combining all components...")
        presentation = merge_agent_outputs(
            section_artifacts=section_artifacts,
            memory_output=memory_output,
            recap_output=recap_output,
            subject=subject,
            grade=grade
        )
        
        logger.info(f"[Pipeline v1.5] Merged {len(presentation.get('sections', []))} sections")
        
        if generate_tts:
            update_status("tts_duration", f"ISS-164: Simplified TTS (word count estimate + {tts_provider} audio)...")
            presentation = update_durations_simplified(
                presentation=presentation,
                output_dir=output_dir,
                production_provider=tts_provider
            )
        
        update_status("manim_code", "Generating Manim code with actual TTS timing...")
        manim_generator = ManimCodeGenerator()
        manim_success_count = 0
        manim_fail_count = 0
        
        for i, section in enumerate(presentation.get("sections", [])):
            renderer = section.get("renderer", "none")
            section_id = section.get("section_id", f"section_{i}")
            
            if renderer == "manim":
                logger.info(f"[Pipeline v1.5] Generating Manim code for {section_id}")
                
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
                    manim_code, validation_errors = manim_generator.generate(manim_input)
                    
                    if manim_code and len(manim_code) > 50:
                        if validation_errors:
                            logger.warning(f"[Pipeline v1.5] Manim validation warnings for {section_id}: {validation_errors}")
                        
                        section = integrate_manim_code_into_section(section, manim_code)
                        presentation["sections"][i] = section
                        
                        logger.info(f"[Pipeline v1.5] Manim code generated for {section_id} ({len(manim_code)} chars)")
                        manim_success_count += 1
                    else:
                        manim_failed_sections.append({
                            "section_id": section_id,
                            "section_index": i,
                            "error": "Empty or too short code returned",
                            "validation_errors": validation_errors,
                            "manim_input": manim_input
                        })
                        manim_fail_count += 1
                        logger.warning(f"[Pipeline v1.5] Manim code empty/short for {section_id}")
                    
                except Exception as e:
                    manim_failed_sections.append({
                        "section_id": section_id,
                        "section_index": i,
                        "error": str(e),
                        "manim_input": manim_input
                    })
                    manim_fail_count += 1
                    logger.error(f"[Pipeline v1.5] Manim code generation failed for {section_id}: {e}")
        
        if manim_failed_sections:
            _save_artifact(output_dir, "manim_failed_sections.json", {
                "failed_count": len(manim_failed_sections),
                "sections": manim_failed_sections,
                "note": "These sections can be retried via /api/v15/retry-manim endpoint"
            })
            logger.info(f"[Pipeline v1.5] Manim generation: {manim_success_count} success, {manim_fail_count} failed (saved for retry)")
        
        if output_dir and not dry_run:
            update_status("render_execute", "Rendering videos...")
            videos_dir = Path(output_dir) / "videos"
            videos_dir.mkdir(parents=True, exist_ok=True)
            
            presentation = enforce_renderer_policy(presentation)
            
            rendered_videos = render_all_topics(
                presentation=presentation,
                output_dir=str(videos_dir),
                dry_run=dry_run,
                skip_wan=skip_wan,
                output_dir_base=str(output_dir)
            )
            
            for result in rendered_videos:
                section_id_result = result.get("topic_id")
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
                            # Also populate visual_beats[].video_asset for player sync
                            visual_beats = section.get("visual_beats", [])
                            for idx, beat_path in enumerate(beat_videos):
                                if idx < len(visual_beats):
                                    visual_beats[idx]["video_asset"] = f"videos/{Path(beat_path).name}"
                                else:
                                    visual_beats.append({
                                        "segment_id": idx + 1,
                                        "video_asset": f"videos/{Path(beat_path).name}"
                                    })
                            section["visual_beats"] = visual_beats
                        if recap_video_paths:
                            section["recap_video_paths"] = [f"videos/{Path(p).name}" for p in recap_video_paths]
                        break
            
            success_count = sum(1 for r in rendered_videos if r.get("status") in ["success", "skipped"])
            fail_count = sum(1 for r in rendered_videos if r.get("status") == "failed")
            logger.info(f"[Pipeline v1.5] Rendering complete: {success_count} success, {fail_count} failed")
        
        tracker.end_pipeline(status="completed")
        
        # Collect and save content metrics
        _save_analytics(tracker, presentation, output_dir)
        
        logger.info(f"[Pipeline v1.5] Completed successfully for job {job_id}")
        
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
        logger.exception(f"[Pipeline v1.5] Unexpected error: {e}")
        raise PipelineError(f"Pipeline error: {e}", phase="unknown")


def resume_from_recap(
    job_id: str,
    output_dir: Path,
    markdown_content: str,
    subject: str = "General",
    grade: str = "General",
    tts_provider: TTSProvider = "edge_tts",
    generate_tts: bool = True,
    run_renderers: bool = True,
    dry_run: bool = False,
    skip_wan: bool = False,
    status_callback=None,
    log_callback=None
) -> Tuple[Dict, AnalyticsTracker]:
    """Resume pipeline from recap stage by loading existing artifacts.
    
    Use this when the pipeline failed at recap narration/scene generation.
    Loads: chunker, planner, section_artifacts, memory from artifacts folder.
    Runs: recap narration, recap agent, merge, TTS, renderers.
    """
    tracker = create_tracker(job_id)
    tracker.start_pipeline()
    
    def update_status(phase: str, message: str):
        logger.info(f"[Resume v1.5] {phase}: {message}")
        if status_callback:
            status_callback(phase, message)
    
    def log(message: str):
        logger.info(f"[Resume v1.5] {message}")
        if log_callback:
            log_callback(message)
    
    artifacts_dir = output_dir / "artifacts"
    if not artifacts_dir.exists():
        raise PipelineError(f"Artifacts directory not found: {artifacts_dir}", phase="resume_init")
    
    update_status("resume_init", f"Loading artifacts from {artifacts_dir}...")
    
    planner_path = artifacts_dir / "02_planner.json"
    if not planner_path.exists():
        raise PipelineError("02_planner.json not found", phase="resume_init")
    
    with open(planner_path) as f:
        planner_data = json.load(f)
        section_blueprints = planner_data.get("sections", planner_data) if isinstance(planner_data, dict) else planner_data
    
    memory_path = artifacts_dir / "memory.json"
    if not memory_path.exists():
        raise PipelineError("memory.json not found", phase="resume_init")
    
    with open(memory_path) as f:
        memory_output = json.load(f)
    
    section_artifacts = []
    idx = 3
    while True:
        prefix = f"{idx:02d}_section_"
        narration_files = list(artifacts_dir.glob(f"{prefix}*_narration.json"))
        if not narration_files:
            break
        
        narration_file = narration_files[0]
        section_id = narration_file.stem.replace(f"{idx:02d}_", "").replace("_narration", "")
        
        visuals_file = artifacts_dir / f"{idx:02d}_{section_id}_visuals.json"
        render_spec_file = artifacts_dir / f"{idx:02d}_{section_id}_render_spec.json"
        
        with open(narration_file) as f:
            narration_output = json.load(f)
        
        visuals_output = {}
        if visuals_file.exists():
            with open(visuals_file) as f:
                visuals_output = json.load(f)
        
        render_spec = None
        if render_spec_file.exists():
            with open(render_spec_file) as f:
                render_spec = json.load(f)
        
        blueprint = next((b for b in section_blueprints if b.get("section_id") == section_id), {})
        
        section_artifacts.append({
            "blueprint": blueprint,
            "narration": narration_output,
            "visuals": visuals_output,
            "render_spec": render_spec
        })
        idx += 1
    
    log(f"Loaded {len(section_artifacts)} section artifacts, memory output")
    
    key_concepts = [f.get("front", "") for f in memory_output.get("flashcards", [])]
    
    update_status("recap", "Creating recap section with narration (resumed)...")
    
    recap_blueprint = {
        "section_id": "recap",
        "section_type": "recap",
        "title": f"{subject} - Chapter Recap",
        "learning_goals": ["Review all major concepts", "Reinforce learning with video"],
        "suggested_renderer": "video",
        "avatar_visibility": "always",
        "avatar_position": "right",
        "avatar_width_percent": 52
    }
    
    # ISS-166 FIX: Generate video prompts FIRST, then narration that matches them (resumed flow)
    recap_agent = RecapSceneAgent(tracker=tracker, log_func=log)
    recap_output = recap_agent.run(
        source_markdown=markdown_content,
        subject=subject,
        key_concepts=key_concepts
    )
    _save_artifact(output_dir, "recap.json", recap_output)
    
    # Extract video prompt summaries for narration alignment
    video_prompts = recap_output.get("video_prompts", [])
    video_summaries = []
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
        logger.info(f"[Resume v1.5] Recap prompt {i+1}: {word_count} words, {char_count} chars - VALID")
        # Extract first 50 words as summary for narration context
        words = prompt.split()[:50]
        video_summaries.append(f"Scene {i+1}: {' '.join(words)}...")
    
    # Add video summaries to blueprint for narration alignment
    recap_blueprint["video_scenes"] = video_summaries
    recap_blueprint["segment_count"] = 5  # Must match 5 videos
    
    recap_narration_writer = NarrationWriterAgent(tracker=tracker, log_func=log)
    recap_narration_output = recap_narration_writer.run(
        section_blueprint=recap_blueprint,
        source_markdown=markdown_content[:3000]
    )
    _save_artifact(output_dir, "recap_narration.json", recap_narration_output)
    
    recap_output["narration"] = recap_narration_output.get("narration", {})
    
    update_status("merge", "Combining all components...")
    presentation = merge_agent_outputs(
        section_artifacts=section_artifacts,
        memory_output=memory_output,
        recap_output=recap_output,
        subject=subject,
        grade=grade
    )
    
    logger.info(f"[Resume v1.5] Merged {len(presentation.get('sections', []))} sections")
    
    if generate_tts:
        update_status("tts_duration", f"Generating TTS audio with {tts_provider}...")
        presentation = update_durations_simplified(
            presentation=presentation,
            output_dir=output_dir,
            production_provider=tts_provider
        )
    
    update_status("manim_code", "Generating Manim code...")
    manim_generator = ManimCodeGenerator()
    manim_failed_sections = []
    
    for i, section in enumerate(presentation.get("sections", [])):
        renderer = section.get("renderer", "none")
        section_id = section.get("section_id", f"section_{i}")
        
        if renderer == "manim":
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
                manim_code, validation_errors = manim_generator.generate(manim_input)
                if manim_code and len(manim_code) > 50:
                    section = integrate_manim_code_into_section(section, manim_code)
                    presentation["sections"][i] = section
            except Exception as e:
                logger.warning(f"[Resume v1.5] Manim failed for {section_id}: {e}")
    
    if run_renderers and not dry_run:
        update_status("render", "Executing renderers...")
        videos_dir = output_dir / "videos"
        videos_dir.mkdir(exist_ok=True)
        
        presentation = enforce_renderer_policy(presentation)
        
        rendered_videos = render_all_topics(
            presentation=presentation,
            output_dir=str(videos_dir),
            dry_run=dry_run,
            skip_wan=skip_wan,
            output_dir_base=str(output_dir)
        )
        
        for result in rendered_videos:
            section_id_result = result.get("topic_id")
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
                        # Also populate visual_beats[].video_asset for player sync
                        visual_beats = section.get("visual_beats", [])
                        for idx, beat_path in enumerate(beat_videos):
                            if idx < len(visual_beats):
                                visual_beats[idx]["video_asset"] = f"videos/{Path(beat_path).name}"
                            else:
                                visual_beats.append({
                                    "segment_id": idx + 1,
                                    "video_asset": f"videos/{Path(beat_path).name}"
                                })
                        section["visual_beats"] = visual_beats
                    if recap_video_paths:
                        section["recap_video_paths"] = [f"videos/{Path(p).name}" for p in recap_video_paths]
                    break
    
    tracker.end_pipeline(status="completed")
    logger.info(f"[Resume v1.5] Completed successfully for job {job_id}")
    
    return presentation, tracker


def resume_from_section(
    job_id: str,
    output_dir: Path,
    markdown_content: str,
    resume_from_section_idx: int,
    subject: str = "General",
    grade: str = "General",
    tts_provider: TTSProvider = "edge_tts",
    generate_tts: bool = True,
    run_renderers: bool = True,
    dry_run: bool = False,
    skip_wan: bool = False,
    status_callback=None,
    log_callback=None
) -> Tuple[Dict, AnalyticsTracker]:
    """Resume pipeline from a specific failed section by loading existing artifacts.
    
    Use this when the pipeline failed at a specific section (e.g., NarrationWriter for section 8).
    Loads: chunker, planner, and all completed section artifacts.
    Runs: remaining sections from resume_from_section_idx, memory, recap, merge, TTS, renderers.
    
    Args:
        job_id: Job identifier
        output_dir: Job output directory
        markdown_content: Source markdown content
        resume_from_section_idx: 0-based index of section to resume from (the failed one)
        subject: Subject area
        grade: Grade level
        tts_provider: TTS provider
        generate_tts: Whether to generate TTS
        run_renderers: Whether to run renderers
        dry_run: Dry run mode
        skip_wan: Skip WAN video generation
        status_callback: Status update callback
        log_callback: Log callback
        
    Returns:
        Tuple of (presentation dict, analytics tracker)
    """
    tracker = create_tracker(job_id)
    tracker.start_pipeline()
    
    def update_status(phase: str, message: str):
        logger.info(f"[Resume v1.5] {phase}: {message}")
        if status_callback:
            status_callback(phase, message)
    
    def log(message: str):
        logger.info(f"[Resume v1.5] {message}")
        if log_callback:
            log_callback(message)
    
    artifacts_dir = output_dir / "artifacts"
    if not artifacts_dir.exists():
        raise PipelineError(f"Artifacts directory not found: {artifacts_dir}", phase="resume_init")
    
    update_status("resume_init", f"Loading artifacts from {artifacts_dir}...")
    
    chunker_path = artifacts_dir / "01_chunker.json"
    if not chunker_path.exists():
        raise PipelineError("01_chunker.json not found", phase="resume_init")
    
    with open(chunker_path) as f:
        chunker_output = json.load(f)
        topics = chunker_output.get("topics", [])
        quiz_questions = chunker_output.get("quiz_questions", [])
    
    planner_path = artifacts_dir / "02_planner.json"
    if not planner_path.exists():
        raise PipelineError("02_planner.json not found", phase="resume_init")
    
    with open(planner_path) as f:
        planner_data = json.load(f)
        blueprints = planner_data.get("sections", [])
    
    log(f"Loaded {len(blueprints)} section blueprints, resuming from section {resume_from_section_idx}")
    
    section_artifacts = []
    
    content_section_idx = 0
    for i, blueprint in enumerate(blueprints):
        section_type = blueprint.get("section_type")
        section_id = blueprint.get("section_id")
        
        if section_type in ["memory", "recap"]:
            continue
        
        if i < resume_from_section_idx:
            artifact_idx = content_section_idx + 3
            narration_file = artifacts_dir / f"{artifact_idx:02d}_{section_id}_narration.json"
            visuals_file = artifacts_dir / f"{artifact_idx:02d}_{section_id}_visuals.json"
            render_spec_file = artifacts_dir / f"{artifact_idx:02d}_{section_id}_render_spec.json"
            
            if narration_file.exists() and visuals_file.exists():
                with open(narration_file) as f:
                    narration_output = json.load(f)
                with open(visuals_file) as f:
                    visuals_output = json.load(f)
                
                render_spec = None
                if render_spec_file.exists():
                    with open(render_spec_file) as f:
                        render_spec = json.load(f)
                
                section_artifacts.append({
                    "blueprint": blueprint,
                    "narration": narration_output,
                    "visuals": visuals_output,
                    "render_spec": render_spec
                })
                log(f"Loaded existing artifact for {section_id}")
                content_section_idx += 1
                continue
        
        update_status("narration", f"Writing narration for {section_id}...")
        
        source_topics = blueprint.get("source_topics", [])
        topic_blocks = []
        for topic in topics:
            if topic.get("topic_id") in source_topics:
                topic_blocks.extend(topic.get("source_blocks", []))
        source_content = _extract_source_content(markdown_content, topic_blocks)
        
        section_quiz_questions = quiz_questions if section_type == "quiz" else []
        
        narration_writer = NarrationWriterAgent(tracker=tracker, log_func=log)
        narration_output = narration_writer.run(
            section_blueprint=blueprint,
            source_markdown=source_content,
            quiz_questions=section_quiz_questions
        )
        
        update_status("visuals", f"Designing visuals for {section_id}...")
        
        content_blocks = parse_content_blocks(source_content) if source_content else []
        content_blocks_json = json.dumps(content_blocks, indent=2) if content_blocks else "[]"
        
        visual_artist = VisualSpecArtistAgent(tracker=tracker, log_func=log)
        visuals_output = visual_artist.run(
            section_blueprint=blueprint,
            narration=narration_output.get("narration", {}),
            source_markdown=source_content,
            content_blocks=content_blocks_json
        )
        
        visuals_output = _enhance_visual_content_types(visuals_output, source_content, content_blocks)
        
        render_spec = None
        renderer = blueprint.get("suggested_renderer", "none")
        
        if renderer == "video":
            update_status("renderer_spec", f"Creating {renderer} spec for {section_id}...")
            
            visual_beats = visuals_output.get("visual_beats", [])
            narration_summary = narration_output.get("narration", {}).get("full_text", "")[:500]
            
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
                logger.warning(f"[Resume v1.5] RendererSpec failed for {section_id}: {e}")
                render_spec = None
        
        artifact = {
            "blueprint": blueprint,
            "narration": narration_output,
            "visuals": visuals_output,
            "render_spec": render_spec
        }
        section_artifacts.append(artifact)
        
        artifact_idx = len(section_artifacts) + 2
        _save_artifact(output_dir, f"{artifact_idx:02d}_{section_id}_narration.json", narration_output)
        _save_artifact(output_dir, f"{artifact_idx:02d}_{section_id}_visuals.json", visuals_output)
        if render_spec:
            _save_artifact(output_dir, f"{artifact_idx:02d}_{section_id}_render_spec.json", render_spec)
        
        content_section_idx += 1
    
    update_status("memory", "Creating memory section...")
    
    memory_blueprint = {
        "section_id": "memory",
        "section_type": "memory",
        "title": f"{subject} - Key Flashcards",
        "learning_goals": ["Review key concepts", "Test your understanding"],
        "suggested_renderer": "none",
        "avatar_visibility": "always",
        "avatar_position": "right",
        "avatar_width_percent": 52
    }
    
    memory_narration_writer = NarrationWriterAgent(tracker=tracker, log_func=log)
    memory_narration_output = memory_narration_writer.run(
        section_blueprint=memory_blueprint,
        source_markdown=markdown_content[:2000]
    )
    _save_artifact(output_dir, "memory_narration.json", memory_narration_output)
    
    memory_agent = MemoryFlashcardAgent(tracker=tracker, log_func=log)
    memory_output = memory_agent.run(
        source_markdown=markdown_content,
        subject=subject
    )
    memory_output["narration"] = memory_narration_output.get("narration", {})
    
    _save_artifact(output_dir, "memory.json", memory_output)
    
    key_concepts = [f.get("front", "") for f in memory_output.get("flashcards", [])]
    
    update_status("recap", "Creating recap section...")
    
    recap_blueprint = {
        "section_id": "recap",
        "section_type": "recap",
        "title": f"{subject} - Chapter Recap",
        "learning_goals": ["Review all major concepts", "Reinforce learning with video"],
        "suggested_renderer": "video",
        "avatar_visibility": "always",
        "avatar_position": "right",
        "avatar_width_percent": 52
    }
    
    recap_agent = RecapSceneAgent(tracker=tracker, log_func=log)
    recap_output = recap_agent.run(
        source_markdown=markdown_content,
        subject=subject,
        key_concepts=key_concepts
    )
    _save_artifact(output_dir, "recap.json", recap_output)
    
    video_prompts = recap_output.get("video_prompts", [])
    video_summaries = []
    for i_vp, vp in enumerate(video_prompts):
        prompt = vp.get("prompt", "") if isinstance(vp, dict) else str(vp)
        words = prompt.split()[:50]
        video_summaries.append(f"Scene {i_vp+1}: {' '.join(words)}...")
    
    recap_blueprint["video_scenes"] = video_summaries
    recap_blueprint["segment_count"] = 5
    
    recap_narration_writer = NarrationWriterAgent(tracker=tracker, log_func=log)
    recap_narration_output = recap_narration_writer.run(
        section_blueprint=recap_blueprint,
        source_markdown=markdown_content[:3000]
    )
    _save_artifact(output_dir, "recap_narration.json", recap_narration_output)
    
    recap_output["narration"] = recap_narration_output.get("narration", {})
    
    update_status("merge", "Combining all components...")
    presentation = merge_agent_outputs(
        section_artifacts=section_artifacts,
        memory_output=memory_output,
        recap_output=recap_output,
        subject=subject,
        grade=grade
    )
    
    logger.info(f"[Resume v1.5] Merged {len(presentation.get('sections', []))} sections")
    
    if generate_tts:
        update_status("tts_duration", f"Generating TTS audio with {tts_provider}...")
        presentation = update_durations_simplified(
            presentation=presentation,
            output_dir=output_dir,
            production_provider=tts_provider
        )
    
    update_status("manim_code", "Generating Manim code...")
    manim_generator = ManimCodeGenerator()
    
    for i_sec, section in enumerate(presentation.get("sections", [])):
        renderer = section.get("renderer", "none")
        section_id = section.get("section_id", f"section_{i_sec}")
        
        if renderer == "manim":
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
                manim_code, validation_errors = manim_generator.generate(manim_input)
                if manim_code and len(manim_code) > 50:
                    section = integrate_manim_code_into_section(section, manim_code)
                    presentation["sections"][i_sec] = section
            except Exception as e:
                logger.warning(f"[Resume v1.5] Manim failed for {section_id}: {e}")
    
    if run_renderers and not dry_run:
        update_status("render", "Executing renderers...")
        videos_dir = output_dir / "videos"
        videos_dir.mkdir(exist_ok=True)
        
        presentation = enforce_renderer_policy(presentation)
        
        rendered_videos = render_all_topics(
            presentation=presentation,
            output_dir=str(videos_dir),
            dry_run=dry_run,
            skip_wan=skip_wan,
            output_dir_base=str(output_dir)
        )
        
        for result in rendered_videos:
            section_id_result = result.get("topic_id")
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
                        # Also populate visual_beats[].video_asset for player sync
                        visual_beats = section.get("visual_beats", [])
                        for idx, beat_path in enumerate(beat_videos):
                            if idx < len(visual_beats):
                                visual_beats[idx]["video_asset"] = f"videos/{Path(beat_path).name}"
                            else:
                                visual_beats.append({
                                    "segment_id": idx + 1,
                                    "video_asset": f"videos/{Path(beat_path).name}"
                                })
                        section["visual_beats"] = visual_beats
                    if recap_video_paths:
                        section["recap_video_paths"] = [f"videos/{Path(p).name}" for p in recap_video_paths]
                    break
    
    presentation_path = output_dir / "presentation.json"
    with open(presentation_path, "w") as f:
        json.dump(presentation, f, indent=2)
    
    tracker.end_pipeline(status="completed")
    _save_analytics(tracker, presentation, output_dir)
    
    logger.info(f"[Resume v1.5] Completed successfully for job {job_id}")
    
    return presentation, tracker

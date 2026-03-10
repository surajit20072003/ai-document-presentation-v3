"""
Pipeline v1.4 - Split Director Architecture

Orchestrates the complete V1.4 pipeline:
- Pass 0: Smart Chunker (topic extraction)
- Pass 1a: Content Director (intro/summary/content/example/quiz)
- Pass 1b: Recap Director (memory/recap with video prompts)
- Merge Step: Combine outputs into single presentation.json
- Pass 1.5: TTS Duration (generate audio, measure actual duration)
- Validation: 3-tier validation (structural, semantic, quality)
- Pass 2: Renderers (Remotion/Manim/WAN)

This resolves ISS-080: Director LLM Fails v1.3 Structural Validation.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from core.smart_chunker import call_smart_chunker, ChunkerError
from core.content_director import call_content_director, ContentDirectorError
from core.recap_director import call_recap_director, RecapDirectorError
from core.merge_step import merge_director_outputs, get_section_stats
from core.tts_duration import update_durations_from_tts, cleanup_temp_audio, TTSProvider
from core.analytics import AnalyticsTracker, create_tracker

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "1.4"


class PipelineError(Exception):
    """Error raised when pipeline fails."""
    def __init__(self, message: str, phase: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.phase = phase
        self.details = details or {}


def process_markdown_to_presentation_v14(
    markdown_content: str,
    subject: str,
    grade: str,
    job_id: str,
    update_status_callback = None,
    generate_tts: bool = True,
    output_dir: Optional[Path] = None,
    tts_provider: TTSProvider = "edge_tts"
) -> Tuple[Dict, AnalyticsTracker]:
    """
    V1.4 Pipeline: Process markdown to presentation.json.
    
    This is the main entry point for V1.4 pipeline. It orchestrates:
    1. Smart Chunker (topic extraction)
    2. Content Director + Recap Director (parallel or sequential)
    3. Merge Step
    4. TTS Duration measurement
    5. Validation
    
    Args:
        markdown_content: Raw markdown content from document
        subject: Subject area (e.g., "Biology", "Physics")
        grade: Grade level (e.g., "Grade 10")
        job_id: Unique job identifier
        update_status_callback: Optional callback for status updates
        generate_tts: Whether to generate TTS audio for duration measurement
        output_dir: Output directory for assets
        tts_provider: TTS provider - "edge_tts" (default), "narakeet", "pyttsx3", "estimate"
        
    Returns:
        Tuple of (presentation dict, analytics tracker)
        
    Raises:
        PipelineError: If any pipeline phase fails
    """
    logger.info(f"[Pipeline v1.4] Starting for job {job_id}")
    
    tracker = create_tracker(job_id)
    tracker.start_pipeline()
    
    def update_status(phase: str, message: str):
        if update_status_callback:
            update_status_callback(job_id, phase, message)
        logger.info(f"[{phase}] {message}")
    
    try:
        update_status("chunker", "Analyzing content structure...")
        chunker_output = call_smart_chunker(
            markdown_content=markdown_content,
            subject=subject,
            tracker=tracker,
            max_retries=2
        )
        
        topics = chunker_output.get("topics", [])
        logger.info(f"[Pipeline v1.4] Extracted {len(topics)} topics")
        
        update_status("content_director", "Creating lesson structure...")
        content_output = call_content_director(
            topics=topics,
            subject=subject,
            grade=grade,
            tracker=tracker,
            max_structural_retries=4,
            max_semantic_retries=2
        )
        
        update_status("recap_director", "Creating memory aids and recap...")
        recap_output = call_recap_director(
            full_markdown=markdown_content,
            subject=subject,
            grade=grade,
            tracker=tracker,
            max_structural_retries=2,
            max_semantic_retries=1
        )
        
        update_status("merge", "Combining lesson components...")
        presentation = merge_director_outputs(
            content_output=content_output,
            recap_output=recap_output,
            subject=subject,
            grade=grade
        )
        
        stats = get_section_stats(presentation)
        logger.info(f"[Pipeline v1.4] Merged: {stats}")
        
        if generate_tts:
            update_status("tts_duration", f"Measuring audio durations ({tts_provider})...")
            presentation = update_durations_from_tts(
                presentation=presentation,
                output_dir=output_dir,
                generate_audio=True,
                tts_provider=tts_provider
            )
        
        update_status("validation", "Validating lesson structure...")
        validation_result = validate_presentation_v14(presentation)
        
        if validation_result["has_errors"]:
            error_summary = "; ".join(validation_result["errors"][:5])
            raise PipelineError(
                f"Validation failed: {error_summary}",
                phase="validation",
                details=validation_result
            )
        
        if validation_result["warnings"]:
            logger.warning(f"[Pipeline v1.4] Validation warnings: {validation_result['warnings']}")
        
        logger.info(f"[Pipeline v1.4] Trace: chunker={len(topics)} topics, "
                    f"content={len(content_output.get('sections', []))} sections, "
                    f"recap={len(recap_output.get('sections', []))} sections")
        
        tracker.end_pipeline(status="completed")
        logger.info(f"[Pipeline v1.4] Completed successfully for job {job_id}")
        
        return presentation, tracker
        
    except ChunkerError as e:
        tracker.end_pipeline(status="failed", error=str(e))
        raise PipelineError(f"Chunker failed: {e}", phase="chunker")
        
    except ContentDirectorError as e:
        tracker.end_pipeline(status="failed", error=str(e))
        raise PipelineError(f"Content Director failed: {e}", phase="content_director")
        
    except RecapDirectorError as e:
        tracker.end_pipeline(status="failed", error=str(e))
        raise PipelineError(f"Recap Director failed: {e}", phase="recap_director")
        
    except Exception as e:
        tracker.end_pipeline(status="failed", error=str(e))
        logger.error(f"[Pipeline v1.4] Unexpected error: {e}")
        raise PipelineError(f"Pipeline failed: {e}", phase="unknown")


SKIP_DIRECTIVE_SECTIONS = ["memory", "recap"]


def validate_presentation_v14(presentation: Dict) -> Dict:
    """
    Run 3-tier validation on merged presentation.
    
    Tier 1: Structural (required fields, valid values)
    Tier 2: Semantic (content rules, mutual exclusion)
    Tier 3: Quality (warnings only)
    
    Returns:
        Dict with has_errors, errors list, warnings list
    """
    errors = []
    warnings = []
    
    sections = presentation.get("sections", [])
    section_types = [s.get("section_type") for s in sections]
    
    required_types = ["intro", "summary", "memory", "recap"]
    for req_type in required_types:
        if req_type not in section_types:
            errors.append(f"Missing required section: {req_type}")
    
    for i, section in enumerate(sections):
        prefix = f"sections[{i}]"
        
        if "section_id" not in section:
            errors.append(f"{prefix}: missing section_id")
        if "section_type" not in section:
            errors.append(f"{prefix}: missing section_type")
        if "renderer" not in section:
            errors.append(f"{prefix}: missing renderer")
        if "narration" not in section:
            errors.append(f"{prefix}: missing narration")
        
        narration = section.get("narration", {})
        segments = narration.get("segments", [])
        section_type = section.get("section_type", "")
        
        for j, seg in enumerate(segments):
            seg_prefix = f"{prefix}.segments[{j}]"
            dd = seg.get("display_directives", {})
            
            if not dd:
                if section_type not in SKIP_DIRECTIVE_SECTIONS:
                    errors.append(f"{seg_prefix}: missing display_directives")
            elif section_type not in SKIP_DIRECTIVE_SECTIONS:
                text_layer = dd.get("text_layer")
                visual_layer = dd.get("visual_layer")
                
                if text_layer == "show" and visual_layer == "show":
                    errors.append(f"{seg_prefix}: mutual exclusion violation")
    
    memory_sections = [s for s in sections if s.get("section_type") == "memory"]
    for mem in memory_sections:
        flashcards = mem.get("flashcards", [])
        if len(flashcards) != 5:
            errors.append(f"Memory section must have exactly 5 flashcards, got {len(flashcards)}")
    
    recap_sections = [s for s in sections if s.get("section_type") == "recap"]
    for recap in recap_sections:
        recap_scenes = recap.get("recap_scenes", [])
        visual_beats = recap.get("visual_beats", [])
        
        if len(recap_scenes) < 5 and len(visual_beats) < 5:
            errors.append(f"Recap section must have 5 scenes, got {max(len(recap_scenes), len(visual_beats))}")
        
        layout = recap.get("layout", {})
        if layout.get("avatar_position") != "hidden":
            errors.append("Recap avatar must be hidden")
        
        narration = recap.get("narration", {})
        full_text = narration.get("full_text", "")
        word_count = len(full_text.split())
        if word_count < 150:
            warnings.append(f"Recap narration short: {word_count} words (expected 200-600)")
        if word_count > 700:
            warnings.append(f"Recap narration long: {word_count} words (expected 200-600)")
    
    content_sections = [s for s in sections if s.get("section_type") == "content"]
    for content in content_sections:
        narration = content.get("narration", {})
        full_text = narration.get("full_text", "")
        word_count = len(full_text.split())
        if word_count < 100:
            warnings.append(f"Content section narration short: {word_count} words")
    
    total_segments = sum(
        len(s.get("narration", {}).get("segments", []))
        for s in sections
    )
    if total_segments > 50:
        warnings.append(f"High segment count: {total_segments} (may affect performance)")
    
    return {
        "has_errors": len(errors) > 0,
        "errors": errors,
        "warnings": warnings,
        "section_count": len(sections),
        "total_segments": total_segments
    }


def process_with_renderers_v14(
    presentation: Dict,
    tracker: AnalyticsTracker,
    job_id: str,
    update_status_callback = None,
    use_remotion: bool = True,
    output_dir: Optional[Path] = None,
    dry_run: bool = False,
    skip_wan: bool = False
) -> Dict:
    """
    Pass 2: Dispatch to renderers and execute rendering.
    
    This is called after presentation.json is generated and validated.
    It does TWO things:
    1. Generate render specs (manim_scene_spec, video_prompts) via LLM
    2. Execute renderers (Manim CLI, WAN API) to create actual video files
    
    ISS-111 FIX: Added render_all_topics() call to actually execute renderers.
    
    Args:
        presentation: Validated presentation.json
        tracker: Analytics tracker
        job_id: Job identifier
        update_status_callback: Status callback
        use_remotion: Enable Remotion renderer
        output_dir: Output directory for rendered videos
        dry_run: If True, validate only without actual rendering
        skip_wan: If True, skip WAN API calls (for testing)
        
    Returns:
        Updated presentation with rendered content and video paths
    """
    from core.llm_client_v12 import pass2_dispatch_renderers
    from core.renderer_executor import render_all_topics, enforce_renderer_policy
    
    if update_status_callback:
        update_status_callback(job_id, "render_specs", "Generating render specifications...")
    
    presentation = pass2_dispatch_renderers(
        presentation=presentation,
        tracker=tracker,
        use_remotion=use_remotion
    )
    
    if output_dir:
        videos_dir = Path(output_dir) / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)
        
        if update_status_callback:
            update_status_callback(job_id, "render_execute", "Rendering videos...")
        
        presentation = enforce_renderer_policy(presentation)
        
        rendered_videos = render_all_topics(
            presentation=presentation,
            output_dir=str(videos_dir),
            dry_run=dry_run,
            skip_wan=skip_wan,
            output_dir_base=str(output_dir)
        )
        
        for result in rendered_videos:
            section_id = result.get("topic_id")
            video_path = result.get("video_path")
            beat_videos = result.get("beat_videos", [])
            recap_video_paths = result.get("recap_video_paths", [])
            
            for section in presentation.get("sections", []):
                if section.get("section_id") == section_id:
                    if video_path:
                        rel_path = str(Path(video_path).name) if "/" in str(video_path) else video_path
                        section["video_path"] = f"videos/{rel_path}"
                    if beat_videos:
                        section["beat_videos"] = [f"videos/{Path(p).name}" for p in beat_videos]
                    if recap_video_paths:
                        section["recap_video_paths"] = [f"videos/{Path(p).name}" for p in recap_video_paths]
                    break
        
        success_count = sum(1 for r in rendered_videos if r.get("status") in ["success", "skipped"])
        fail_count = sum(1 for r in rendered_videos if r.get("status") == "failed")
        logger.info(f"[Pipeline v1.4] Rendering complete: {success_count} success, {fail_count} failed")
    
    return presentation


def get_pipeline_version() -> str:
    """Return current pipeline version."""
    return PIPELINE_VERSION


def get_pipeline_info() -> Dict:
    """Return pipeline information for debugging."""
    return {
        "version": PIPELINE_VERSION,
        "architecture": "Split Director with Scene Architecture",
        "passes": {
            "0": "Smart Chunker (topic extraction)",
            "1a": "Content Director (intro/summary/content/example/quiz)",
            "1b": "Recap Director (memory + 5 recap_scene sections)",
            "1.5": "TTS Duration (audio measurement)",
            "2": "Renderers (Remotion/Manim/WAN)"
        },
        "section_types": {
            "from_content_director": ["intro", "summary", "content", "example", "quiz"],
            "from_recap_director": ["memory", "recap_scene_1", "recap_scene_2", "recap_scene_3", "recap_scene_4", "recap_scene_5"]
        },
        "retry_strategy": {
            "smart_chunker": {"structural": 2, "semantic": 0},
            "content_director": {"structural": 4, "semantic": 2},
            "recap_director": {"structural": 2, "semantic": 1}
        },
        "models": {
            "chunker": "google/gemini-2.5-pro",
            "content_director": "google/gemini-2.5-pro",
            "recap_director": "google/gemini-2.5-pro",
            "remotion_renderer": "anthropic/claude-sonnet-4",
            "manim_renderer": "anthropic/claude-sonnet-4",
            "video_renderer": "google/gemini-2.5-pro"
        }
    }

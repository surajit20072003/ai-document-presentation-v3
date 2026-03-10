"""
Pipeline v1.3 - Deterministic Educational Film Engine

This pipeline uses the v1.3 architecture with strict schema enforcement:
- Parse: Chunker (Gemini Flash) - Split markdown into chunks
- Direct: Director (Gemini Pro) - Pedagogy, structure, timing, display_directives
- Render: Specialized Renderers - Generate scene specs
    - Manim Renderer (Claude Sonnet) - Math/physics/formulas
    - Remotion Renderer (Claude Sonnet) - intro/summary/memory/quiz motion graphics
    - Video Renderer (Gemini Pro) - WAN video prompts for content/recap

v1.3 CHANGES:
- Director decides renderer. Pipeline obeys. No collapse logic.
- All sections have visual_beats (including intro/summary/memory).
- Schema validation runs BEFORE Python semantic validation.
- Normalization is pass-through only - missing structure = hard fail.
- use_remotion defaults to True.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from core.datalab_client import pdf_to_markdown
from core.llm_client_v12 import generate_presentation_v12, generate_presentation_v14_hybrid, PipelineError
from core.renderer_executor import render_all_topics, enforce_renderer_policy
from core.image_processor import extract_images_from_markdown, strip_base64_from_markdown, create_image_list_for_llm
from core.traceability import init_traceability, log_event, log_validation, log_hard_fail, complete_trace, save_render_prompts_json
from core.schema_validator import validate_presentation as validate_schema
from core.validators import validate as validate_3tier, ValidationResult
from tts.generate_audio import generate_all_audio, sync_timing_with_audio
from render.render_trace import clear_render_trace


def normalize_director_output(presentation: dict) -> dict:
    """
    Normalize Director LLM output to canonical v1.3 schema (PASS-THROUGH MODE).
    
    v1.3 CHANGE: This is strictly pass-through. It ONLY renames fields that exist.
    It does NOT create, infer, or fabricate any missing structures.
    Missing required fields will trigger schema validation failure → retry or hard fail.
    
    Allowed operations (RENAMING ONLY):
    - "scenes" key → "recap_scenes" key (if exists)
    - "narration_beats" key → kept as-is (schema expects narration.segments)
    - "lesson_plan" key → "sections" key (if exists)
    - "topics" key → "sections" key (if exists)
    
    NOT ALLOWED:
    - Creating visual_beats from embedded objects
    - Creating recap_scenes from narration_segments
    - Inferring word_count, duration_seconds, or renderer
    - Creating any field that doesn't exist in LLM output
    """
    print("[Normalize v1.3] Pass-through mode - renaming only, no fabrication")
    
    if "lesson_plan" in presentation and "sections" not in presentation:
        presentation["sections"] = presentation.pop("lesson_plan")
        print("[Normalize v1.3] Renamed 'lesson_plan' → 'sections'")
    
    if "topics" in presentation and "sections" not in presentation:
        presentation["sections"] = presentation.pop("topics")
        print("[Normalize v1.3] Renamed 'topics' → 'sections'")
    
    sections = presentation.get("sections", [])
    
    for section in sections:
        section_type = section.get("section_type", "")
        section_id = section.get("section_id", "?")
        
        if "scenes" in section and "recap_scenes" not in section:
            section["recap_scenes"] = section.pop("scenes")
            print(f"[Normalize v1.3] Section {section_id}: Renamed 'scenes' → 'recap_scenes'")
        
        if isinstance(section.get("renderer"), dict):
            renderer_dict = section["renderer"]
            section["renderer"] = renderer_dict.get("type", renderer_dict.get("name", "unknown"))
            print(f"[Normalize v1.3] Section {section_id}: Flattened renderer dict → '{section['renderer']}'")
    
    return presentation

PLAYER_ASSETS_DIR = Path(__file__).parent.parent / "player" / "assets"


def _reconcile_video_paths(presentation: dict, rendered_videos: list):
    """Update presentation sections with their rendered video paths.
    
    Matches rendered_videos results back to sections using section_id/topic_id.
    ISS-092 FIX: Also sets recap_video_paths for recap sections.
    ISS-093 FIX: Also sets beat_videos for Manim multi-beat sections.
    """
    sections = presentation.get("sections", presentation.get("topics", []))
    
    video_map = {}
    recap_paths_map = {}
    beat_videos_map = {}
    for result in rendered_videos:
        topic_id = result.get("topic_id")
        if topic_id:
            if result.get("video_path"):
                video_map[str(topic_id)] = result.get("video_path")
            # ISS-092: Capture recap video paths if present
            if result.get("recap_video_paths"):
                recap_paths_map[str(topic_id)] = result.get("recap_video_paths")
            # ISS-093: Capture Manim beat videos if present
            if result.get("beat_videos"):
                beat_videos_map[str(topic_id)] = result.get("beat_videos")
    
    recap_count = 0
    beat_count = 0
    for section in sections:
        section_id = section.get("section_id", section.get("id"))
        section_type = section.get("section_type", "")
        
        if section_id and str(section_id) in video_map:
            video_path = video_map[str(section_id)]
            video_filename = Path(video_path).name if video_path else None
            if video_filename:
                section["content_video_path"] = f"videos/{video_filename}"
                section["video_path"] = f"videos/{video_filename}"
                section["has_content_video"] = True
        
        # ISS-093 FIX: Set beat_videos for Manim multi-beat sections
        if str(section_id) in beat_videos_map:
            all_beats = beat_videos_map[str(section_id)]
            section["beat_videos"] = [f"videos/{Path(p).name}" for p in all_beats]
            section["has_content_video"] = True
            beat_count += 1
            print(f"[RECONCILE] Set beat_videos for section {section_id}: {len(all_beats)} beats")
        
        # ISS-092 FIX: Set recap_video_paths for recap sections
        if section_type == "recap" and str(section_id) in recap_paths_map:
            all_paths = recap_paths_map[str(section_id)]
            # Convert full paths to relative paths
            section["recap_video_paths"] = [f"videos/{Path(p).name}" for p in all_paths]
            section["has_content_video"] = True
            # Also set video_path to first recap video (player expects this)
            if all_paths:
                section["video_path"] = f"videos/{Path(all_paths[0]).name}"
            recap_count += 1
            print(f"[RECONCILE] Set recap_video_paths for section {section_id}: {len(all_paths)} videos")
    
    print(f"[RECONCILE] Updated {len(video_map)} sections with video paths, {recap_count} with recap paths, {beat_count} with beat videos")


def process_pdf_to_videos_v12(
    pdf_path: str,
    subject: str = "General Science",
    grade: str = "9",
    output_dir: str = None,
    job_id: str = None,
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    source_file: str = None,
    use_remotion: bool = True
) -> dict:
    """Process PDF through v1.3 3-phase pipeline (Parse → Direct → Render).
    
    v1.3 CHANGE: use_remotion defaults to True. Director decides renderer.
    """
    from core.job_manager import job_manager
    
    output_dir = output_dir or str(PLAYER_ASSETS_DIR)
    videos_dir = Path(output_dir) / "videos"
    audio_dir = Path(output_dir) / "audio"
    images_dir = Path(output_dir) / "images"
    
    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    
    trace_logger = init_traceability(job_id or "pdf_job_v12", output_dir)
    log_event("pipeline_start", {
        "pipeline_version": "1.2",
        "pipeline_type": "pdf",
        "source_file": source_file,
        "subject": subject,
        "grade": grade,
        "dry_run": dry_run,
        "skip_wan": skip_wan
    })
    
    clear_render_trace(output_dir)
    
    job_status = {
        "status": "processing",
        "pipeline_version": "1.2",
        "started_at": datetime.now().isoformat(),
        "source_file": source_file,
        "steps": []
    }
    
    try:
        if job_id:
            job_manager.set_step(job_id, "Converting PDF to text...", 0, phase_key="chunker")
        
        job_status["steps"].append({"step": "pdf_to_markdown", "status": "started"})
        markdown_content = pdf_to_markdown(pdf_path)
        job_status["steps"][-1]["status"] = "completed"
        
        images_mapping = {}
        images_list_text = ""
        try:
            images_mapping = extract_images_from_markdown(markdown_content, str(images_dir))
            images_list_text = create_image_list_for_llm(images_mapping)
            markdown_for_llm = strip_base64_from_markdown(markdown_content)
            job_status["steps"].append({"step": "extract_images", "status": "completed", "count": len(images_mapping)})
        except Exception as e:
            print(f"[Pipeline v1.2] Image extraction failed: {e}")
            markdown_for_llm = markdown_content
            job_status["steps"].append({"step": "extract_images", "status": "failed", "error": str(e)})
        
        if job_id:
            job_manager.complete_step(job_id, 0)
            job_manager.set_step(job_id, "LLM generating presentation (V1.4 Split Directors)...", 1, phase_key="director")
        
        job_status["steps"].append({"step": "generate_presentation_v14_hybrid", "status": "started"})
        
        llm_content = markdown_for_llm
        if images_list_text:
            llm_content = f"{images_list_text}\n\n---\n\n{markdown_for_llm}"
        
        def hybrid_status_callback(phase: str, message: str):
            """Wire hybrid pipeline status to job manager."""
            if job_id:
                job_manager.update_job(job_id, {
                    "current_phase_key": phase,
                    "status_message": message
                }, persist=True)
        
        presentation, analytics_tracker = generate_presentation_v14_hybrid(
            markdown_content=llm_content,
            subject=subject,
            grade=grade,
            use_remotion=use_remotion,
            status_callback=hybrid_status_callback
        )
        
        if presentation and images_mapping:
            presentation["images_mapping"] = {k: v for k, v in images_mapping.items()}
        
        presentation["use_remotion"] = use_remotion
        job_status["steps"][-1]["status"] = "completed"
        job_status["steps"][-1]["analytics"] = analytics_tracker.get_summary()
        
        if presentation:
            print("[Pipeline v1.2 PDF] Normalizing Director output to v1.3 schema...")
            presentation = normalize_director_output(presentation)
        
        presentation_path = Path(output_dir) / "presentation.json"
        if presentation:
            presentation["source_file"] = source_file
            with open(presentation_path, "w") as f:
                json.dump(presentation, f, indent=2)
        
        analytics_path = Path(output_dir) / "analytics.json"
        analytics_tracker.save_to_file(str(analytics_path))
        
        if presentation:
            print("[Pipeline v1.3] Running JSON Schema validation FIRST...")
            schema_valid, schema_errors = validate_schema(presentation)
            if not schema_valid:
                log_validation("schema_validation", None, False, schema_errors[:10], [])
                job_status["steps"].append({
                    "step": "schema_validation",
                    "status": "failed",
                    "errors": schema_errors[:20]
                })
                complete_trace("schema_fail")
                raise PipelineError(
                    f"SCHEMA FAIL: {len(schema_errors)} schema violations. No fallbacks allowed.",
                    "schema_validation",
                    {"schema_errors": schema_errors}
                )
            else:
                log_validation("schema_validation", None, True, [], [])
                job_status["steps"].append({"step": "schema_validation", "status": "passed"})
                print("[Pipeline v1.3] Schema validation PASSED")
            
            print("[Pipeline v1.3] Running 3-tier validation...")
            validation_result = validate_3tier(presentation)
            
            if validation_result.structural_errors:
                for err in validation_result.structural_errors:
                    log_hard_fail(err.code, err.section_id, err.details)
                    log_validation("tier1_structural", err.section_id, False, [str(err)], [])
                job_status["steps"].append({
                    "step": "tier1_structural_validation",
                    "status": "failed",
                    "errors": [str(e) for e in validation_result.structural_errors]
                })
                complete_trace("structural_fail")
                raise PipelineError(
                    f"STRUCTURAL FAIL: {len(validation_result.structural_errors)} tier-1 errors",
                    "tier1_validation",
                    {"structural_errors": [str(e) for e in validation_result.structural_errors]}
                )
            else:
                job_status["steps"].append({"step": "tier1_structural_validation", "status": "passed"})
                print("[Pipeline v1.3] Tier-1 Structural validation PASSED")
            
            if validation_result.semantic_errors:
                for err in validation_result.semantic_errors:
                    log_validation("tier2_semantic", err.section_id, False, [str(err)], [])
                job_status["steps"].append({
                    "step": "tier2_semantic_validation",
                    "status": "failed",
                    "errors": [str(e) for e in validation_result.semantic_errors]
                })
                complete_trace("semantic_fail")
                raise PipelineError(
                    f"SEMANTIC FAIL: {len(validation_result.semantic_errors)} tier-2 errors",
                    "tier2_validation",
                    {"semantic_errors": [str(e) for e in validation_result.semantic_errors]}
                )
            else:
                job_status["steps"].append({"step": "tier2_semantic_validation", "status": "passed"})
                print("[Pipeline v1.3] Tier-2 Semantic validation PASSED")
            
            if validation_result.quality_warnings:
                job_status["steps"].append({
                    "step": "tier3_quality_lint",
                    "status": "passed",
                    "warnings": [str(w) for w in validation_result.quality_warnings[:10]]
                })
                print(f"[Pipeline v1.3] Tier-3 Quality: {len(validation_result.quality_warnings)} warnings (non-blocking)")
            else:
                job_status["steps"].append({"step": "tier3_quality_lint", "status": "passed", "warnings": []})
                print("[Pipeline v1.3] Tier-3 Quality: No warnings")
        
        if job_id:
            job_manager.complete_step(job_id, 1)
            job_manager.set_step(job_id, "Rendering videos with AI...", 2, phase_key="video_renderer")
        
        log_event("render_start", {"dry_run": dry_run, "skip_wan": skip_wan})
        
        if presentation:
            presentation["skip_avatar"] = skip_avatar
            presentation = enforce_renderer_policy(presentation)
        
        job_status["steps"].append({"step": "render_videos", "status": "started"})
        rendered_videos = render_all_topics(presentation, str(videos_dir), dry_run=dry_run, skip_wan=skip_wan, output_dir_base=output_dir)
        
        _reconcile_video_paths(presentation, rendered_videos)
        
        with open(presentation_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        success_count = sum(1 for v in rendered_videos if v.get("status") in ("success", "skipped"))
        fail_count = sum(1 for v in rendered_videos if v.get("status") not in ("success", "skipped"))
        
        job_status["steps"][-1]["status"] = "completed" if fail_count == 0 else "partial"
        job_status["steps"][-1]["videos"] = rendered_videos
        job_status["steps"][-1]["success_count"] = success_count
        job_status["steps"][-1]["fail_count"] = fail_count
        job_status["steps"][-1]["dry_run"] = dry_run
        
        if job_id:
            job_manager.complete_step(job_id, 2)
        
        if dry_run:
            job_status["steps"].append({"step": "generate_audio", "status": "skipped", "reason": "dry_run"})
            audio_files = []
        else:
            if job_id:
                job_manager.set_step(job_id, "Generating audio narration...", 3, phase_key="audio")
            job_status["steps"].append({"step": "generate_audio", "status": "started"})
            audio_files = generate_all_audio(presentation, str(audio_dir))
            
            # ISS-074 FIX: Sync timing with actual TTS durations
            presentation = sync_timing_with_audio(presentation, audio_files)
            
            # Re-save presentation with updated timings
            with open(presentation_path, 'w') as f:
                json.dump(presentation, f, indent=2)
            print(f"[TIMING SYNC] Updated presentation saved with synchronized timings")
            
            job_status["steps"][-1]["status"] = "completed"
            job_status["steps"][-1]["audio_files"] = audio_files
            if job_id:
                job_manager.complete_step(job_id, 3)
        
        job_status["status"] = "completed"
        job_status["completed_at"] = datetime.now().isoformat()
        job_status["presentation_path"] = str(presentation_path)
        job_status["analytics_path"] = str(analytics_path)
        job_status["sections_count"] = len(presentation.get("sections", []))
        job_status["total_cost_usd"] = analytics_tracker.analytics.total_cost_usd
        job_status["dry_run"] = dry_run
        
        save_render_prompts_json()
        complete_trace("completed")
        log_event("pipeline_complete", {"status": "success", "pipeline_version": "1.2"})
        
    except Exception as e:
        job_status["status"] = "failed"
        job_status["error"] = str(e)
        job_status["failed_at"] = datetime.now().isoformat()
        complete_trace("failed")
        raise
    
    return job_status


def process_markdown_to_videos_v12(
    markdown_content: str,
    subject: str = "General Science",
    grade: str = "9",
    output_dir: str = None,
    job_id: str = None,
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    source_file: str = None,
    use_remotion: bool = True
) -> dict:
    """Process Markdown through v1.3 3-phase pipeline (Parse → Direct → Render).
    
    v1.3 CHANGE: use_remotion defaults to True. Director decides renderer.
    """
    from core.job_manager import job_manager
    
    output_dir = output_dir or str(PLAYER_ASSETS_DIR)
    videos_dir = Path(output_dir) / "videos"
    audio_dir = Path(output_dir) / "audio"
    images_dir = Path(output_dir) / "images"
    
    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    
    trace_logger = init_traceability(job_id or "md_job_v12", output_dir)
    log_event("pipeline_start", {
        "pipeline_version": "1.2",
        "pipeline_type": "markdown",
        "source_file": source_file,
        "subject": subject,
        "grade": grade,
        "dry_run": dry_run,
        "skip_wan": skip_wan
    })
    
    clear_render_trace(output_dir)
    
    job_status = {
        "status": "processing",
        "pipeline_version": "1.2",
        "started_at": datetime.now().isoformat(),
        "source_file": source_file,
        "steps": []
    }
    
    try:
        images_mapping = {}
        images_list_text = ""
        try:
            images_mapping = extract_images_from_markdown(markdown_content, str(images_dir))
            images_list_text = create_image_list_for_llm(images_mapping)
            markdown_for_llm = strip_base64_from_markdown(markdown_content)
            job_status["steps"].append({"step": "extract_images", "status": "completed", "count": len(images_mapping)})
        except Exception as e:
            print(f"[Pipeline v1.2] Image extraction failed: {e}")
            markdown_for_llm = markdown_content
            job_status["steps"].append({"step": "extract_images", "status": "failed", "error": str(e)})
        
        if job_id:
            job_manager.set_step(job_id, "LLM generating presentation (V1.4 Split Directors)...", 0, phase_key="director")
        
        job_status["steps"].append({"step": "generate_presentation_v14_hybrid", "status": "started"})
        
        llm_content = markdown_for_llm
        if images_list_text:
            llm_content = f"{images_list_text}\n\n---\n\n{markdown_for_llm}"
        
        def hybrid_status_callback(phase: str, message: str):
            """Wire hybrid pipeline status to job manager."""
            if job_id:
                job_manager.update_job(job_id, {
                    "current_phase_key": phase,
                    "status_message": message
                }, persist=True)
        
        presentation, analytics_tracker = generate_presentation_v14_hybrid(
            markdown_content=llm_content,
            subject=subject,
            grade=grade,
            use_remotion=use_remotion,
            status_callback=hybrid_status_callback
        )
        
        if presentation and images_mapping:
            presentation["images_mapping"] = {k: v for k, v in images_mapping.items()}
        
        presentation["use_remotion"] = use_remotion
        job_status["steps"][-1]["status"] = "completed"
        job_status["steps"][-1]["analytics"] = analytics_tracker.get_summary()
        
        if presentation:
            print("[Pipeline v1.2 MD] Normalizing Director output to v1.3 schema...")
            presentation = normalize_director_output(presentation)
        
        presentation_path = Path(output_dir) / "presentation.json"
        if presentation:
            presentation["source_file"] = source_file
            with open(presentation_path, "w") as f:
                json.dump(presentation, f, indent=2)
        
        analytics_path = Path(output_dir) / "analytics.json"
        analytics_tracker.save_to_file(str(analytics_path))
        
        print("[Pipeline v1.3] Validation already done in Director pass (3-tier with retries)")
        job_status["steps"].append({"step": "validation", "status": "passed", "note": "Handled in Director with retries"})
        
        if job_id:
            job_manager.complete_step(job_id, 0)
            job_manager.set_step(job_id, "Rendering videos with AI...", 1, phase_key="video_renderer")
        
        log_event("render_start", {"dry_run": dry_run, "skip_wan": skip_wan})
        
        if presentation:
            presentation["skip_avatar"] = skip_avatar
            presentation = enforce_renderer_policy(presentation)
        
        job_status["steps"].append({"step": "render_videos", "status": "started"})
        rendered_videos = render_all_topics(presentation, str(videos_dir), dry_run=dry_run, skip_wan=skip_wan, output_dir_base=output_dir)
        
        _reconcile_video_paths(presentation, rendered_videos)
        
        with open(presentation_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        success_count = sum(1 for v in rendered_videos if v.get("status") in ("success", "skipped"))
        fail_count = sum(1 for v in rendered_videos if v.get("status") not in ("success", "skipped"))
        
        job_status["steps"][-1]["status"] = "completed" if fail_count == 0 else "partial"
        job_status["steps"][-1]["videos"] = rendered_videos
        job_status["steps"][-1]["success_count"] = success_count
        job_status["steps"][-1]["fail_count"] = fail_count
        job_status["steps"][-1]["dry_run"] = dry_run
        
        if job_id:
            job_manager.complete_step(job_id, 1)
        
        if dry_run:
            job_status["steps"].append({"step": "generate_audio", "status": "skipped", "reason": "dry_run"})
            audio_files = []
        else:
            if job_id:
                job_manager.set_step(job_id, "Generating audio narration...", 2, phase_key="audio")
            job_status["steps"].append({"step": "generate_audio", "status": "started"})
            audio_files = generate_all_audio(presentation, str(audio_dir))
            
            # ISS-074 FIX: Sync timing with actual TTS durations
            presentation = sync_timing_with_audio(presentation, audio_files)
            with open(presentation_path, 'w') as f:
                json.dump(presentation, f, indent=2)
            
            job_status["steps"][-1]["status"] = "completed"
            job_status["steps"][-1]["audio_files"] = audio_files
            if job_id:
                job_manager.complete_step(job_id, 2)
        
        job_status["status"] = "completed"
        job_status["completed_at"] = datetime.now().isoformat()
        job_status["presentation_path"] = str(presentation_path)
        job_status["analytics_path"] = str(analytics_path)
        job_status["sections_count"] = len(presentation.get("sections", []))
        job_status["total_cost_usd"] = analytics_tracker.analytics.total_cost_usd
        job_status["dry_run"] = dry_run
        
        save_render_prompts_json()
        complete_trace("completed")
        log_event("pipeline_complete", {"status": "success", "pipeline_version": "1.2"})
        
    except Exception as e:
        job_status["status"] = "failed"
        job_status["error"] = str(e)
        job_status["failed_at"] = datetime.now().isoformat()
        complete_trace("failed")
        raise
    
    return job_status


def detect_job_phase(job_dir: str) -> dict:
    """
    Detect which phases completed for a job based on artifacts.
    
    Returns dict with phase completion status:
    - presentation: True if presentation.json exists and is valid
    - videos: True if videos/ has content
    - audio: True if audio/ has mp3 files
    """
    job_path = Path(job_dir)
    
    phases = {
        "presentation": False,
        "videos": False, 
        "audio": False,
        "presentation_path": None,
        "video_count": 0,
        "audio_count": 0
    }
    
    presentation_path = job_path / "presentation.json"
    if presentation_path.exists():
        try:
            with open(presentation_path) as f:
                data = json.load(f)
            if data.get("sections"):
                phases["presentation"] = True
                phases["presentation_path"] = str(presentation_path)
        except (json.JSONDecodeError, IOError):
            pass
    
    videos_dir = job_path / "videos"
    if videos_dir.exists():
        video_files = list(videos_dir.glob("*.mp4"))
        phases["video_count"] = len(video_files)
        phases["videos"] = len(video_files) > 0
    
    audio_dir = job_path / "audio"
    if audio_dir.exists():
        audio_files = list(audio_dir.glob("*.mp3"))
        phases["audio_count"] = len(audio_files)
        phases["audio"] = len(audio_files) > 0
    
    return phases


def resume_job_from_phase(
    job_id: str,
    from_phase: str = "audio",
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False
) -> dict:
    """
    Resume a failed job from a specific phase.
    
    Phases:
    - "render": Re-run video rendering + audio
    - "audio": Re-run audio generation only
    
    Requires presentation.json to exist.
    """
    from core.job_manager import JobManager
    
    job_manager = JobManager()
    job_dir = Path("player/jobs") / job_id
    
    if not job_dir.exists():
        raise ValueError(f"Job directory not found: {job_dir}")
    
    phases = detect_job_phase(str(job_dir))
    
    if not phases["presentation"]:
        raise ValueError(f"Cannot resume - presentation.json missing or invalid for job {job_id}")
    
    presentation_path = Path(phases["presentation_path"])
    with open(presentation_path) as f:
        presentation = json.load(f)
    
    print(f"[Resume] Job {job_id}: Loaded presentation with {len(presentation.get('sections', []))} sections")
    print(f"[Resume] Phase status: presentation={phases['presentation']}, videos={phases['videos']}, audio={phases['audio']}")
    print(f"[Resume] Resuming from phase: {from_phase}")
    
    job_status = {
        "status": "resumed",
        "job_id": job_id,
        "resumed_from": from_phase,
        "resumed_at": datetime.now().isoformat(),
        "steps": []
    }
    
    videos_dir = job_dir / "videos"
    audio_dir = job_dir / "audio"
    videos_dir.mkdir(exist_ok=True)
    audio_dir.mkdir(exist_ok=True)
    
    try:
        if from_phase == "render":
            print(f"[Resume] Re-running video rendering...")
            job_status["steps"].append({"step": "render_videos", "status": "started"})
            
            presentation["skip_avatar"] = skip_avatar
            presentation = enforce_renderer_policy(presentation)
            
            rendered_videos = render_all_topics(
                presentation, 
                str(videos_dir), 
                dry_run=dry_run, 
                skip_wan=skip_wan,
                output_dir_base=str(job_dir)
            )
            
            _reconcile_video_paths(presentation, rendered_videos)
            
            with open(presentation_path, "w") as f:
                json.dump(presentation, f, indent=2)
            
            success_count = sum(1 for v in rendered_videos if v.get("status") in ("success", "skipped"))
            fail_count = sum(1 for v in rendered_videos if v.get("status") not in ("success", "skipped"))
            
            job_status["steps"][-1]["status"] = "completed" if fail_count == 0 else "partial"
            job_status["steps"][-1]["videos"] = rendered_videos
            job_status["steps"][-1]["success_count"] = success_count
            job_status["steps"][-1]["fail_count"] = fail_count
        
        if from_phase in ["render", "audio"]:
            if dry_run:
                job_status["steps"].append({"step": "generate_audio", "status": "skipped", "reason": "dry_run"})
                audio_files = []
            else:
                print(f"[Resume] Generating audio narration...")
                job_status["steps"].append({"step": "generate_audio", "status": "started"})
                audio_files = generate_all_audio(presentation, str(audio_dir))
                
                # ISS-074 FIX: Sync timing with actual TTS durations
                presentation = sync_timing_with_audio(presentation, audio_files)
                with open(presentation_path, 'w') as f:
                    json.dump(presentation, f, indent=2)
                
                job_status["steps"][-1]["status"] = "completed"
                job_status["steps"][-1]["audio_files"] = audio_files
                job_status["steps"][-1]["audio_count"] = len(audio_files)
        
        job_status["status"] = "completed"
        job_status["completed_at"] = datetime.now().isoformat()
        
        job_manager.update_job(job_id, {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "error": None,
            "progress": 100,
            "steps_completed": 3,
            "current_step_name": "Completed"
        }, persist=True)
        
        print(f"[Resume] Job {job_id} completed successfully!")
        
    except Exception as e:
        job_status["status"] = "failed"
        job_status["error"] = str(e)
        job_status["failed_at"] = datetime.now().isoformat()
        
        job_manager.update_job(job_id, {
            "status": "failed",
            "error": str(e)
        }, persist=True)
        
        raise
    
    return job_status



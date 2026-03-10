import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Union

from core.datalab_client import pdf_to_markdown
from core.llm_client import generate_chunked_presentation, ValidationError
from core.renderer_executor import render_all_topics, enforce_renderer_policy
from core.image_processor import extract_images_from_markdown, strip_base64_from_markdown, create_image_list_for_llm
from core.hard_fail_validator import validate_presentation_hard_fails, format_hard_fail_report, HardFailError
from core.traceability import init_traceability, log_event, log_validation, log_hard_fail, complete_trace
from tts.generate_audio import generate_all_audio
from render.render_trace import clear_render_trace

PLAYER_ASSETS_DIR = Path(__file__).parent.parent / "player" / "assets"


def process_pdf_to_videos(
    pdf_path: str,
    subject: str = "General Science",
    grade: str = "9",
    output_dir: str = None,
    job_id: str = None,
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    source_file: str = None
) -> dict:
    from core.job_manager import job_manager
    
    output_dir = output_dir or str(PLAYER_ASSETS_DIR)
    videos_dir = Path(output_dir) / "videos"
    audio_dir = Path(output_dir) / "audio"
    images_dir = Path(output_dir) / "images"
    
    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    
    trace_logger = init_traceability(job_id or "pdf_job", output_dir)
    log_event("pipeline_start", {
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
        "started_at": datetime.now().isoformat(),
        "source_file": source_file,
        "steps": []
    }
    
    try:
        if job_id:
            job_manager.set_step(job_id, "Converting PDF to text...", 0)
        
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
            print(f"[Pipeline] Image extraction failed: {e}")
            markdown_for_llm = markdown_content
            job_status["steps"].append({"step": "extract_images", "status": "failed", "error": str(e)})
        
        if job_id:
            job_manager.complete_step(job_id, 0)
            job_manager.set_step(job_id, "LLM generating presentation plan...", 1)
        
        job_status["steps"].append({"step": "generate_presentation_plan", "status": "started"})
        
        presentation = None
        generation_trace = None
        validation_failed = False
        validation_error_msg = None
        
        try:
            llm_content = markdown_for_llm
            if images_list_text:
                llm_content = f"{images_list_text}\n\n---\n\n{markdown_for_llm}"
            
            presentation, generation_trace = generate_chunked_presentation(
                markdown_content=llm_content,
                subject=subject,
                grade=grade
            )
            
            if presentation and images_mapping:
                presentation["images_mapping"] = {k: v for k, v in images_mapping.items()}
            
            job_status["steps"][-1]["status"] = "completed"
        except ValidationError as ve:
            validation_failed = True
            validation_error_msg = str(ve)
            presentation = ve.presentation
            generation_trace = ve.trace
            job_status["steps"][-1]["status"] = "validation_failed"
            job_status["steps"][-1]["validation_errors"] = validation_error_msg
        
        presentation_path = Path(output_dir) / "presentation.json"
        if presentation:
            presentation["source_file"] = source_file
            with open(presentation_path, "w") as f:
                json.dump(presentation, f, indent=2)
        
        trace_path = Path(output_dir) / "generation_trace.json"
        if generation_trace:
            with open(trace_path, "w") as f:
                json.dump(generation_trace, f, indent=2)
        
        if validation_failed:
            raise ValidationError(validation_error_msg or "Validation failed", presentation, generation_trace)
        
        if presentation:
            is_valid, hard_fails = validate_presentation_hard_fails(presentation)
            if not is_valid:
                for hf in hard_fails:
                    log_hard_fail(hf.condition, hf.section_id, hf.details)
                    log_validation("hard_fail_check", hf.section_id, False, 
                                  [str(hf)], [])
                report = format_hard_fail_report(hard_fails)
                print(report)
                job_status["steps"].append({
                    "step": "hard_fail_validation",
                    "status": "failed",
                    "errors": [str(hf) for hf in hard_fails]
                })
                complete_trace("hard_fail")
                raise ValidationError(
                    f"HARD FAIL: {len(hard_fails)} validation failures - generation aborted. " + 
                    "; ".join([str(hf) for hf in hard_fails[:3]]),
                    presentation, generation_trace
                )
            else:
                log_validation("hard_fail_check", None, True, [], [])
                job_status["steps"].append({
                    "step": "hard_fail_validation",
                    "status": "passed"
                })
        
        if job_id:
            job_manager.complete_step(job_id, 1)
            job_manager.set_step(job_id, "Rendering videos with AI...", 2)
        
        log_event("render_start", {"dry_run": dry_run, "skip_wan": skip_wan})
        
        if presentation:
            presentation["skip_avatar"] = skip_avatar
            presentation = enforce_renderer_policy(presentation)
        
        job_status["steps"].append({"step": "render_videos", "status": "started"})
        rendered_videos = render_all_topics(presentation, str(videos_dir), dry_run=dry_run, skip_wan=skip_wan, output_dir_base=output_dir)
        
        success_count = sum(1 for v in rendered_videos if v.get("status") in ("success", "skipped"))
        fail_count = sum(1 for v in rendered_videos if v.get("status") not in ("success", "skipped"))
        
        job_status["steps"][-1]["status"] = "completed" if fail_count == 0 else "partial"
        job_status["steps"][-1]["videos"] = rendered_videos
        job_status["steps"][-1]["success_count"] = success_count
        job_status["steps"][-1]["fail_count"] = fail_count
        job_status["steps"][-1]["dry_run"] = dry_run
        
        if job_id:
            job_manager.complete_step(job_id, 2)
        
        # Skip audio generation in dry_run mode
        if dry_run:
            job_status["steps"].append({"step": "generate_audio", "status": "skipped", "reason": "dry_run"})
            audio_files = []
        else:
            if job_id:
                job_manager.set_step(job_id, "Generating audio narration...", 3)
            job_status["steps"].append({"step": "generate_audio", "status": "started"})
            audio_files = generate_all_audio(presentation, str(audio_dir))
            job_status["steps"][-1]["status"] = "completed"
            job_status["steps"][-1]["audio_files"] = audio_files
            if job_id:
                job_manager.complete_step(job_id, 3)
        
        job_status["status"] = "completed"
        job_status["completed_at"] = datetime.now().isoformat()
        job_status["presentation_path"] = str(presentation_path)
        job_status["trace_path"] = str(trace_path)
        job_status["sections_count"] = len(presentation.get("sections", []))
        job_status["dry_run"] = dry_run
        
        complete_trace("completed")
        log_event("pipeline_complete", {"status": "success"})
        
    except Exception as e:
        job_status["status"] = "failed"
        job_status["error"] = str(e)
        job_status["failed_at"] = datetime.now().isoformat()
        complete_trace("failed")
        raise
    
    return job_status


def process_markdown_to_videos(
    markdown_content: str,
    subject: str = "General Science",
    grade: str = "9",
    output_dir: str = None,
    job_id: str = None,
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    source_file: str = None
) -> dict:
    from core.job_manager import job_manager
    
    output_dir = output_dir or str(PLAYER_ASSETS_DIR)
    videos_dir = Path(output_dir) / "videos"
    audio_dir = Path(output_dir) / "audio"
    images_dir = Path(output_dir) / "images"
    
    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    
    trace_logger = init_traceability(job_id or "md_job", output_dir)
    log_event("pipeline_start", {
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
            print(f"[Pipeline] Image extraction failed: {e}")
            markdown_for_llm = markdown_content
            job_status["steps"].append({"step": "extract_images", "status": "failed", "error": str(e)})
        
        if job_id:
            job_manager.set_step(job_id, "LLM generating presentation plan...", 0)
        
        job_status["steps"].append({"step": "generate_presentation_plan", "status": "started"})
        
        presentation = None
        generation_trace = None
        validation_failed = False
        validation_error_msg = None
        
        try:
            llm_content = markdown_for_llm
            if images_list_text:
                llm_content = f"{images_list_text}\n\n---\n\n{markdown_for_llm}"
            
            presentation, generation_trace = generate_chunked_presentation(
                markdown_content=llm_content,
                subject=subject,
                grade=grade
            )
            
            if presentation and images_mapping:
                presentation["images_mapping"] = {k: v for k, v in images_mapping.items()}
            
            job_status["steps"][-1]["status"] = "completed"
        except ValidationError as ve:
            validation_failed = True
            validation_error_msg = str(ve)
            presentation = ve.presentation
            generation_trace = ve.trace
            job_status["steps"][-1]["status"] = "validation_failed"
            job_status["steps"][-1]["validation_errors"] = validation_error_msg
        
        presentation_path = Path(output_dir) / "presentation.json"
        if presentation:
            presentation["source_file"] = source_file
            with open(presentation_path, "w") as f:
                json.dump(presentation, f, indent=2)
        
        trace_path = Path(output_dir) / "generation_trace.json"
        if generation_trace:
            with open(trace_path, "w") as f:
                json.dump(generation_trace, f, indent=2)
        
        if validation_failed:
            raise ValidationError(validation_error_msg or "Validation failed", presentation, generation_trace)
        
        if presentation:
            is_valid, hard_fails = validate_presentation_hard_fails(presentation)
            if not is_valid:
                for hf in hard_fails:
                    log_hard_fail(hf.condition, hf.section_id, hf.details)
                    log_validation("hard_fail_check", hf.section_id, False, 
                                  [str(hf)], [])
                report = format_hard_fail_report(hard_fails)
                print(report)
                job_status["steps"].append({
                    "step": "hard_fail_validation",
                    "status": "failed",
                    "errors": [str(hf) for hf in hard_fails]
                })
                complete_trace("hard_fail")
                raise ValidationError(
                    f"HARD FAIL: {len(hard_fails)} validation failures - generation aborted. " + 
                    "; ".join([str(hf) for hf in hard_fails[:3]]),
                    presentation, generation_trace
                )
            else:
                log_validation("hard_fail_check", None, True, [], [])
                job_status["steps"].append({
                    "step": "hard_fail_validation",
                    "status": "passed"
                })
        
        if job_id:
            job_manager.complete_step(job_id, 0)
            job_manager.set_step(job_id, "Rendering videos with AI...", 1)
        
        log_event("render_start", {"dry_run": dry_run, "skip_wan": skip_wan})
        
        if presentation:
            presentation["skip_avatar"] = skip_avatar
            presentation = enforce_renderer_policy(presentation)
        
        job_status["steps"].append({"step": "render_videos", "status": "started"})
        rendered_videos = render_all_topics(presentation, str(videos_dir), dry_run=dry_run, skip_wan=skip_wan, output_dir_base=output_dir)
        
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
                job_manager.set_step(job_id, "Generating audio narration...", 2)
            job_status["steps"].append({"step": "generate_audio", "status": "started"})
            audio_files = generate_all_audio(presentation, str(audio_dir))
            job_status["steps"][-1]["status"] = "completed"
            job_status["steps"][-1]["audio_files"] = audio_files
            if job_id:
                job_manager.complete_step(job_id, 2)
        
        job_status["status"] = "completed"
        job_status["completed_at"] = datetime.now().isoformat()
        job_status["presentation_path"] = str(presentation_path)
        job_status["trace_path"] = str(trace_path)
        job_status["sections_count"] = len(presentation.get("sections", []))
        job_status["dry_run"] = dry_run
        
        complete_trace("completed")
        log_event("pipeline_complete", {"status": "success"})
        
    except Exception as e:
        job_status["status"] = "failed"
        job_status["error"] = str(e)
        job_status["failed_at"] = datetime.now().isoformat()
        complete_trace("failed")
        raise
    
    return job_status

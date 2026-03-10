import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from threading import Thread
from dotenv import load_dotenv

# Load environment variables from .env file
# Load environment variables from .env file (Force override to ensure correct key)
load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS

from core.pipeline import process_pdf_to_videos
from core.pipeline_v12 import process_markdown_to_videos_v12 as process_markdown_to_videos
from core.pipeline_v14 import get_pipeline_info, process_markdown_to_presentation_v14, process_with_renderers_v14, validate_presentation_v14
from core.pipeline_v15 import process_markdown_to_presentation_v15, resume_from_section, PipelineError as PipelineV15Error
from core.pipeline_v15_optimized import process_markdown_optimized
from core.unified_content_generator import generate_presentation, transform_to_player_schema, GeneratorConfig
from core.job_manager import job_manager, run_job_async, is_job_running, get_current_job_ids

app = Flask(__name__)
CORS(app)

# SILENCE POLLING LOGS: Prevent console flood from status calls
import logging
class PollingLogFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        # Silence /avatar_status and /status calls
        if "avatar_status" in msg or "/status" in msg:
            return False
        return True

# Apply to werkzeug and root loggers to be sure
logging.getLogger("werkzeug").setLevel(logging.ERROR)
logging.getLogger("werkzeug").addFilter(PollingLogFilter())
logging.getLogger("flask.app").addFilter(PollingLogFilter())

PLAYER_DIR = Path(__file__).parent.parent / "player"
ASSETS_DIR = PLAYER_DIR / "assets"
JOBS_DIR = PLAYER_DIR / "jobs"
TEMP_DIR = Path(tempfile.gettempdir()) / "ai_education_jobs"

os.makedirs(ASSETS_DIR / "videos", exist_ok=True)
os.makedirs(ASSETS_DIR / "audio", exist_ok=True)
os.makedirs(JOBS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Track active avatar generation jobs in memory
ACTIVE_AVATAR_JOBS = set()

def setup_job_folder(job_output_dir: Path):
    """Copy player files to job folder for self-contained playback"""
    os.makedirs(job_output_dir / "videos", exist_ok=True)
    os.makedirs(job_output_dir / "audio", exist_ok=True)
    # Copy player_v2 files for self-contained job
    # player_v2.html becomes index.html, player_v2.js and player_v2.css keep their names
    file_mappings = [
        ("player_v2.html", "index.html"),
        ("player_v2.js", "player_v2.js"),
        ("player_v2.css", "player_v2.css")
    ]
    for src_name, dst_name in file_mappings:
        src = PLAYER_DIR / src_name
        dst = job_output_dir / dst_name
        if src.exists() and not dst.exists():
            shutil.copy(str(src), str(dst))

@app.route("/sanity_check.html")
def serve_sanity_check():
    return send_from_directory(PLAYER_DIR, "sanity_check.html")

@app.route("/")
def index():
    return redirect("/dashboard")

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "ai-animated-education-phase1",
        "version": "1.4.0",
        "features": ["job_mode", "pdf", "markdown", "v14_pipeline", "split_director"]
    })


"""
Add this as a NEW endpoint at the end of api/app.py (before if __name__ == '__main__')

This adds a /regenerate_manim/<job_id> endpoint without modifying any existing code.
"""

@app.route('/regenerate_manim/<job_id>', methods=['POST'])
def regenerate_manim(job_id):
    """
    Regenerate Manim code for all manim sections in a job.
    Uses the V2.5 Director data mapping fix.
    """
    from core.agents.manim_code_generator import ManimCodeGenerator, integrate_manim_code_into_section
    
    job_dir = JOBS_DIR / job_id
    pres_path = job_dir / "presentation.json"
    
    if not pres_path.exists():
        return jsonify({"error": "Job not found"}), 404
    
    try:
        # Load presentation
        with open(pres_path, "r", encoding="utf-8") as f:
            presentation = json.load(f)
        
        manim_gen = ManimCodeGenerator()
        sections = presentation.get("sections", [])
        results = {"generated": [], "skipped": [], "failed": []}
        
        for section in sections:
            if section.get("renderer") != "manim":
                continue
            
            section_id = section.get("section_id")
            
            # Transform V2.5 Director data (same as pipeline fix)
            nar = section.get("narration", {})
            segments = nar.get("segments", [])
            
            render_spec = section.get("render_spec", {})
            manim_spec_from_director = render_spec.get("manim_scene_spec")
            if isinstance(manim_spec_from_director, dict):
                manim_spec_from_director = manim_spec_from_director.get("description", "")
            
            section_data = {
                "section_title": section.get("title", "Section"),
                "narration_segments": segments,
                "manim_spec": manim_spec_from_director or section.get("explanation_plan", ""),
                "visual_description": "",
                "formulas": [],
                "key_terms": []
            }
            
            try:
                code = manim_gen.generate_code(section_data, style_config={"style": "standard"})
                
                if not code or len(code) < 100:
                    results["failed"].append({
                        "section_id": section_id,
                        "error": "Generated code too short"
                    })
                    continue
                
                # Save to file
                manim_code_dir = job_dir / "manim_code"
                manim_code_dir.mkdir(exist_ok=True)
                code_file = manim_code_dir / f"section_{section_id}.py"
                
                with open(code_file, "w", encoding="utf-8") as f:
                    f.write(code)
                
                # Update presentation.json
                integrate_manim_code_into_section(section, code)
                
                results["generated"].append({
                    "section_id": section_id,
                    "title": section.get("title"),
                    "code_length": len(code),
                    "segments": len(segments)
                })
                
            except Exception as e:
                results["failed"].append({
                    "section_id": section_id,
                    "error": str(e)
                })
        
        # Save updated presentation
        with open(pres_path, "w", encoding="utf-8") as f:
            json.dump(presentation, f, indent=4)
        
        return jsonify({
            "status": "complete",
            "job_id": job_id,
            "results": results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/submit_job", methods=["POST"])
def submit_job():
    try:
        if False: # is_job_running():
            current_id = get_current_job_ids()
            return jsonify({
                "status": "busy",
                "message": "A job is already running. Please wait for it to complete.",
                "current_job_id": current_id
            }), 409
        
        subject = request.form.get("subject", "General Science")
        grade = request.form.get("grade", "9")
        dry_run = request.form.get("dry_run", "false").lower() == "true"
        skip_wan = request.form.get("skip_wan", "false").lower() == "true"
        skip_avatar = request.form.get("skip_avatar", "false").lower() == "true"
        tts_provider = request.form.get("tts_provider", "edge_tts")
        # FIXED: Default to V2.5 Director Mode for all new jobs
        pipeline_version = request.form.get("pipeline_version", "v15_v2_director")
        generation_scope = request.form.get("generation_scope", "full")
        model = request.form.get("model")
        print(f"=" * 80)
        print(f"[ROUTING DEBUG] Received pipeline_version from form: '{pipeline_version}'")
        print(f"=" * 80)
        
        if "file" in request.files:
            uploaded_file = request.files["file"]
            if uploaded_file.filename == "":
                return jsonify({"error": "No file selected"}), 400
            
            filename = (uploaded_file.filename or "").lower()
            
            # ISS-206: Accept PDF, DOC, DOCX, ODT (all via Datalab) and Markdown
            if filename.endswith(".pdf"):
                job_type = "document"
                suffix = ".pdf"
            elif filename.endswith(".doc"):
                job_type = "document"
                suffix = ".doc"
            elif filename.endswith(".docx"):
                job_type = "document"
                suffix = ".docx"
            elif filename.endswith(".odt"):
                job_type = "document"
                suffix = ".odt"
            elif filename.endswith(".md") or filename.endswith(".markdown") or filename.endswith(".txt"):
                job_type = "markdown_file"
                suffix = ".md"
            else:
                return jsonify({"error": " Unsupported file type. Supported: PDF, DOC, DOCX, ODT, MD"}), 400
            
            temp_file = TEMP_DIR / f"{os.urandom(8).hex()}{suffix}"
            uploaded_file.save(str(temp_file))
            original_filename = uploaded_file.filename
            
            if pipeline_version in ["v15_v2", "v15_v2_director"]:
                job_type_name = "v15_v2_pipeline"
            elif pipeline_version == "v15":
                job_type_name = "v15_pipeline"
            else:
                job_type_name = "v14_pipeline"
            job_id = job_manager.create_job(job_type_name, {
                "subject": subject,
                "grade": grade,
                "file_path": str(temp_file),
                "source_file": original_filename,
                "skip_wan": skip_wan,
                "skip_avatar": skip_avatar,
                "tts_provider": tts_provider,
                "pipeline_version": pipeline_version,
                "generation_scope": generation_scope,
                "model": model
            })
            
            job_output_dir = JOBS_DIR / job_id
            setup_job_folder(job_output_dir)
            
            if job_type == "document":
                # ISS-206: Handle PDF, DOC, DOCX, ODT via Datalab
                if pipeline_version in ["v15_v2", "v15_v2_director"]:
                    document_processor = process_document_job_v15_v2
                elif pipeline_version == "v15":
                    document_processor = process_document_job_v15
                else:
                    document_processor = process_pdf_job
                run_job_async(
                    job_id,
                    document_processor,
                    document_path=str(temp_file),
                    subject=subject,
                    grade=grade,
                    output_dir=str(job_output_dir),
                    dry_run=dry_run,
                    skip_avatar=skip_avatar,
                    source_file=original_filename,
                    tts_provider=tts_provider,
                    pipeline_version=pipeline_version,
                    generation_scope=generation_scope,
                    model=model
                )
            else:
                with open(temp_file, "r", encoding="utf-8") as f:
                    markdown_content = f.read()
                os.unlink(temp_file)
                
                content_preview = markdown_content[:300].replace('\n', ' ').strip()
                if len(markdown_content) > 300:
                    content_preview += "..."
                
                job_manager.update_job(job_id, {"content_preview": content_preview}, persist=True)
                
                if pipeline_version in ["v15_v2", "v15_v2_director"]:
                    job_processor = process_markdown_job_v15_v2
                    print(f"[ROUTING DEBUG] Selected processor: process_markdown_job_v15_v2")
                elif pipeline_version == "v15":
                    job_processor = process_markdown_job_v15
                    print(f"[ROUTING DEBUG] Selected processor: process_markdown_job_v15")
                else:
                    job_processor = process_markdown_job
                    print(f"[ROUTING DEBUG] Selected processor: process_markdown_job (legacy)")
                print(f"[ROUTING DEBUG] Calling {job_processor.__name__} with pipeline_version='{pipeline_version}'")
                run_job_async(
                    job_id,
                    job_processor,
                    markdown_content=markdown_content,
                    subject=subject,
                    grade=grade,
                    output_dir=str(job_output_dir),
                    dry_run=dry_run,
                    skip_wan=skip_wan,
                    skip_avatar=skip_avatar,
                    source_file=original_filename,
                    tts_provider=tts_provider,
                    pipeline_version=pipeline_version,
                    generation_scope=generation_scope,
                    model=model
                )
        
        elif request.is_json:
            data = request.json
            markdown_content = data.get("markdown", "")
            subject = data.get("subject", subject)
            grade = data.get("grade", grade)
            dry_run = data.get("dry_run", False)
            skip_wan = data.get("skip_wan", False)
            skip_avatar = data.get("skip_avatar", False)
            tts_provider = data.get("tts_provider", "edge_tts")
            # FIXED: Default to V2.5 Director Mode for all new jobs
            pipeline_version = data.get("pipeline_version", "v15_v2_director")
            generation_scope = data.get("generation_scope", "full")
            model = data.get("model")
            
            if not markdown_content:
                return jsonify({"error": "Markdown content is required"}), 400
            
            content_preview = markdown_content[:300].replace('\n', ' ').strip()
            if len(markdown_content) > 300:
                content_preview += "..."
            
            if pipeline_version == "v15_v2":
                job_type_name = "v15_v2_pipeline"
            elif pipeline_version == "v15":
                job_type_name = "v15_pipeline"
            else:
                job_type_name = "v14_pipeline"
            job_id = job_manager.create_job(job_type_name, {
                "subject": subject,
                "grade": grade,
                "dry_run": dry_run,
                "skip_wan": skip_wan,
                "skip_avatar": skip_avatar,
                "tts_provider": tts_provider,
                "pipeline_version": pipeline_version,
                "generation_scope": generation_scope,
                "model": model,
                "content_preview": content_preview
            })
            
            job_output_dir = JOBS_DIR / job_id
            setup_job_folder(job_output_dir)
            
            if pipeline_version in ["v15_v2", "v15_v2_director"]:
                job_processor = process_markdown_job_v15_v2
            elif pipeline_version == "v15":
                job_processor = process_markdown_job_v15
            else:
                job_processor = process_markdown_job
            run_job_async(
                job_id,
                job_processor,
                markdown_content=markdown_content,
                subject=subject,
                grade=grade,
                output_dir=str(job_output_dir),
                dry_run=dry_run,
                skip_wan=skip_wan,
                skip_avatar=skip_avatar,
                tts_provider=tts_provider,
                pipeline_version=pipeline_version,
                generation_scope=generation_scope,
                model=model
            )
        
        else:
            return jsonify({"error": "Please provide a file or markdown content"}), 400
        
        mode_msg = " (DRY RUN - prompts only, no real rendering)" if dry_run else ""
        job_data = job_manager.get_job(job_id)
        content_preview = None
        if job_data:
            content_preview = job_data.get("content_preview") or job_data.get("params", {}).get("content_preview")
        
        return jsonify({
            "status": "accepted",
            "job_id": job_id,
            "dry_run": dry_run,
            "skip_wan": skip_wan,
            "skip_avatar": skip_avatar,
            "content_preview": content_preview,
            "message": f"Job submitted successfully{mode_msg}. Poll /job/<job_id>/status for progress."
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route("/job/<job_id>/status", methods=["GET"])
def get_job_status(job_id):
    job = job_manager.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    response = {
        "job_id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "current_step": job["current_step_name"],
        "current_phase": job.get("current_phase_key"),
        "status_message": job.get("status_message"),
        "steps_completed": job["steps_completed"],
        "total_steps": job["total_steps"],
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "completed_at": job["completed_at"],
        "error": job["error"]
    }
    
    if job["status"] == "failed":
        response["failure_message"] = job.get("failure_message")
        response["failed_phase"] = job.get("failed_phase")
    
    # ISS-Analytics: Inject live progress details from analytics.json if available
    job_folder = Path(JOBS_DIR) / job_id
    analytics_path = job_folder / "analytics.json"
    if analytics_path.exists():
        try:
            with open(analytics_path, 'r') as f:
                analytics_data = json.load(f)
            # Inject relevant fields
            response["progress_details"] = analytics_data.get("progress_details")
            response["timings"] = analytics_data.get("timings")
        except:
            pass # Non-critical if read fails
    
    return jsonify(response)


@app.route("/jobs", methods=["GET"])
def list_all_jobs():
    """List all jobs with their status (persisted across restarts)."""
    jobs = job_manager.get_all_jobs()
    return jsonify({
        "jobs": [{
            "job_id": j["id"],
            "type": j.get("type", "unknown"),
            "status": j["status"],
            "progress": j["progress"],
            "status_message": j.get("status_message") or j.get("message", ""),
            "created_at": j["created_at"],
            "completed_at": j["completed_at"],
            "error": j.get("error"),
            "params": {
                "subject": j.get("params", {}).get("subject", ""),
                "grade": j.get("params", {}).get("grade", ""),
                "dry_run": j.get("params", {}).get("dry_run", False)
            }
        } for j in jobs],
        "total": len(jobs)
    })


@app.route("/job/<job_id>/analytics", methods=["GET"])
def get_job_analytics(job_id):
    """Get analytics data for a completed job."""
    job = job_manager.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    # Try to load analytics.json from job folder
    job_folder = Path(JOBS_DIR) / job_id
    analytics_path = job_folder / "analytics.json"
    
    if analytics_path.exists():
        try:
            with open(analytics_path, 'r') as f:
                analytics_data = json.load(f)
            return jsonify({
                "job_id": job_id,
                "has_analytics": True,
                "analytics": analytics_data
            })
        except Exception as e:
            return jsonify({
                "job_id": job_id,
                "has_analytics": False,
                "error": f"Failed to load analytics: {str(e)}"
            }), 500
    else:
        # No analytics file - return basic job info
        return jsonify({
            "job_id": job_id,
            "has_analytics": False,
            "message": "Analytics not available for this job (pre-analytics feature or failed early)",
            "basic_info": {
                "status": job["status"],
                "created_at": job["created_at"],
                "completed_at": job.get("completed_at"),
                "error": job.get("error")
            }
        })


@app.route("/job/<job_id>/retry", methods=["POST"])
def retry_failed_job(job_id):
    """Retry a failed job - from point of failure if artifacts exist, or fresh if they don't."""
    try:
        if False: # is_job_running():
            current_id = get_current_job_ids()
            return jsonify({
                "status": "busy",
                "message": "A job is already running. Please wait for it to complete.",
                "current_job_id": current_id
            }), 409
        
        job = job_manager.get_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        if job["status"] != "failed":
            return jsonify({"error": "Can only retry failed jobs"}), 400
        
        job_folder = Path(JOBS_DIR) / job_id
        if not job_folder.exists():
            return jsonify({"error": "Job folder not found"}), 404
        
        source_markdown_path = job_folder / "source_markdown.md"
        if not source_markdown_path.exists():
            return jsonify({"error": "Source markdown not found"}), 400
        
        with open(source_markdown_path, 'r') as f:
            markdown_content = f.read()
        
        params = job.get("params", {})
        subject = params.get("subject", "General")
        grade = params.get("grade", "General")
        tts_provider = params.get("tts_provider", "edge_tts")
        dry_run = params.get("dry_run", False)
        skip_wan = params.get("skip_wan", False)
        skip_avatar = params.get("skip_avatar", False)
        
        # ISS-202 FIX: Check if artifacts exist to determine retry mode
        artifacts_dir = job_folder / "artifacts"
        chunker_exists = (artifacts_dir / "01_chunker.json").exists() if artifacts_dir.exists() else False
        planner_exists = (artifacts_dir / "02_planner.json").exists() if artifacts_dir.exists() else False
        
        # If no chunker/planner artifacts, job failed early - start fresh
        start_fresh = not (chunker_exists and planner_exists)
        
        if start_fresh:
            # ISS-202: Start fresh - job failed before any artifacts were created
            # Clear any partial artifacts/analytics from previous failed run
            import shutil
            if artifacts_dir.exists():
                shutil.rmtree(artifacts_dir)
            analytics_path = job_folder / "analytics.json"
            if analytics_path.exists():
                analytics_path.unlink()
            
            # Reset job status for fresh start
            job_manager.update_job(job_id, {
                "status": "pending", 
                "progress": 0, 
                "message": "Preparing fresh restart...",
                "error": None,
                "failure_message": None,
                "failed_phase": None
            }, persist=True)
            
            # Save markdown content for the job processor
            with open(source_markdown_path, 'w') as f:
                f.write(markdown_content)
            
            # Use run_job_async for proper lifecycle management (same as new jobs)
            run_job_async(
                job_id,
                process_markdown_job_v15,
                markdown_content=markdown_content,
                subject=subject,
                grade=grade,
                output_dir=str(job_folder),
                dry_run=dry_run,
                skip_wan=skip_wan,
                skip_avatar=skip_avatar,
                tts_provider=tts_provider
            )
            
            return jsonify({
                "status": "started",
                "job_id": job_id,
                "message": "Retry started fresh (cleared previous artifacts)",
                "mode": "fresh"
            })
        else:
            # Resume from failure point - artifacts exist
            analytics_path = job_folder / "analytics.json"
            error_msg = ""
            if analytics_path.exists():
                with open(analytics_path, 'r') as f:
                    analytics = json.load(f)
                error_msg = analytics.get("error", "")
            
            failed_section_idx = _determine_failed_section_idx(job_folder, error_msg)
            
            # ISS-203: Reset job state completely before launching worker
            job_manager.update_job(job_id, {
                "status": "pending", 
                "progress": 0, 
                "message": f"Preparing to resume from section {failed_section_idx}...",
                "status_message": f"Preparing to resume from section {failed_section_idx}...",
                "current_phase": None,
                "current_step": None,
                "error": None,
                "failure_message": None,
                "failed_phase": None,
                "started_at": None,
                "completed_at": None,
                "steps_completed": 0
            }, persist=True)
            
            # Define wrapper function for run_job_async
            def resume_job_wrapper(job_id, **kwargs):
                presentation, tracker = resume_from_section(
                    job_id=job_id,
                    output_dir=job_folder,
                    markdown_content=markdown_content,
                    resume_from_section_idx=failed_section_idx,
                    subject=subject,
                    grade=grade,
                    tts_provider=tts_provider,
                    generate_tts=True,
                    run_renderers=True,
                    dry_run=dry_run,
                    skip_wan=skip_wan,
                    status_callback=lambda phase, msg: job_manager.update_job(job_id, {"message": f"{phase}: {msg}", "status_message": f"{phase}: {msg}"}, persist=True)
                )
                
                presentation_path = job_folder / "presentation.json"
                with open(presentation_path, 'w') as f:
                    json.dump(presentation, f, indent=2)
                
                return {"presentation_path": str(presentation_path)}
            
            # Use run_job_async for proper lifecycle management (same as fresh jobs)
            run_job_async(job_id, resume_job_wrapper)
            
            return jsonify({
                "status": "started",
                "job_id": job_id,
                "message": f"Retry resuming from section {failed_section_idx}",
                "mode": "resume",
                "resume_from_section": failed_section_idx
            })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/job/<job_id>/cancel", methods=["POST"])
def cancel_job(job_id):
    """Force cancel a running job."""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
            
        # Update status to failed so user can retry or see it's stopped
        job_manager.update_job(job_id, {
            "status": "failed",
            "error": "Force stopped by user",
            "failure_message": "User initiated force stop"
        }, persist=True)
        
        return jsonify({"status": "cancelled", "job_id": job_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/job/<job_id>/regenerate_failed", methods=["POST"])
def regenerate_failed_videos(job_id):
    try:
        from core.video_regenerator import VideoRegenerator
        job_folder = Path(JOBS_DIR) / job_id
        if not job_folder.exists():
            return jsonify({"error": "Job folder not found"}), 404
            
        reg = VideoRegenerator(str(job_folder))
        result = reg.regenerate_failed()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/job/<job_id>/regenerate_section/<section_id>", methods=["POST"])
def regenerate_section_videos(job_id, section_id):
    try:
        from core.video_regenerator import VideoRegenerator
        job_folder = Path(JOBS_DIR) / job_id
        if not job_folder.exists():
            return jsonify({"error": "Job folder not found"}), 404
            
        reg = VideoRegenerator(str(job_folder))
        result = reg.regenerate_section(section_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/job/<job_id>/retry_phase", methods=["POST"])
def retry_phase(job_id):
    """
    Retry a specific phase for specific sections.
    
    POST body:
    {
        "phase": "manim_codegen" | "video_render" | "tts_generation",
        "section_ids": [3, 6, 11]  // Optional - if not provided, retries all failed sections for that phase
    }
    """
    try:
        # Parallel jobs enabled
        
        job = job_manager.get_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        job_folder = Path(JOBS_DIR) / job_id
        if not job_folder.exists():
            return jsonify({"error": "Job folder not found"}), 404
        
        presentation_path = job_folder / "presentation.json"
        if not presentation_path.exists():
            return jsonify({"error": "Presentation not found - job must complete LLM phase first"}), 400
        
        with open(presentation_path, 'r') as f:
            presentation = json.load(f)
        
        data = request.get_json() or {}
        phase = data.get("phase", "video_render")
        section_ids = data.get("section_ids")
        
        if phase == "manim_codegen":
            result = _retry_manim_codegen(job_id, job_folder, presentation, section_ids)
        elif phase == "video_render":
            result = _retry_video_render(job_id, job_folder, presentation, section_ids)
        elif phase == "wan_render":
            result = _retry_wan_render(job_id, job_folder, presentation, section_ids)
        elif phase == "manim_render":
            result = _retry_manim_render(job_id, job_folder, presentation, section_ids)
        elif phase == "avatar_generation":
            result = _retry_avatar_generation(job_id, job_folder, presentation, section_ids)
        else:
            return jsonify({"error": f"Unknown phase: {phase}. Valid: manim_codegen, wan_render, manim_render, avatar_generation"}), 400
        
        with open(presentation_path, 'w') as f:
            json.dump(presentation, f, indent=2)
        
        return jsonify({
            "status": "success",
            "phase": phase,
            "result": result
        })
        
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


def _retry_manim_codegen(job_id: str, job_folder: Path, presentation: dict, section_ids: list = None) -> dict:
    """Retry Manim code generation for specific sections."""
    from core.agents.manim_code_generator import ManimCodeGenerator, build_manim_section_data, integrate_manim_code_into_section
    
    manim_generator = ManimCodeGenerator()
    results = {"success": [], "failed": [], "skipped": []}
    
    failed_sections_path = job_folder / "manim_failed_sections.json"
    if failed_sections_path.exists() and section_ids is None:
        with open(failed_sections_path, 'r') as f:
            failed_data = json.load(f)
        section_ids = [s["section_id"] for s in failed_data.get("sections", [])]
    
    for section in presentation.get("sections", []):
        section_id = section.get("section_id")
        renderer = section.get("renderer", "")
        
        print(f"DEBUG: Checking Section {section_id} (Renderer: {renderer}) for retry. Target IDs: {section_ids}")

        if renderer != "manim":
            continue
        
        if section_ids and section_id not in section_ids:
            results["skipped"].append({"section_id": section_id, "reason": "Not in retry list"})
            continue
        
        # Check for existing manim_code in multiple locations (V2.5 compatibility)
        has_code = (
            section.get("manim_code") or  # Top-level (v1.5)
            section.get("render_spec", {}).get("manim_scene_spec", {}).get("manim_code")  # Nested (v2.5)
        )
        print(f"DEBUG: Section {section_id} has_code={bool(has_code)}")
        if has_code:
            if section_ids is None:
                print(f"DEBUG: Section {section_id} SKIPPED - already has valid code")
                results["skipped"].append({"section_id": section_id, "reason": "Already has valid code"})
                continue
            else:
                print(f"DEBUG: Forcing regen for Section {section_id} despite existing code.")
        
        print(f"DEBUG: Section {section_id} PROCEEDING to code generation")
        try:
            print(f"[RETRY] Regenerating Manim code for section {section_id}")
            manim_input = build_manim_section_data(
                section=section,
                narration_segments=section.get("narration", {}).get("segments", []),
                visual_beats=section.get("visual_beats", []),
                segment_enrichments=[]
            )
            
            manim_code, validation_errors = manim_generator.generate(manim_input)
            
            if manim_code and len(manim_code) > 100:
                section = integrate_manim_code_into_section(section, manim_code)
                results["success"].append({"section_id": section_id, "code_length": len(manim_code)})
                print(f"[RETRY] Manim code regenerated for section {section_id}: {len(manim_code)} chars")
            else:
                results["failed"].append({"section_id": section_id, "errors": validation_errors})
                print(f"[RETRY] Manim code regeneration failed for section {section_id}")
        except Exception as e:
            results["failed"].append({"section_id": section_id, "error": str(e)})
            print(f"[RETRY] Manim code regeneration error for section {section_id}: {e}")
    
    if failed_sections_path.exists() and results["success"]:
        failed_sections_path.unlink()
    
    return results


def _retry_video_render(job_id: str, job_folder: Path, presentation: dict, section_ids: list = None) -> dict:
    """Retry video rendering for specific sections."""
    from core.renderer_executor import execute_renderer
    
    videos_dir = job_folder / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    
    results = {"success": [], "failed": [], "skipped": []}
    
    for section in presentation.get("sections", []):
        section_id = section.get("section_id")
        renderer = section.get("renderer", "none")
        section_type = section.get("section_type", "")
        
        if renderer == "none" or section_type in ["intro", "summary", "quiz", "memory"]:
            continue
        
        if section_ids and section_id not in section_ids:
            results["skipped"].append({"section_id": section_id, "reason": "Not in retry list"})
            continue
        
        existing_video = section.get("video_path")
        if existing_video and (job_folder / existing_video).exists():
            if section_ids is None:
                results["skipped"].append({"section_id": section_id, "reason": "Video already exists"})
                continue
        
        try:
            print(f"[RETRY] Re-rendering video for section {section_id} (renderer: {renderer})")
            
            result = execute_renderer(
                topic=section,
                output_dir=str(videos_dir),
                dry_run=False,
                skip_wan=False,
                trace_output_dir=str(job_folder),
                strict_mode=True
            )
            
            if result.get("status") == "success":
                video_path = result.get("video_path")
                if video_path:
                    rel_path = Path(video_path).name
                    section["video_path"] = f"videos/{rel_path}"
                results["success"].append({"section_id": section_id, "video_path": video_path})
                print(f"[RETRY] Video rendered for section {section_id}: {video_path}")
            else:
                results["failed"].append({"section_id": section_id, "error": result.get("error")})
                print(f"[RETRY] Video render failed for section {section_id}: {result.get('error')}")
        except Exception as e:
            results["failed"].append({"section_id": section_id, "error": str(e)})
            print(f"[RETRY] Video render error for section {section_id}: {e}")
    
    return results


def _retry_wan_render(job_id: str, job_folder: Path, presentation: dict, section_ids: list = None) -> dict:
    """Retry WAN video rendering for sections with renderer='video'."""
    from core.renderer_executor import execute_renderer
    
    videos_dir = job_folder / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    
    results = {"success": [], "failed": [], "skipped": []}
    
    for section in presentation.get("sections", []):
        section_id = section.get("section_id")
        renderer = section.get("renderer", "none")
        
        # Only process WAN/video sections
        if renderer not in ["video", "wan"]:
            continue
        
        if section_ids and section_id not in section_ids:
            results["skipped"].append({"section_id": section_id, "reason": "Not in retry list"})
            continue
        
        try:
            print(f"[RETRY-WAN] Re-rendering WAN video for section {section_id}")
            
            result = execute_renderer(
                topic=section,
                output_dir=str(videos_dir),
                dry_run=False,
                skip_wan=False,
                trace_output_dir=str(job_folder),
                strict_mode=True
            )
            
            if result.get("status") == "success":
                video_path = result.get("video_path")
                if video_path:
                    rel_path = Path(video_path).name
                    section["video_path"] = f"videos/{rel_path}"
                results["success"].append({"section_id": section_id, "video_path": video_path})
            else:
                results["failed"].append({"section_id": section_id, "error": result.get("error")})
        except Exception as e:
            results["failed"].append({"section_id": section_id, "error": str(e)})
    
    return results


def _retry_manim_render(job_id: str, job_folder: Path, presentation: dict, section_ids: list = None) -> dict:
    """Retry Manim video rendering for sections with renderer='manim'."""
    from core.renderer_executor import execute_renderer
    
    videos_dir = job_folder / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    
    results = {"success": [], "failed": [], "skipped": []}
    
    for section in presentation.get("sections", []):
        section_id = section.get("section_id")
        renderer = section.get("renderer", "none")
        
        # Only process Manim sections
        if renderer != "manim":
            continue
        
        if section_ids and section_id not in section_ids:
            results["skipped"].append({"section_id": section_id, "reason": "Not in retry list"})
            continue
        
        try:
            print(f"[RETRY-MANIM] Re-rendering Manim video for section {section_id}")
            
            result = execute_renderer(
                topic=section,
                output_dir=str(videos_dir),
                dry_run=False,
                skip_wan=True,  # Skip WAN for Manim sections
                trace_output_dir=str(job_folder),
                strict_mode=True
            )
            
            if result.get("status") == "success":
                video_path = result.get("video_path")
                if video_path:
                    rel_path = Path(video_path).name
                    section["video_path"] = f"videos/{rel_path}"
                results["success"].append({"section_id": section_id, "video_path": video_path})
            else:
                results["failed"].append({"section_id": section_id, "error": result.get("error")})
        except Exception as e:
            results["failed"].append({"section_id": section_id, "error": str(e)})
    
    return results



def _retry_avatar_generation(job_id: str, job_folder: Path, presentation: dict, section_ids: list = None) -> dict:
    """Retry avatar generation for specific sections or all failed."""
    from core.agents.avatar_generator import AvatarGenerator
    
    avatars_dir = job_folder / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)
    
    results = {"success": [], "failed": [], "skipped": []}
    generator = AvatarGenerator()
    
    # If no section_ids provided, find failed sections from status
    if section_ids is None:
        status_file = job_folder / "avatar_status.json"
        if status_file.exists():
            try:
                status_data = json.loads(status_file.read_text())
                section_ids = status_data.get("details", {}).get("failed_sections", [])
            except:
                section_ids = []
    
    if not section_ids:
        # Fallback: check all segments that don't have a valid avatar
        section_ids = []
        for section in presentation.get("sections", []):
            sec_id = section.get("section_id")
            avatar_path = avatars_dir / f"section_{sec_id}_avatar.mp4"
            if not avatar_path.exists() or avatar_path.stat().st_size < 10000:
                section_ids.append(sec_id)

    if not section_ids:
        return {"message": "No sections to retry", "success": [], "failed": [], "skipped": []}
    
    for section in presentation.get("sections", []):
        sec_id = section.get("section_id")
        
        if sec_id not in section_ids:
            continue
        
        # Extract narration text
        narration = section.get("narration", {})
        full_text = ""
        if isinstance(narration, dict):
             full_text = narration.get("full_text", "") or " ".join([str(s.get("text", "") or "") for s in narration.get("segments", [])])
        else:
             full_text = str(narration)
             
        if not full_text.strip():
            results["skipped"].append({"section_id": sec_id, "reason": "No narration text"})
            continue
        
        try:
            output_filename = f"section_{sec_id}_avatar.mp4"
            output_path = avatars_dir / output_filename
            
            # Submit and poll
            print(f"[RETRY-AVATAR] Submitting Sec {sec_id}...", flush=True)
            response = generator.generate_avatar_video(full_text, job_id, sec_id)
            task_id = response.get("task_id")
            
            if not task_id:
                results["failed"].append({"section_id": sec_id, "error": response.get("error", "No task_id returned")})
                continue
            
            # Poll for completion (max 5 minutes per section)
            start_poll = time.time()
            success = False
            while time.time() - start_poll < 300:
                status_resp = generator.check_status(task_id)
                status = status_resp.get("status")
                print(f"[RETRY-AVATAR] Sec {sec_id} polling: {status}", flush=True)
                
                if status == "completed" or status == "success":
                    if generator.download_video(task_id, str(output_path)):
                        section["avatar_path"] = f"avatars/{output_filename}"
                        results["success"].append({"section_id": sec_id, "task_id": task_id})
                        print(f"[RETRY-AVATAR] Sec {sec_id} DONE! Saved to {output_path}", flush=True)
                        
                        # Save presentation immediately so we don't lose progress
                        try:
                            with open(job_folder / "presentation.json", "w", encoding="utf-8") as f:
                                json.dump(presentation, f, indent=2)
                        except Exception as save_err:
                            print(f"[RETRY-AVATAR] Warning: Failed to save presentation.json: {save_err}")
                    else:
                        results["failed"].append({"section_id": sec_id, "error": "Download failed"})
                    
                    success = True
                    break
                elif status == "failed" or status == "not_found":
                    results["failed"].append({"section_id": sec_id, "error": status_resp.get("message", f"Task {status}")})
                    success = True # Marked as handled
                    break
                time.sleep(5)
            
            if not success:
                results["failed"].append({"section_id": sec_id, "error": "Timeout after 5 minutes"})
                
        except Exception as e:
            results["failed"].append({"section_id": sec_id, "error": str(e)})
    
    return results


def _retry_tts_generation(job_id: str, job_folder: Path, presentation: dict, section_ids: list = None) -> dict:
    """Retry TTS generation for specific sections (or all if None)."""
    from core.tts_duration import update_durations_simplified
    
    results = {"success": [], "failed": [], "skipped": []}
    
    # Get tts_provider from job params or default to edge_tts
    job = job_manager.get_job(job_id)
    params = job.get("params", {})
    tts_provider = params.get("tts_provider", "edge_tts")
    if tts_provider == "edge": tts_provider = "edge_tts" # Force fix
    
    try:
        print(f"[RETRY] Starting TTS generation retry for job {job_id} using {tts_provider}")
        # update_durations_simplified updates the presentation object in-place
        _ = update_durations_simplified(
            presentation=presentation,
            output_dir=job_folder,
            production_provider=tts_provider
        )
        
        # Count progress
        audio_dir = job_folder / "audio"
        audio_files = list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.wav"))
        
        results["success"].append({
            "message": f"TTS generation completed. {len(audio_files)} audio files present.",
            "audio_count": len(audio_files)
        })
        print(f"[RETRY] TTS generation retry successful for {job_id}")
    except Exception as e:
        results["failed"].append({"error": str(e)})
        print(f"[RETRY] TTS generation failed for {job_id}: {e}")
        
    return results


def _determine_failed_section_idx(job_folder: Path, error_msg: str) -> int:
    """Determine which section index to resume from based on existing artifacts."""
    artifacts_dir = job_folder / "artifacts"
    if not artifacts_dir.exists():
        return 0
    
    planner_path = artifacts_dir / "02_planner.json"
    if not planner_path.exists():
        return 0
    
    with open(planner_path, 'r') as f:
        planner_data = json.load(f)
        blueprints = planner_data.get("sections", [])
    
    content_section_count = 0
    for i, bp in enumerate(blueprints):
        section_type = bp.get("section_type", "")
        section_id = bp.get("section_id", "")
        
        if section_type in ["memory", "recap"]:
            continue
        
        artifact_idx = content_section_count + 3
        narration_file = artifacts_dir / f"{artifact_idx:02d}_{section_id}_narration.json"
        visuals_file = artifacts_dir / f"{artifact_idx:02d}_{section_id}_visuals.json"
        
        if not narration_file.exists() or not visuals_file.exists():
            return i
        
        content_section_count += 1
    
    memory_file = artifacts_dir / "memory.json"
    if not memory_file.exists():
        for i, bp in enumerate(blueprints):
            if bp.get("section_type") == "memory":
                return i
    
    recap_file = artifacts_dir / "recap.json"
    if not recap_file.exists():
        for i, bp in enumerate(blueprints):
            if bp.get("section_type") == "recap":
                return i
    
    return 0


@app.route("/job/<job_id>/llm-outputs", methods=["GET"])
def get_job_llm_outputs(job_id):
    """List all available LLM output artifacts for a job."""
    job = job_manager.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    job_folder = Path(JOBS_DIR) / job_id
    if not job_folder.exists():
        return jsonify({"error": "Job folder not found"}), 404
    
    outputs = []
    
    # Check for artifacts directory (structured agent outputs)
    artifacts_dir = job_folder / "artifacts"
    if artifacts_dir.exists():
        for f in sorted(artifacts_dir.iterdir()):
            if f.is_file() and f.suffix == ".json":
                stat = f.stat()
                outputs.append({
                    "name": f.name,
                    "path": f"artifacts/{f.name}",
                    "category": "agent_output",
                    "size_bytes": stat.st_size,
                    "description": _get_artifact_description(f.name)
                })
    
    # Check for llm_responses directory (raw LLM outputs)
    llm_responses_dir = job_folder / "llm_responses"
    if llm_responses_dir.exists():
        for f in sorted(llm_responses_dir.iterdir()):
            if f.is_file():
                stat = f.stat()
                outputs.append({
                    "name": f.name,
                    "path": f"llm_responses/{f.name}",
                    "category": "raw_llm",
                    "size_bytes": stat.st_size,
                    "description": "Raw LLM response with prompt"
                })
    
    # Check for render_prompts.json
    render_prompts = job_folder / "render_prompts.json"
    if render_prompts.exists():
        stat = render_prompts.stat()
        outputs.append({
            "name": "render_prompts.json",
            "path": "render_prompts.json",
            "category": "renderer",
            "size_bytes": stat.st_size,
            "description": "All Manim/WAN video generation prompts"
        })
    
    # Check for generation_trace.json
    trace_file = job_folder / "generation_trace.json"
    if trace_file.exists():
        stat = trace_file.stat()
        outputs.append({
            "name": "generation_trace.json",
            "path": "generation_trace.json",
            "category": "trace",
            "size_bytes": stat.st_size,
            "description": "Full pipeline execution trace"
        })
    
    # Check for source markdown
    source_md = job_folder / "source_markdown.md"
    if source_md.exists():
        stat = source_md.stat()
        outputs.append({
            "name": "source_markdown.md",
            "path": "source_markdown.md",
            "category": "source",
            "size_bytes": stat.st_size,
            "description": "Input markdown from PDF/file"
        })
    
    return jsonify({
        "job_id": job_id,
        "total_outputs": len(outputs),
        "outputs": outputs,
        "categories": {
            "agent_output": "Structured outputs from pipeline agents (Chunker, Planner, NarrationWriter, VisualSpecArtist)",
            "raw_llm": "Raw LLM API responses with full prompts",
            "renderer": "Prompts sent to visual renderers (Manim, WAN)",
            "trace": "Pipeline execution trace with all events",
            "source": "Original input content"
        }
    })


def _get_artifact_description(filename: str) -> str:
    """Get human-readable description for artifact files."""
    name_lower = filename.lower()
    if "chunker" in name_lower:
        return "SmartChunker output - content blocks with metadata"
    elif "planner" in name_lower:
        return "SectionPlanner output - section structure and goals"
    elif "narration" in name_lower:
        return "NarrationWriter output - narration segments with timing"
    elif "visuals" in name_lower:
        return "VisualSpecArtist output - visual beats and display directives"
    elif "memory" in name_lower:
        return "MemoryAgent output - key concepts for retention"
    elif "recap" in name_lower:
        return "RecapAgent output - chapter summary"
    return "Pipeline artifact"


@app.route("/job/<job_id>/llm-outputs/<path:file_path>", methods=["GET"])
def get_job_llm_output_file(job_id, file_path):
    """Get content of a specific LLM output file."""
    job = job_manager.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    job_folder = Path(JOBS_DIR) / job_id
    target_file = job_folder / file_path
    
    # Security: ensure path stays within job folder
    try:
        target_file.resolve().relative_to(job_folder.resolve())
    except ValueError:
        return jsonify({"error": "Invalid file path"}), 400
    
    if not target_file.exists():
        return jsonify({"error": "File not found"}), 404
    
    try:
        content = target_file.read_text(encoding="utf-8")
        
        # Try to parse as JSON for structured response
        file_type = "text"
        parsed_content = None
        if target_file.suffix == ".json":
            try:
                parsed_content = json.loads(content)
                file_type = "json"
            except json.JSONDecodeError:
                pass
        
        return jsonify({
            "job_id": job_id,
            "file_path": file_path,
            "file_type": file_type,
            "size_bytes": len(content),
            "content": parsed_content if file_type == "json" else content
        })
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {str(e)}"}), 500


def process_pdf_job(job_id: str, pdf_path: str, subject: str, grade: str, output_dir: str, dry_run: bool = False, skip_wan: bool = False, skip_avatar: bool = False, source_file: Optional[str] = None, tts_provider: str = "edge_tts") -> dict:
    try:
        result = process_pdf_to_videos(
            pdf_path=pdf_path,
            subject=subject,
            grade=grade,
            output_dir=output_dir,
            job_id=job_id,
            dry_run=dry_run,
            skip_wan=skip_wan,
            skip_avatar=skip_avatar,
            source_file=source_file
        )
        return result
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)


def process_pdf_job_v15(job_id: str, pdf_path: str, subject: str, grade: str, output_dir: str, dry_run: bool = False, skip_wan: bool = False, skip_avatar: bool = False, source_file: Optional[str] = None, tts_provider: str = "edge_tts") -> dict:
    """Legacy wrapper - redirects to process_document_job_v15."""
    return process_document_job_v15(
        job_id=job_id,
        document_path=pdf_path,
        subject=subject,
        grade=grade,
        output_dir=output_dir,
        dry_run=dry_run,
        skip_wan=skip_wan,
        skip_avatar=skip_avatar,
        source_file=source_file,
        tts_provider=tts_provider
    )


def process_document_job_v15(job_id: str, document_path: str, subject: str, grade: str, output_dir: str, dry_run: bool = False, skip_wan: bool = False, skip_avatar: bool = False, source_file: Optional[str] = None, tts_provider: str = "edge_tts") -> dict:
    """ISS-206/207: Process PDF/DOC/DOCX/ODT using V1.5 Optimized pipeline.
    
    1. Convert document to Markdown using Datalab API (supports PDF, DOC, DOCX, ODT)
    2. Capture page_count from Datalab response
    3. Run V1.5 optimized pipeline on the markdown
    """
    from core.datalab_client import document_to_markdown, DatalabConversionError
    from pathlib import Path
    
    try:
        file_ext = Path(document_path).suffix.lower()
        job_manager.update_job(job_id, {
            "current_phase_key": "document_conversion",
            "status_message": f"Converting {file_ext.upper()} to Markdown..."
        }, persist=True)
        
        # ISS-206/207: Use new document_to_markdown with ConversionResult
        conversion_result = document_to_markdown(document_path)
        markdown_content = conversion_result.markdown
        page_count = conversion_result.page_count
        
        # Save raw markdown for comparison/debugging
        source_md_path = Path(output_dir) / "source_markdown.md"
        with open(source_md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"[V1.5 Optimized] Saved source markdown to {source_md_path} ({len(markdown_content)} chars, {page_count} pages)")
        
        content_preview = markdown_content[:300].replace('\n', ' ').strip()
        if len(markdown_content) > 300:
            content_preview += "..."
        
        # ISS-207: Store page_count in job metadata
        job_manager.update_job(job_id, {
            "content_preview": content_preview,
            "page_count": page_count,
            "source_type": file_ext.replace('.', '')
        }, persist=True)
        
        def status_callback(jid, phase, message):
            job_manager.update_job(jid, {
                "current_phase_key": phase,
                "status_message": message
            }, persist=True)
        
        generate_tts = tts_provider != "estimate"
        output_path = Path(output_dir)
        
        # Use optimized pipeline with combined agents
        presentation, tracker = process_markdown_optimized(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            job_id=job_id,
            update_status_callback=status_callback,
            generate_tts=generate_tts,
            output_dir=output_path,
            tts_provider=tts_provider,
            dry_run=dry_run,
            skip_wan=skip_wan
        )
        
        pres_path = output_path / "presentation.json"
        with open(pres_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        analytics_summary = tracker.get_summary() if hasattr(tracker, 'get_summary') else {}
        
        # ISS-207: Add page_count to analytics
        analytics_summary["page_count"] = page_count
        
        return {
            "status": "success",
            "presentation": presentation,
            "analytics": analytics_summary,
            "output_path": str(pres_path),
            "pipeline_version": "1.5",
            "source_type": file_ext.replace('.', ''),
            "page_count": page_count
        }
    except DatalabConversionError as e:
        raise RuntimeError(f"Document conversion failed: {e}")
    finally:
        if os.path.exists(document_path):
            os.unlink(document_path)


def process_document_job_v15_v2(job_id: str, document_path: str, subject: str, grade: str, output_dir: str, dry_run: bool = False, skip_wan: bool = False, skip_avatar: bool = False, source_file: Optional[str] = None, tts_provider: str = "edge_tts", pipeline_version: str = "v15_v2_director", generation_scope: str = "full", model: Optional[str] = None) -> dict:
    """Process PDF/DOC/DOCX/ODT using V1.5 V2 Unified pipeline with image handling.
    
    1. Convert document to Markdown using Datalab API (captures images)
    2. Save images to job/images/ folder with green screen processing
    3. Run V2 unified pipeline with images_list
    """
    from core.datalab_client import document_to_markdown, DatalabConversionError
    from pathlib import Path
    
    try:
        file_ext = Path(document_path).suffix.lower()
        job_manager.update_job(job_id, {
            "current_phase_key": "document_conversion",
            "status_message": f"Converting {file_ext.upper()} to Markdown..."
        }, persist=True)
        
        conversion_result = document_to_markdown(document_path)
        markdown_content = conversion_result.markdown
        page_count = conversion_result.page_count
        images_dict = conversion_result.images
        
        print(f"[V1.5-V2] Document converted: {len(markdown_content)} chars, {page_count} pages, {len(images_dict)} images")
        
        job_manager.update_job(job_id, {
            "page_count": page_count,
            "source_type": file_ext.replace('.', ''),
            "image_count": len(images_dict)
        }, persist=True)
        
        return process_markdown_job_v15_v2(
            job_id=job_id,
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            output_dir=output_dir,
            dry_run=dry_run,
            skip_wan=skip_wan,
            skip_avatar=skip_avatar,
            source_file=source_file,
            tts_provider=tts_provider,
            images_dict=images_dict,
            pipeline_version=pipeline_version,
            generation_scope=generation_scope
        )
    except DatalabConversionError as e:
        raise RuntimeError(f"Document conversion failed: {e}")
    finally:
        if os.path.exists(document_path):
            os.unlink(document_path)


def process_markdown_job(job_id: str, markdown_content: str, subject: str, grade: str, output_dir: str, dry_run: bool = False, skip_wan: bool = False, skip_avatar: bool = False, source_file: Optional[str] = None, tts_provider: str = "edge_tts") -> dict:
    """Process markdown using V1.4 Hybrid pipeline (Split Directors + V1.3 infrastructure)."""
    result = process_markdown_to_videos(
        markdown_content=markdown_content,
        subject=subject,
        grade=grade,
        output_dir=output_dir,
        job_id=job_id,
        dry_run=dry_run,
        skip_wan=skip_wan,
        skip_avatar=skip_avatar,
        source_file=source_file,
        use_remotion=True
    )
    return result


def process_markdown_job_v15(job_id: str, markdown_content: str, subject: str, grade: str, output_dir: str, dry_run: bool = False, skip_wan: bool = False, skip_avatar: bool = False, source_file: Optional[str] = None, tts_provider: str = "edge_tts") -> dict:
    """Process markdown using V1.5 Optimized pipeline (combined agents, ~50% fewer LLM calls)."""
    from pathlib import Path
    
    # Save raw markdown for comparison/debugging
    output_path = Path(output_dir)
    source_md_path = output_path / "source_markdown.md"
    with open(source_md_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"[V1.5 Optimized] Saved source markdown to {source_md_path} ({len(markdown_content)} chars)")
    
    def status_callback(jid, phase, message):
        job_manager.update_job(jid, {
            "current_phase_key": phase,
            "status_message": message
        }, persist=True)
    
    generate_tts = tts_provider != "estimate"
    
    # Use optimized pipeline with combined agents
    presentation, tracker = process_markdown_optimized(
        markdown_content=markdown_content,
        subject=subject,
        grade=grade,
        job_id=job_id,
        update_status_callback=status_callback,
        generate_tts=generate_tts,
        output_dir=output_path,
        tts_provider=tts_provider,
        dry_run=dry_run,
        skip_wan=skip_wan
    )
    
    pres_path = output_path / "presentation.json"
    with open(pres_path, "w") as f:
        json.dump(presentation, f, indent=2)
    
    analytics_summary = tracker.get_summary() if hasattr(tracker, 'get_summary') else {}
    
    return {
        "status": "success",
        "presentation": presentation,
        "analytics": analytics_summary,
        "output_path": str(pres_path),
        "pipeline_version": "1.5"
    }


def process_markdown_job_v15_v2(job_id: str, markdown_content: str, subject: str, grade: str, output_dir: str, dry_run: bool = False, skip_wan: bool = False, skip_avatar: bool = False, source_file: Optional[str] = None, tts_provider: str = "edge_tts", images_dict: dict = None, pipeline_version: str = "v15_v2_director", generation_scope: str = "full", model: Optional[str] = None) -> dict:
    """Process markdown using V1.5 V2 Unified pipeline (single LLM call).
    
    Routes to core.pipeline_unified.process_markdown_unified which handles:
    - Image extraction and processing
    - Single LLM generation
    - Manim code generation (Bridging)
    - TTS and Rendering
    """
    from pathlib import Path
    from core.pipeline_unified import process_markdown_unified, PipelineUnifiedError
    
    output_path = Path(output_dir)
    source_md_path = output_path / "source_markdown.md"
    with open(source_md_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"[V1.5-V2] Saved source markdown to {source_md_path} ({len(markdown_content)} chars)")
    
    def status_callback(jid, phase, message):
        job_manager.update_job(jid, {
            "current_phase_key": phase,
            "status_message": message
        }, persist=True)
    
    try:
        generate_tts = tts_provider not in ["estimate"]
        
        presentation, tracker = process_markdown_unified(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            job_id=job_id,
            update_status_callback=status_callback,
            generate_tts=generate_tts,
            output_dir=output_path,
            tts_provider=tts_provider,
            dry_run=dry_run,
            skip_wan=skip_wan,
            images_dict=images_dict,
            pipeline_version=pipeline_version,
            generation_scope=generation_scope
        )
        
        pres_path = output_path / "presentation.json"
        with open(pres_path, "w") as f:
            json.dump(presentation, f, indent=2)
            
        # Analytics handling
        analytics_summary = tracker.get_summary() if hasattr(tracker, 'get_summary') else {}
        # Ensure complete analytics dict is saved if get_summary is partial
        if hasattr(tracker, 'to_dict'):
            analytics_full = tracker.to_dict()
            analytics_path = output_path / "analytics.json"
            with open(analytics_path, "w") as f:
                json.dump(analytics_full, f, indent=2)
        
        # Auto-trigger Avatar Polling & Download
        if not skip_avatar:
            print(f"[AVATAR] Auto-triggering background generation task for Job {job_id}", flush=True)
            from threading import Thread
            if job_id not in ACTIVE_AVATAR_JOBS:
                ACTIVE_AVATAR_JOBS.add(job_id)
                thread = Thread(target=run_avatar_sequential_task, args=(job_id, str(JOBS_DIR)))
                thread.daemon = True
                thread.start()
        
        return {
            "status": "success",
            "presentation": presentation,
            "analytics": analytics_summary,
            "output_path": str(pres_path),
            "pipeline_version": "1.5-unified"
        }
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[V1.5-V2 Pipeline Error] {str(e)}\n{tb}")
        raise RuntimeError(f"Unified Pipeline Error: {e}")



    



@app.route("/process_pdf", methods=["POST"])
def process_pdf():
    """Legacy endpoint - now creates job folders for proper isolation."""
    try:
        subject = request.form.get("subject", "General Science")
        grade = request.form.get("grade", "9")
        
        if "file" in request.files:
            pdf_file = request.files["file"]
            if pdf_file.filename == "":
                return jsonify({"error": "No file selected"}), 400
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf_file.save(tmp.name)
                tmp_path = tmp.name
            
            job_id = job_manager.create_job("pdf_legacy", {
                "subject": subject,
                "grade": grade,
                "source_file": pdf_file.filename
            })
            job_output_dir = JOBS_DIR / job_id
            setup_job_folder(job_output_dir)
            
            try:
                result = process_pdf_to_videos(
                    pdf_path=tmp_path,
                    subject=subject,
                    grade=grade,
                    output_dir=str(job_output_dir),
                    job_id=job_id
                )
                result["job_id"] = job_id
            finally:
                os.unlink(tmp_path)
        
        elif request.is_json and "markdown" in request.json:
            markdown_content = request.json["markdown"]
            subject = request.json.get("subject", subject)
            grade = request.json.get("grade", grade)
            
            job_id = job_manager.create_job("markdown_legacy", {
                "subject": subject,
                "grade": grade
            })
            job_output_dir = JOBS_DIR / job_id
            setup_job_folder(job_output_dir)
            
            result = process_markdown_to_videos(
                markdown_content=markdown_content,
                subject=subject,
                grade=grade,
                output_dir=str(job_output_dir),
                job_id=job_id
            )
            result["job_id"] = job_id
        
        else:
            return jsonify({
                "error": "Please provide either a PDF file or markdown content"
            }), 400
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route("/process_markdown", methods=["POST"])
def process_markdown():
    """Legacy endpoint - now creates job folders for proper isolation."""
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.json
        markdown_content = data.get("markdown", "")
        subject = data.get("subject", "General Science")
        grade = data.get("grade", "9")
        
        if not markdown_content:
            return jsonify({"error": "Markdown content is required"}), 400
        
        job_id = job_manager.create_job("markdown_legacy", {
            "subject": subject,
            "grade": grade
        })
        job_output_dir = JOBS_DIR / job_id
        setup_job_folder(job_output_dir)
        
        result = process_markdown_to_videos(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            output_dir=str(job_output_dir),
            job_id=job_id
        )
        result["job_id"] = job_id
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route("/jobs/<job_id>/resume", methods=["POST"])
def resume_job(job_id):
    """Resume a failed job from a specific phase.
    
    POST body:
    - from_phase: "render" or "audio" (default: "audio")
    - dry_run: boolean (default: false)
    - skip_wan: boolean (default: false)
    - skip_avatar: boolean (default: false)
    """
    from core.pipeline_v12 import resume_job_from_phase, detect_job_phase
    
    data = request.get_json() or {}
    from_phase = data.get("from_phase", "audio")
    dry_run = data.get("dry_run", False)
    skip_wan = data.get("skip_wan", False)
    skip_avatar = data.get("skip_avatar", False)
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    
    phases = detect_job_phase(str(job_dir))
    
    if not phases["presentation"]:
        return jsonify({
            "error": "Cannot resume - presentation.json missing. Job must have completed Director phase.",
            "job_id": job_id,
            "phases": phases
        }), 400
    
    try:
        print(f"[API] Resuming job {job_id} from phase: {from_phase}")
        result = resume_job_from_phase(
            job_id=job_id,
            from_phase=from_phase,
            dry_run=dry_run,
            skip_wan=skip_wan,
            skip_avatar=skip_avatar
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "job_id": job_id
        }), 500


@app.route("/jobs/<job_id>/resume-recap", methods=["POST"])
def resume_job_from_recap(job_id):
    """Resume a V1.5 job from the recap stage.
    
    Use when the job failed at recap narration/scene generation.
    Loads existing artifacts and continues from recap.
    
    POST body (optional):
    - skip_wan: boolean (default: false)
    - dry_run: boolean (default: false)
    """
    from core.pipeline_v15 import resume_from_recap, PipelineError
    
    data = request.get_json() or {}
    skip_wan = data.get("skip_wan", False)
    dry_run = data.get("dry_run", False)
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    
    artifacts_dir = job_dir / "artifacts"
    if not artifacts_dir.exists():
        return jsonify({
            "error": "Artifacts directory not found. Job must have completed section processing.",
            "job_id": job_id
        }), 400
    
    chunker_path = artifacts_dir / "01_chunker.json"
    if not chunker_path.exists():
        return jsonify({
            "error": "01_chunker.json not found. Cannot resume without source content.",
            "job_id": job_id
        }), 400
    
    with open(chunker_path) as f:
        chunker_data = json.load(f)
    
    chunks = chunker_data.get("chunks", [])
    markdown_content = "\n\n".join([c.get("content", "") for c in chunks])
    
    subject = chunker_data.get("subject", "General")
    grade = chunker_data.get("grade", "General")
    
    try:
        print(f"[API] Resuming job {job_id} from recap stage")
        
        def status_callback(phase, message):
            print(f"[Resume {job_id}] {phase}: {message}")
        
        presentation, tracker = resume_from_recap(
            job_id=job_id,
            output_dir=job_dir,
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            generate_tts=True,
            run_renderers=True,
            dry_run=dry_run,
            skip_wan=skip_wan,
            status_callback=status_callback
        )
        
        pres_path = job_dir / "presentation.json"
        with open(pres_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        for filename in ["index.html", "player.js"]:
            src = PLAYER_DIR / filename
            dst = job_dir / filename
            if src.exists():
                shutil.copy(str(src), str(dst))
        
        # Update job_manager status so dashboard shows completed
        sections_count = len(presentation.get("sections", []))
        job_manager.update_job(job_id, {
            "status": "completed",
            "progress": 100,
            "current_step_name": "Complete",
            "status_message": f"Resumed from recap - {sections_count} sections rendered",
            "completed_at": __import__('datetime').datetime.utcnow().isoformat(),
            "error": None
        }, persist=True)
        
        return jsonify({
            "status": "success",
            "job_id": job_id,
            "sections_count": sections_count,
            "message": "Job resumed from recap stage successfully"
        })
        
    except PipelineError as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "phase": e.phase,
            "job_id": job_id
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "job_id": job_id
        }), 500


@app.route("/jobs/<job_id>/phases", methods=["GET"])
def get_job_phases(job_id):
    """Get phase completion status for a job."""
    from core.pipeline_v12 import detect_job_phase
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    
    phases = detect_job_phase(str(job_dir))
    phases["job_id"] = job_id
    
    return jsonify(phases)


@app.route("/jobs/<job_id>/rerender", methods=["POST"])
def rerender_job_sections(job_id):
    """Re-render specific sections with WAN video renderer.
    
    POST body:
    - section_ids: List of section IDs to re-render (required)
    - renderer: "wan_video" (default, only option currently)
    """
    from core.llm_client_v12 import rerender_sections_wan
    from core.analytics import create_tracker
    
    data = request.get_json() or {}
    section_ids = data.get("section_ids", [])
    
    if not section_ids:
        return jsonify({"error": "section_ids required"}), 400
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    
    pres_path = job_dir / "presentation.json"
    if not pres_path.exists():
        return jsonify({"error": "presentation.json not found"}), 400
    
    try:
        with open(pres_path, "r") as f:
            presentation = json.load(f)
        
        tracker = create_tracker(job_id)
        
        print(f"[API] Re-rendering sections {section_ids} for job {job_id}")
        updated = rerender_sections_wan(presentation, section_ids, tracker)
        
        with open(pres_path, "w") as f:
            json.dump(updated, f, indent=2)
        
        sections_updated = []
        for s in updated.get("sections", []):
            sid = s.get("section_id") or s.get("id")
            if sid in section_ids:
                sections_updated.append({
                    "section_id": sid,
                    "renderer": s.get("renderer"),
                    "video_prompts_count": len(s.get("video_prompts", [])),
                    "error": s.get("renderer_error")
                })
        
        return jsonify({
            "status": "success",
            "job_id": job_id,
            "sections_updated": sections_updated
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "job_id": job_id
        }), 500


@app.route("/jobs/<job_id>/generate_videos", methods=["POST"])
def generate_videos_from_prompts(job_id):
    """Generate actual videos from video_prompts using WAN/KIE API.
    
    POST body:
    - section_ids: List of section IDs to generate videos for (required)
    - skip_wan: If true, create placeholder videos (default: false)
    - dry_run: If true, only create marker files (default: false)
    """
    from render.wan.wan_runner import render_from_video_prompts, WanRenderError
    
    data = request.get_json() or {}
    section_ids = data.get("section_ids", [])
    skip_wan = data.get("skip_wan", False)
    dry_run = data.get("dry_run", False)
    
    if not section_ids:
        return jsonify({"error": "section_ids required"}), 400
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    
    pres_path = job_dir / "presentation.json"
    if not pres_path.exists():
        return jsonify({"error": "presentation.json not found"}), 400
    
    try:
        with open(pres_path, "r") as f:
            presentation = json.load(f)
        
        videos_dir = job_dir / "videos"
        videos_dir.mkdir(exist_ok=True)
        
        results = []
        for section in presentation.get("sections", []):
            sid = section.get("section_id") or section.get("id")
            if sid not in section_ids:
                continue
            
            video_prompts = section.get("video_prompts", [])
            if not video_prompts:
                results.append({
                    "section_id": sid,
                    "status": "skipped",
                    "reason": "No video_prompts"
                })
                continue
            
            print(f"[API] Generating videos for section {sid} ({len(video_prompts)} prompts)")
            
            try:
                video_paths = render_from_video_prompts(
                    section=section,
                    output_dir=str(videos_dir),
                    dry_run=dry_run,
                    skip_wan=skip_wan
                )
                
                section_type = section.get("section_type", "content")
                if video_paths and not dry_run:
                    if section_type == "recap":
                        section["recap_video_paths"] = [f"videos/{Path(p).name}" for p in video_paths if p.endswith('.mp4')]
                    else:
                        section["content_video_path"] = f"videos/topic_{sid}.mp4"
                        section["beat_video_paths"] = [f"videos/{Path(p).name}" for p in video_paths if 'beat' in Path(p).name]
                    section["has_content_video"] = True
                
                results.append({
                    "section_id": sid,
                    "status": "success",
                    "videos": video_paths
                })
            except WanRenderError as e:
                results.append({
                    "section_id": sid,
                    "status": "error",
                    "error": str(e)
                })
            except Exception as e:
                results.append({
                    "section_id": sid,
                    "status": "error",
                    "error": str(e)
                })
        
        if not dry_run:
            with open(pres_path, "w") as f:
                json.dump(presentation, f, indent=2)
        
        return jsonify({
            "status": "success",
            "job_id": job_id,
            "results": results,
            "dry_run": dry_run,
            "skip_wan": skip_wan,
            "presentation_updated": not dry_run
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "job_id": job_id
        }), 500


@app.route("/jobs/<job_id>/regenerate_and_render", methods=["POST"])
def regenerate_and_render(job_id):
    """Regenerate render specs using updated prompts and execute renderers.
    
    POST body:
    - section_ids: List of section IDs to regenerate (required)
    - renderers: List of renderer types to regenerate ["manim", "wan", "all"] (default: ["all"])
    - execute: Whether to execute renderers after generating specs (default: true)
    - skip_wan: Skip WAN API calls during execution (default: false)
    - dry_run: Only generate specs, don't execute (default: false)
    
    This endpoint:
    1. Regenerates render specs (manim_scene_spec, video_prompts) via LLM with updated prompts
    2. Optionally executes the renderers to create actual video files
    """
    from core.llm_client_v12 import pass2_manim_renderer, pass2_video_renderer, rerender_sections_wan
    from core.renderer_executor import render_all_topics, enforce_renderer_policy
    from core.analytics import create_tracker
    
    data = request.get_json() or {}
    section_ids = data.get("section_ids", [])
    renderers = data.get("renderers", ["all"])
    execute = data.get("execute", True)
    skip_wan = data.get("skip_wan", False)
    dry_run = data.get("dry_run", False)
    
    if not section_ids:
        return jsonify({"error": "section_ids required"}), 400
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    
    pres_path = job_dir / "presentation.json"
    if not pres_path.exists():
        return jsonify({"error": "presentation.json not found"}), 400
    
    try:
        with open(pres_path, "r") as f:
            presentation = json.load(f)
        
        tracker = create_tracker(job_id)
        videos_dir = job_dir / "videos"
        videos_dir.mkdir(exist_ok=True)
        
        results = {"regenerated": [], "render_results": []}
        do_all = "all" in renderers
        do_manim = do_all or "manim" in renderers
        do_wan = do_all or "wan" in renderers
        
        for section in presentation.get("sections", []):
            sid = section.get("section_id") or section.get("id")
            if sid not in section_ids:
                continue
            
            renderer = section.get("renderer", "none")
            section_title = section.get("title", "")[:40]
            
            try:
                if renderer == "manim" and do_manim:
                    print(f"[Regenerate] Section {sid}: Regenerating manim spec...")
                    manim_result = pass2_manim_renderer(section, tracker)
                    section["manim_scene_spec"] = manim_result.get("manim_scene_spec")
                    results["regenerated"].append({
                        "section_id": sid,
                        "title": section_title,
                        "renderer": "manim",
                        "status": "success",
                        "objects": len(section.get("manim_scene_spec", {}).get("objects", [])),
                        "animations": len(section.get("manim_scene_spec", {}).get("animation_sequence", []))
                    })
                    
                elif renderer in ["video", "wan_video", "wan"] and do_wan:
                    print(f"[Regenerate] Section {sid}: Regenerating WAN video prompts...")
                    video_result = pass2_video_renderer(section, tracker)
                    section["video_prompts"] = video_result.get("video_prompts", [])
                    results["regenerated"].append({
                        "section_id": sid,
                        "title": section_title,
                        "renderer": renderer,
                        "status": "success",
                        "prompts_count": len(section.get("video_prompts", []))
                    })
                else:
                    results["regenerated"].append({
                        "section_id": sid,
                        "title": section_title,
                        "renderer": renderer,
                        "status": "skipped",
                        "reason": f"Renderer {renderer} not in requested types"
                    })
                    
            except Exception as e:
                results["regenerated"].append({
                    "section_id": sid,
                    "title": section_title,
                    "renderer": renderer,
                    "status": "error",
                    "error": str(e)
                })
        
        with open(pres_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        if execute and not dry_run:
            print(f"[Regenerate] Executing renderers for sections {section_ids}...")
            presentation = enforce_renderer_policy(presentation)
            
            rendered_videos = render_all_topics(
                presentation=presentation,
                output_dir=str(videos_dir),
                dry_run=False,
                skip_wan=skip_wan,
                output_dir_base=str(job_dir)
            )
            
            for result in rendered_videos:
                topic_id = result.get("topic_id")
                if topic_id in section_ids:
                    video_path = result.get("video_path")
                    for section in presentation.get("sections", []):
                        if section.get("section_id") == topic_id:
                            if video_path:
                                rel_path = Path(video_path).name if "/" in str(video_path) else video_path
                                section["video_path"] = f"videos/{rel_path}"
                            break
                    
                    results["render_results"].append({
                        "section_id": topic_id,
                        "status": result.get("status"),
                        "video_path": result.get("video_path"),
                        "error": result.get("error")
                    })
            
            with open(pres_path, "w") as f:
                json.dump(presentation, f, indent=2)
        
        return jsonify({
            "status": "success",
            "job_id": job_id,
            "results": results,
            "execute": execute,
            "dry_run": dry_run,
            "skip_wan": skip_wan
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "job_id": job_id
        }), 500


@app.route("/api/v14/pipeline-info", methods=["GET"])
def get_v14_pipeline_info():
    """Return V1.4 pipeline architecture information."""
    return jsonify(get_pipeline_info())


@app.route("/api/v14/generate", methods=["POST"])
def generate_v14():
    """
    V1.4 Split Director Pipeline endpoint.
    
    Request body (JSON):
    - markdown: Markdown content to process (required)
    - subject: Subject area (default: "General Science")
    - grade: Grade level (default: "9")
    - skip_wan: If true, skips WAN video rendering (default: false) 
    - tts_provider: TTS provider - "narakeet" (production), "pyttsx3" (dry run local), "estimate" (default: "narakeet")
    
    Returns:
    - presentation.json following v1.3 schema with spec_version v1.4
    - analytics data including token usage and timing
    - validation results
    """
    try:
        if False: # is_job_running():
            current_id = get_current_job_ids()
            return jsonify({
                "status": "busy",
                "message": "A job is already running. Please wait for it to complete.",
                "current_job_id": current_id
            }), 409
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400
        
        markdown_content = data.get("markdown", "")
        if not markdown_content:
            return jsonify({"error": "markdown field is required"}), 400
        
        subject = data.get("subject", "General Science")
        grade = data.get("grade", "9")
        skip_wan = data.get("skip_wan", False)
        tts_provider = data.get("tts_provider", "narakeet")
        
        if tts_provider not in ["narakeet", "pyttsx3", "estimate"]:
            return jsonify({"error": f"Invalid tts_provider: {tts_provider}. Use 'narakeet', 'pyttsx3', or 'estimate'"}), 400
        
        job_id = job_manager.create_job("v14_pipeline", {
            "subject": subject,
            "grade": grade,
            "skip_wan": skip_wan,
            "tts_provider": tts_provider,
            "content_preview": markdown_content[:200] + "..." if len(markdown_content) > 200 else markdown_content
        })
        
        job_output_dir = JOBS_DIR / job_id
        setup_job_folder(job_output_dir)
        
        def status_callback(jid, phase, message):
            job_manager.update_job(jid, {
                "current_phase_key": phase,
                "status_message": message
            }, persist=True)
        
        generate_tts = tts_provider != "estimate"
        
        presentation, tracker = process_markdown_to_presentation_v14(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            job_id=job_id,
            update_status_callback=status_callback,
            generate_tts=generate_tts,
            output_dir=job_output_dir,
            tts_provider=tts_provider
        )
        
        validation = validate_presentation_v14(presentation)
        
        if not validation.get("has_errors"):
            status_callback(job_id, "renderers", "Generating video content...")
            presentation = process_with_renderers_v14(
                presentation=presentation,
                tracker=tracker,
                job_id=job_id,
                update_status_callback=status_callback,
                use_remotion=True,
                output_dir=job_output_dir,
                dry_run=False,
                skip_wan=skip_wan
            )
        
        pres_path = job_output_dir / "presentation.json"
        with open(pres_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        analytics_summary = tracker.get_summary() if hasattr(tracker, 'get_summary') else {}
        
        job_manager.update_job(job_id, {
            "status": "completed" if not validation.get("has_errors") else "failed",
            "progress": 100,
            "validation": validation
        }, persist=True)
        
        return jsonify({
            "status": "success" if not validation.get("has_errors") else "validation_failed",
            "job_id": job_id,
            "presentation": presentation,
            "validation": validation,
            "analytics": analytics_summary,
            "output_path": str(pres_path),
            "skip_wan": skip_wan,
            "tts_provider": tts_provider
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route("/api/v15/pipeline-info", methods=["GET"])
def get_v15_pipeline_info():
    """Return V1.5 pipeline architecture information."""
    return jsonify({
        "version": "1.5",
        "name": "Split Agent Architecture",
        "agents": [
            {"name": "SmartChunker", "output_fields": "5-10"},
            {"name": "SectionPlanner", "output_fields": "10"},
            {"name": "NarrationWriter", "output_fields": "5"},
            {"name": "VisualSpecArtist", "output_fields": "12"},
            {"name": "RendererSpecAgent", "output_fields": "variable"},
            {"name": "MemoryFlashcard", "output_fields": "5"},
            {"name": "RecapScene", "output_fields": "5"}
        ],
        "flow": [
            "SmartChunker → topics",
            "SectionPlanner(topics) → section_blueprints",
            "FOR EACH blueprint: NarrationWriter → VisualSpecArtist → RendererSpec",
            "MemoryFlashcardAgent → memory_section",
            "RecapSceneAgent → recap_section",
            "MergeStep → presentation.json",
            "TTS → audio + durations",
            "Renderers → video files"
        ],
        "improvements": [
            "5-15 fields per agent (vs 50+ in V1.4)",
            "Per-agent retries instead of full pipeline restarts",
            "Focused prompts for better quality"
        ]
    })


@app.route("/api/v15/generate", methods=["POST"])
def generate_v15():
    """
    V1.5 Split Agent Pipeline endpoint.
    
    Request body (JSON):
    - markdown: Markdown content to process (required)
    - subject: Subject area (default: "General Science")
    - grade: Grade level (default: "9")
    - skip_wan: If true, skips WAN video rendering (default: false)
    - tts_provider: TTS provider - "edge" (default, free), "narakeet", or "estimate"
    
    Returns:
    - presentation.json following v1.3 schema with spec_version v1.5
    - analytics data including per-agent token usage
    """
    try:
        if False: # is_job_running():
            current_id = get_current_job_ids()
            return jsonify({
                "status": "busy",
                "message": "A job is already running. Please wait for it to complete.",
                "current_job_id": current_id
            }), 409
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400
        
        markdown_content = data.get("markdown", "")
        if not markdown_content:
            return jsonify({"error": "markdown field is required"}), 400
        
        subject = data.get("subject", "General Science")
        grade = data.get("grade", "9")
        skip_wan = data.get("skip_wan", False)
        tts_provider = data.get("tts_provider", "edge_tts")
        
        if tts_provider not in ["narakeet", "estimate", "edge", "edge_tts", "pyttsx3"]:
            return jsonify({"error": f"Invalid tts_provider: {tts_provider}. Use 'edge_tts', 'pyttsx3', 'narakeet', or 'estimate'"}), 400
        
        if tts_provider == "edge":
            tts_provider = "edge_tts"
        
        job_id = job_manager.create_job("v15_pipeline", {
            "subject": subject,
            "grade": grade,
            "skip_wan": skip_wan,
            "tts_provider": tts_provider,
            "pipeline_version": "1.5",
            "content_preview": markdown_content[:200] + "..." if len(markdown_content) > 200 else markdown_content
        })
        
        job_manager.start_job(job_id)
        
        job_output_dir = JOBS_DIR / job_id
        setup_job_folder(job_output_dir)
        
        def status_callback(jid, phase, message):
            job_manager.update_job(jid, {
                "current_phase_key": phase,
                "status_message": message
            }, persist=True)
        
        generate_tts = tts_provider not in ["estimate"]
        
        
        # Switch to Unified Pipeline (Single LLM) - Phase 16
        from core.pipeline_unified import process_markdown_unified, PipelineUnifiedError
        
        presentation, tracker = process_markdown_unified(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            job_id=job_id,
            update_status_callback=status_callback,
            generate_tts=generate_tts,
            output_dir=job_output_dir,
            tts_provider=tts_provider,
            dry_run=False,
            skip_wan=skip_wan
        )
        
        pres_path = job_output_dir / "presentation.json"
        with open(pres_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        analytics_summary = tracker.get_summary() if hasattr(tracker, 'get_summary') else {}
        
        job_manager.update_job(job_id, {
            "status": "completed",
            "progress": 100,
            "pipeline_version": "1.5-unified"
        }, persist=True)
        
        return jsonify({
            "status": "success",
            "job_id": job_id,
            "presentation": presentation,
            "analytics": analytics_summary,
            "output_path": str(pres_path),
            "pipeline_version": "1.5-unified",
            "skip_wan": skip_wan,
            "tts_provider": tts_provider
        })
        
    except PipelineUnifiedError as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[Results] Unified Pipeline Error: {str(e)}")
        if 'job_id' in locals():
            job_manager.fail_job(job_id, str(e), phase_key=e.phase)
        return jsonify({
            "status": "error",
            "error": str(e),
            "phase": e.phase,
            "traceback": tb
        }), 500
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[V1.5 Pipeline Error] Error: {str(e)}")
        print(f"[V1.5 Pipeline Error] Traceback:\n{tb}")
        if 'job_id' in locals():
            job_manager.fail_job(job_id, str(e))
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": tb
        }), 500


@app.route("/api/v14/dry-run-test", methods=["POST"])
def dry_run_test_v14():
    """
    Dry run test for V1.4 pipeline.
    
    This endpoint runs the full pipeline but captures output without actually
    calling LLMs or TTS services. Useful for validating pipeline structure.
    
    Request body (JSON):
    - markdown: Markdown content (optional, uses sample if not provided)
    - subject: Subject area (default: "Biology")
    - grade: Grade level (default: "10")
    
    Returns:
    - Pipeline info and expected flow
    - Sample topics structure
    - Expected section structure
    """
    try:
        data = request.get_json() or {}
        
        sample_markdown = data.get("markdown") or """
# Cell Structure and Function

## Introduction
Cells are the basic building blocks of all living organisms. Understanding cell structure is fundamental to biology.

## Cell Membrane
The cell membrane is a semi-permeable barrier that controls what enters and exits the cell.
- Made of phospholipid bilayer
- Contains proteins for transport
- Maintains cell homeostasis

### Transport Mechanisms
1. **Passive Transport**: Movement without energy (diffusion, osmosis)
2. **Active Transport**: Requires ATP energy

## Example: Red Blood Cells
Red blood cells demonstrate osmosis:
- In hypotonic solution: cells swell and burst
- In hypertonic solution: cells shrink
- In isotonic solution: cells remain normal

## Summary
Cells are complex structures with specialized components working together to maintain life.
"""
        
        subject = data.get("subject", "Biology")
        grade = data.get("grade", "10")
        
        pipeline_info = get_pipeline_info()
        
        expected_topics = {
            "source_topic": "Cell Structure and Function",
            "topics": [
                {
                    "topic_id": "t1",
                    "title": "Cell Membrane",
                    "concept_type": "definition",
                    "has_formula": False,
                    "suggested_renderer": "video"
                },
                {
                    "topic_id": "t2", 
                    "title": "Transport Mechanisms",
                    "concept_type": "process",
                    "has_formula": False,
                    "suggested_renderer": "video"
                },
                {
                    "topic_id": "t3",
                    "title": "Red Blood Cells Osmosis",
                    "concept_type": "example",
                    "has_formula": False,
                    "suggested_renderer": "video"
                }
            ]
        }
        
        expected_sections = {
            "from_content_director": ["intro", "summary", "content", "example", "quiz"],
            "from_recap_director": ["memory", "recap"],
            "merge_result_order": ["intro", "summary", "content", "example", "quiz", "memory", "recap"]
        }
        
        validation_criteria = {
            "memory": {
                "flashcard_count": 5,
                "mnemonic_style": "R-A-S letters"
            },
            "recap": {
                "video_prompt_count": 5,
                "per_prompt_min_words": 300,
                "total_narration_words": "300-500",
                "avatar": "MUST be hidden"
            }
        }
        
        return jsonify({
            "status": "dry_run_complete",
            "pipeline_version": pipeline_info["version"],
            "pipeline_architecture": pipeline_info["architecture"],
            "passes": pipeline_info["passes"],
            "models": pipeline_info["models"],
            "retry_strategy": pipeline_info["retry_strategy"],
            "test_input": {
                "subject": subject,
                "grade": grade,
                "markdown_length": len(sample_markdown),
                "markdown_preview": sample_markdown[:300] + "..."
            },
            "expected_output": {
                "topics": expected_topics,
                "sections": expected_sections,
                "validation_criteria": validation_criteria
            },
            "next_steps": [
                "Use /api/v14/generate with actual markdown to run full pipeline",
                "Set skip_tts=true to avoid Narakeet costs during testing",
                "Set dry_run=true for fastest iteration"
            ]
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route("/dashboard")
@app.route("/dashboard/")
def serve_dashboard():
    return send_from_directory(PLAYER_DIR, "dashboard.html")

@app.route("/player/")
@app.route("/player/<path:filename>")
def serve_player(filename="index.html"):
    return send_from_directory(PLAYER_DIR, filename)

@app.route("/player_v2/")
@app.route("/player_v2/<path:filename>")
def serve_player_v2(filename=None):
    # If accessing /player_v2/ or /player_v2/?job=xxx, serve player_v2.html
    if filename is None or filename == "":
        return send_from_directory(PLAYER_DIR, "player_v2.html")
    return send_from_directory(PLAYER_DIR, filename)

# --- Remotion V2 Player Routes ---

@app.route("/player/assets/<path:filename>")
def serve_assets(filename):
    return send_from_directory(ASSETS_DIR, filename)

@app.route("/player/jobs/<job_id>/")
def serve_job_player_old(job_id):
    """Legacy route - redirect to new structure"""
    return redirect(f"/jobs/{job_id}/")

@app.route("/jobs/<job_id>/")
def serve_job_player(job_id):
    """Serve job-specific player with all assets in one folder"""
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found"}), 404
    # Serve index.html from job folder (copied during job creation)
    if (job_dir / "index.html").exists():
        return send_from_directory(job_dir, "index.html")
    # Fallback to main player if not copied yet
    return send_from_directory(PLAYER_DIR, "index.html")

@app.route("/jobs/<job_id>/<path:filename>")
def serve_job_assets(job_id, filename):
    """Serve all job assets from job folder"""
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found"}), 404
    # Check if file exists in job folder
    if (job_dir / filename).exists():
        return send_from_directory(job_dir, filename)
    # Fallback to main player folder for shared assets
    if (PLAYER_DIR / filename).exists():
        return send_from_directory(PLAYER_DIR, filename)
    return jsonify({"error": "File not found"}), 404

# --- Avatar Generation Endpoints ---

@app.route("/job/<job_id>/generate_avatar", methods=["POST"])
def generate_avatar(job_id):
    """Trigger AI Avatar generation for a job."""
    print(f"[AVATAR] Received request to generate for Job {job_id}", flush=True)
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found"}), 404
        
    # Check if already running in memory
    if job_id in ACTIVE_AVATAR_JOBS:
        return jsonify({"status": "already_running", "message": "Avatar generation in progress (Active Thread)"}), 409
            
    # Start async task
    ACTIVE_AVATAR_JOBS.add(job_id)
    thread = Thread(target=run_avatar_sequential_task, args=(job_id, str(JOBS_DIR)))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "queued", "message": "Avatar generation started"})

@app.route("/job/<job_id>/avatar_status", methods=["GET"])
def get_avatar_status(job_id):
    """Get AI Avatar generation status."""
    job_dir = JOBS_DIR / job_id
    status_file = job_dir / "avatar_status.json"
    
    if not status_file.exists():
        # If it doesn't exist, it's either an old dead job or not started. 
        # Return 404 to signal the client to STOP polling.
        return jsonify({"state": "not_found", "message": "Job status not found or expired"}), 404
        
    try:
        return jsonify(json.loads(status_file.read_text()))
    except Exception as e:
        return jsonify({"state": "error", "error": str(e)}), 500

@app.route("/job/<job_id>/regenerate_failed_avatars", methods=["POST"])
def regenerate_failed_avatars(job_id):
    """Regenerate only the avatars that previously failed or are missing."""
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found"}), 404
        
    # Check if already running in memory
    if job_id in ACTIVE_AVATAR_JOBS:
        return jsonify({"status": "already_running", "message": "Avatar generation in progress"}), 409
            
    # Parse failed sections from status file if it exists
    status_file = job_dir / "avatar_status.json"
    failed_sections = None
    if status_file.exists():
        try:
            status_data = json.loads(status_file.read_text())
            failed_sections = status_data.get("details", {}).get("failed_sections", [])
        except: pass
        
    # Start async task with force=True for the specified sections
    ACTIVE_AVATAR_JOBS.add(job_id)
    thread = Thread(target=run_avatar_sequential_task, args=(job_id, str(JOBS_DIR), failed_sections, True))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "queued", "message": "Avatar retry started", "failed_sections_detected": failed_sections})

@app.route("/job/<job_id>/regenerate_avatar/<section_id>", methods=["POST"])
def regenerate_section_avatar(job_id, section_id):
    """Regenerate avatar for a specific section (force overwrite)."""
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found"}), 404
        
    if job_id in ACTIVE_AVATAR_JOBS:
        return jsonify({"status": "already_running", "message": "Avatar generation in progress"}), 409
    
    ACTIVE_AVATAR_JOBS.add(job_id)
    thread = Thread(target=run_avatar_sequential_task, args=(job_id, str(JOBS_DIR), [section_id], True))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "queued", "section_id": section_id})

def run_avatar_generation_task(job_id, jobs_root):
    """
    Background worker to handle avatar generation workflow:
    1. Read presentation.json
    2. Iterate sections -> Preprocess text -> Submit to API
    3. Poll status until complete
    4. Download videos
    5. Update presentation.json
    """
    from core.agents.avatar_generator import AvatarGenerator
    import time
    
    print(f"[DEBUG] Starting avatar task for job {job_id} in {jobs_root}", flush=True)
    job_dir = Path(jobs_root) / job_id
    status_file = job_dir / "avatar_status.json"
    presentation_file = job_dir / "presentation.json"
    avatar_dir = job_dir / "avatars"
    
    try:
        os.makedirs(avatar_dir, exist_ok=True)
        print(f"[DEBUG] Avatar dir created at {avatar_dir}", flush=True)
    except Exception as e:
        print(f"[ERROR] Failed to create avatar dir: {e}", flush=True)
        return

    def update_status(state, message, progress=0, details=None):
        print(f"[DEBUG] Status Update: {state} - {message}", flush=True)
        data = {
            "state": state,
            "message": message,
            "progress": progress,
            "updated_at": time.time(),
            "details": details or {}
        }
        try:
            with open(status_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
             print(f"[ERROR] Failed to write status file {status_file}: {e}", flush=True)

    try:
        if not presentation_file.exists():
            print(f"[ERROR] Presentation file not found at {presentation_file}", flush=True)
            update_status("failed", "presentation.json not found")
            return
            
        update_status("processing", "Initializing generator...", 5)
        
        with open(presentation_file, "r") as f:
            presentation = json.load(f)
            
        generator = AvatarGenerator()
        tasks = []
        failed_tasks = []
        
        # Initialize Analytics Tracker
        from core.analytics import create_tracker
        tracker = create_tracker(job_id)
        analytics_file = job_dir / "analytics.json"
        tracker.load_from_file(str(analytics_file))
        
        avatar_overall_start = time.time()
        submission_times = {}
        sections = presentation.get("sections", [])
        total_sections = len(sections)
        
        update_status("processing", "Checking sections for avatar generation...", 10)
        
        # Use shared helper for consistency
        results = generator.submit_parallel_job(presentation, job_id, str(JOBS_DIR / job_id))
        
        queued = len(results["queued"])
        skipped = len(results["skipped"])
        failed = len(results["failed"])
        
        # Add to tracking
        for item in results["queued"]:
            tasks.append({
                "section_id": item["section_id"],
                "task_id": item["task_id"],
                "status": "queued"
            })
            submission_times[ item["task_id"] ] = time.time()
            
        # Add failed to tracking
        for item in results["failed"]:
            failed_tasks.append({
                "section_id": item["section_id"],
                "task_id": "failed",
                "status": "failed_submit",
                "error": item.get("error", "Unknown")
            })
            
        if not tasks:
            update_status("completed", f"Done. (Queued: {queued}, Skipped: {skipped}, Failed: {failed})", 100)
            return

        # 2. Poll & Download
        active_tasks = list(tasks)
        completed_tasks = []
        failed_tasks = []
        start_time = time.time()
        
        while active_tasks:
            still_active = []
            
            # Calculate overall progress
            total_count = len(tasks)
            success_count = len(completed_tasks)
            error_count = len(failed_tasks)
            done_count = success_count + error_count
            
            base_progress = 30 + (done_count / total_count) * 60
            
            status_msg = f"Progress: {done_count}/{total_count} processed ({success_count} ready, {error_count} failed)"
            if active_tasks:
                status_msg += f" - {len(active_tasks)} still active..."
            
            details = {
                "success": [t["section_id"] for t in completed_tasks],
                "failed": [t["section_id"] for t in failed_tasks],
                "active": [t["section_id"] for t in active_tasks]
            }
            
            update_status("processing", status_msg, base_progress, details=details)
            
            for task in active_tasks:
                task_id = task["task_id"]
                section_id = task["section_id"]
                
                # Check API
                try:
                    status_res = generator.check_status(task_id)
                    api_status = status_res.get("status")
                    if api_status != "completed":
                        print(f"[AVATAR] Task {task_id} (Sec {section_id}) status: {api_status}", flush=True)
                except Exception as e:
                    print(f"[ERROR] Status check failed for task {task_id}: {e}", flush=True)
                    api_status = "error_check"
                
                if api_status == "completed":
                    # Download
                    output_filename = f"section_{section_id}_avatar.mp4"
                    output_path = avatar_dir / output_filename
                    
                    if generator.download_video(task_id, str(output_path)):
                        task["status"] = "downloaded"
                        task["local_path"] = f"avatars/{output_filename}"
                        completed_tasks.append(task)
                        
                        # Track Analytics Detail
                        duration = time.time() - submission_times.get(task_id, time.time())
                        tracker.add_avatar_detail(str(section_id), duration, "success")
                        
                        # Update presentation.json immediately
                        for sec in presentation["sections"]:
                            if sec["section_id"] == section_id:
                                sec["avatar_video"] = task["local_path"]
                                sec["avatar_task_id"] = task_id
                                break
                        with open(presentation_file, "w") as f:
                            json.dump(presentation, f, indent=2)
                    else:
                        task["status"] = "failed_download"
                        failed_tasks.append(task)
                        tracker.add_avatar_detail(str(section_id), 0, "failed_download")
                        
                elif api_status == "failed":
                    task["status"] = "failed_api"
                    failed_tasks.append(task)
                    tracker.add_avatar_detail(str(section_id), 0, "failed_api", error=status_res.get("error"))
                elif api_status == "error_check":
                    # Potentially transient, but let's count attempts or just keep active?
                    # For now, keep it active to retry check
                    still_active.append(task)
                else:
                    still_active.append(task)
            
            active_tasks = still_active
            time.sleep(5) # Poll interval
            
            if time.time() - start_time > 1800: # 30 min timeout
                update_status("failed", "Timeout waiting for avatar generation", details=details)
                return

        final_msg = f"Completed: {len(completed_tasks)} successes, {len(failed_tasks)} failures"
        update_status("completed", final_msg, 100, details={
            "success": [t["section_id"] for t in completed_tasks],
            "failed": [t["section_id"] for t in failed_tasks]
        })

        # Save Final Analytics
        tracker.set_avatar_metrics(
            total_sections=total_sections,
            successful=len(completed_tasks),
            failed=len(failed_tasks),
            duration=time.time() - avatar_overall_start
        )
        tracker.save_to_file(str(analytics_file))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        update_status("failed", f"Internal error: {str(e)}")
        print(f"[AVATAR-SEQ] Fatal error: {e}", flush=True)
        update_status("failed", str(e))
    finally:
        ACTIVE_AVATAR_JOBS.discard(job_id)
def run_avatar_sequential_task(job_id, jobs_root, target_sections=None, force=False):
    """
    Background worker to handle avatar generation:
    Now uses the refactored 'Submit All' strategy from AvatarGenerator.
    """
    from core.agents.avatar_generator import AvatarGenerator
    import time
    
    print(f"[AVATAR-TASK] Initiating generation for job {job_id}", flush=True)
    job_dir = Path(jobs_root) / job_id
    presentation_file = job_dir / "presentation.json"
    
    try:
        if not presentation_file.exists():
            print(f"[AVATAR-TASK] Error: presentation.json not found for {job_id}")
            return
            
        with open(presentation_file, "r") as f:
            presentation = json.load(f)
            
        generator = AvatarGenerator()
        
        # Use the new high-performance "Submit All" method
        # This handles its own persistence, polling (30s), and Vimeo metadata
        generator.submit_all_jobs(
            presentation=presentation,
            job_id=job_id,
            output_dir=str(job_dir),
            target_sections=target_sections,
            force=force
        )
        
        print(f"[AVATAR-TASK] Background task completed for job {job_id}")
        
    except Exception as e:
        print(f"[AVATAR-TASK] Fatal error: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        if job_id in ACTIVE_AVATAR_JOBS:
            ACTIVE_AVATAR_JOBS.remove(job_id)


@app.route("/api/repair-metadata/<job_id>", methods=["POST"])
def repair_metadata(job_id):
    """
    Surgically repair presentation.json by scanning for orphaned assets.
    """
    from core.locks import presentation_lock, analytics_lock
    
    job_dir = JOBS_DIR / job_id
    pres_path = job_dir / "presentation.json"
    video_dir = job_dir / "videos"
    avatar_dir = job_dir / "avatars"
    
    if not pres_path.exists():
        return jsonify({"error": "Job presentation.json not found"}), 404
        
    try:
        with presentation_lock:
            with open(pres_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Scan directories
            found_videos = []
            if video_dir.exists():
                found_videos = [f.name for f in video_dir.iterdir() if f.is_file() and f.suffix == ".mp4"]
                
            found_avatars = []
            if avatar_dir.exists():
                found_avatars = [f.name for f in avatar_dir.iterdir() if f.is_file() and f.suffix == ".mp4"]
                
            updated_count = 0
            # 1. Update Sections
            for section in data.get("sections", []):
                sid = str(section.get("section_id"))
                
                # Check for topic videos or beats (V2.5 WAN patterns)
                topic_v = f"topic_{sid}.mp4"
                topic_beat_0 = f"topic_{sid}_beat_0.mp4"
                
                # CRITICAL: Treat /jobs/... absolute paths as INVALID - must normalize to relative
                current_video_path = section.get("video_path", "")
                video_needs_update = (
                    not current_video_path or 
                    current_video_path.startswith("/jobs/") or
                    "placeholder" in current_video_path
                )
                
                if topic_v in found_videos and video_needs_update:
                    section["video_path"] = f"videos/{topic_v}"
                    updated_count += 1
                elif topic_beat_0 in found_videos and video_needs_update:
                    # Found beat 0 but no main path - stitch as a multi-beat section
                    beats = sorted([v for v in found_videos if v.startswith(f"topic_{sid}_beat_")])
                    section["video_path"] = f"videos/{topic_beat_0}"
                    section["beat_videos"] = [f"videos/{b}" for b in beats]
                    
                    # For content/example, also attempt to repopulate visual_beats
                    if section.get("section_type") in ["content", "example"]:
                        v_beats = section.get("visual_beats", [])
                        for i, b_path in enumerate(beats):
                            if i < len(v_beats):
                                v_beats[i]["video_asset"] = f"videos/{b_path}"
                        section["visual_beats"] = v_beats
                        
                    updated_count += 1
                
                # Check for recap-specific paths if still missing or using wrong /jobs/... format
                recap_video_paths = section.get("recap_video_paths", [])
                recap_needs_update = (
                    not recap_video_paths or 
                    any(p.startswith("/jobs/") for p in recap_video_paths if p)
                )
                if section.get("section_type") == "recap" and recap_needs_update:
                    beats = sorted([v for v in found_videos if v.startswith(f"topic_{sid}_beat_")])
                    if beats:
                        section["recap_video_paths"] = [f"videos/{b}" for b in beats]
                        # Also update video_path if missing or using absolute format
                        current_vp = section.get("video_path", "")
                        if not current_vp or current_vp.startswith("/jobs/"):
                            section["video_path"] = f"videos/{beats[0]}"
                        updated_count += 1
                
                # Check for avatars
                # Format section_1_avatar.mp4 or section_1.mp4? Let's check both patterns
                avatar_patterns = [f"section_{sid}_avatar.mp4", f"section_{sid}.mp4"]
                for p in avatar_patterns:
                    if p in found_avatars:
                        current_path = section.get("avatar_video", "")
                        
                        # SCENARIO MATCH:
                        # 1. current_path is empty (None/"") or missing
                        # 2. current_path is a placeholder
                        # 3. current_path points to a file that DOES NOT EXIST (broken link)
                        
                        current_file_valid = False
                        if current_path and "placeholder" not in current_path:
                             # CRITICAL: If path uses absolute /jobs/... format, it's INVALID
                             # We MUST normalize to relative "avatars/..." format
                             if current_path.startswith("/jobs/"):
                                 # Force update - absolute paths are always wrong
                                 current_file_valid = False
                             else:
                                 # Check if relative path points to existing file
                                 full_check_path = job_dir / current_path.lstrip("/")
                                 current_file_valid = full_check_path.exists()

                        if not current_file_valid:
                            section["avatar_video"] = f"avatars/{p}"
                            section["avatar_status"] = "completed"
                            updated_count += 1
                            break
            
            if updated_count > 0:
                with open(pres_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                    
        return jsonify({
            "status": "success",
            "updated_assets": updated_count,
            "message": f"Successfully stitched {updated_count} assets back into metadata."
        })
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == "__main__":
    # Pre-flight check for LLM access
    try:
        from core.llm_config import validate_model_access
        is_valid, msg = validate_model_access()
        if is_valid:
            print(f"✅ LLM Pre-flight check passed: {msg}")
        else:
            print(f"⚠️ LLM Pre-flight check FAILED: {msg}")
            # We don't exit to allow the app to start and show dashboard, but logs will show the issue
    except ImportError:
        print("⚠️ Could not import validation module")
        
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

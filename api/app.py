import os
import sys
import json
import shutil
import time
import tempfile
import logging
import uuid
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables from .env file
# Load environment variables from .env file (Force override to ensure correct key)
load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request, jsonify, send_from_directory, redirect, make_response
from flask_cors import CORS

from core.pipeline import process_pdf_to_videos
from core.pipeline_v12 import (
    process_markdown_to_videos_v12 as process_markdown_to_videos,
)
from core.pipeline_v14 import (
    get_pipeline_info,
    process_markdown_to_presentation_v14,
    process_with_renderers_v14,
    validate_presentation_v14,
)
from core.pipeline_v15 import (
    process_markdown_to_presentation_v15,
    resume_from_section,
    PipelineError as PipelineV15Error,
)
from core.pipeline_v15_optimized import process_markdown_optimized
from core.unified_content_generator import (
    generate_presentation,
    transform_to_player_schema,
    GeneratorConfig,
)
from core.job_manager import (
    job_manager,
    run_job_async,
    is_job_running,
    get_current_job_ids,
)
from core.locks import presentation_lock, analytics_lock  # Thread-safe JSON writes

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
# Apply to werkzeug and root loggers to be sure
logging.getLogger("werkzeug").setLevel(logging.ERROR)
logging.getLogger("werkzeug").addFilter(PollingLogFilter())
logging.getLogger("flask.app").addFilter(PollingLogFilter())

# ADDED: File Logging for Admin Panel
try:
    file_handler = logging.FileHandler("app.log", encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logging.getLogger().addHandler(file_handler)
    logging.getLogger().setLevel(logging.INFO)
except Exception as e:
    print(f"Failed to setup file logging: {e}")

# Module logger for app.py
logger = logging.getLogger(__name__)

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


def setup_job_folder(job_output_dir: Path, pipeline_version: str = ""):
    """Copy player files to job folder for self-contained playback"""
    os.makedirs(job_output_dir / "videos", exist_ok=True)
    os.makedirs(job_output_dir / "audio", exist_ok=True)
    # Copy player_v2 files for self-contained job
    file_mappings = [
        ("player_v2.html", "index.html"),
        ("player_v2.js", "player_v2.js"),
        ("player_v2.css", "player_v2.css"),
    ]
    for src_name, dst_name in file_mappings:
        src = PLAYER_DIR / src_name
        dst = job_output_dir / dst_name
        if src.exists() and not dst.exists():
            shutil.copy(str(src), str(dst))
    # V3: always overwrite player_v3.html so latest fixes are present
    if pipeline_version == "v3":
        v3_src = PLAYER_DIR / "player_v3.html"
        v3_dst = job_output_dir / "player_v3.html"
        if v3_src.exists():
            shutil.copy(str(v3_src), str(v3_dst))
            logger.info(f"[V3] Synced player_v3.html to {v3_dst}")


@app.route("/sanity_check.html")
def serve_sanity_check():
    return send_from_directory(PLAYER_DIR, "sanity_check.html")


@app.route("/")
def index():
    return redirect("/dashboard")


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify(
        {
            "status": "healthy",
            "service": "ai-animated-education-phase1",
            "version": "1.4.0",
            "features": [
                "job_mode",
                "pdf",
                "markdown",
                "v14_pipeline",
                "split_director",
            ],
        }
    )


@app.route("/submit_review", methods=["POST"])
def submit_review_endpoint():
    """
    Submit a review for a specific job section.
    Saves the review to a reviews.json file in the job directory.
    """
    try:
        data = request.json
        job_id = data.get("job_id")
        section_id = data.get("section_id")
        review_text = data.get("review")
        rating = data.get("rating")  # Optional

        if not job_id or not section_id or not review_text:
            return jsonify({"error": "Missing job_id, section_id, or review text"}), 400

        job_dir = JOBS_DIR / job_id
        if not job_dir.exists():
            return jsonify({"error": "Job not found"}), 404

        reviews_path = job_dir / "reviews.json"
        reviews = []
        if reviews_path.exists():
            try:
                with open(reviews_path, "r", encoding="utf-8") as f:
                    reviews = json.load(f)
            except json.JSONDecodeError:
                pass  # Start fresh if corrupt

        # Check if review for this section already exists, update if so
        existing_review_index = next(
            (i for i, r in enumerate(reviews) if r["section_id"] == section_id), -1
        )

        new_review = {
            "section_id": section_id,
            "review": review_text,
            "rating": rating,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }

        if existing_review_index != -1:
            reviews[existing_review_index] = new_review
        else:
            reviews.append(new_review)

        with open(reviews_path, "w", encoding="utf-8") as f:
            json.dump(reviews, f, indent=2)

        return jsonify(
            {"status": "success", "message": "Review saved", "reviews": reviews}
        )

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# Read-only variant of repair_metadata - for sanity checker UI
@app.route("/api/sanity-report/<job_id>", methods=["GET"])
def sanity_report(job_id):
    """
    Returns comprehensive truth report about job assets (READ-ONLY).
    Scans disk vs JSON and returns detailed diff without modifying anything.
    """
    try:
        job_dir = JOBS_DIR / job_id
        pres_path = job_dir / "presentation.json"
        video_dir = job_dir / "videos"
        avatar_dir = job_dir / "avatars"
        images_dir = job_dir / "images"

        if not pres_path.exists():
            return jsonify({"error": "Job presentation.json not found"}), 404

        # Load presentation.json
        with open(pres_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Scan directories
        found_videos = []
        if video_dir.exists():
            found_videos = [
                f.name
                for f in video_dir.iterdir()
                if f.is_file() and f.suffix == ".mp4"
            ]

        found_avatars = []
        if avatar_dir.exists():
            found_avatars = [
                f.name
                for f in avatar_dir.iterdir()
                if f.is_file() and f.suffix == ".mp4"
            ]

        found_images = []
        if images_dir.exists():
            found_images = [
                f.name
                for f in images_dir.iterdir()
                if f.is_file() and f.suffix in [".png", ".jpg", ".jpeg"]
            ]

        # Extract all references from JSON
        json_videos = set()
        json_avatars = set()
        json_images = set()
        section_details = []

        for section in data.get("sections", []):
            sid = str(section.get("section_id"))
            section_info = {
                "section_id": sid,
                "section_type": section.get("section_type"),
                "title": section.get("title"),
                "renderer": section.get("renderer"),
                "videos_on_disk": [],
                "videos_in_json": [],
                "videos_orphaned": [],
                "videos_missing": [],
                "avatar_status": "unknown",
                "segments_with_beats": 0,
                "total_beat_videos": 0,
            }

            def _register_video(path):
                if not path:
                    return
                fname = Path(path).name
                if fname and fname not in section_info["videos_in_json"]:
                    json_videos.add(fname)
                    section_info["videos_in_json"].append(fname)

            # ── section-level video_path ──────────────────────────────────────────
            _register_video(section.get("video_path"))

            # ── beat_video_paths[] (V3 flat list on section) ──────────────────────
            for vp in section.get("beat_video_paths", []):
                _register_video(vp)

            # ── beat_videos[] (older flat list) ───────────────────────────────────
            for bv in section.get("beat_videos", []):
                _register_video(bv)

            # ── visual_beats[].video_path (V3 primary format) ────────────────────
            for beat in section.get("visual_beats", []):
                _register_video(beat.get("video_path"))

            # ── narration.segments[].beat_videos + .video_path ───────────────────
            narration = section.get("narration", {})
            segments = narration.get("segments", [])
            for seg in segments:
                _register_video(seg.get("video_path"))
                for sbv in seg.get("beat_videos", []):
                    _register_video(sbv)
                    section_info["segments_with_beats"] += 1
                    section_info["total_beat_videos"] += 1

            # ── render_spec image_to_video_beats ─────────────────────────────────
            render_spec = section.get("render_spec", {})
            for b in render_spec.get("image_to_video_beats", []):
                _register_video(b.get("video_path"))

            # ── recap_video_paths[] ───────────────────────────────────────────────
            for rp in section.get("recap_video_paths", []):
                _register_video(rp)

            # ── explanation_plan.visual_beats[].video_path ────────────────────────
            for beat in section.get("explanation_plan", {}).get("visual_beats", []):
                _register_video(beat.get("video_path"))

            # ── understanding_quiz & questions[]: explanation_visual paths ─────────
            def _register_explanation_visual(quiz_obj):
                if not quiz_obj:
                    return
                _register_video(quiz_obj.get("explanation_visual_video_path"))
                ev = quiz_obj.get("explanation_visual") or {}
                _register_video(ev.get("video_path"))
                for vp in ev.get("beat_video_paths", []):
                    _register_video(vp)
                for b in ev.get("image_to_video_beats", []):
                    _register_video(b.get("video_path"))

            _register_explanation_visual(section.get("understanding_quiz"))
            for q in section.get("questions", []):
                _register_explanation_visual(q)

            # ── video_prompts (legacy) ────────────────────────────────────────────
            video_prompts = section.get("video_prompts") or render_spec.get("video_prompts", [])

            # Check avatar
            avatar_path = section.get("avatar_video", "")
            if avatar_path:
                filename = Path(avatar_path).name
                json_avatars.add(filename)
                if filename in found_avatars:
                    section_info["avatar_status"] = "found"
                else:
                    section_info["avatar_status"] = "missing"
            else:
                section_info["avatar_status"] = "not_referenced"

            # Find videos on disk for this section
            section_video_pattern = f"topic_{sid}"
            section_videos_on_disk = [
                v for v in found_videos if v.startswith(section_video_pattern)
            ]
            section_info["videos_on_disk"] = section_videos_on_disk

            # Determine orphaned vs missing
            for vod in section_videos_on_disk:
                if vod not in section_info["videos_in_json"]:
                    section_info["videos_orphaned"].append(vod)

            for vij in section_info["videos_in_json"]:
                if vij not in found_videos:
                    section_info["videos_missing"].append(vij)

            section_details.append(section_info)

        # Global orphaned/missing files
        orphaned_videos = [v for v in found_videos if v not in json_videos]
        missing_videos = [v for v in json_videos if v not in found_videos]

        orphaned_avatars = [a for a in found_avatars if a not in json_avatars]
        missing_avatars = [a for a in json_avatars if a not in found_avatars]

        # Calculate accuracy
        total_on_disk = len(found_videos) + len(found_avatars)
        total_referenced = len(json_videos) + len(json_avatars)
        matched = len(json_videos & set(found_videos)) + len(
            json_avatars & set(found_avatars)
        )

        accuracy = 100.0
        if total_referenced > 0:
            accuracy = (matched / total_referenced) * 100

        return jsonify(
            {
                "job_id": job_id,
                "accuracy": round(accuracy, 2),
                "summary": {
                    "videos_on_disk": len(found_videos),
                    "videos_in_json": len(json_videos),
                    "avatars_on_disk": len(found_avatars),
                    "avatars_in_json": len(json_avatars),
                    "images_on_disk": len(found_images),
                    "orphaned_videos": len(orphaned_videos),
                    "missing_videos": len(missing_videos),
                    "matched_videos": len(json_videos & set(found_videos)),
                },
                "orphaned": {"videos": orphaned_videos, "avatars": orphaned_avatars},
                "missing": {"videos": missing_videos, "avatars": missing_avatars},
                "sections": section_details,
            }
        )

    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/recreate_job_from_review", methods=["POST"])
def recreate_job_from_review():
    """
    Trigger regeneration of a job (or specific sections) based on submitted reviews.
    Currently, this is a stub that acknowledges the request.
    Real implementation would parse reviews and adjust generation parameters.
    """
    try:
        data = request.json
        job_id = data.get("job_id")

        if not job_id:
            return jsonify({"error": "Missing job_id"}), 400

        job_dir = JOBS_DIR / job_id
        reviews_path = job_dir / "reviews.json"

        if not reviews_path.exists():
            return jsonify({"error": "No reviews found for this job"}), 400

        # TODO: Implement actual regeneration logic using the reviews.
        # For now, we will just return a success message simulating the start of the process.
        # Ideally this would call something like `job_manager.create_job(..., parent_job_id=job_id, ...)`

        print(f"[Review] Triggering regeneration for Job {job_id} based on reviews.")

        return jsonify(
            {
                "status": "accepted",
                "message": "Regeneration based on reviews initiated (Stub)",
                "job_id": job_id,
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/regenerate_manim/<job_id>", methods=["POST"])
def regenerate_manim(job_id):
    """
    Regenerate Manim code for all manim sections in a job.
    Uses the V2.5 Director data mapping fix.

    POST body (optional):
    - user_feedback: String with user's improvement requests (optional)
    - section_id: Specific section to regenerate (optional, regenerates all if not provided)
    """
    from core.agents.manim_code_generator import (
        ManimCodeGenerator,
        integrate_manim_code_into_section,
    )

    job_dir = JOBS_DIR / job_id
    pres_path = job_dir / "presentation.json"

    if not pres_path.exists():
        return jsonify({"error": "Job not found"}), 404

    try:
        # Get optional parameters from request body
        data = request.get_json() or {}
        user_feedback = data.get("user_feedback", "")
        target_section_id = data.get("section_id")

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

            # If target_section_id specified, only regenerate that section
            if target_section_id and section_id != target_section_id:
                results["skipped"].append(
                    {"section_id": section_id, "reason": "Not the target section"}
                )
                continue

            # Transform V2.5 Director data (same as pipeline fix)
            nar = section.get("narration", {})
            segments = nar.get("segments", [])

            render_spec = section.get("render_spec", {})
            manim_spec_from_director = render_spec.get("manim_scene_spec")
            if isinstance(manim_spec_from_director, dict):
                manim_spec_from_director = manim_spec_from_director.get(
                    "description", ""
                )

            section_data = {
                "section_title": section.get("title", "Section"),
                "narration_segments": segments,
                "manim_spec": manim_spec_from_director
                or section.get("explanation_plan", ""),
                "visual_description": "",
                "formulas": [],
                "key_terms": [],
            }

            # FEATURE: Inject user feedback if provided
            if user_feedback:
                section_data["user_feedback"] = user_feedback
                print(f"[Manim Regen] Applying user feedback to section {section_id}")

            try:
                code = manim_gen.generate_code(
                    section_data, style_config={"style": "standard"}
                )

                if not code or len(code) < 100:
                    results["failed"].append(
                        {"section_id": section_id, "error": "Generated code too short"}
                    )
                    continue

                # Save to file
                manim_code_dir = job_dir / "manim_code"
                manim_code_dir.mkdir(exist_ok=True)
                code_file = manim_code_dir / f"section_{section_id}.py"

                with open(code_file, "w", encoding="utf-8") as f:
                    f.write(code)

                # Update presentation.json
                integrate_manim_code_into_section(section, code)

                results["generated"].append(
                    {
                        "section_id": section_id,
                        "title": section.get("title"),
                        "code_length": len(code),
                        "segments": len(segments),
                        "user_feedback_applied": bool(user_feedback),
                    }
                )

            except Exception as e:
                results["failed"].append({"section_id": section_id, "error": str(e)})

        # Save updated presentation
        with open(pres_path, "w", encoding="utf-8") as f:
            json.dump(presentation, f, indent=4)

        return jsonify(
            {
                "status": "complete",
                "job_id": job_id,
                "user_feedback_provided": bool(user_feedback),
                "results": results,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- PREVIEW & APPROVE WORKFLOW (V2.6) ---

PREVIEW_LOCK = threading.Lock()


def _update_preview_status(job_id: str, key: str, status_data: dict):
    """Thread-safe update of preview_status.json in job directory."""
    try:
        status_path = JOBS_DIR / job_id / "preview_status.json"
        with PREVIEW_LOCK:
            current_status = {}
            if status_path.exists():
                try:
                    with open(status_path, "r") as f:
                        current_status = json.load(f)
                except:
                    pass

            # Merge or set
            if key in current_status:
                current_status[key].update(status_data)
            else:
                current_status[key] = status_data

            current_status[key]["last_updated"] = datetime.utcnow().isoformat()

            with open(status_path, "w") as f:
                json.dump(current_status, f, indent=2)
    except Exception as e:
        print(f"[Preview] Failed to update status: {e}")


def _run_preview_generation(
    job_id: str,
    section_id: str,
    beat_id: str,
    renderer: str,
    user_feedback: str,
    raw_prompt_override: str,
    image_prompt_start: str,
    image_prompt_end: str,
    preview_filename: str,
    video_provider: str = "wan",
):
    """Background task for generating preview video."""
    import traceback
    from render.wan.wan_client import WANClient
    from core.agents.manim_code_generator import ManimCodeGenerator
    from render.manim.manim_runner import render_manim_video

    preview_key = f"{section_id}_{beat_id}"
    job_dir = JOBS_DIR / job_id
    images_dir = job_dir / "images"
    os.makedirs(images_dir, exist_ok=True)
    output_path = job_dir / "videos" / preview_filename

    try:
        print(f"[Preview] Starting generation for {preview_key} ({renderer})...")
        _update_preview_status(
            job_id, preview_key, {"status": "processing", "progress": 10}
        )

        pres_path = job_dir / "presentation.json"
        if not pres_path.exists():
            raise Exception("Job presentation not found")

        with open(pres_path, "r") as f:
            data = json.load(f)

        # Find section
        section = next(
            (
                s
                for s in data.get("sections", [])
                if str(s["section_id"]) == str(section_id)
            ),
            None,
        )
        if not section:
            raise Exception(f"Section {section_id} not found")

        final_prompt_used = ""

        if renderer == "image_to_video":
            # 1. Generate Image(s)
            from render.image.image_generator import generate_image_for_beat
            try:
                from render.wan.local_gpu_client import LocalGPUClient
            except ImportError:
                LocalGPUClient = None
            
            _update_preview_status(job_id, preview_key, {"status": "processing", "progress": 15, "message": "Generating reference images..."})
            
            image_path_start_real = None
            import time
            timestamp = int(time.time())
            
            if image_prompt_start:
                print(f"[Preview] Generating START image for preview: {image_prompt_start[:50]}...")
                beat_data = {"beat_id": f"preview_start_{timestamp}", "image_prompt": image_prompt_start}
                image_path_start_real = generate_image_for_beat(beat_data, job_id, section_id, output_dir=str(job_dir))
                print(f"[Preview] START image generated: {image_path_start_real}")
            
            image_path_end_real = None
            if image_prompt_end:
                print(f"[Preview] Generating END image for preview: {image_prompt_end[:50]}...")
                beat_data_end = {"beat_id": f"preview_end_{timestamp}", "image_prompt": image_prompt_end}
                image_path_end_real = generate_image_for_beat(beat_data_end, job_id, section_id, output_dir=str(job_dir))
                print(f"[Preview] END image generated: {image_path_end_real}")
            
            if not image_path_start_real:
                raise Exception("Failed to generate start image for image_to_video")
            
            # Make sure it's absolute for LocalGPUClient
            if not Path(image_path_start_real).is_absolute():
                image_path_start_real = str(job_dir / image_path_start_real)
            if image_path_end_real and not Path(image_path_end_real).is_absolute():
                image_path_end_real = str(job_dir / image_path_end_real)
                
            _update_preview_status(job_id, preview_key, {"status": "processing", "progress": 40, "message": "Rendering video on Local GPU..."})
            
            if not LocalGPUClient:
                raise Exception("LocalGPUClient not found")
            client = LocalGPUClient()
            if not client.is_available():
                raise Exception("Local GPU is not available to render image_to_video")
                
            prompt = raw_prompt_override or user_feedback
            final_prompt_used = prompt
            result_path = client.generate_video(prompt, duration=15, output_path=str(output_path), image_path=image_path_start_real, image_path_end=image_path_end_real)
            if not result_path:
                raise Exception("Local GPU generation returned None")

        elif renderer == "text_to_video":
            from render.wan.local_gpu_client import LocalGPUClient
            _update_preview_status(job_id, preview_key, {"status": "processing", "progress": 20, "message": "Rendering text_to_video on Local GPU..."})
            client = LocalGPUClient()
            if not client.is_available():
                raise Exception("Local GPU is not available")
            prompt = raw_prompt_override or user_feedback
            final_prompt_used = prompt
            result_path = client.generate_video(prompt, duration=15, output_path=str(output_path))
            if not result_path:
                raise Exception("Local GPU generation returned None")

        elif renderer == "wan":
            # 1. Determine Prompt
            prompt = ""
            if raw_prompt_override:
                prompt = raw_prompt_override
                print(f"[Preview] Using raw prompt override: {prompt[:50]}...")
            else:
                # Use LLM to rewrite prompt based on feedback
                # For now (MVP), just append feedback or use feedback as prompt?
                # Plan said: Call KieBatchGenerator internal LLM.
                # But creating KieBatchGenerator is heavy.
                # Let's simple-append for MVP or use logic if feedback > 10 chars
                # Better: Allow user to just write the new prompt in user_feedback if they want.
                # Or if we strictly follow plan, we need the rewriter.
                # Let's fallback to "feedback IS the prompt" if raw_override is empty
                # UNLESS we implement the rewriter here.
                # Given user's request "retry with new text or prompt", let's treat user_feedback as the new prompt
                # if raw check fails, OR if user_feedback looks like a prompt.
                # Actuall, let's just use user_feedback as the prompt for simplicity V1.
                prompt = user_feedback

            final_prompt_used = prompt

            # 2. Pick client based on video_provider
            provider_label = "Local GPU" if video_provider == "gpu" else "Kie.ai WAN"
            _update_preview_status(
                job_id,
                preview_key,
                {
                    "status": "processing",
                    "progress": 20,
                    "message": f"Sending to {provider_label}...",
                },
            )

            client = None
            if video_provider == "gpu":
                try:
                    from render.wan.local_gpu_client import LocalGPUClient

                    gpu_client = LocalGPUClient()
                    if gpu_client.is_available():
                        client = gpu_client
                        print(f"[Preview] Using Local GPU client")
                    else:
                        print(
                            f"[Preview] Local GPU unavailable — falling back to Kie.ai WAN"
                        )
                except Exception as gpu_err:
                    print(
                        f"[Preview] LocalGPUClient error: {gpu_err} — falling back to WAN"
                    )
            if client is None:
                client = WANClient()
                print(f"[Preview] Using Kie.ai WAN client")

            result_path = client.generate_video(
                prompt, duration=15, output_path=str(output_path)
            )

            if not result_path:
                raise Exception(f"{provider_label} generation returned None (Failed)")

        elif renderer == "manim":
            # 1. Generate Code with Feedback
            _update_preview_status(
                job_id,
                preview_key,
                {
                    "status": "processing",
                    "progress": 20,
                    "message": "Generating Manim code...",
                },
            )

            # Prepare data
            nar = section.get("narration", {})
            all_segments = nar.get("segments", [])
            render_spec = section.get("render_spec", {})
            segment_specs = render_spec.get("segment_specs", [])

            # ── Fix C: V3-aware Manim spec resolution ──────────────────────────────
            # Two distinct paths depending on whether this is a quiz explanation beat
            # (beat_id starts with "eq_") or a main section beat (numeric / "beat_N").
            beat_is_quiz_eq = beat_id.startswith("eq_") or beat_id == "eq_main"

            segments = all_segments  # default narration context
            manim_spec = ""

            if beat_is_quiz_eq:
                # Quiz explanation_visual — the spec lives directly on the ev object
                for q_src in [section.get("understanding_quiz")] + section.get("questions", []):
                    if not q_src:
                        continue
                    ev = q_src.get("explanation_visual") or {}
                    if ev.get("renderer") == "manim":
                        manim_spec = ev.get("manim_scene_spec", "") or ev.get("display_text", "")
                        if isinstance(manim_spec, dict):
                            manim_spec = manim_spec.get("description", "")
                        # Use a single narration segment if possible
                        if all_segments:
                            segments = all_segments[:1]
                        print(f"[Preview] Fix C: quiz eq beat — manim_spec from explanation_visual (len={len(str(manim_spec))})")
                        break
            else:
                # Main section beat — try to find per-beat spec then fall back to section-level
                beat_manim_spec = ""
                try:
                    # Support both pure numeric ("0","1") and named ("beat_1","beat_2") beat IDs.
                    # visual_beats uses "beat_1" → trailing num 1 → 0-based index 0.
                    if beat_id.isdigit():
                        beat_idx = int(beat_id)
                    else:
                        import re as _re
                        m_num = _re.search(r'(\d+)$', beat_id)
                        if m_num:
                            beat_num = int(m_num.group(1))
                            # Determine if 1-based naming (beat_1 → index 0) or 0-based
                            vb_ids = [b.get("beat_id","") for b in section.get("visual_beats",[])]
                            # If "beat_0" exists → 0-based; otherwise "beat_1" is 0-based index = num-1
                            if "beat_0" in vb_ids:
                                beat_idx = beat_num          # beat_0 → 0, beat_1 → 1
                            else:
                                beat_idx = beat_num - 1      # beat_1 → 0, beat_2 → 1
                        else:
                            beat_idx = None

                    # V3 primary: select the matching visual_beat's display_text and narration segment
                    if beat_idx is not None:
                        vb = section.get("visual_beats", [])
                        if 0 <= beat_idx < len(vb):
                            beat_manim_spec = vb[beat_idx].get("display_text", "")
                            segments = [all_segments[beat_idx]] if beat_idx < len(all_segments) else all_segments
                            print(f"[Preview] Fix C: beat_id={beat_id!r} → beat_idx={beat_idx} → 1 narration seg, display_text={beat_manim_spec[:60]!r}")

                    # Legacy: render_spec.segment_specs[N].manim_scene_spec
                    if not beat_manim_spec and beat_idx is not None and beat_idx < len(segment_specs):
                        spec_entry = segment_specs[beat_idx]
                        raw_spec = spec_entry.get("manim_scene_spec", "")
                        beat_manim_spec = raw_spec.get("description", "") if isinstance(raw_spec, dict) else raw_spec
                        spec_seg_id = spec_entry.get("segment_id", "")
                        if spec_seg_id.startswith("seg_"):
                            try:
                                seg_num = int(spec_seg_id.replace("seg_", ""))
                                if 0 <= seg_num - 1 < len(all_segments):
                                    segments = [all_segments[seg_num - 1]]
                            except ValueError:
                                pass
                except (ValueError, TypeError):
                    pass

                # Fall back to section-level spec
                section_spec = render_spec.get("manim_scene_spec", {})
                if isinstance(section_spec, dict):
                    section_spec = section_spec.get("description", "")
                manim_spec = beat_manim_spec or section_spec
                print(f"[Preview] Fix C: main beat '{beat_id}' — manim_spec len={len(str(manim_spec))}")

            # ── Fix Duration: Resolve exact beat duration ──────────────────────────
            beat_duration = None
            if beat_is_quiz_eq:
                for q_src in [section.get("understanding_quiz")] + section.get("questions", []):
                    if not q_src: continue
                    ev = q_src.get("explanation_visual") or {}
                    if ev.get("renderer") == "manim":
                        beat_duration = ev.get("duration_seconds")
                        break
            else:
                # Check render_spec.manim_beats direct duration field first
                for mb in render_spec.get("manim_beats", []):
                    if str(mb.get("beat_id", "")) == beat_id:
                        beat_duration = mb.get("duration")
                        break
                # Fallback to visual_beats duration math
                if beat_duration is None:
                    for b in section.get("visual_beats", []):
                        if str(b.get("beat_id", "")) == beat_id:
                            s = b.get("beat_start_seconds")
                            e = b.get("beat_end_seconds")
                            if s is not None and e is not None:
                                beat_duration = round(e - s, 1)
                            break
                # Last resort: section average
                if beat_duration is None:
                    beat_duration = section.get("segment_duration_seconds")

            # Clamp between 5s and 30s to prevent excessively long generations
            if beat_duration:
                beat_duration = max(5, min(30, float(beat_duration)))
            else:
                beat_duration = 15.0

            print(f"[Preview] Manim duration resolved: {beat_duration}s for beat '{beat_id}'")

            # ── Build section_data matching build_v3_segment_data() pattern ──────
            # Full pipeline uses build_v3_segment_data() which creates ONE segment
            # with the correct duration_seconds. Raw narration segments from JSON
            # have duration_seconds=None, causing the LLM to default to 5s×N=wrong.
            # We replicate that pattern here for correct preview length.
            merged_narration_text = " ".join(
                s.get("text", "") for s in segments if s.get("text")
            ).strip() or "Visualizing the concept."

            section_data = {
                "section_title": section.get("title", "Preview"),
                "manim_spec": raw_prompt_override or manim_spec,
                "visual_description": raw_prompt_override or manim_spec,
                "narration_segments": [
                    {
                        "text": merged_narration_text,
                        "duration_seconds": beat_duration,   # ← key: tells LLM the target length
                        "duration": beat_duration,
                    }
                ],
                "key_terms": section.get("key_terms", []),
                "formulas": section.get("formulas", []),
                "special_requirements": (
                    f"Duration exactly {beat_duration:.1f}s. "
                    "Single beat animation. Screen starts blank. "
                    "End with FadeOut(*self.mobjects)."
                ),
                "user_feedback": user_feedback if not raw_prompt_override else "",
            }

            gen = ManimCodeGenerator()
            print(f"[Preview] Manim generator model: {gen.model}")
            print(f"[Preview] API key present: {bool(gen.api_key)}")
            print(f"[Preview] Section data keys: {list(section_data.keys())}")
            print(
                f"[Preview] manim_spec length: {len(str(section_data.get('manim_spec', '')))}"
            )
            print(
                f"[Preview] narration_segments count: {len(section_data.get('narration_segments', []))}"
            )

            code, errors = gen.generate(section_data)

            if errors:
                print(f"[Preview] Manim generation errors: {errors}")
            if code:
                print(f"[Preview] Generated code length: {len(code)} chars")
            else:
                print(f"[Preview] Code is EMPTY. Errors: {errors}")

            if not code:
                raise Exception(f"Failed to generate Manim code. Errors: {errors}")

            final_prompt_used = code  # Store code as "prompt"

            # 2. Render Code
            _update_preview_status(
                job_id,
                preview_key,
                {
                    "status": "processing",
                    "progress": 50,
                    "message": "Rendering Manim video...",
                },
            )

            # We need to execute this code.
            # ManimRunner expects topic dict. We can create a fake one.
            # But ManimRunner.render_manim_video is complex.
            # Easier to use internal helper _execute_spec_generated_render or similar if accessible,
            # OR just use the code generator's output and run manim command directly here.

            # Let's use the standard "render_manim_video" but we need to trick it into using our code.
            # We'll create a temp topic dict with "spec_generated" plan.

            fake_topic = {
                "section_id": f"preview_{section_id}",
                "title": "Preview",
                "explanation_plan": {
                    "manim_plan": {
                        "scene_type": "spec_generated",
                        "manim_code": code,
                        "params": {},
                    }
                },
            }

            # Manim runner writes to output_dir/topic_ID.mp4
            # We want specific output_path.
            # We'll rely on temp dir then rename.
            temp_dir = job_dir / "videos" / "temp_preview"
            os.makedirs(temp_dir, exist_ok=True)

            # Import inside function to avoid circular imports
            from render.manim.manim_runner import render_manim_video

            result_paths = render_manim_video(fake_topic, str(temp_dir))

            # Result is likely temp_dir/topic_preview_...mp4
            # We need to move it to output_path
            msg = "No output"
            if isinstance(result_paths, str) and os.path.exists(result_paths):
                shutil.move(result_paths, str(output_path))
            elif (
                isinstance(result_paths, list)
                and len(result_paths) > 0
                and os.path.exists(result_paths[0])
            ):
                shutil.move(result_paths[0], str(output_path))
            else:
                raise Exception("Manim runner did not produce a file")

            # Cleanup
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

        _update_preview_status(
            job_id,
            preview_key,
            {
                "status": "success",
                "progress": 100,
                "preview_url": f"/player/jobs/{job_id}/videos/{preview_filename}",
                "generated_prompt": final_prompt_used,
            },
        )
        print(f"[Preview] Success for {preview_key}")

    except Exception as e:
        print(f"[Preview] Error: {e}")
        traceback.print_exc()
        _update_preview_status(
            job_id, preview_key, {"status": "failed", "error": str(e)}
        )


@app.route("/job/<job_id>/generate_preview", methods=["POST"])
def generate_preview(job_id):
    """
    Generate a preview video (non-destructive) with new feedback/prompt.
    Returns immediately and runs in background.
    """
    try:
        data = request.json
        section_id = data.get("section_id")
        beat_id = data.get("beat_id", "0")  # Default to 0 if not provided
        renderer = data.get("renderer", "wan").lower()

        user_feedback = data.get("user_feedback", "")
        raw_prompt_override = data.get("raw_prompt_override", "")
        image_prompt_start = data.get("image_prompt_start", "")
        image_prompt_end = data.get("image_prompt_end", "")
        video_provider = data.get("video_provider", "wan")  # 'wan' or 'gpu'

        if not section_id:
            return jsonify({"error": "section_id is required"}), 400

        if not user_feedback and not raw_prompt_override and renderer not in ["image_to_video", "text_to_video"]:
            return jsonify(
                {"error": "Either user_feedback or raw_prompt_override is required"}
            ), 400

        # Unique preview filename
        timestamp = int(time.time())
        preview_filename = f"preview_{section_id}_{beat_id}_{timestamp}.mp4"

        # Start background thread
        thread = threading.Thread(
            target=_run_preview_generation,
            args=(
                job_id,
                section_id,
                beat_id,
                renderer,
                user_feedback,
                raw_prompt_override,
                image_prompt_start,
                image_prompt_end,
                preview_filename,
                video_provider,
            ),
        )
        thread.start()

        preview_key = f"{section_id}_{beat_id}"

        return jsonify(
            {
                "status": "accepted",
                "message": "Preview generation started",
                "preview_key": preview_key,
                "status_endpoint": f"/job/{job_id}/preview_status/{preview_key}",
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/job/<job_id>/preview_status/<preview_key>", methods=["GET"])
def check_preview_status(job_id, preview_key):
    """Check status of a specific preview generation."""
    try:
        status_path = JOBS_DIR / job_id / "preview_status.json"
        if not status_path.exists():
            return jsonify({"status": "unknown", "message": "No status file found"})

        with open(status_path, "r") as f:
            data = json.load(f)

        return jsonify(data.get(preview_key, {"status": "unknown"}))

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/job/<job_id>/approve_preview", methods=["POST"])
def approve_preview(job_id):
    """
    Promote a preview video to be the official asset.
    Updates the file on disk and all relevant paths inside presentation.json.
    """
    import re
    try:
        data = request.json
        print(f"[DEBUG] approve_preview called for {job_id} with data: {data}")

        section_id         = data.get("section_id")
        beat_id            = data.get("beat_id")
        preview_path       = data.get("preview_path")   # e.g. "videos/preview_3_beat_2_1234.mp4"
        new_prompt         = data.get("new_prompt")
        image_prompt_start = data.get("image_prompt_start")
        image_prompt_end   = data.get("image_prompt_end")
        renderer           = data.get("renderer", "wan").lower()

        if not all([section_id, preview_path]):
            return jsonify({"error": "Missing required fields"}), 400

        job_dir     = JOBS_DIR / job_id
        beat_id_str = str(beat_id) if beat_id else ""

        # ── 1. Verify preview exists ──────────────────────────────────────────────
        clean_preview = preview_path.split("videos/")[-1]
        abs_preview   = job_dir / "videos" / clean_preview
        if not abs_preview.exists():
            return jsonify({"error": f"Preview file not found: {clean_preview}"}), 404

        # ── 2. Load presentation ──────────────────────────────────────────────────
        pres_path = job_dir / "presentation.json"
        with open(pres_path, "r", encoding="utf-8") as f:
            presentation = json.load(f)

        section = next(
            (s for s in presentation.get("sections", [])
             if str(s["section_id"]) == str(section_id)),
            None,
        )
        if not section:
            return jsonify({"error": f"Section {section_id} not found"}), 404

        # ── 3. Resolve beat_id → target_filename ─────────────────────────────────
        #
        # Priority:
        #   A. render_spec.image_to_video_beats   (V3 primary)
        #   B. understanding_quiz.explanation_visual
        #   C. questions[N].explanation_visual
        #   D. visual_beats
        #   E. video_prompts  (WAN older)
        #   F. beat_videos numeric index  (Manim older)
        #   G. trailing-int pattern fallback
        #   H. safe string fallback

        target_filename   = None
        prompt_index      = None
        beat_location     = None
        quiz_question_idx = None

        def _safe_existing(beat_obj, sec, idx):
            """
            Return the existing video filename ONLY if its stem contains this
            beat's ID — guards against cross-contaminated paths left by bad
            generation runs (e.g. beat_1 having video_path = beat_2's file).
            """
            bid = str(beat_obj.get("beat_id", ""))

            vp = beat_obj.get("video_path")
            if vp:
                if bid and bid not in Path(vp).stem:
                    print(f"[Approve] WARNING: beat '{bid}' has suspicious "
                          f"video_path '{vp}' — ignoring, will derive canonical name")
                else:
                    return Path(vp).name

            # Try beat_video_paths[] at same index, with same sanity check
            bvp = sec.get("beat_video_paths") or []
            if idx < len(bvp) and bvp[idx]:
                if bid and bid not in Path(bvp[idx]).stem:
                    print(f"[Approve] WARNING: beat_video_paths[{idx}]='{bvp[idx]}' "
                          f"doesn't match beat '{bid}' — ignoring")
                else:
                    return Path(bvp[idx]).name

            return None

        # ── A. render_spec.image_to_video_beats ──────────────────────────────────
        rs_beats = section.get("render_spec", {}).get("image_to_video_beats", [])
        for idx, b in enumerate(rs_beats):
            if str(b.get("beat_id", "")) == beat_id_str:
                prompt_index    = idx
                beat_location   = "render_spec_i2v"
                existing        = _safe_existing(b, section, idx)
                target_filename = existing or f"topic_{section_id}_{beat_id_str}.mp4"
                print(f"[Approve] A: render_spec.i2v_beats[{idx}] → {target_filename}")
                break

        # ── B. understanding_quiz.explanation_visual ──────────────────────────────
        if prompt_index is None:
            uq = section.get("understanding_quiz") or {}
            ev = uq.get("explanation_visual") or {}
            for idx, b in enumerate(ev.get("image_to_video_beats", [])):
                if str(b.get("beat_id", "")) == beat_id_str:
                    prompt_index    = idx
                    beat_location   = "quiz_ev"
                    existing = b.get("video_path") or ev.get("video_path")
                    if existing:
                        target_filename = Path(existing).name
                    else:
                        bvp = ev.get("beat_video_paths") or []
                        target_filename = Path(bvp[idx]).name \
                            if idx < len(bvp) and bvp[idx] \
                            else f"topic_{section_id}_{beat_id_str}.mp4"
                    print(f"[Approve] B: quiz ev.i2v_beats[{idx}] → {target_filename}")
                    break

        # ── C. questions[N].explanation_visual ────────────────────────────────────
        if prompt_index is None:
            for q_idx, q in enumerate(section.get("questions", [])):
                ev = q.get("explanation_visual") or {}
                for idx, b in enumerate(ev.get("image_to_video_beats", [])):
                    if str(b.get("beat_id", "")) == beat_id_str:
                        prompt_index      = idx
                        beat_location     = "question_ev"
                        quiz_question_idx = q_idx
                        existing = b.get("video_path") or ev.get("video_path")
                        if existing:
                            target_filename = Path(existing).name
                        else:
                            bvp = ev.get("beat_video_paths") or []
                            target_filename = Path(bvp[idx]).name \
                                if idx < len(bvp) and bvp[idx] \
                                else f"topic_{section_id}_{beat_id_str}.mp4"
                        print(f"[Approve] C: questions[{q_idx}].ev.i2v_beats[{idx}] → {target_filename}")
                        break
                if prompt_index is not None:
                    break

        # ── D. visual_beats ───────────────────────────────────────────────────────
        if prompt_index is None:
            for idx, b in enumerate(section.get("visual_beats", [])):
                if str(b.get("beat_id", "")) == beat_id_str:
                    prompt_index    = idx
                    beat_location   = "visual_beats"
                    existing        = b.get("video_path")
                    target_filename = Path(existing).name if existing \
                        else f"topic_{section_id}_{beat_id_str}.mp4"
                    print(f"[Approve] D: visual_beats[{idx}] → {target_filename}")
                    break

        # ── E. video_prompts (WAN older) ──────────────────────────────────────────
        if prompt_index is None:
            for idx, p in enumerate(section.get("video_prompts", [])):
                if isinstance(p, dict) and str(p.get("beat_id", "")) == beat_id_str:
                    prompt_index    = idx
                    beat_location   = "video_prompts"
                    target_filename = f"{beat_id_str}.mp4"
                    print(f"[Approve] E: video_prompts[{idx}] → {target_filename}")
                    break

        # ── D2. Fix A: Manim main section — visual_beats by beat_id ───────────────
        # Handles beat_id values like "beat_1", "beat_2" for renderer="manim" sections.
        # These are not in image_to_video_beats, so they were missed by blocks A/B/C/D.
        if prompt_index is None and section.get("renderer") == "manim":
            for idx, b in enumerate(section.get("visual_beats", [])):
                if str(b.get("beat_id", "")) == beat_id_str:
                    prompt_index    = idx
                    beat_location   = "manim_visual_beats"
                    existing        = b.get("video_path")
                    target_filename = Path(existing).name if existing \
                        else f"topic_{section_id}_{beat_id_str}.mp4"
                    print(f"[Approve] D2 (manim): visual_beats[{idx}] → {target_filename}")
                    break

        # ── D3. Fix A: Manim quiz — explanation_visual flat block ─────────────────
        # Handles beat_id values like "eq_beat_0", "eq_main" for quiz explanation_visual
        # blocks that use renderer="manim" with a flat manim_scene_spec string.
        if prompt_index is None and beat_id_str.startswith("eq_"):
            for q_src in [section.get("understanding_quiz")] + section.get("questions", []):
                if not q_src:
                    continue
                ev = q_src.get("explanation_visual") or {}
                if ev.get("renderer") == "manim":
                    prompt_index    = 0
                    beat_location   = "manim_eq_visual"
                    existing        = ev.get("video_path")
                    target_filename = Path(existing).name if existing \
                        else f"topic_{section_id}_eq_beat_0.mp4"
                    print(f"[Approve] D3 (manim quiz eq): explanation_visual → {target_filename}")
                    break

        # ── F. Numeric beat_id → beat_videos[] (Manim older) ─────────────────────
        if prompt_index is None and beat_id_str.isdigit():
            idx         = int(beat_id_str)
            beat_videos = section.get("beat_videos") or []
            if 0 <= idx < len(beat_videos):
                prompt_index    = idx
                beat_location   = "beat_videos"
                bv_path         = beat_videos[idx]
                target_filename = Path(bv_path).name if bv_path \
                    else f"topic_{section_id}_beat_{idx}.mp4"
                print(f"[Approve] F: beat_videos[{idx}] → {target_filename}")

        # ── G. Trailing-int pattern (recap_beat_N, eq_beat_N, beat_N …) ──────────
        if prompt_index is None:
            m = re.search(r"(\d+)$", beat_id_str)
            if m:
                prompt_index    = int(m.group(1))
                beat_location   = "beat_videos"
                target_filename = f"topic_{section_id}_{beat_id_str}.mp4"
                print(f"[Approve] G: trailing-int pattern → {target_filename}")

        # ── H. Safe string fallback ───────────────────────────────────────────────
        if target_filename is None:
            if beat_id_str and beat_id_str != "None":
                safe            = beat_id_str.replace("/", "_").replace("\\", "_")
                target_filename = f"topic_{section_id}_{safe}.mp4"
                beat_location   = beat_location or "beat_videos"
                print(f"[Approve] H: string fallback → {target_filename}")
            else:
                target_filename = f"topic_{section_id}.mp4"
                beat_location   = "video_path"
                print(f"[Approve] H: single-video fallback → {target_filename}")

        abs_target = job_dir / "videos" / target_filename

        # ── 4. Move preview → target ──────────────────────────────────────────────
        shutil.move(str(abs_preview), str(abs_target))
        print(f"[Approve] Moved {abs_preview.name} → {target_filename}")

        # ── 5. Update presentation.json ───────────────────────────────────────────
        with presentation_lock:
            with open(pres_path, "r", encoding="utf-8") as f:
                presentation = json.load(f)

            updated = False
            for sec in presentation.get("sections", []):
                if str(sec.get("section_id")) != str(section_id):
                    continue

                rel_path = f"videos/{target_filename}"

                # Helper: stamp prompt fields onto a beat dict
                def _apply_prompts(beat_dict):
                    beat_dict["video_path"] = rel_path
                    if new_prompt:
                        if renderer in ["wan", "image_to_video", "text_to_video", "video"]:
                            beat_dict["video_prompt"] = new_prompt
                        elif renderer == "manim":
                            # Persist the new instruction as manim_scene_spec
                            # so re-editing a Manim beat uses the latest spec, not the old one
                            beat_dict["manim_scene_spec"] = new_prompt
                        else:
                            beat_dict["video_prompt"] = new_prompt
                            beat_dict["manim_scene_spec"] = new_prompt
                    if image_prompt_start:
                        beat_dict["image_prompt_start"] = image_prompt_start
                    if image_prompt_end is not None:
                        beat_dict["image_prompt_end"] = image_prompt_end

                # ─────────────────────────────────────────────────────────────────
                # THE CORE FIX: sync beat_video_paths[] by STEM MATCHING, not by
                # positional index.
                #
                # The old code did: bvp[prompt_index] = rel_path
                # That breaks whenever beat_video_paths[] is shorter than
                # render_spec beats OR has a gap (e.g. section 6 skipped beat_4,
                # so bvp[3] held beat_5's filename — overwriting it with beat_4
                # would permanently lose beat_5 from the player's list).
                #
                # New approach:
                #   1. Search bvp for an entry whose stem matches target_filename's stem.
                #      If found → update that slot in-place.
                #   2. If not found (beat was never in the list) → insert at the
                #      correct ordered position by counting how many render_spec
                #      beats that precede this one already have confirmed slots.
                # ─────────────────────────────────────────────────────────────────
                def _sync_bvp(bvp_list, rs_beat_list):
                    target_stem = Path(target_filename).stem  # e.g. "topic_6_recap_beat_4"

                    # 1. Find and update existing slot
                    for i, entry in enumerate(bvp_list):
                        if entry and Path(entry).stem == target_stem:
                            bvp_list[i] = rel_path
                            print(f"[Approve] bvp: updated existing slot[{i}] → {rel_path}")
                            return bvp_list

                    # 2. Insert at correct ordered position
                    insert_at = len(bvp_list)  # default: append
                    for rs_idx, rb in enumerate(rs_beat_list):
                        if str(rb.get("beat_id", "")) == beat_id_str:
                            # Count render_spec beats before this one that are
                            # already represented in bvp (matched by beat_id stem)
                            confirmed_before = 0
                            for prev_b in rs_beat_list[:rs_idx]:
                                prev_bid = str(prev_b.get("beat_id", ""))
                                if any(e and prev_bid in Path(e).stem for e in bvp_list):
                                    confirmed_before += 1
                            insert_at = confirmed_before
                            break

                    bvp_list.insert(insert_at, rel_path)
                    print(f"[Approve] bvp: inserted at [{insert_at}] → {rel_path} "
                          f"(list now has {len(bvp_list)} entries)")
                    return bvp_list

                # ── A. render_spec.image_to_video_beats ──────────────────────────
                if beat_location == "render_spec_i2v" and prompt_index is not None:
                    rs     = sec.setdefault("render_spec", {})
                    rs_i2v = rs.get("image_to_video_beats", [])
                    if prompt_index < len(rs_i2v):
                        _apply_prompts(rs_i2v[prompt_index])

                    bvp = sec.get("beat_video_paths") or []
                    bvp = _sync_bvp(bvp, rs_i2v)
                    sec["beat_video_paths"] = bvp

                # ── B. understanding_quiz explanation_visual ───────────────────────
                elif beat_location == "quiz_ev" and prompt_index is not None:
                    uq       = sec.get("understanding_quiz") or {}
                    ev       = uq.get("explanation_visual") or {}
                    ev_beats = ev.get("image_to_video_beats", [])
                    if prompt_index < len(ev_beats):
                        _apply_prompts(ev_beats[prompt_index])
                    ev["video_path"] = rel_path
                    ev_bvp = ev.get("beat_video_paths") or []
                    ev_bvp = _sync_bvp(ev_bvp, ev_beats)
                    ev["beat_video_paths"] = ev_bvp
                    uq["explanation_visual_video_path"] = rel_path

                # ── C. questions[N].explanation_visual ────────────────────────────
                elif beat_location == "question_ev" and prompt_index is not None \
                        and quiz_question_idx is not None:
                    questions = sec.get("questions", [])
                    if quiz_question_idx < len(questions):
                        q        = questions[quiz_question_idx]
                        ev       = q.get("explanation_visual") or {}
                        ev_beats = ev.get("image_to_video_beats", [])
                        if prompt_index < len(ev_beats):
                            _apply_prompts(ev_beats[prompt_index])
                        ev["video_path"] = rel_path
                        ev_bvp = ev.get("beat_video_paths") or []
                        ev_bvp = _sync_bvp(ev_bvp, ev_beats)
                        ev["beat_video_paths"] = ev_bvp
                        q["explanation_visual_video_path"] = rel_path

                # ── D. visual_beats ───────────────────────────────────────────────
                elif beat_location == "visual_beats" and prompt_index is not None:
                    vb = sec.get("visual_beats", [])
                    if prompt_index < len(vb):
                        _apply_prompts(vb[prompt_index])

                # ── E. video_prompts ──────────────────────────────────────────────
                elif beat_location == "video_prompts" and prompt_index is not None:
                    vp = sec.get("video_prompts", [])
                    if prompt_index < len(vp) and isinstance(vp[prompt_index], dict):
                        if new_prompt:
                            vp[prompt_index]["prompt"] = new_prompt

                # ── F/G. beat_videos[] ────────────────────────────────────────────
                elif beat_location == "beat_videos" and prompt_index is not None:
                    bv = sec.get("beat_videos") or []
                    while len(bv) <= prompt_index:
                        bv.append(None)
                    bv[prompt_index] = rel_path
                    sec["beat_videos"] = bv

                # ── Fix A: D2. Manim main section — update visual_beats[] directly ─
                elif beat_location == "manim_visual_beats" and prompt_index is not None:
                    vb = sec.get("visual_beats", [])
                    if prompt_index < len(vb):
                        vb[prompt_index]["video_path"] = rel_path
                        if new_prompt:
                            # Persist the new instruction so next edit opens correct spec
                            vb[prompt_index]["manim_scene_spec"] = new_prompt
                    # Also sync beat_video_paths so the player can navigate to it
                    bvp = sec.get("beat_video_paths") or []
                    beat_stem = Path(target_filename).stem
                    replaced = False
                    for i, entry in enumerate(bvp):
                        if entry and Path(entry).stem == beat_stem:
                            bvp[i] = rel_path
                            replaced = True
                            break
                    if not replaced:
                        bvp.append(rel_path)
                    sec["beat_video_paths"] = bvp
                    print(f"[Approve] D2 writeback: visual_beats[{prompt_index}].video_path = {rel_path}")

                # ── Fix A: D3. Manim quiz — update explanation_visual flat block ───
                elif beat_location == "manim_eq_visual":
                    for q_src in [sec.get("understanding_quiz")] + sec.get("questions", []):
                        if not q_src:
                            continue
                        ev = q_src.get("explanation_visual") or {}
                        if ev.get("renderer") == "manim":
                            ev["video_path"] = rel_path
                            if new_prompt:
                                ev["manim_scene_spec"] = new_prompt
                            # Also update the shortcut field the player uses
                            q_src["explanation_visual_video_path"] = rel_path
                            print(f"[Approve] D3 writeback: explanation_visual.video_path = {rel_path}")
                            break

                # ── H. Single video_path ──────────────────────────────────────────
                elif beat_location == "video_path":
                    sec["video_path"] = rel_path

                # ── Always: sync section top-level video_path if stem matches ─────
                if sec.get("video_path") and \
                        Path(sec["video_path"]).stem == Path(target_filename).stem:
                    sec["video_path"] = rel_path

                # ── Always: sync top-level image_to_video_beats (older format) ────
                for b in sec.get("image_to_video_beats", []):
                    if str(b.get("beat_id", "")) == beat_id_str:
                        _apply_prompts(b)
                        break

                # ── Always: sync narration segments ───────────────────────────────
                # Three cases handled:
                #   1. Segment already pointed to this file (stem match) → update path
                #   2. Segment's beat_videos list contained this file → update list
                #   3. Segment was wrongly pointing to a different beat's file
                #      but beat_id_str appears in its stem → correct the wrong pointer
                #      (this is what caused seg_4 → recap_beat_5 to persist forever)
                target_stem = Path(target_filename).stem
                for seg in sec.get("narration", {}).get("segments", []):
                    seg_vp = seg.get("video_path", "")
                    seg_bv = seg.get("beat_videos") or []

                    # Case 1: direct path match
                    if seg_vp and Path(seg_vp).stem == target_stem:
                        seg["video_path"]  = rel_path
                        seg["beat_videos"] = [rel_path]
                        continue

                    # Case 2: inside beat_videos list
                    bv_changed = False
                    for i, sv in enumerate(seg_bv):
                        if sv and Path(sv).stem == target_stem:
                            seg_bv[i] = rel_path
                            bv_changed = True
                    if bv_changed:
                        seg["beat_videos"] = seg_bv
                        if not seg_vp or seg_vp == seg_bv[0]:
                            seg["video_path"] = rel_path
                        continue

                    # Case 3: segment wrongly points to a DIFFERENT file but
                    # beat_id_str is in that file's stem — fix the wrong pointer
                    if beat_id_str and seg_vp and beat_id_str in Path(seg_vp).stem \
                            and Path(seg_vp).stem != target_stem:
                        print(f"[Approve] Correcting seg '{seg.get('segment_id')}': "
                              f"'{seg_vp}' → '{rel_path}'")
                        seg["video_path"]  = rel_path
                        seg["beat_videos"] = [rel_path]

                updated = True
                break

            if updated:
                with open(pres_path, "w", encoding="utf-8") as f:
                    json.dump(presentation, f, indent=4)
                print(f"[Approve] presentation.json saved — {rel_path}")
            else:
                print(f"[Approve] WARNING: section {section_id} not found during JSON update")

        # ── 6. Cleanup stale previews for this beat ───────────────────────────────
        try:
            pattern = f"preview_{section_id}_"
            if beat_id_str and beat_id_str not in ("None", ""):
                pattern += f"{beat_id_str}_"
            for stale in job_dir.glob(f"videos/{pattern}*.mp4"):
                try:
                    if stale.resolve() != abs_target.resolve():
                        stale.unlink()
                        print(f"[Cleanup] Deleted stale preview: {stale.name}")
                except Exception as ex:
                    print(f"[Cleanup] Could not delete {stale.name}: {ex}")
        except Exception as e:
            print(f"[Cleanup] Error: {e}")

        return jsonify({
            "status": "success",
            "saved_as": target_filename,
            "beat_location": beat_location,
            "prompt_index": prompt_index,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

        
@app.route("/submit_job", methods=["POST"])
def submit_job():
    try:
        if False:  # is_job_running():
            current_id = get_current_job_ids()
            return jsonify(
                {
                    "status": "busy",
                    "message": "A job is already running. Please wait for it to complete.",
                    "current_job_id": current_id,
                }
            ), 409

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
        video_provider = request.form.get("video_provider", "kie")
        print(f"=" * 80)
        print(
            f"[ROUTING DEBUG] Received pipeline_version from form: '{pipeline_version}'"
        )
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
            elif (
                filename.endswith(".md")
                or filename.endswith(".markdown")
                or filename.endswith(".txt")
            ):
                job_type = "markdown_file"
                suffix = ".md"
            else:
                return jsonify(
                    {
                        "error": " Unsupported file type. Supported: PDF, DOC, DOCX, ODT, MD"
                    }
                ), 400

            temp_file = TEMP_DIR / f"{os.urandom(8).hex()}{suffix}"
            uploaded_file.save(str(temp_file))
            original_filename = uploaded_file.filename

            if pipeline_version in ["v15_v2", "v15_v2_director"]:
                job_type_name = "v15_v2_pipeline"
            elif pipeline_version == "v15":
                job_type_name = "v15_pipeline"
            else:
                job_type_name = "v14_pipeline"
            # ISS-PREFIX: Extract job prefix or use IP address
            job_prefix = request.form.get("job_prefix")
            if not job_prefix:
                # Fallback to IP address if no prefix provided
                job_prefix = request.remote_addr
                # Replace dots/colons in IP with underscores for safety
                if job_prefix:
                    job_prefix = job_prefix.replace(".", "_").replace(":", "_")

            job_id = job_manager.create_job(
                job_type_name,
                {
                    "subject": subject,
                    "grade": grade,
                    "file_path": str(temp_file),
                    "source_file": original_filename,
                    "skip_wan": skip_wan,
                    "skip_avatar": skip_avatar,
                    "tts_provider": tts_provider,
                    "pipeline_version": pipeline_version,
                    "generation_scope": generation_scope,
                    "model": model,
                    "video_provider": video_provider,
                    "job_prefix": job_prefix,  # Store in params too for reference
                },
                prefix=job_prefix,
            )

            job_output_dir = JOBS_DIR / job_id
            setup_job_folder(job_output_dir, pipeline_version=pipeline_version)

            # ISS-SAVE-UPLOAD: Save a copy of the original uploaded file to the job folder
            try:
                upload_backup_path = job_output_dir / f"source_document{suffix}"
                shutil.copy2(str(temp_file), str(upload_backup_path))
                print(f"[JOB] Saved original upload to {upload_backup_path}")
            except Exception as e:
                print(f"[JOB] WARNING: Failed to save original upload backup: {e}")

            if job_type == "document":
                # ISS-206: Handle PDF, DOC, DOCX, ODT via Datalab
                if pipeline_version == "v3":
                    document_processor = process_document_job_v3
                elif pipeline_version in ["v15_v2", "v15_v2_director"]:
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
                    skip_wan=skip_wan,
                    skip_avatar=skip_avatar,
                    source_file=original_filename,
                    tts_provider=tts_provider,
                    pipeline_version=pipeline_version,
                    generation_scope=generation_scope,
                    model=model,
                    video_provider=video_provider,
                )
            else:
                with open(temp_file, "r", encoding="utf-8") as f:
                    markdown_content = f.read()
                os.unlink(temp_file)

                content_preview = markdown_content[:300].replace("\n", " ").strip()
                if len(markdown_content) > 300:
                    content_preview += "..."

                job_manager.update_job(
                    job_id, {"content_preview": content_preview}, persist=True
                )

                if pipeline_version == "v3":
                    job_processor = process_markdown_job_v3
                    print(
                        f"[ROUTING DEBUG] Selected processor: process_markdown_job_v3 (V3 Three.js)"
                    )
                elif pipeline_version in ["v15_v2", "v15_v2_director"]:
                    job_processor = process_markdown_job_v15_v2
                    print(
                        f"[ROUTING DEBUG] Selected processor: process_markdown_job_v15_v2"
                    )
                elif pipeline_version == "v15":
                    job_processor = process_markdown_job_v15
                    print(
                        f"[ROUTING DEBUG] Selected processor: process_markdown_job_v15"
                    )
                else:
                    job_processor = process_markdown_job
                    print(
                        f"[ROUTING DEBUG] Selected processor: process_markdown_job (legacy)"
                    )
                print(
                    f"[ROUTING DEBUG] Calling {job_processor.__name__} with pipeline_version='{pipeline_version}'"
                )
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
            video_provider = data.get("video_provider", "kie")
            # Capture images from JSON payload (critical for external API usage)
            images_dict = data.get("images", data.get("images_dict"))
            title = data.get("title", f"Presentation {int(time.time())}")

            if not markdown_content:
                return jsonify({"error": "Markdown content is required"}), 400

            content_preview = markdown_content[:300].replace("\n", " ").strip()
            if len(markdown_content) > 300:
                content_preview += "..."

            if pipeline_version == "v15_v2":
                job_type_name = "v15_v2_pipeline"
            elif pipeline_version == "v15":
                job_type_name = "v15_pipeline"
            else:
                job_type_name = "v14_pipeline"
            # ISS-PREFIX: Extract job prefix (JSON payload)
            job_prefix = data.get("job_prefix")
            if not job_prefix:
                job_prefix = request.remote_addr
                if job_prefix:
                    job_prefix = job_prefix.replace(".", "_").replace(":", "_")

            job_id = job_manager.create_job(
                job_type_name,
                {
                    "subject": subject,
                    "grade": grade,
                    "dry_run": dry_run,
                    "skip_wan": skip_wan,
                    "skip_avatar": skip_avatar,
                    "tts_provider": tts_provider,
                    "pipeline_version": pipeline_version,
                    "generation_scope": generation_scope,
                    "model": model,
                    "content_preview": content_preview,
                    "video_provider": video_provider,
                    "job_prefix": job_prefix,
                },
                prefix=job_prefix,
            )

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
                model=model,
                video_provider=video_provider,
                review_mode=review_mode,
                images_dict=images_dict,
            )

        else:
            return jsonify({"error": "Please provide a file or markdown content"}), 400

        mode_msg = " (DRY RUN - prompts only, no real rendering)" if dry_run else ""
        job_data = job_manager.get_job(job_id)
        content_preview = None
        if job_data:
            content_preview = job_data.get("content_preview") or job_data.get(
                "params", {}
            ).get("content_preview")

        return jsonify(
            {
                "status": "accepted",
                "job_id": job_id,
                "dry_run": dry_run,
                "skip_wan": skip_wan,
                "skip_avatar": skip_avatar,
                "video_provider": video_provider,
                "content_preview": content_preview,
                "message": f"Job submitted successfully{mode_msg}. Poll /job/<job_id>/status for progress.",
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


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
        "error": job["error"],
    }

    if job["status"] == "failed":
        response["failure_message"] = job.get("failure_message")
        response["failed_phase"] = job.get("failed_phase")

    # ISS-Analytics: Inject live progress details from analytics.json if available
    job_folder = Path(JOBS_DIR) / job_id
    analytics_path = job_folder / "analytics.json"
    if analytics_path.exists():
        try:
            with open(analytics_path, "r") as f:
                analytics_data = json.load(f)
            # Inject relevant fields
            response["progress_details"] = analytics_data.get("progress_details")
            response["timings"] = analytics_data.get("timings")
        except:
            pass  # Non-critical if read fails

    return jsonify(response)


@app.route("/job/<job_id>/debug_status", methods=["GET"])
def debug_job_status(job_id):
    """
    Deep diagnostic endpoint for any job — especially useful for ongoing/stuck jobs.
    Performs live disk inspection: counts audio, video, avatar files; reads validation
    reports, checks phase state, and generates human-readable advisories.
    READ-ONLY — never modifies any job data.

    Returns:
        {
          "job_id", "status", "is_wip", "created_at", "elapsed_seconds",
          "source": { file, type, pages },
          "pipeline": { version, model, tts_provider, video_provider },
          "phase": { current, message, steps_completed, total_steps, progress_pct },
          "content": { sections, segments, section_breakdown, renderers },
          "assets": {
            "audio":   { found, expected, missing, wired_to_sections },
            "videos":  { found, expected_manim, expected_wan, missing },
            "avatars": { found, files }
          },
          "validation": { issues_count, issues },
          "analytics": { exists, cost_usd, timings },
          "advisories": [ "human-readable diagnostic strings" ],
          "health_score": 0-100,
          "health_grade": "HEALTHY|FAIR|DEGRADED|CRITICAL"
        }
    """
    import traceback as _traceback
    from datetime import timezone

    try:
        job = job_manager.get_job(job_id)
        if not job:
            return jsonify({"error": f"Job '{job_id}' not found in index"}), 404

        job_dir = Path(JOBS_DIR) / job_id
        now_utc = datetime.utcnow()
        advisories = []
        score = 0
        max_score = 100

        # ── 1. BASE INFO ──────────────────────────────────────────────────────
        created_str = job.get("created_at", "")
        elapsed_seconds = None
        try:
            created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            elapsed_seconds = int(
                (now_utc.replace(tzinfo=timezone.utc) - created_dt).total_seconds()
            )
        except Exception:
            pass

        status = job.get("status", "unknown")
        is_wip = status == "processing"
        has_error = status == "failed"

        params = job.get("params", {})
        source_info = {
            "file": params.get("source_file", params.get("file_path", "unknown")),
            "type": job.get("source_type", params.get("source_type", "unknown")),
            "pages": job.get("page_count", params.get("page_count", 0)),
        }
        pipeline_info = {
            "version": params.get(
                "pipeline_version", job.get("pipeline_version", "unknown")
            ),
            "model": params.get("model", "default"),
            "tts_provider": params.get("tts_provider", "unknown"),
            "video_provider": params.get("video_provider", "unknown"),
            "skip_wan": params.get("skip_wan", False),
            "skip_avatar": params.get("skip_avatar", False),
        }

        # ── 2. PHASE INFO ─────────────────────────────────────────────────────
        current_phase = job.get("current_phase_key", "unknown")
        steps_completed = job.get("steps_completed", 0)
        total_steps = job.get("total_steps", 0)
        progress_pct = job.get("progress", 0)
        phase_info = {
            "current": current_phase,
            "message": job.get("status_message", ""),
            "step_name": job.get("current_step_name", ""),
            "steps_completed": steps_completed,
            "total_steps": total_steps,
            "progress_pct": progress_pct,
            "blueprint_ready": job.get("blueprint_ready", False),
        }

        if is_wip:
            score += 20
            if elapsed_seconds and elapsed_seconds > 3600:
                advisories.append(
                    f"⚠️  Job has been running for {elapsed_seconds // 60} minutes. Consider checking for a stall."
                )
            elif elapsed_seconds:
                advisories.append(
                    f"ℹ️  Job is actively processing. Running for {elapsed_seconds // 60}m {elapsed_seconds % 60}s."
                )
        elif status == "completed":
            score += 30
            advisories.append("✅ Job completed successfully.")
        elif has_error:
            err_msg = job.get("error", "No error message recorded")
            advisories.append(f"❌ Job FAILED — error: {err_msg[:200]}")

        # ── 3. PRESENTATION.JSON ANALYSIS ─────────────────────────────────────
        pres_path = job_dir / "presentation.json"
        content_info = {
            "sections": 0,
            "segments": 0,
            "section_breakdown": {},
            "renderers": {},
        }

        if pres_path.exists():
            score += 10
            try:
                with open(pres_path, "r", encoding="utf-8") as f:
                    pres = json.load(f)
                sections = pres.get("sections", [])
                content_info["sections"] = len(sections)
                section_breakdown = {}
                renderer_counts = {}
                expected_audio = len(sections)
                expected_manim = 0
                expected_wan = 0
                for sec in sections:
                    st = sec.get("section_type", "unknown")
                    section_breakdown[st] = section_breakdown.get(st, 0) + 1
                    renderer = sec.get("renderer", "none")
                    renderer_counts[renderer] = renderer_counts.get(renderer, 0) + 1
                    if renderer == "manim":
                        expected_manim += 1
                    elif renderer in ("video", "wan", "wan_video"):
                        expected_wan += 1
                    # count segments
                    content_info["segments"] += len(
                        sec.get("narration", {}).get("segments", [])
                    )

                content_info["section_breakdown"] = section_breakdown
                content_info["renderers"] = renderer_counts
                content_info["_expected_audio"] = expected_audio
                content_info["_expected_manim"] = expected_manim
                content_info["_expected_wan"] = expected_wan
            except Exception as e:
                advisories.append(f"⚠️  presentation.json parse error: {e}")
        else:
            advisories.append(
                "❌ presentation.json missing — content pipeline hasn't completed yet."
            )

        # ── 4. ASSET SCAN ─────────────────────────────────────────────────────
        # Audio
        audio_dir = job_dir / "audio"
        audio_files = []
        if audio_dir.exists():
            audio_files = [
                f.name
                for f in audio_dir.iterdir()
                if f.is_file()
                and f.suffix in (".mp3", ".wav")
                and f.stat().st_size > 500
            ]
        expected_audio = content_info.get("_expected_audio", content_info["sections"])
        audio_info = {
            "found": len(audio_files),
            "expected": expected_audio,
            "files": sorted(audio_files),
            "complete": len(audio_files) >= expected_audio and expected_audio > 0,
        }
        if len(audio_files) >= expected_audio and expected_audio > 0:
            score += 20
            advisories.append(
                f"✅ Audio: {len(audio_files)}/{expected_audio} files ready."
            )
        elif is_wip and current_phase in ("tts", "audio"):
            advisories.append(
                f"🔄 Audio: TTS in progress — {len(audio_files)}/{expected_audio} done so far."
            )
        elif current_phase not in ("tts", "audio") and len(audio_files) == 0 and is_wip:
            advisories.append(
                f"⏳ Audio: TTS hasn't started yet (current phase: {current_phase})."
            )
        else:
            advisories.append(
                f"⚠️  Audio incomplete: {len(audio_files)}/{expected_audio} files present."
            )

        # Videos
        video_dir = job_dir / "videos"
        video_files = []
        if video_dir.exists():
            video_files = [
                f.name
                for f in video_dir.iterdir()
                if f.is_file() and f.suffix == ".mp4" and f.stat().st_size > 5000
            ]
        exp_manim = content_info.get("_expected_manim", 0)
        exp_wan = content_info.get("_expected_wan", 0)
        video_info = {
            "found": len(video_files),
            "expected_manim": exp_manim,
            "expected_wan": exp_wan,
            "expected_total": exp_manim + exp_wan,
            "files": sorted(video_files),
        }
        total_expected_video = exp_manim + exp_wan
        if total_expected_video > 0:
            if len(video_files) >= total_expected_video:
                score += 15
                advisories.append(
                    f"✅ Videos: {len(video_files)}/{total_expected_video} rendered."
                )
            elif is_wip and current_phase in (
                "manim",
                "video",
                "wan",
                "rendering",
                "visual_rendering",
            ):
                advisories.append(
                    f"🔄 Video rendering in progress — {len(video_files)}/{total_expected_video} done ({exp_manim} manim, {exp_wan} WAN expected)."
                )
            else:
                advisories.append(
                    f"⏳ Videos: {len(video_files)}/{total_expected_video} rendered — not started or pending."
                )
        else:
            advisories.append(
                "ℹ️  No video rendering expected for this job (all static/none renderers)."
            )
            score += 15  # Not expected → not a penalty

        # Avatars
        avatar_dir = job_dir / "avatars"
        avatar_files = []
        if avatar_dir.exists():
            avatar_files = [
                f.name
                for f in avatar_dir.iterdir()
                if f.is_file() and f.suffix == ".mp4" and f.stat().st_size > 10000
            ]
        expected_avatars = content_info["sections"]
        avatar_info = {
            "found": len(avatar_files),
            "expected": expected_avatars,
            "files": sorted(avatar_files),
            "complete": len(avatar_files) >= expected_avatars and expected_avatars > 0,
        }
        if len(avatar_files) >= expected_avatars and expected_avatars > 0:
            score += 15
            advisories.append(
                f"✅ Avatars: {len(avatar_files)}/{expected_avatars} generated."
            )
        elif len(avatar_files) > 0:
            score += int(15 * len(avatar_files) / max(expected_avatars, 1))
            if is_wip and current_phase == "avatar":
                advisories.append(
                    f"🔄 Avatar generation in progress — {len(avatar_files)}/{expected_avatars} sections done."
                )
            else:
                advisories.append(
                    f"⚠️  Avatars partial: {len(avatar_files)}/{expected_avatars} sections."
                )
        else:
            if is_wip and current_phase == "avatar":
                advisories.append(
                    f"🔄 Avatar generation just started (0/{expected_avatars} done)."
                )
            elif pipeline_info.get("skip_avatar"):
                advisories.append("ℹ️  Avatars skipped (skip_avatar=True).")
                score += 15
            else:
                advisories.append(
                    f"⏳ Avatars: waiting — 0/{expected_avatars} generated yet."
                )

        # ── 5. VALIDATION REPORT ──────────────────────────────────────────────
        val_path = job_dir / "v3_validation_report.txt"
        validation_info = {"exists": False, "issues_count": 0, "issues": []}
        if val_path.exists():
            try:
                val_text = val_path.read_text(encoding="utf-8")
                validation_info["exists"] = True
                lines = val_text.splitlines()
                issues = []
                for line in lines:
                    if line.strip().startswith("Section") or line.strip().startswith(
                        "["
                    ):
                        issues.append(line.strip())
                # Extract total count
                for line in lines:
                    if "Total failures:" in line:
                        try:
                            validation_info["issues_count"] = int(
                                line.split(":")[1].strip()
                            )
                        except Exception:
                            pass
                validation_info["issues"] = issues[:30]  # cap for response size
                if validation_info["issues_count"] == 0:
                    score += 10
                    advisories.append("✅ Validation passed — no issues.")
                else:
                    n = validation_info["issues_count"]
                    advisories.append(
                        f"⚠️  Validation: {n} issue(s) flagged in v3_validation_report.txt."
                    )
            except Exception as e:
                validation_info["error"] = str(e)

        # ── 6. ANALYTICS / TIMING ─────────────────────────────────────────────
        analytics_path = job_dir / "analytics.json"
        analytics_info = {"exists": False}
        if analytics_path.exists():
            try:
                with open(analytics_path, "r", encoding="utf-8") as f:
                    ana = json.load(f)
                analytics_info["exists"] = True
                analytics_info["cost_usd"] = ana.get("total_cost_usd", 0)
                analytics_info["tokens"] = ana.get("total_tokens", 0)
                analytics_info["status"] = ana.get("status", "unknown")
                analytics_info["timings"] = ana.get("timings", {})
                analytics_info["phase_breakdown"] = ana.get("phase_breakdown", {})
                score += 10
            except Exception as e:
                analytics_info["error"] = str(e)
        else:
            # Try debug_global_worker.json (V3 style)
            dbg_path = job_dir / "debug_global_worker.json"
            if dbg_path.exists():
                try:
                    with open(dbg_path, "r", encoding="utf-8") as f:
                        dbg = json.load(f)
                    analytics_info["exists"] = True
                    analytics_info["source"] = "debug_global_worker.json"
                    analytics_info["sections_processed"] = (
                        len(dbg) if isinstance(dbg, list) else "?"
                    )
                    score += 5
                except Exception:
                    pass

        # ── 7. STUCK PHASE DETECTION ──────────────────────────────────────────
        if is_wip and elapsed_seconds:
            phase_timeout_minutes = {
                "tts": 30,
                "audio": 30,
                "manim": 60,
                "rendering": 90,
                "visual_rendering": 120,
                "wan": 120,
                "video": 120,
                "kie": 120,
                "avatar": 60,
            }
            timeout = phase_timeout_minutes.get(current_phase, 45)
            elapsed_min = elapsed_seconds // 60
            if elapsed_min > timeout:
                advisories.append(
                    f"🚨 POSSIBLE STALL: Job has been in phase '{current_phase}' "
                    f"for ~{elapsed_min} minutes (typical timeout: {timeout}m). "
                    f"Check app.log for errors."
                )

        # ── 8. HEALTH SCORE & GRADE ───────────────────────────────────────────
        score = min(score, max_score)
        pct = (score / max_score) * 100
        if pct >= 80:
            grade = "HEALTHY"
        elif pct >= 60:
            grade = "FAIR"
        elif pct >= 40:
            grade = "DEGRADED"
        else:
            grade = "CRITICAL"

        return jsonify(
            {
                "job_id": job_id,
                "status": status,
                "is_wip": is_wip,
                "created_at": created_str,
                "elapsed_seconds": elapsed_seconds,
                "elapsed_human": f"{elapsed_seconds // 3600}h {(elapsed_seconds % 3600) // 60}m {elapsed_seconds % 60}s"
                if elapsed_seconds
                else None,
                "error": job.get("error"),
                "source": source_info,
                "pipeline": pipeline_info,
                "phase": phase_info,
                "content": content_info,
                "assets": {
                    "audio": audio_info,
                    "videos": video_info,
                    "avatars": avatar_info,
                },
                "validation": validation_info,
                "analytics": analytics_info,
                "advisories": advisories,
                "health_score": score,
                "health_max": max_score,
                "health_pct": round(pct, 1),
                "health_grade": grade,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e), "traceback": _traceback.format_exc()}), 500


@app.route("/jobs", methods=["GET"])
def list_all_jobs():
    """List all jobs with their status (persisted across restarts)."""
    jobs = job_manager.get_all_jobs()

    def get_pipeline_version(j):
        # 1. From job params (stored at submit time)
        pv = j.get("params", {}).get("pipeline_version", "")
        if pv:
            return pv
        # 2. Fallback: read from presentation.json
        try:
            job_folder = Path(JOBS_DIR) / j["id"]
            pres_path = job_folder / "presentation.json"
            if pres_path.exists():
                import json as _json

                with open(pres_path) as f:
                    pres = _json.load(f)
                return pres.get("pipeline_version", "")
        except Exception:
            pass
        return ""

    return jsonify(
        {
            "jobs": [
                {
                    "job_id": j["id"],
                    "type": j.get("type", "unknown"),
                    "status": j["status"],
                    "progress": j["progress"],
                    "status_message": j.get("status_message") or j.get("message", ""),
                    "created_at": j["created_at"],
                    "completed_at": j["completed_at"],
                    "error": j.get("error"),
                    "pipeline_version": get_pipeline_version(j),
                    "params": {
                        "subject": j.get("params", {}).get("subject", ""),
                        "grade": j.get("params", {}).get("grade", ""),
                        "dry_run": j.get("params", {}).get("dry_run", False),
                    },
                }
                for j in jobs
            ],
            "total": len(jobs),
        }
    )


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
            with open(analytics_path, "r") as f:
                analytics_data = json.load(f)
            return jsonify(
                {"job_id": job_id, "has_analytics": True, "analytics": analytics_data}
            )
        except Exception as e:
            return jsonify(
                {
                    "job_id": job_id,
                    "has_analytics": False,
                    "error": f"Failed to load analytics: {str(e)}",
                }
            ), 500
    else:
        # No analytics file - return basic job info
        return jsonify(
            {
                "job_id": job_id,
                "has_analytics": False,
                "message": "Analytics not available for this job (pre-analytics feature or failed early)",
                "basic_info": {
                    "status": job["status"],
                    "created_at": job["created_at"],
                    "completed_at": job.get("completed_at"),
                    "error": job.get("error"),
                },
            }
        )


@app.route("/job/<job_id>/retry", methods=["POST"])
def retry_failed_job(job_id):
    """Retry a failed job - from point of failure if artifacts exist, or fresh if they don't."""
    try:
        if False:  # is_job_running():
            current_id = get_current_job_ids()
            return jsonify(
                {
                    "status": "busy",
                    "message": "A job is already running. Please wait for it to complete.",
                    "current_job_id": current_id,
                }
            ), 409

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

        with open(source_markdown_path, "r") as f:
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
        chunker_exists = (
            (artifacts_dir / "01_chunker.json").exists()
            if artifacts_dir.exists()
            else False
        )
        planner_exists = (
            (artifacts_dir / "02_planner.json").exists()
            if artifacts_dir.exists()
            else False
        )

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
            job_manager.update_job(
                job_id,
                {
                    "status": "pending",
                    "progress": 0,
                    "message": "Preparing fresh restart...",
                    "error": None,
                    "failure_message": None,
                    "failed_phase": None,
                },
                persist=True,
            )

            # Save markdown content for the job processor
            with open(source_markdown_path, "w") as f:
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
                tts_provider=tts_provider,
            )

            return jsonify(
                {
                    "status": "started",
                    "job_id": job_id,
                    "message": "Retry started fresh (cleared previous artifacts)",
                    "mode": "fresh",
                }
            )
        else:
            # Resume from failure point - artifacts exist
            analytics_path = job_folder / "analytics.json"
            error_msg = ""
            if analytics_path.exists():
                with open(analytics_path, "r") as f:
                    analytics = json.load(f)
                error_msg = analytics.get("error", "")

            failed_section_idx = _determine_failed_section_idx(job_folder, error_msg)

            # ISS-203: Reset job state completely before launching worker
            job_manager.update_job(
                job_id,
                {
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
                    "steps_completed": 0,
                },
                persist=True,
            )

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
                    status_callback=lambda phase, msg: job_manager.update_job(
                        job_id,
                        {
                            "message": f"{phase}: {msg}",
                            "status_message": f"{phase}: {msg}",
                        },
                        persist=True,
                    ),
                )

                # V2.5 FIX: Use lock for thread-safe write after resume
                presentation_path = job_folder / "presentation.json"
                with presentation_lock:
                    with open(presentation_path, "w") as f:
                        json.dump(presentation, f, indent=2)

                return {"presentation_path": str(presentation_path)}

            # Use run_job_async for proper lifecycle management (same as fresh jobs)
            run_job_async(job_id, resume_job_wrapper)

            return jsonify(
                {
                    "status": "started",
                    "job_id": job_id,
                    "message": f"Retry resuming from section {failed_section_idx}",
                    "mode": "resume",
                    "resume_from_section": failed_section_idx,
                }
            )

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
        job_manager.update_job(
            job_id,
            {
                "status": "failed",
                "error": "Force stopped by user",
                "failure_message": "User initiated force stop",
            },
            persist=True,
        )

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
            return jsonify(
                {"error": "Presentation not found - job must complete LLM phase first"}
            ), 400

        with open(presentation_path, "r") as f:
            presentation = json.load(f)

        data = request.get_json() or {}
        phase = data.get("phase", "video_render")
        section_ids = data.get("section_ids")
        user_feedback = data.get("user_feedback")

        # V2.5 FIX: Validate section_ids exist in presentation
        if section_ids:
            valid_ids = {s.get("section_id") for s in presentation.get("sections", [])}
            invalid_ids = set(section_ids) - valid_ids
            if invalid_ids:
                return jsonify(
                    {
                        "error": f"Invalid section_ids: {sorted(invalid_ids)}. Valid IDs: {sorted(valid_ids)}"
                    }
                ), 400

        if phase == "manim_codegen":
            result = _retry_manim_codegen(job_id, job_folder, presentation, section_ids)
        elif phase == "video_render":
            result = _retry_video_render(job_id, job_folder, presentation, section_ids)
        elif phase == "wan_render":
            result = _retry_wan_render(
                job_id,
                job_folder,
                presentation,
                section_ids,
                user_feedback=user_feedback,
            )
        elif phase == "manim_render":
            result = _retry_manim_render(job_id, job_folder, presentation, section_ids)
        elif phase == "avatar_generation":
            result = _retry_avatar_generation(
                job_id, job_folder, presentation, section_ids
            )
        else:
            return jsonify(
                {
                    "error": f"Unknown phase: {phase}. Valid: manim_codegen, wan_render, manim_render, avatar_generation"
                }
            ), 400

        # V2.5 FIX: Use presentation_lock to prevent race conditions with background threads
        with presentation_lock:
            with open(presentation_path, "w") as f:
                json.dump(presentation, f, indent=2)

        return jsonify({"status": "success", "phase": phase, "result": result})

    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


def _retry_manim_codegen(
    job_id: str, job_folder: Path, presentation: dict, section_ids: list = None
) -> dict:
    """Retry Manim code generation for specific sections.

    V2.6 FIX: After regenerating code, this function now:
    1. Deletes existing .mp4 files for the section
    2. Calls _retry_manim_render to generate new videos with the new code
    """
    from core.agents.manim_code_generator import (
        ManimCodeGenerator,
        build_manim_section_data,
        integrate_manim_code_into_section,
    )
    import glob

    manim_generator = ManimCodeGenerator()
    results = {"success": [], "failed": [], "skipped": []}
    sections_to_render = []  # V2.6: Track sections that need re-rendering

    failed_sections_path = job_folder / "manim_failed_sections.json"
    if failed_sections_path.exists() and section_ids is None:
        with open(failed_sections_path, "r") as f:
            failed_data = json.load(f)
        section_ids = [s["section_id"] for s in failed_data.get("sections", [])]

    videos_dir = job_folder / "videos"

    for section in presentation.get("sections", []):
        section_id = section.get("section_id")
        renderer = section.get("renderer", "")

        logger.debug(
            f"Checking Section {section_id} (Renderer: {renderer}) for retry. Target IDs: {section_ids}"
        )

        if renderer != "manim":
            continue

        if section_ids and section_id not in section_ids:
            results["skipped"].append(
                {"section_id": section_id, "reason": "Not in retry list"}
            )
            continue

        # Check for existing manim_code in multiple locations (V2.5 compatibility)
        has_code = (
            section.get("manim_code")  # Top-level (v1.5)
            or section.get("render_spec", {})
            .get("manim_scene_spec", {})
            .get("manim_code")  # Nested (v2.5)
        )
        logger.debug(f"Section {section_id} has_code={bool(has_code)}")
        if has_code:
            if section_ids is None:
                logger.debug(f"Section {section_id} SKIPPED - already has valid code")
                results["skipped"].append(
                    {"section_id": section_id, "reason": "Already has valid code"}
                )
                continue
            else:
                logger.debug(
                    f"Forcing regen for Section {section_id} despite existing code."
                )

        logger.debug(f"Section {section_id} PROCEEDING to code generation")
        try:
            print(f"[RETRY] Regenerating Manim code for section {section_id}")
            manim_input = build_manim_section_data(
                section=section,
                narration_segments=section.get("narration", {}).get("segments", []),
                visual_beats=section.get("visual_beats", []),
                segment_enrichments=[],
            )

            manim_code, validation_errors = manim_generator.generate(manim_input)

            if manim_code and len(manim_code) > 100:
                section = integrate_manim_code_into_section(section, manim_code)
                results["success"].append(
                    {"section_id": section_id, "code_length": len(manim_code)}
                )
                print(
                    f"[RETRY] Manim code regenerated for section {section_id}: {len(manim_code)} chars"
                )

                # V2.6 FIX: Delete old video files for this section
                if videos_dir.exists():
                    # Use set to avoid duplicate deletion attempts
                    old_videos = set(videos_dir.glob(f"topic_{section_id}_*.mp4"))
                    for old_video in old_videos:
                        print(f"[RETRY] Deleting old video: {old_video.name}")
                        try:
                            old_video.unlink()
                        except FileNotFoundError:
                            pass  # Already deleted, ignore

                # Mark this section for re-rendering
                sections_to_render.append(section_id)
            else:
                results["failed"].append(
                    {"section_id": section_id, "errors": validation_errors}
                )
                print(
                    f"[RETRY] Manim code regeneration failed for section {section_id}"
                )
        except Exception as e:
            results["failed"].append({"section_id": section_id, "error": str(e)})
            print(
                f"[RETRY] Manim code regeneration error for section {section_id}: {e}"
            )

    if failed_sections_path.exists() and results["success"]:
        failed_sections_path.unlink()

    # V2.6 FIX: Automatically trigger Manim render for sections with new code
    if sections_to_render:
        print(f"[RETRY] Triggering Manim render for sections: {sections_to_render}")
        render_results = _retry_manim_render(
            job_id, job_folder, presentation, sections_to_render
        )
        results["render_results"] = render_results

    return results


def _retry_video_render(
    job_id: str, job_folder: Path, presentation: dict, section_ids: list = None
) -> dict:
    """Retry video rendering for specific sections."""
    from core.renderer_executor import execute_renderer

    videos_dir = job_folder / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    # V2.6 FIX: Read video_provider from job params (set from Dashboard)
    job = job_manager.get_job(job_id)
    params = job.get("params", {}) if job else {}
    video_provider = params.get("video_provider", "kie")  # Default to Kie if not set

    results = {"success": [], "failed": [], "skipped": []}

    for section in presentation.get("sections", []):
        section_id = section.get("section_id")
        renderer = section.get("renderer", "none")
        section_type = section.get("section_type", "")

        if renderer == "none" or section_type in ["intro", "summary", "quiz", "memory"]:
            continue

        if section_ids and section_id not in section_ids:
            results["skipped"].append(
                {"section_id": section_id, "reason": "Not in retry list"}
            )
            continue

        existing_video = section.get("video_path")
        if existing_video and (job_folder / existing_video).exists():
            if section_ids is None:
                results["skipped"].append(
                    {"section_id": section_id, "reason": "Video already exists"}
                )
                continue

        try:
            print(
                f"[RETRY] Re-rendering video for section {section_id} (renderer: {renderer})"
            )

            result = execute_renderer(
                topic=section,
                output_dir=str(videos_dir),
                dry_run=False,
                skip_wan=False,
                trace_output_dir=str(job_folder),
                strict_mode=True,
                video_provider=video_provider,
            )

            if result.get("status") == "success":
                video_path = result.get("video_path")
                if video_path:
                    rel_path = Path(video_path).name
                    section["video_path"] = f"videos/{rel_path}"
                results["success"].append(
                    {"section_id": section_id, "video_path": video_path}
                )
                print(f"[RETRY] Video rendered for section {section_id}: {video_path}")
            else:
                results["failed"].append(
                    {"section_id": section_id, "error": result.get("error")}
                )
                print(
                    f"[RETRY] Video render failed for section {section_id}: {result.get('error')}"
                )
        except Exception as e:
            results["failed"].append({"section_id": section_id, "error": str(e)})
            print(f"[RETRY] Video render error for section {section_id}: {e}")

    return results


def _retry_wan_render(
    job_id: str,
    job_folder: Path,
    presentation: dict,
    section_ids: list = None,
    user_feedback: str = None,
) -> dict:
    """Retry WAN video rendering for sections with renderer='video'."""
    from core.renderer_executor import execute_renderer

    videos_dir = job_folder / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    # V2.6 FIX: Read video_provider from job params (set from Dashboard)
    job = job_manager.get_job(job_id)
    params = job.get("params", {}) if job else {}
    video_provider = params.get("video_provider", "kie")  # Default to Kie if not set
    print(f"[RETRY-WAN] Using video_provider: {video_provider}")

    results = {"success": [], "failed": [], "skipped": []}

    for section in presentation.get("sections", []):
        section_id = section.get("section_id")
        renderer = section.get("renderer", "none")

        # Only process WAN/video sections
        if renderer not in ["video", "wan"]:
            continue

        if section_ids and section_id not in section_ids:
            results["skipped"].append(
                {"section_id": section_id, "reason": "Not in retry list"}
            )
            continue

        try:
            print(f"[RETRY-WAN] Re-rendering WAN video for section {section_id}")

            # V2.6 FIX: Use KieBatchGenerator directly to match original job filenames ({beat_id}.mp4)
            # This ensures idempotency works (skips existing files) and naming is consistent.
            from render.wan.kie_batch_generator import KieBatchGenerator

            # Collect video_prompts from section
            video_prompts = section.get("video_prompts", [])

            # Also check if it's a recap section
            if section.get("section_type") == "recap":
                # Recap scenes also need to be handled if they have prompts
                recap_scenes = section.get("recap_scenes", [])
                if recap_scenes:
                    # Adapt recap scenes to video_prompts format if needed, but usually
                    # video_prompts are already populated for background job.
                    # If empty, we might need to construct them, but for retry lets rely on video_prompts
                    pass

            if video_prompts:
                use_local = section.get("use_local_gpu", True)
                print(
                    f"[RETRY-WAN] Section {section_id}: {len(video_prompts)} prompts → {'Local GPU' if use_local else 'Kie.ai WAN'}"
                )

                batch_results = {}

                if use_local:
                    # Route to Local GPU (same as background job router)
                    try:
                        from render.wan.local_gpu_client import LocalGPUClient

                        local_client = LocalGPUClient()
                        if local_client.is_available():
                            for beat in video_prompts:
                                beat_id = beat.get("beat_id", "")
                                prompt = (
                                    beat.get("prompt")
                                    or beat.get("wan_prompt")
                                    or beat.get("video_prompt")
                                    or ""
                                )
                                duration = int(beat.get("duration_hint", 5))
                                out_path = str(videos_dir / f"{beat_id}.mp4")
                                video_path = local_client.generate_video(
                                    prompt, duration=duration, output_path=out_path
                                )
                                if video_path:
                                    batch_results[beat_id] = video_path
                                    print(f"[LocalGPU] ✓ Beat {beat_id} done")
                                else:
                                    print(
                                        f"[LocalGPU] ✗ Beat {beat_id} failed → falling back to Kie.ai"
                                    )
                                    # Per-beat fallback to WAN
                                    wan_status_path = job_folder / "wan_status.json"
                                    batch_gen = KieBatchGenerator(
                                        status_file_path=str(wan_status_path)
                                    )
                                    fb = batch_gen.generate_batch(
                                        [beat],
                                        str(videos_dir),
                                        user_feedback=user_feedback,
                                    )
                                    batch_results.update(fb)
                        else:
                            print(
                                f"[RETRY-WAN] Local GPU unavailable — falling back all beats to Kie.ai WAN"
                            )
                            wan_status_path = job_folder / "wan_status.json"
                            batch_gen = KieBatchGenerator(
                                status_file_path=str(wan_status_path)
                            )
                            batch_results = batch_gen.generate_batch(
                                video_prompts,
                                str(videos_dir),
                                user_feedback=user_feedback,
                            )
                    except Exception as e:
                        print(
                            f"[RETRY-WAN] LocalGPUClient error: {e} — falling back to Kie.ai WAN"
                        )
                        wan_status_path = job_folder / "wan_status.json"
                        batch_gen = KieBatchGenerator(
                            status_file_path=str(wan_status_path)
                        )
                        batch_results = batch_gen.generate_batch(
                            video_prompts, str(videos_dir), user_feedback=user_feedback
                        )
                else:
                    # Route to Kie.ai WAN (biology/anatomy)
                    wan_status_path = job_folder / "wan_status.json"
                    batch_gen = KieBatchGenerator(status_file_path=str(wan_status_path))
                    batch_results = batch_gen.generate_batch(
                        video_prompts, str(videos_dir), user_feedback=user_feedback
                    )

                generated_count = sum(1 for p in batch_results.values() if p)

                if generated_count > 0:
                    results["success"].append(
                        {"section_id": section_id, "count": generated_count}
                    )
                    section["beat_video_paths"] = [
                        f"videos/{Path(p).name}" for p in batch_results.values() if p
                    ]
                else:
                    results["skipped"].append(
                        {
                            "section_id": section_id,
                            "reason": "No new videos generated (all existed or failed)",
                        }
                    )

                result = {"status": "success", "video_path": None}
            else:
                print(
                    f"[RETRY-WAN] No video_prompts found for section {section_id} - falling back to legacy renderer"
                )
                # Fallback to legacy path if no pre-compiled prompts (e.g. old jobs)
                result = execute_renderer(
                    topic=section,
                    output_dir=str(videos_dir),
                    dry_run=False,
                    skip_wan=False,
                    trace_output_dir=str(job_folder),
                    strict_mode=True,
                    video_provider=video_provider,
                )

            if result.get("status") == "success":
                video_path = result.get("video_path")
                if video_path:
                    rel_path = Path(video_path).name
                    section["video_path"] = f"videos/{rel_path}"
                results["success"].append(
                    {"section_id": section_id, "video_path": video_path}
                )
            else:
                results["failed"].append(
                    {"section_id": section_id, "error": result.get("error")}
                )
        except Exception as e:
            results["failed"].append({"section_id": section_id, "error": str(e)})

    return results


def _retry_manim_render(
    job_id: str, job_folder: Path, presentation: dict, section_ids: list = None
) -> dict:
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
            results["skipped"].append(
                {"section_id": section_id, "reason": "Not in retry list"}
            )
            continue

        try:
            print(f"[RETRY-MANIM] Re-rendering Manim video for section {section_id}")

            result = execute_renderer(
                topic=section,
                output_dir=str(videos_dir),
                dry_run=False,
                skip_wan=True,  # Skip WAN for Manim sections
                trace_output_dir=str(job_folder),
                strict_mode=True,
            )

            if result.get("status") == "success":
                video_path = result.get("video_path")
                if video_path:
                    rel_path = Path(video_path).name
                    section["video_path"] = f"videos/{rel_path}"
                results["success"].append(
                    {"section_id": section_id, "video_path": video_path}
                )
            else:
                results["failed"].append(
                    {"section_id": section_id, "error": result.get("error")}
                )
        except Exception as e:
            results["failed"].append({"section_id": section_id, "error": str(e)})

    return results


def _retry_avatar_generation(
    job_id: str,
    job_folder: Path,
    presentation: dict,
    section_ids: list = None,
    languages: list = None,
    speaker: str = None,
) -> dict:
    """Retry avatar generation - uses same parallel logic as new jobs.

    Args:
        languages (list, optional): List of language codes for multi-language generation
        speaker (str, optional): Voice ID for non-English languages
    """
    from core.agents.avatar_generator import AvatarGenerator
    import time

    avatars_dir = job_folder / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)

    generator = AvatarGenerator()

    # Filter presentation to only include sections we want to retry
    if section_ids:
        filtered_presentation = {
            "sections": [
                s
                for s in presentation.get("sections", [])
                if s.get("section_id") in section_ids
            ]
        }
    else:
        filtered_presentation = presentation

    lang_info = f" for {len(languages)} language(s)" if languages else ""
    print(
        f"[RETRY-AVATAR] Using parallel submit for {len(filtered_presentation['sections'])} sections{lang_info}",
        flush=True,
    )

    # Use the SAME parallel submit that new jobs use, with language support
    submit_results = generator.submit_parallel_job(
        filtered_presentation,
        job_id,
        str(job_folder),
        languages=languages,
        speaker=speaker,
    )

    tasks = submit_results.get("queued", [])
    if not tasks:
        return {
            "success": [],
            "failed": submit_results.get("failed", []),
            "skipped": submit_results.get("skipped", []),
        }

    print(f"[RETRY-AVATAR] Submitted {len(tasks)} tasks. Polling...", flush=True)

    # Poll ALL tasks in parallel (same as new jobs)
    active_tasks = list(tasks)
    results = {
        "success": [],
        "failed": [],
        "skipped": submit_results.get("skipped", []),
    }
    start_time = time.time()
    max_wait = 1800  # 30 min

    while active_tasks and (time.time() - start_time < max_wait):
        still_active = []

        for task in active_tasks:
            section_id = task["section_id"]
            task_id = task["task_id"]

            try:
                status_resp = generator.check_status(task_id)
                status = status_resp.get("status")

                if status in ["completed", "success", "done"]:
                    output_path = avatars_dir / f"section_{section_id}_avatar.mp4"

                    if generator.download_video(task_id, str(output_path)):
                        # Update presentation.json
                        for sec in presentation["sections"]:
                            # FIX: Use string comparison to avoid int/str type mismatch
                            if str(sec.get("section_id")) == str(section_id):
                                sec["avatar_path"] = (
                                    f"avatars/section_{section_id}_avatar.mp4"
                                )
                                sec["avatar_video"] = (
                                    f"avatars/section_{section_id}_avatar.mp4"
                                )
                                sec["avatar_status"] = "completed"
                                # CRITICAL FIX: Store task_id for repair feature
                                if task_id:
                                    sec["avatar_task_id"] = task_id
                                    sec["avatar_id"] = task_id

                                # Extract Vimeo and B2 URLs if available
                                raw = status_resp.get("raw_response", {})
                                vimeo_url = raw.get("vimeo_url")
                                b2_url = raw.get("b2_url")

                                if vimeo_url:
                                    sec["vimeo_url"] = vimeo_url
                                    sec["vimeo_uploaded"] = True
                                if b2_url:
                                    sec["b2_url"] = b2_url
                                    sec["b2_uploaded"] = True

                                break

                        results["success"].append(
                            {
                                "section_id": section_id,
                                "task_id": task_id,
                                "vimeo_url": vimeo_url,
                                "b2_url": b2_url,
                            }
                        )
                        print(
                            f"[RETRY-AVATAR] OK Sec {section_id} downloaded", flush=True
                        )
                        # V2.5 FIX: Removed write from inside loop - will save once at end with lock
                    else:
                        results["failed"].append(
                            {"section_id": section_id, "error": "Download failed"}
                        )

                elif status in ["failed", "error", "not_found"]:
                    results["failed"].append(
                        {"section_id": section_id, "error": status}
                    )
                    print(
                        f"[RETRY-AVATAR] FAIL Sec {section_id} failed: {status}",
                        flush=True,
                    )

                else:
                    # Still processing
                    still_active.append(task)

            except Exception as e:
                still_active.append(task)  # Keep retrying

        active_tasks = still_active

        if active_tasks:
            print(
                f"[RETRY-AVATAR] {len(active_tasks)} active, {len(results['success'])} done",
                flush=True,
            )
            time.sleep(10)

    # Timeout handling
    for task in active_tasks:
        results["failed"].append({"section_id": task["section_id"], "error": "Timeout"})

    # V2.5 FIX: Single write at end with lock (prevents race condition with WAN/TTS threads)
    if results["success"]:  # Only write if we actually updated something
        # RELOAD from disk to avoid overwriting generator updates (Vimeo/B2 URLs)
        current_presentation = presentation
        try:
            with presentation_lock:
                with open(job_folder / "presentation.json", "r", encoding="utf-8") as f:
                    current_presentation = json.load(f)
        except Exception as e:
            print(f"[RETRY-AVATAR] Warning: converting presentation reload failed: {e}")

        # Re-apply our successful updates to the FRESH presentation object
        for success_item in results["success"]:
            sid = success_item["section_id"]
            tid = success_item["task_id"]
            vimeo = success_item.get("vimeo_url")
            b2 = success_item.get("b2_url")

            # Find section in fresh presentation
            for sec in current_presentation.get("sections", []):
                if sec["section_id"] == sid:
                    # Update standard fields
                    sec["avatar_path"] = f"avatars/section_{sid}_avatar.mp4"
                    sec["avatar_video"] = f"avatars/section_{sid}_avatar.mp4"
                    sec["avatar_status"] = "completed"

                    if tid:
                        sec["avatar_task_id"] = tid
                        sec["avatar_id"] = tid

                    # Re-apply Vimeo/B2 URLs since they weren't saved to disk yet
                    if vimeo:
                        sec["vimeo_url"] = vimeo
                        sec["vimeo_uploaded"] = True
                    if b2:
                        sec["b2_url"] = b2
                        sec["b2_uploaded"] = True

                    break

        with presentation_lock:
            with open(job_folder / "presentation.json", "w", encoding="utf-8") as f:
                json.dump(current_presentation, f, indent=2)

    print(
        f"[RETRY-AVATAR] Complete: {len(results['success'])} success, {len(results['failed'])} failed",
        flush=True,
    )
    return results


def _retry_tts_generation(
    job_id: str, job_folder: Path, presentation: dict, section_ids: list = None
) -> dict:
    """Retry TTS generation for specific sections (or all if None)."""
    from core.tts_duration import update_durations_simplified

    results = {"success": [], "failed": [], "skipped": []}

    # Get tts_provider from job params or default to edge_tts
    job = job_manager.get_job(job_id)
    params = job.get("params", {})
    tts_provider = params.get("tts_provider", "edge_tts")
    if tts_provider == "edge":
        tts_provider = "edge_tts"  # Force fix

    try:
        print(
            f"[RETRY] Starting TTS generation retry for job {job_id} using {tts_provider}"
        )
        # update_durations_simplified updates the presentation object in-place
        _ = update_durations_simplified(
            presentation=presentation,
            output_dir=job_folder,
            production_provider=tts_provider,
        )

        # Count progress
        audio_dir = job_folder / "audio"
        audio_files = list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.wav"))

        results["success"].append(
            {
                "message": f"TTS generation completed. {len(audio_files)} audio files present.",
                "audio_count": len(audio_files),
            }
        )
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

    with open(planner_path, "r") as f:
        planner_data = json.load(f)
        blueprints = planner_data.get("sections", [])

    content_section_count = 0
    for i, bp in enumerate(blueprints):
        section_type = bp.get("section_type", "")
        section_id = bp.get("section_id", "")

        if section_type in ["memory", "recap"]:
            continue

        artifact_idx = content_section_count + 3
        narration_file = (
            artifacts_dir / f"{artifact_idx:02d}_{section_id}_narration.json"
        )
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
                outputs.append(
                    {
                        "name": f.name,
                        "path": f"artifacts/{f.name}",
                        "category": "agent_output",
                        "size_bytes": stat.st_size,
                        "description": _get_artifact_description(f.name),
                    }
                )

    # Check for llm_responses directory (raw LLM outputs)
    llm_responses_dir = job_folder / "llm_responses"
    if llm_responses_dir.exists():
        for f in sorted(llm_responses_dir.iterdir()):
            if f.is_file():
                stat = f.stat()
                outputs.append(
                    {
                        "name": f.name,
                        "path": f"llm_responses/{f.name}",
                        "category": "raw_llm",
                        "size_bytes": stat.st_size,
                        "description": "Raw LLM response with prompt",
                    }
                )

    # Check for render_prompts.json
    render_prompts = job_folder / "render_prompts.json"
    if render_prompts.exists():
        stat = render_prompts.stat()
        outputs.append(
            {
                "name": "render_prompts.json",
                "path": "render_prompts.json",
                "category": "renderer",
                "size_bytes": stat.st_size,
                "description": "All Manim/WAN video generation prompts",
            }
        )

    # Check for generation_trace.json
    trace_file = job_folder / "generation_trace.json"
    if trace_file.exists():
        stat = trace_file.stat()
        outputs.append(
            {
                "name": "generation_trace.json",
                "path": "generation_trace.json",
                "category": "trace",
                "size_bytes": stat.st_size,
                "description": "Full pipeline execution trace",
            }
        )

    # Check for source markdown
    source_md = job_folder / "source_markdown.md"
    if source_md.exists():
        stat = source_md.stat()
        outputs.append(
            {
                "name": "source_markdown.md",
                "path": "source_markdown.md",
                "category": "source",
                "size_bytes": stat.st_size,
                "description": "Input markdown from PDF/file",
            }
        )

    return jsonify(
        {
            "job_id": job_id,
            "total_outputs": len(outputs),
            "outputs": outputs,
            "categories": {
                "agent_output": "Structured outputs from pipeline agents (Chunker, Planner, NarrationWriter, VisualSpecArtist)",
                "raw_llm": "Raw LLM API responses with full prompts",
                "renderer": "Prompts sent to visual renderers (Manim, WAN)",
                "trace": "Pipeline execution trace with all events",
                "source": "Original input content",
            },
        }
    )


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

        return jsonify(
            {
                "job_id": job_id,
                "file_path": file_path,
                "file_type": file_type,
                "size_bytes": len(content),
                "content": parsed_content if file_type == "json" else content,
            }
        )
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {str(e)}"}), 500


def process_pdf_job(
    job_id: str,
    pdf_path: str,
    subject: str,
    grade: str,
    output_dir: str,
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    source_file: Optional[str] = None,
    tts_provider: str = "edge_tts",
) -> dict:
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
            source_file=source_file,
        )
        return result
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)


def process_pdf_job_v15(
    job_id: str,
    pdf_path: str,
    subject: str,
    grade: str,
    output_dir: str,
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    source_file: Optional[str] = None,
    tts_provider: str = "edge_tts",
    video_provider: str = "kie",
) -> dict:
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
        tts_provider=tts_provider,
        video_provider=video_provider,
    )


def process_document_job_v15(
    job_id: str,
    document_path: str,
    subject: str,
    grade: str,
    output_dir: str,
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    source_file: Optional[str] = None,
    tts_provider: str = "edge_tts",
    video_provider: str = "kie",
) -> dict:
    """ISS-206/207: Process PDF/DOC/DOCX/ODT using V1.5 Optimized pipeline.

    1. Convert document to Markdown using Datalab API (supports PDF, DOC, DOCX, ODT)
    2. Capture page_count from Datalab response
    3. Run V1.5 optimized pipeline on the markdown
    """
    from core.datalab_client import document_to_markdown, DatalabConversionError
    from pathlib import Path

    try:
        file_ext = Path(document_path).suffix.lower()
        job_manager.update_job(
            job_id,
            {
                "current_phase_key": "document_conversion",
                "status_message": f"Converting {file_ext.upper()} to Markdown...",
            },
            persist=True,
        )

        # ISS-206/207: Use new document_to_markdown with ConversionResult
        conversion_result = document_to_markdown(document_path)
        markdown_content = conversion_result.markdown
        page_count = conversion_result.page_count

        # Save raw markdown for comparison/debugging
        source_md_path = Path(output_dir) / "source_markdown.md"
        with open(source_md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(
            f"[V1.5 Optimized] Saved source markdown to {source_md_path} ({len(markdown_content)} chars, {page_count} pages)"
        )

        content_preview = markdown_content[:300].replace("\n", " ").strip()
        if len(markdown_content) > 300:
            content_preview += "..."

        # ISS-207: Store page_count in job metadata
        job_manager.update_job(
            job_id,
            {
                "content_preview": content_preview,
                "page_count": page_count,
                "source_type": file_ext.replace(".", ""),
            },
            persist=True,
        )

        def status_callback(jid, phase, message):
            job_manager.update_job(
                jid,
                {"current_phase_key": phase, "status_message": message},
                persist=True,
            )

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
            skip_wan=skip_wan,
            video_provider=video_provider,
        )

        pres_path = output_path / "presentation.json"
        with open(pres_path, "w") as f:
            json.dump(presentation, f, indent=2)

        analytics_summary = (
            tracker.get_summary() if hasattr(tracker, "get_summary") else {}
        )

        # ISS-207: Add page_count to analytics
        analytics_summary["page_count"] = page_count

        return {
            "status": "success",
            "presentation": presentation,
            "analytics": analytics_summary,
            "output_path": str(pres_path),
            "pipeline_version": "1.5",
            "source_type": file_ext.replace(".", ""),
            "page_count": page_count,
        }
    except DatalabConversionError as e:
        raise RuntimeError(f"Document conversion failed: {e}")
    finally:
        if os.path.exists(document_path):
            os.unlink(document_path)


def process_document_job_v15_v2(
    job_id: str,
    document_path: str,
    subject: str,
    grade: str,
    output_dir: str,
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    source_file: Optional[str] = None,
    tts_provider: str = "edge_tts",
    pipeline_version: str = "v15_v2_director",
    generation_scope: str = "full",
    model: Optional[str] = None,
    video_provider: str = "kie",
) -> dict:
    """Process PDF/DOC/DOCX/ODT using V1.5 V2 Unified pipeline with image handling.

    1. Convert document to Markdown using Datalab API (captures images)
    2. Save images to job/images/ folder with green screen processing
    3. Run V2 unified pipeline with images_list
    """
    from core.datalab_client import document_to_markdown, DatalabConversionError
    from pathlib import Path

    try:
        file_ext = Path(document_path).suffix.lower()
        job_manager.update_job(
            job_id,
            {
                "current_phase_key": "document_conversion",
                "status_message": f"Converting {file_ext.upper()} to Markdown...",
            },
            persist=True,
        )

        conversion_result = document_to_markdown(document_path)
        markdown_content = conversion_result.markdown
        page_count = conversion_result.page_count
        images_dict = conversion_result.images

        print(
            f"[V1.5-V2] Document converted: {len(markdown_content)} chars, {page_count} pages, {len(images_dict)} images"
        )

        job_manager.update_job(
            job_id,
            {
                "page_count": page_count,
                "source_type": file_ext.replace(".", ""),
                "image_count": len(images_dict),
            },
            persist=True,
        )

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
            generation_scope=generation_scope,
            video_provider=video_provider,
        )
    except DatalabConversionError as e:
        raise RuntimeError(f"Document conversion failed: {e}")
    finally:
        if os.path.exists(document_path):
            os.unlink(document_path)


def process_document_job_v3(
    job_id: str,
    document_path: str,
    subject: str,
    grade: str,
    output_dir: str,
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    skip_manim: bool = False,
    skip_threejs: bool = False,
    source_file: Optional[str] = None,
    tts_provider: str = "edge_tts",
    model: Optional[str] = None,
    **kwargs,
) -> dict:
    """V3 document processor: PDF/DOC/DOCX → Markdown → V3 pipeline."""
    from core.datalab_client import document_to_markdown, DatalabConversionError
    from pathlib import Path

    # Backward compat: accept skip_threejs as alias for skip_manim
    _skip_manim = skip_manim or skip_threejs

    try:
        file_ext = Path(document_path).suffix.lower()
        job_manager.update_job(
            job_id,
            {
                "current_phase_key": "document_conversion",
                "status_message": f"[V3] Converting {file_ext.upper()} to Markdown...",
            },
            persist=True,
        )

        conversion_result = document_to_markdown(document_path)
        markdown_content = conversion_result.markdown
        page_count = conversion_result.page_count
        images_dict = conversion_result.images  # ← FIX: extract source images from PDF

        print(
            f"[V3 Document] Converted {file_ext}: {len(markdown_content)} chars, {page_count} pages, {len(images_dict)} images"
        )

        job_manager.update_job(
            job_id,
            {
                "page_count": page_count,
                "source_type": file_ext.replace(".", ""),
                "image_count": len(images_dict),
            },
            persist=True,
        )

        return process_markdown_job_v3(
            job_id=job_id,
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            output_dir=output_dir,
            dry_run=dry_run,
            skip_wan=skip_wan,
            skip_avatar=skip_avatar,
            skip_manim=_skip_manim,
            source_file=source_file,
            tts_provider=tts_provider,
            model=model,
            images_dict=images_dict,  # ← FIX: pass images through
        )
    except DatalabConversionError as e:
        raise RuntimeError(f"[V3] Document conversion failed: {e}")
    finally:
        if os.path.exists(document_path):
            os.unlink(document_path)


def process_markdown_job(
    job_id: str,
    markdown_content: str,
    subject: str,
    grade: str,
    output_dir: str,
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    source_file: Optional[str] = None,
    tts_provider: str = "edge_tts",
) -> dict:
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
        use_remotion=True,
    )
    return result


def process_markdown_job_v15(
    job_id: str,
    markdown_content: str,
    subject: str,
    grade: str,
    output_dir: str,
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    source_file: Optional[str] = None,
    tts_provider: str = "edge_tts",
    video_provider: str = "kie",
) -> dict:
    """Process markdown using V1.5 Optimized pipeline (combined agents, ~50% fewer LLM calls)."""
    from pathlib import Path

    # Save raw markdown for comparison/debugging
    output_path = Path(output_dir)
    source_md_path = output_path / "source_markdown.md"
    with open(source_md_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(
        f"[V1.5 Optimized] Saved source markdown to {source_md_path} ({len(markdown_content)} chars)"
    )

    def status_callback(jid, phase, message):
        job_manager.update_job(
            jid, {"current_phase_key": phase, "status_message": message}, persist=True
        )

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
        skip_wan=skip_wan,
        video_provider=video_provider,
    )

    pres_path = output_path / "presentation.json"
    with open(pres_path, "w") as f:
        json.dump(presentation, f, indent=2)

    analytics_summary = tracker.get_summary() if hasattr(tracker, "get_summary") else {}

    return {
        "status": "success",
        "presentation": presentation,
        "analytics": analytics_summary,
        "output_path": str(pres_path),
        "pipeline_version": "1.5",
    }


def process_markdown_job_v15_v2(
    job_id: str,
    markdown_content: str,
    subject: str,
    grade: str,
    output_dir: str,
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    source_file: Optional[str] = None,
    tts_provider: str = "edge_tts",
    images_dict: dict = None,
    pipeline_version: str = "v15_v2_director",
    generation_scope: str = "full",
    model: Optional[str] = None,
    video_provider: str = "kie",
) -> dict:
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
    print(
        f"[V1.5-V2] Saved source markdown to {source_md_path} ({len(markdown_content)} chars)"
    )

    def status_callback(jid, phase, message):
        job_manager.update_job(
            jid, {"current_phase_key": phase, "status_message": message}, persist=True
        )

    def job_update_callback(updates: dict, persist: bool = True):
        job_manager.update_job(job_id, updates, persist=persist)

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
            skip_avatar=skip_avatar,
            images_dict=images_dict,
            pipeline_version=pipeline_version,
            generation_scope=generation_scope,
            video_provider=video_provider,
            job_update_callback=job_update_callback,
        )

        # V2.5 FIX: Use locks for thread-safe JSON writes (avatar/WAN threads may be starting)
        pres_path = output_path / "presentation.json"
        with presentation_lock:
            with open(pres_path, "w") as f:
                json.dump(presentation, f, indent=2)

        # Analytics handling
        analytics_summary = (
            tracker.get_summary() if hasattr(tracker, "get_summary") else {}
        )
        # Ensure complete analytics dict is saved if get_summary is partial
        if hasattr(tracker, "to_dict"):
            analytics_full = tracker.to_dict()
            analytics_path = output_path / "analytics.json"
            with analytics_lock:
                with open(analytics_path, "w") as f:
                    json.dump(analytics_full, f, indent=2)

        # Auto-trigger Avatar Polling & Download (Synchronous / Blocking)
        # Check explicit dry_run arg or params
        is_dry_run_job = locals().get("dry_run", False) or presentation.get(
            "params", {}
        ).get("dry_run", False)

        if not skip_avatar and not is_dry_run_job:
            print(
                f"[AVATAR] Starting synchronous avatar generation for Job {job_id}",
                flush=True,
            )
            if job_id not in ACTIVE_AVATAR_JOBS:
                ACTIVE_AVATAR_JOBS.add(job_id)
                # RUN SYNCHRONOUSLY to hold the worker slot
                run_avatar_sequential_task(job_id, str(JOBS_DIR))

        return {
            "status": "success",
            "presentation": presentation,
            "analytics": analytics_summary,
            "output_path": str(pres_path),
            "pipeline_version": "1.5-unified",
            "pending_background_tasks": False,  # Now blocking, so job is truly done when this returns
        }
    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        print(f"[V1.5-V2 Pipeline Error] {str(e)}\n{tb}")
        raise RuntimeError(f"Unified Pipeline Error: {e}")


def process_markdown_job_v3(
    job_id: str,
    markdown_content: str,
    subject: str,
    grade: str,
    output_dir: str,
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    skip_manim: bool = False,
    skip_threejs: bool = False,
    source_file: Optional[str] = None,
    tts_provider: str = "edge_tts",
    model: Optional[str] = None,
    images_dict: Optional[dict] = None,  # ← FIX: accept source images from PDF
    **kwargs,
) -> dict:
    """
    V3 pipeline job processor — Manim-based pipeline.
    Called by run_job_async when pipeline_version == 'v3'.
    """
    from pathlib import Path
    from core.pipeline_v3 import run_v3_pipeline, V3PipelineError

    # Backward compat: accept skip_threejs as alias for skip_manim
    _skip_manim = skip_manim or skip_threejs

    output_path = Path(output_dir)

    # Save source markdown for reference
    source_md_path = output_path / "source_markdown.md"
    with open(source_md_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"[V3 Job] Saved source markdown ({len(markdown_content)} chars)")

    def status_callback(jid, phase, message):
        job_manager.update_job(
            jid, {"current_phase_key": phase, "status_message": message}, persist=True
        )

    def job_update_callback(updates: dict, persist: bool = True):
        job_manager.update_job(job_id, updates, persist=persist)

    try:
        presentation, tracker = run_v3_pipeline(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            job_id=job_id,
            output_dir=output_dir,
            update_status_callback=status_callback,
            dry_run=dry_run,
            skip_manim=_skip_manim,
            skip_avatar=skip_avatar,
            tts_provider=tts_provider,
            model=model,
            job_update_callback=job_update_callback,
            images_dict=images_dict,  # ← FIX: pass images into V3 pipeline
        )

        # Save analytics
        if hasattr(tracker, "to_dict"):
            analytics_full = tracker.to_dict()
            analytics_path = output_path / "analytics.json"
            with analytics_lock:
                with open(analytics_path, "w") as f:
                    json.dump(analytics_full, f, indent=2)

        analytics_summary = (
            tracker.get_summary() if hasattr(tracker, "get_summary") else {}
        )

        return {
            "status": "success",
            "presentation": presentation,
            "analytics": analytics_summary,
            "output_path": str(output_path / "presentation.json"),
            "pipeline_version": "v3",
        }

    except V3PipelineError as e:
        import traceback

        tb = traceback.format_exc()
        print(f"[V3 Pipeline Error] Phase={e.phase}: {e}\n{tb}")
        raise RuntimeError(f"V3 Pipeline Error [{e.phase}]: {e}")
    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        print(f"[V3 Pipeline Unexpected Error] {e}\n{tb}")
        raise RuntimeError(f"V3 Pipeline Error: {e}")


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

            job_id = job_manager.create_job(
                "pdf_legacy",
                {"subject": subject, "grade": grade, "source_file": pdf_file.filename},
            )
            job_output_dir = JOBS_DIR / job_id
            setup_job_folder(job_output_dir)

            try:
                result = process_pdf_to_videos(
                    pdf_path=tmp_path,
                    subject=subject,
                    grade=grade,
                    output_dir=str(job_output_dir),
                    job_id=job_id,
                )
                result["job_id"] = job_id
            finally:
                os.unlink(tmp_path)

        elif request.is_json and "markdown" in request.json:
            markdown_content = request.json["markdown"]
            subject = request.json.get("subject", subject)
            grade = request.json.get("grade", grade)

            job_id = job_manager.create_job(
                "markdown_legacy", {"subject": subject, "grade": grade}
            )
            job_output_dir = JOBS_DIR / job_id
            setup_job_folder(job_output_dir)

            result = process_markdown_to_videos(
                markdown_content=markdown_content,
                subject=subject,
                grade=grade,
                output_dir=str(job_output_dir),
                job_id=job_id,
            )
            result["job_id"] = job_id

        else:
            return jsonify(
                {"error": "Please provide either a PDF file or markdown content"}
            ), 400

        return jsonify(result)

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


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

        job_id = job_manager.create_job(
            "markdown_legacy", {"subject": subject, "grade": grade}
        )
        job_output_dir = JOBS_DIR / job_id
        setup_job_folder(job_output_dir)

        result = process_markdown_to_videos(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            output_dir=str(job_output_dir),
            job_id=job_id,
        )
        result["job_id"] = job_id

        return jsonify(result)

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


def _async_resume_worker(
    job_id,
    mode="standard",
    from_phase="audio",
    dry_run=False,
    skip_wan=False,
    skip_avatar=False,
    markdown_content=None,
    subject=None,
    grade=None,
):
    """Background worker logic for queued retries (Video, Manim, Avatar)."""
    try:
        job_dir = JOBS_DIR / job_id

        if mode == "standard":
            from core.pipeline_v12 import resume_job_from_phase

            result = resume_job_from_phase(
                job_id=job_id,
                from_phase=from_phase,
                dry_run=dry_run,
                skip_wan=skip_wan,
                skip_avatar=skip_avatar,
            )
        else:  # Recap mode
            from core.pipeline_v15 import resume_from_recap

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
                status_callback=lambda p, m: print(f"[Resume {job_id}] {p}: {m}"),
            )

            pres_path = job_dir / "presentation.json"
            with open(pres_path, "w") as f:
                json.dump(presentation, f, indent=2)

            # Copy player files
            for filename in ["player_v2.html", "player_v2.js", "player_v2.css"]:
                src = PLAYER_DIR / filename
                dst_name = "index.html" if filename == "player_v2.html" else filename
                dst = job_dir / dst_name
                if src.exists():
                    shutil.copy(str(src), str(dst))

            result = {
                "status": "success",
                "presentation": presentation,
                "analytics": tracker.get_summary() if tracker else {},
            }

        # FINAL STEP: Auto-trigger Avatar Polling & Download (Synchronous / Blocking)
        if not skip_avatar and not dry_run:
            print(
                f"[RETRY-AVATAR] Starting synchronous avatar generation for Job {job_id}",
                flush=True,
            )
            if job_id not in ACTIVE_AVATAR_JOBS:
                ACTIVE_AVATAR_JOBS.add(job_id)
                # RUN SYNCHRONOUSLY
                run_avatar_sequential_task(job_id, str(JOBS_DIR))

                # Job is not complete until this returns
                result["pending_background_tasks"] = False

        return result

    except Exception as e:
        import traceback

        print(f"[ASYNC-RESUME-ERROR] {job_id}: {str(e)}\n{traceback.format_exc()}")
        raise e


@app.route("/jobs/<job_id>/resume", methods=["POST"])
def resume_job(job_id):
    """Resume a failed job from a specific phase (Queued)."""
    from core.pipeline_v12 import detect_job_phase

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
        return jsonify(
            {"error": "Cannot resume - presentation.json missing.", "job_id": job_id}
        ), 400

    try:
        print(f"[API] Queueing resume for job {job_id} from phase: {from_phase}")
        run_job_async(
            job_id=job_id,
            process_func=_async_resume_worker,
            mode="standard",
            from_phase=from_phase,
            dry_run=dry_run,
            skip_wan=skip_wan,
            skip_avatar=skip_avatar,
        )
        return jsonify(
            {
                "status": "success",
                "message": "Resume queued successfully",
                "job_id": job_id,
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "error": str(e), "job_id": job_id}), 500


@app.route("/jobs/<job_id>/resume-recap", methods=["POST"])
def resume_job_from_recap(job_id):
    """Resume a V1.5 job from the recap stage (Queued)."""
    data = request.get_json() or {}
    skip_wan = data.get("skip_wan", False)
    dry_run = data.get("dry_run", False)

    job_dir = JOBS_DIR / job_id
    artifacts_dir = job_dir / "artifacts"
    chunker_path = artifacts_dir / "01_chunker.json"

    if not chunker_path.exists():
        return jsonify(
            {"error": "Original artifacts not found. Cannot resume.", "job_id": job_id}
        ), 400

    with open(chunker_path) as f:
        chunker_data = json.load(f)

    chunks = chunker_data.get("chunks", [])
    markdown_content = "\n\n".join([c.get("content", "") for c in chunks])
    subject = chunker_data.get("subject", "General")
    grade = chunker_data.get("grade", "General")

    try:
        print(f"[API] Queueing recap resume for job {job_id}")
        run_job_async(
            job_id=job_id,
            process_func=_async_resume_worker,
            mode="recap",
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            skip_wan=skip_wan,
            dry_run=dry_run,
        )
        return jsonify(
            {
                "status": "success",
                "message": "Recap resume queued successfully",
                "job_id": job_id,
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "error": str(e), "job_id": job_id}), 500


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
        print(f"[API] Queueing WAN re-render for sections {section_ids} (Job {job_id})")

        # Define wrapper task locally or import
        def run_wan_rerender_task(job_id, section_ids):
            from core.llm_client_v12 import rerender_sections_wan
            from core.analytics import create_tracker
            from render.wan.kie_batch_generator import KieBatchGenerator
            from pathlib import Path

            try:
                job_dir = JOBS_DIR / job_id
                pres_path = job_dir / "presentation.json"
                videos_dir = job_dir / "videos"
                videos_dir.mkdir(parents=True, exist_ok=True)

                # Update Status
                job_manager.update_job(
                    job_id,
                    {
                        "status": "processing",
                        "current_step_name": f"Rerendering {len(section_ids)} WAN video(s)...",
                        "current_phase_key": "video_generation",
                    },
                    persist=True,
                )

                # 1. Load presentation
                with open(pres_path, "r") as f:
                    presentation = json.load(f)

                # 2. Generate NEW prompts via LLM
                tracker = create_tracker(job_id)
                updated = rerender_sections_wan(presentation, section_ids, tracker)

                # 3. Extract wan_beats from updated sections
                wan_beats = []
                for section in updated.get("sections", []):
                    section_id = section.get("section_id")
                    if section_id not in section_ids:
                        continue

                    video_prompts = section.get("video_prompts", [])
                    for idx, prompt_data in enumerate(video_prompts):
                        beat_id = f"section_{section_id}_beat_{idx}"
                        wan_beats.append(
                            {
                                "beat_id": beat_id,
                                "prompt": prompt_data.get("prompt", ""),
                                "duration_hint": prompt_data.get(
                                    "duration", 5
                                ),  # FIX: Use duration_hint, not duration
                                "section_id": section_id,
                            }
                        )

                # 4. Render videos using KieBatchGenerator
                print(
                    f"[WAN-RETRY] Found {len(wan_beats)} beats to render (Job {job_id})"
                )

                if wan_beats:
                    wan_status_path = job_dir / "wan_status.json"
                    batch_gen = KieBatchGenerator(status_file_path=str(wan_status_path))

                    try:
                        results = batch_gen.generate_batch(wan_beats, str(videos_dir))
                    except Exception as render_error:
                        print(f"[WAN-RETRY] Rendering error: {render_error}")
                        import traceback

                        traceback.print_exc()
                        results = {}  # Continue with empty results to update what we can

                    # 5. Update presentation.json with video paths
                    for section in updated.get("sections", []):
                        section_id = section.get("section_id")
                        if section_id not in section_ids:
                            continue

                        beat_videos = []
                        video_prompts = section.get("video_prompts", [])
                        for idx, prompt_data in enumerate(video_prompts):
                            beat_id = f"section_{section_id}_beat_{idx}"
                            result = results.get(beat_id)

                            if isinstance(result, dict):
                                video_path = result.get("path", "")
                            else:
                                video_path = result or ""

                            # FIX: Ensure paths are relative, not absolute
                            if video_path:
                                rel_path = Path(video_path).name
                                beat_videos.append(f"videos/{rel_path}")
                            else:
                                beat_videos.append("")

                        section["beat_videos"] = beat_videos

                # 6. Save updated presentation.json
                with open(pres_path, "w") as f:
                    json.dump(updated, f, indent=2)

                # 7. Check for failures
                failed_count = 0
                for s in updated.get("sections", []):
                    if s.get("section_id") in section_ids and s.get("renderer_error"):
                        failed_count += 1

                final_status = (
                    "completed_with_errors" if failed_count > 0 else "completed"
                )
                job_manager.complete_job(job_id, status=final_status)
                print(f"[WAN-TASK] Job {job_id} rerender complete: {final_status}")

            except Exception as e:
                import traceback

                print(f"[WAN-TASK] Error during rerender: {e}")
                print(traceback.format_exc())
                job_manager.fail_job(job_id, str(e))

        # Submit to JobManager
        job_manager.submit_task(run_wan_rerender_task, job_id, section_ids)

        return jsonify(
            {
                "status": "queued",
                "message": "WAN re-render started in background",
                "job_id": job_id,
                "section_ids": section_ids,
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "error": str(e), "job_id": job_id}), 500


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
                results.append(
                    {
                        "section_id": sid,
                        "status": "skipped",
                        "reason": "No video_prompts",
                    }
                )
                continue

            print(
                f"[API] Generating videos for section {sid} ({len(video_prompts)} prompts)"
            )

            try:
                video_paths = render_from_video_prompts(
                    section=section,
                    output_dir=str(videos_dir),
                    dry_run=dry_run,
                    skip_wan=skip_wan,
                )

                section_type = section.get("section_type", "content")
                if video_paths and not dry_run:
                    if section_type == "recap":
                        section["recap_video_paths"] = [
                            f"videos/{Path(p).name}"
                            for p in video_paths
                            if p.endswith(".mp4")
                        ]
                    else:
                        section["content_video_path"] = f"videos/topic_{sid}.mp4"
                        section["beat_video_paths"] = [
                            f"videos/{Path(p).name}"
                            for p in video_paths
                            if "beat" in Path(p).name
                        ]
                    section["has_content_video"] = True

                results.append(
                    {"section_id": sid, "status": "success", "videos": video_paths}
                )
            except WanRenderError as e:
                results.append({"section_id": sid, "status": "error", "error": str(e)})
            except Exception as e:
                results.append({"section_id": sid, "status": "error", "error": str(e)})

        if not dry_run:
            with open(pres_path, "w") as f:
                json.dump(presentation, f, indent=2)

        return jsonify(
            {
                "status": "success",
                "job_id": job_id,
                "results": results,
                "dry_run": dry_run,
                "skip_wan": skip_wan,
                "presentation_updated": not dry_run,
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "error": str(e), "job_id": job_id}), 500


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
    from core.llm_client_v12 import (
        pass2_manim_renderer,
        pass2_video_renderer,
        rerender_sections_wan,
    )
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
        # Check if already running
        if job_manager.is_job_running(job_id):
            return jsonify(
                {"status": "error", "message": "Job is already running"}
            ), 409

        print(
            f"[API] Queueing Regenerate & Render for sections {section_ids} (Job {job_id})"
        )

        def run_regenerate_task(
            job_id, section_ids, renderers, execute, skip_wan, dry_run
        ):
            from core.llm_client_v12 import pass2_manim_renderer, pass2_video_renderer
            from core.renderer_executor import (
                render_all_topics,
                enforce_renderer_policy,
            )
            from core.analytics import create_tracker

            try:
                job_dir = JOBS_DIR / job_id
                pres_path = job_dir / "presentation.json"
                videos_dir = job_dir / "videos"
                videos_dir.mkdir(exist_ok=True)

                # Update Status
                job_manager.update_job(
                    job_id,
                    {
                        "status": "processing",
                        "current_step_name": f"Regenerating specs for {len(section_ids)} sections...",
                        "current_phase_key": "video_generation",
                    },
                    persist=True,
                )

                with open(pres_path, "r") as f:
                    presentation = json.load(f)

                tracker = create_tracker(job_id)
                results = {"regenerated": [], "render_results": []}
                do_all = "all" in renderers
                do_manim = do_all or "manim" in renderers
                do_wan = do_all or "wan" in renderers

                # 1. Regenerate Specs
                for section in presentation.get("sections", []):
                    sid = section.get("section_id") or section.get("id")
                    if sid not in section_ids:
                        continue

                    renderer = section.get("renderer", "none")
                    try:
                        if renderer == "manim" and do_manim:
                            print(
                                f"[Regenerate] Section {sid}: Regenerating manim spec..."
                            )
                            manim_result = pass2_manim_renderer(section, tracker)
                            section["manim_scene_spec"] = manim_result.get(
                                "manim_scene_spec"
                            )
                        elif renderer in ["video", "wan_video", "wan"] and do_wan:
                            print(
                                f"[Regenerate] Section {sid}: Regenerating WAN video prompts..."
                            )
                            video_result = pass2_video_renderer(section, tracker)
                            section["video_prompts"] = video_result.get(
                                "video_prompts", []
                            )
                    except Exception as e:
                        print(f"[Regenerate] Error regenerating spec for {sid}: {e}")

                with open(pres_path, "w") as f:
                    json.dump(presentation, f, indent=2)

                # 2. Execute Renderers
                if execute and not dry_run:
                    job_manager.update_job(
                        job_id,
                        {
                            "current_step_name": f"Rendering videos for {len(section_ids)} sections..."
                        },
                        persist=True,
                    )

                    print(
                        f"[Regenerate] Executing renderers for sections {section_ids}..."
                    )
                    presentation = enforce_renderer_policy(presentation)

                    rendered_videos = render_all_topics(
                        presentation=presentation,
                        output_dir=str(videos_dir),
                        dry_run=False,
                        skip_wan=skip_wan,
                        output_dir_base=str(job_dir),
                    )

                    # Stitch back results
                    for result in rendered_videos:
                        topic_id = result.get("topic_id")
                        if topic_id in section_ids and result.get("video_path"):
                            video_path = result.get("video_path")
                            for section in presentation.get("sections", []):
                                if section.get("section_id") == topic_id:
                                    rel_path = (
                                        Path(video_path).name
                                        if "/" in str(video_path)
                                        else video_path
                                    )
                                    section["video_path"] = f"videos/{rel_path}"
                                    break

                    with open(pres_path, "w") as f:
                        json.dump(presentation, f, indent=2)

                job_manager.complete_job(job_id, status="completed")
                print(f"[Regenerate] Job {job_id} complete.")

            except Exception as e:
                print(f"[Regenerate] Error: {e}")
                job_manager.fail_job(job_id, str(e))

        # Submit to JobManager
        job_manager.submit_task(
            run_regenerate_task,
            job_id,
            section_ids,
            renderers,
            execute,
            skip_wan,
            dry_run,
        )

        return jsonify(
            {
                "status": "queued",
                "message": "Regeneration started in background",
                "job_id": job_id,
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "error": str(e), "job_id": job_id}), 500


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
        if False:  # is_job_running():
            current_id = get_current_job_ids()
            return jsonify(
                {
                    "status": "busy",
                    "message": "A job is already running. Please wait for it to complete.",
                    "current_job_id": current_id,
                }
            ), 409

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
            return jsonify(
                {
                    "error": f"Invalid tts_provider: {tts_provider}. Use 'narakeet', 'pyttsx3', or 'estimate'"
                }
            ), 400

        job_id = job_manager.create_job(
            "v14_pipeline",
            {
                "subject": subject,
                "grade": grade,
                "skip_wan": skip_wan,
                "tts_provider": tts_provider,
                "content_preview": markdown_content[:200] + "..."
                if len(markdown_content) > 200
                else markdown_content,
            },
        )

        job_output_dir = JOBS_DIR / job_id
        setup_job_folder(job_output_dir)

        def status_callback(jid, phase, message):
            job_manager.update_job(
                jid,
                {"current_phase_key": phase, "status_message": message},
                persist=True,
            )

        generate_tts = tts_provider != "estimate"

        presentation, tracker = process_markdown_to_presentation_v14(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            job_id=job_id,
            update_status_callback=status_callback,
            generate_tts=generate_tts,
            output_dir=job_output_dir,
            tts_provider=tts_provider,
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
                skip_wan=skip_wan,
            )

        pres_path = job_output_dir / "presentation.json"
        with open(pres_path, "w") as f:
            json.dump(presentation, f, indent=2)

        analytics_summary = (
            tracker.get_summary() if hasattr(tracker, "get_summary") else {}
        )

        job_manager.update_job(
            job_id,
            {
                "status": "completed" if not validation.get("has_errors") else "failed",
                "progress": 100,
                "validation": validation,
            },
            persist=True,
        )

        return jsonify(
            {
                "status": "success"
                if not validation.get("has_errors")
                else "validation_failed",
                "job_id": job_id,
                "presentation": presentation,
                "validation": validation,
                "analytics": analytics_summary,
                "output_path": str(pres_path),
                "skip_wan": skip_wan,
                "tts_provider": tts_provider,
            }
        )

    except Exception as e:
        import traceback

        return jsonify(
            {"status": "error", "error": str(e), "traceback": traceback.format_exc()}
        ), 500


@app.route("/api/v15/pipeline-info", methods=["GET"])
def get_v15_pipeline_info():
    """Return V1.5 pipeline architecture information."""
    return jsonify(
        {
            "version": "1.5",
            "name": "Split Agent Architecture",
            "agents": [
                {"name": "SmartChunker", "output_fields": "5-10"},
                {"name": "SectionPlanner", "output_fields": "10"},
                {"name": "NarrationWriter", "output_fields": "5"},
                {"name": "VisualSpecArtist", "output_fields": "12"},
                {"name": "RendererSpecAgent", "output_fields": "variable"},
                {"name": "MemoryFlashcard", "output_fields": "5"},
                {"name": "RecapScene", "output_fields": "5"},
            ],
            "flow": [
                "SmartChunker â†’ topics",
                "SectionPlanner(topics) â†’ section_blueprints",
                "FOR EACH blueprint: NarrationWriter â†’ VisualSpecArtist â†’ RendererSpec",
                "MemoryFlashcardAgent â†’ memory_section",
                "RecapSceneAgent â†’ recap_section",
                "MergeStep â†’ presentation.json",
                "TTS â†’ audio + durations",
                "Renderers â†’ video files",
            ],
            "improvements": [
                "5-15 fields per agent (vs 50+ in V1.4)",
                "Per-agent retries instead of full pipeline restarts",
                "Focused prompts for better quality",
            ],
        }
    )


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
        if False:  # is_job_running():
            current_id = get_current_job_ids()
            return jsonify(
                {
                    "status": "busy",
                    "message": "A job is already running. Please wait for it to complete.",
                    "current_job_id": current_id,
                }
            ), 409

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
            return jsonify(
                {
                    "error": f"Invalid tts_provider: {tts_provider}. Use 'edge_tts', 'pyttsx3', 'narakeet', or 'estimate'"
                }
            ), 400

        if tts_provider == "edge":
            tts_provider = "edge_tts"

        job_id = job_manager.create_job(
            "v15_pipeline",
            {
                "subject": subject,
                "grade": grade,
                "skip_wan": skip_wan,
                "tts_provider": tts_provider,
                "pipeline_version": "1.5",
                "content_preview": markdown_content[:200] + "..."
                if len(markdown_content) > 200
                else markdown_content,
            },
        )

        job_manager.start_job(job_id)

        job_output_dir = JOBS_DIR / job_id
        setup_job_folder(job_output_dir)

        def status_callback(update_data_or_jid, phase=None, message=None):
            # Handle both legacy signature (jid, phase, message) and new dict signature (update_dict)
            if isinstance(update_data_or_jid, dict):
                # New dict signature from pipeline_unified
                update_data = update_data_or_jid
                # ensure job_id is present
                if "job_id" not in update_data:
                    update_data["job_id"] = job_id
                job_manager.update_job(job_id, update_data, persist=True)
            else:
                # Legacy signature
                # jid is update_data_or_jid
                job_manager.update_job(
                    update_data_or_jid,
                    {"current_phase_key": phase, "status_message": message},
                    persist=True,
                )

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
            skip_wan=skip_wan,
        )

        pres_path = job_output_dir / "presentation.json"
        with open(pres_path, "w") as f:
            json.dump(presentation, f, indent=2)

        analytics_summary = (
            tracker.get_summary() if hasattr(tracker, "get_summary") else {}
        )

        job_manager.update_job(
            job_id,
            {"status": "completed", "progress": 100, "pipeline_version": "1.5-unified"},
            persist=True,
        )

        return jsonify(
            {
                "status": "success",
                "job_id": job_id,
                "presentation": presentation,
                "analytics": analytics_summary,
                "output_path": str(pres_path),
                "pipeline_version": "1.5-unified",
                "skip_wan": skip_wan,
                "tts_provider": tts_provider,
            }
        )

    except PipelineUnifiedError as e:
        import traceback

        tb = traceback.format_exc()
        print(f"[Results] Unified Pipeline Error: {str(e)}")
        if "job_id" in locals():
            job_manager.fail_job(job_id, str(e), phase_key=e.phase)
        return jsonify(
            {"status": "error", "error": str(e), "phase": e.phase, "traceback": tb}
        ), 500

    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        print(f"[V1.5 Pipeline Error] Error: {str(e)}")
        print(f"[V1.5 Pipeline Error] Traceback:\n{tb}")
        if "job_id" in locals():
            job_manager.fail_job(job_id, str(e))
        return jsonify({"status": "error", "error": str(e), "traceback": tb}), 500


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

        sample_markdown = (
            data.get("markdown")
            or """
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
        )

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
                    "suggested_renderer": "video",
                },
                {
                    "topic_id": "t2",
                    "title": "Transport Mechanisms",
                    "concept_type": "process",
                    "has_formula": False,
                    "suggested_renderer": "video",
                },
                {
                    "topic_id": "t3",
                    "title": "Red Blood Cells Osmosis",
                    "concept_type": "example",
                    "has_formula": False,
                    "suggested_renderer": "video",
                },
            ],
        }

        expected_sections = {
            "from_content_director": ["intro", "summary", "content", "example", "quiz"],
            "from_recap_director": ["memory", "recap"],
            "merge_result_order": [
                "intro",
                "summary",
                "content",
                "example",
                "quiz",
                "memory",
                "recap",
            ],
        }

        validation_criteria = {
            "memory": {"flashcard_count": 5, "mnemonic_style": "R-A-S letters"},
            "recap": {
                "video_prompt_count": 5,
                "per_prompt_min_words": 300,
                "total_narration_words": "300-500",
                "avatar": "MUST be hidden",
            },
        }

        return jsonify(
            {
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
                    "markdown_preview": sample_markdown[:300] + "...",
                },
                "expected_output": {
                    "topics": expected_topics,
                    "sections": expected_sections,
                    "validation_criteria": validation_criteria,
                },
                "next_steps": [
                    "Use /api/v14/generate with actual markdown to run full pipeline",
                    "Set skip_tts=true to avoid Narakeet costs during testing",
                    "Set dry_run=true for fastest iteration",
                ],
            }
        )

    except Exception as e:
        import traceback

        return jsonify(
            {"status": "error", "error": str(e), "traceback": traceback.format_exc()}
        ), 500


# ============================================
# ADMIN PANEL ROUTES
# ============================================

from functools import wraps


def require_admin_key(f):
    """Decorator to require X-Admin-Key header"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_key = os.environ.get("ADMIN_KEY") or os.environ.get("ADMIN_API_KEY")
        if not admin_key:
            return jsonify({"error": "ADMIN_KEY not configured in .env"}), 500

        request_key = request.headers.get("X-Admin-Key")
        if not request_key or request_key != admin_key:
            return jsonify({"error": "Invalid Admin Key"}), 401

        return f(*args, **kwargs)

    return decorated_function


ADMIN_PANEL_DIR = Path(__file__).parent.parent / "admin_panel"


@app.route("/admin")
def serve_admin_panel():
    if not ADMIN_PANEL_DIR.exists():
        return "Admin Panel directory not found", 404
    return send_from_directory(ADMIN_PANEL_DIR, "index.html")


@app.route("/admin/assets/<path:filename>")
def serve_admin_assets(filename):
    return send_from_directory(ADMIN_PANEL_DIR, filename)


@app.route("/admin/api/restart", methods=["POST"])
@require_admin_key
def restart_server():
    """Restart the server (Docker or Local)"""
    try:

        def restart_thread():
            time.sleep(1)
            print("[ADMIN] Restart triggered by admin user.", flush=True)
            # Use os._exit to force kill (Docker restarts it; Local requires manual start)
            os._exit(1)

        Thread(target=restart_thread).start()
        return jsonify({"success": True, "message": "Server restarting..."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/admin/api/logs", methods=["GET"])
@require_admin_key
def get_server_logs():
    """Get recent logs"""
    try:
        lines = int(request.args.get("lines", 100))
        log_file = Path("app.log")

        # Primary: Read from log file
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                return jsonify({"logs": "".join(all_lines[-lines:])})

        # Fallback: Docker Logs (if available)
        import subprocess

        try:
            container_id = os.environ.get("HOSTNAME") or "ai-doc-presentation-prod"
            # Only try if looks like we might be in docker or have docker cli
            res = subprocess.run(
                ["docker", "logs", "--tail", str(lines), container_id],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                return jsonify({"logs": res.stdout})
        except Exception:
            pass

        return jsonify(
            {"logs": "Log file (app.log) not found. console logs not available."}
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/admin/api/config", methods=["GET", "PUT"])
@require_admin_key
def handle_config():
    """Get or Update .env configuration"""
    env_path = Path(__file__).parent.parent / ".env"

    if request.method == "GET":
        try:
            config = {}
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "=" in line and not line.startswith("#"):
                            k, v = line.strip().split("=", 1)
                            config[k] = v
            return jsonify({"config": config})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == "PUT":
        try:
            new_config = request.json.get("config", {})
            lines = []
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

            updated_lines = []
            seen_keys = set()
            for line in lines:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    if k in new_config:
                        updated_lines.append(f"{k}={new_config[k]}\n")
                        seen_keys.add(k)
                    else:
                        updated_lines.append(line)
                else:
                    updated_lines.append(line)
            for k, v in new_config.items():
                if k not in seen_keys:
                    updated_lines.append(f"{k}={v}\n")

            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(updated_lines)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/admin/api/prompts", methods=["GET"])
@require_admin_key
def list_prompts():
    """List available prompt files"""
    try:
        prompts_dir = Path(__file__).parent.parent / "core" / "prompts"
        files = []
        if prompts_dir.exists():
            for f in prompts_dir.glob("*.txt"):
                files.append(
                    {
                        "filename": f.name,
                        "size": f.stat().st_size,
                        "modified": f.stat().st_mtime,
                    }
                )
        return jsonify({"prompts": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/admin/api/prompts/<filename>", methods=["GET", "PUT"])
@require_admin_key
def handle_prompt_file(filename):
    """Read or Update a prompt file"""
    try:
        prompts_dir = Path(__file__).parent.parent / "core" / "prompts"
        file_path = prompts_dir / filename

        # Security check
        if not file_path.resolve().is_relative_to(prompts_dir.resolve()):
            return jsonify({"error": "Invalid file path"}), 403

        if request.method == "GET":
            if not file_path.exists():
                return jsonify({"error": "File not found"}), 404
            with open(file_path, "r", encoding="utf-8") as f:
                return jsonify({"content": f.read()})

        elif request.method == "PUT":
            content = request.json.get("content", "")
            if file_path.exists():
                backup_path = file_path.parent / "unused" / f"{filename}.bak"
                os.makedirs(backup_path.parent, exist_ok=True)
                shutil.copy(str(file_path), str(backup_path))
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/admin/api/system-info", methods=["GET"])
@require_admin_key
def get_system_info():
    """Get system information"""
    try:
        import platform
        from datetime import datetime

        recent_jobs = len(list(JOBS_DIR.glob("*"))) if JOBS_DIR.exists() else 0
        return jsonify(
            {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "pipeline_version": "v2.5_director",
                "total_jobs": recent_jobs,
                "server_time": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/dashboard")
@app.route("/dashboard/")
def serve_dashboard():
    response = make_response(send_from_directory(PLAYER_DIR, "dashboard.html"))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


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
        return send_from_directory(PLAYER_DIR, "index.html")


@app.route("/assets/<job_id>/<path:filename>")
def serve_job_asset(job_id, filename):
    """Serve any asset from the job directory."""
    try:
        job_folder = JOBS_DIR / job_id
        print(f"DEBUG: Serving {filename} from {job_folder}", flush=True)
        full_path = job_folder / filename
        print(f"DEBUG: Full path: {full_path} Exists: {full_path.exists()}", flush=True)
        return send_from_directory(job_folder, filename)
    except Exception as e:
        print(f"Error serving asset: {e}", flush=True)
        return jsonify({"error": "Asset not found"}), 404


@app.route("/jobs/<job_id>/<path:filename>")
@app.route("/player/jobs/<job_id>/<path:filename>")
def serve_job_assets(job_id, filename):
    """Serve all job assets from job folder"""
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found"}), 404
    # player_v3.html always served from master so fixes are instantly live
    if filename == "player_v3.html":
        return send_from_directory(PLAYER_DIR, "player_v3.html")
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
    """Trigger AI Avatar generation for a job with optional multi-language support."""
    print(f"[AVATAR] Received request to generate for Job {job_id}", flush=True)
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found"}), 404

    # Check if already running in memory
    if job_id in ACTIVE_AVATAR_JOBS:
        return jsonify(
            {
                "status": "already_running",
                "message": "Avatar generation in progress (Active Thread)",
            }
        ), 409

    # Extract optional parameters from request body
    data = request.get_json() or {}
    languages = data.get("languages")  # Optional: list of language codes
    speaker = data.get("speaker")  # Optional: voice ID
    sections = data.get("sections")  # Optional: specific section IDs

    # Start async task
    ACTIVE_AVATAR_JOBS.add(job_id)
    # Use JobManager to respect global concurrency
    job_manager.submit_task(
        run_avatar_sequential_task, job_id, str(JOBS_DIR), languages, speaker, sections
    )

    response = {"status": "queued", "message": "Avatar generation started"}
    if languages:
        response["languages"] = languages

    return jsonify(response)


@app.route("/job/<job_id>/avatar_status", methods=["GET"])
def get_avatar_status(job_id):
    """Get AI Avatar generation status."""
    job_dir = JOBS_DIR / job_id
    status_file = job_dir / "avatar_status.json"

    if not status_file.exists():
        # If it doesn't exist, it's either an old dead job or not started.
        # Return 404 to signal the client to STOP polling.
        return jsonify(
            {"state": "not_found", "message": "Job status not found or expired"}
        ), 404

    try:
        return jsonify(json.loads(status_file.read_text()))
    except Exception as e:
        return jsonify({"state": "error", "error": str(e)}), 500


@app.route("/job/<job_id>/wan_status", methods=["GET"])
def get_wan_status(job_id):
    """Get WAN video generation status."""
    job_dir = JOBS_DIR / job_id
    status_file = job_dir / "wan_status.json"

    if not status_file.exists():
        return jsonify(
            {"state": "not_found", "message": "WAN generation not started"}
        ), 404

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
        return jsonify(
            {"status": "already_running", "message": "Avatar generation in progress"}
        ), 409

    # Parse failed sections from status file if it exists
    status_file = job_dir / "avatar_status.json"
    failed_sections = None
    if status_file.exists():
        try:
            status_data = json.loads(status_file.read_text())
            failed_sections = status_data.get("details", {}).get("failed_sections", [])
        except:
            pass

    # Start async task with force=True for the specified sections
    ACTIVE_AVATAR_JOBS.add(job_id)
    # Use JobManager to respect global concurrency
    job_manager.submit_task(
        run_avatar_sequential_task,
        job_id,
        str(JOBS_DIR),
        None,
        None,
        failed_sections,
        True,
    )

    return jsonify(
        {
            "status": "queued",
            "message": "Avatar retry started",
            "failed_sections_detected": failed_sections,
        }
    )


@app.route("/job/<job_id>/regenerate_avatar/<section_id>", methods=["POST"])
def regenerate_section_avatar(job_id, section_id):
    """Regenerate avatar for a specific section (force overwrite)."""
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found"}), 404

    if job_id in ACTIVE_AVATAR_JOBS:
        return jsonify(
            {"status": "already_running", "message": "Avatar generation in progress"}
        ), 409

    ACTIVE_AVATAR_JOBS.add(job_id)
    # Use JobManager to respect global concurrency
    job_manager.submit_task(
        run_avatar_sequential_task,
        job_id,
        str(JOBS_DIR),
        None,
        None,
        [section_id],
        True,
    )

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
            "details": details or {},
        }
        try:
            with open(status_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"[ERROR] Failed to write status file {status_file}: {e}", flush=True)

    try:
        if not presentation_file.exists():
            print(
                f"[ERROR] Presentation file not found at {presentation_file}",
                flush=True,
            )
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
        results = generator.submit_parallel_job(
            presentation, job_id, str(JOBS_DIR / job_id)
        )

        queued = len(results["queued"])
        skipped = len(results["skipped"])
        failed = len(results["failed"])

        # Add to tracking
        for item in results["queued"]:
            tasks.append(
                {
                    "section_id": item["section_id"],
                    "task_id": item["task_id"],
                    "status": "queued",
                }
            )
            submission_times[item["task_id"]] = time.time()

        # Add failed to tracking
        for item in results["failed"]:
            failed_tasks.append(
                {
                    "section_id": item["section_id"],
                    "task_id": "failed",
                    "status": "failed_submit",
                    "error": item.get("error", "Unknown"),
                }
            )

        if not tasks:
            update_status(
                "completed",
                f"Done. (Queued: {queued}, Skipped: {skipped}, Failed: {failed})",
                100,
            )
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
                "active": [t["section_id"] for t in active_tasks],
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
                        print(
                            f"[AVATAR] Task {task_id} (Sec {section_id}) status: {api_status}",
                            flush=True,
                        )
                except Exception as e:
                    print(
                        f"[ERROR] Status check failed for task {task_id}: {e}",
                        flush=True,
                    )
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
                        duration = time.time() - submission_times.get(
                            task_id, time.time()
                        )
                        tracker.add_avatar_detail(str(section_id), duration, "success")

                        # Update presentation.json immediately
                        for sec in presentation["sections"]:
                            # FIX: Use string comparison to avoid int/str type mismatch
                            if str(sec.get("section_id")) == str(section_id):
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
                    tracker.add_avatar_detail(
                        str(section_id), 0, "failed_api", error=status_res.get("error")
                    )
                elif api_status == "error_check":
                    # Potentially transient, but let's count attempts or just keep active?
                    # For now, keep it active to retry check
                    still_active.append(task)
                else:
                    still_active.append(task)

            active_tasks = still_active
            time.sleep(5)  # Poll interval

            if time.time() - start_time > 1800:  # 30 min timeout
                update_status(
                    "failed", "Timeout waiting for avatar generation", details=details
                )
                return

        final_msg = (
            f"Completed: {len(completed_tasks)} successes, {len(failed_tasks)} failures"
        )
        update_status(
            "completed",
            final_msg,
            100,
            details={
                "success": [t["section_id"] for t in completed_tasks],
                "failed": [t["section_id"] for t in failed_tasks],
            },
        )

        # Save Final Analytics
        tracker.set_avatar_metrics(
            total_sections=total_sections,
            successful=len(completed_tasks),
            failed=len(failed_tasks),
            duration=time.time() - avatar_overall_start,
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


def run_avatar_sequential_task(
    job_id, jobs_root, languages=None, speaker=None, target_sections=None, force=False
):
    """
    Background worker to handle avatar generation:
    Now uses the refactored 'Submit All' strategy from AvatarGenerator with multi-language support.

    Args:
        languages (list, optional): List of language codes for multi-language generation
        speaker (str, optional): Voice ID for non-English languages
        target_sections (list, optional): Specific section IDs to process
        force (bool): Force regeneration even if videos exist
    """
    from core.agents.avatar_generator import AvatarGenerator
    import time

    lang_info = f" for {len(languages)} language(s)" if languages else ""
    print(
        f"[AVATAR-TASK] Initiating generation for job {job_id}{lang_info}", flush=True
    )
    job_dir = Path(jobs_root) / job_id
    presentation_file = job_dir / "presentation.json"

    # STATUS UPDATE: Start of Avatar Phase
    try:
        from core.job_manager import job_manager

        if job_manager:
            job_manager.update_job(
                job_id,
                {
                    "status": "processing",
                    "current_step_name": "Generating Avatars...",
                    "current_phase_key": "avatar_generation",
                },
                persist=True,
            )
    except Exception as e:
        print(f"[AVATAR-TASK] Failed to update start status: {e}", flush=True)

    try:
        if not presentation_file.exists():
            print(f"[AVATAR-TASK] Error: presentation.json not found for {job_id}")
            return

        with open(presentation_file, "r") as f:
            presentation = json.load(f)

        generator = AvatarGenerator()
        results = {}

        # Use submit_parallel_job for multi-language support (has batch processing with language loops)
        # submit_all_jobs is for single-language, stateful retry mechanism
        if languages:
            # Multi-language: use submit_parallel_job which handles language batching
            print(
                f"[AVATAR-TASK] Using submit_parallel_job for multi-language generation",
                flush=True,
            )
            results = generator.submit_parallel_job(
                presentation=presentation,
                job_id=job_id,
                output_dir=str(job_dir),
                languages=languages,
                speaker=speaker,
            )
            print(
                f"[AVATAR-TASK] Multi-language generation complete: {len(results.get('completed', []))} completed, {len(results.get('failed', []))} failed",
                flush=True,
            )
        else:
            # Single language/default: use submit_all_jobs (stateful with retry)
            print(
                f"[AVATAR-TASK] Using submit_all_jobs for default avatar generation",
                flush=True,
            )
            results = generator.submit_all_jobs(
                presentation=presentation,
                job_id=job_id,
                output_dir=str(job_dir),
                target_sections=target_sections,
                force=force,
            )

        print(f"[AVATAR-TASK] Background task completed for job {job_id}")

        # STATUS UPDATE: Completion
        try:
            failed_count = len(results.get("failed", []))
            completed_count = len(results.get("completed", []))
            skipped_count = len(results.get("skipped", []))

            final_status = "completed"

            if failed_count > 0:
                if completed_count > 0 or skipped_count > 0:
                    final_status = "completed_with_errors"
                else:
                    # Soft Fail: Still mark as completed_with_errors if user wants to see partials or just fail?
                    # Plan says "Soft Fail" logic.
                    final_status = "completed_with_errors"

            if job_manager:
                job_manager.complete_job(job_id, result=results, status=final_status)
                print(f"[AVATAR-TASK] Job {job_id} marked as {final_status}")

        except Exception as e:
            print(f"[AVATAR-TASK] Failed to update completion status: {e}", flush=True)

    except Exception as e:
        print(f"[AVATAR-TASK] Fatal error: {e}", flush=True)
        import traceback

        traceback.print_exc()
        try:
            if job_manager:
                job_manager.fail_job(job_id, str(e), phase_key="avatar_generation")
        except:
            pass
    finally:
        if job_id in ACTIVE_AVATAR_JOBS:
            ACTIVE_AVATAR_JOBS.remove(job_id)


@app.route("/api/repair-missing-assets/<job_id>", methods=["POST"])
def repair_missing_assets(job_id):
    """
    Auto-Repair: Downloads missing avatars IF they are marked as completed
    on the remote server (using existing task_id).
    Does NOT regenerate or re-bill.
    """
    from core.locks import presentation_lock, analytics_lock
    from core.agents.avatar_generator import AvatarGenerator

    job_dir = JOBS_DIR / job_id
    pres_path = job_dir / "presentation.json"
    avatar_dir = job_dir / "avatars"

    if not pres_path.exists():
        return jsonify({"error": "Job presentation.json not found"}), 404

    try:
        # Load presentation with lock
        with presentation_lock:
            with open(pres_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        generator = AvatarGenerator()
        repaired_count = 0
        updates_made = False
        details = []

        # Ensure avatar dir exists
        avatar_dir.mkdir(parents=True, exist_ok=True)

        # Scan sections
        for section in data.get("sections", []):
            sid = str(section.get("section_id"))

            # Helper to check and repair a single reference
            def check_and_repair(task_id, rel_path, language=None):
                nonlocal updates_made
                if not task_id or not rel_path:
                    return False, "no_data", None  # Fixed: Return 3 values

                # Check local file
                # Handle relative paths properly: "avatars/foo.mp4" -> job_dir / "avatars/foo.mp4"
                current_path_is_absolute = rel_path.startswith("/jobs/")

                if current_path_is_absolute:
                    # Force fix to relative
                    filename = Path(rel_path).name
                    if language:
                        rel_path = f"avatars/{language}/{filename}"
                    else:
                        rel_path = f"avatars/{filename}"
                    local_file = job_dir / rel_path
                else:
                    local_file = job_dir / rel_path

                # If missing or empty
                if not local_file.exists() or local_file.stat().st_size < 1000:
                    # 1. Check Status on Server
                    print(
                        f"[REPAIR] Checking status for Task {task_id} (Sec {sid})...",
                        flush=True,
                    )
                    status_res = generator.check_status(task_id)
                    status = status_res.get("status")

                    is_success = status == "completed" or (
                        status_res.get("result", {}).get("success") is True
                    )

                    if is_success:
                        print(
                            f"[REPAIR] Task {task_id} is VALID. Downloading to {local_file}...",
                            flush=True,
                        )
                        local_file.parent.mkdir(parents=True, exist_ok=True)
                        if generator.download_video(task_id, str(local_file)):
                            updates_made = True
                            return True, "restored", rel_path
                        else:
                            return False, "download_failed", rel_path
                    else:
                        return False, f"server_status_{status}", rel_path
                else:
                    return False, "exists", rel_path

            # 1. Default Avatar
            tid = section.get("avatar_task_id")
            path = section.get("avatar_video")
            success, reason, new_path = check_and_repair(tid, path)
            if success:
                repaired_count += 1
                section["avatar_video"] = new_path
                section["avatar_status"] = "completed"
                details.append(
                    {"section_id": sid, "type": "default", "status": "repaired"}
                )
            elif reason == "exists" and path.startswith("/jobs/"):
                # File exists but path is absolute, fix the path
                section["avatar_video"] = new_path
                updates_made = True
                details.append(
                    {"section_id": sid, "type": "default", "status": "metadata_fixed"}
                )

            # 2. Multi-Language Avatars
            for lang_entry in section.get("avatar_languages", []):
                l_tid = lang_entry.get("task_id")
                l_path = lang_entry.get("video_path")
                l_lang = lang_entry.get("language")

                l_success, l_reason, l_new_path = check_and_repair(
                    l_tid, l_path, language=l_lang
                )
                if l_success:
                    repaired_count += 1
                    lang_entry["video_path"] = l_new_path
                    lang_entry["status"] = "completed"
                    details.append(
                        {
                            "section_id": sid,
                            "type": f"lang_{l_lang}",
                            "status": "repaired",
                        }
                    )
                elif l_reason == "exists" and l_path.startswith("/jobs/"):
                    lang_entry["video_path"] = l_new_path
                    updates_made = True
                    details.append(
                        {
                            "section_id": sid,
                            "type": f"lang_{l_lang}",
                            "status": "metadata_fixed",
                        }
                    )

        # Final Persistence with lock
        if updates_made:
            with presentation_lock:
                with open(pres_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)

            # Smart Status Upgrade: If we recovered everything, try to upgrade the job status
            try:
                from core.job_manager import job_manager

                job_info = job_manager.get_job(job_id)
                if job_info and job_info.get("status") == "completed_with_errors":
                    # Simple check: are there any sections still missing avatars?
                    # This is a bit lazy but better than nothing
                    # Future: re-run the whole sanity check logic here
                    pass
            except:
                pass

        return jsonify(
            {
                "status": "success",
                "repaired_count": repaired_count,
                "metadata_updates": updates_made,
                "details": details,
                "message": f"Successfully repaired {repaired_count} avatar files and updated metadata.",
            }
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500


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
                found_videos = [
                    f.name
                    for f in video_dir.iterdir()
                    if f.is_file() and f.suffix == ".mp4"
                ]

            found_avatars = []
            if avatar_dir.exists():
                found_avatars = [
                    f.name
                    for f in avatar_dir.iterdir()
                    if f.is_file() and f.suffix == ".mp4"
                ]

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
                    not current_video_path
                    or current_video_path.startswith("/jobs/")
                    or "placeholder" in current_video_path
                )

                if topic_v in found_videos and video_needs_update:
                    section["video_path"] = f"videos/{topic_v}"
                    updated_count += 1
                elif topic_beat_0 in found_videos and video_needs_update:
                    # Found beat 0 but no main path - stitch as a multi-beat section
                    beats = sorted(
                        [v for v in found_videos if v.startswith(f"topic_{sid}_beat_")]
                    )
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
                recap_needs_update = not recap_video_paths or any(
                    p.startswith("/jobs/") for p in recap_video_paths if p
                )
                if section.get("section_type") == "recap" and recap_needs_update:
                    beats = sorted(
                        [v for v in found_videos if v.startswith(f"topic_{sid}_beat_")]
                    )
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

        return jsonify(
            {
                "status": "success",
                "updated_assets": updated_count,
                "message": f"Successfully stitched {updated_count} assets back into metadata.",
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/job/<job_id>/presentation_for_review", methods=["GET"])
def get_presentation_for_review(job_id):
    """Get presentation data formatted for review UI."""
    try:
        job_folder = JOBS_DIR / job_id
        presentation_path = job_folder / "presentation.json"

        if not presentation_path.exists():
            return jsonify({"error": "Presentation not found"}), 404

        with open(presentation_path, "r", encoding="utf-8") as f:
            presentation = json.load(f)

        # Format sections for review UI
        sections_for_review = []
        for section in presentation.get("sections", []):
            section_data = {
                "section_id": section.get("section_id"),
                "section_type": section.get("section_type"),
                "title": section.get("title"),
                "narration_text": "",
                "content": {
                    "bullet_items": [],
                    "quiz_data": None,
                    "flashcards": [],
                    "images": [],
                    "explanation_plan": "",
                    "visual_beats": [],
                },
            }

            # Extract narration text
            narration = section.get("narration", {})
            segments = narration.get("segments", [])
            if segments:
                section_data["narration_text"] = " ".join(
                    [seg.get("text", "") for seg in segments]
                )

            # Handle Explanation Plan
            plan = section.get("explanation_plan")
            if isinstance(plan, (dict, list)):
                # If plan is an object (common in newer jobs), serialize it nicely
                # or extract just the 'visual_beats' text if appropriate.
                # For editing purposes, JSON string is safest.
                section_data["content"]["explanation_plan"] = json.dumps(plan, indent=2)
            elif plan:
                section_data["content"]["explanation_plan"] = str(plan)

            # Extract structured content
            # Sources:
            # 1. narration.segments.visual_content (legacy/unified format)
            # 2. visual_beats (display_text/description)

            # Helper to deduplicate images
            seen_image_ids = set()

            # 1. From Narration Segments
            for seg in segments:
                vc = seg.get("visual_content", {})
                if isinstance(vc, dict):
                    items = vc.get("items", [])
                    if items:
                        section_data["content"]["bullet_items"].extend(items)

                    image_id = vc.get("image_id")
                    if image_id and image_id not in seen_image_ids:
                        seen_image_ids.add(image_id)
                        section_data["content"]["images"].append(
                            {
                                "image_id": image_id,
                                "description": vc.get("verbatim_content", ""),
                            }
                        )

            # 2. From Visual Beats (Primary source for newer jobs)
            visual_beats = section.get("visual_beats", [])
            if visual_beats:
                for b in visual_beats:
                    # Description/Display Text
                    desc = b.get("description") or b.get("display_text", "")
                    beat_data = {"description": desc}

                    # Video Asset
                    video_asset = b.get("video_asset")
                    if video_asset:
                        beat_data["video_asset"] = video_asset

                    if desc or video_asset:
                        section_data["content"]["visual_beats"].append(beat_data)

                    # Images in visual beats
                    image_id = b.get("image_id")
                    if image_id and image_id not in seen_image_ids:
                        seen_image_ids.add(image_id)
                        section_data["content"]["images"].append(
                            {
                                "image_id": image_id,
                                "description": desc,  # Use beat description for image if available
                            }
                        )

                    # Bullet items (if visual_type is bullet_list and we haven't found items in segments)
                    if (
                        b.get("visual_type") == "bullet_list"
                        and not section_data["content"]["bullet_items"]
                    ):
                        # If display_text looks like a list or we want to treat the beat as a point
                        # Sometimes display_text is just one bullet point.
                        # We can treat each such beat as an item if the section type suggests it.
                        if desc:
                            section_data["content"]["bullet_items"].append(desc)

            # 3. Quiz data
            quiz_data = section.get("quiz_data")
            if quiz_data:
                section_data["content"]["quiz_data"] = quiz_data

            # 4. Flashcards
            flashcards = section.get("flashcards", [])
            if flashcards:
                section_data["content"]["flashcards"] = flashcards

            sections_for_review.append(section_data)

        return jsonify(
            {
                "job_id": job_id,
                "title": presentation.get("title", ""),
                "sections": sections_for_review,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/job/<job_id>/submit_review", methods=["POST"])
def submit_review(job_id):
    """Submit review edits and trigger regeneration."""
    try:
        from core.review_handler import ReviewHandler

        job_folder = JOBS_DIR / job_id
        if not job_folder.exists():
            return jsonify({"error": "Job not found"}), 404

        data = request.get_json()
        edits = data.get("edits", [])

        if not edits:
            return jsonify({"error": "No edits provided"}), 400

        # Process review
        handler = ReviewHandler(job_folder)
        presentation = handler.load_presentation()

        # Apply edits
        presentation = handler.apply_review_edits(presentation, edits)
        handler.save_presentation(presentation)

        # Get sections needing regeneration
        sections_to_regenerate = handler.get_sections_needing_regeneration(presentation)

        # Trigger regeneration in background
        if sections_to_regenerate:
            result = handler.trigger_regeneration(sections_to_regenerate)
            return jsonify(
                {
                    "status": "success",
                    "message": f"Review submitted. Regenerating {len(sections_to_regenerate)} sections.",
                    "sections_regenerated": sections_to_regenerate,
                    "regeneration_result": result,
                }
            )
        else:
            return jsonify(
                {
                    "status": "success",
                    "message": "Review submitted but no sections needed regeneration.",
                    "sections_regenerated": [],
                }
            )

    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


if __name__ == "__main__":
    # Pre-flight check for LLM access
    try:
        from core.llm_config import validate_model_access

        is_valid, msg = validate_model_access()
        if is_valid:
            print(f"âœ… LLM Pre-flight check passed: {msg}")
        else:
            print(f"âš ï¸ LLM Pre-flight check FAILED: {msg}")
            # We don't exit to allow the app to start and show dashboard, but logs will show the issue
    except ImportError:
        print("âš ï¸ Could not import validation module")

    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

"""
V3 Pipeline — Manim-based Presentation Generation

Phases:
  1. Director V3  — director_v3_partition_prompt.txt → manim_scene_spec, understanding_quiz
  2. V3 Validator  — hard-fail on bad output
  3. Duration Estimation (word-count)
  3.3. Avatar Generation — section clips (MP4, master clock)
  3.5. Manim Code Generation — generates Python code per section
  3.6. Manim Timing Enforcer — scales self.wait() to match avatar MP4 duration
  3.7. Manim Render — executes Manim CLI, produces .mp4 files
  4.5. Quiz Card Generation (HTML-based)
  6. Quiz Clips    — 3 clips per question (question/correct/wrong)
  6.5. WAN/LTX Video Generation (renderer: "video" sections)
  7. Save presentation.json
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class V3PipelineError(Exception):
    def __init__(self, message: str, phase: str = "unknown"):
        super().__init__(message)
        self.phase = phase


def run_v3_pipeline(
    markdown_content: str,
    subject: str,
    grade: str,
    job_id: str,
    output_dir: str,
    update_status_callback=None,
    dry_run: bool = False,
    skip_manim: bool = False,
    skip_avatar: bool = False,
    skip_quiz_clips: bool = False,
    tts_provider: str = "edge_tts",
    language: str = None,
    speaker: str = None,
    model: Optional[str] = None,
    job_update_callback=None,
    video_provider: str = "ltx",
    skip_wan: bool = False,
    images_dict: Optional[dict] = None,  # ← FIX: source images extracted from uploaded PDF
) -> Dict[str, Any]:
    """
    Full V3 pipeline. Returns (presentation_dict, analytics_dict).
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    def log(phase: str, message: str):
        logger.info(f"[V3 Job {job_id}] {phase}: {message}")
        print(f"[V3-PIPELINE] [{phase.upper()}] {message}", flush=True)
        if update_status_callback:
            update_status_callback(job_id, phase, message)

    # ─────────────────────────────────────────────
    # Phase 0: Save PDF source images to job/images/
    # Mirrors pipeline_unified.py Phase 0 so V3 jobs
    # preserve the original document images on disk.
    # ─────────────────────────────────────────────
    saved_images = {}
    images_list = "None"
    if images_dict:
        log("image_processing", f"Processing {len(images_dict)} source images from PDF...")
        try:
            from core.image_processor import save_datalab_images
            images_dir = output_path / "images"
            saved_images = save_datalab_images(images_dict, str(images_dir), apply_green_screen=True)
            if saved_images:
                images_list = ", ".join(saved_images.keys())
                logger.info(f"[V3] Saved {len(saved_images)} source images to {images_dir}")
                log("image_processing", f"✅ Saved {len(saved_images)} source image(s) to job/images/")
        except Exception as e:
            logger.error(f"[V3] Image saving failed (non-fatal): {e}")
            log("image_processing", f"⚠️ Image saving error (non-fatal): {e}")
    else:
        log("image_processing", "No source images from PDF — skipping image phase.")

    # ─────────────────────────────────────────────
    # Phase 1: Director V3
    # ─────────────────────────────────────────────
    log("director_v3", "Starting V3 Director (Partition Mode)...")

    try:
        from core.partition_director_generator import PartitionDirectorGenerator
        from core.analytics import AnalyticsTracker

        tracker = AnalyticsTracker(job_id=job_id)

        # V3 uses its own partition prompt (manim_scene_spec, understanding_quiz, zero text_layer)
        v3_prompt_path = (
            Path(__file__).parent / "prompts" / "director_v3_partition_prompt.txt"
        )
        if not v3_prompt_path.exists():
            raise V3PipelineError(
                f"director_v3_partition_prompt.txt not found at {v3_prompt_path}",
                phase="director_v3",
            )

        # PartitionDirectorGenerator accepts content_prompt_file and global_prompt_file
        director = PartitionDirectorGenerator(
            content_prompt_file=str(v3_prompt_path),
            # Global prompt: use same as V2 (intro/summary/recap/quiz schema unchanged)
            global_prompt_file=str(
                Path(__file__).parent / "prompts" / "director_global_prompt.txt"
            ),
        )

        log(
            "director_v3",
            f"Calling V3 Director for subject={subject}, grade={grade}...",
        )
        presentation = director.generate_presentation_partitioned(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            output_dir=output_dir,
        )

        log(
            "director_v3",
            f"Director V3 complete. {len(presentation.get('sections', []))} sections generated.",
        )

    except V3PipelineError:
        raise
    except Exception as e:
        raise V3PipelineError(f"Director V3 failed: {e}", phase="director_v3")

    # ─────────────────────────────────────────────
    # Phase 2: V3 Validator
    # ─────────────────────────────────────────────
    log("v3_validator", "Validating V3 Director output...")

    try:
        from core.v3_validator import validate_presentation_v3, format_v3_report

        is_valid, errors = validate_presentation_v3(presentation)
        report = format_v3_report(errors)

        # Save validation report
        report_path = output_path / "v3_validation_report.txt"
        report_path.write_text(report, encoding="utf-8")

        if not is_valid:
            logger.warning(
                f"[V3] Validation found {len(errors)} issues (non-fatal):\n{report}"
            )
            log(
                "v3_validator",
                f"⚠️ {len(errors)} validation issues (non-fatal) — see v3_validation_report.txt. Continuing.",
            )
        else:
            log("v3_validator", "✅ V3 validation passed.")

    except V3PipelineError:
        raise
    except Exception as e:
        logger.warning(f"[V3] Validator error (non-fatal): {e}")

    # ─────────────────────────────────────────────
    # Phase 3: Duration Estimation (word-count)
    # V3 architecture: NO TTS audio is generated here.
    # The avatar MP4 (Phase 3.3) contains the voice — it is the only audio.
    # This phase applies a fast word-count estimate to duration_seconds per
    # segment so Manim (Phase 3.5) has an initial timing baseline.
    # Phase 3.6 (manim_timing_enforcer) corrects all timings post-avatar
    # using the real MP4 duration — so this estimate only needs to be close.
    # ─────────────────────────────────────────────
    pres_path = output_path / "presentation.json"

    log(
        "duration_estimate",
        "Applying word-count duration estimates to narration segments...",
    )
    try:
        from core.tts_duration import update_durations_simplified

        updated_pres = update_durations_simplified(
            presentation=presentation,
            output_dir=None,  # V3: no audio files — estimates only
            production_provider="estimate",  # word-count math, no audio
        )
        if updated_pres:
            presentation = updated_pres
        log(
            "duration_estimate",
            "✅ Duration estimates applied. Manim will use these as starting proportions.",
        )
    except Exception as e:
        logger.warning(f"[V3] Duration estimation error (non-fatal): {e}")
        log("duration_estimate", f"⚠️ Estimation error (non-fatal): {e}")

    # Save presentation.json with estimated durations
    try:
        from core.locks import presentation_lock

        with presentation_lock:
            with open(pres_path, "w", encoding="utf-8") as f:
                json.dump(presentation, f, indent=2, ensure_ascii=False)
    except ImportError:
        with open(pres_path, "w", encoding="utf-8") as f:
            json.dump(presentation, f, indent=2, ensure_ascii=False)
    log("save_json", f"Saved presentation.json ({pres_path.stat().st_size} bytes)")

    # ─────────────────────────────────────────────
    # Phase 3.3: Avatar Generation (section clips)
    # MOVED UP: Generates MP4s so we have exact real duration for Manim.
    # ─────────────────────────────────────────────
    if skip_avatar:
        log("avatar", "Skipping avatar generation (skip_avatar=True).")
    else:
        avatar_api_url = os.environ.get("AVATAR_API_URL")
        if not avatar_api_url:
            log("avatar", "⚠️ AVATAR_API_URL not set — skipping avatar generation.")
        else:
            try:
                from core.agents.avatar_generator import AvatarGenerator
                from core.analytics import AnalyticsTracker

                log(
                    "avatar",
                    "Phase 3.3: Starting avatar generation for all sections...",
                )
                avatar_gen = AvatarGenerator(api_url=avatar_api_url)

                languages = [language] if language else [None]
                avatar_gen.submit_parallel_job(
                    presentation=presentation,
                    job_id=job_id,
                    output_dir=str(output_path),
                    tracker=tracker,
                    languages=languages,
                    speaker=speaker,
                )
                log("avatar", "✅ Avatar generation complete.")

                # RE-LOAD presentation.json to get the avatar_duration_seconds
                try:
                    with open(pres_path, "r", encoding="utf-8") as f:
                        presentation = json.load(f)
                    log("avatar", "Reloaded presentation.json with avatar durations.")
                except Exception as e:
                    logger.warning(
                        f"[V3] Could not reload presentation after avatar gen: {e}"
                    )

            except Exception as e:
                logger.warning(f"[V3] Avatar generation error (non-fatal): {e}")
                log("avatar", f"⚠️ Avatar error (non-fatal): {e}")

    # ─────────────────────────────────────────────
    # Phase 3.5: Manim Code Generation — PER SEGMENT (Parallel, like V2)
    # Each visual segment in a Manim section gets its own .py + .mp4 (beat video).
    # Runs AFTER avatar generation so avatar_duration_seconds is available.
    # ─────────────────────────────────────────────
    if skip_manim:
        log("manim_gen", "Skipping Manim generation (skip_manim=True).")
    else:
        log("manim_gen", "Phase 3.5: Generating per-segment Manim code (parallel, 5 workers)...")
        try:
            from core.agents.manim_code_generator import ManimCodeGenerator, build_v3_segment_data
            import concurrent.futures

            gen = ManimCodeGenerator()
            manim_dir = output_path / "manim"
            manim_dir.mkdir(parents=True, exist_ok=True)

            sections = presentation.get("sections", [])
            manim_sections = [s for s in sections if s.get("renderer") == "manim"]
            log("manim_gen", f"Found {len(manim_sections)} Manim section(s).")

            def process_section(section):
                sec_id = section.get("section_id", "0")
                render_spec = section.get("render_spec", {})
                narrow_specs = render_spec.get("segment_specs", [])
                manim_specs = [
                    s for s in narrow_specs
                    if s.get("renderer") == "manim" or s.get("manim_scene_spec")
                ]

                # Fallback: director gave ONE section-level spec (old format)
                if not manim_specs:
                    single_spec = render_spec.get("manim_scene_spec", "")
                    if single_spec:
                        narr_segs = section.get("narration", {}).get("segments", [])
                        total_dur = section.get("total_duration_seconds", 20.0)
                        first_seg_id = narr_segs[0]["segment_id"] if narr_segs else "seg_1"
                        manim_specs = [{
                            "segment_id": first_seg_id,
                            "renderer": "manim",
                            "duration_seconds": total_dur,
                            "manim_scene_spec": single_spec,
                        }]

                if not manim_specs:
                    log("manim_gen", f"  Sec {sec_id}: no manim segment_specs found, skipping.")
                    return

                narration_segs = section.get("narration", {}).get("segments", [])
                narration_by_id = {s["segment_id"]: s for s in narration_segs}
                section["_manim_segment_specs"] = []

                for beat_idx, spec in enumerate(manim_specs):
                    seg_id = spec.get("segment_id", f"seg_{beat_idx + 1}")
                    narr_seg = narration_by_id.get(seg_id, {})

                    # Duration priority: real avatar MP4 > director estimate > narration estimate
                    duration = (
                        narr_seg.get("avatar_duration_seconds")
                        or spec.get("duration_seconds")
                        or narr_seg.get("duration_seconds")
                        or 15.0
                    )

                    section_data = build_v3_segment_data(
                        section=section,
                        spec=spec,
                        seg_id=seg_id,
                        duration=duration,
                    )

                    py_filename = f"topic_{sec_id}_beat_{beat_idx}.py"
                    py_path = manim_dir / py_filename

                    log("manim_gen", f"  Sec {sec_id} | seg {seg_id} ({duration:.1f}s) → {py_filename}")
                    manim_code, errors = gen.generate(section_data)

                    if manim_code:
                        py_path.write_text(manim_code, encoding="utf-8")
                        section["_manim_segment_specs"].append({
                            "segment_id": seg_id,
                            "beat_idx": beat_idx,
                            "py_path": str(py_path),
                            "duration_seconds": duration,
                            "topic_id": sec_id,
                        })
                        log("manim_gen", f"    ✅ Saved {py_filename}")
                    else:
                        log("manim_gen", f"    ⚠️ Gen failed for {seg_id}: {errors}")

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                list(executor.map(process_section, manim_sections))

        except Exception as e:
            logger.warning(f"[V3] Manim code gen error (non-fatal): {e}")
            log("manim_gen", f"⚠️ Manim gen error (non-fatal): {e}")

        # Save presentation.json with _manim_segment_specs
        try:
            from core.locks import presentation_lock
            with presentation_lock:
                with open(pres_path, "w", encoding="utf-8") as f:
                    json.dump(presentation, f, indent=2, ensure_ascii=False)
        except ImportError:
            with open(pres_path, "w", encoding="utf-8") as f:
                json.dump(presentation, f, indent=2, ensure_ascii=False)
        log("manim_gen", "✅ Phase 3.5 complete.")

    # ─────────────────────────────────────────────
    # (Phase 5 Avatar Generation was moved up to Phase 3.3)
    # ─────────────────────────────────────────────

    # ─────────────────────────────────────────────
    # Phase 3.6: Manim Timing Enforcement
    # Scales self.wait() in each .py to match real avatar duration.
    # Falls back to narration duration_seconds when avatar is unavailable.
    # NOTE: no longer gated by skip_avatar.
    # ─────────────────────────────────────────────
    if not skip_manim:
        log("manim_timing_enforce", "Phase 3.6: Enforcing Manim timing...")
        try:
            with open(pres_path, "r", encoding="utf-8") as f:
                presentation = json.load(f)

            from core.manim_timing_enforcer import run_manim_timing_enforcement
            patched = run_manim_timing_enforcement(
                presentation=presentation,
                output_dir=str(output_path),
                log_fn=log,
            )
            log("manim_timing_enforce", f"✅ Phase 3.6 complete: {patched} file(s) timing-enforced.")
        except Exception as e:
            logger.warning(f"[V3] Manim timing enforcement error (non-fatal): {e}")
            log("manim_timing_enforce", f"⚠️ Phase 3.6 error (non-fatal): {e}")

    # ─────────────────────────────────────────────
    # Phase 3.7: Manim Render — one .mp4 per segment (beat_videos)
    # Calls V2's _render_manim_segment_specs which writes seg.beat_videos[] directly.
    # ─────────────────────────────────────────────
    if not skip_manim:
        log("manim_render", "Phase 3.7: Rendering per-segment Manim beat videos...")
        try:
            from render.manim.manim_runner import _render_manim_segment_specs

            sections = presentation.get("sections", [])
            manim_sections = [s for s in sections if s.get("renderer") == "manim"]
            rendered_total = 0

            for section in manim_sections:
                sec_id = section.get("section_id", "0")
                internal_specs = section.get("_manim_segment_specs", [])

                if not internal_specs:
                    log("manim_render", f"  Sec {sec_id}: no _manim_segment_specs, skipping.")
                    continue

                log("manim_render", f"  Sec {sec_id}: rendering {len(internal_specs)} beat video(s)...")
                try:
                    rendered = _render_manim_segment_specs(
                        specs=internal_specs,
                        topic_id=sec_id,
                        topic_title=section.get("title", ""),
                        output_dir=str(output_path / "videos"),
                        dry_run=dry_run,
                        topic=section,  # CRITICAL: writes seg.beat_videos[] directly
                    )
                    if rendered:
                        section["video_path"] = f"videos/{Path(rendered[0]).name}"
                        section["manim_video_paths"] = [
                            f"videos/{Path(p).name}" for p in rendered
                        ]
                    rendered_total += len(rendered)
                    log("manim_render", f"  ✅ Sec {sec_id}: {len(rendered)} beat video(s) done.")

                except Exception as render_err:
                    logger.warning(f"[V3] Manim render failed for sec {sec_id}: {render_err}")
                    log("manim_render", f"  ⚠️ Sec {sec_id} render failed: {render_err}")

            log("manim_render", f"✅ Phase 3.7 complete: {rendered_total} beat video(s) rendered.")

            # Save presentation.json with video paths
            try:
                from core.locks import presentation_lock
                with presentation_lock:
                    with open(pres_path, "w", encoding="utf-8") as f:
                        json.dump(presentation, f, indent=2, ensure_ascii=False)
            except ImportError:
                with open(pres_path, "w", encoding="utf-8") as f:
                    json.dump(presentation, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.warning(f"[V3] Manim render error (non-fatal): {e}")
            log("manim_render", f"⚠️ Phase 3.7 error (non-fatal): {e}")

    # ─────────────────────────────────────────────
    # Phase 4.5: Quiz Card Generation
    # V3 Goal: Every quiz question has a visual quiz card.
    # This is programmatic — no LLM needed. Template-filled from quiz data.
    # ─────────────────────────────────────────────
    log("quiz_card_gen", "Phase 4.5: Generating quiz cards...")
    try:
        from core.quiz_card_generator import run_phase_4_5

        quiz_cards = run_phase_4_5(
            presentation=presentation,
            output_dir=str(output_path),
            log_fn=log,
        )
        # Save presentation.json with quiz card paths
        try:
            from core.locks import presentation_lock

            with presentation_lock:
                with open(pres_path, "w", encoding="utf-8") as f:
                    json.dump(presentation, f, indent=2, ensure_ascii=False)
        except ImportError:
            with open(pres_path, "w", encoding="utf-8") as f:
                json.dump(presentation, f, indent=2, ensure_ascii=False)
        log(
            "quiz_card_gen",
            f"✅ Phase 4.5 complete: {quiz_cards} quiz card(s) generated.",
        )
    except Exception as e:
        logger.warning(f"[V3] Quiz card generation error (non-fatal): {e}")
        log("quiz_card_gen", f"⚠️ Phase 4.5 error (non-fatal): {e}")

    # ─────────────────────────────────────────────
    # Phase 6: Quiz Clips (3 per question)

    # ─────────────────────────────────────────────
    if skip_quiz_clips or skip_avatar:
        log("quiz_clips", "Skipping quiz clip generation.")
    else:
        avatar_api_url = os.environ.get("AVATAR_API_URL")
        if avatar_api_url:
            try:
                from core.agents.avatar_generator import AvatarGenerator

                log("quiz_clips", "Generating quiz avatar clips (3 per question)...")
                quiz_gen = AvatarGenerator(api_url=avatar_api_url)
                quiz_results = quiz_gen.submit_quiz_clips(
                    presentation=presentation,
                    job_id=job_id,
                    output_dir=str(output_path),
                    language=language,
                    speaker=speaker,
                )
                log(
                    "quiz_clips",
                    f"✅ Quiz clips done: {quiz_results['completed']} completed, {quiz_results['failed']} failed.",
                )

            except Exception as e:
                logger.warning(f"[V3] Quiz clips error (non-fatal): {e}")
                log("quiz_clips", f"⚠️ Quiz clips error (non-fatal): {e}")

    # ─────────────────────────────────────────────
    # Phase 6.5: WAN / LTX2 Video Generation
    # V3: Handle text_to_video, image_to_video, and video sections
    # ─────────────────────────────────────────────

    # V3: Sections that need video generation
    video_sections = [
        s
        for s in presentation.get("sections", [])
        if s.get("renderer") in ("video", "text_to_video", "image_to_video")
    ]

    # V3: Separate sections by type
    wan_video_sections = [s for s in video_sections if s.get("renderer") == "video"]
    v3_video_sections = [
        s
        for s in video_sections
        if s.get("renderer") in ("text_to_video", "image_to_video")
    ]

    # V3: Handle text_to_video and image_to_video sections via execute_renderer()
    if v3_video_sections and not skip_wan:
        log(
            "wan_video",
            f"Starting V3 video generation for {len(v3_video_sections)} section(s) via execute_renderer()...",
        )
        try:
            from core.renderer_executor import execute_renderer

            for section in v3_video_sections:
                section_id = section.get("section_id", "?")
                renderer = section.get("renderer", "?")
                log("wan_video", f"  Processing section {section_id} ({renderer})...")

                result = execute_renderer(
                    topic=section,
                    output_dir=str(output_path / "videos"),
                    dry_run=False,
                    skip_wan=False,
                    video_provider=video_provider,
                )

                if result.get("status") == "success":
                    log(
                        "wan_video",
                        f"    ✅ Section {section_id} complete: {result.get('video_path')}",
                    )
                else:
                    log(
                        "wan_video",
                        f"    ❌ Section {section_id} failed: {result.get('error', 'Unknown error')}",
                    )

            log(
                "wan_video",
                f"✅ V3 video generation complete for {len(v3_video_sections)} section(s).",
            )
        except Exception as e:
            logger.warning(f"[V3] V3 video generation error (non-fatal): {e}")
            log("wan_video", f"⚠️ V3 video error (non-fatal): {e}")

    # Legacy: Handle renderer: "video" sections via submit_wan_background_job()
    if wan_video_sections and not skip_wan:
        log(
            "wan_video",
            f"Starting WAN/LTX video generation for {len(wan_video_sections)} renderer:video section(s)...",
        )
        try:
            from core.renderer_executor import submit_wan_background_job

            submit_wan_background_job(
                presentation=presentation,
                output_dir=str(output_path / "videos"),
                job_id=job_id,
                skip_wan=skip_wan,
                skip_avatar=False,
                video_provider=video_provider,
            )
            log("wan_video", "✅ WAN/LTX video generation complete.")
        except Exception as e:
            logger.warning(f"[V3] WAN/LTX generation error (non-fatal): {e}")
            log("wan_video", f"⚠️ WAN/LTX error (non-fatal): {e}")
    elif skip_wan:
        log("wan_video", "Skipping WAN/LTX video generation (skip_wan=True).")
    elif not video_sections:
        log("wan_video", "No video sections found — skipping WAN/LTX.")

    # ─────────────────────────────────────────────
    # Phase 7: Final save
    # ─────────────────────────────────────────────

    # Re-read from disk (avatar generator may have updated it)
    try:
        with open(pres_path, "r", encoding="utf-8") as f:
            presentation = json.load(f)
    except Exception:
        pass

    # Stamp pipeline version
    presentation["pipeline_version"] = "v3"
    presentation["player"] = "player_v3.html"

    with open(pres_path, "w", encoding="utf-8") as f:
        json.dump(presentation, f, indent=2, ensure_ascii=False)

    log("done", f"✅ V3 Pipeline complete. Output: {output_path}")

    analytics_summary = {}
    if hasattr(tracker, "get_summary"):
        analytics_summary = tracker.get_summary()

    return presentation, tracker

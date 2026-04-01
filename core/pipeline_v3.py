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


def substitute_placeholders(presentation_data: dict, subject: str, grade: str) -> dict:
    """
    Replace {{subject}} and {{grade}} in all narration text fields
    before avatar generation is triggered.
    Recursively scans the dict for string values containing placeholders.
    """
    replacements = {
        "{{subject}}": subject,
        "{{grade}}": str(grade),
    }

    def replace_in_value(val):
        if isinstance(val, str):
            for placeholder, replacement in replacements.items():
                val = val.replace(placeholder, replacement)
            return val
        elif isinstance(val, dict):
            return {k: replace_in_value(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [replace_in_value(item) for item in val]
        return val

    return replace_in_value(presentation_data)


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
    images_dict: Optional[
        dict
    ] = None,  # ← FIX: source images extracted from uploaded PDF
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
        log(
            "image_processing",
            f"Processing {len(images_dict)} source images from PDF...",
        )
        try:
            from core.image_processor import save_datalab_images

            images_dir = output_path / "images"
            saved_images = save_datalab_images(
                images_dict, str(images_dir), apply_green_screen=True
            )
            if saved_images:
                images_list = ", ".join(saved_images.keys())
                logger.info(
                    f"[V3] Saved {len(saved_images)} source images to {images_dir}"
                )
                log(
                    "image_processing",
                    f"✅ Saved {len(saved_images)} source image(s) to job/images/",
                )
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

        # Validation gate with retry — catches Director quality issues before
        # proceeding to image generation. Retries up to 2 times with error
        # feedback fed back to the Global Director via missing_content_hint.
        max_validation_retries = 2
        validation_hint = None
        for attempt in range(1, max_validation_retries + 1):
            presentation = director.generate_presentation_partitioned(
                markdown_content=markdown_content,
                subject=subject,
                grade=grade,
                output_dir=output_dir,
                missing_content_hint=validation_hint,
            )

            # Run V3 validator
            from core.v3_validator import validate_presentation_v3

            is_valid, errors = validate_presentation_v3(presentation)

            if is_valid:
                log("director_v3", f"✅ Validation passed on attempt {attempt}.")
                break

            # Check if there are retryable errors (Director-quality issues)
            retryable = [
                e
                for e in errors
                if e.condition
                in (
                    "v3_narration_short",
                    "v3_total_duration_missing",
                    "v3_quiz_missing",
                    "v3_quiz_incomplete",
                    "v3_text_layer_not_hidden",
                )
            ]

            if not retryable or attempt >= max_validation_retries:
                log(
                    "director_v3",
                    f"⚠️ Validation has {len(errors)} issues ({len(retryable)} retryable) — "
                    f"proceeding after attempt {attempt}/{max_validation_retries}.",
                )
                break

            # Build retry hint for the Global Director
            hint_lines = [
                "CRITICAL VALIDATION ERRORS — Fix these in your next attempt:",
            ]
            for err in retryable:
                hint_lines.append(f"- Section {err.section_id}: {err.details}")
            validation_hint = "\n".join(hint_lines)
            log(
                "director_v3",
                f"⚠️ Validation attempt {attempt}/{max_validation_retries} — "
                f"{len(retryable)} retryable errors. Retrying with feedback...",
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
    # Phase 1.5: Normalize image_source filenames
    # ALWAYS run normalization Pass — browser cannot resolve absolute paths.
    log(
        "image_normalize",
        "Phase 1.5: Normalizing image_source filenames to match disk...",
    )
    try:
        from pathlib import Path as _Path

        images_dir_path = output_path / "images"

        # Build stem → actual filename map from what exists on disk
        stem_map = {}
        if images_dir_path.exists():
            for f in images_dir_path.iterdir():
                if f.suffix in (".png", ".jpg", ".jpeg", ".webp"):
                    stem_map[f.stem] = (
                        f.name
                    )  # e.g. "b0d31e64_img" → "b0d31e64_img.png"

        fixed_count = 0

        def _fix_image_source(obj):
            """
            Normalize an image_source path to be relative to output_dir.
            Strips any absolute path prefix, then searches images/ and
            generated_images/ for a filename stem match.
            """
            nonlocal fixed_count
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "image_source" and isinstance(v, str):
                        # Step 1 — strip absolute prefix down to bare filename
                        filename = os.path.basename(v)
                        stem = os.path.splitext(filename)[0]

                        found_rel = None
                        # Step 2 — search images/ then generated_images/ for a stem match
                        for subdir in ["images", "generated_images"]:
                            search_dir = output_path / subdir
                            if not search_dir.is_dir():
                                continue
                            for f in search_dir.iterdir():
                                if f.stem == stem:
                                    found_rel = f"{subdir}/{f.name}"
                                    break
                            if found_rel:
                                break

                        if found_rel and obj[k] != found_rel:
                            obj[k] = found_rel
                            fixed_count += 1
                        elif not found_rel and "/" in v:
                            # Fallback — return bare filename if absolute path but not found on disk
                            obj[k] = filename
                            fixed_count += 1
                    else:
                        _fix_image_source(v)
            elif isinstance(obj, list):
                for item in obj:
                    _fix_image_source(item)

        _fix_image_source(presentation)
        log(
            "image_normalize",
            f"✅ Phase 1.5 complete: {fixed_count} path(s) corrected.",
        )
    except Exception as e:
        logger.warning(f"[V3] Image normalize error (non-fatal): {e}")
        log("image_normalize", f"⚠️ Phase 1.5 error (non-fatal): {e}")

    # ─────────────────────────────────────────────
    # Phase 1.6: Auto-fix missing total_duration_seconds
    # Computes total_duration_seconds from narration segments
    # if the Director forgot to set it.
    # ─────────────────────────────────────────────
    try:
        for section in presentation.get("sections", []):
            narration = section.get("narration", {})
            if not narration:
                continue
            existing_total = section.get("total_duration_seconds")
            segs = narration.get("segments", [])
            computed_total = sum(s.get("duration_seconds", 0) for s in segs)
            if existing_total is None or existing_total == 0:
                if computed_total > 0:
                    section["total_duration_seconds"] = round(computed_total, 2)
                    sid = section.get("section_id", "?")
                    log(
                        "auto_fix",
                        f"  ✅ S{sid}: auto-computed total_duration_seconds={section['total_duration_seconds']}s",
                    )
    except Exception as e:
        logger.warning(f"[V3] Auto-fix error (non-fatal): {e}")

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
    # Phase 2.5: Visual Prompt Enhancer
    # Calls GPT-4o (OpenRouter) to upgrade image_prompt_start / image_prompt_end /
    # video_prompt for image_to_video, image, and infographic sections.
    # Skipped for: manim, none, per_question, text_to_video.
    # Non-fatal: errors skip the section and continue the pipeline.
    # ─────────────────────────────────────────────
    log("prompt_enhancer", "Phase 2.5: Running Visual Prompt Enhancer...")
    try:
        from core.agents.visual_prompt_enhancer import run_prompt_enhancement

        presentation = run_prompt_enhancement(presentation, log_fn=log)
        log("prompt_enhancer", "✅ Phase 2.5 complete.")
    except Exception as e:
        logger.warning(f"[V3] Prompt enhancer error (non-fatal): {e}")
        log("prompt_enhancer", f"⚠️ Phase 2.5 error (non-fatal): {e}")

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
    # SUBST-001: Substitute placeholders (always run this, even on dry_run)
    # ─────────────────────────────────────────────
    log("substitute", "Substituting {{subject}} and {{grade}} placeholders...")
    try:
        from core.tts_generator import substitute_placeholders

        presentation = substitute_placeholders(
            presentation, subject=subject, grade=grade
        )
        # Re-save presentation.json with placeholders filled
        with open(pres_path, "w", encoding="utf-8") as f:
            json.dump(presentation, f, indent=2, ensure_ascii=False)
        log("substitute", "✅ Placeholders substituted successfully.")
    except Exception as e:
        logger.warning(f"[V3] Placeholder substitution error (non-fatal): {e}")

    # ─────────────────────────────────────────────
    # Phase 3.3: Avatar Generation (section clips)
    # MOVED UP: Generates MP4s so we have exact real duration for Manim.
    # ─────────────────────────────────────────────
    if skip_avatar or dry_run:
        log("avatar", "Skipping avatar generation (skip_avatar=True or dry_run=True).")
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
        log(
            "manim_gen",
            "Phase 3.5: Generating per-segment Manim code (parallel, 5 workers)...",
        )
        try:
            from core.agents.manim_code_generator import (
                ManimCodeGenerator,
                build_v3_segment_data,
            )
            import concurrent.futures

            gen = ManimCodeGenerator()
            manim_dir = output_path / "manim"
            manim_dir.mkdir(parents=True, exist_ok=True)

            sections = presentation.get("sections", [])
            manim_sections = [
                s
                for s in sections
                if s.get("renderer") == "manim"
                or s.get("render_spec", {}).get("renderer") == "manim"
            ]
            log("manim_gen", f"Found {len(manim_sections)} Manim section(s).")

            def process_section(section):
                sec_id = section.get("section_id", "0")
                render_spec = section.get("render_spec", {})
                narrow_specs = render_spec.get("segment_specs", [])
                manim_specs = [
                    s
                    for s in narrow_specs
                    if s.get("renderer") == "manim" or s.get("manim_scene_spec")
                ]

                # FIX: V3 Director outputs manim_segment_specs[] directly inside render_spec
                # (not inside segment_specs[]). Fall back to this key when segment_specs is empty.
                if not manim_specs:
                    v3_manim_specs = render_spec.get("manim_segment_specs", [])
                    if v3_manim_specs:
                        for s in v3_manim_specs:
                            s.setdefault("renderer", "manim")
                        manim_specs = v3_manim_specs
                        log(
                            "manim_gen",
                            f"  Sec {sec_id}: using render_spec.manim_segment_specs[] ({len(manim_specs)} specs) [V3 format]",
                        )

                # NEW: V3 schema uses manim_beats[] inside render_spec
                if not manim_specs:
                    manim_beats = render_spec.get("manim_beats", [])
                    if manim_beats:
                        for beat in manim_beats:
                            manim_specs.append(
                                {
                                    "segment_id": beat.get(
                                        "beat_id", f"seg_{len(manim_specs) + 1}"
                                    ),
                                    "renderer": "manim",
                                    "duration_seconds": beat.get("duration", 15.0),
                                    "duration": beat.get("duration", 15.0),
                                    "manim_scene_spec": beat.get(
                                        "manim_scene_spec", ""
                                    ),
                                }
                            )
                        log(
                            "manim_gen",
                            f"  Sec {sec_id}: using render_spec.manim_beats[] ({len(manim_specs)} beats) [V3 new schema]",
                        )

                # Fallback: director gave ONE section-level spec (old format)
                if not manim_specs:
                    single_spec = render_spec.get("manim_scene_spec", "")
                    if single_spec:
                        narr_segs = section.get("narration", {}).get("segments", [])
                        total_dur = section.get("total_duration_seconds", 20.0)
                        first_seg_id = (
                            narr_segs[0]["segment_id"] if narr_segs else "seg_1"
                        )
                        manim_specs = [
                            {
                                "segment_id": first_seg_id,
                                "renderer": "manim",
                                "duration_seconds": total_dur,
                                "manim_scene_spec": single_spec,
                            }
                        ]

                if not manim_specs:
                    log(
                        "manim_gen",
                        f"  Sec {sec_id}: no manim segment_specs found, skipping.",
                    )
                    return

                narration_segs = section.get("narration", {}).get("segments", [])
                narration_by_id = {s["segment_id"]: s for s in narration_segs}
                section["_manim_segment_specs"] = []

                for beat_idx, spec in enumerate(manim_specs):
                    seg_id = spec.get("segment_id", f"seg_{beat_idx + 1}")
                    narr_seg = narration_by_id.get(seg_id, {})

                    # Duration priority: real avatar MP4 > director estimate > narration estimate
                    # FIX: V3 manim_segment_specs use "duration" key, not "duration_seconds"
                    duration = (
                        narr_seg.get("avatar_duration_seconds")
                        or spec.get("duration_seconds")
                        or spec.get("duration")  # V3 format uses "duration"
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

                    log(
                        "manim_gen",
                        f"  Sec {sec_id} | seg {seg_id} ({duration:.1f}s) → {py_filename}",
                    )
                    manim_code, errors = gen.generate(section_data)

                    if manim_code:
                        py_path.write_text(manim_code, encoding="utf-8")
                        section["_manim_segment_specs"].append(
                            {
                                "segment_id": seg_id,
                                "beat_idx": beat_idx,
                                "py_path": str(py_path),
                                "duration_seconds": duration,
                                "topic_id": sec_id,
                            }
                        )
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
            log(
                "manim_timing_enforce",
                f"✅ Phase 3.6 complete: {patched} file(s) timing-enforced.",
            )
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
                    log(
                        "manim_render",
                        f"  Sec {sec_id}: no _manim_segment_specs, skipping.",
                    )
                    continue

                log(
                    "manim_render",
                    f"  Sec {sec_id}: rendering {len(internal_specs)} beat video(s)...",
                )
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
                        # V2 player reads beat_video_paths — mirror manim_video_paths so all beats play
                        section["beat_video_paths"] = section["manim_video_paths"]
                    rendered_total += len(rendered)
                    log(
                        "manim_render",
                        f"  ✅ Sec {sec_id}: {len(rendered)} beat video(s) done.",
                    )

                except Exception as render_err:
                    logger.warning(
                        f"[V3] Manim render failed for sec {sec_id}: {render_err}"
                    )
                    log("manim_render", f"  ⚠️ Sec {sec_id} render failed: {render_err}")

            log(
                "manim_render",
                f"✅ Phase 3.7 complete: {rendered_total} beat video(s) rendered.",
            )

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
    # Phase 3.7b: Render quiz explanation_visual Manim
    # Handles questions[].explanation_visual with renderer="manim" for ALL
    # section types (content, image_to_video, etc.) — not just per_question.
    # ─────────────────────────────────────────────
    if not skip_manim:
        log("manim_render", "Phase 3.7b: Rendering quiz explanation_visual Manim...")
        try:
            from render.manim.manim_runner import _render_manim_segment_specs

            quiz_manim_rendered = 0
            for section in presentation.get("sections", []):
                sec_id = section.get("section_id", "?")
                # Check both understanding_quiz and questions[]
                quiz_sources = []
                if section.get("understanding_quiz"):
                    quiz_sources.append(
                        ("understanding_quiz", section["understanding_quiz"])
                    )
                for qi, q in enumerate(section.get("questions", [])):
                    quiz_sources.append((f"question_{qi}", q))

                for q_label, q_obj in quiz_sources:
                    exp_visual = q_obj.get("explanation_visual", {})
                    if not exp_visual:
                        continue
                    if exp_visual.get("renderer") != "manim":
                        continue

                    # NEW: support manim_beats[] array (new V3 schema)
                    # Falls back to legacy manim_scene_spec string
                    manim_beats_ev = exp_visual.get("manim_beats", [])
                    if manim_beats_ev:
                        for beat_idx_ev, beat_ev in enumerate(manim_beats_ev):
                            manim_spec_str = beat_ev.get("manim_scene_spec", "")
                            if not manim_spec_str:
                                continue
                            duration = beat_ev.get(
                                "duration", exp_visual.get("duration_seconds", 15.0)
                            )
                            spec = {
                                "segment_id": f"quiz_{sec_id}_{q_label}_beat{beat_idx_ev}",
                                # Use the LLM beat_id (e.g. "eq_beat_1") so the output file
                                # is topic_N_eq_beat_1.mp4 and does NOT overwrite beat_0.mp4
                                "beat_id": beat_ev.get(
                                    "beat_id", f"eq_beat_{beat_idx_ev}"
                                ),
                                "beat_idx": beat_idx_ev,
                                "py_path": None,
                                "duration_seconds": duration,
                                "topic_id": sec_id,
                                "manim_scene_spec": manim_spec_str,
                            }
                            log(
                                "manim_render",
                                f"  Sec {sec_id} / {q_label} beat {beat_idx_ev}: rendering explanation_visual manim ({duration}s)...",
                            )
                            try:
                                from core.agents.manim_code_generator import (
                                    ManimCodeGenerator,
                                    build_v3_segment_data,
                                )

                                gen = ManimCodeGenerator()
                                segment_data = build_v3_segment_data(
                                    section=section,
                                    spec={
                                        "manim_scene_spec": manim_spec_str,
                                        "segment_id": spec["segment_id"],
                                    },
                                    seg_id=spec["segment_id"],
                                    duration=duration,
                                )
                                manim_code, errors = gen.generate(segment_data)
                                if not manim_code:
                                    log(
                                        "manim_render",
                                        f"    ⚠️ Code gen failed for {q_label} beat {beat_idx_ev}: {errors}",
                                    )
                                    continue
                                manim_dir = output_path / "manim"
                                manim_dir.mkdir(parents=True, exist_ok=True)
                                py_filename = (
                                    f"topic_{sec_id}_{q_label}_beat{beat_idx_ev}.py"
                                )
                                py_path = manim_dir / py_filename
                                py_path.write_text(manim_code, encoding="utf-8")
                                spec["py_path"] = str(py_path)
                                rendered = _render_manim_segment_specs(
                                    specs=[spec],
                                    topic_id=sec_id,
                                    topic_title=section.get("title", ""),
                                    output_dir=str(output_path / "videos"),
                                    dry_run=dry_run,
                                    topic=None,  # Don't write quiz video into main narration segments
                                )
                                if rendered:
                                    rel_path = f"videos/{Path(rendered[0]).name}"
                                    if beat_idx_ev == 0:
                                        exp_visual["video_path"] = rel_path
                                    quiz_manim_rendered += 1
                                    log(
                                        "manim_render",
                                        f"    ✅ {q_label} beat {beat_idx_ev} → {rel_path}",
                                    )
                            except Exception as qe:
                                log(
                                    "manim_render",
                                    f"    ⚠️ {q_label} beat {beat_idx_ev} failed: {qe}",
                                )
                        continue  # skip legacy manim_scene_spec path

                    manim_spec_str = exp_visual.get("manim_scene_spec", "")
                    if not manim_spec_str:
                        continue

                    duration = exp_visual.get("duration_seconds", 15.0)
                    spec = {
                        "segment_id": f"quiz_{sec_id}_{q_label}",
                        # Use eq_beat_0 so this never collides with main section beat_0
                        "beat_id": exp_visual.get("beat_id", "eq_beat_0"),
                        "beat_idx": 0,
                        "py_path": None,  # will be generated fresh
                        "duration_seconds": duration,
                        "topic_id": sec_id,
                        "manim_scene_spec": manim_spec_str,
                    }
                    log(
                        "manim_render",
                        f"  Sec {sec_id} / {q_label}: rendering explanation_visual manim ({duration}s)...",
                    )
                    try:
                        # Generate .py code first
                        from core.agents.manim_code_generator import (
                            ManimCodeGenerator,
                            build_v3_segment_data,
                        )

                        gen = ManimCodeGenerator()
                        segment_data = build_v3_segment_data(
                            section=section,
                            spec={
                                "manim_scene_spec": manim_spec_str,
                                "segment_id": spec["segment_id"],
                            },
                            seg_id=spec["segment_id"],
                            duration=duration,
                        )
                        manim_code, errors = gen.generate(segment_data)
                        if not manim_code:
                            log(
                                "manim_render",
                                f"    ⚠️ Code gen failed for {q_label}: {errors}",
                            )
                            continue

                        manim_dir = output_path / "manim"
                        manim_dir.mkdir(parents=True, exist_ok=True)
                        py_filename = f"topic_{sec_id}_{q_label}.py"
                        py_path = manim_dir / py_filename
                        py_path.write_text(manim_code, encoding="utf-8")
                        spec["py_path"] = str(py_path)

                        rendered = _render_manim_segment_specs(
                            specs=[spec],
                            topic_id=sec_id,
                            topic_title=section.get("title", ""),
                            output_dir=str(output_path / "videos"),
                            dry_run=dry_run,
                            topic=None,  # Don't write quiz video into main narration segments
                        )
                        if rendered:
                            rel_path = f"videos/{Path(rendered[0]).name}"
                            exp_visual["video_path"] = rel_path
                            quiz_manim_rendered += 1
                            log("manim_render", f"    ✅ {q_label} → {rel_path}")
                    except Exception as qe:
                        log("manim_render", f"    ⚠️ {q_label} failed: {qe}")

            log(
                "manim_render",
                f"✅ Phase 3.7b complete: {quiz_manim_rendered} quiz visual(s) rendered.",
            )

            # Save updated presentation.json
            try:
                from core.locks import presentation_lock

                with presentation_lock:
                    with open(pres_path, "w", encoding="utf-8") as f:
                        json.dump(presentation, f, indent=2, ensure_ascii=False)
            except ImportError:
                with open(pres_path, "w", encoding="utf-8") as f:
                    json.dump(presentation, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.warning(f"[V3] Phase 3.7b error (non-fatal): {e}")
            log("manim_render", f"⚠️ Phase 3.7b error (non-fatal): {e}")

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
        if s.get("renderer")
        in ("video", "text_to_video", "image_to_video", "per_question")
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
                    dry_run=dry_run,
                    skip_wan=skip_wan,
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

        # ── Save presentation.json with all video paths written by writeback ──
        try:
            with open(pres_path, "w", encoding="utf-8") as f:
                json.dump(presentation, f, indent=2, ensure_ascii=False)
            log("wan_video", "✅ presentation.json saved with video paths.")
        except Exception as e:
            logger.warning(
                f"[V3] Failed to save presentation.json after video gen: {e}"
            )

    # ─────────────────────────────────────────────
    # Phase 6.5a: Infographic Image Generation
    # V3: Handle infographic sections (memory_infographic, etc.)
    # Generates static PNG images via Gemini — no video animation
    # ─────────────────────────────────────────────
    infographic_sections = [
        s
        for s in presentation.get("sections", [])
        if s.get("renderer") == "infographic"
    ]
    if infographic_sections and not skip_wan:
        log(
            "infographic",
            f"Starting infographic generation for {len(infographic_sections)} section(s)...",
        )
        try:
            from core.renderer_executor import execute_renderer

            for section in infographic_sections:
                section_id = section.get("section_id", "?")
                log("infographic", f"  Processing infographic section {section_id}...")

                result = execute_renderer(
                    topic=section,
                    output_dir=str(output_path / "images"),
                    dry_run=dry_run,
                    skip_wan=skip_wan,
                    video_provider=video_provider,
                )

                if result.get("status") == "success":
                    log("infographic", f"    ✅ Section {section_id} complete")
                else:
                    log(
                        "infographic",
                        f"    ❌ Section {section_id} failed: {result.get('error', 'Unknown error')}",
                    )

            log(
                "infographic",
                f"✅ Infographic generation complete for {len(infographic_sections)} section(s).",
            )
        except Exception as e:
            logger.warning(f"[V3] Infographic generation error (non-fatal): {e}")
            log("infographic", f"⚠️ Infographic error (non-fatal): {e}")

        # ── Save presentation.json with image paths ──
        try:
            with open(pres_path, "w", encoding="utf-8") as f:
                json.dump(presentation, f, indent=2, ensure_ascii=False)
            log(
                "infographic",
                "✅ presentation.json saved with infographic image paths.",
            )
        except Exception as e:
            logger.warning(
                f"[V3] Failed to save presentation.json after infographic gen: {e}"
            )

    # V3: Handle per_question quiz sections - each question has its own explanation_visual renderer
    per_question_sections = [
        s for s in video_sections if s.get("renderer") == "per_question"
    ]
    if per_question_sections and not skip_wan:
        log(
            "wan_video",
            f"Starting per_question quiz explanation_visual generation for {len(per_question_sections)} section(s)...",
        )
        try:
            from core.renderer_executor import execute_renderer

            total_processed = 0
            for section in per_question_sections:
                section_id = section.get("section_id", "?")
                questions = section.get("questions", [])
                log(
                    "wan_video",
                    f"  Processing quiz section {section_id} with {len(questions)} question(s)...",
                )

                for qi, question in enumerate(questions):
                    q_id = question.get("question_id", f"q{qi + 1}")
                    exp_visual = question.get("explanation_visual", {})
                    exp_renderer = exp_visual.get("renderer", "")

                    if not exp_renderer or exp_renderer == "none":
                        log(
                            "wan_video",
                            f"    Q{q_id}: no explanation_visual renderer, skipping.",
                        )
                        continue

                    log(
                        "wan_video",
                        f"    Q{q_id}: processing explanation_visual with renderer={exp_renderer}...",
                    )

                    # Process the explanation_visual using execute_renderer
                    result = execute_renderer(
                        topic=exp_visual,
                        output_dir=str(output_path / "videos"),
                        dry_run=dry_run,
                        skip_wan=skip_wan,
                        video_provider=video_provider,
                    )

                    if result.get("status") == "success":
                        video_path = result.get("video_path", "")
                        question["explanation_visual_video_path"] = video_path
                        total_processed += 1
                        log(
                            "wan_video",
                            f"    ✅ Q{q_id} explanation_visual complete: {video_path}",
                        )
                    else:
                        log(
                            "wan_video",
                            f"    ❌ Q{q_id} failed: {result.get('error', 'Unknown error')}",
                        )

            log(
                "wan_video",
                f"✅ Per-question explanation_visual complete: {total_processed} visual(s) generated.",
            )
        except Exception as e:
            logger.warning(
                f"[V3] Per-question explanation_visual error (non-fatal): {e}"
            )
            log("wan_video", f"⚠️ Per-question error (non-fatal): {e}")

    # V3: Handle explanation_visual GPU video for ALL section types (content, image_to_video, etc.)
    # Mirrors Phase 3.7b logic but for image_to_video / text_to_video renderers —
    # the per_question_sections block above only catches renderer=="per_question" sections,
    # missing explanation_visuals nested inside content/image_to_video sections.
    if not skip_wan:
        log(
            "wan_video",
            "Phase 6.5b: Scanning ALL sections for quiz explanation_visual GPU video...",
        )
        try:
            from core.renderer_executor import execute_renderer

            quiz_gpu_rendered = 0
            for section in presentation.get("sections", []):
                sec_id = section.get("section_id", "?")
                # Skip per_question sections — already handled above
                if section.get("renderer") == "per_question":
                    continue

                # Collect quiz sources: understanding_quiz and bare questions[]
                quiz_sources = []
                if section.get("understanding_quiz"):
                    quiz_sources.append(
                        ("understanding_quiz", section["understanding_quiz"])
                    )
                for qi, q in enumerate(section.get("questions", [])):
                    quiz_sources.append((f"question_{qi}", q))

                for q_label, q_obj in quiz_sources:
                    # understanding_quiz can be either:
                    #   (a) a flat single-question object {question, options, explanation_visual, ...}
                    #   (b) a container with questions[] array [{question_id, explanation_visual}, ...]
                    nested = q_obj.get("questions", [])
                    if nested:
                        questions_to_check = nested
                    elif q_obj.get("explanation_visual"):
                        # Flat format — the quiz object itself IS the single question
                        questions_to_check = [q_obj]
                    else:
                        questions_to_check = []

                    for qi2, question in enumerate(questions_to_check):
                        q_id = question.get("question_id", f"q{qi2 + 1}")
                        exp_visual = question.get("explanation_visual", {})
                        if not exp_visual:
                            continue
                        exp_renderer = exp_visual.get("renderer", "")
                        if exp_renderer not in (
                            "image_to_video",
                            "text_to_video",
                            "video",
                        ):
                            continue

                        log(
                            "wan_video",
                            f"  Sec {sec_id} / {q_label} / Q{q_id}: rendering explanation_visual ({exp_renderer})...",
                        )
                        # Inject section_id so execute_renderer() produces correct filename
                        # (e.g. topic_3_eq_beat_1.mp4 instead of topic_1_eq_beat_1.mp4)
                        if not exp_visual.get("section_id"):
                            exp_visual["section_id"] = sec_id
                        result = execute_renderer(
                            topic=exp_visual,
                            output_dir=str(output_path / "videos"),
                            dry_run=dry_run,
                            skip_wan=skip_wan,
                            video_provider=video_provider,
                        )
                        if result.get("status") == "success":
                            video_path = result.get("video_path", "")
                            question["explanation_visual_video_path"] = video_path
                            exp_visual["video_path"] = video_path
                            quiz_gpu_rendered += 1
                            log("wan_video", f"    ✅ Q{q_id} → {video_path}")
                        else:
                            log(
                                "wan_video",
                                f"    ❌ Q{q_id} failed: {result.get('error', 'Unknown error')}",
                            )

            log(
                "wan_video",
                f"✅ Phase 6.5b complete: {quiz_gpu_rendered} explanation_visual(s) rendered.",
            )

            # Save updated presentation.json
            if quiz_gpu_rendered > 0:
                try:
                    with open(pres_path, "w", encoding="utf-8") as f:
                        json.dump(presentation, f, indent=2, ensure_ascii=False)
                    log("wan_video", "✅ presentation.json saved after Phase 6.5b.")
                except Exception as e:
                    logger.warning(
                        f"[V3] Failed to save presentation.json after Phase 6.5b: {e}"
                    )

        except Exception as e:
            logger.warning(f"[V3] Phase 6.5b error (non-fatal): {e}")
            log("wan_video", f"⚠️ Phase 6.5b error (non-fatal): {e}")

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

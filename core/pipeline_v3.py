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
    # Phase 3.5: Manim Code Generation
    # Runs after Avatar generation. Generates Python code per section
    # using the exactly known actual avatar duration for timing.
    # ─────────────────────────────────────────────
    if skip_manim:
        log("manim_gen", "Skipping Manim generation (skip_manim=True).")
    else:
        log("manim_gen", "Generating Manim code (with real avatar durations)...")

        try:
            from core.agents.manim_code_generator import (
                ManimCodeGenerator,
                build_manim_section_data,
                integrate_manim_code_into_section,
            )

            gen = ManimCodeGenerator()
            manim_dir = output_path / "manim"
            manim_dir.mkdir(parents=True, exist_ok=True)

            sections = presentation.get("sections", [])
            manim_sections = [s for s in sections if s.get("renderer") == "manim"]

            log("manim_gen", f"Found {len(manim_sections)} Manim sections.")

            for section in manim_sections:
                sec_id = section.get("section_id", "0")
                render_spec = section.get("render_spec", {})
                segment_specs = render_spec.get("segment_specs", [])

                # Pull narration segments with REAL TTS durations (updated by Phase 3)
                narration_segments = section.get("narration", {}).get("segments", [])

                # Use real avatar_duration_seconds from Phase 3.3 if available
                total_avatar_sec = section.get("avatar_duration_seconds", None)
                total_narration_secs = (
                    sum(
                        seg.get("duration_seconds") or seg.get("duration", 5.0)
                        for seg in narration_segments
                    )
                    if narration_segments
                    else None
                )

                # Target duration: avatar MP4 > TTS estimate > section default
                target_duration = (
                    total_avatar_sec
                    or total_narration_secs
                    or section.get("segment_duration_seconds", 20)
                )

                # Build manim_spec from render_spec segment_specs or section-level
                manim_spec = ""
                if segment_specs:
                    # Combine all segment specs into one visual description
                    spec_parts = []
                    for spec in segment_specs:
                        ms = spec.get("manim_scene_spec", "")
                        if ms:
                            spec_parts.append(ms)
                    manim_spec = " ".join(spec_parts)
                if not manim_spec:
                    manim_spec = section.get("manim_scene_spec", "") or render_spec.get(
                        "manim_scene_spec", ""
                    )

                if not manim_spec:
                    log("manim_gen", f"  Sec {sec_id}: no manim_scene_spec, skipping.")
                    continue

                # Build section_data for ManimCodeGenerator
                section_data = {
                    "section_title": section.get("title", "Educational Section"),
                    "manim_spec": manim_spec,
                    "visual_description": manim_spec,
                    "narration_segments": [
                        {
                            "text": seg.get("text", ""),
                            "duration": float(
                                seg.get("duration_seconds") or seg.get("duration", 5.0)
                            ),
                        }
                        for seg in narration_segments
                    ],
                    "formulas": section.get("formulas", []),
                    "key_terms": section.get("key_terms", []),
                    "special_requirements": "",
                }

                log(
                    "manim_gen",
                    f"  Generating Sec {sec_id} (target_dur={target_duration:.1f}s)...",
                )

                manim_code, errors = gen.generate(section_data)

                if manim_code:
                    # Save the .py file
                    py_filename = f"topic_{sec_id}.py"
                    py_path = manim_dir / py_filename
                    with open(py_path, "w", encoding="utf-8") as f:
                        f.write(manim_code)

                    # Store paths in presentation.json for later rendering
                    rel_py_path = f"manim/{py_filename}"
                    section["manim_code_path"] = rel_py_path

                    # Also store in render_spec for renderer_executor compatibility
                    integrate_manim_code_into_section(section, manim_code)

                    log("manim_gen", f"  ✅ Saved: {rel_py_path}")
                else:
                    log("manim_gen", f"  ⚠️ Sec {sec_id} generation failed: {errors}")

        except V3PipelineError:
            raise
        except Exception as e:
            logger.warning(f"[V3] Manim code generation error (non-fatal): {e}")
            log("manim_gen", f"⚠️ Manim gen error (non-fatal): {e}")

        # ── Save presentation.json with manim code paths ──────────
        try:
            from core.locks import presentation_lock

            with presentation_lock:
                with open(pres_path, "w", encoding="utf-8") as f:
                    json.dump(presentation, f, indent=2, ensure_ascii=False)
        except ImportError:
            with open(pres_path, "w", encoding="utf-8") as f:
                json.dump(presentation, f, indent=2, ensure_ascii=False)
        log("manim_gen", "✅ presentation.json updated with Manim code paths.")

    # ─────────────────────────────────────────────
    # (Phase 5 Avatar Generation was moved up to Phase 3.3)
    # ─────────────────────────────────────────────

    # ─────────────────────────────────────────────
    # Phase 3.6: Manim Timing Enforcement (VSYNC-001)
    # V3 Core Goal: Perfect avatar–animation sync.
    # Runs AFTER avatar generation so avatar_duration_seconds is available.
    # Scales self.wait() calls in generated .py files to match real MP4 duration.
    # ─────────────────────────────────────────────
    if not skip_manim and not skip_avatar:
        log(
            "manim_timing_enforce",
            "Phase 3.6: Enforcing Manim timing against real avatar durations...",
        )
        try:
            # Re-read presentation.json: avatar_generator has written avatar_duration_seconds
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
                f"✅ Phase 3.6 complete: {patched} Manim file(s) timing-enforced.",
            )
        except Exception as e:
            logger.warning(f"[V3] Manim timing enforcement error (non-fatal): {e}")
            log("manim_timing_enforce", f"⚠️ Phase 3.6 error (non-fatal): {e}")

    # ─────────────────────────────────────────────
    # Phase 3.7: Manim Render (execute Manim CLI → .mp4)
    # Renders the timing-enforced .py files into video files.
    # ─────────────────────────────────────────────
    if not skip_manim:
        log("manim_render", "Phase 3.7: Rendering Manim videos...")
        try:
            from render.manim.manim_runner import render_manim_video

            sections = presentation.get("sections", [])
            manim_sections = [s for s in sections if s.get("renderer") == "manim"]
            rendered_count = 0

            for section in manim_sections:
                sec_id = section.get("section_id", "0")
                manim_code_path = section.get("manim_code_path")
                if not manim_code_path:
                    log(
                        "manim_render",
                        f"  Sec {sec_id}: no manim_code_path, skipping render.",
                    )
                    continue

                abs_py_path = output_path / manim_code_path
                if not abs_py_path.exists():
                    log(
                        "manim_render",
                        f"  Sec {sec_id}: {manim_code_path} not found, skipping.",
                    )
                    continue

                log("manim_render", f"  Rendering Sec {sec_id}...")
                try:
                    video_result = render_manim_video(
                        topic=section,
                        output_dir=str(output_path / "videos"),
                        dry_run=dry_run,
                    )

                    # Store video path(s) in section
                    if isinstance(video_result, list):
                        section["manim_video_paths"] = video_result
                        section["video_path"] = (
                            video_result[0] if video_result else None
                        )
                    elif video_result:
                        section["manim_video_paths"] = [video_result]
                        section["video_path"] = video_result

                    rendered_count += 1
                    log("manim_render", f"  ✅ Sec {sec_id}: rendered → {video_result}")

                except Exception as render_err:
                    logger.warning(
                        f"[V3] Manim render failed for sec {sec_id}: {render_err}"
                    )
                    log("manim_render", f"  ⚠️ Sec {sec_id} render failed: {render_err}")

            log(
                "manim_render",
                f"✅ Phase 3.7 complete: {rendered_count} video(s) rendered.",
            )

            # FIX: Populate manim_video_paths from segment-level beat_videos if not already set
            for section in manim_sections:
                if not section.get("manim_video_paths"):
                    segment_videos = []
                    narration = section.get("narration", {})
                    for seg in narration.get("segments", []):
                        beat_videos = seg.get("beat_videos", [])
                        if beat_videos:
                            segment_videos.extend(beat_videos)
                    if segment_videos:
                        section["manim_video_paths"] = segment_videos
                        if not section.get("video_path"):
                            section["video_path"] = segment_videos[0]
                        log(
                            "manim_render",
                            f"  📝 Sec {section.get('section_id')}: populated manim_video_paths from segments",
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
    # renderer: "video" sections — Biology, History, Geography
    # UNCHANGED from V2 — WAN handles non-math visual content.
    # ─────────────────────────────────────────────
    video_sections = [
        s for s in presentation.get("sections", []) if s.get("renderer") == "video"
    ]
    if video_sections and not skip_wan:
        log(
            "wan_video",
            f"Starting WAN/LTX video generation for {len(video_sections)} renderer:video section(s)...",
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
    else:
        log("wan_video", "No renderer:video sections — skipping WAN/LTX.")

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

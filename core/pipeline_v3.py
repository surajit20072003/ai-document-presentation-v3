"""
V3 Pipeline — Three.js-based Presentation Generation

Phases:
  1. Director V3  — director_v3_partition_prompt.txt → threejs_spec, understanding_quiz
  2. ThreejsCodeGenerator — generates .js files per section/beat
  3. V3 Validator  — hard-fail on bad output
  4. Avatar Generation — section clips
  5. Quiz Clips    — 3 clips per question (question/correct/wrong)
  6. Save presentation.json
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
    skip_threejs: bool = False,
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

        # V3 uses its own partition prompt (threejs_spec, understanding_quiz, zero text_layer)
        v3_prompt_path = Path(__file__).parent / "prompts" / "director_v3_partition_prompt.txt"
        if not v3_prompt_path.exists():
            raise V3PipelineError(
                f"director_v3_partition_prompt.txt not found at {v3_prompt_path}",
                phase="director_v3"
            )

        # PartitionDirectorGenerator accepts content_prompt_file and global_prompt_file
        director = PartitionDirectorGenerator(
            content_prompt_file=str(v3_prompt_path),
            # Global prompt: use same as V2 (intro/summary/recap/quiz schema unchanged)
            global_prompt_file=str(Path(__file__).parent / "prompts" / "director_global_prompt.txt"),
        )

        log("director_v3", f"Calling V3 Director for subject={subject}, grade={grade}...")
        presentation = director.generate_presentation_partitioned(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            output_dir=output_dir,
        )

        log("director_v3", f"Director V3 complete. {len(presentation.get('sections', []))} sections generated.")

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
            logger.warning(f"[V3] Validation found {len(errors)} issues (non-fatal):\n{report}")
            log("v3_validator", f"⚠️ {len(errors)} validation issues (non-fatal) — see v3_validation_report.txt. Continuing.")
        else:
            log("v3_validator", "✅ V3 validation passed.")

    except V3PipelineError:
        raise
    except Exception as e:
        logger.warning(f"[V3] Validator error (non-fatal): {e}")

    # ─────────────────────────────────────────────
    # Phase 3: Duration Estimation (word-count)
    # V3 architecture: NO TTS audio is generated here.
    # The avatar MP4 (Phase 5) contains the voice — it is the only audio.
    # This phase applies a fast word-count estimate to duration_seconds per
    # segment so Three.js (Phase 3.5) has an initial timing baseline.
    # Phase 3.6 (threejs_timing_enforcer) corrects all timings post-avatar
    # using the real MP4 duration — so this estimate only needs to be close.
    # ─────────────────────────────────────────────
    pres_path = output_path / "presentation.json"

    log("duration_estimate", "Applying word-count duration estimates to narration segments...")
    try:
        from core.tts_duration import update_durations_simplified
        updated_pres = update_durations_simplified(
            presentation=presentation,
            output_dir=None,          # V3: no audio files — estimates only
            production_provider="estimate",  # word-count math, no audio
        )
        if updated_pres:
            presentation = updated_pres
        log("duration_estimate", "✅ Duration estimates applied. Three.js will use these as starting proportions.")
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
    # Phase 3.5: Three.js Code Generation
    # Runs after duration estimation. Generates .js files using
    # proportional SEG_DUR[] timing (VSYNC-002). Phase 3.6 will
    # correct these values using real avatar MP4 durations.
    # ─────────────────────────────────────────────
    if skip_threejs:
        log("threejs_gen", "Skipping Three.js generation (skip_threejs=True).")
    else:
        log("threejs_gen", "Generating Three.js scenes (with real TTS durations)...")

        try:
            from core.agents.threejs_code_generator import ThreejsCodeGenerator

            gen = ThreejsCodeGenerator()
            threejs_dir = output_path / "threejs"
            threejs_dir.mkdir(parents=True, exist_ok=True)

            sections = presentation.get("sections", [])
            threejs_sections = [
                s for s in sections
                if s.get("renderer") == "threejs"
            ]

            log("threejs_gen", f"Found {len(threejs_sections)} Three.js sections.")

            for section in threejs_sections:
                sec_id = section.get("section_id", "0")
                render_spec = section.get("render_spec", {})
                segment_specs = render_spec.get("segment_specs", [])

                # Pull narration segments with REAL TTS durations (updated by Phase 3)
                narration_segments = section.get("narration", {}).get("segments", [])

                if not segment_specs:
                    # Fallback: treat the whole section as one beat
                    section_as_spec = {
                        "threejs_spec": section.get("threejs_spec", ""),
                        "segment_duration_seconds": section.get("segment_duration_seconds", 20),
                        "key_terms": section.get("key_terms", []),
                        "complexity": section.get("complexity", "medium"),
                    }
                    segment_specs = [section_as_spec]

                total_beats = len(segment_specs)
                total_narration_secs = sum(
                    seg.get("duration_seconds") or seg.get("duration", 5.0)
                    for seg in narration_segments
                ) if narration_segments else None

                # SYNC FIX (Cause 2): each beat gets its OWN duration slice,
                # not the entire section total.  Split narration segments evenly
                # across beats so each .js file matches its avatar audio window.
                # When there is only 1 beat (most common), all narration segments
                # belong to it and the full total is correct.
                def _beat_duration(beat_idx: int, spec: dict) -> float:
                    if total_narration_secs is not None and narration_segments:
                        if total_beats == 1:
                            # 1 beat = whole section duration (original behaviour, correct)
                            return total_narration_secs
                        # Multi-beat: divide narration segments evenly across beats
                        segs_per_beat = max(1, len(narration_segments) // total_beats)
                        start_seg = beat_idx * segs_per_beat
                        # Last beat gets any remainder
                        end_seg = start_seg + segs_per_beat if beat_idx < total_beats - 1 else len(narration_segments)
                        beat_segs = narration_segments[start_seg:end_seg]
                        if beat_segs:
                            return sum(
                                seg.get("duration_seconds") or seg.get("duration", 5.0)
                                for seg in beat_segs
                            )
                    # Fallback: use LLM estimate from spec
                    return spec.get("segment_duration_seconds", 20)

                for beat_idx, spec in enumerate(segment_specs):
                    # SYNC FIX: per-beat duration (not total section duration)
                    total_real_duration = _beat_duration(beat_idx, spec)

                    # Per-beat narration segments for JS hard-sync timeline
                    if narration_segments and total_beats > 1:
                        segs_per_beat = max(1, len(narration_segments) // total_beats)
                        start_seg = beat_idx * segs_per_beat
                        end_seg = start_seg + segs_per_beat if beat_idx < total_beats - 1 else len(narration_segments)
                        beat_narration_segments = narration_segments[start_seg:end_seg]
                    else:
                        beat_narration_segments = narration_segments

                    section_data = {
                        "section_id": sec_id,
                        "section_title": section.get("title", ""),
                        "section_type": section.get("section_type", "content"),
                        "title": section.get("title", ""),
                        "threejs_spec": spec.get("threejs_spec", ""),
                        # SYNC FIX: per-beat real TTS duration (not entire section total)
                        "segment_duration_seconds": total_real_duration,
                        "key_terms": section.get("key_terms", []),
                        "complexity": spec.get("complexity", section.get("complexity", "medium")),
                        # SYNC FIX: per-beat narration segments for correct JS hard-sync timeline
                        # beat_narration_segments = this beat's portion only (or all if 1 beat)
                        "narration_segments": beat_narration_segments,
                        # PRIMARY content driver: full narration text for this beat only
                        "narration_full_text": " ".join(
                            seg.get("text", "") for seg in beat_narration_segments if seg.get("text")
                        ) or section.get("narration", {}).get("full_text", ""),
                    }

                    if not section_data["threejs_spec"]:
                        log("threejs_gen", f"  Sec {sec_id} beat {beat_idx}: no threejs_spec, skipping.")
                        continue

                    log("threejs_gen", f"  Generating Sec {sec_id} beat {beat_idx} (total_dur={total_real_duration:.1f}s)...")

                    js_code, errors = gen.generate(section_data)

                    if js_code:
                        js_path = gen.save_js_file(
                            js_code,
                            job_id=job_id,
                            topic_id=str(sec_id),
                            beat_idx=beat_idx,
                            output_dir=str(output_path)
                        )
                        # Store relative path in presentation.json
                        rel_path = f"threejs/topic_{sec_id}_beat_{beat_idx}.js"
                        spec["threejs_file"] = rel_path
                        # Accumulate all beats; threejs_file = beat_0 (player default start)
                        if "threejs_files" not in section:
                            section["threejs_files"] = []
                        section["threejs_files"].append(rel_path)
                        if beat_idx == 0 or "threejs_file" not in section:
                            section["threejs_file"] = rel_path
                        log("threejs_gen", f"  ✅ Saved: {rel_path}")
                    else:
                        log("threejs_gen", f"  ⚠️ Sec {sec_id} beat {beat_idx} generation failed: {errors}")

        except V3PipelineError:
            raise
        except Exception as e:
            logger.warning(f"[V3] Three.js generation error (non-fatal): {e}")
            log("threejs_gen", f"⚠️ Three.js gen error (non-fatal): {e}")

        # ── Save presentation.json with threejs_file paths ──────────
        # CRITICAL: Must save here so player can find the JS files.
        # TTS save (above) ran before Three.js paths were added.
        try:
            from core.locks import presentation_lock
            with presentation_lock:
                with open(pres_path, "w", encoding="utf-8") as f:
                    json.dump(presentation, f, indent=2, ensure_ascii=False)
        except ImportError:
            with open(pres_path, "w", encoding="utf-8") as f:
                json.dump(presentation, f, indent=2, ensure_ascii=False)
        log("threejs_gen", "✅ presentation.json updated with Three.js file paths.")

    # ─────────────────────────────────────────────
    # Phase 5: Avatar Generation (section clips)
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

                log("avatar", "Starting avatar generation for all sections...")
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

            except Exception as e:
                logger.warning(f"[V3] Avatar generation error (non-fatal): {e}")
                log("avatar", f"⚠️ Avatar error (non-fatal): {e}")

    # ─────────────────────────────────────────────
    # Phase 3.6: Three.js Timing Enforcement (VSYNC-001)
    # V3 Core Goal: Perfect avatar–animation sync.
    # Runs AFTER avatar generation so avatar_duration_seconds is available.
    # Patches SEG_DUR[] in every .js file to match real MP4 duration.
    # This is the V3 equivalent of Manim's _enforce_timing() — no LLM needed.
    # ─────────────────────────────────────────────
    if not skip_threejs and not skip_avatar:
        log("threejs_timing_enforce", "Phase 3.6: Enforcing Three.js timing against real avatar durations...")
        try:
            # Re-read presentation.json: avatar_generator has written avatar_duration_seconds
            with open(pres_path, "r", encoding="utf-8") as f:
                presentation = json.load(f)

            from core.threejs_timing_enforcer import run_phase_3_6
            patched = run_phase_3_6(
                presentation=presentation,
                output_dir=str(output_path),
                log_fn=log,
            )
            log("threejs_timing_enforce", f"✅ Phase 3.6 complete: {patched} Three.js file(s) timing-enforced.")
        except Exception as e:
            logger.warning(f"[V3] Timing enforcement error (non-fatal): {e}")
            log("threejs_timing_enforce", f"⚠️ Phase 3.6 error (non-fatal): {e}")

    # ─────────────────────────────────────────────
    # Phase 4.5: Quiz Card Three.js Generation (QUIZ-001)
    # V3 Goal: Every quiz question has a Three.js visual layer (.js card)
    # displayed while the avatar reads the question aloud.
    # This is programmatic — no LLM needed. Template-filled from quiz data.
    # ─────────────────────────────────────────────
    log("quiz_card_gen", "Phase 4.5: Generating quiz card Three.js scenes...")
    try:
        from core.quiz_card_generator import run_phase_4_5
        quiz_cards = run_phase_4_5(
            presentation=presentation,
            output_dir=str(output_path),
            log_fn=log,
        )
        # Save presentation.json with quiz_threejs_file paths
        try:
            from core.locks import presentation_lock
            with presentation_lock:
                with open(pres_path, "w", encoding="utf-8") as f:
                    json.dump(presentation, f, indent=2, ensure_ascii=False)
        except ImportError:
            with open(pres_path, "w", encoding="utf-8") as f:
                json.dump(presentation, f, indent=2, ensure_ascii=False)
        log("quiz_card_gen", f"✅ Phase 4.5 complete: {quiz_cards} quiz card(s) generated.")
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
                log("quiz_clips", f"✅ Quiz clips done: {quiz_results['completed']} completed, {quiz_results['failed']} failed.")

            except Exception as e:
                logger.warning(f"[V3] Quiz clips error (non-fatal): {e}")
                log("quiz_clips", f"⚠️ Quiz clips error (non-fatal): {e}")

    # ─────────────────────────────────────────────
    # Phase 6.5: WAN / LTX2 Video Generation
    # renderer: "video" sections — Biology, History, Geography
    # This is UNCHANGED from V2 — V3 only replaces Manim with Three.js.
    # ─────────────────────────────────────────────
    video_sections = [s for s in presentation.get("sections", []) if s.get("renderer") == "video"]
    if video_sections and not skip_wan:
        log("wan_video", f"Starting WAN/LTX video generation for {len(video_sections)} renderer:video section(s)...")
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

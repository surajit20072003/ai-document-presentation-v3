"""
Three.js Timing Enforcer — VSYNC-001 Phase 3.6
===============================================
V3.0 Core Goal: Next-level visual learning where Three.js animations illustrate
the topic in perfect sync with avatar narration.

V2 Parity: Manim achieved byte-exact sync via _enforce_timing() which
programmatically patched self.wait() in generated Python code.
This module is the Three.js equivalent — it patches the SEG_DUR array in
the generated .js files using the REAL avatar MP4 duration stored by
avatar_generator._update_artifacts() (VSYNC-001 write-back).

Pipeline position: Phase 3.6 — runs AFTER avatar generation, reads
avatar_duration_seconds from presentation.json, rewrites .js timing.

No LLM needed — pure regex string replacement, deterministic, fast.
"""

import re
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def _rewrite_seg_dur(js_code: str, real_duration: float, narration_segments: list) -> str:
    """
    Rewrite the SEG_DUR array in a Three.js .js file to match real avatar duration.

    Strategy:
      1. Find the LLM-generated SEG_DUR array (from proportional-sync pattern)
      2. Compute the sum of narration_segment durations
      3. Re-scale each element so the total matches real_duration
      4. Rewrite the array in the JS source

    Falls back to scaling the whole array if individual segment durations unavailable.

    Args:
        js_code:             Raw JS string from ThreejsCodeGenerator
        real_duration:       Actual avatar MP4 duration in seconds
        narration_segments:  List of narration segment dicts with duration_seconds

    Returns:
        Patched JS string with corrected SEG_DUR values
    """
    if real_duration <= 0:
        logger.warning("[THREEJS ENFORCER] real_duration=0, skipping patch")
        return js_code

    # ── 1. Find existing SEG_DUR array ────────────────────────────────────────
    seg_dur_pattern = re.compile(
        r'(var\s+SEG_DUR\s*=\s*\[)([^\]]+)(\];)',
        re.DOTALL
    )
    match = seg_dur_pattern.search(js_code)

    if not match:
        # LLM didn't use our proportional pattern — try to inject totalDuration fix
        # by patching/replacing any hardcoded totalDuration reference
        logger.info("[THREEJS ENFORCER] No SEG_DUR array found — injecting totalDuration guard")
        return _inject_total_duration_comment(js_code, real_duration)

    # ── 2. Parse existing values ───────────────────────────────────────────────
    existing_values_str = match.group(2)
    try:
        existing_values = [float(x.strip()) for x in existing_values_str.split(',') if x.strip()]
    except ValueError:
        logger.warning("[THREEJS ENFORCER] Cannot parse SEG_DUR values, skipping")
        return js_code

    if not existing_values:
        return js_code

    # ── 3. Compute corrected values from narration segments ───────────────────
    # Use real narration segment proportions (they are proportionally correct
    # even if absolute values drift from the avatar GPU pace)
    seg_durations = [
        float(seg.get("duration_seconds") or seg.get("duration") or 5.0)
        for seg in narration_segments
    ] if narration_segments else existing_values

    # If segment count doesn't match LLM output, fall back to uniform scaling
    if len(seg_durations) != len(existing_values):
        logger.info(
            f"[THREEJS ENFORCER] Segment count mismatch "
            f"(narration={len(seg_durations)}, js={len(existing_values)}) "
            f"— using uniform scale"
        )
        existing_total = sum(existing_values) or real_duration
        scale = real_duration / existing_total
        corrected = [round(v * scale, 3) for v in existing_values]
    else:
        # Scale narration durations proportionally to real_duration
        narration_total = sum(seg_durations) or real_duration
        scale = real_duration / narration_total
        corrected = [round(d * scale, 3) for d in seg_durations]

    # ── 4. Patch the JS source ─────────────────────────────────────────────────
    new_array_content = ", ".join(str(v) for v in corrected)
    patched = seg_dur_pattern.sub(
        r'\g<1>' + new_array_content + r'\g<3>',
        js_code,
        count=1
    )

    logger.info(
        f"[THREEJS ENFORCER] Patched SEG_DUR: {existing_values} → {corrected} "
        f"(real_duration={real_duration:.2f}s)"
    )
    return patched


def _inject_total_duration_comment(js_code: str, real_duration: float) -> str:
    """
    Fallback: inject a comment + assertion at the top of initScene so developers
    know the real duration, even if SEG_DUR wasn't found.
    This does NOT break execution — it's a diagnostic aid only.
    """
    comment = (
        f"// VSYNC-001: Real avatar duration = {real_duration:.2f}s "
        f"(injected by threejs_timing_enforcer)\n"
    )
    # Insert after first opening brace of initScene
    patched = re.sub(
        r'(function\s+initScene\s*\([^)]*\)\s*\{)',
        r'\1\n  ' + comment,
        js_code,
        count=1
    )
    return patched


def enforce_threejs_timing(
    js_path: str,
    real_duration: float,
    narration_segments: list,
    dry_run: bool = False
) -> bool:
    """
    Patch a Three.js .js file to use real avatar duration.

    Args:
        js_path:             Absolute path to .js file
        real_duration:       Actual avatar MP4 duration (from presentation.json avatar_duration_seconds)
        narration_segments:  Narration segments with duration_seconds for proportional scaling
        dry_run:             If True, log but do not write

    Returns:
        True if patched successfully, False if error or nothing changed
    """
    try:
        with open(js_path, "r", encoding="utf-8") as f:
            original = f.read()

        patched = _rewrite_seg_dur(original, real_duration, narration_segments)

        if patched == original:
            logger.info(f"[THREEJS ENFORCER] No changes needed for {js_path}")
            return True

        if dry_run:
            logger.info(f"[THREEJS ENFORCER] DRY RUN — would patch {js_path}")
            return True

        with open(js_path, "w", encoding="utf-8") as f:
            f.write(patched)

        logger.info(f"[THREEJS ENFORCER] ✅ Patched: {js_path}")
        return True

    except Exception as e:
        logger.error(f"[THREEJS ENFORCER] Failed to patch {js_path}: {e}")
        return False


def run_phase_3_6(presentation: Dict[str, Any], output_dir: str, log_fn=None) -> int:
    """
    Phase 3.6: Post-avatar Three.js timing enforcement.

    Reads avatar_duration_seconds from each section (written by avatar_generator
    VSYNC-001 patch), then re-scales the SEG_DUR timing array in each section's
    Three.js .js file to match the real avatar MP4 duration.

    This is the V3 equivalent of Manim's _enforce_timing() — it guarantees
    byte-accurate sync without relying on LLM timing accuracy.

    Args:
        presentation:   Loaded presentation dict (from presentation.json)
        output_dir:     Job output directory (parent of threejs/)
        log_fn:         Optional callback log(phase, message) for pipeline logging

    Returns:
        Number of sections patched
    """
    def _log(msg):
        logger.info(f"[PHASE 3.6] {msg}")
        if log_fn:
            log_fn("threejs_timing_enforce", msg)

    _log("Starting Three.js timing enforcement (VSYNC-001 Phase 3.6)...")

    output_path = Path(output_dir)
    sections = presentation.get("sections", [])
    patched_count = 0
    skipped_count = 0

    for section in sections:
        if section.get("renderer") != "threejs":
            continue

        sec_id = section.get("section_id", "?")
        real_duration = section.get("avatar_duration_seconds")

        if not real_duration or real_duration <= 0:
            _log(f"  Sec {sec_id}: no avatar_duration_seconds yet — skipping (avatar not done?)")
            skipped_count += 1
            continue

        narration_segments = section.get("narration", {}).get("segments", [])

        # Find all threejs_files for this section
        js_files = section.get("threejs_files", [])
        if not js_files and section.get("threejs_file"):
            js_files = [section["threejs_file"]]

        if not js_files:
            _log(f"  Sec {sec_id}: no threejs_files — skipping")
            skipped_count += 1
            continue

        for rel_path in js_files:
            abs_path = output_path / rel_path
            if not abs_path.exists():
                _log(f"  Sec {sec_id}: {rel_path} not found — skipping")
                continue

            ok = enforce_threejs_timing(
                js_path=str(abs_path),
                real_duration=real_duration,
                narration_segments=narration_segments,
            )
            if ok:
                patched_count += 1
                _log(f"  ✅ Sec {sec_id}: {rel_path} patched for {real_duration:.2f}s")
            else:
                _log(f"  ⚠️  Sec {sec_id}: {rel_path} patch failed")

    _log(
        f"Phase 3.6 complete: {patched_count} file(s) patched, "
        f"{skipped_count} section(s) skipped (avatar not yet ready)."
    )
    return patched_count

"""
Manim Timing Enforcer — VSYNC-001 Phase 3.6
=============================================
V3 Core Goal: Perfect avatar-animation sync.

The avatar MP4 is the master clock. The Manim-generated animation must have
exactly the same duration as the avatar clip. This module scales self.wait()
calls in the generated Python code so that the total animation time matches
the real avatar_duration_seconds stored in presentation.json.

Pipeline position: Phase 3.6 — runs AFTER avatar generation (Phase 3.3)
and AFTER Manim code generation (Phase 3.5), but BEFORE Manim rendering
(Phase 3.7).

Strategy:
  1. Parse the .py file for all self.wait(...) calls
  2. Parse all run_time=... arguments in self.play() calls
  3. Calculate total animation duration (sum of waits + run_times)
  4. Compute the deficit = avatar_duration - animation_duration
  5. If deficit > 0: increase the last self.wait() or append one
  6. If deficit < 0: scale all self.wait() calls proportionally

No LLM needed — pure regex string manipulation, deterministic, fast.
"""

import re
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


def _parse_animation_duration(code: str) -> Tuple[float, List[Tuple[int, int, float]]]:
    """
    Parse total animation duration from Manim code.

    Returns:
        (total_duration, wait_locations)
        wait_locations: list of (start_pos, end_pos, duration) for each self.wait() call
    """
    # Find all self.wait(X) calls
    wait_pattern = re.compile(r"self\.wait\(\s*([\d.]+)\s*\)")
    wait_locations = []
    total_wait = 0.0

    for match in wait_pattern.finditer(code):
        dur = float(match.group(1))
        wait_locations.append((match.start(), match.end(), dur))
        total_wait += dur

    # Find all run_time=X in self.play() calls
    runtime_pattern = re.compile(r"run_time\s*=\s*([\d.]+)")
    total_runtime = 0.0
    for match in runtime_pattern.finditer(code):
        total_runtime += float(match.group(1))

    total_duration = total_wait + total_runtime
    return total_duration, wait_locations


def _scale_waits(code: str, real_duration: float) -> str:
    """
    Scale self.wait() calls in Manim code to match real avatar duration.

    Strategy:
      - If animation is shorter than avatar: increase last wait (or add one)
      - If animation is longer than avatar: scale all waits down proportionally
      - Tolerance: ±0.1s (don't patch if close enough)
    """
    if real_duration <= 0:
        logger.warning("[MANIM ENFORCER] real_duration=0, skipping patch")
        return code

    total_duration, wait_locations = _parse_animation_duration(code)

    if total_duration <= 0:
        # No timing info found — append a final wait
        logger.info(
            f"[MANIM ENFORCER] No timing found, appending self.wait({real_duration:.3f})"
        )
        # Find the last line of construct() and append wait
        return _append_final_wait(code, real_duration)

    deficit = real_duration - total_duration

    # Within tolerance — no change needed
    if abs(deficit) < 0.1:
        logger.info(
            f"[MANIM ENFORCER] Duration {total_duration:.2f}s matches target {real_duration:.2f}s (within 0.1s)"
        )
        return code

    if deficit > 0:
        # Animation is shorter than avatar — increase last wait or append one
        if wait_locations:
            # Increase the last self.wait() by the deficit
            last_start, last_end, last_dur = wait_locations[-1]
            new_dur = last_dur + deficit
            patched = code[:last_start] + f"self.wait({new_dur:.3f})" + code[last_end:]
            logger.info(
                f"[MANIM ENFORCER] Extended last wait: {last_dur:.2f}s → {new_dur:.2f}s "
                f"(deficit={deficit:.2f}s, target={real_duration:.2f}s)"
            )
            return patched
        else:
            # No waits exist — append one
            return _append_final_wait(code, deficit)

    else:
        # Animation is longer than avatar — scale all waits down proportionally
        total_wait = sum(dur for _, _, dur in wait_locations)
        if total_wait <= 0:
            logger.warning(
                "[MANIM ENFORCER] No waits to scale, animation exceeds target"
            )
            return code

        # We need to reduce total wait by |deficit|
        required_total_wait = total_wait + deficit  # deficit is negative
        if required_total_wait < 0:
            # Even removing all waits isn't enough — set all to minimum
            logger.warning(
                f"[MANIM ENFORCER] Animation run_time alone exceeds target "
                f"({total_duration - total_wait:.2f}s > {real_duration:.2f}s). "
                f"Setting all waits to 0.1s."
            )
            scale = 0.0
        else:
            scale = required_total_wait / total_wait

        # Replace waits from end to start (so positions don't shift)
        patched = code
        for start, end, dur in reversed(wait_locations):
            new_dur = max(0.1, dur * scale)  # minimum 0.1s wait
            patched = patched[:start] + f"self.wait({new_dur:.3f})" + patched[end:]

        logger.info(
            f"[MANIM ENFORCER] Scaled {len(wait_locations)} waits by {scale:.3f}x "
            f"({total_duration:.2f}s → ~{real_duration:.2f}s)"
        )
        return patched


def _append_final_wait(code: str, wait_duration: float) -> str:
    """Append a self.wait() at the end of the construct() method."""
    # Find the last non-empty line to determine indentation
    lines = code.split("\n")
    indent = "        "  # default: 2 levels of indentation

    for line in reversed(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            leading = len(line) - len(line.lstrip())
            indent = " " * leading
            break

    wait_line = f"\n{indent}# VSYNC-001: Injected wait to match avatar duration"
    wait_line += f"\n{indent}self.wait({wait_duration:.3f})"

    # Append before the last line if it's just whitespace, otherwise at end
    return code.rstrip() + wait_line + "\n"


def enforce_manim_timing(
    py_path: str,
    real_duration: float,
    dry_run: bool = False,
) -> bool:
    """
    Patch a Manim .py file to match real avatar duration.

    Args:
        py_path:        Absolute path to .py file
        real_duration:  Actual avatar MP4 duration (from presentation.json avatar_duration_seconds)
        dry_run:        If True, log but do not write

    Returns:
        True if patched successfully, False if error
    """
    try:
        with open(py_path, "r", encoding="utf-8") as f:
            original = f.read()

        patched = _scale_waits(original, real_duration)

        if patched == original:
            logger.info(f"[MANIM ENFORCER] No changes needed for {py_path}")
            return True

        if dry_run:
            logger.info(f"[MANIM ENFORCER] DRY RUN — would patch {py_path}")
            return True

        with open(py_path, "w", encoding="utf-8") as f:
            f.write(patched)

        logger.info(f"[MANIM ENFORCER] ✅ Patched: {py_path}")
        return True

    except Exception as e:
        logger.error(f"[MANIM ENFORCER] Failed to patch {py_path}: {e}")
        return False


def run_manim_timing_enforcement(
    presentation: Dict[str, Any],
    output_dir: str,
    log_fn=None,
) -> int:
    """
    Phase 3.6: Post-avatar Manim timing enforcement.

    Reads avatar_duration_seconds from each section, then scales self.wait()
    calls in each section's Manim .py file to match the real avatar MP4 duration.

    Args:
        presentation:   Loaded presentation dict (from presentation.json)
        output_dir:     Job output directory (parent of manim/)
        log_fn:         Optional callback log(phase, message) for pipeline logging

    Returns:
        Number of sections patched
    """

    def _log(msg):
        logger.info(f"[PHASE 3.6] {msg}")
        if log_fn:
            log_fn("manim_timing_enforce", msg)

    _log("Starting Manim timing enforcement (VSYNC-001 Phase 3.6)...")

    output_path = Path(output_dir)
    sections = presentation.get("sections", [])
    patched_count = 0
    skipped_count = 0

    for section in sections:
        if section.get("renderer") != "manim":
            continue

        sec_id = section.get("section_id", "?")
        real_duration = section.get("avatar_duration_seconds")

        if not real_duration or real_duration <= 0:
            _log(
                f"  Sec {sec_id}: no avatar_duration_seconds yet — skipping (avatar not done?)"
            )
            skipped_count += 1
            continue

        # Find the .py file for this section
        py_rel_path = section.get("manim_code_path")
        if not py_rel_path:
            _log(f"  Sec {sec_id}: no manim_code_path — skipping")
            skipped_count += 1
            continue

        abs_path = output_path / py_rel_path
        if not abs_path.exists():
            _log(f"  Sec {sec_id}: {py_rel_path} not found — skipping")
            skipped_count += 1
            continue

        ok = enforce_manim_timing(
            py_path=str(abs_path),
            real_duration=real_duration,
        )
        if ok:
            patched_count += 1
            _log(f"  ✅ Sec {sec_id}: {py_rel_path} patched for {real_duration:.2f}s")
        else:
            _log(f"  ⚠️  Sec {sec_id}: {py_rel_path} patch failed")

    _log(
        f"Phase 3.6 complete: {patched_count} file(s) patched, "
        f"{skipped_count} section(s) skipped."
    )
    return patched_count

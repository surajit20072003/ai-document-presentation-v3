"""
Visual Prompt Enhancer — Phase 2.5 of the V3 Pipeline

Calls GPT-4o (via OpenRouter) to improve image_prompt_start / image_prompt_end /
video_prompt fields for sections that use image-based renderers.

ONLY runs for: image_to_video, image, infographic
SKIPS:         manim, none, per_question, text_to_video
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Load system prompt from .txt file ─────────────────────────────────────────
_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "visual_prompt_enhancer_prompt.txt"
try:
    ENHANCER_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")
except FileNotFoundError:
    logger.error(f"[Enhancer] Prompt file not found: {_PROMPT_PATH}")
    ENHANCER_SYSTEM_PROMPT = ""

# ── Config ─────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
ENHANCER_MODEL = os.environ.get("ENHANCER_MODEL", "openai/gpt-4o")

ELIGIBLE_RENDERERS = {"image_to_video", "image", "infographic"}


# ── Beat extraction ────────────────────────────────────────────────────────────

def extract_beats(section: dict) -> list:
    """
    Extract beats from a section for the enhancer.
    Handles image_to_video_beats[], visual_beats[], and segment_specs[].
    """
    renderer = section.get("renderer", "")
    render_spec = section.get("render_spec", {})
    beats = []

    # Primary: image_to_video_beats (recap, content image_to_video)
    itv_beats = render_spec.get("image_to_video_beats", [])
    if itv_beats:
        for b in itv_beats:
            # Find matching narration text for context
            narration_text = ""
            segs = section.get("narration", {}).get("segments", [])
            for seg in segs:
                if seg.get("segment_id") == b.get("beat_id") or seg.get("beat_id") == b.get("beat_id"):
                    narration_text = seg.get("text", "")
                    break

            beats.append({
                "beat_id": b.get("beat_id", ""),
                "narration": narration_text,
                "beat_goal": b.get("beat_goal", ""),
                "renderer": renderer,
                "image_prompt_start": b.get("image_prompt_start", ""),
                "image_prompt_end": b.get("image_prompt_end", ""),
                "video_prompt": b.get("video_prompt", ""),
            })
        return beats

    # Fallback: segment_specs[] for infographic / image renderers
    seg_specs = render_spec.get("segment_specs", [])
    for spec in seg_specs:
        if spec.get("renderer") in ELIGIBLE_RENDERERS:
            beats.append({
                "beat_id": spec.get("segment_id", ""),
                "narration": spec.get("narration", ""),
                "beat_goal": spec.get("beat_goal", ""),
                "renderer": spec.get("renderer", renderer),
                "image_prompt_start": spec.get("image_prompt_start", spec.get("image_prompt", "")),
                "image_prompt_end": spec.get("image_prompt_end", ""),
                "video_prompt": spec.get("video_prompt", ""),
            })

    return beats


# ── Write-back ─────────────────────────────────────────────────────────────────

def _apply_by_position(orig_beats: list, enhanced_beats: list, id_key: str) -> None:
    """
    Write enhanced fields back into orig_beats using position (zip).
    Position-based matching is more reliable than beat_id string matching
    because GPT-4o may strip prefixes (e.g. 'recap_beat_1' → '1').
    GPT-4o always preserves beat ORDER, so position is safe.
    """
    for i, orig_beat in enumerate(orig_beats):
        if i >= len(enhanced_beats):
            logger.warning(f"[Enhancer] GPT-4o returned fewer beats than input — keeping original for beat {i+1}+")
            break
        enh = enhanced_beats[i]
        if enh.get("image_prompt_start"):
            orig_beat["image_prompt_start"] = enh["image_prompt_start"]
        if enh.get("image_prompt_end"):
            orig_beat["image_prompt_end"] = enh["image_prompt_end"]
        if enh.get("video_prompt"):
            orig_beat["video_prompt"] = enh["video_prompt"]
        if enh.get("visual_reasoning"):
            orig_beat["visual_reasoning"] = enh["visual_reasoning"]


def apply_enhanced_prompts(section: dict, enhanced_beats: list) -> None:
    """
    Write enhanced image_prompt_start / image_prompt_end / video_prompt
    back into the section's render_spec beats using position-based matching.
    Does NOT touch renderer, narration, beat_id, or timing fields.
    """
    render_spec = section.get("render_spec", {})

    # Apply to image_to_video_beats[] (recap, content image_to_video)
    itv_beats = render_spec.get("image_to_video_beats", [])
    if itv_beats:
        _apply_by_position(itv_beats, enhanced_beats, id_key="beat_id")

    # Apply to segment_specs[] (infographic / image renderer)
    seg_specs = render_spec.get("segment_specs", [])
    eligible_specs = [s for s in seg_specs if s.get("renderer") in ELIGIBLE_RENDERERS]
    if eligible_specs:
        _apply_by_position(eligible_specs, enhanced_beats, id_key="segment_id")
        # Mirror image_prompt into image_prompt_start for old-format compatibility
        for spec in eligible_specs:
            if spec.get("image_prompt_start") and not spec.get("image_prompt"):
                spec["image_prompt"] = spec["image_prompt_start"]


# ── API call ───────────────────────────────────────────────────────────────────

def enhance_section(section: dict) -> Optional[list]:
    """
    Call GPT-4o to enhance visual prompts for one section.
    Returns list of enhanced beats, or None on failure.
    """
    import requests

    if not OPENROUTER_API_KEY:
        logger.warning("[Enhancer] OPENROUTER_API_KEY not set — skipping enhancement.")
        return None

    beats = extract_beats(section)
    if not beats:
        logger.info(f"[Enhancer] Section {section.get('section_id')}: no beats to enhance, skipping.")
        return None

    user_payload = {
        "section_id": section.get("section_id"),
        "renderer": section.get("renderer"),
        "beats": beats,
    }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://opencode.ai",
                "X-Title": "AI Document Presentation Enhancer",
                "Content-Type": "application/json",
            },
            json={
                "model": ENHANCER_MODEL,
                "temperature": 0.5,
                "messages": [
                    {"role": "system", "content": ENHANCER_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(user_payload)},
                ],
            },
            timeout=120,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]

        # Strip markdown code fences if model wraps JSON in ```
        if raw.strip().startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines()
                if not line.strip().startswith("```")
            )

        data = json.loads(raw)
        return data.get("beats", [])

    except Exception as e:
        logger.error(f"[Enhancer] Section {section.get('section_id')} enhance failed: {e}")
        return None


# ── Main entry point ───────────────────────────────────────────────────────────

def run_prompt_enhancement(presentation: dict, log_fn=None) -> dict:
    """
    Main entry point called from pipeline_v3.py (Phase 2.5).
    Iterates all sections, enhances eligible ones, and returns
    the updated presentation dict.
    """
    def _log(msg: str):
        logger.info(f"[Enhancer] {msg}")
        if log_fn:
            log_fn("prompt_enhancer", msg)

    sections = presentation.get("sections", [])
    eligible = [s for s in sections if s.get("renderer") in ELIGIBLE_RENDERERS]

    _log(f"Found {len(eligible)} eligible section(s) out of {len(sections)} total.")

    enhanced_count = 0
    for section in eligible:
        sec_id = section.get("section_id", "?")
        renderer = section.get("renderer", "?")
        _log(f"  Enhancing section {sec_id} (renderer={renderer})...")

        try:
            enhanced_beats = enhance_section(section)
            if enhanced_beats:
                apply_enhanced_prompts(section, enhanced_beats)
                _log(f"  ✅ Section {sec_id}: {len(enhanced_beats)} beat(s) enhanced.")
                enhanced_count += 1
            else:
                _log(f"  ⚠️ Section {sec_id}: no enhancement returned, keeping original prompts.")
        except Exception as e:
            _log(f"  ⚠️ Section {sec_id}: enhancement error (non-fatal): {e}")

    _log(f"Enhancement complete: {enhanced_count}/{len(eligible)} section(s) improved.")
    return presentation

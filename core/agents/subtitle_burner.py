"""
subtitle_burner.py

Burns karaoke-style word-highlighted subtitles into the final audio-only
presentation video using word-level timings from subtitles.json.

Technique: ASS (Advanced SubStation Alpha) karaoke {\k<cs>} tags.
  - Future words: semi-transparent white (SecondaryColour)
  - Past/active words: bright yellow  (PrimaryColour)
  - Black outline + shadow for readability on any background

Usage:
    from core.agents.subtitle_burner import burn_subtitles
    out = burn_subtitles(
        video_path="videos/presentation_final.mp4",
        subtitles_json_path="subtitles.json",
        presentation=presentation_dict,
        output_path="videos/presentation_final.mp4",  # overwrites in-place
    )
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── ASS styling constants ────────────────────────────────────────────────────
# Colours in ASS &HAABBGGRR format (A=alpha, 00=opaque, FF=fully transparent)
# Yellow = RGB(255,255,0)  → BGR 00FFFF → &H0000FFFF
# White  = RGB(255,255,255)→ BGR FFFFFF → &H80FFFFFF (50 % transparent for future words)
# Black outline
ASS_STYLE = (
    "Style: Default,"
    "Arial,{fontsize},"      # Fontname, Fontsize
    "&H0000FFFF,"            # PrimaryColour   = yellow (active / past words)
    "&H80FFFFFF,"            # SecondaryColour = dim white (future words)
    "&H00000000,"            # OutlineColour   = black
    "&H90000000,"            # BackColour      = dark shadow
    "-1,0,0,0,"              # Bold, Italic, Underline, StrikeOut
    "100,100,0,0,"           # ScaleX, ScaleY, Spacing, Angle
    "1,3,1,"                 # BorderStyle=1, Outline=3px, Shadow=1px
    "2,"                     # Alignment = 2 (bottom-center, numpad layout)
    "20,20,{margin_v},1"     # MarginL, MarginR, MarginV, Encoding
)

MAX_WORDS_PER_LINE = 4       # words before forcing a line break (keep lines short)
PAUSE_BREAK_SECS   = 0.55    # pause longer than this → new subtitle line


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _sec_to_ass(seconds: float) -> str:
    """Convert float seconds → ASS time string  H:MM:SS.cc"""
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    cs = int(round((seconds % 1) * 100))
    if cs >= 100:           # handle rounding edge case
        cs -= 100
        s  += 1
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _build_ass_header(width: int, height: int, fontsize: int, margin_v: int) -> str:
    style = ASS_STYLE.format(fontsize=fontsize, margin_v=margin_v)
    return (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "ScaledBorderAndShadow: yes\n"
        "WrapStyle: 1\n"      # wrap on whole-word boundaries
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"{style}\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )


def _words_to_events(words: List[Dict], section_offset: float) -> List[str]:
    """
    Convert word-level timings (section-relative) to ASS Dialogue events
    with karaoke {\\k<cs>} tags.

    Args:
        words:          [{"word": str, "start": float, "end": float}, ...]
        section_offset: seconds to add to each word's start/end to get
                        its absolute position in the final merged video.
    Returns:
        List of "Dialogue: ..." strings.
    """
    events: List[str] = []
    line:   List[Dict] = []

    for i, w in enumerate(words):
        line.append(w)

        next_w = words[i + 1] if i + 1 < len(words) else None

        # Decide whether to flush the current line
        flush = (
            len(line) >= MAX_WORDS_PER_LINE
            or next_w is None
            or (next_w["start"] - w["end"]) > PAUSE_BREAK_SECS
        )

        if not flush:
            continue

        # ── Build karaoke text ──────────────────────────────────────────
        parts: List[str] = []
        prev_end = line[0]["start"]

        for j, lw in enumerate(line):
            # Inter-word gap: silent karaoke token + guaranteed space
            gap_s = lw["start"] - prev_end
            if j > 0:
                if gap_s > 0.01:
                    gap_cs = max(1, int(round(gap_s * 100)))
                    parts.append(f"{{\\k{gap_cs}}} ")
                else:
                    # Always add a space even when words are adjacent
                    parts.append(" ")

            word_cs = max(1, int(round((lw["end"] - lw["start"]) * 100)))
            parts.append(f"{{\\k{word_cs}}}{lw['word']}")
            prev_end = lw["end"]

        text = "".join(parts)

        abs_start = line[0]["start"] + section_offset
        abs_end   = line[-1]["end"]  + section_offset
        # Guard against zero/negative duration
        if abs_end <= abs_start:
            abs_end = abs_start + 0.5

        events.append(
            f"Dialogue: 0,{_sec_to_ass(abs_start)},{_sec_to_ass(abs_end)},"
            f"Default,,0,0,0,,{text}"
        )
        line = []

    return events




# ─── Public API ───────────────────────────────────────────────────────────────

def burn_subtitles(
    video_path: str,
    subtitles_json_path: str,
    presentation: dict,
    output_path: str,
    target_width: int = 720,
    target_height: int = 1280,
    log_fn=None,
) -> Optional[str]:
    """
    Burn karaoke word-highlighted subtitles into an audio-only video.

    Args:
        video_path:           Path to presentation_final.mp4 (input).
        subtitles_json_path:  Path to subtitles.json.
        presentation:         Parsed presentation.json dict (for section offsets).
        output_path:          Where to save the result (can equal video_path → in-place).
        target_width/height:  Video resolution (for ASS PlayRes).
        log_fn:               Optional log(tag, message) callback.

    Returns:
        output_path on success, None on failure.
    """

    def _log(msg: str):
        if log_fn:
            log_fn("subtitle_burn", msg)
        logger.info(f"[SUBTITLE] {msg}")

    # ── Validate inputs ────────────────────────────────────────────────
    if not Path(video_path).exists():
        _log(f"Input video not found: {video_path}")
        return None

    if not Path(subtitles_json_path).exists():
        _log(f"subtitles.json not found: {subtitles_json_path} — skipping")
        return None

    with open(subtitles_json_path, "r", encoding="utf-8") as f:
        subs_data = json.load(f)

    sections_subs: Dict[str, Dict] = subs_data.get("sections", {})
    if not sections_subs:
        _log("subtitles.json has no sections — skipping")
        return None

    # ── Compute cumulative section offsets ────────────────────────────
    sections = presentation.get("sections", [])
    cumulative = 0.0
    section_offsets: Dict[str, float] = {}
    for sec in sections:
        sid = str(sec.get("section_id", ""))
        section_offsets[sid] = cumulative
        cumulative += sec.get("audio_duration_seconds", 0.0)

    # ── Build all ASS events ───────────────────────────────────────────
    all_events: List[str] = []
    for sid, sec_subs in sections_subs.items():
        words = sec_subs.get("words", [])
        if not words:
            continue
        offset = section_offsets.get(sid, 0.0)
        all_events.extend(_words_to_events(words, offset))

    if not all_events:
        _log("No subtitle events generated — skipping burn")
        return None

    _log(f"Generated {len(all_events)} subtitle events across {len(sections_subs)} sections")

    # Font size & margin scaled to resolution — keep readable but not huge
    fontsize = max(28, int(target_width * 34 / 720))   # ~34pt at 720px wide
    margin_v = max(30, int(target_height * 50 / 1280))  # ~50px from bottom at 1280px

    # ── Write .ass file ────────────────────────────────────────────────
    ass_path = Path(video_path).parent.parent / "subtitles_burn.ass"
    ass_content = (
        _build_ass_header(target_width, target_height, fontsize, margin_v)
        + "\n".join(all_events)
        + "\n"
    )
    with open(str(ass_path), "w", encoding="utf-8") as f:
        f.write(ass_content)
    _log(f"ASS file written: {ass_path}")

    # ── FFmpeg burn ────────────────────────────────────────────────────
    tmp_out = str(Path(output_path).with_suffix(".subtitled.mp4"))

    # Escape the ass path (FFmpeg vf needs special handling on Linux)
    ass_str = str(ass_path).replace("\\", "/")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"ass={ass_str}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "copy",
        tmp_out,
    ]

    _log("Running FFmpeg subtitle burn (this may take ~30s)...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)

    if result.returncode != 0:
        _log(f"FFmpeg subtitle burn FAILED:\n{result.stderr[-1000:]}")
        # Clean up temp file
        try:
            Path(tmp_out).unlink(missing_ok=True)
        except Exception:
            pass
        return None

    # Atomic replace: temp → final
    os.replace(tmp_out, output_path)
    _log(f"✅ Subtitles burned → {output_path}")
    return output_path

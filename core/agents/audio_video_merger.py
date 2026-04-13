"""
Audio-Video Merger — Phase 7 of the V3 Audio-Only Pipeline
============================================================

Merges EVERY section's visual beats (Manim / WAN / LTX / Local-GPU)
with EVERY section's HeyGem TTS audio into ONE single final MP4 for
the whole presentation: `videos/presentation_final.mp4`.

Steps:
  1. Walk sections IN ORDER, collect video beats and audio WAV per section.
  2. For each section: pad/fit video length to match audio length, or just
     concatenate video beats as-is, then append the audio segment.
  3. Concatenate all silent video segments → temp_video_all.mp4  (no re-encode)
  4. Concatenate all audio segments        → temp_audio_all.wav  (sox / ffmpeg)
  5. Mux combined video + combined audio   → videos/presentation_final.mp4
  6. Patch presentation.json with `final_video_path`.

Renderer support:
  - manim          → beat_video_paths / manim_video_paths
  - image_to_video / text_to_video (WAN / LTX / Local GPU)
                   → beat_video_paths / video_path / narration[].video_path
  - infographic / image / none → no video; section skipped from video track
                                 (audio still concatenated if present)
"""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from core.locks import presentation_lock

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal path helpers
# ---------------------------------------------------------------------------

def _resolve_path(rel_or_abs: str, output_dir: str) -> Optional[str]:
    """Resolve a video/audio path that may be absolute (/app/...) or relative."""
    if not rel_or_abs:
        return None
    p = Path(rel_or_abs)
    if p.is_absolute():
        if p.exists():
            return str(p)
        # Docker /app/... remap: find the sub-path after jobs/<job_id>/
        try:
            parts = p.parts
            job_idx = None
            for i, part in enumerate(parts):
                if part == "jobs" and i + 2 < len(parts):
                    job_idx = i + 2
                    break
            if job_idx is not None:
                rel = "/".join(parts[job_idx:])
                candidate = Path(output_dir) / rel
                if candidate.exists():
                    return str(candidate)
        except Exception:
            pass
        return None
    candidate = Path(output_dir) / rel_or_abs
    return str(candidate) if candidate.exists() else None


def _collect_section_video_paths(section: Dict[str, Any], output_dir: str) -> List[str]:
    """
    Return ordered video beat paths for one section.
    Returns empty list for sections with no visual video (infographic/image/none).
    """
    renderer = (
        section.get("renderer")
        or section.get("render_spec", {}).get("renderer")
        or "none"
    )
    if renderer in ("none", "infographic", "image"):
        return []

    resolved: List[str] = []

    def _add(raw: str):
        p = _resolve_path(raw, output_dir)
        if p and p not in resolved:
            resolved.append(p)

    # 1. beat_video_paths[]  (most complete — covers Manim multi-beat + WAN multi-beat)
    for item in section.get("beat_video_paths", []):
        if isinstance(item, str):
            _add(item)
    if resolved:
        return resolved

    # 2. manim_video_paths[]
    for item in section.get("manim_video_paths", []):
        if isinstance(item, str):
            _add(item)
    if resolved:
        return resolved

    # 3. narration.segments[].video_path  (ordered per narration segment)
    for seg in section.get("narration", {}).get("segments", []):
        vp = seg.get("video_path", "")
        if vp:
            _add(vp)
    if resolved:
        return resolved

    # 4. Fallback: single video_path on the section
    single = section.get("video_path", "")
    if single:
        _add(single)

    return resolved


def _get_video_duration(path: str) -> float:
    """Return video duration via ffprobe, or 0.0 on failure."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return float(r.stdout.strip())
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# FFmpeg primitives
# ---------------------------------------------------------------------------

def _write_filelist(paths: List[str], tmp: str) -> str:
    """Write an ffmpeg concat filelist and return its path."""
    flist = os.path.join(tmp, "filelist.txt")
    with open(flist, "w", encoding="utf-8") as f:
        for p in paths:
            escaped = p.replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")
    return flist


def _ffmpeg_concat_video(
    paths: List[str],
    output: str,
    target_width: int = 480,
    target_height: int = 854,
    fps: int = 30,
) -> bool:
    """
    Concatenate MP4 files with resolution normalization via filter_complex.
    All inputs are scaled to target_width×target_height (default 480×854, 9:16)
    and padded with black bars if the aspect ratio differs.
    This avoids silent corruption when Manim (480×864) and GPU recap (480×832)
    videos have different heights.
    """
    n = len(paths)
    if n == 0:
        return False

    # Build inputs
    input_args = []
    for p in paths:
        input_args += ["-i", p]

    # Build filter: scale+setsar each stream, then concat
    filter_parts = []
    for i in range(n):
        # Scale to target size, pad if needed, force fps
        filter_parts.append(
            f"[{i}:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,"
            f"fps={fps},setsar=1[v{i}]"
        )

    stream_labels = "".join(f"[v{i}]" for i in range(n))
    filter_parts.append(f"{stream_labels}concat=n={n}:v=1:a=0[vout]")
    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        output,
    ]
    logger.debug(f"[MERGE] concat cmd: ffmpeg ... -filter_complex '...' {output}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        logger.error(f"[MERGE] video concat failed:\n{r.stderr[-1200:]}")
        return False
    return True


def _ffmpeg_concat_audio(paths: List[str], output: str) -> bool:
    """
    Concatenate WAV/MP3 audio segments into one WAV using ffmpeg filter_complex.
    Re-encodes to a consistent PCM-16 WAV to avoid format mismatches.
    """
    inputs = []
    for p in paths:
        inputs += ["-i", p]

    n = len(paths)
    filter_chain = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[outa]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_chain,
        "-map", "[outa]",
        "-c:a", "pcm_s16le",
        output,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        logger.error(f"[MERGE] audio concat failed:\n{r.stderr[-800:]}")
        return False
    return True


def _ffmpeg_mux(video: str, audio: str, output: str) -> bool:
    """Mux video + audio into final MP4 (copy video, encode audio as AAC)."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video,
        "-i", audio,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        output,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        logger.error(f"[MERGE] mux failed:\n{r.stderr[-800:]}")
        return False
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def merge_section_videos(
    presentation: Dict[str, Any],
    output_dir: str,
    log_fn=None,
) -> Optional[str]:
    """
    Combine ALL section beat videos + ALL section HeyGem audio into ONE
    final presentation MP4: `videos/presentation_final.mp4`.

    Args:
        presentation:  Loaded presentation.json dict.
        output_dir:    Absolute path to the job directory.
        log_fn:        Optional callable(tag, message) for pipeline logging.

    Returns:
        Relative path to the final video ("videos/presentation_final.mp4"),
        or None if merge failed.
    """

    def _log(tag: str, msg: str):
        logger.info(f"[MERGE] {msg}")
        if log_fn:
            try:
                log_fn(tag, msg)
            except Exception:
                pass

    output_dir = str(output_dir)
    videos_dir = Path(output_dir) / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    final_name = "presentation_final.mp4"
    final_path = str(videos_dir / final_name)
    final_rel  = f"videos/{final_name}"

    sections = presentation.get("sections", [])
    all_video_paths: List[str] = []
    all_audio_paths: List[str] = []

    for section in sections:
        sec_id = section.get("section_id", "?")

        # ── Video beats ───────────────────────────────────────────────────
        beat_videos = _collect_section_video_paths(section, output_dir)
        if beat_videos:
            _log("merge", f"  Sec {sec_id}: {len(beat_videos)} video beat(s) → adding to timeline")
            all_video_paths.extend(beat_videos)
        else:
            _log("merge", f"  Sec {sec_id}: no video beats (renderer={section.get('renderer','none')})")

        # ── Audio ─────────────────────────────────────────────────────────
        audio_rel = section.get("audio_path", "")
        audio_abs = _resolve_path(audio_rel, output_dir) if audio_rel else None
        if audio_abs:
            _log("merge", f"  Sec {sec_id}: audio → {os.path.basename(audio_abs)}")
            all_audio_paths.append(audio_abs)
        else:
            _log("merge", f"  Sec {sec_id}: no audio_path found, skipping audio for this section")

    if not all_audio_paths:
        _log("merge", "❌ No audio segments found — cannot produce final video.")
        return None

    if not all_video_paths:
        _log("merge", "❌ No video segments found — cannot produce final video.")
        return None

    _log("merge", f"Total: {len(all_video_paths)} video beat(s), {len(all_audio_paths)} audio segment(s)")

    with tempfile.TemporaryDirectory() as tmp:
        # Step 1: Concat all video beats → one silent video
        if len(all_video_paths) == 1:
            combined_video = all_video_paths[0]
            _log("merge", "Single video beat — skipping concat.")
        else:
            combined_video = os.path.join(tmp, "combined_video.mp4")
            _log("merge", f"Concatenating {len(all_video_paths)} video beats...")
            if not _ffmpeg_concat_video(all_video_paths, combined_video):
                _log("merge", "❌ Video concat failed.")
                return None
            _log("merge", "✅ Video concat done.")

        # Step 2: Concat all audio segments → one WAV
        if len(all_audio_paths) == 1:
            combined_audio = all_audio_paths[0]
            _log("merge", "Single audio segment — skipping concat.")
        else:
            combined_audio = os.path.join(tmp, "combined_audio.wav")
            _log("merge", f"Concatenating {len(all_audio_paths)} audio segments...")
            if not _ffmpeg_concat_audio(all_audio_paths, combined_audio):
                _log("merge", "❌ Audio concat failed.")
                return None
            _log("merge", "✅ Audio concat done.")

        # Step 3: Mux video + audio → final MP4
        _log("merge", f"Muxing into {final_name}...")
        if not _ffmpeg_mux(combined_video, combined_audio, final_path):
            _log("merge", "❌ Final mux failed.")
            return None

    size_mb = os.path.getsize(final_path) / (1024 * 1024)
    _log("merge", f"✅ Final video → {final_rel} ({size_mb:.1f} MB)")

    # Patch presentation.json
    try:
        pres_path = Path(output_dir) / "presentation.json"
        with presentation_lock:
            with open(pres_path, "r", encoding="utf-8") as f:
                pres_data = json.load(f)
            pres_data["final_video_path"] = final_rel
            with open(pres_path, "w", encoding="utf-8") as f:
                json.dump(pres_data, f, indent=2, ensure_ascii=False)
        _log("merge", "✅ presentation.json patched with final_video_path.")
    except Exception as e:
        _log("merge", f"⚠️ Could not patch presentation.json: {e}")

    # Also mutate the in-memory dict the pipeline holds
    presentation["final_video_path"] = final_rel

    return final_rel

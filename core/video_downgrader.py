"""
core/video_downgrader.py
Phase 7: Downgrade all job videos to 360p after pipeline completion.

Strategy (per file):
  1. Check current height via ffprobe — skip if already ≤ 360p
  2. ffmpeg encode → <name>_tmp360.mp4
  3. Success: delete original, rename tmp → original filename
  4. Failure: delete tmp, keep original untouched
"""

import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_video_height(filepath: str) -> int:
    """Return video height in pixels using ffprobe. Returns 0 on failure."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=height",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip())
    except Exception as e:
        logger.warning(f"[DOWNGRADE] ffprobe failed for {filepath}: {e}")
    return 0


def downgrade_videos_to_360p(videos_dir: str, log_fn=None) -> int:
    """
    Re-encode all .mp4 files in videos_dir to 360p in-place.

    - Only processes files with height > 360.
    - Atomic: encodes to a temp file first, then replaces original.
    - Original high-res file is DELETED after successful conversion.
    - Non-fatal: individual file failures are logged and skipped.

    Returns count of files successfully downgraded.
    """

    def _log(msg: str):
        if log_fn:
            log_fn("video_downgrade", msg)
        else:
            logger.info(f"[DOWNGRADE] {msg}")

    videos_path = Path(videos_dir)
    if not videos_path.is_dir():
        _log(f"⚠️ videos dir does not exist: {videos_dir}")
        return 0

    # Check ffmpeg is available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=10, check=True)
    except Exception:
        _log("⚠️ ffmpeg not found — skipping 360p downgrade.")
        return 0

    mp4_files = sorted(videos_path.glob("*.mp4"))
    _log(f"Found {len(mp4_files)} .mp4 file(s) in {videos_dir}")

    converted = 0
    skipped = 0
    failed = 0

    for mp4 in mp4_files:
        filepath = str(mp4)
        tmp_path = str(mp4.with_suffix("")) + "_tmp360.mp4"

        # Clean up any leftover tmp files from previous interrupted runs
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        # Check current height — skip if already ≤ 360p
        height = _get_video_height(filepath)
        if height == 0:
            _log(f"  ⚠️ Could not read height for {mp4.name} — skipping.")
            skipped += 1
            continue
        if height <= 360:
            _log(f"  ↪ {mp4.name} already {height}p — skipping.")
            skipped += 1
            continue

        _log(f"  🔄 {mp4.name} ({height}p) → encoding to 360p...")

        # Encode to tmp file
        cmd = [
            "ffmpeg",
            "-i", filepath,
            "-vf", "scale=-2:360",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "copy",
            "-y",
            tmp_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,   # 10 min max per file
            )

            if result.returncode != 0:
                _log(
                    f"  ❌ {mp4.name}: ffmpeg failed (code {result.returncode}): "
                    f"{result.stderr[-300:].strip()}"
                )
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                failed += 1
                continue

            # Verify tmp file exists and has non-zero size
            if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                _log(f"  ❌ {mp4.name}: ffmpeg produced empty or missing output.")
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                failed += 1
                continue

            # Delete original, then rename tmp → original name
            os.remove(filepath)
            os.rename(tmp_path, filepath)

            converted += 1
            _log(f"  ✅ {mp4.name}: converted to 360p, original deleted.")

        except subprocess.TimeoutExpired:
            _log(f"  ❌ {mp4.name}: ffmpeg timed out after 600s.")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            failed += 1
        except Exception as e:
            _log(f"  ❌ {mp4.name}: unexpected error — {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            failed += 1

    _log(
        f"360p downgrade summary: {converted} converted, "
        f"{skipped} already ≤360p/skipped, {failed} failed."
    )
    return converted

"""
subtitle_aligner.py
====================
Post-job step: reads presentation.json, extracts/uses audio for each section,
runs faster-whisper word-level transcription, and writes subtitles.json.

Usage (CLI):
    python3 -m core.agents.subtitle_aligner <job_dir>

Usage (Python):
    aligner = SubtitleAligner()
    aligner.align_job("player/jobs/45_123_216_62_7ce71676")
"""

import os
import sys
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model singleton (lazy-loaded on first use)
# ---------------------------------------------------------------------------
_model = None

def _get_model(model_size: str = "base"):
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        device = "cuda" if _cuda_available() else "cpu"
        compute = "float16" if device == "cuda" else "int8"
        logger.info(f"[SUBTITLE] Loading faster-whisper '{model_size}' on {device}/{compute}")
        _model = WhisperModel(model_size, device=device, compute_type=compute)
    return _model


def _cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _extract_audio_from_video(video_path: str, tmp_dir: str) -> Optional[str]:
    """Extract audio track from mp4 → wav using ffmpeg."""
    out_path = os.path.join(tmp_dir, Path(video_path).stem + "_extracted.wav")
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        out_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and os.path.exists(out_path):
            return out_path
        logger.error(f"[SUBTITLE] ffmpeg failed: {result.stderr[:200]}")
    except Exception as e:
        logger.error(f"[SUBTITLE] Audio extraction failed: {e}")
    return None


def _transcribe_words(audio_path: str, language: str = "en") -> list:
    """
    Run faster-whisper on audio_path with word_timestamps=True.
    Returns list of {word, start, end} dicts.
    """
    model = _get_model()
    segments, _info = model.transcribe(
        audio_path,
        word_timestamps=True,
        language=language[:2] if language else "en",
        beam_size=1,           # fast
        vad_filter=True,       # skip silence
    )
    words = []
    for seg in segments:
        for w in seg.words:
            words.append({
                "word":  w.word.strip(),
                "start": round(w.start, 3),
                "end":   round(w.end, 3),
            })
    return words


def _language_code(language: Optional[str]) -> str:
    """Convert our language label to ISO-639-1 code for Whisper."""
    mapping = {
        "english": "en", "hindi": "hi", "kannada": "kn",
        "tamil": "ta", "telugu": "te", "bengali": "bn",
        "malayalam": "ml", "marathi": "mr", "gujarati": "gu",
        "punjabi": "pa", "odia": "or", "assamese": "as",
    }
    return mapping.get((language or "english").lower(), "en")


# ---------------------------------------------------------------------------
# Main aligner class
# ---------------------------------------------------------------------------

class SubtitleAligner:

    def align_job(self, job_dir: str) -> dict:
        """
        Process all sections in a job and write subtitles.json.

        Returns summary dict: {sections_aligned, sections_skipped, sections_failed}
        """
        job_path = Path(job_dir)
        pres_path = job_path / "presentation.json"

        if not pres_path.exists():
            raise FileNotFoundError(f"presentation.json not found: {pres_path}")

        with open(pres_path, "r", encoding="utf-8") as f:
            presentation = json.load(f)

        sections = presentation.get("sections", [])
        global_language = presentation.get("metadata", {}).get("language", "english")

        summary = {"sections_aligned": [], "sections_skipped": [], "sections_failed": []}
        result: dict = {"version": 1, "sections": {}}

        with tempfile.TemporaryDirectory() as tmp_dir:
            for section in sections:
                sec_id = str(section.get("section_id", ""))
                try:
                    sec_result = self._align_section(
                        section, job_path, tmp_dir, global_language
                    )
                    if sec_result is None:
                        summary["sections_skipped"].append(sec_id)
                        continue
                    result["sections"][sec_id] = sec_result
                    summary["sections_aligned"].append(sec_id)
                    logger.info(f"[SUBTITLE] ✅ Sec {sec_id} aligned")
                except Exception as e:
                    logger.error(f"[SUBTITLE] ❌ Sec {sec_id} failed: {e}")
                    summary["sections_failed"].append(sec_id)

        # Write subtitles.json
        out_path = job_path / "subtitles.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        print(
            f"[SUBTITLE] Done → {out_path}\n"
            f"  aligned={len(summary['sections_aligned'])} "
            f"skipped={len(summary['sections_skipped'])} "
            f"failed={len(summary['sections_failed'])}"
        )
        return summary

    # ------------------------------------------------------------------

    def _align_section(
        self, section: dict, job_path: Path, tmp_dir: str, global_language: str
    ) -> Optional[dict]:
        """
        Align one section — returns the subtitle data dict or None if skipped.
        """
        language = section.get("language") or global_language
        lang_code = _language_code(language)
        sec_id = section.get("section_id", "?")

        # Resolve the audio source
        audio_path = self._resolve_audio(section, job_path, tmp_dir)
        if audio_path is None:
            logger.info(f"[SUBTITLE] Sec {sec_id}: no audio source, skipping")
            return None

        # Transcribe main narration
        logger.info(f"[SUBTITLE] Transcribing Sec {sec_id} from {Path(audio_path).name}")
        words = _transcribe_words(audio_path, lang_code)

        # Convert words to segment-aware structure
        # We keep a flat word list per section (simplest to consume in frontend)
        sec_result: dict = {
            "source": "audio" if section.get("audio_path") else "video",
            "words": words,          # flat list for main narration
            "segments": [],          # per-segment breakdown
            "questions": [],
        }

        # Build per-segment timing (map flat words back to segment time ranges)
        segs = section.get("narration", {}).get("segments", [])
        for idx, seg in enumerate(segs):
            seg_start = seg.get("start_seconds", 0)
            seg_end = seg.get("end_seconds", seg_start + seg.get("duration_seconds", seg.get("duration", 5)))
            seg_words = [w for w in words if w["start"] >= seg_start - 0.05 and w["end"] <= seg_end + 0.05]
            sec_result["segments"].append({"idx": idx, "words": seg_words})

        # Align quiz phase audio clips
        questions = section.get("questions", [])
        if not questions and section.get("understanding_quiz"):
            questions = [section["understanding_quiz"]]

        for q_idx, q in enumerate(questions):
            q_entry: dict = {"q_idx": q_idx}
            audio_clips  = q.get("audio_clips")  or {}  # wav files  (audio-only jobs)
            avatar_clips = q.get("avatar_clips") or {}  # mp4 files  (avatar-video jobs)

            for phase in ("question", "correct", "wrong", "explanation"):
                clip_audio_path: Optional[str] = None

                # Priority 1: direct wav (audio-only mode)
                clip_rel = audio_clips.get(phase)
                if clip_rel:
                    p = job_path / clip_rel
                    if p.exists():
                        clip_audio_path = str(p)
                    else:
                        logger.warning(f"[SUBTITLE] Quiz audio clip missing: {p}")

                # Priority 2: avatar mp4 → extract audio (avatar-video mode)
                if clip_audio_path is None:
                    avatar_rel = avatar_clips.get(phase)
                    if avatar_rel:
                        p = job_path / avatar_rel
                        if p.exists():
                            clip_audio_path = _extract_audio_from_video(str(p), tmp_dir)
                        else:
                            logger.warning(f"[SUBTITLE] Quiz avatar clip missing: {p}")

                if clip_audio_path is None:
                    continue

                try:
                    phase_words = _transcribe_words(clip_audio_path, lang_code)
                    q_entry[phase] = {"words": phase_words}
                except Exception as e:
                    logger.error(f"[SUBTITLE] Quiz Sec {sec_id} Q{q_idx} {phase}: {e}")

            if len(q_entry) > 1:  # has at least one phase
                sec_result["questions"].append(q_entry)


        return sec_result

    # ------------------------------------------------------------------

    def _resolve_audio(
        self, section: dict, job_path: Path, tmp_dir: str
    ) -> Optional[str]:
        """
        Return an absolute path to a wav file for this section.
        Priority: audio_path (wav) > avatar_video (extract audio from mp4)
        """
        # 1. Audio-only mode: direct wav
        audio_rel = section.get("audio_path")
        if audio_rel:
            p = job_path / audio_rel
            if p.exists():
                return str(p)

        # 2. Avatar video: extract audio track
        video_rel = section.get("avatar_video")
        if video_rel:
            p = job_path / video_rel
            if p.exists():
                return _extract_audio_from_video(str(p), tmp_dir)

        return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if len(sys.argv) < 2:
        print("Usage: python3 -m core.agents.subtitle_aligner <job_dir>")
        sys.exit(1)
    aligner = SubtitleAligner()
    aligner.align_job(sys.argv[1])

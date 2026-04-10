import os
import time
import requests
import logging
import json
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.latex_to_speech import latex_to_speech
from core.locks import presentation_lock, analytics_lock

logger = logging.getLogger(__name__)

# Sarvam-supported languages (must match HeyGem webapp_chatterbox)
SARVAM_LANGUAGES = {
    'kannada', 'hindi', 'bengali', 'tamil', 'telugu',
    'malayalam', 'marathi', 'gujarati', 'punjabi', 'odia', 'assamese'
}

# Valid Sarvam speaker IDs
SARVAM_SPEAKERS = {
    'abhilash', 'karun', 'hitesh',        # Male
    'anushka', 'manisha', 'vidya', 'arya'  # Female
}


class AudioOnlyGenerator:
    """
    Generates per-section TTS audio using HeyGem's /api/generate-audio endpoint.

    - English  → Chatterbox (GPU voice clone, reference audio on server)
    - Indian langs → IndicTrans2 translation + Sarvam.ai bulbul:v2

    Mirrors avatar_generator.py's patterns:
      - Batches of 3 sections processed in parallel
      - Live-patches presentation.json after each section (thread-safe)
      - Stores audio under {output_dir}/audio/[language/]section_{id}.wav
    """

    BATCH_SIZE = 3

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = (api_url or os.environ.get("AVATAR_API_URL", "")).rstrip("/")
        if not self.api_url:
            raise ValueError("AVATAR_API_URL environment variable is not set")
        self.audio_endpoint = f"{self.api_url}/generate-audio"
        logger.info(f"[AUDIO-ONLY] Audio endpoint: {self.audio_endpoint}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_narration_text(self, section: Dict[str, Any]) -> str:
        """Extract combined narration text from a section (same logic as avatar_generator)."""
        if "narration_segments" in section:
            return " ".join(
                str(seg.get("text", "") or "")
                for seg in section["narration_segments"]
            )
        narr = section.get("narration", {})
        if isinstance(narr, dict):
            text = narr.get("full_text", "")
            if not text:
                text = " ".join(
                    str(s.get("text", "") or "")
                    for s in narr.get("segments", [])
                )
            return text
        return str(narr or "")

    def _get_audio_duration(self, audio_path: str) -> float:
        """Use ffprobe to get audio duration in seconds."""
        try:
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"[AUDIO-ONLY] ffprobe failed for {audio_path}: {e}")
            return 0.0

    def _call_generate_audio(
        self,
        text: str,
        language: str,
        speaker: str,
        section_id: int
    ) -> bytes:
        """
        POST to /api/generate-audio.
        Returns raw WAV bytes on success.
        Raises on failure.
        """
        clean_text = latex_to_speech(text)

        lang = language.lower() if language else "english"
        spkr = speaker.lower() if speaker else "abhilash"

        if lang in SARVAM_LANGUAGES and spkr not in SARVAM_SPEAKERS:
            logger.warning(
                f"[AUDIO-ONLY] Unknown Sarvam speaker '{spkr}', defaulting to 'abhilash'"
            )
            spkr = "abhilash"

        payload = {
            "text": clean_text,
            "language": lang,
            "speaker": spkr,
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"[AUDIO-ONLY] POST {self.audio_endpoint} | "
                    f"Sec {section_id} | lang={lang} | speaker={spkr} | "
                    f"attempt {attempt + 1}/{max_retries}"
                )
                resp = requests.post(
                    self.audio_endpoint,
                    data=payload,
                    timeout=300
                )
                if resp.status_code == 200:
                    content_type = resp.headers.get("Content-Type", "")
                    if "audio" not in content_type and len(resp.content) < 1000:
                        raise RuntimeError(
                            f"Response looks like an error, not audio: {resp.text[:200]}"
                        )
                    logger.info(
                        f"[AUDIO-ONLY] Sec {section_id} audio received "
                        f"({len(resp.content):,} bytes)"
                    )
                    return resp.content
                else:
                    err = resp.text[:200]
                    logger.error(
                        f"[AUDIO-ONLY] HTTP {resp.status_code} for Sec {section_id}: {err}"
                    )
                    if resp.status_code < 500:
                        raise RuntimeError(f"Client error {resp.status_code}: {err}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"[AUDIO-ONLY] Network error (attempt {attempt + 1}): {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

        raise RuntimeError(
            f"[AUDIO-ONLY] Max retries exceeded for Sec {section_id}"
        )

    def _update_artifacts(
        self,
        output_dir: str,
        section_id: int,
        audio_path: str,
        duration: float,
        language: Optional[str] = None,
        speaker: Optional[str] = None,
    ):
        """
        Live-patch presentation.json with audio_path + audio_duration_seconds.
        Thread-safe — uses the same presentation_lock as avatar_generator.
        """
        try:
            pres_path = Path(output_dir) / "presentation.json"
            if not pres_path.exists():
                logger.warning("[AUDIO-ONLY] presentation.json not found, skipping patch")
                return

            with presentation_lock:
                with open(pres_path, 'r', encoding='utf-8') as f:
                    pres_data = json.load(f)

                updated = False
                for section in pres_data.get("sections", []):
                    if str(section.get("section_id")) == str(section_id):
                        audio_filename = os.path.basename(audio_path)

                        if language and language.lower() != "english":
                            if "audio_languages" not in section:
                                section["audio_languages"] = []

                            rel_path = f"audio/{language}/{audio_filename}"
                            lang_entry = None
                            for entry in section["audio_languages"]:
                                if entry.get("language") == language:
                                    lang_entry = entry
                                    break

                            if lang_entry:
                                lang_entry["audio_path"] = rel_path
                                lang_entry["audio_duration_seconds"] = round(duration, 2)
                                lang_entry["status"] = "completed"
                            else:
                                lang_entry = {
                                    "language": language,
                                    "audio_path": rel_path,
                                    "audio_duration_seconds": round(duration, 2),
                                    "status": "completed",
                                }
                                if speaker:
                                    lang_entry["speaker"] = speaker
                                section["audio_languages"].append(lang_entry)

                            if duration > 0:
                                section["audio_duration_seconds"] = round(duration, 2)

                        else:
                            section["audio_path"] = f"audio/{audio_filename}"
                            section["audio_duration_seconds"] = round(duration, 2)
                            section["audio_only"] = True  # player flag

                        logger.info(
                            f"[AUDIO-ONLY] Updated presentation.json "
                            f"Sec {section_id} [{language or 'english'}] "
                            f"dur={duration:.2f}s"
                        )
                        updated = True
                        break

                if updated:
                    with open(pres_path, 'w', encoding='utf-8') as f:
                        json.dump(pres_data, f, indent=2)

        except Exception as e:
            logger.error(f"[AUDIO-ONLY] _update_artifacts failed for Sec {section_id}: {e}")

    def _generate_quiz_audio(
        self,
        section: Dict[str, Any],
        audio_dir: Path,
        language: Optional[str] = None,
        speaker: Optional[str] = None,
    ) -> Dict[int, Dict[str, str]]:
        """
        Generate TTS wav files for each quiz question phase (question/correct/wrong/explanation).
        Returns {q_idx: {phase: rel_path}} for all generated clips.
        Audio files saved to {audio_dir}/quiz/sec_{sec_id}_q{idx}_{phase}.wav
        """
        questions = []
        if section.get("questions"):
            questions = list(section["questions"])
        elif section.get("understanding_quiz"):
            questions = [section["understanding_quiz"]]
        if not questions:
            return {}

        quiz_dir = audio_dir / "quiz"
        quiz_dir.mkdir(parents=True, exist_ok=True)

        sec_id = section.get("section_id", "unknown")
        lang_label = (language or "english").lower()
        results: Dict[int, Dict[str, str]] = {}

        PHASES = {
            "question":    "question_script",
            "correct":     "correct_script",
            "wrong":       "wrong_script",
            "explanation": "explanation_script",
        }

        for q_idx, q in enumerate(questions):
            narration = q.get("narration") or {}
            clips: Dict[str, str] = {}

            for phase, script_key in PHASES.items():
                text = (narration.get(script_key) or "").strip()
                if not text:
                    continue

                fname = f"sec_{sec_id}_q{q_idx}_{phase}.wav"
                wav_path = quiz_dir / fname

                # Re-use existing file if valid
                if wav_path.exists() and wav_path.stat().st_size > 500:
                    rel = f"audio/quiz/{fname}" if lang_label == "english" else f"audio/{lang_label}/quiz/{fname}"
                    clips[phase] = rel
                    logger.info(f"[AUDIO-ONLY] Quiz clip exists, skip: {fname}")
                    continue

                try:
                    wav_bytes = self._call_generate_audio(
                        text, language or "english", speaker or "abhilash", sec_id
                    )
                    with open(wav_path, "wb") as f:
                        f.write(wav_bytes)
                    rel = f"audio/quiz/{fname}" if lang_label == "english" else f"audio/{lang_label}/quiz/{fname}"
                    clips[phase] = rel
                    logger.info(f"[AUDIO-ONLY] ✅ Quiz Sec {sec_id} Q{q_idx} {phase} ({len(wav_bytes):,}B)")
                except Exception as e:
                    logger.error(f"[AUDIO-ONLY] ❌ Quiz Sec {sec_id} Q{q_idx} {phase}: {e}")

            if clips:
                results[q_idx] = clips

        return results

    def _update_quiz_artifacts(
        self,
        output_dir: str,
        section_id,
        quiz_audio_map: Dict[int, Dict[str, str]],
    ):
        """Patch audio_clips into each question in presentation.json. Thread-safe."""
        if not quiz_audio_map:
            return
        try:
            pres_path = Path(output_dir) / "presentation.json"
            if not pres_path.exists():
                return
            with presentation_lock:
                with open(pres_path, "r", encoding="utf-8") as f:
                    pres_data = json.load(f)

                for section in pres_data.get("sections", []):
                    if str(section.get("section_id")) != str(section_id):
                        continue
                    qs = section.get("questions", [])
                    if not qs and section.get("understanding_quiz"):
                        qs = [section["understanding_quiz"]]
                    for q_idx, clips in quiz_audio_map.items():
                        if q_idx < len(qs):
                            qs[q_idx]["audio_clips"] = clips
                            logger.info(f"[AUDIO-ONLY] Patched audio_clips Sec {section_id} Q{q_idx}")
                    break

                with open(pres_path, "w", encoding="utf-8") as f:
                    json.dump(pres_data, f, indent=2)
        except Exception as e:
            logger.error(f"[AUDIO-ONLY] _update_quiz_artifacts failed Sec {section_id}: {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_all(
        self,
        presentation: Dict[str, Any],
        job_id: str,
        output_dir: str,
        language: Optional[str] = None,
        speaker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate TTS audio for all sections in parallel batches of 3.
        Also generates quiz phase audio (question/correct/wrong/explanation) for
        sections that contain embedded quizzes.

        Args:
            presentation: Loaded presentation.json dict.
            job_id:       Job identifier (for logging).
            output_dir:   Absolute path to job output directory (contains presentation.json).
            language:     Target language or None / 'english' for default.
            speaker:      Sarvam speaker ID (ignored for English). Default: 'abhilash'.

        Returns:
            Dict with keys: completed, failed, skipped (list of section IDs).
        """
        sections = presentation.get("sections", [])
        if not sections:
            logger.warning("[AUDIO-ONLY] No sections found in presentation.")
            return {"completed": [], "failed": [], "skipped": []}

        lang_label = (language or "english").lower()
        if lang_label == "english":
            audio_dir = Path(output_dir) / "audio"
        else:
            audio_dir = Path(output_dir) / "audio" / lang_label

        audio_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"[AUDIO-ONLY] Job {job_id} | {len(sections)} sections | "
            f"lang={lang_label} | speaker={speaker or 'abhilash'} | "
            f"output={audio_dir}"
        )

        results = {"completed": [], "failed": [], "skipped": []}

        def _process_section(section: Dict[str, Any]) -> Dict[str, Any]:
            sec_id = section.get("section_id")
            audio_filename = f"section_{sec_id}.wav"
            audio_path = audio_dir / audio_filename

            # Skip if already generated
            if audio_path.exists() and audio_path.stat().st_size > 1000:
                logger.info(f"[AUDIO-ONLY] Sec {sec_id} audio exists, skipping.")
                return {"status": "skipped", "section_id": sec_id}

            # Collect text
            text = self._collect_narration_text(section)
            if not text.strip():
                logger.warning(f"[AUDIO-ONLY] Sec {sec_id} has empty narration, skipping.")
                return {"status": "skipped", "section_id": sec_id, "reason": "empty_text"}

            try:
                wav_bytes = self._call_generate_audio(
                    text, language or "english", speaker or "abhilash", sec_id
                )

                with open(audio_path, 'wb') as f:
                    f.write(wav_bytes)

                duration = self._get_audio_duration(str(audio_path))
                logger.info(
                    f"[AUDIO-ONLY] ✅ Sec {sec_id} saved → {audio_path} "
                    f"({os.path.getsize(audio_path):,} bytes, {duration:.2f}s)"
                )

                # Live-patch presentation.json with section audio path
                self._update_artifacts(
                    output_dir, sec_id, str(audio_path), duration,
                    language=None if lang_label == "english" else lang_label,
                    speaker=speaker,
                )

                # Generate quiz phase audio (question / correct / wrong / explanation)
                has_quiz = section.get("questions") or section.get("understanding_quiz")
                if has_quiz:
                    try:
                        quiz_map = self._generate_quiz_audio(
                            section, audio_dir, language=language, speaker=speaker
                        )
                        if quiz_map:
                            self._update_quiz_artifacts(output_dir, sec_id, quiz_map)
                            logger.info(
                                f"[AUDIO-ONLY] Quiz audio OK Sec {sec_id} "
                                f"({len(quiz_map)} question(s))"
                            )
                    except Exception as qe:
                        logger.error(f"[AUDIO-ONLY] Quiz audio failed Sec {sec_id}: {qe}")

                return {"status": "completed", "section_id": sec_id, "duration": duration}

            except Exception as e:
                logger.error(f"[AUDIO-ONLY] ❌ Sec {sec_id} failed: {e}")
                return {"status": "failed", "section_id": sec_id, "error": str(e)}

        # Process in batches
        batches = [
            sections[i:i + self.BATCH_SIZE]
            for i in range(0, len(sections), self.BATCH_SIZE)
        ]
        print(
            f"[AUDIO-ONLY] Starting {len(batches)} batches "
            f"(size {self.BATCH_SIZE}) for {len(sections)} sections..."
        )

        for batch_idx, batch in enumerate(batches):
            print(
                f"[AUDIO-ONLY] === Batch {batch_idx + 1}/{len(batches)} "
                f"({len(batch)} sections) ==="
            )
            with ThreadPoolExecutor(max_workers=self.BATCH_SIZE) as executor:
                futures = {
                    executor.submit(_process_section, sec): sec
                    for sec in batch
                }
                for future in as_completed(futures):
                    try:
                        res = future.result()
                        status = res.get("status")
                        results[status].append(res.get("section_id"))
                        print(
                            f"[AUDIO-ONLY] Sec {res.get('section_id')} → {status.upper()}"
                            + (f" ({res.get('duration', 0):.2f}s)" if status == "completed" else "")
                        )
                    except Exception as e:
                        logger.error(f"[AUDIO-ONLY] Batch future exception: {e}")

        print(
            f"[AUDIO-ONLY] Done. "
            f"completed={len(results['completed'])} "
            f"skipped={len(results['skipped'])} "
            f"failed={len(results['failed'])}"
        )
        return results

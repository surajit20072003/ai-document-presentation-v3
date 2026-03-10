"""
TTS Duration v1.4 - Pass 1.5: Audio Generation & Duration Measurement

Generates TTS audio files and extracts actual duration via metadata inspection.
Updates presentation.json with real durations (not LLM estimates).

Supports TTS providers:
- edge_tts: FREE Microsoft Edge TTS (default for production)
- narakeet: Paid high-quality Indian voice
- pyttsx3: Local/offline for dry run testing
- estimate: No audio, word-count based estimates only
"""

import os
import json
import time
import logging
import tempfile
import asyncio
import requests
from core.latex_to_speech import latex_to_speech
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Literal

MP3 = None
MutagenFile = None
pyttsx3 = None
edge_tts = None
MUTAGEN_AVAILABLE = False
PYTTSX3_AVAILABLE = False
EDGE_TTS_AVAILABLE = False

try:
    from mutagen.mp3 import MP3
    from mutagen._file import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except ImportError:
    pass

try:
    import pyttsx3 as pyttsx3_module
    pyttsx3 = pyttsx3_module
    PYTTSX3_AVAILABLE = True
except ImportError:
    pass

try:
    import edge_tts as edge_tts_module
    edge_tts = edge_tts_module
    EDGE_TTS_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger(__name__)

NARAKEET_API_KEY = os.environ.get("NARAKEET_API_KEY")
NARAKEET_API_URL = "https://api.narakeet.com/text-to-speech/mp3"

NARAKEET_VOICE = "ravi"
NARAKEET_VOICE_SPEED = 1.0

EDGE_TTS_VOICE = "en-IN-PrabhatNeural"
EDGE_TTS_RATE = "+0%"

# Custom TTS API (our-tts)
OUR_TTS_BASE_URL = os.environ.get("OUR_TTS_BASE_URL", "http://69.197.145.4:8000")
OUR_TTS_API_KEY = os.environ.get("OUR_TTS_API_KEY", "c2ef60a22479de3c143851dd9e8808786488928b7bf58c16a8ab92022c568a72")
OUR_TTS_VOICE_DESCRIPTION = "Male speaks clearly with calm tone"

MAX_RETRIES = 3
RETRY_DELAY = 2

TEMP_AUDIO_DIR = Path("/tmp/tts_audio")

TTSProvider = Literal["edge_tts", "narakeet", "pyttsx3", "our_tts", "estimate"]


def update_durations_simplified(
    presentation: Dict,
    output_dir: Optional[Path] = None,
    production_provider: TTSProvider = "edge_tts",
    update_status_callback=None
) -> Dict:

    """
    ISS-164 FIX: Simplified TTS system - word count estimation + single Edge TTS pass.
    
    Step 1: Apply word-count based duration estimates (fast, no audio needed)
    Step 2: Generate production audio using Edge TTS (async, concurrent)
    
    This is faster than two-pass because:
    - No pyttsx3 dependency needed
    - Duration estimation is instant (word count formula)
    - Only one audio generation pass
    
    Args:
        presentation: Merged presentation.json
        output_dir: Directory to save audio files
        production_provider: Provider for final audio ("edge_tts" or "narakeet")
        
    Returns:
        Updated presentation with estimated durations AND production audio
    """
    # Step 1: Apply word-count estimates (instant)
    logger.info("[TTS Simplified] Step 1: Applying word-count duration estimates...")
    presentation = _apply_estimates(presentation)
    
    # Step 2: Generate production audio
    if output_dir:
        audio_dir = Path(output_dir) / "audio"
    else:
        audio_dir = TEMP_AUDIO_DIR
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"[TTS Simplified] Step 2: Generating production audio with {production_provider}...")
    
    # Initialize pyttsx3 engine if needed as fallback
    # OPTIMIZATION: Skip completely if provider is 'estimate'
    pyttsx3_engine = None
    if production_provider != "estimate" and not (production_provider == "edge_tts" and EDGE_TTS_AVAILABLE):
        if PYTTSX3_AVAILABLE:
            try:
                pyttsx3_engine = pyttsx3.init()
                pyttsx3_engine.setProperty('rate', 150)
                logger.info("[TTS Simplified] Using pyttsx3 as fallback audio provider")
            except Exception as e:
                logger.warning(f"[TTS Simplified] pyttsx3 init failed: {e}")
    
    sections = presentation.get("sections", [])
    audio_count = 0
    import concurrent.futures
    tasks = []
    for section_idx, section in enumerate(sections):
        section_id = section.get("section_id", f"section_{section_idx}")
        segments = section.get("narration", {}).get("segments", [])
        for seg_idx, segment in enumerate(segments):
            text = segment.get("text", "")
            if not text.strip(): continue
            audio_filename = f"{section_id}_{segment.get('segment_id', f'seg_{seg_idx}')}"
            audio_path = audio_dir / f"{audio_filename}.mp3"
            tasks.append((segment, text, audio_path))

    # TTS Retry Configuration
    MAX_TTS_RETRIES = 2
    tts_failures = []  # Track failed segments for reporting
    
    def work(task):
        segment, text, audio_path = task
        nonlocal audio_count, tts_failures
        
        # ISS-FIX: Clean text (LaTeX to Speech) before sending to TTS
        clean_text = latex_to_speech(text)
        
        # Retry logic with max 2 attempts
        for attempt in range(MAX_TTS_RETRIES):
            try:
                if production_provider == "edge_tts" and EDGE_TTS_AVAILABLE:
                    duration = _generate_edge_tts(clean_text, audio_path)
                elif production_provider == "narakeet":
                    duration = _generate_narakeet(clean_text, audio_path)
                elif production_provider == "our_tts":
                    wav_path = audio_dir / f"{audio_path.stem}.wav"
                    try:
                        duration = _generate_our_tts(clean_text, wav_path)
                        if wav_path.exists(): audio_path = wav_path
                    except Exception as try_fallback_err:
                        logger.warning(f"[TTS] our_tts failed ({try_fallback_err}), falling back to edge_tts")
                        if EDGE_TTS_AVAILABLE:
                            audio_path = audio_dir / f"{audio_path.stem}.mp3" # Reset to mp3
                            duration = _generate_edge_tts(clean_text, audio_path)
                        else:
                            raise try_fallback_err
                elif pyttsx3_engine:
                    wav_path = audio_dir / f"{audio_path.stem}.wav"
                    duration = _generate_pyttsx3(text, wav_path, pyttsx3_engine)
                    if wav_path.exists(): audio_path = wav_path
                else:
                    # Estimate provider - no retries needed
                    return
                
                if audio_path.exists():
                    segment["audio_file"] = str(audio_path.name)
                    segment["audio_path"] = f"audio/{audio_path.name}"
                    segment["duration_seconds"] = duration
                    segment["duration"] = duration
                    audio_count += 1
                    print(f"[TTS] Generated: {audio_path.name}")
                    return  # Success, exit retry loop
                    
            except Exception as e:
                # FAIL-FAST: Stop retrying if Server Error (5xx) OR Timeout
                err_str = str(e)
                fail_indicators = [
                    "500", "502", "503", "504", "Internal Server Error",
                    "Read timed out", "Connection timed out", "ConnectTimeout", "ReadTimeout"
                ]
                if any(x in err_str for x in fail_indicators):
                    logger.error(f"[TTS] Fail-Fast on Server Error/Timeout for {audio_path.name}: {e}")
                    break # Stop retrying immediately

                if attempt < MAX_TTS_RETRIES - 1:
                    logger.warning(f"[TTS] Retry {attempt + 1}/{MAX_TTS_RETRIES} for {audio_path.name}: {e}")
                    time.sleep(0.5)  # Brief pause before retry
                else:
                    logger.error(f"[TTS] Failed after {MAX_TTS_RETRIES} attempts for {audio_path.name}: {e}")
                    tts_failures.append(str(audio_path.name))
                    # Use estimated duration as fallback
                    segment["duration_seconds"] = _estimate_duration(text)
                    segment["duration"] = segment["duration_seconds"]
                    segment["tts_failed"] = True

    logger.info(f"[TTS Simplified] Spawning workers for {len(tasks)} segments...")
    
    # ISS-FIX: pyttsx3 is not thread-safe, especially on Windows SAPI5
    if production_provider == "pyttsx3":
        logger.info("[TTS Simplified] Using sequential execution for pyttsx3")
        for task in tasks:
            work(task)
    else:
        # edge_tts and narakeet (network based) are throttled in batches of 5 per user request
        BATCH_SIZE = 5
        task_batches = [tasks[i:i + BATCH_SIZE] for i in range(0, len(tasks), BATCH_SIZE)]
        logger.info(f"[TTS Simplified] Processing {len(tasks)} segments in {len(task_batches)} throttled batches...")
        
        for batch_idx, batch in enumerate(task_batches):
            with concurrent.futures.ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
                # Use wait to ensure entire batch finishes before pause
                futures = [executor.submit(work, task) for task in batch]
                concurrent.futures.wait(futures)
            
            if batch_idx < len(task_batches) - 1:
                import time
                time.sleep(1) # Small 1s cooldown between batches
    
    logger.info(f"[TTS Simplified] Parallel generation complete. Generated {audio_count} files.")
    
    if "metadata" not in presentation:
        presentation["metadata"] = {}
    presentation["metadata"]["tts_method"] = "simplified"
    presentation["metadata"]["duration_provider"] = "word_count_estimate"
    presentation["metadata"]["audio_provider"] = production_provider
    
    # TTS failure tracking for completed_with_warnings status
    presentation["metadata"]["tts_generated_count"] = audio_count
    presentation["metadata"]["tts_total_segments"] = len(tasks)
    if tts_failures:
        presentation["metadata"]["tts_failed_count"] = len(tts_failures)
        presentation["metadata"]["tts_failures"] = tts_failures[:10]  # First 10 for debugging
        msg = f"[TTS] {len(tts_failures)} segments failed - using estimated durations"
        logger.warning(msg)
        if update_status_callback:
            update_status_callback("tts_generation", f"Warning: {len(tts_failures)} audio files failed. Using estimates.")

    
    # RECALCULATE TOTALS: Ensure metadata matches real audio lengths
    total_pres_duration = 0.0
    for section in presentation.get("sections", []):
        section_total = 0.0
        for seg in section.get("narration", {}).get("segments", []):
            section_total += seg.get("duration_seconds", 0.0)
        if "narration" in section:
            section["narration"]["total_duration_seconds"] = round(section_total, 2)
        total_pres_duration += section_total
    presentation["metadata"]["total_duration_seconds"] = round(total_pres_duration, 2)
    
    # Consolidate section audio
    if output_dir:
        presentation = consolidate_section_audio(presentation, audio_dir)
    
    return presentation


def update_durations_two_pass(
    presentation: Dict,
    output_dir: Optional[Path] = None,
    production_provider: TTSProvider = "edge_tts"
) -> Dict:
    """
    DEPRECATED: Two-pass TTS system - use update_durations_simplified() instead.
    
    ISS-164: This is kept for backwards compatibility but the simplified
    approach is preferred for performance.
    """
    # Redirect to simplified approach
    logger.info("[TTS Two-Pass] DEPRECATED - redirecting to simplified approach")
    return update_durations_simplified(presentation, output_dir, production_provider)
    
    
def _update_durations_two_pass_legacy(
    presentation: Dict,
    output_dir: Optional[Path] = None,
    production_provider: TTSProvider = "edge_tts"
) -> Dict:
    """
    LEGACY: Two-pass TTS system per V1.5 spec.
    
    Pass 1: Use pyttsx3 to measure accurate durations (local, fast)
    Pass 2: Use Edge TTS to generate production audio (keeps pyttsx3 durations)
    
    This ensures display_directives timing matches actual audio because
    pyttsx3 and Edge TTS have different speaking rates.
    
    Args:
        presentation: Merged presentation.json
        output_dir: Directory to save audio files
        production_provider: Provider for final audio ("edge_tts" or "narakeet")
        
    Returns:
        Updated presentation with measured durations AND production audio
    """
    if not PYTTSX3_AVAILABLE:
        logger.warning("[TTS Two-Pass] pyttsx3 not available, falling back to single-pass")
        return update_durations_from_tts(presentation, output_dir, True, production_provider)
    
    if output_dir:
        audio_dir = Path(output_dir) / "audio"
    else:
        audio_dir = TEMP_AUDIO_DIR
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("[TTS Two-Pass] PASS 1: Measuring durations with pyttsx3...")
    
    # Pass 1: Measure with pyttsx3
    try:
        pyttsx3_engine = pyttsx3.init()
        pyttsx3_engine.setProperty('rate', 150)
    except Exception as e:
        logger.warning(f"[TTS Two-Pass] pyttsx3 init failed: {e}, falling back to single-pass")
        return update_durations_from_tts(presentation, output_dir, True, production_provider)
    
    sections = presentation.get("sections", [])
    measured_durations = {}  # Store measured durations
    
    for section_idx, section in enumerate(sections):
        section_id = section.get("section_id", f"section_{section_idx}")
        narration = section.get("narration", {})
        segments = narration.get("segments", [])
        section_duration = 0.0
        
        for seg_idx, segment in enumerate(segments):
            segment_id = segment.get("segment_id", f"seg_{seg_idx}")
            text = segment.get("text", "")
            
            if not text.strip():
                segment["duration_seconds"] = 0.0
                continue
            
            # Measure with pyttsx3 (temp file, discarded after)
            temp_wav = audio_dir / f"temp_measure_{section_id}_{segment_id}.wav"
            try:
                actual_duration = _generate_pyttsx3(text, temp_wav, pyttsx3_engine)
                segment["duration_seconds"] = round(actual_duration, 2)
                measured_durations[f"{section_id}_{segment_id}"] = actual_duration
                section_duration += actual_duration
                # Delete temp file
                if temp_wav.exists():
                    temp_wav.unlink()
            except Exception as e:
                logger.warning(f"[TTS Two-Pass] Measure failed for {segment_id}: {e}")
                estimate = _estimate_duration(text)
                segment["duration_seconds"] = estimate
                measured_durations[f"{section_id}_{segment_id}"] = estimate
                section_duration += estimate
        
        narration["total_duration_seconds"] = round(section_duration, 2)
    
    logger.info(f"[TTS Two-Pass] PASS 1 complete: Measured {len(measured_durations)} segments")
    
    # Pass 2: Generate production audio (but keep measured durations)
    logger.info(f"[TTS Two-Pass] PASS 2: Generating production audio with {production_provider}...")
    
    for section_idx, section in enumerate(sections):
        section_id = section.get("section_id", f"section_{section_idx}")
        narration = section.get("narration", {})
        segments = narration.get("segments", [])
        
        for seg_idx, segment in enumerate(segments):
            segment_id = segment.get("segment_id", f"seg_{seg_idx}")
            text = segment.get("text", "")
            
            if not text.strip():
                continue
            
            audio_filename = f"{section_id}_{segment_id}"
            audio_path = audio_dir / f"{audio_filename}.mp3"
            
            try:
                if production_provider == "edge_tts" and EDGE_TTS_AVAILABLE:
                    _generate_edge_tts(text, audio_path)
                else:
                    # Fallback: use pyttsx3 audio (skip Narakeet)
                    audio_path = audio_dir / f"{audio_filename}.wav"
                    _generate_pyttsx3(text, audio_path, pyttsx3_engine)
                
                if audio_path.exists():
                    segment["audio_file"] = str(audio_path.name)
                    # IMPORTANT: Keep the pyttsx3-measured duration, don't overwrite!
                    logger.debug(f"[TTS Two-Pass] {segment_id}: audio={audio_path.name}, duration={segment['duration_seconds']}s (measured)")
                    
            except Exception as e:
                logger.warning(f"[TTS Two-Pass] Production audio failed for {segment_id}: {e}")
    
    logger.info(f"[TTS Two-Pass] PASS 2 complete: Production audio generated")
    
    if "metadata" not in presentation:
        presentation["metadata"] = {}
    presentation["metadata"]["tts_method"] = "two_pass"
    presentation["metadata"]["duration_provider"] = "pyttsx3"
    presentation["metadata"]["audio_provider"] = production_provider
    
    # Consolidate section audio
    if output_dir:
        presentation = consolidate_section_audio(presentation, audio_dir)
    
    return presentation


def update_durations_from_tts(
    presentation: Dict,
    output_dir: Optional[Path] = None,
    generate_audio: bool = True,
    tts_provider: TTSProvider = "edge_tts"
) -> Dict:
    """
    LEGACY: Single-pass TTS - generates audio and measures from same provider.
    
    NOTE: For V1.5, use update_durations_two_pass() instead to avoid
    audio/video drift caused by different speaking rates.
    
    For each narration segment:
    1. Generate TTS audio file (based on provider)
    2. Inspect file metadata to get exact duration
    3. Update duration_seconds field in JSON
    4. Optionally keep audio files for later use
    
    Args:
        presentation: Merged presentation.json
        output_dir: Directory to save audio files (if None, uses temp dir)
        generate_audio: If True, generate audio and measure. If False, use estimates.
        tts_provider: "edge_tts" (default), "narakeet", "pyttsx3", or "estimate"
        
    Returns:
        Updated presentation.json with actual durations
    """
    if not generate_audio or tts_provider == "estimate":
        logger.info("[TTS Duration] Using word-count estimates (no audio generation)")
        return _apply_estimates(presentation)
    
    if tts_provider == "edge_tts":
        if not EDGE_TTS_AVAILABLE:
            logger.warning("[TTS Duration] edge_tts not available, falling back to narakeet")
            tts_provider = "narakeet"
    
    if tts_provider == "narakeet":
        if not NARAKEET_API_KEY:
            logger.warning("[TTS Duration] NARAKEET_API_KEY not set, falling back to pyttsx3")
            tts_provider = "pyttsx3"
    
    if tts_provider == "pyttsx3":
        if not PYTTSX3_AVAILABLE:
            logger.warning("[TTS Duration] pyttsx3 not available, using estimates")
            return _apply_estimates(presentation)
    
    if output_dir:
        audio_dir = Path(output_dir) / "audio"
    else:
        audio_dir = TEMP_AUDIO_DIR
    
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"[TTS Duration] Starting TTS generation with provider: {tts_provider}")
    
    pyttsx3_engine = None
    if tts_provider == "pyttsx3":
        try:
            pyttsx3_engine = pyttsx3.init()
            pyttsx3_engine.setProperty('rate', 150)
        except Exception as e:
            logger.warning(f"[TTS Duration] pyttsx3 init failed: {e}, using estimates")
            return _apply_estimates(presentation)
    
    total_segments = 0
    total_duration = 0.0
    
    sections = presentation.get("sections", [])
    
    for section_idx, section in enumerate(sections):
        section_id = section.get("section_id", f"section_{section_idx}")
        narration = section.get("narration", {})
        segments = narration.get("segments", [])
        
        section_duration = 0.0
        
        for seg_idx, segment in enumerate(segments):
            segment_id = segment.get("segment_id", f"seg_{seg_idx}")
            text = segment.get("text", "")
            
            if not text.strip():
                segment["duration_seconds"] = 0.0
                continue
            
            audio_filename = f"{section_id}_{segment_id}"
            
            try:
                if tts_provider == "edge_tts":
                    audio_path = audio_dir / f"{audio_filename}.mp3"
                    try:
                        actual_duration = _generate_edge_tts(text, audio_path)
                    except EdgeTTSError as e:
                        logger.warning(f"[TTS Duration] Edge TTS failed, trying Narakeet: {e}")
                        if NARAKEET_API_KEY:
                            try:
                                actual_duration = _generate_narakeet(text, audio_path)
                            except NarakeetError as ne:
                                logger.warning(f"[TTS Duration] Narakeet also failed: {ne}")
                                if PYTTSX3_AVAILABLE:
                                    if pyttsx3_engine is None:
                                        pyttsx3_engine = pyttsx3.init()
                                        pyttsx3_engine.setProperty('rate', 150)
                                    audio_path = audio_dir / f"{audio_filename}.wav"
                                    actual_duration = _generate_pyttsx3(text, audio_path, pyttsx3_engine)
                                else:
                                    raise
                        elif PYTTSX3_AVAILABLE:
                            if pyttsx3_engine is None:
                                pyttsx3_engine = pyttsx3.init()
                                pyttsx3_engine.setProperty('rate', 150)
                            audio_path = audio_dir / f"{audio_filename}.wav"
                            actual_duration = _generate_pyttsx3(text, audio_path, pyttsx3_engine)
                        else:
                            raise
                        
                elif tts_provider == "narakeet":
                    audio_path = audio_dir / f"{audio_filename}.mp3"
                    try:
                        actual_duration = _generate_narakeet(text, audio_path)
                    except NarakeetError as e:
                        if PYTTSX3_AVAILABLE and pyttsx3_engine is None:
                            logger.warning(f"[TTS Duration] Narakeet failed, falling back to pyttsx3: {e}")
                            pyttsx3_engine = pyttsx3.init()
                            pyttsx3_engine.setProperty('rate', 150)
                        if pyttsx3_engine:
                            audio_path = audio_dir / f"{audio_filename}.wav"
                            actual_duration = _generate_pyttsx3(text, audio_path, pyttsx3_engine)
                        else:
                            raise
                else:
                    audio_path = audio_dir / f"{audio_filename}.wav"
                    actual_duration = _generate_pyttsx3(text, audio_path, pyttsx3_engine)
                
                segment["duration_seconds"] = round(actual_duration, 2)
                
                # ISS-137 FIX: Only set audio_file if file actually exists
                if audio_path.exists():
                    segment["audio_file"] = str(audio_path.name)
                    logger.debug(f"[TTS Duration] {segment_id}: {actual_duration:.2f}s, file={audio_path.name}")
                else:
                    logger.warning(f"[TTS Duration] {segment_id}: Audio file not created, using estimate duration")
                
                section_duration += actual_duration
                total_duration += actual_duration
                total_segments += 1
                
            except Exception as e:
                logger.warning(f"[TTS Duration] Failed for {segment_id}: {e}, using estimate")
                estimate = _estimate_duration(text)
                segment["duration_seconds"] = estimate
                section_duration += estimate
                total_duration += estimate
                total_segments += 1
        
        narration["total_duration_seconds"] = round(section_duration, 2)
    
    if "metadata" not in presentation:
        presentation["metadata"] = {}
    presentation["metadata"]["total_duration_seconds"] = round(total_duration, 2)
    presentation["metadata"]["tts_segments_processed"] = total_segments
    presentation["metadata"]["tts_provider"] = tts_provider
    
    logger.info(f"[TTS Duration] Processed {total_segments} segments, total duration: {total_duration:.2f}s")
    
    # ISS-115 FIX: Consolidate segment audio into section-level audio files
    if output_dir:
        presentation = consolidate_section_audio(presentation, audio_dir)
    
    return presentation


def consolidate_section_audio(presentation: Dict, audio_dir: Path) -> Dict:
    """
    ISS-115 FIX: Consolidate per-segment audio into per-section audio files.
    
    Player expects section-level audio_path like "section_1.mp3".
    TTS generates per-segment files like "1_1.mp3", "1_2.mp3".
    
    This function:
    1. Concatenates segment audio files into section audio file
    2. Sets section["audio_path"] to the consolidated filename
    """
    try:
        from pydub import AudioSegment
        PYDUB_AVAILABLE = True
    except ImportError:
        logger.warning("[TTS Consolidate] pydub not available, using symlink to first segment instead")
        PYDUB_AVAILABLE = False
    
    sections = presentation.get("sections", [])
    
    for section in sections:
        section_id = section.get("section_id", 0)
        narration = section.get("narration", {})
        segments = narration.get("segments", [])
        
        if not segments:
            continue
        
        # Collect segment audio files
        segment_files = []
        for seg in segments:
            audio_file = seg.get("audio_file")
            if audio_file:
                audio_path = audio_dir / audio_file
                if audio_path.exists():
                    segment_files.append(audio_path)
        
        if not segment_files:
            continue
        
        # Output filename matches player expectation
        section_audio_name = f"section_{section_id}.mp3"
        section_audio_path = audio_dir / section_audio_name
        
        if len(segment_files) == 1:
            # Single segment - just copy/link
            import shutil
            shutil.copy(segment_files[0], section_audio_path)
            logger.debug(f"[TTS Consolidate] Section {section_id}: Copied single segment audio")
        elif PYDUB_AVAILABLE:
            # Multiple segments - concatenate with pydub
            try:
                combined = AudioSegment.empty()
                for seg_file in segment_files:
                    audio = AudioSegment.from_file(seg_file)
                    combined += audio
                combined.export(section_audio_path, format="mp3")
                logger.debug(f"[TTS Consolidate] Section {section_id}: Concatenated {len(segment_files)} segments")
            except Exception as e:
                logger.warning(f"[TTS Consolidate] Section {section_id} concat failed: {e}, using first segment")
                import shutil
                shutil.copy(segment_files[0], section_audio_path)
        else:
            # Fallback: use first segment
            import shutil
            shutil.copy(segment_files[0], section_audio_path)
            logger.debug(f"[TTS Consolidate] Section {section_id}: Copied first segment (no pydub)")
        
        # ISS-115 FIX: Set section-level audio_path
        section["audio_path"] = section_audio_name
        logger.info(f"[TTS Consolidate] Section {section_id}: audio_path = {section_audio_name}")
    
    return presentation


class EdgeTTSError(Exception):
    """Raised when Edge TTS fails."""
    pass


class NarakeetError(Exception):
    """Raised when Narakeet API fails after all retries."""
    pass


async def _generate_edge_tts_async(text: str, output_path: Path) -> float:
    """
    Async function to generate TTS audio using Edge TTS.
    """
    import re
    clean_text = re.sub(r'<[^>]+/>', '', text)
    
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(clean_text, EDGE_TTS_VOICE, rate=EDGE_TTS_RATE)
            await communicate.save(str(output_path))
            
            if output_path.exists() and MUTAGEN_AVAILABLE:
                audio = MP3(output_path)
                duration = audio.info.length
                return duration
            else:
                return _estimate_duration(text)
        except Exception as e:
            if attempt < 2:
                logger.warning(f"[TTS Retry] Edge TTS failed (attempt {attempt+1}/3) for {output_path.name}: {e}")
                await asyncio.sleep(1) # Small pause before retry
                continue
            raise EdgeTTSError(f"Edge TTS generation failed after retries: {e}")
    return _estimate_duration(text)


def _generate_edge_tts(text: str, output_path: Path) -> float:
    """
    Generate TTS audio using Edge TTS (sync wrapper for async).
    """
    try:
        # Simplest possible robust approach:
        # Always run in a separate thread with a clean event loop
        import concurrent.futures
        
        def run_async():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                async def _timed_gen():
                    return await asyncio.wait_for(_generate_edge_tts_async(text, output_path), timeout=60.0)
                return new_loop.run_until_complete(_timed_gen())
            finally:
                new_loop.close()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            return executor.submit(run_async).result(timeout=65.0)

    except Exception as e:
        logger.error(f"[TTS Duration] Edge TTS failure: {e}")
        raise EdgeTTSError(f"Edge TTS failed: {e}")


def _generate_narakeet(text: str, output_path: Path) -> float:
    """
    Generate TTS audio using Narakeet API and measure its duration.
    
    Args:
        text: Text to convert to speech
        output_path: Path to save the audio file
        
    Returns:
        Audio duration in seconds
        
    Raises:
        NarakeetError: If Narakeet fails after all retries (allows fallback to pyttsx3)
    """
    for attempt in range(MAX_RETRIES):
        try:
            headers = {
                "x-api-key": NARAKEET_API_KEY,
                "Content-Type": "text/plain",
                "Accept": "application/octet-stream"
            }
            
            params = {
                "voice": NARAKEET_VOICE,
                "voice-speed": NARAKEET_VOICE_SPEED
            }
            
            response = requests.post(
                NARAKEET_API_URL,
                headers=headers,
                params=params,
                data=text.encode("utf-8"),
                timeout=60
            )
            
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                audio = MP3(output_path)
                duration = audio.info.length
                
                return duration
            
            elif response.status_code == 429:
                logger.warning(f"[TTS Duration] Rate limited, waiting...")
                time.sleep(RETRY_DELAY * (attempt + 1))
                
            else:
                logger.error(f"[TTS Duration] API error: {response.status_code}")
                raise NarakeetError(f"Narakeet API error: {response.status_code}")
                
        except NarakeetError:
            raise
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"[TTS Duration] Retry {attempt + 1}/{MAX_RETRIES}: {e}")
                time.sleep(RETRY_DELAY)
            else:
                raise NarakeetError(f"Failed after {MAX_RETRIES} attempts: {e}")
    
    raise NarakeetError(f"Failed to generate TTS after {MAX_RETRIES} attempts")


class OurTTSError(Exception):
    """Raised when our custom TTS API fails."""
    pass


def _generate_our_tts(text: str, output_path: Path) -> float:
    """
    Generate TTS audio using our custom TTS API.
    
    API: http://69.197.145.4:8000
    Returns duration in seconds.
    """
    import requests
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": OUR_TTS_API_KEY
    }
    
    payload = {
        "text": text,
        "description": OUR_TTS_VOICE_DESCRIPTION
    }
    
    try:
        # Step 1: Request TTS generation (POST to /tts endpoint)
        response = requests.post(
            f"{OUR_TTS_BASE_URL}/tts",
            headers=headers,
            json=payload,
            timeout=(5, 15)
        )
        
        data = response.json()
        
        if data.get("status") == "success":
            audio_path_from_api = data.get("audio_url")
            full_audio_url = f"{OUR_TTS_BASE_URL}{audio_path_from_api}"
            
            # Step 2: Download the audio file
            audio_response = requests.get(full_audio_url, timeout=(5, 30))
            
            with open(output_path, "wb") as f:
                f.write(audio_response.content)
            
            # Get duration using mutagen (for WAV files)
            if MUTAGEN_AVAILABLE and output_path.exists():
                try:
                    from mutagen.wave import WAVE
                    audio = WAVE(str(output_path))
                    duration = audio.info.length
                    return duration
                except:
                    # Fallback to estimate
                    return _estimate_duration(text)
            else:
                return _estimate_duration(text)
        else:
            error_msg = data.get("error", "Unknown error")
            raise OurTTSError(f"TTS API returned error: {error_msg}")
            
    except OurTTSError:
        raise
    except Exception as e:
        raise OurTTSError(f"Failed to generate TTS: {e}")


class Pyttsx3Error(Exception):
    """Raised when pyttsx3 fails to generate audio."""
    pass


def _generate_pyttsx3(text: str, output_path: Path, engine) -> float:
    """
    Generate TTS audio using pyttsx3 (local/offline) and measure its duration.
    
    Args:
        text: Text to convert to speech
        output_path: Path to save the audio file
        engine: pyttsx3 engine instance
        
    Returns:
        Audio duration in seconds
        
    Raises:
        Pyttsx3Error: If file generation fails (ISS-137 fix)
    """
    try:
        engine.save_to_file(text, str(output_path))
        engine.runAndWait()
        
        if output_path.exists():
            audio = MutagenFile(output_path)
            if audio is not None and hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                return audio.info.length
            else:
                # File exists but can't read duration - use estimate but file is valid
                logger.warning(f"[TTS Duration] pyttsx3: Cannot read duration from {output_path.name}, using estimate")
                return _estimate_duration(text)
        else:
            # ISS-137 FIX: Raise exception instead of silently returning estimate
            raise Pyttsx3Error(f"pyttsx3 failed to create file: {output_path}")
            
    except Pyttsx3Error:
        raise
    except Exception as e:
        logger.error(f"[TTS Duration] pyttsx3 error: {e}")
        raise Pyttsx3Error(f"pyttsx3 failed: {e}")


def _apply_estimates(presentation: Dict) -> Dict:
    """Apply word-count based duration estimates to all segments."""
    total_duration = 0.0
    total_segments = 0
    
    for section in presentation.get("sections", []):
        section_duration = 0.0
        for segment in section.get("narration", {}).get("segments", []):
            text = segment.get("text", "")
            estimate = _estimate_duration(text)
            segment["duration_seconds"] = estimate
            section_duration += estimate
            total_duration += estimate
            total_segments += 1
        
        if "narration" in section:
            section["narration"]["total_duration_seconds"] = round(section_duration, 2)
    
    if "metadata" not in presentation:
        presentation["metadata"] = {}
    presentation["metadata"]["total_duration_seconds"] = round(total_duration, 2)
    presentation["metadata"]["tts_segments_processed"] = total_segments
    presentation["metadata"]["tts_provider"] = "estimate"
    
    return presentation


def _estimate_duration(text: str) -> float:
    """
    Estimate duration based on word count.
    Used as fallback when TTS generation fails.
    
    Average speaking rate: ~150 words per minute
    Indian English with pauses: ~130 words per minute
    """
    word_count = len(text.split())
    words_per_second = 130 / 60
    
    duration = word_count / words_per_second
    
    duration *= 1.1
    
    return round(duration, 2)


def cleanup_temp_audio(keep_files: bool = False) -> None:
    """Remove temporary audio files."""
    if keep_files:
        logger.info(f"[TTS Duration] Keeping audio files in {TEMP_AUDIO_DIR}")
        return
    
    if TEMP_AUDIO_DIR.exists():
        for file in TEMP_AUDIO_DIR.glob("*.*"):
            try:
                file.unlink()
            except Exception as e:
                logger.warning(f"[TTS Duration] Failed to delete {file}: {e}")
        logger.info("[TTS Duration] Cleaned up temporary audio files")


def get_total_duration(presentation: Dict) -> float:
    """Get total duration from presentation metadata or calculate it."""
    if "metadata" in presentation and "total_duration_seconds" in presentation["metadata"]:
        return presentation["metadata"]["total_duration_seconds"]
    
    total = 0.0
    for section in presentation.get("sections", []):
        for segment in section.get("narration", {}).get("segments", []):
            total += segment.get("duration_seconds", 0)
    
    return total

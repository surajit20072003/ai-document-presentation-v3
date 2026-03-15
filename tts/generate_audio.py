import os
import sys
import time
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.latex_to_speech import latex_to_speech

NARAKEET_API_KEY = os.environ.get("NARAKEET_API_KEY", "")
NARAKEET_VOICE = "ravi"
NARAKEET_STREAMING_LIMIT = 1024


class TTSGenerationError(Exception):
    """Raised when TTS generation fails - NO fallback to gTTS."""
    pass


def _narakeet_streaming(narration: str, output_path: str, section_id: int) -> tuple:
    """Use Narakeet streaming API for short text (<= 1024 chars).
    
    Returns: (output_path, actual_duration_seconds)
    """
    response = requests.post(
        f"https://api.narakeet.com/text-to-speech/mp3?voice={NARAKEET_VOICE}",
        headers={
            "x-api-key": NARAKEET_API_KEY,
            "Content-Type": "text/plain",
            "accept": "application/octet-stream"
        },
        data=narration.encode('utf-8'),
        timeout=120
    )
    
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        duration_str = response.headers.get('x-duration-seconds', '')
        try:
            actual_duration = float(duration_str) if duration_str else None
        except ValueError:
            actual_duration = None
        print(f"[TTS] Section {section_id}: Narakeet streaming SUCCESS - {output_path} (actual_duration={actual_duration}s)")
        return output_path, actual_duration
    else:
        raise TTSGenerationError(
            f"Narakeet streaming API failed: {response.status_code} - {response.text[:200]}"
        )


def _narakeet_polling(narration: str, output_path: str, section_id: int) -> tuple:
    """Use Narakeet polling API for long text (> 1024 chars).
    
    Returns: (output_path, actual_duration_seconds)
    """
    print(f"[TTS] Section {section_id}: Using Narakeet polling API (text_len={len(narration)})")
    
    response = requests.post(
        f"https://api.narakeet.com/text-to-speech/mp3?voice={NARAKEET_VOICE}",
        headers={
            "x-api-key": NARAKEET_API_KEY,
            "Content-Type": "text/plain"
        },
        data=narration.encode('utf-8'),
        timeout=30
    )
    
    if response.status_code != 200:
        raise TTSGenerationError(
            f"Narakeet polling API submission failed: {response.status_code} - {response.text[:200]}"
        )
    
    result = response.json()
    status_url = result.get('statusUrl')
    
    if not status_url:
        raise TTSGenerationError("Narakeet polling API did not return statusUrl")
    
    max_wait = 300
    poll_interval = 3
    elapsed = 0
    
    while elapsed < max_wait:
        status_response = requests.get(
            status_url,
            headers={"x-api-key": NARAKEET_API_KEY},
            timeout=30
        )
        
        if status_response.status_code != 200:
            raise TTSGenerationError(
                f"Narakeet status poll failed: {status_response.status_code}"
            )
        
        status_data = status_response.json()
        
        if status_data.get('finished'):
            if status_data.get('succeeded'):
                audio_url = status_data.get('result')
                if not audio_url:
                    raise TTSGenerationError("Narakeet finished but no result URL")
                
                audio_response = requests.get(audio_url, timeout=120)
                if audio_response.status_code != 200:
                    raise TTSGenerationError(
                        f"Failed to download audio: {audio_response.status_code}"
                    )
                
                with open(output_path, 'wb') as f:
                    f.write(audio_response.content)
                
                actual_duration = status_data.get('durationInSeconds')
                try:
                    actual_duration = float(actual_duration) if actual_duration else None
                except (ValueError, TypeError):
                    actual_duration = None
                print(f"[TTS] Section {section_id}: Narakeet polling SUCCESS - {output_path} (actual_duration={actual_duration}s)")
                return output_path, actual_duration
            else:
                raise TTSGenerationError("Narakeet polling task failed")
        
        time.sleep(poll_interval)
        elapsed += poll_interval
    
    raise TTSGenerationError(f"Narakeet polling timed out after {max_wait}s")


def generate_section_audio(section: dict, output_dir: str) -> tuple:
    """Generate audio for a section using Narakeet TTS.
    
    FAIL-FAST: No fallback to gTTS. Raises TTSGenerationError if Narakeet fails.
    Uses streaming API for short text, polling API for long text.
    
    ISS-074 FIX: Now returns actual audio duration for timing sync.
    
    Returns: (audio_path, actual_duration_seconds)
    """
    section_id = section.get("section_id") or section.get("id", 1)
    section_type = section.get("section_type", "content")
    narration = section.get("narration", "")
    
    # v1.3 FIX: Handle narration as dict (v1.3 format) or string (legacy)
    if isinstance(narration, dict):
        # v1.3 format: narration is {"full_text": "...", "segments": [...]}
        narration = narration.get("full_text", "")
        if not narration:
            # Fallback: combine segment texts
            segments = section.get("narration", {}).get("segments", [])
            narration = " ".join(seg.get("text", "") for seg in segments if seg.get("text"))
    
    # ISS-003 FIX: For recap sections, combine narration from all recap_scenes
    if section_type == "recap":
        recap_scenes = section.get("recap_scenes", [])
        if recap_scenes:
            scene_narrations = [scene.get("narration", "") for scene in recap_scenes if scene.get("narration")]
            if scene_narrations:
                narration = " ".join(scene_narrations)
                print(f"[TTS] Section {section_id}: Recap - combined {len(scene_narrations)} scene narrations (total={len(narration)} chars)")
    
    if not narration:
        segments = section.get("segments", [])
        narration = " ".join([seg.get("text", "") for seg in segments])
    
    if not narration:
        narration = f"Section {section_id}: {section.get('title', 'Educational content')}"
    
    original_len = len(narration)
    narration = latex_to_speech(narration)
    if len(narration) != original_len:
        print(f"[TTS] Section {section_id}: LaTeX converted ({original_len} -> {len(narration)} chars)")
    
    output_path = str(Path(output_dir) / f"section_{section_id}.mp3")
    
    if not NARAKEET_API_KEY:
        raise TTSGenerationError(
            "NARAKEET_API_KEY not configured. TTS requires Narakeet API."
        )
    
    print(f"[TTS] Section {section_id}: Generating audio (voice={NARAKEET_VOICE}, text_len={len(narration)})")
    
    try:
        if len(narration) <= NARAKEET_STREAMING_LIMIT:
            path, duration = _narakeet_streaming(narration, output_path, section_id)
        else:
            path, duration = _narakeet_polling(narration, output_path, section_id)
        return path, duration
    except requests.exceptions.RequestException as e:
        raise TTSGenerationError(f"Narakeet API request failed: {e}")


def generate_all_audio(presentation: dict, output_dir: str) -> list:
    """Generate audio for all sections in presentation.
    
    ISS-074 FIX: Now collects actual durations for timing sync.
    Returns audio file info including actual duration from Narakeet API.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    audio_files = []
    sections = presentation.get("sections", presentation.get("topics", []))
    
    for section in sections:
        audio_path, actual_duration = generate_section_audio(section, output_dir)
        audio_files.append({
            "section_id": section.get("section_id") or section.get("id"),
            "section_type": section.get("section_type", "content"),
            "audio_path": audio_path,
            "actual_duration_seconds": actual_duration
        })
    
    return audio_files


def sync_timing_with_audio(presentation: dict, audio_files: list) -> dict:
    """
    ISS-074 FIX: Synchronize segment durations with actual TTS audio durations.
    
    This ensures display_directives fire at correct times matching audio playback.
    Also sets audio_path and audio_duration on each section for player consumption.
    
    Args:
        presentation: The presentation dict with sections
        audio_files: List of audio info dicts with actual_duration_seconds
    
    Returns:
        Updated presentation with synchronized timing and audio paths
    """
    audio_by_section = {af["section_id"]: af for af in audio_files}
    
    sections = presentation.get("sections", presentation.get("topics", []))
    
    for section in sections:
        section_id = section.get("section_id") or section.get("id")
        audio_info = audio_by_section.get(section_id)
        
        if not audio_info:
            continue
        
        section["audio_path"] = audio_info.get("audio_path")
        section["audio_duration"] = audio_info.get("actual_duration_seconds")
        
        actual_total = audio_info.get("actual_duration_seconds")
        if actual_total is None:
            continue
        
        narration = section.get("narration", {})
        segments = narration.get("segments", []) if isinstance(narration, dict) else section.get("narration_segments", [])
        
        if not segments:
            continue
        
        llm_total = sum(seg.get("duration_seconds", 0) for seg in segments)
        
        if llm_total <= 0:
            continue
        
        scale_factor = actual_total / llm_total
        
        if abs(scale_factor - 1.0) > 0.05:
            print(f"[TIMING SYNC] Section {section_id}: Scaling durations by {scale_factor:.2f} (LLM={llm_total:.1f}s, actual={actual_total:.1f}s)")
            
            cumulative = 0.0
            for seg in segments:
                old_duration = seg.get("duration_seconds", 0)
                new_duration = round(old_duration * scale_factor, 2)
                seg["duration_seconds"] = new_duration
                seg["start"] = round(cumulative, 2)
                cumulative += new_duration
            
            section["actual_duration_seconds"] = actual_total
            section["timing_scaled"] = True
        else:
            print(f"[TIMING SYNC] Section {section_id}: Durations match (diff < 5%)")
    
    return presentation

"""
WAN Video Client - Kie.ai WAN 2.6 Text-to-Video API
Updated: January 2026 to use new unified jobs API with getTask endpoint

Uses WAN 2.6 for variable duration support (5, 10, 15 seconds).
API Docs: https://docs.kie.ai/market/wan/2-6-text-to-video

Key API endpoints:
- POST /api/v1/jobs/createTask - Create video generation task
- GET /api/v1/jobs/getTask/{task_id} - Poll task status (preferred over recordInfo)
"""
import os
import time
import json
import random
import hashlib
import requests
from pathlib import Path
from typing import Optional, Set

class WanSafetyError(Exception):
    """Raised when the prompt violates safety policies (NSFW, blocked content)."""
    pass

class WanFatalError(Exception):
    """Raised for non-retryable errors like authentication or payment issues."""
    pass

KIE_API_KEY = os.environ.get("KIE_API_KEY", "")
KIE_API_BASE = "https://api.kie.ai/api/v1"

class WANClient:
    MAX_RETRIES = 3
    RETRY_DELAY = 5
    POLL_INTERVAL = 30  # seconds between status checks (reduced API load)
    MAX_POLL_ATTEMPTS = 60  # 30 minutes max wait (60 * 30s)
    
    # Track video hashes to detect duplicates within a session
    _generated_hashes: Set[str] = set()
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or KIE_API_KEY
        self.base_url = KIE_API_BASE
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_video(self, prompt: str, duration: int = 5, output_path: Optional[str] = None, max_retries: Optional[int] = None, seed: Optional[int] = None) -> Optional[str]:
        """Generate video with retry logic for transient failures and duplicate detection.

        Returns:
            str: Path to generated video file on success
            None: If all retries failed (no placeholder created)
        """
        retries = max_retries if max_retries is not None else self.MAX_RETRIES
        last_error = None
        current_seed = seed if seed is not None else random.randint(1, 999999)

        for attempt in range(retries):
            try:
                result = self._generate_video_attempt(prompt, duration, output_path, seed=current_seed)
                if result and not result.endswith("_placeholder.mp4"):
                    # Check for duplicate video
                    video_hash = self._compute_file_hash(result)
                    if video_hash in WANClient._generated_hashes:
                        print(f"[WAN 2.6] Duplicate video detected (hash={video_hash[:8]}), retrying with new seed...")
                        current_seed = random.randint(1, 999999)
                        continue
                    WANClient._generated_hashes.add(video_hash)
                    print(f"[WAN 2.6] Unique video generated (hash={video_hash[:8]})")
                    return result
                last_error = "Placeholder generated instead of real video"
            except Exception as e:
                last_error = str(e)
                print(f"[WAN 2.6] Attempt {attempt + 1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    print(f"[WAN 2.6] Retrying in {self.RETRY_DELAY}s with new seed...")
                    current_seed = random.randint(1, 999999)
                    time.sleep(self.RETRY_DELAY)

        # FIX: Return None instead of placeholder - let caller mark as failed
        print(f"[WAN 2.6] All {retries} attempts failed. Error: {last_error}")
        return None
    
    def _compute_file_hash(self, file_path: str) -> str:
        """Compute MD5 hash of a file for duplicate detection."""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    @classmethod
    def reset_hash_cache(cls):
        """Reset the hash cache for a new generation session."""
        cls._generated_hashes.clear()
        print("[WAN 2.6] Hash cache cleared for new session")
    
    def _generate_video_attempt(self, prompt: str, duration: int = 5, output_path: Optional[str] = None, seed: Optional[int] = None) -> str:
        """
        Single attempt to generate video using new Kie.ai unified jobs API.
        
        Uses WAN 2.6 for variable duration support (5, 10, 15 seconds).
        
        API format (2026):
        POST /api/v1/jobs/createTask
        {
            "model": "wan/2-6-text-to-video",
            "input": {
                "prompt": "...",
                "duration": "5",  // "5", "10", or "15"
                "resolution": "720p",
                "seed": 12345,  // For reproducibility/uniqueness
                "aspect_ratio": "16:9",
                "negative_prompt": "blurry, low quality, distorted"
            }
        }
        
        Status polling: GET /api/v1/jobs/getTask/{task_id}
        """
        if not self.api_key:
            print("[WAN 2.6] No API key configured - cannot generate video")
            return None
        
        # Truncate prompt to 800 chars max
        prompt = self._truncate_prompt(prompt, max_chars=800)
        
        # Normalize duration to valid WAN 2.6 values: 5, 10, or 15 seconds
        valid_durations = [5, 10, 15]
        if duration not in valid_durations:
            if duration <= 7:
                normalized_duration = 5
            elif duration <= 12:
                normalized_duration = 10
            else:
                normalized_duration = 15
            print(f"[WAN 2.6] Normalizing duration {duration}s -> {normalized_duration}s")
        else:
            normalized_duration = duration
        
        # Use provided seed or generate random one for uniqueness
        effective_seed = seed if seed is not None else random.randint(1, 999999)
        
        # Prepare request payload per new API spec - using WAN 2.6 for duration support
        payload = {
            "model": "wan/2-6-text-to-video",
            "input": {
                "prompt": prompt,
                "duration": str(normalized_duration),
                "resolution": "720p",
                "seed": effective_seed,
                "aspect_ratio": "16:9",
                "negative_prompt": "blurry, low quality, distorted, text overlay, watermark"
            }
        }
        
        print(f"[WAN 2.6] Creating task (duration={normalized_duration}s, seed={effective_seed}): {prompt[:80]}...")
        
        try:
            # Step 1: Create the task
            create_response = requests.post(
                f"{self.base_url}/jobs/createTask",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            print(f"[WAN 2.6] Create response status: {create_response.status_code}")
            
            # --- ERROR MAPPING ---
            if create_response.status_code in [422, 403, 451]:
                raise WanSafetyError(f"Safety/Policy Violation ({create_response.status_code}): {create_response.text}")
                
            if create_response.status_code in [401, 402, 404]:
                raise WanFatalError(f"Fatal API Error ({create_response.status_code}): {create_response.text}")
                
            if create_response.status_code == 400:
                err_text = create_response.text.lower()
                if "nsfw" in err_text or "policy" in err_text or "safety" in err_text:
                    raise WanSafetyError(f"Safety Violation (400): {create_response.text}")
                else:
                    raise WanFatalError(f"Bad Request (400): {create_response.text}")
            # ---------------------

            if create_response.status_code != 200:
                error_text = create_response.text[:500] if create_response.text else "No response body"
                raise Exception(f"API creation failed: {create_response.status_code} - {error_text}")
            
            result = create_response.json()
            
            if result.get("code") != 200:
                raise Exception(f"API error: {result.get('msg', result.get('message', 'Unknown error'))}")
            
            task_id = result.get("data", {}).get("taskId")
            
            if not task_id:
                raise Exception(f"No task ID returned from API. Response: {result}")
            
            print(f"[WAN 2.6] Task created: {task_id}")
            
            # Step 2: Poll for completion using unified recordInfo endpoint
            video_url = self._poll_task_status(task_id)
            
            if not video_url:
                raise Exception("Task completed but no video URL returned")
            
            # Step 3: Download the video
            return self._download_video(video_url, output_path)
            
        except (WanSafetyError, WanFatalError) as e:
            print(f"[WAN 2.6] CRITICAL ERROR: {e}")
            raise e # Propagate these up
            
        except requests.exceptions.Timeout:
            raise Exception("API request timed out")
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"Connection error: {e}")
        except Exception as e:
            raise Exception(f"WAN API error: {e}")
    
    def _poll_task_status(self, task_id: str) -> Optional[str]:
        """
        Poll task status using /jobs/getTask/{task_id} endpoint (preferred method).
        
        Response format:
        {
            "task_id": "abc123",
            "status": "success",  // waiting, generating, success, failed
            "video_url": "https://cdn.kie.ai/output/video.mp4"
        }
        
        Falls back to /jobs/recordInfo if getTask fails.
        """
        print(f"[WAN 2.6] Polling task status for {task_id}...")
        
        for attempt in range(self.MAX_POLL_ATTEMPTS):
            try:
                # Try new getTask endpoint first (preferred per latest docs)
                status_response = requests.get(
                    f"{self.base_url}/jobs/getTask/{task_id}",
                    headers=self.headers,
                    timeout=30
                )
                
                # If getTask returns 404 or error, fallback to recordInfo
                if status_response.status_code == 404:
                    status_response = requests.get(
                        f"{self.base_url}/jobs/recordInfo",
                        headers=self.headers,
                        params={"taskId": task_id},
                        timeout=30
                    )
                
                if status_response.status_code != 200:
                    print(f"[WAN 2.6] Status check failed: {status_response.status_code}")
                    time.sleep(self.POLL_INTERVAL)
                    continue
                
                status_result = status_response.json()
                
                # Handle both response formats
                # New format: {"task_id": "...", "status": "...", "video_url": "..."}
                # Old format: {"code": 200, "data": {"state": "...", "resultJson": "..."}}
                
                if "status" in status_result:
                    # New getTask format
                    state = status_result.get("status", "")
                    print(f"[WAN 2.6] Poll {attempt + 1}/{self.MAX_POLL_ATTEMPTS}: status={state}")
                    
                    if state == "success":
                        video_url = status_result.get("video_url")
                        if video_url:
                            print(f"[WAN 2.6] Video ready: {video_url[:80]}...")
                            return video_url
                        else:
                            raise Exception("Success status but no video_url found")
                    elif state == "failed":
                        msg = status_result.get('message', 'Unknown error')
                        err_text = msg.lower()
                        if any(k in err_text for k in ["nsfw", "policy", "safety", "flagged", "violation"]):
                            raise WanSafetyError(f"Safety Violation in Polling: {msg}")
                        raise Exception(f"Generation failed: {msg}")
                    elif state in ["waiting", "generating"]:
                        pass
                    else:
                        print(f"[WAN 2.6] Unknown status: {state}")
                else:
                    # Old recordInfo format (fallback)
                    if status_result.get("code") != 200:
                        print(f"[WAN 2.6] Status API error: {status_result.get('msg', 'Unknown')}")
                        time.sleep(self.POLL_INTERVAL)
                        continue
                    
                    data = status_result.get("data", {})
                    state = data.get("state", "")
                    
                    print(f"[WAN 2.6] Poll {attempt + 1}/{self.MAX_POLL_ATTEMPTS}: state={state}")
                    
                    if state == "success":
                        result_json_str = data.get("resultJson", "{}")
                        try:
                            result_json = json.loads(result_json_str) if isinstance(result_json_str, str) else result_json_str
                            result_urls = result_json.get("resultUrls", [])
                            if result_urls:
                                print(f"[WAN 2.6] Video ready: {result_urls[0][:80]}...")
                                return result_urls[0]
                            else:
                                raise Exception("Success state but no resultUrls found")
                        except json.JSONDecodeError as e:
                            raise Exception(f"Failed to parse resultJson: {e}")
                    
                    elif state == "fail":
                        fail_msg = data.get("failMsg", "Unknown error")
                        fail_code = data.get("failCode", "")
                        err_text = fail_msg.lower()
                        if any(k in err_text for k in ["nsfw", "policy", "safety", "flagged", "violation"]):
                            raise WanSafetyError(f"Safety Violation in Polling [{fail_code}]: {fail_msg}")
                        raise Exception(f"Generation failed: [{fail_code}] {fail_msg}")
                    
                    elif state in ["waiting", "queuing", "generating"]:
                        pass
                    else:
                        print(f"[WAN 2.6] Unknown state: {state}")
                
            except requests.exceptions.RequestException as e:
                print(f"[WAN 2.6] Poll request failed: {e}")
            
            time.sleep(self.POLL_INTERVAL)
        
        raise Exception(f"Task timed out after {self.MAX_POLL_ATTEMPTS * self.POLL_INTERVAL}s")
    
    def _download_video(self, video_url: str, output_path: Optional[str]) -> str:
        """Download video from URL to local file."""
        print(f"[WAN 2.6] Downloading video...")
        
        response = requests.get(video_url, stream=True, timeout=120)
        if response.status_code == 200:
            output_path = output_path or f"wan_video_{int(time.time())}.mp4"
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[WAN 2.6] Video saved to: {output_path}")
            return output_path
        raise Exception(f"Failed to download video: {response.status_code}")
    
    def _generate_placeholder(self, prompt: str, duration: int, output_path: Optional[str]) -> str:
        """Generate placeholder video when API fails or is not configured."""
        try:
            try:
                from moviepy import ColorClip  # moviepy 2.x
            except ImportError:
                from moviepy.editor import ColorClip  # moviepy 1.x
            
            output_path = output_path or f"placeholder_{int(time.time())}.mp4"
            
            bg = ColorClip(size=(1280, 720), color=(255, 0, 0), duration=1)  # 1-sec RED placeholder for easy detection
            
            bg.write_videofile(
                output_path,
                fps=24,
                codec="libx264",
                audio=False,
                logger=None
            )
            
            bg.close()
            print(f"[WAN 2.2] Placeholder saved to: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Placeholder generation error: {e}")
            return self._create_ffmpeg_video(output_path, duration)
    
    def _create_ffmpeg_video(self, output_path: Optional[str], duration: int) -> str:
        """Fallback: create video using ffmpeg directly."""
        import subprocess
        
        output_path = output_path or f"minimal_{int(time.time())}.mp4"
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=0x1e3c72:s=1280x720:d={duration}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            output_path
        ]
        subprocess.run(cmd, capture_output=True)
        return output_path
    
    def _truncate_prompt(self, prompt: str, max_chars: int = 800) -> str:
        """Truncate prompt to max_chars at sentence boundary if possible."""
        if len(prompt) <= max_chars:
            return prompt
        
        truncated = prompt[:max_chars]
        last_period = truncated.rfind('.')
        if last_period > max_chars * 0.6:
            truncated = truncated[:last_period + 1]
        
        print(f"[WAN 2.2] Prompt truncated from {len(prompt)} to {len(truncated)} chars")
        return truncated

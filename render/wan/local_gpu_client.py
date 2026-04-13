"""
Local GPU Video Client — `69.197.145.4:9090`

Used for non-biology/anatomy video generation (general scenes, etc.)
Routing decision is made by the Director LLM at generation time via `use_local_gpu` field.

API Endpoints:
  GET  /health           → Health check
  POST /generate         → Submit job
  GET  /status/<job_id>  → Poll status {"status": "pending|processing|completed|failed"}
  GET  /download/<job_id>→ Download completed video
  POST /upload           → Upload image/audio (returns token for image_start_token)
"""

import os
import time
import requests
import logging
import base64
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

LOCAL_GPU_URL = os.environ.get("LOCAL_GPU_URL", "http://69.197.145.4:9090")
LOCAL_GPU_API_KEY = os.environ.get("LOCAL_GPU_API_KEY", "")

POLL_INTERVAL = 30  # seconds between status polls
MAX_POLL_ATTEMPTS = 120  # 120 * 30s = 60 min (1 hour) max


class LocalGPUClient:
    """Client for local GPU video generation server."""

    def upload_file(self, file_path: str) -> Optional[str]:
        """
        Upload an image/audio file to get a token for generation.

        POST /upload - multipart/form-data with file field
        Returns token string that can be used in image_start_token

        Args:
            file_path: Path to image (.jpg, .png, .webp) or audio (.wav, .mp3)

        Returns:
            Token string or None on failure
        """
        try:
            with open(file_path, "rb") as f:
                files = {"file": (Path(file_path).name, f)}
                response = requests.post(
                    f"{self.base_url}/upload", files=files, headers=self.headers, timeout=60
                )

            if response.status_code != 200:
                logger.error(
                    f"[LocalGPU] Upload failed: {response.status_code} - {response.text[:200]}"
                )
                return None

            data = response.json()
            # API returns token in different ways - check for common keys
            token = (
                data.get("token") or data.get("image_token") or data.get("file_token")
            )

            if token:
                logger.info(f"[LocalGPU] File uploaded, token: {token[:20]}...")
                return token

            logger.error(f"[LocalGPU] No token in upload response: {data}")
            return None

        except Exception as e:
            logger.error(f"[LocalGPU] Upload error: {e}")
            return None

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or LOCAL_GPU_URL).rstrip("/")
        self.headers = {"x-api-key": LOCAL_GPU_API_KEY} if LOCAL_GPU_API_KEY else {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Quick health check — returns True if server is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/health", headers=self.headers, timeout=5)
            if resp.status_code == 200:
                logger.info("[LocalGPU] Server is available")
                return True
            logger.warning(f"[LocalGPU] Health check returned {resp.status_code}")
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"[LocalGPU] Server unreachable: {e}")
            return False

    def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        output_path: Optional[str] = None,
        image_path: Optional[str] = None,
        image_path_end: Optional[str] = None,
        aspect_ratio: str = "16:9",
    ) -> Optional[str]:
        """
        Generate a video on the local GPU server.

        Args:
            prompt: Text prompt for video generation
            duration: Video duration in seconds
            output_path: Where to save the video
            image_path: Optional start frame image for image-to-video
            image_path_end: Optional end frame image for image-to-video (creates smooth transition)

        Returns:
            str: Path to downloaded .mp4 file on success
            None: On failure (caller should fallback to Kie.ai WAN)
        """
        # V2.6 IDEMPOTENT: Skip if valid file already exists
        if output_path:
            existing = Path(output_path)
            if existing.exists() and existing.stat().st_size > 10000:
                print(
                    f"[LocalGPU] SKIP: Valid file already exists ({existing.stat().st_size // 1024}KB): {output_path}"
                )
                return output_path

        # Read image for image-to-video if provided
        image_token = None
        if image_path and Path(image_path).exists():
            # Upload start frame to get token
            print(f"[LocalGPU] Uploading start-frame image: {image_path}")
            image_token = self.upload_file(image_path)
            if not image_token:
                logger.error("[LocalGPU] Failed to upload start image for i2v")
                return None

        # Upload end frame if provided (non-fatal if it fails)
        image_end_token = None
        if image_path_end and Path(image_path_end).exists():
            print(f"[LocalGPU] Uploading end-frame image: {image_path_end}")
            image_end_token = self.upload_file(image_path_end)
            if not image_end_token:
                logger.warning("[LocalGPU] Failed to upload end image — continuing with start frame only")

        try:
            print(f"[LocalGPU] Submitting job: {prompt[:80]}...")

            # Step 2: Submit job
            job_id = self._submit_job(prompt, duration, image_token, image_end_token, aspect_ratio)
            if not job_id:
                return None

            print(f"[LocalGPU] Job submitted: {job_id}")

            # Step 2: Poll until done
            if not self._wait_for_completion(job_id):
                return None

            # Step 3: Download video
            return self._download_video(job_id, output_path)

        except Exception as e:
            logger.error(f"[LocalGPU] generate_video failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _submit_job(
        self, prompt: str, duration: int,
        image_token: str = None, image_end_token: str = None,
        aspect_ratio: str = "16:9",
    ) -> Optional[str]:
        """POST /generate — returns job_id or None."""
        try:
            # Wan2GP API uses video_length (frames) not duration (seconds)
            # Default 25fps, so 5 seconds = 125 frames
            video_length = duration * 25  # Convert seconds to frames

            payload = {
                "prompt": prompt,
                "video_length": video_length,
                "resolution": {"16:9": "704x480", "9:16": "480x864"}.get(aspect_ratio, "704x480"),
                "model": "ltx23_distilled_q6",
                "seed": 42,
            }

            # Add start-frame token for image-to-video
            if image_token:
                payload["image_start_token"] = image_token

            # Add end-frame token for smooth start-to-end transition
            if image_end_token:
                payload["image_end_token"] = image_end_token

            resp = requests.post(
                f"{self.base_url}/generate",
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            if resp.status_code != 200:
                logger.error(
                    f"[LocalGPU] Submit failed: {resp.status_code} — {resp.text[:200]}"
                )
                return None

            data = resp.json()
            job_id = data.get("job_id")
            if not job_id:
                logger.error(f"[LocalGPU] No job_id in response: {data}")
                return None
            return job_id

        except requests.exceptions.RequestException as e:
            logger.error(f"[LocalGPU] Submit request error: {e}")
            return None

    def _wait_for_completion(self, job_id: str) -> bool:
        """Poll GET /status/<job_id> until completed or failed."""
        for attempt in range(MAX_POLL_ATTEMPTS):
            try:
                resp = requests.get(
                    f"{self.base_url}/status/{job_id}",
                    headers=self.headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    logger.warning(
                        f"[LocalGPU] Poll {attempt + 1}: status {resp.status_code}"
                    )
                    time.sleep(POLL_INTERVAL)
                    continue

                data = resp.json()
                status = data.get("status", "unknown")
                print(f"[LocalGPU] Poll {attempt + 1}/{MAX_POLL_ATTEMPTS}: {status}")

                if status == "completed":
                    return True
                elif status == "failed":
                    msg = data.get("error", "Unknown error")
                    logger.error(f"[LocalGPU] Job failed: {msg}")
                    return False
                # pending / processing — continue polling

            except requests.exceptions.RequestException as e:
                logger.warning(f"[LocalGPU] Poll request error: {e}")

            time.sleep(POLL_INTERVAL)

        logger.error(
            f"[LocalGPU] Job {job_id} timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL}s"
        )
        return False

    def _download_video(self, job_id: str, output_path: Optional[str]) -> Optional[str]:
        """GET /download/<job_id> — save video to output_path."""
        try:
            resp = requests.get(
                f"{self.base_url}/download/{job_id}",
                stream=True,
                headers=self.headers,
                timeout=120,
            )
            if resp.status_code != 200:
                logger.error(f"[LocalGPU] Download failed: {resp.status_code}")
                return None

            out = output_path or f"local_gpu_{job_id}_{int(time.time())}.mp4"
            Path(out).parent.mkdir(parents=True, exist_ok=True)

            with open(out, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"[LocalGPU] Video saved: {out}")
            return out

        except requests.exceptions.RequestException as e:
            logger.error(f"[LocalGPU] Download request error: {e}")
            return None

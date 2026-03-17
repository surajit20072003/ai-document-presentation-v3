"""
Local GPU Video Client — `69.197.145.4:8000`

Used for non-biology/anatomy video generation (general scenes, etc.)
Routing decision is made by the Director LLM at generation time via `use_local_gpu` field.

API Endpoints:
  GET  /health           → Health check
  POST /generate         → Submit job {"prompt": "...", "duration": 5}
  GET  /status/<job_id>  → Poll status {"status": "pending|processing|completed|failed"}
  GET  /download/<job_id>→ Download completed video
"""

import os
import time
import requests
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

LOCAL_GPU_URL = os.environ.get("LOCAL_GPU_URL", "http://69.197.145.4:8000")

POLL_INTERVAL = 30  # seconds between status polls
MAX_POLL_ATTEMPTS = 120  # 120 * 30s = 60 min (1 hour) max


class LocalGPUClient:
    """Client for local GPU video generation server."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or LOCAL_GPU_URL).rstrip("/")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Quick health check — returns True if server is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
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
    ) -> Optional[str]:
        """
        Generate a video on the local GPU server.

        Returns:
            str: Path to downloaded .mp4 file on success
            None: On failure (caller should fallback to Kie.ai WAN)
        """
        # V2.6 IDEMPOTENT: Skip if valid file already exists (mirrors wan_runner.py behaviour)
        if output_path:
            existing = Path(output_path)
            if existing.exists() and existing.stat().st_size > 10000:
                print(
                    f"[LocalGPU] SKIP: Valid file already exists ({existing.stat().st_size // 1024}KB): {output_path}"
                )
                return output_path

        try:
            print(f"[LocalGPU] Submitting job: {prompt[:80]}...")

            # Step 1: Submit job
            job_id = self._submit_job(prompt, duration)
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

    def _submit_job(self, prompt: str, duration: int) -> Optional[str]:
        """POST /generate — returns job_id or None."""
        try:
            resp = requests.post(
                f"{self.base_url}/generate",
                json={"prompt": prompt, "duration": duration},
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

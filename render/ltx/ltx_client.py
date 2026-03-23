"""
Wan2GP Video Client - Wan2GP API (Self-Hosted/Custom)

API Structure (Wan2GP):
- POST /generate
- GET /status/{job_id}
- GET /download/{job_id}
"""

import os
import time
import requests
from typing import Optional
from pathlib import Path

WAN_BASE_URL = os.environ.get("WAN_BASE_URL", "http://69.197.145.4:9090")
LOCAL_GPU_API_KEY = os.environ.get("LOCAL_GPU_API_KEY", "")


class LtxClient:
    POLL_INTERVAL = 5
    MAX_POLL_ATTEMPTS = 120  # 10 minutes max

    def __init__(self):
        self.base_url = WAN_BASE_URL.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        if LOCAL_GPU_API_KEY:
            self.headers["x-api-key"] = LOCAL_GPU_API_KEY

    def generate_video(
        self,
        prompt: str,
        width: int = 704,
        height: int = 480,
        num_frames: int = 25,
        frame_rate: int = 25,
        steps: int = 10,
        guidance_scale: float = 3.0,
        seed: int = 42,
        output_path: Optional[str] = None,
        duration: Optional[int] = None,
    ) -> str:
        """
        Generate a video using Wan2GP API.
        """
        if duration is not None:
            num_frames = int(duration * frame_rate)
            print(
                f"[WAN] Dynamic duration requested: {duration}s -> {num_frames} frames at {frame_rate}fps"
            )

        print(f"[WAN] Requesting video: {prompt[:60]}...")

        # Wan2GP API uses video_length (frames) and resolution (WxH)
        resolution = f"{width}x{height}"

        payload = {
            "prompt": prompt,
            "resolution": resolution,
            "video_length": num_frames,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "seed": seed,
        }

        try:
            # 1. Submit Job - Wan2GP uses /generate endpoint
            response = requests.post(
                f"{self.base_url}/generate",
                headers=self.headers,
                json=payload,
                timeout=30,
            )

            if response.status_code != 200:
                try:
                    err_data = response.json()
                    err_msg = err_data.get("detail") or err_data
                except:
                    err_msg = response.text[:200]
                raise Exception(f"Wan2GP API Error {response.status_code}: {err_msg}")

            data = response.json()
            job_id = data.get("job_id")
            if not job_id:
                raise Exception(f"No job_id returned: {data}")

            print(f"[WAN] Job submitted: {job_id}")

            # 2. Poll Status - Wan2GP uses /status/{job_id}
            video_url = self._poll_status(job_id)

            # 3. Download - Wan2GP uses /download/{job_id}
            return self._download_video(job_id, output_path)

        except Exception as e:
            raise Exception(f"Wan2GP Generation Failed: {e}")

    def _poll_status(self, job_id: str) -> str:
        print(f"[WAN] Polling status for {job_id}...")
        for _ in range(self.MAX_POLL_ATTEMPTS):
            try:
                response = requests.get(
                    f"{self.base_url}/status/{job_id}",
                    headers=self.headers,
                    timeout=10,
                )

                if response.status_code != 200:
                    print(f"[WAN] Poll failed: {response.status_code}")
                    time.sleep(self.POLL_INTERVAL)
                    continue

                data = response.json()
                status = data.get("status")

                if status == "completed":
                    # Wan2GP returns download URL separately via /download/{job_id}
                    # Just return job_id, download will handle it
                    print(f"[WAN] Job completed: {job_id}")
                    return job_id

                elif status == "failed":
                    raise Exception(
                        f"Job failed: {data.get('error') or data.get('detail')}"
                    )
                elif status in ["processing", "pending", "queued", "running"]:
                    print(f"[WAN] Status: {status}")
                else:
                    print(f"[WAN] Unknown status: {status}")

            except Exception as e:
                print(f"[WAN] Poll error: {e}")

            time.sleep(self.POLL_INTERVAL)

        raise Exception("Polling timed out")

    def _download_video(self, job_id: str, output_path: Optional[str]) -> str:
        if not output_path:
            output_path = f"wan_{int(time.time())}.mp4"

        print(f"[WAN] Downloading from /download/{job_id}...")

        # Wan2GP uses /download/{job_id} endpoint
        response = requests.get(
            f"{self.base_url}/download/{job_id}", headers=self.headers, stream=True
        )

        if response.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[WAN] Saved to {output_path}")
            return output_path
        else:
            raise Exception(
                f"Download failed: {response.status_code} - {response.text[:200]}"
            )

    def generate_video_from_image(
        self,
        prompt: str,
        image_path: str,
        output_path: Optional[str] = None,
        width: int = 704,
        height: int = 480,
        num_frames: int = 375,  # 15 seconds at 25fps
        frame_rate: int = 25,
        steps: int = 10,
        guidance_scale: float = 3.0,
        seed: int = 42,
        duration: Optional[int] = None,
    ) -> str:
        """
        Generate a video from a reference image using Wan2GP API.

        The image is uploaded first, then token is used for generation.

        Args:
            prompt: Text description for video animation
            image_path: Path to the reference PNG image
            output_path: Where to save the output video
            width: Video width
            height: Video height
            num_frames: Number of frames to generate
            frame_rate: Frames per second
            steps: Generation steps
            guidance_scale: CFG scale
            seed: Random seed
            duration: If provided, overrides num_frames

        Returns:
            Path to generated video file
        """
        if duration is not None:
            num_frames = int(duration * frame_rate)
            print(
                f"[WAN-I2V] Dynamic duration: {duration}s -> {num_frames} frames at {frame_rate}fps"
            )

        print(f"[WAN-I2V] Requesting video from image: {prompt[:60]}...")
        print(f"[WAN-I2V] Reference image: {image_path}")

        # Step 1: Upload image to get token
        try:
            with open(image_path, "rb") as f:
                files = {"file": (Path(image_path).name, f)}
                response = requests.post(
                    f"{self.base_url}/upload", files=files, timeout=60
                )

            if response.status_code != 200:
                raise Exception(
                    f"Upload failed: {response.status_code} - {response.text[:200]}"
                )

            data = response.json()
            image_token = data.get("token") or data.get("image_token")
            if not image_token:
                raise Exception(f"No token in upload response: {data}")

            print(f"[WAN-I2V] Image uploaded, token received")

        except Exception as e:
            raise Exception(f"Failed to upload image: {e}")

        # Build payload with token using correct Wan2GP parameters
        resolution = f"{width}x{height}"

        payload = {
            "prompt": prompt,
            "image_start_token": image_token,  # Token from /upload
            "resolution": resolution,
            "video_length": num_frames,  # Frames, not seconds
            "steps": steps,
            "guidance_scale": guidance_scale,
            "seed": seed,
            "image_prompt_type": "image",  # Tell API this is image-to-video
        }

        try:
            # 1. Submit Job
            response = requests.post(
                f"{self.base_url}/generate",
                headers=self.headers,
                json=payload,
                timeout=60,  # Longer timeout for i2v
            )

            if response.status_code != 200:
                try:
                    err_data = response.json()
                    err_msg = err_data.get("detail") or err_data
                except:
                    err_msg = response.text[:200]
                raise Exception(
                    f"Wan2GP I2V API Error {response.status_code}: {err_msg}"
                )

            data = response.json()
            job_id = data.get("job_id")
            if not job_id:
                raise Exception(f"No job_id returned: {data}")

            print(f"[WAN-I2V] Job submitted: {job_id}")

            # 2. Poll Status
            self._poll_status(job_id)

            # 3. Download
            return self._download_video(job_id, output_path)

        except Exception as e:
            raise Exception(f"Wan2GP Image-to-Video Failed: {e}")

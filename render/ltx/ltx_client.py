"""
LTX Video Client - LTX Video API (Self-Hosted/Custom)

API Structure (based on tests/test_self_text2video_api.py):
- POST /api/generate/text-to-video
- GET /api/job/{job_id}
- GET /api/videos/list
"""
import os
import time
import requests
from typing import Optional

LTX_BASE_URL = os.environ.get("LTX_BASE_URL", "http://69.197.176.2:8000")

class LtxClient:
    POLL_INTERVAL = 5
    MAX_POLL_ATTEMPTS = 120 # 10 minutes max
    
    def __init__(self):
        self.base_url = LTX_BASE_URL.rstrip('/')
        # No auth headers required based on test script
        self.headers = {
            "Content-Type": "application/json"
        }

    def generate_video(self, prompt: str, width: int = 704, height: int = 480, 
                       num_frames: int = 25, frame_rate: int = 25, steps: int = 10,
                       guidance_scale: float = 3.0, seed: int = 42,
                       output_path: Optional[str] = None) -> str:
        """
        Generate a video using LTX API.
        """
        print(f"[LTX] Requesting video: {prompt[:60]}...")
        
        payload = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_frames": num_frames,
            "frame_rate": frame_rate,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "seed": seed
        }
        
        try:
            # 1. Submit Job
            response = requests.post(
                f"{self.base_url}/api/generate/text-to-video",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                # Try to get error details
                try:
                    err_data = response.json()
                    err_msg = err_data.get('detail') or err_data
                except:
                    err_msg = response.text[:200]
                raise Exception(f"LTX API Error {response.status_code}: {err_msg}")
                
            data = response.json()
            job_id = data.get("job_id")
            if not job_id:
                 raise Exception(f"No job_id returned: {data}")
                 
            print(f"[LTX] Job submitted: {job_id}")
            
            # 2. Poll Status
            video_url = self._poll_status(job_id)
            
            # 3. Download
            return self._download_video(video_url, output_path)

        except Exception as e:
            raise Exception(f"LTX Generation Failed: {e}")

    def _poll_status(self, job_id: str) -> str:
        print(f"[LTX] Polling status for {job_id}...")
        for _ in range(self.MAX_POLL_ATTEMPTS):
            try:
                response = requests.get(
                    f"{self.base_url}/api/job/{job_id}",
                    headers=self.headers,
                    timeout=10
                )
                
                if response.status_code != 200:
                    print(f"[LTX] Poll failed: {response.status_code}")
                    time.sleep(self.POLL_INTERVAL)
                    continue
                    
                data = response.json()
                status = data.get("status")
                
                if status == "completed":
                    # Determine where URL is kept. Test script uses 'status' check but doesn't explicitly look for url in same call?
                    # Wait, test script just prints status. It doesn't fetch url.
                    # But GET /api/job/{id} typically returns result info.
                    # Let's assume result url is in data. If not, we might need another call or logic.
                    # Commonly: data['output_url'], data['url'], or data['result_url'].
                    # Re-checking test script... it doesn't show fetching the URL! 
                    # Use typical patterns. If generic 'completed' status, look for 'output' or 'video_url'.
                    # Or check /api/videos/list?
                    # Let's dump data to debug if key not found.
                    
                    url = data.get("output_url") or data.get("video_url") or data.get("url") or data.get("result_url") or data.get("output_path")
                    
                    # If direct URL not found, check if there's a specific 'output' object
                    if not url and "output" in data:
                        url = data["output"].get("url") or data["output"].get("video_url")
                        
                    if not url:
                         print(f"[LTX] Completed but URL not apparent in keys: {list(data.keys())}")
                         # Fallback: maybe it's constructed from ID? Or check /api/videos/list filtered?
                         # For now, raise specific error to debug.
                         raise Exception(f"Completed but no URL found. Data keys: {list(data.keys())}")
                         
                    return url
                    
                elif status == "failed":
                    raise Exception(f"Job failed: {data.get('error') or data.get('detail')}")
                elif status in ["processing", "pending", "queued", "running"]:
                    pass
                else:
                    print(f"[LTX] Unknown status: {status}")
                
            except Exception as e:
                print(f"[LTX] Poll error: {e}")
            
            time.sleep(self.POLL_INTERVAL)
            
        raise Exception("Polling timed out")

    def _download_video(self, url: str, output_path: Optional[str]) -> str:
        if not output_path:
            output_path = f"ltx_{int(time.time())}.mp4"
            
        # Handle relative URLs if any
        if not url.startswith("http"):
             url = f"{self.base_url}{url}" if url.startswith("/") else f"{self.base_url}/{url}"

        print(f"[LTX] Downloading from {url}...")
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[LTX] Saved to {output_path}")
            return output_path
        else:
             raise Exception(f"Download failed: {response.status_code}")

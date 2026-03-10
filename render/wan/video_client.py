"""
Multi-model video generation client for Kie.ai
Supports: Runway Gen-3 Alpha, Veo 3.1 (Google)
"""
import os
import time
import requests
from pathlib import Path
from typing import Optional, Literal

KIE_API_KEY = os.environ.get("KIE_API_KEY", "")
KIE_BASE_URL = "https://api.kie.ai/api/v1"

ModelType = Literal["runway", "veo3", "veo3_fast"]

class VideoClient:
    """Unified video generation client supporting multiple models"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or KIE_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_video(
        self, 
        prompt: str, 
        model: ModelType = "runway",
        duration: int = 5, 
        output_path: Optional[str] = None,
        aspect_ratio: str = "16:9"
    ) -> str:
        """
        Generate video using specified model.
        
        Args:
            prompt: Text description for video generation
            model: "runway" (Gen-3 Alpha), "veo3" (quality), or "veo3_fast" (speed)
            duration: Duration in seconds (5, 8, 10 for Runway; auto for Veo)
            output_path: Where to save the video
            aspect_ratio: "16:9" or "9:16"
        
        Returns:
            Path to generated video file
        """
        if not self.api_key:
            print(f"[{model.upper()}] No API key - generating placeholder")
            return self._generate_placeholder(prompt, duration, output_path)
        
        if model == "runway":
            return self._generate_runway(prompt, duration, output_path, aspect_ratio)
        elif model in ["veo3", "veo3_fast"]:
            return self._generate_veo3(prompt, model, output_path, aspect_ratio)
        else:
            raise ValueError(f"Unknown model: {model}")
    
    def _generate_runway(
        self, 
        prompt: str, 
        duration: int, 
        output_path: Optional[str],
        aspect_ratio: str
    ) -> str:
        """Generate video using Runway Gen-3 Alpha Turbo"""
        valid_durations = [5, 8, 10]
        if duration not in valid_durations:
            duration = 5 if duration <= 6 else (8 if duration <= 9 else 10)
        
        try:
            print(f"[RUNWAY] Generating {duration}s video...")
            print(f"[RUNWAY] Prompt: {prompt[:100]}...")
            
            create_response = requests.post(
                f"{KIE_BASE_URL}/runway/generate",
                headers=self.headers,
                json={
                    "prompt": prompt,
                    "duration": duration,
                    "quality": "720p",
                    "aspectRatio": aspect_ratio,
                    "waterMark": ""
                },
                timeout=30
            )
            
            if create_response.status_code != 200:
                print(f"[RUNWAY] API creation failed: {create_response.status_code}")
                return self._generate_placeholder(prompt, duration, output_path)
            
            result = create_response.json()
            if result.get("code") != 200:
                print(f"[RUNWAY] API error: {result.get('msg', 'Unknown error')}")
                return self._generate_placeholder(prompt, duration, output_path)
            
            task_id = result.get("data", {}).get("taskId")
            if not task_id:
                print("[RUNWAY] No task ID returned")
                return self._generate_placeholder(prompt, duration, output_path)
            
            print(f"[RUNWAY] Task ID: {task_id}")
            return self._poll_runway(task_id, output_path, duration, prompt)
            
        except Exception as e:
            print(f"[RUNWAY] Error: {e}")
            return self._generate_placeholder(prompt, duration, output_path)
    
    def _poll_runway(
        self, 
        task_id: str, 
        output_path: Optional[str], 
        duration: int,
        prompt: str
    ) -> str:
        """Poll Runway task until completion"""
        max_attempts = 60
        for attempt in range(max_attempts):
            try:
                status_response = requests.get(
                    f"{KIE_BASE_URL}/runway/record-detail?taskId={task_id}",
                    headers=self.headers,
                    timeout=30
                )
                
                if status_response.status_code == 200:
                    status_result = status_response.json()
                    if status_result.get("code") == 200:
                        status_data = status_result.get("data", {})
                        state = status_data.get("state", "")
                        
                        if state == "success":
                            video_info = status_data.get("videoInfo", {})
                            video_url = video_info.get("videoUrl")
                            if video_url:
                                print(f"[RUNWAY] Success! Downloading video...")
                                return self._download_video(video_url, output_path)
                        elif state == "fail":
                            fail_msg = status_data.get("failMsg", "Unknown error")
                            print(f"[RUNWAY] Generation failed: {fail_msg}")
                            return self._generate_placeholder(prompt, duration, output_path)
                        elif state in ["wait", "queueing", "generating"]:
                            print(f"[RUNWAY] Status: {state} (attempt {attempt+1}/{max_attempts})")
                
                time.sleep(5)
                
            except Exception as e:
                print(f"[RUNWAY] Poll error: {e}")
                time.sleep(5)
        
        print("[RUNWAY] Generation timed out")
        return self._generate_placeholder(prompt, duration, output_path)
    
    def _generate_veo3(
        self, 
        prompt: str, 
        model: str,
        output_path: Optional[str],
        aspect_ratio: str
    ) -> str:
        """Generate video using Google Veo 3.1"""
        try:
            print(f"[VEO3] Generating video with {model}...")
            print(f"[VEO3] Prompt: {prompt[:100]}...")
            
            create_response = requests.post(
                f"{KIE_BASE_URL}/veo/generate",
                headers=self.headers,
                json={
                    "prompt": prompt,
                    "model": model,
                    "aspectRatio": aspect_ratio
                },
                timeout=30
            )
            
            if create_response.status_code != 200:
                print(f"[VEO3] API creation failed: {create_response.status_code}")
                print(f"[VEO3] Response: {create_response.text[:500]}")
                return self._generate_placeholder(prompt, 8, output_path)
            
            result = create_response.json()
            if result.get("code") != 200:
                print(f"[VEO3] API error: {result.get('msg', 'Unknown error')}")
                return self._generate_placeholder(prompt, 8, output_path)
            
            task_id = result.get("data", {}).get("taskId")
            if not task_id:
                print("[VEO3] No task ID returned")
                return self._generate_placeholder(prompt, 8, output_path)
            
            print(f"[VEO3] Task ID: {task_id}")
            return self._poll_veo3(task_id, output_path, prompt)
            
        except Exception as e:
            print(f"[VEO3] Error: {e}")
            return self._generate_placeholder(prompt, 8, output_path)
    
    def _poll_veo3(
        self, 
        task_id: str, 
        output_path: Optional[str],
        prompt: str
    ) -> str:
        """Poll Veo3 task until completion"""
        max_attempts = 120  # Veo can take longer
        for attempt in range(max_attempts):
            try:
                status_response = requests.get(
                    f"{KIE_BASE_URL}/veo/record-info?taskId={task_id}",
                    headers=self.headers,
                    timeout=30
                )
                
                if status_response.status_code == 200:
                    status_result = status_response.json()
                    if status_result.get("code") == 200:
                        status_data = status_result.get("data", {})
                        success_flag = status_data.get("successFlag", 0)
                        
                        if success_flag == 1:
                            # Success - parse result URLs
                            result_urls_str = status_data.get("resultUrls", "[]")
                            try:
                                import json
                                video_urls = json.loads(result_urls_str)
                                if video_urls and len(video_urls) > 0:
                                    print(f"[VEO3] Success! Downloading video...")
                                    return self._download_video(video_urls[0], output_path)
                            except json.JSONDecodeError:
                                print(f"[VEO3] Failed to parse result URLs: {result_urls_str}")
                        elif success_flag in [2, 3]:
                            print(f"[VEO3] Generation failed (flag={success_flag})")
                            return self._generate_placeholder(prompt, 8, output_path)
                        else:
                            print(f"[VEO3] Generating... (attempt {attempt+1}/{max_attempts})")
                
                time.sleep(5)
                
            except Exception as e:
                print(f"[VEO3] Poll error: {e}")
                time.sleep(5)
        
        print("[VEO3] Generation timed out")
        return self._generate_placeholder(prompt, 8, output_path)
    
    def _download_video(self, video_url: str, output_path: Optional[str]) -> str:
        """Download video from URL"""
        response = requests.get(video_url, stream=True, timeout=120)
        if response.status_code == 200:
            output_path = output_path or f"video_{int(time.time())}.mp4"
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[DOWNLOAD] Saved to {output_path}")
            return output_path
        raise Exception(f"Failed to download video: {response.status_code}")
    
    def _generate_placeholder(self, prompt: str, duration: int, output_path: Optional[str]) -> str:
        """Generate placeholder video when API fails or is not configured."""
        try:
            try:
                from moviepy import ColorClip
            except ImportError:
                from moviepy.editor import ColorClip
            
            output_path = output_path or f"placeholder_{int(time.time())}.mp4"
            
            bg = ColorClip(size=(1280, 720), color=(30, 30, 60), duration=duration)
            
            bg.write_videofile(
                output_path,
                fps=24,
                codec="libx264",
                audio=False,
                logger=None
            )
            
            bg.close()
            print(f"[PLACEHOLDER] Generated {output_path}")
            return output_path
            
        except Exception as e:
            print(f"[PLACEHOLDER] MoviePy error: {e}")
            return self._create_ffmpeg_video(output_path, duration)
    
    def _create_ffmpeg_video(self, output_path: Optional[str], duration: int) -> str:
        """Create minimal video using ffmpeg"""
        import subprocess
        
        output_path = output_path or f"minimal_{int(time.time())}.mp4"
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=0x1e3c72:s=1280x720:d={duration}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            output_path
        ]
        subprocess.run(cmd, capture_output=True)
        print(f"[FFMPEG] Generated {output_path}")
        return output_path


def compare_models(prompt: str, output_dir: str = "comparison") -> dict:
    """
    Generate the same prompt with both Runway and Veo3 for comparison.
    
    Returns dict with paths to both videos.
    """
    from pathlib import Path
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    client = VideoClient()
    results = {}
    
    print("\n" + "="*60)
    print("MODEL COMPARISON TEST")
    print("="*60)
    print(f"Prompt: {prompt[:200]}...")
    print("="*60)
    
    # Generate with Runway
    print("\n[1/2] RUNWAY GEN-3 ALPHA")
    runway_path = str(Path(output_dir) / "runway_output.mp4")
    results["runway"] = client.generate_video(
        prompt=prompt,
        model="runway",
        duration=8,
        output_path=runway_path
    )
    
    # Generate with Veo3
    print("\n[2/2] VEO 3.1 (GOOGLE)")
    veo3_path = str(Path(output_dir) / "veo3_output.mp4")
    results["veo3"] = client.generate_video(
        prompt=prompt,
        model="veo3",
        output_path=veo3_path
    )
    
    print("\n" + "="*60)
    print("COMPARISON COMPLETE")
    print("="*60)
    print(f"Runway: {results['runway']}")
    print(f"Veo3: {results['veo3']}")
    print("="*60)
    
    return results


if __name__ == "__main__":
    # Test with a sample educational prompt
    test_prompt = """
    A stylized Bohr model of a Helium atom appears on a dark background. 
    It has a central nucleus with two red spheres marked '+' and two grey spheres, 
    with two blue spheres marked '-' orbiting it on elliptical paths.
    The two blue electrons animate smoothly along their orbital paths around the nucleus.
    Title at top: 'Matter is made of Atoms'. 
    Label pointing to nucleus: 'Nucleus'. Label pointing to orbiting sphere: 'Electron'.
    """
    
    results = compare_models(test_prompt.strip(), output_dir="model_comparison")
    print(f"\nResults saved to: {results}")

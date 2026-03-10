import os
import json
import logging
from pathlib import Path
from render.wan.wan_client import WANClient
from render.wan.kie_batch_generator import KieBatchGenerator

logger = logging.getLogger(__name__)

class VideoRegenerator:
    """Service to handle video regeneration for failed/corrupt assets."""
    
    def __init__(self, job_dir: str):
        self.job_dir = Path(job_dir)
        self.videos_dir = self.job_dir / "videos"
        self.pres_path = self.job_dir / "presentation.json"
        
    def find_failed_videos(self):
        """Find videos that are missing or corrupt (<10KB placeholder)."""
        failed = []
        if not self.pres_path.exists():
            return []
            
        with open(self.pres_path, "r", encoding="utf-8") as f:
            presentation = json.load(f)
            
        for section in presentation.get("sections", []):
            # Check all beat videos for this section
            beats = section.get("video_prompts", [])
            for beat in beats:
                beat_id = beat.get("beat_id")
                video_file = self.videos_dir / f"{beat_id}.mp4"
                
                status = "ok"
                if not video_file.exists():
                    status = "missing"
                elif video_file.stat().st_size < 10000: # < 10KB
                    status = "corrupt"
                
                if status != "ok":
                    failed.append({
                        "section_id": section.get("section_id"),
                        "beat_id": beat_id,
                        "prompt": beat.get("prompt"),
                        "duration": beat.get("duration_hint", 15),
                        "status": status,
                        "path": str(video_file)
                    })
        return failed

    def regenerate_failed(self):
        """Trigger regeneration for all identified failed videos."""
        failed = self.find_failed_videos()
        if not failed:
            return {"status": "success", "message": "No failed videos found"}
            
        logger.info(f"Regenerating {len(failed)} failed videos for job {self.job_dir.name}")
        batch_gen = KieBatchGenerator()
        
        # Prepare beats for generator
        beats_to_gen = [
            {"beat_id": f["beat_id"], "prompt": f["prompt"], "duration_hint": f["duration"]}
            for f in failed
        ]
        
        results = batch_gen.generate_batch(beats_to_gen, str(self.videos_dir))
        
        # Update presentation.json with new paths (safely)
        from core.renderer_executor import _update_presentation_safely
        for f in failed:
            new_path = results.get(f["beat_id"])
            if new_path:
                _update_presentation_safely(self.pres_path, f["section_id"], new_path, {"status": "success", "topic_results": {f["beat_id"]: new_path}, "beat_video_paths": [new_path]})
                
        return {"status": "success", "regenerated_count": len(results)}

    def regenerate_section(self, section_id: str):
        """Regenerate all WAN videos for a specific section."""
        if not self.pres_path.exists():
            return {"status": "error", "message": "Presentation not found"}
            
        with open(self.pres_path, "r", encoding="utf-8") as f:
            presentation = json.load(f)
            
        target_section = None
        for section in presentation.get("sections", []):
            if str(section.get("section_id")) == str(section_id):
                target_section = section
                break
        
        if not target_section:
            return {"status": "error", "message": f"Section {section_id} not found"}
            
        beats = target_section.get("video_prompts", [])
        if not beats:
            return {"status": "error", "message": "No video prompts found for this section"}
            
        batch_gen = KieBatchGenerator()
        results = batch_gen.generate_batch(beats, str(self.videos_dir))
        
        # Update presentation
        from core.renderer_executor import _update_presentation_safely
        first_path = list(results.values())[0] if results else None
        _update_presentation_safely(self.pres_path, section_id, first_path, {"status": "success", "topic_results": results, "beat_video_paths": list(results.values())})
        
        return {"status": "success", "regenerated_count": len(results)}

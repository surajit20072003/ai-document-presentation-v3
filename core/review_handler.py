"""
Human-in-the-Loop Review Handler

Allows users to manually edit presentation sections and trigger regeneration.
"""

import json
from pathlib import Path
from typing import Dict, List, Any


class ReviewHandler:
    """Handles review submissions and job regeneration."""
    
    def __init__(self, job_dir: Path):
        self.job_dir = Path(job_dir)
        self.presentation_path = self.job_dir / "presentation.json"
        
    def load_presentation(self) -> Dict[str, Any]:
        """Load the current presentation.json."""
        if not self.presentation_path.exists():
            raise FileNotFoundError(f"Presentation not found: {self.presentation_path}")
        
        with open(self.presentation_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def apply_review_edits(self, presentation: Dict[str, Any], edits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply user edits to the presentation.
        
        Args:
            presentation: The current presentation dict
            edits: List of edits, each with:
                - section_id: int
                - narration_text: str (optional)
                - content: dict with structured edits (optional):
                    - explanation_plan: str
                    - visual_beats: list
                    - bullet_items: list
                    - images: list
                    - quiz_data: dict
                    - flashcards: list
        
        Returns:
            Modified presentation dict
        """
        sections = presentation.get("sections", [])
        
        for edit in edits:
            section_id = edit.get("section_id")
            if section_id is None:
                continue
            
            # Find the section (section_id is 1-indexed)
            section = next((s for s in sections if s.get("section_id") == section_id), None)
            if not section:
                continue
            
            modified = False
            
            # Apply narration text changes
            if "narration_text" in edit and edit["narration_text"]:
                narration = section.get("narration", {})
                segments = narration.get("segments", [])
                
                # Update the first segment's text (simplified approach)
                if segments:
                    segments[0]["text"] = edit["narration_text"]
                    modified = True
            
            # Apply structured content edits
            content_edits = edit.get("content", {})
            
            # Explanation plan
            if "explanation_plan" in content_edits:
                section["explanation_plan"] = content_edits["explanation_plan"]
                modified = True
            
            # Visual beats
            if "visual_beats" in content_edits:
                visual_beats = section.get("visual_beats", [])
                for idx, beat_edit in enumerate(content_edits["visual_beats"]):
                    if idx < len(visual_beats):
                        visual_beats[idx]["description"] = beat_edit.get("description", "")
                modified = True
            
            # Bullet items (update visual_content.items in narration segments)
            if "bullet_items" in content_edits:
                narration = section.get("narration", {})
                segments = narration.get("segments", [])
                
                # Find segments with visual_content.items and update them
                bullet_idx = 0
                for seg in segments:
                    vc = seg.get("visual_content", {})
                    if isinstance(vc, dict) and "items" in vc:
                        items = vc.get("items", [])
                        new_items = []
                        for _ in range(len(items)):
                            if bullet_idx < len(content_edits["bullet_items"]):
                                new_items.append(content_edits["bullet_items"][bullet_idx])
                                bullet_idx += 1
                        vc["items"] = new_items
                        modified = True
            
            # Images (update visual_content.image_id and verbatim_content)
            if "images" in content_edits:
                narration = section.get("narration", {})
                segments = narration.get("segments", [])
                
                img_idx = 0
                for seg in segments:
                    vc = seg.get("visual_content", {})
                    if isinstance(vc, dict) and "image_id" in vc:
                        if img_idx < len(content_edits["images"]):
                            img_edit = content_edits["images"][img_idx]
                            vc["image_id"] = img_edit.get("image_id", vc["image_id"])
                            vc["verbatim_content"] = img_edit.get("description", "")
                            img_idx += 1
                            modified = True
            
            # Quiz data
            if "quiz_data" in content_edits:
                section["quiz_data"] = content_edits["quiz_data"]
                modified = True
            
            # Flashcards
            if "flashcards" in content_edits:
                section["flashcards"] = content_edits["flashcards"]
                modified = True
            
            # Mark section for regeneration if modified
            if modified:
                section["_needs_regeneration"] = True
        
        return presentation
    
    def save_presentation(self, presentation: Dict[str, Any]):
        """Save the modified presentation back to disk."""
        with open(self.presentation_path, 'w', encoding='utf-8') as f:
            json.dump(presentation, f, indent=2, ensure_ascii=False)
    
    def get_sections_needing_regeneration(self, presentation: Dict[str, Any]) -> List[int]:
        """Get list of section IDs that need regeneration."""
        sections = presentation.get("sections", [])
        return [
            s.get("section_id") 
            for s in sections 
            if s.get("_needs_regeneration", False)
        ]
    
    def trigger_regeneration(self, section_ids: List[int]) -> Dict[str, Any]:
        """
        Trigger regeneration for specific sections.
        
        This will regenerate:
        - TTS audio
        - Videos (if renderer is video/manim)
        - Avatar (if applicable)
        
        Returns:
            Status dict
        """
        # Import here to avoid circular dependency
        from core.tts_duration import update_durations_simplified
        from core.renderer_executor import render_all_topics
        
        presentation = self.load_presentation()
        
        # Regenerate TTS for modified sections
        try:
            update_durations_simplified(
                presentation,
                output_dir=self.job_dir,
                production_provider="our_tts"
            )
        except Exception as e:
            return {"status": "error", "message": f"TTS regeneration failed: {str(e)}"}
        
        # Regenerate videos for modified sections
        try:
            render_all_topics(
                presentation,
                output_dir=str(self.job_dir),
                dry_run=False,
                skip_wan=False
            )
        except Exception as e:
            return {"status": "error", "message": f"Video regeneration failed: {str(e)}"}
        
        # Save updated presentation
        self.save_presentation(presentation)
        
        return {
            "status": "success",
            "regenerated_sections": section_ids,
            "message": f"Regenerated {len(section_ids)} sections"
        }

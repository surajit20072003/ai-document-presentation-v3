"""
V1.5 Visual Spec Artist Agent (REQ-012)

Takes SectionBlueprint + Narration, outputs visual_beats and segment_enrichments.
Visual content is for SCREEN DISPLAY - extracted from source document.
"""
from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent


class VisualSpecArtistAgent(BaseAgent):
    """
    Visual Spec Artist Agent - Creates visual specifications.
    
    Input: section_blueprint, narration, source_markdown
    Output: section_id, visual_beats, segment_enrichments
    """
    
    name = "VisualSpecArtist"
    system_prompt_file = "visual_spec_artist_system_v1.5.txt"
    user_prompt_file = "visual_spec_artist_user_v1.5.txt"
    output_schema_file = "section_visuals.schema.json"
    model = "google/gemini-2.5-flash"
    temperature = 0.3
    
    def validate_structural(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate visual output structure."""
        errors = []
        
        if "section_id" not in output:
            errors.append("Missing 'section_id'")
        
        if "visual_beats" not in output:
            errors.append("Missing 'visual_beats' array")
        else:
            beats = output.get("visual_beats", [])
            valid_types = ["diagram", "formula", "process", "video_clip", "text_only", "animation"]
            
            for i, beat in enumerate(beats):
                if "beat_id" not in beat:
                    errors.append(f"Beat {i}: missing 'beat_id'")
                elif not isinstance(beat.get("beat_id"), str):
                    errors.append(f"Beat {i}: 'beat_id' must be a string")
                
                if "segment_id" not in beat:
                    errors.append(f"Beat {i}: missing 'segment_id'")
                elif not isinstance(beat.get("segment_id"), int):
                    errors.append(f"Beat {i}: 'segment_id' must be an integer")
                
                if "visual_beat_type" not in beat:
                    errors.append(f"Beat {i}: missing 'visual_beat_type'")
                elif beat.get("visual_beat_type") not in valid_types:
                    errors.append(f"Beat {i}: invalid visual_beat_type '{beat.get('visual_beat_type')}'")
                
                if "description" not in beat:
                    errors.append(f"Beat {i}: missing 'description'")
                elif len(beat.get("description", "")) < 10:
                    errors.append(f"Beat {i}: description too short (min 10 chars)")
        
        if "segment_enrichments" not in output:
            errors.append("Missing 'segment_enrichments' array")
        else:
            enrichments = output.get("segment_enrichments", [])
            valid_text_layer = ["show", "hide", "swap"]
            valid_visual_layer = ["show", "hide", "replace"]
            valid_avatar_layer = ["show", "hide", "gesture_only"]
            
            for i, enrich in enumerate(enrichments):
                if "segment_id" not in enrich:
                    errors.append(f"Enrichment {i}: missing 'segment_id'")
                
                if "visual_content" not in enrich:
                    errors.append(f"Enrichment {i}: missing 'visual_content'")
                
                if "display_directives" not in enrich:
                    errors.append(f"Enrichment {i}: missing 'display_directives'")
                else:
                    dd = enrich.get("display_directives", {})
                    if dd.get("text_layer") not in valid_text_layer:
                        errors.append(f"Enrichment {i}: invalid text_layer")
                    if dd.get("visual_layer") not in valid_visual_layer:
                        errors.append(f"Enrichment {i}: invalid visual_layer")
                    if dd.get("avatar_layer") not in valid_avatar_layer:
                        errors.append(f"Enrichment {i}: invalid avatar_layer")
        
        return len(errors) == 0, errors
    
    def validate_semantic(self, output: Dict[str, Any], input_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate semantic rules for visuals."""
        errors = []
        
        narration = input_data.get("narration", {})
        segments = narration.get("segments", [])
        segment_ids = {s.get("segment_id") for s in segments}
        
        beats = output.get("visual_beats", [])
        for beat in beats:
            if beat.get("segment_id") not in segment_ids:
                errors.append(f"Beat {beat.get('beat_id')}: segment_id {beat.get('segment_id')} not in narration")
        
        enrichments = output.get("segment_enrichments", [])
        enrichment_ids = {e.get("segment_id") for e in enrichments}
        
        for seg_id in segment_ids:
            if seg_id not in enrichment_ids:
                errors.append(f"Missing segment_enrichment for segment_id {seg_id}")
        
        for enrich in enrichments:
            dd = enrich.get("display_directives", {})
            if dd.get("text_layer") == "show" and dd.get("visual_layer") == "show":
                errors.append(f"Segment {enrich.get('segment_id')}: text_layer and visual_layer cannot both be 'show'")
        
        if len(beats) != len(segments):
            errors.append(f"Beat count ({len(beats)}) should match segment count ({len(segments)})")
        
        return len(errors) == 0, errors

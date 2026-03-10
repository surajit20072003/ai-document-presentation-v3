"""
V1.5 Narration Writer Agent (REQ-011)

Takes one SectionBlueprint, outputs narration with segments.
Narration text is for TTS audio ONLY - not screen display.
"""
from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent


class NarrationWriterAgent(BaseAgent):
    """
    Narration Writer Agent - Creates TTS narration for a section.
    
    Input: section_blueprint, source_markdown
    Output: section_id, narration (full_text + segments)
    """
    
    name = "NarrationWriter"
    system_prompt_file = "narration_writer_system_v1.5.txt"
    user_prompt_file = "narration_writer_user_v1.5.txt"
    output_schema_file = "section_narration.schema.json"
    model = "google/gemini-2.5-flash"
    temperature = 0.4
    
    WORD_LIMITS = {
        "intro": (50, 150),
        "summary": (50, 200),
        "content": (100, 300),
        "example": (100, 300),
        "quiz": (50, 250),  # Increased from 200 - quiz sections with multiple questions need more words
        "memory": (30, 100),
        "recap": (150, 350)  # ISS-166: Adjusted for 5 segments x 30-50 words each
    }
    
    REQUIRED_SEGMENTS = {
        "recap": 5  # ISS-166: Recap must have exactly 5 segments to match 5 videos
    }
    
    def validate_structural(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate narration structure."""
        errors = []
        
        if "section_id" not in output:
            errors.append("Missing 'section_id'")
        
        if "narration" not in output:
            errors.append("Missing 'narration' object")
            return False, errors
        
        narration = output.get("narration", {})
        
        if "full_text" not in narration:
            errors.append("Missing 'narration.full_text'")
        
        if "segments" not in narration:
            errors.append("Missing 'narration.segments' array")
            return False, errors
        
        segments = narration.get("segments", [])
        if not isinstance(segments, list) or len(segments) == 0:
            errors.append("'segments' must be a non-empty array")
            return False, errors
        
        segment_ids = []
        for i, seg in enumerate(segments):
            if "segment_id" not in seg:
                errors.append(f"Segment {i}: missing 'segment_id'")
            else:
                segment_ids.append(seg["segment_id"])
            
            if "text" not in seg:
                errors.append(f"Segment {i}: missing 'text'")
            elif len(seg.get("text", "")) < 10:
                errors.append(f"Segment {i}: text too short (min 10 chars)")
            
            if "duration_seconds" not in seg:
                errors.append(f"Segment {i}: missing 'duration_seconds'")
        
        expected_ids = list(range(1, len(segments) + 1))
        if sorted(segment_ids) != expected_ids:
            errors.append(f"segment_ids must be sequential 1 to {len(segments)}, got {segment_ids}")
        
        return len(errors) == 0, errors
    
    def validate_semantic(self, output: Dict[str, Any], input_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate word counts and content quality."""
        errors = []
        
        blueprint = input_data.get("section_blueprint", {})
        section_type = blueprint.get("section_type", "content")
        
        narration = output.get("narration", {})
        full_text = narration.get("full_text", "")
        word_count = len(full_text.split())
        
        min_words, max_words = self.WORD_LIMITS.get(section_type, (50, 300))
        # Allow 10% tolerance on minimum word count (149 vs 150 should pass)
        min_with_tolerance = int(min_words * 0.9)
        
        if word_count < min_with_tolerance:
            errors.append(f"Narration too short for {section_type}: {word_count} words (min {min_words})")
        
        if word_count > max_words * 1.5:
            errors.append(f"Narration too long for {section_type}: {word_count} words (max ~{max_words})")
        
        segments = narration.get("segments", [])
        total_segment_words = sum(len(s.get("text", "").split()) for s in segments)
        
        if abs(total_segment_words - word_count) > 20:
            errors.append(f"Segment word count ({total_segment_words}) doesn't match full_text ({word_count})")
        
        # ISS-166: Validate segment count for section types that require specific counts
        required_count = self.REQUIRED_SEGMENTS.get(section_type)
        if required_count and len(segments) != required_count:
            errors.append(f"{section_type} section must have exactly {required_count} segments (got {len(segments)}) to match video scenes")
        
        return len(errors) == 0, errors

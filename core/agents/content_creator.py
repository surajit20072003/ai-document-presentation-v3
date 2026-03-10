"""
V1.5 ContentCreator Agent - Combined Narration + Visual Specification

Optimization: Combines NarrationWriter + VisualSpecArtist into single LLM call.
This reduces 2 LLM calls per section to 1, with coupled visual+narration output.

V3 Integration:
- Uses persona-based narration (Namaste intro, quizmaster for quiz, etc.)
- Detects Q&A pairs and marks display_format: flashcard
- Ensures avatar always visible
- Word count limits from V3

V1.5.1 Dynamic Budgets:
- Uses budgets from SectionPlanner blueprint instead of fixed limits
- Validates against dynamic budgets for word count and segment count

Output is compatible with existing MergeStep - produces same fields.
"""
import json
from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent, STRONG_MODEL


class ContentCreatorAgent(BaseAgent):
    """
    ContentCreator Agent - Creates coupled narration + visual specs.
    
    Input: section_blueprint, source_markdown, quiz_questions (optional)
    Output: section_id, narration, visual_beats, segment_enrichments
    
    Replaces: NarrationWriterAgent + VisualSpecArtistAgent (2 LLM calls → 1)
    """
    
    name = "ContentCreator"
    previous_system_prompt_file = "content_creator_system_v1.5.txt"
    system_prompt_file = "content_creator_system_v2.5.txt"
    user_prompt_file = "content_creator_user_v2.5.txt"
    output_schema_file = "content_creator.schema.json"
    model = "google/gemini-2.5-flash"
    temperature = 0.5
    structural_retries = 2
    semantic_retries = 2
    
    WORD_LIMITS = {
        "intro": (40, 80),
        "summary": (60, 150),
        "content": (100, 300),
        "example": (100, 300),
        "quiz": (80, 250), # Will likely increase dynamically
        "memory": (30, 100),
        "recap": (150, 350)
    }
    
    SEGMENT_LIMITS = {
        "intro": (1, 1),      # Single greeting segment
        "summary": (1, 2),    # Brief overview only
        "content": (2, 6),    # Group 3-5 concepts per segment, max 6 segments
        "example": (2, 4),    # Group related examples, max 4 segments
        "quiz": (3, 30),      # UPDATED V2.5: dynamic lower bound will be qa_count * 3
        "memory": (3, 3),     # Fixed: 3 flashcards
        "recap": (5, 5)       # Fixed: 5 video scenes
    }
    
    def build_user_prompt(self, **kwargs) -> str:
        """
        V1.5.1: Override to extract budgets from section_blueprint and inject into prompt.
        """
        blueprint = kwargs.get("section_blueprint", {})
        if isinstance(blueprint, str):
            try:
                blueprint = json.loads(blueprint)
            except json.JSONDecodeError:
                blueprint = {}
        
        section_type = blueprint.get("section_type", "content")
        budgets = blueprint.get("budgets", {})
        
        if budgets:
            word_min = budgets.get("word_min", self.WORD_LIMITS.get(section_type, (50, 300))[0])
            word_max = budgets.get("word_max", self.WORD_LIMITS.get(section_type, (50, 300))[1])
            segment_min = budgets.get("segment_min", self.SEGMENT_LIMITS.get(section_type, (2, 5))[0])
            segment_max = budgets.get("segment_max", self.SEGMENT_LIMITS.get(section_type, (2, 5))[1])
            qa_count = budgets.get("qa_count", 0)
            concept_count = budgets.get("concept_count", 0)
        else:
            word_min, word_max = self.WORD_LIMITS.get(section_type, (50, 300))
            segment_min, segment_max = self.SEGMENT_LIMITS.get(section_type, (2, 5))
            qa_count = 0
            concept_count = 0
        
        if section_type == "quiz" and qa_count > 0:
            # V2.5: STRICT 3-Step Dance (Intro, Pause, Reveal) per question
            # So segment count MUST be exactly qa_count * 3
            segment_min = qa_count * 3
            segment_max = qa_count * 3
            # Allow slightly more words per question (intro + reveal explanation)
            word_min = max(word_min, qa_count * 40)
            word_max = max(word_max, qa_count * 80)
        
        kwargs["word_min"] = word_min
        kwargs["word_max"] = word_max
        kwargs["segment_min"] = segment_min
        kwargs["segment_max"] = segment_max
        kwargs["qa_count"] = qa_count
        kwargs["concept_count"] = concept_count
        
        return super().build_user_prompt(**kwargs)
    
    def validate_structural(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate combined output structure."""
        errors = []
        
        if "section_id" not in output:
            errors.append("Missing 'section_id'")
        
        if "narration" not in output:
            errors.append("Missing 'narration' object")
        else:
            narration = output.get("narration", {})
            
            if "full_text" not in narration:
                errors.append("Missing 'narration.full_text'")
            
            if "segments" not in narration:
                errors.append("Missing 'narration.segments' array")
            else:
                segments = narration.get("segments", [])
                if not isinstance(segments, list) or len(segments) == 0:
                    errors.append("'narration.segments' must be a non-empty array")
                else:
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
        
        if "visual_beats" not in output:
            errors.append("Missing 'visual_beats' array")
        else:
            beats = output.get("visual_beats", [])
            valid_types = ["diagram", "formula", "process", "video_clip", "text_only", "animation", "flashcard"]
            
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
            valid_avatar_layer = ["show", "gesture_only"]
            
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
                        errors.append(f"Enrichment {i}: invalid text_layer '{dd.get('text_layer')}'")
                    if dd.get("visual_layer") not in valid_visual_layer:
                        errors.append(f"Enrichment {i}: invalid visual_layer '{dd.get('visual_layer')}'")
                    if dd.get("avatar_layer") not in valid_avatar_layer:
                        errors.append(f"Enrichment {i}: invalid avatar_layer '{dd.get('avatar_layer')}' (must be 'show' or 'gesture_only')")
        
        return len(errors) == 0, errors
    
    def validate_semantic(self, output: Dict[str, Any], input_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate semantic rules for combined output using dynamic budgets."""
        errors = []
        
        # V1.5.1: Handle both dict and JSON string blueprints (same as build_user_prompt)
        blueprint = input_data.get("section_blueprint", {})
        if isinstance(blueprint, str):
            try:
                blueprint = json.loads(blueprint)
            except json.JSONDecodeError:
                blueprint = {}
        
        section_type = blueprint.get("section_type", "content")
        
        # V1.5.1: Use dynamic budgets from blueprint if available, else fallback to fixed limits
        budgets = blueprint.get("budgets", {})
        
        narration = output.get("narration", {})
        full_text = narration.get("full_text", "")
        word_count = len(full_text.split())
        
        # Get word limits from dynamic budgets or fallback to fixed limits
        if budgets:
            min_words = budgets.get("word_min", self.WORD_LIMITS.get(section_type, (50, 300))[0])
            max_words = budgets.get("word_max", self.WORD_LIMITS.get(section_type, (50, 300))[1])
        else:
            min_words, max_words = self.WORD_LIMITS.get(section_type, (50, 300))
        
        # ISS-216: Allow 25% tolerance on minimum word count to prevent false failures
        min_with_tolerance = int(min_words * 0.75)
        if word_count < min_with_tolerance:
            errors.append(f"Narration too short for {section_type}: {word_count} words (min {min_with_tolerance})")
        # Allow 50% overage before failing
        if word_count > max_words * 1.5:
            errors.append(f"Narration too long for {section_type}: {word_count} words (max ~{max_words})")
        
        segments = narration.get("segments", [])
        total_segment_words = sum(len(s.get("text", "").split()) for s in segments)
        if abs(total_segment_words - word_count) > 10:
            errors.append(f"Segment word count ({total_segment_words}) doesn't match full_text ({word_count})")
        
        # Get segment limits from dynamic budgets or fallback to fixed limits
        if budgets:
            min_segs = budgets.get("segment_min", self.SEGMENT_LIMITS.get(section_type, (2, 5))[0])
            max_segs = budgets.get("segment_max", self.SEGMENT_LIMITS.get(section_type, (2, 5))[1])
        else:
            min_segs, max_segs = self.SEGMENT_LIMITS.get(section_type, (2, 5))
        
        if len(segments) < min_segs or len(segments) > max_segs:
            errors.append(f"{section_type} section should have {min_segs}-{max_segs} segments, got {len(segments)}")
        
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
            if dd.get("avatar_layer") == "hide":
                errors.append(f"Segment {enrich.get('segment_id')}: avatar_layer cannot be 'hide' (avatar always visible)")
        
        if len(beats) != len(segments):
            errors.append(f"Beat count ({len(beats)}) should match segment count ({len(segments)})")
        
        if section_type == "intro":
            if not any(word in full_text.lower() for word in ["namaste", "welcome", "hello", "greet"]):
                errors.append("Intro section should start with warm greeting (e.g., 'Namaste students')")
        
        return len(errors) == 0, errors

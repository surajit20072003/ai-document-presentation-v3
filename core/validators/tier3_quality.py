"""
Tier 3 - QUALITY WARNINGS Validator (Non-Blocking)

Purpose: Detect style issues without blocking production.
Tier-3 NEVER fails a job.

Tier-3 checks (warnings only):
- Vague visual language: "clear diagram", "appropriate animation"
- Repetitive phrasing
- Overly generic scene descriptions
- Mild redundancy

These are editorial polish issues, not correctness issues.
May be logged, shown in QA dashboards, or used for future polish passes.
"""

from typing import List, Dict, Any

VAGUE_PHRASES = [
    "appropriate animation", "suitable visual", "relevant content",
    "necessary elements", "various objects", "etc", "and so on",
    "properly animated", "correctly displayed", "accordingly",
    "as needed", "as required", "generic visual", "typical animation",
    "standard display", "some kind of", "some sort of", "a type of",
    "appropriate visual", "suitable animation", "relevant visual",
    "clear diagram", "educational visualization", "appropriate demonstration"
]

WEAK_EXPLANATION_PHRASES = [
    "will be shown", "will appear", "is displayed", "is shown",
    "we see", "you can see", "observe that", "notice how"
]


class QualityWarning:
    """Quality warning - non-blocking, for logging/QA only."""
    def __init__(self, code: str, section_id: int, details: str, suggestion: str = ""):
        self.code = code
        self.section_id = section_id
        self.details = details
        self.suggestion = suggestion
    
    def __str__(self):
        sug = f" [Suggestion: {self.suggestion}]" if self.suggestion else ""
        return f"[QUALITY] {self.code} (section {self.section_id}): {self.details}{sug}"


def validate_quality(presentation: dict) -> List[QualityWarning]:
    """
    Run all Tier-3 quality checks.
    
    Returns list of QualityWarning (never blocks job).
    """
    warnings = []
    sections = presentation.get("sections", [])
    
    for section in sections:
        warnings.extend(_check_vague_language(section))
        warnings.extend(_check_weak_explanations(section))
        warnings.extend(_check_generic_descriptions(section))
    
    return warnings


def _check_vague_phrases_in_text(text: str) -> List[str]:
    """Return list of vague phrases found in text."""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for phrase in VAGUE_PHRASES:
        if phrase.lower() in text_lower:
            found.append(phrase)
    return found


def _check_vague_language(section: Dict) -> List[QualityWarning]:
    """Check for vague visual language in visual beats."""
    warnings = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "")
    
    if section_type not in ["content", "example"]:
        return warnings
    
    visual_beats = section.get("visual_beats", [])
    fields_to_check = ["scene_setup", "objects_and_properties", "motion_sequence", 
                       "labels_and_text", "description"]
    
    for i, beat in enumerate(visual_beats):
        if not isinstance(beat, dict):
            continue
        
        for field in fields_to_check:
            value = beat.get(field, "")
            if value:
                vague = _check_vague_phrases_in_text(value)
                if vague:
                    warnings.append(QualityWarning(
                        "vague_visual_language",
                        section_id,
                        f"Visual beat {i} field '{field}' contains vague phrases: {vague}",
                        "Use specific, concrete descriptions"
                    ))
    
    return warnings


def _check_weak_explanations(section: Dict) -> List[QualityWarning]:
    """Check for weak explanatory language in narration."""
    warnings = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "")
    
    if section_type not in ["content", "example"]:
        return warnings
    
    narration = section.get("narration", {})
    narration_text = ""
    
    if isinstance(narration, dict):
        narration_text = narration.get("full_text", "")
        if not narration_text:
            segments = narration.get("segments", [])
            narration_text = " ".join(seg.get("text", "") for seg in segments)
    else:
        narration_text = narration or ""
    
    text_lower = narration_text.lower()
    found_weak = []
    
    for phrase in WEAK_EXPLANATION_PHRASES:
        if phrase.lower() in text_lower:
            found_weak.append(phrase)
    
    if len(found_weak) >= 3:
        warnings.append(QualityWarning(
            "weak_explanation_detected",
            section_id,
            f"Narration uses {len(found_weak)} weak explanatory phrases: {found_weak[:5]}",
            "Use more active, specific teaching language"
        ))
    
    return warnings


def _check_generic_descriptions(section: Dict) -> List[QualityWarning]:
    """Check for overly generic visual descriptions."""
    warnings = []
    section_id = section.get("section_id") or section.get("id", 0)
    
    manim_spec = section.get("manim_scene_spec", {})
    if manim_spec:
        objects = manim_spec.get("objects", [])
        for i, obj in enumerate(objects):
            obj_id = obj.get("id", f"object_{i}")
            obj_type = obj.get("type", "")
            
            if obj_type in ["generic", "placeholder", "unknown"]:
                warnings.append(QualityWarning(
                    "generic_object_type",
                    section_id,
                    f"Object '{obj_id}' has generic type '{obj_type}'",
                    "Specify concrete object type (e.g., 'circle', 'vector', 'graph')"
                ))
    
    video_prompts = section.get("video_prompts", [])
    for i, prompt in enumerate(video_prompts):
        prompt_text = prompt.get("prompt", "") if isinstance(prompt, dict) else prompt
        if len(prompt_text) < 20:
            warnings.append(QualityWarning(
                "short_video_prompt",
                section_id,
                f"Video prompt {i} is very short ({len(prompt_text)} chars)",
                "Add more visual detail to video prompt"
            ))
    
    return warnings


def format_quality_warnings(warnings: List[QualityWarning]) -> str:
    """Format quality warnings for logging."""
    if not warnings:
        return ""
    
    lines = ["QUALITY WARNINGS (Tier 3 - Non-Blocking):"]
    for warn in warnings:
        lines.append(f"  - {warn}")
    return "\n".join(lines)

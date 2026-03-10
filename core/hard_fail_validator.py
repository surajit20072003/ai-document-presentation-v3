"""
Hard Fail Validator - Implements hard fail conditions for v1.3.

These conditions MUST cause generation to fail - no fallbacks allowed.
Reference: docs/llm_output_requirements_v1.3.json

Hard Fail Conditions (v1.3):
STRUCTURE CHECKS:
1. missing_intro_section
2. missing_summary_section
3. missing_recap_section
4. missing_memory_section

NARRATION CHECKS:
5. content_or_example_narration_below_minimum
6. recap_narration_out_of_range

DISPLAY DIRECTIVE CHECKS:
7. missing_display_directives
8. text_and_visuals_simultaneous (v1.3: text must hide before visuals)
9. missing_visual_content (ISS-077: content/example/summary with text_layer=show must have visual_content)

VISUAL BEAT CHECKS:
9. missing_visual_beats
10. example_without_step_visualization
11. formula_mentioned_but_not_visualized
12. vague_visual_language_detected

RENDERER CHECKS:
13. manim_section_without_scene_spec
14. remotion_section_without_scene_spec
15. video_section_without_prompts

AVATAR CHECKS:
16. intro_avatar_not_visible
17. recap_avatar_visible
"""

import re
from typing import List, Tuple, Dict, Any

CONTENT_MIN_WORDS = 150
EXAMPLE_MIN_WORDS = 100
EXAMPLE_REQUIRED_STEPS = 2  # Minimum 2 visual beats for examples (flexible based on content)

VAGUE_PHRASES = [
    "appropriate animation", "suitable visual", "relevant content",
    "necessary elements", "various objects", "etc", "and so on",
    "properly animated", "correctly displayed", "accordingly",
    "as needed", "as required", "generic visual", "typical animation",
    "standard display", "some kind of", "some sort of", "a type of",
    "appropriate visual", "suitable animation", "relevant visual",
    "clear diagram"
]

REQUIRED_SECTION_TYPES = ["intro", "summary", "memory", "recap"]

RECAP_MIN_WORDS = 300
RECAP_MAX_WORDS = 500
RECAP_SCENE_COUNT = 5
MEMORY_FLASHCARD_COUNT = 5

FORMULA_PATTERNS = [
    r'F\s*=\s*m\s*[*×·]\s*a',
    r'E\s*=\s*m\s*c\s*²',
    r'v\s*=\s*u\s*[+\-]\s*a\s*t',
    r's\s*=\s*ut\s*[+\-]',
    r'[A-Z]\s*=\s*[A-Z0-9\s\+\-\*/\^]{3,}',
    r'\\frac\{',
    r'\\sum',
    r'\\int',
    r'\bformula\b',
    r'\bequation\b',
    r'\bcalculate the\b',
    r'\bcompute the\b',
    r'\bderivation\b',
]


class HardFailError(Exception):
    """Raised when a hard fail condition is detected. NO FALLBACK ALLOWED."""
    def __init__(self, condition: str, section_id: int, details: str):
        self.condition = condition
        self.section_id = section_id
        self.details = details
        super().__init__(f"HARD FAIL [{condition}] Section {section_id}: {details}")


def count_words(text: str) -> int:
    """Count words in text."""
    if not text:
        return 0
    return len(text.split())


def check_vague_phrases(text: str) -> List[str]:
    """Return list of vague phrases found in text."""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for phrase in VAGUE_PHRASES:
        if phrase.lower() in text_lower:
            found.append(phrase)
    return found


def check_formula_in_narration(narration: str) -> bool:
    """Check if narration mentions formulas/equations."""
    if not narration:
        return False
    for pattern in FORMULA_PATTERNS:
        if re.search(pattern, narration, re.IGNORECASE):
            return True
    return False


def validate_visuals_are_shown(section: dict) -> Tuple[bool, str]:
    """
    ISS-065 FIX: Validate that visual_layer is shown at least once when visual_beats exist.
    
    If a section has visual_beats, at least ONE narration segment must have:
    visual_layer = "show" OR visual_layer = "replace"
    
    Returns: (is_valid, error_message_or_none)
    """
    visual_beats = section.get("visual_beats", [])
    if not visual_beats:
        return True, None
    
    narration_raw = section.get("narration", {})
    if isinstance(narration_raw, dict):
        segments = narration_raw.get("segments", [])
    else:
        segments = section.get("narration_segments", [])
    
    if not segments:
        return True, None
    
    has_visual_shown = any(
        seg.get("display_directives", {}).get("visual_layer") in ("show", "replace")
        for seg in segments
    )
    
    if not has_visual_shown:
        section_id = section.get("section_id") or section.get("id", 0)
        return False, f"Section {section_id}: Has {len(visual_beats)} visual_beats but ALL segments have visual_layer='hide'. At least one segment must show visuals."
    
    return True, None


def validate_renderer_subject_match(section: dict, subject: str = None) -> Tuple[bool, str]:
    """
    ISS-066 FIX: Validate renderer matches subject matter.
    
    - Biology content MUST use 'video' renderer (Manim forbidden)
    - Recap sections MUST use 'video' renderer
    
    Returns: (is_valid, error_message_or_none)
    """
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "")
    renderer = section.get("renderer", "")
    
    inferred_subject = subject or section.get("subject", "")
    if inferred_subject:
        inferred_subject = inferred_subject.lower()
    
    if inferred_subject == "biology" and renderer == "manim":
        return False, f"Section {section_id}: Biology content MUST use 'video' renderer, not 'manim'. Manim is forbidden for biology."
    
    if section_type == "recap" and renderer not in ("video", "wan_video"):
        return False, f"Section {section_id}: Recap sections MUST use 'video' renderer, got '{renderer}'."
    
    return True, None


def validate_hard_fail_conditions(section: dict) -> List[HardFailError]:
    """
    Validate all 6 hard fail conditions for a section.
    
    Returns list of HardFailError instances (empty if valid).
    """
    errors = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "unknown")
    renderer = section.get("renderer", "")
    narration_raw = section.get("narration", "")
    if isinstance(narration_raw, dict):
        narration = narration_raw.get("full_text", "")
    else:
        narration = narration_raw or ""
    word_count = count_words(narration)
    visual_beats = section.get("visual_beats", [])
    narration_segments = section.get("narration_segments", [])
    if not narration_segments and isinstance(narration_raw, dict):
        narration_segments = narration_raw.get("segments", [])
    
    embedded_visual_beats = [
        seg.get("visual_beat") for seg in narration_segments 
        if seg.get("visual_beat")
    ]
    
    effective_visual_beats = visual_beats if visual_beats else embedded_visual_beats
    
    if section_type == "content":
        if word_count < CONTENT_MIN_WORDS:
            errors.append(HardFailError(
                "content_or_example_narration_below_minimum",
                section_id,
                f"Content section has {word_count} words, minimum is {CONTENT_MIN_WORDS}"
            ))
        
        if narration_segments and not effective_visual_beats:
            errors.append(HardFailError(
                "missing_visual_beats",
                section_id,
                f"Content section has {len(narration_segments)} narration segments but no visual beats"
            ))
    
    if section_type == "example":
        if word_count < EXAMPLE_MIN_WORDS:
            errors.append(HardFailError(
                "content_or_example_narration_below_minimum",
                section_id,
                f"Example section has {word_count} words, minimum is {EXAMPLE_MIN_WORDS}"
            ))
        
        if not effective_visual_beats:
            errors.append(HardFailError(
                "example_without_step_visualization",
                section_id,
                "Example section has no visual beats - examples must be visualized step-by-step"
            ))
        elif len(effective_visual_beats) < EXAMPLE_REQUIRED_STEPS:
            errors.append(HardFailError(
                "example_without_step_visualization",
                section_id,
                f"Example section has {len(effective_visual_beats)} visual beats, need {EXAMPLE_REQUIRED_STEPS} for 5-step structure"
            ))
    
    if section_type in ["content", "example"] and check_formula_in_narration(narration):
        has_formula_visual = False
        
        section_manim_spec = section.get("manim_scene_spec", {})
        if section_manim_spec:
            objects = section_manim_spec.get("objects", [])
            for obj in objects:
                if obj.get("type") == "equation" or obj.get("properties", {}).get("latex"):
                    has_formula_visual = True
                    break
        
        if not has_formula_visual:
            for beat in effective_visual_beats:
                if not isinstance(beat, dict):
                    continue
                labels = beat.get("labels_and_text", "") or beat.get("description", "")
                manim_spec = beat.get("manim_scene_spec", {})
                equations = manim_spec.get("equations", []) if manim_spec else []
                
                if equations or re.search(r'[a-zA-Z]\s*=', labels):
                    has_formula_visual = True
                    break
        
        if not has_formula_visual:
            errors.append(HardFailError(
                "formula_mentioned_but_not_visualized",
                section_id,
                "Narration mentions formulas/equations but no visual beat shows them"
            ))
    
    if section_type in ["content", "example"]:
        for i, beat in enumerate(effective_visual_beats):
            if not isinstance(beat, dict):
                continue
            fields_to_check = ["scene_setup", "objects_and_properties", "motion_sequence", "labels_and_text", "description"]
            for field in fields_to_check:
                value = beat.get(field, "")
                if value:
                    vague = check_vague_phrases(value)
                    if vague:
                        errors.append(HardFailError(
                            "vague_visual_language_detected",
                            section_id,
                            f"Visual beat {i} field '{field}' contains vague phrases: {vague}"
                        ))
                        break
    
    if renderer == "manim" and section_type in ["content", "example"]:
        section_manim_spec = section.get("manim_scene_spec")
        
        if section_manim_spec:
            objects = section_manim_spec.get("objects", [])
            equations = section_manim_spec.get("equations", [])
            forces = section_manim_spec.get("forces", [])
            animation_seq = section_manim_spec.get("animation_sequence", [])
            
            if not objects and not equations and not forces:
                errors.append(HardFailError(
                    "manim_section_without_scene_spec",
                    section_id,
                    "Section manim_scene_spec has no renderable content (objects/equations/forces)"
                ))
            if not animation_seq:
                errors.append(HardFailError(
                    "manim_section_without_scene_spec",
                    section_id,
                    "Section manim_scene_spec has no animation_sequence"
                ))
        else:
            has_beat_level_spec = any(beat.get("manim_scene_spec") for beat in visual_beats if isinstance(beat, dict))
            if not has_beat_level_spec:
                errors.append(HardFailError(
                    "manim_section_without_scene_spec",
                    section_id,
                    "Manim section has no manim_scene_spec (neither section-level nor beat-level)"
                ))
    
    if renderer == "remotion" and section_type in ["content", "example"]:
        if not section.get("remotion_scene_spec"):
            errors.append(HardFailError(
                "remotion_section_without_scene_spec",
                section_id,
                "Remotion section has no remotion_scene_spec"
            ))
    
    if renderer in ["video", "wan", "wan_video"] and section_type in ["content", "example"]:
        if not section.get("video_prompts") and not section.get("recap_scenes"):
            errors.append(HardFailError(
                "video_section_without_prompts",
                section_id,
                "Video section has no video_prompts"
            ))
    
    return errors


def validate_presentation_hard_fails(presentation: dict) -> Tuple[bool, List[HardFailError]]:
    """
    Validate entire presentation against all hard fail conditions.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    all_errors = []
    sections = presentation.get("sections", [])
    subject = presentation.get("subject", "")
    
    structure_errors = validate_v13_structure(sections)
    all_errors.extend(structure_errors)
    
    for section in sections:
        section_errors = validate_hard_fail_conditions(section)
        all_errors.extend(section_errors)
        
        v13_errors = validate_v13_section_rules(section)
        all_errors.extend(v13_errors)
        
        is_valid, error_msg = validate_visuals_are_shown(section)
        if not is_valid:
            all_errors.append(HardFailError(
                "visuals_never_displayed",
                section.get("section_id") or section.get("id", 0),
                error_msg
            ))
        
        is_valid, error_msg = validate_renderer_subject_match(section, subject)
        if not is_valid:
            all_errors.append(HardFailError(
                "renderer_subject_mismatch",
                section.get("section_id") or section.get("id", 0),
                error_msg
            ))
    
    return len(all_errors) == 0, all_errors


def validate_v13_structure(sections: List[Dict]) -> List[HardFailError]:
    """
    v1.3 Structure Validation - Check mandatory sections exist.
    """
    errors = []
    section_types = [s.get("section_type") for s in sections]
    
    for required_type in REQUIRED_SECTION_TYPES:
        if required_type not in section_types:
            errors.append(HardFailError(
                f"missing_{required_type}_section",
                0,
                f"Presentation is missing required '{required_type}' section"
            ))
    
    recap_sections = [s for s in sections if s.get("section_type") == "recap"]
    for recap in recap_sections:
        recap_scenes = recap.get("recap_scenes", [])
        if not recap_scenes:
            recap_scenes = recap.get("visual_beats", [])
        if len(recap_scenes) != RECAP_SCENE_COUNT:
            errors.append(HardFailError(
                "recap_scene_count_wrong",
                recap.get("section_id", 0),
                f"Recap section has {len(recap_scenes)} scenes, must be exactly {RECAP_SCENE_COUNT}"
            ))
        
        narration_obj = recap.get("narration", {})
        if isinstance(narration_obj, dict):
            segments = narration_obj.get("segments", [])
            total_words = sum(count_words(seg.get("text", "")) for seg in segments)
        else:
            total_words = sum(count_words(scene.get("narration", "")) for scene in recap_scenes)
        if total_words < RECAP_MIN_WORDS:
            errors.append(HardFailError(
                "recap_narration_below_minimum",
                recap.get("section_id", 0),
                f"Recap total narration is {total_words} words, minimum is {RECAP_MIN_WORDS}"
            ))
        if total_words > RECAP_MAX_WORDS:
            errors.append(HardFailError(
                "recap_narration_above_maximum",
                recap.get("section_id", 0),
                f"Recap total narration is {total_words} words, maximum is {RECAP_MAX_WORDS}"
            ))
    
    memory_sections = [s for s in sections if s.get("section_type") == "memory"]
    for memory in memory_sections:
        flashcards = memory.get("flashcards", [])
        if not flashcards:
            flashcards = memory.get("visual_beats", [])
        if len(flashcards) != MEMORY_FLASHCARD_COUNT:
            errors.append(HardFailError(
                "memory_flashcard_count_wrong",
                memory.get("section_id", 0),
                f"Memory section has {len(flashcards)} flashcards, must be exactly {MEMORY_FLASHCARD_COUNT}"
            ))
    
    return errors


def validate_v13_section_rules(section: Dict) -> List[HardFailError]:
    """
    v1.3 Section-level Validation - display_directives and avatar rules.
    Enforces:
    - display_directives on ALL section types with narration_segments
    - text_layer must hide BEFORE visual_layer shows (mutual exclusion)
    - avatar rules per section type at both layout and segment level
    """
    errors = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "unknown")
    narration_segments = section.get("narration_segments", [])
    layout = section.get("layout", {})
    avatar_zone = layout.get("avatar_zone", {})
    
    for i, segment in enumerate(narration_segments):
        display_directives = segment.get("display_directives")
        if not display_directives:
            errors.append(HardFailError(
                "missing_display_directives",
                section_id,
                f"Narration segment {i} ({section_type}) is missing display_directives (v1.3 required)"
            ))
        else:
            if not isinstance(display_directives, dict):
                errors.append(HardFailError(
                    "invalid_display_directives",
                    section_id,
                    f"Narration segment {i} display_directives must be an object"
                ))
            else:
                required_layers = ["text_layer", "visual_layer", "avatar_layer"]
                for layer in required_layers:
                    if layer not in display_directives:
                        errors.append(HardFailError(
                            "missing_display_directives",
                            section_id,
                            f"Narration segment {i} display_directives missing '{layer}'"
                        ))
                
                text_layer = display_directives.get("text_layer", "")
                visual_layer = display_directives.get("visual_layer", "")
                
                if text_layer == "show" and visual_layer in ["show", "replace"]:
                    errors.append(HardFailError(
                        "text_and_visuals_simultaneous",
                        section_id,
                        f"Narration segment {i}: text_layer=show + visual_layer={visual_layer} violates mutual exclusion rule"
                    ))
                
                # ISS-077: Two-channel separation - text_layer=show requires visual_content
                if text_layer == "show" and section_type in ["content", "example", "summary"]:
                    visual_content = segment.get("visual_content", {})
                    has_bullet_points = visual_content.get("bullet_points") and len(visual_content.get("bullet_points", [])) > 0
                    has_formula = visual_content.get("formula")
                    has_labels = visual_content.get("labels") and len(visual_content.get("labels", [])) > 0
                    
                    if not (has_bullet_points or has_formula or has_labels):
                        errors.append(HardFailError(
                            "missing_visual_content",
                            section_id,
                            f"Narration segment {i}: text_layer=show but visual_content is empty. Two-channel separation requires visual_content for display."
                        ))
                
                if section_type == "intro":
                    avatar_layer = display_directives.get("avatar_layer", "")
                    if avatar_layer == "hide":
                        errors.append(HardFailError(
                            "intro_avatar_not_visible",
                            section_id,
                            f"Narration segment {i}: intro avatar_layer cannot be 'hide'"
                        ))
                
                if section_type == "recap":
                    avatar_layer = display_directives.get("avatar_layer", "")
                    if avatar_layer in ["show", "gesture_only"]:
                        errors.append(HardFailError(
                            "recap_avatar_visible",
                            section_id,
                            f"Narration segment {i}: recap avatar_layer must be 'hide', not '{avatar_layer}'"
                        ))
    
    if section_type == "intro":
        avatar_mode = avatar_zone.get("mode", "")
        avatar_width = avatar_zone.get("width_percent", 0)
        avatar_visibility = avatar_zone.get("visibility", "visible")
        
        if avatar_visibility == "hidden" or avatar_mode == "hidden":
            errors.append(HardFailError(
                "intro_avatar_not_visible",
                section_id,
                "Intro section layout.avatar_zone must have visible avatar (center or overlay, ≥50% width)"
            ))
        elif avatar_width and avatar_width < 50:
            errors.append(HardFailError(
                "intro_avatar_too_small",
                section_id,
                f"Intro avatar width is {avatar_width}%, must be ≥50%"
            ))
    
    if section_type == "recap":
        avatar_mode = avatar_zone.get("mode", "")
        avatar_visibility = avatar_zone.get("visibility", "")
        
        if avatar_mode not in ["hidden", ""] and avatar_visibility != "hidden":
            if avatar_zone:
                errors.append(HardFailError(
                    "recap_avatar_visible",
                    section_id,
                    "Recap section layout.avatar_zone must have hidden avatar (video only)"
                ))
    
    return errors


def format_hard_fail_report(errors: List[HardFailError]) -> str:
    """Format hard fail errors into a readable report."""
    if not errors:
        return "No hard fail conditions detected."
    
    lines = [
        "=" * 60,
        "HARD FAIL VALIDATION REPORT",
        "=" * 60,
        f"Total failures: {len(errors)}",
        ""
    ]
    
    by_condition = {}
    for err in errors:
        if err.condition not in by_condition:
            by_condition[err.condition] = []
        by_condition[err.condition].append(err)
    
    for condition, errs in by_condition.items():
        lines.append(f"\n[{condition}] - {len(errs)} occurrence(s)")
        for err in errs:
            lines.append(f"  Section {err.section_id}: {err.details}")
    
    lines.append("\n" + "=" * 60)
    return "\n".join(lines)

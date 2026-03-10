"""
Tier 1 - STRUCTURAL HARD FAIL Validator (Compiler Errors)

Purpose: Guarantee output is structurally executable by pipeline + player.
If Tier 1 fails → STOP IMMEDIATELY. NO RETRY FOR CONTENT.

Tier-1 checks (HARD FAIL):
- Sections & ordering: missing intro/summary/memory/recap
- Core structure: missing renderer, missing visual_beats, missing display_directives
- Counts: recap scenes ≠ 5, memory flashcards ≠ 5
- Layer logic: text + complex visual visible simultaneously
- Renderer contracts: manim without manim_scene_spec, etc.
"""

from typing import List, Dict, Any, Tuple

REQUIRED_SECTION_TYPES = ["intro", "summary", "memory", "recap"]
RECAP_SCENE_COUNT = 5
MEMORY_FLASHCARD_COUNT = 5


class StructuralError:
    """Structural validation error - causes hard fail."""
    def __init__(self, code: str, section_id: int, details: str):
        self.code = code
        self.section_id = section_id
        self.details = details
    
    def __str__(self):
        return f"[STRUCTURAL] {self.code} (section {self.section_id}): {self.details}"


def validate_structural(presentation: dict) -> List[StructuralError]:
    """
    Run all Tier-1 structural checks.
    
    Returns list of StructuralError (empty if valid).
    """
    errors = []
    sections = presentation.get("sections", [])
    
    errors.extend(_check_required_sections(sections))
    errors.extend(_check_section_counts(sections))
    
    for section in sections:
        errors.extend(_check_section_structure(section))
        errors.extend(_check_display_directives(section))
        errors.extend(_check_layer_logic(section))
        errors.extend(_check_renderer_contracts(section))
        errors.extend(_check_avatar_rules(section))
    
    return errors


def _check_required_sections(sections: List[Dict]) -> List[StructuralError]:
    """Check mandatory sections exist."""
    errors = []
    section_types = [s.get("section_type") for s in sections]
    
    for required_type in REQUIRED_SECTION_TYPES:
        if required_type not in section_types:
            errors.append(StructuralError(
                f"missing_{required_type}_section",
                0,
                f"Presentation is missing required '{required_type}' section"
            ))
    
    return errors


def _check_section_counts(sections: List[Dict]) -> List[StructuralError]:
    """Check recap scene count = 5, memory flashcard count = 5."""
    errors = []
    
    for section in sections:
        section_id = section.get("section_id") or section.get("id", 0)
        section_type = section.get("section_type", "")
        
        if section_type == "recap":
            recap_scenes = section.get("recap_scenes", [])
            if not recap_scenes:
                recap_scenes = section.get("visual_beats", [])
            if len(recap_scenes) != RECAP_SCENE_COUNT:
                errors.append(StructuralError(
                    "recap_scene_count_wrong",
                    section_id,
                    f"Recap has {len(recap_scenes)} scenes, must be exactly {RECAP_SCENE_COUNT}"
                ))
        
        if section_type == "memory":
            flashcards = section.get("flashcards", [])
            if not flashcards:
                flashcards = section.get("visual_beats", [])
            if len(flashcards) != MEMORY_FLASHCARD_COUNT:
                errors.append(StructuralError(
                    "memory_flashcard_count_wrong",
                    section_id,
                    f"Memory has {len(flashcards)} flashcards, must be exactly {MEMORY_FLASHCARD_COUNT}"
                ))
    
    return errors


def _check_section_structure(section: Dict) -> List[StructuralError]:
    """Check core structure: renderer present, visual_beats present for content/example."""
    errors = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "")
    renderer = section.get("renderer")
    
    if not renderer:
        errors.append(StructuralError(
            "missing_renderer",
            section_id,
            f"Section type '{section_type}' has no renderer specified"
        ))
    
    if section_type in ["content", "example"]:
        visual_beats = section.get("visual_beats", [])
        narration_segments = section.get("narration_segments", [])
        narration = section.get("narration", {})
        if isinstance(narration, dict):
            narration_segments = narration_segments or narration.get("segments", [])
        
        embedded_visual_beats = [
            seg.get("visual_beat") for seg in narration_segments 
            if seg.get("visual_beat")
        ]
        
        effective_beats = visual_beats if visual_beats else embedded_visual_beats
        
        if not effective_beats:
            errors.append(StructuralError(
                "missing_visual_beats",
                section_id,
                f"Section type '{section_type}' has no visual_beats"
            ))
    
    return errors


def _check_display_directives(section: Dict) -> List[StructuralError]:
    """Check display_directives exist INSIDE each narration segment (v1.3 per-segment format).
    
    BIBLE ALIGNMENT (v2.5):
    - Intro: text_layer=HIDE, visual_layer=HIDE, avatar=SHOW (Fixed defaults, no per-segment directives needed)
    - Summary: text_layer=SHOW (Fixed, bullet list display)
    - Memory: Flashcard behavior is fixed (Front -> Pause -> Back)
    - Recap: visual_layer=SHOW, text_layer=HIDE (Full screen video, fixed)
    - Content/Example: REQUIRE per-segment display_directives (Teach->Show toggle)
    """
    errors = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "")
    
    # BIBLE: Only Content and Example sections require per-segment display_directives
    # Other section types have fixed defaults that the player knows
    if section_type not in ["content", "example"]:
        return errors  # Skip validation for intro, summary, memory, recap, quiz
    
    narration = section.get("narration", {})
    narration_segments = []
    if isinstance(narration, dict):
        narration_segments = narration.get("segments", [])
    
    if not narration_segments:
        return errors
    
    for i, seg in enumerate(narration_segments):
        if not isinstance(seg, dict):
            continue
        
        seg_id = seg.get("segment_id", i + 1)
        dd = seg.get("display_directives")
        
        if dd is None:
            errors.append(StructuralError(
                "missing_segment_display_directives",
                section_id,
                f"Segment {seg_id} missing display_directives (must be inside each segment)"
            ))
            continue

        
        if not isinstance(dd, dict):
            errors.append(StructuralError(
                "invalid_segment_display_directives",
                section_id,
                f"Segment {seg_id} display_directives must be an object"
            ))
            continue
        
        required_layers = ["text_layer", "visual_layer", "avatar_layer"]
        valid_text_values = ["show", "hide", "swap"]
        valid_visual_values = ["show", "hide", "replace"]
        valid_avatar_values = ["show", "hide", "gesture_only"]
        
        for layer in required_layers:
            layer_val = dd.get(layer)
            if layer_val is None:
                errors.append(StructuralError(
                    "missing_layer_in_segment",
                    section_id,
                    f"Segment {seg_id} display_directives missing '{layer}'"
                ))
            elif isinstance(layer_val, dict):
                errors.append(StructuralError(
                    "layer_must_be_string",
                    section_id,
                    f"Segment {seg_id} '{layer}' must be a string enum, not object"
                ))
            elif isinstance(layer_val, str):
                if layer == "text_layer" and layer_val not in valid_text_values:
                    errors.append(StructuralError(
                        "invalid_text_layer_value",
                        section_id,
                        f"Segment {seg_id} text_layer='{layer_val}' invalid, must be: {valid_text_values}"
                    ))
                elif layer == "visual_layer" and layer_val not in valid_visual_values:
                    errors.append(StructuralError(
                        "invalid_visual_layer_value",
                        section_id,
                        f"Segment {seg_id} visual_layer='{layer_val}' invalid, must be: {valid_visual_values}"
                    ))
                elif layer == "avatar_layer" and layer_val not in valid_avatar_values:
                    errors.append(StructuralError(
                        "invalid_avatar_layer_value",
                        section_id,
                        f"Segment {seg_id} avatar_layer='{layer_val}' invalid, must be: {valid_avatar_values}"
                    ))
    
    return errors


def _check_layer_logic(section: Dict) -> List[StructuralError]:
    """Check text + complex visual not shown simultaneously (per-segment check).
    Also check that text_layer=show segments have visual_content (two-channel separation)."""
    errors = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "")
    
    narration = section.get("narration", {})
    narration_segments = []
    if isinstance(narration, dict):
        narration_segments = narration.get("segments", [])
    
    for i, seg in enumerate(narration_segments):
        if not isinstance(seg, dict):
            continue
        
        dd = seg.get("display_directives", {})
        if not isinstance(dd, dict):
            continue
        
        seg_id = seg.get("segment_id", i + 1)
        text_layer = dd.get("text_layer", "hide")
        visual_layer = dd.get("visual_layer", "hide")
        
        if text_layer == "show" and visual_layer in ["show", "replace"]:
            errors.append(StructuralError(
                "text_and_visuals_simultaneous",
                section_id,
                f"Segment {seg_id}: text_layer=show + visual_layer={visual_layer} violates mutual exclusion"
            ))
        
        # BIBLE: Only content/example sections need visual_content when text_layer=show
        # Intro/Summary have fixed defaults and don't need this validation
        if text_layer == "show" and section_type in ["content", "example"]:

            visual_content = seg.get("visual_content")
            has_content = False
            if isinstance(visual_content, dict):
                bullet_points = visual_content.get("bullet_points", [])
                formula = visual_content.get("formula")
                labels = visual_content.get("labels", [])
                has_content = bool(bullet_points) or bool(formula) or bool(labels)
            
            if not has_content:
                errors.append(StructuralError(
                    "text_layer_show_missing_visual_content",
                    section_id,
                    f"Segment {seg_id}: text_layer=show but no visual_content (narration text cannot be displayed)"
                ))
    
    return errors


def _check_renderer_contracts(section: Dict) -> List[StructuralError]:
    """Check renderer-specific specs are present."""
    errors = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "")
    renderer = section.get("renderer", "")
    
    if section_type not in ["content", "example"]:
        return errors
    
    if renderer == "manim":
        section_manim_spec = section.get("manim_scene_spec")
        
        if section_manim_spec:
            objects = section_manim_spec.get("objects", [])
            equations = section_manim_spec.get("equations", [])
            forces = section_manim_spec.get("forces", [])
            animation_seq = section_manim_spec.get("animation_sequence", [])
            
            if not objects and not equations and not forces:
                errors.append(StructuralError(
                    "manim_no_renderable_content",
                    section_id,
                    "manim_scene_spec has no objects/equations/forces"
                ))
            if not animation_seq:
                errors.append(StructuralError(
                    "manim_no_animation_sequence",
                    section_id,
                    "manim_scene_spec has no animation_sequence"
                ))
        else:
            visual_beats = section.get("visual_beats", [])
            has_beat_level_spec = any(
                beat.get("manim_scene_spec") for beat in visual_beats 
                if isinstance(beat, dict)
            )
            if not has_beat_level_spec:
                errors.append(StructuralError(
                    "manim_section_without_scene_spec",
                    section_id,
                    "Manim section has no manim_scene_spec"
                ))
    
    if renderer == "remotion" and section_type in ["content", "example"]:
        if not section.get("remotion_scene_spec"):
            errors.append(StructuralError(
                "remotion_section_without_scene_spec",
                section_id,
                "Remotion section has no remotion_scene_spec"
            ))
    
    if renderer in ["video", "wan", "wan_video"] and section_type in ["content", "example"]:
        if not section.get("video_prompts") and not section.get("recap_scenes"):
            errors.append(StructuralError(
                "video_section_without_prompts",
                section_id,
                "Video section has no video_prompts"
            ))
    
    return errors


def _check_avatar_rules(section: Dict) -> List[StructuralError]:
    """Check avatar visibility rules per section type."""
    errors = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "")
    layout = section.get("layout", {})
    avatar_zone = layout.get("avatar_zone", {})
    
    narration = section.get("narration", {})
    narration_segments = []
    if isinstance(narration, dict):
        narration_segments = narration.get("segments", [])
    
    if section_type == "intro":
        avatar_mode = avatar_zone.get("mode", "")
        avatar_width = avatar_zone.get("width_percent", 0)
        avatar_visibility = avatar_zone.get("visibility", "visible")
        
        if avatar_visibility == "hidden" or avatar_mode == "hidden":
            errors.append(StructuralError(
                "intro_avatar_not_visible",
                section_id,
                "Intro avatar_zone must be visible"
            ))
        elif avatar_width and avatar_width < 50:
            errors.append(StructuralError(
                "intro_avatar_too_small",
                section_id,
                f"Intro avatar width is {avatar_width}%, must be ≥50%"
            ))
        
        for i, seg in enumerate(narration_segments):
            if isinstance(seg, dict):
                dd = seg.get("display_directives", {})
                avatar_layer = dd.get("avatar_layer") if isinstance(dd, dict) else None
                if avatar_layer == "hide":
                    errors.append(StructuralError(
                        "intro_avatar_hidden_in_segment",
                        section_id,
                        f"Intro segment {i+1}: avatar cannot be 'hide'"
                    ))
    
    if section_type == "recap":
        avatar_mode = avatar_zone.get("mode", "")
        avatar_visibility = avatar_zone.get("visibility", "")
        
        if avatar_mode not in ["hidden", ""] and avatar_visibility != "hidden":
            if avatar_zone:
                errors.append(StructuralError(
                    "recap_avatar_visible",
                    section_id,
                    "Recap avatar_zone must be hidden (video only)"
                ))
        
        for i, seg in enumerate(narration_segments):
            if isinstance(seg, dict):
                dd = seg.get("display_directives", {})
                avatar_layer = dd.get("avatar_layer") if isinstance(dd, dict) else None
                if avatar_layer in ["show", "gesture_only"]:
                    errors.append(StructuralError(
                        "recap_avatar_visible_in_segment",
                        section_id,
                        f"Recap segment {i+1}: avatar must be 'hide', not '{avatar_layer}'"
                    ))
    
    return errors


def format_structural_errors(errors: List[StructuralError]) -> str:
    """Format structural errors for logging/retry prompt."""
    if not errors:
        return ""
    
    lines = ["STRUCTURAL ERRORS (Tier 1 - Hard Fail):"]
    for err in errors:
        lines.append(f"  - {err}")
    return "\n".join(lines)

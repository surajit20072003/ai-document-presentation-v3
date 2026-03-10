"""
V1.5 Agent Validation Utilities

Provides schema validation and semantic rule checking for agent outputs.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

SCHEMAS_DIR = Path(__file__).parent.parent.parent / "schemas" / "v1.5"


def load_schema(filename: str) -> Dict[str, Any]:
    """Load a JSON schema from the v1.5 schemas directory."""
    path = SCHEMAS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    return json.loads(path.read_text())


def validate_blueprint(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a SectionBlueprint against schema."""
    if not JSONSCHEMA_AVAILABLE:
        return True, []
    
    schema = load_schema("section_blueprint.schema.json")
    validator = jsonschema.Draft7Validator(schema)
    errors = [f"{' -> '.join(str(p) for p in e.absolute_path) or 'root'}: {e.message}" 
              for e in validator.iter_errors(data)]
    return len(errors) == 0, errors


def validate_narration(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a SectionNarration against schema."""
    if not JSONSCHEMA_AVAILABLE:
        return True, []
    
    schema = load_schema("section_narration.schema.json")
    validator = jsonschema.Draft7Validator(schema)
    errors = [f"{' -> '.join(str(p) for p in e.absolute_path) or 'root'}: {e.message}" 
              for e in validator.iter_errors(data)]
    return len(errors) == 0, errors


def validate_visuals(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a SectionVisuals against schema."""
    if not JSONSCHEMA_AVAILABLE:
        return True, []
    
    schema = load_schema("section_visuals.schema.json")
    validator = jsonschema.Draft7Validator(schema)
    errors = [f"{' -> '.join(str(p) for p in e.absolute_path) or 'root'}: {e.message}" 
              for e in validator.iter_errors(data)]
    return len(errors) == 0, errors


def validate_render_spec(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a RenderSpec against schema."""
    if not JSONSCHEMA_AVAILABLE:
        return True, []
    
    schema = load_schema("render_spec.schema.json")
    validator = jsonschema.Draft7Validator(schema)
    errors = [f"{' -> '.join(str(p) for p in e.absolute_path) or 'root'}: {e.message}" 
              for e in validator.iter_errors(data)]
    return len(errors) == 0, errors


def validate_display_directives_mutual_exclusion(segment_enrichments: List[Dict]) -> Tuple[bool, List[str]]:
    """
    Guardrail G4: text_layer and visual_layer cannot both be 'show'.
    """
    errors = []
    for enrich in segment_enrichments:
        dd = enrich.get("display_directives", {})
        if dd.get("text_layer") == "show" and dd.get("visual_layer") == "show":
            errors.append(f"Segment {enrich.get('segment_id')}: text_layer and visual_layer both 'show' violates G4")
    return len(errors) == 0, errors


def validate_beat_segment_mapping(
    visual_beats: List[Dict], 
    narration_segments: List[Dict]
) -> Tuple[bool, List[str]]:
    """
    Validate that visual_beat.segment_id references valid narration segment_ids.
    """
    errors = []
    valid_segment_ids = {s.get("segment_id") for s in narration_segments}
    
    for beat in visual_beats:
        if beat.get("segment_id") not in valid_segment_ids:
            errors.append(f"Beat {beat.get('beat_id')}: segment_id {beat.get('segment_id')} not found in narration")
    
    return len(errors) == 0, errors


def validate_renderer_spec_required(section: Dict) -> Tuple[bool, List[str]]:
    """
    Guardrail G5: Non-none renderers must have corresponding spec.
    """
    errors = []
    renderer = section.get("renderer")
    
    if renderer == "manim" and "manim_scene_spec" not in section:
        errors.append("Renderer 'manim' requires manim_scene_spec")
    elif renderer == "video" and "video_prompts" not in section:
        errors.append("Renderer 'video' requires video_prompts")
    elif renderer == "remotion" and "remotion_scene_spec" not in section:
        errors.append("Renderer 'remotion' requires remotion_scene_spec")
    
    return len(errors) == 0, errors


def validate_word_count(text: str, min_words: int, max_words: int, field_name: str) -> Tuple[bool, List[str]]:
    """Validate word count within range."""
    word_count = len(text.split())
    errors = []
    
    if word_count < min_words:
        errors.append(f"{field_name}: {word_count} words (min {min_words})")
    if word_count > max_words:
        errors.append(f"{field_name}: {word_count} words (max {max_words})")
    
    return len(errors) == 0, errors

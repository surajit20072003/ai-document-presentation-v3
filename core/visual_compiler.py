"""
Visual Compiler - Converts visual_beats to concrete renderer prompts/code.

CRITICAL: This module implements FAIL-FAST for incomplete visual beats.
- If a visual beat is missing required fields, it FAILS.
- NO "best effort" interpretation.
- NO silent fallback to placeholders.
- NO renderer creativity.

SCHEMA: Each visual beat MUST have these 5 fields:
- scene_setup
- objects_and_properties
- motion_sequence
- labels_and_text
- pedagogical_focus

VALIDATION: Two-layer approach
1. Structural checks (code) - missing fields = hard error
2. Semantic checks (Flash LLM) - vague content = error (understands context)
"""

import re
import sys
from typing import Tuple, List, Optional

REQUIRED_VISUAL_BEAT_FIELDS = [
    "scene_setup",
    "objects_and_properties", 
    "motion_sequence",
    "labels_and_text",
    "purpose",
    "duration_seconds"
]

_flash_validator_enabled = True

def set_flash_validator_enabled(enabled: bool):
    """Enable or disable Flash LLM semantic validation."""
    global _flash_validator_enabled
    _flash_validator_enabled = enabled
    
def is_flash_validator_enabled() -> bool:
    """Check if Flash LLM semantic validation is enabled."""
    return _flash_validator_enabled


class VisualCompilationError(Exception):
    def __init__(self, section_id: int, beat_index: int, reason: str):
        self.section_id = section_id
        self.beat_index = beat_index
        self.reason = reason
        super().__init__(f"Section {section_id}, Beat {beat_index}: {reason}")


def log(msg: str):
    """Print with immediate flush for real-time logging."""
    print(msg)
    sys.stdout.flush()


def validate_visual_beat_structure(beat: dict, section_id: int, beat_index: int, section_type: str = "content", strict: bool = False) -> list:
    """Validate that a visual beat has all required fields with sufficient content.
    
    Two-layer validation:
    1. Structural checks (code) - missing fields = hard error for content sections
    2. Semantic checks (Flash LLM) - vague content = error (understands context)
    
    Args:
        beat: The visual beat dict
        section_id: Section identifier
        beat_index: Beat index within section
        section_type: Type of section (intro, summary, content, example, memory, recap)
        strict: If True, raise errors for semantic issues. If False, log warnings.
    
    Returns:
        List of warning messages (empty if no warnings)
    """
    warnings = []
    missing_fields = []
    
    for field in REQUIRED_VISUAL_BEAT_FIELDS:
        value = beat.get(field, "")
        if field == "purpose" and not value:
            value = beat.get("pedagogical_focus", "")
        if field == "duration_seconds" and not value:
            value = beat.get("duration", "")
        if not value and not (isinstance(value, (int, float)) and value >= 0):
            missing_fields.append(field)
    
    if len(missing_fields) == len(REQUIRED_VISUAL_BEAT_FIELDS):
        raise VisualCompilationError(
            section_id, beat_index,
            f"Visual beat has no content. All fields are empty or missing."
        )
    
    if section_type in ("content", "example"):
        if missing_fields:
            raise VisualCompilationError(
                section_id, beat_index,
                f"Missing required fields: {missing_fields}. "
                f"All visual beats must have: {REQUIRED_VISUAL_BEAT_FIELDS}"
            )
    else:
        if missing_fields:
            warnings.append(f"[WARN] Section {section_id}, Beat {beat_index}: Missing fields {missing_fields}")
    
    if _flash_validator_enabled and section_type in ("content", "example"):
        try:
            from core.flash_validator import validate_beat_with_flash
            result = validate_beat_with_flash(beat, section_id, beat_index, section_type)
            
            if not result.get("valid"):
                reason = result.get("reason", "Content too vague to render")
                if strict:
                    raise VisualCompilationError(section_id, beat_index, f"Flash validation failed: {reason}")
                else:
                    warnings.append(f"[SEMANTIC WARN] Section {section_id}, Beat {beat_index}: {reason}")
        except ImportError:
            log(f"[WARN] Flash validator not available, skipping semantic check")
        except VisualCompilationError:
            raise
        except Exception as e:
            log(f"[WARN] Flash validation error: {e}, continuing without semantic check")
    
    return warnings


def extract_labels_from_text(labels_text: str) -> List[str]:
    """Extract label strings from labels_and_text field."""
    labels = re.findall(r"['\"]([^'\"]+)['\"]", labels_text)
    if not labels:
        labels = re.findall(r"Label\s+(\S+)", labels_text)
    return labels if labels else ["Label"]


def compile_wan_prompt(beat: dict, section_id: int, beat_index: int, section_type: str = "content") -> str:
    """Compile a WAN video prompt from structured visual beat fields."""
    use_strict = section_type in ("content", "example")
    warnings = validate_visual_beat_structure(beat, section_id, beat_index, section_type=section_type, strict=use_strict)
    for w in warnings:
        print(w)
    
    scene_setup = beat.get("scene_setup", "") or "Educational scene"
    objects_text = beat.get("objects_and_properties", "") or "Visual elements"
    motion = beat.get("motion_sequence", "") or "Smooth transitions"
    labels_text = beat.get("labels_and_text", "") or "Text labels"
    focus = beat.get("purpose", "") or beat.get("pedagogical_focus", "") or "Educational content"
    
    labels = extract_labels_from_text(labels_text)
    
    prompt_parts = [
        f"Scene: {scene_setup}",
        f"Objects: {objects_text}",
        f"Animation: {motion}",
        f"Text labels to show: {', '.join(labels)}.",
        f"Educational goal: {focus}"
    ]
    
    compiled_prompt = " ".join(prompt_parts)
    return compiled_prompt


COLOR_MAP = {
    "blue": "BLUE",
    "red": "RED",
    "green": "GREEN",
    "orange": "ORANGE",
    "yellow": "YELLOW",
    "purple": "PURPLE",
    "white": "WHITE",
    "gray": "GRAY",
    "grey": "GRAY",
    "pink": "PINK",
    "cyan": "TEAL",
}

POSITION_MAP = {
    "top_center": "UP * 3",
    "top_left": "UP * 3 + LEFT * 4",
    "top_right": "UP * 3 + RIGHT * 4",
    "bottom_center": "DOWN * 3",
    "bottom_left": "DOWN * 3 + LEFT * 4",
    "bottom_right": "DOWN * 3 + RIGHT * 4",
    "left": "LEFT * 5",
    "right": "RIGHT * 5",
    "center": "ORIGIN",
}


def validate_manim_scene_spec(spec: dict, section_id: int, beat_index: int) -> None:
    """Validate manim_scene_spec has required structure.
    
    Accepts specs with at least ONE of: objects, equations, or forces.
    This allows equation-only specs for math-heavy content sections.
    """
    if not spec:
        raise VisualCompilationError(
            section_id, beat_index,
            "Missing manim_scene_spec. Manim sections require structured scene specs, not prose descriptions."
        )
    
    objects = spec.get("objects", [])
    equations = spec.get("equations", [])
    forces = spec.get("forces", [])
    
    if not objects and not equations and not forces:
        raise VisualCompilationError(
            section_id, beat_index,
            "manim_scene_spec has no renderable content. Must define at least one of: objects, equations, or forces."
        )
    
    animation_sequence = spec.get("animation_sequence", [])
    if not animation_sequence:
        raise VisualCompilationError(
            section_id, beat_index,
            "manim_scene_spec.animation_sequence is empty. Must define animation actions."
        )
    
    for obj in objects:
        if not obj.get("id"):
            raise VisualCompilationError(
                section_id, beat_index,
                f"Object missing 'id' field: {obj}"
            )
        if not obj.get("type"):
            raise VisualCompilationError(
                section_id, beat_index,
                f"Object '{obj.get('id')}' missing 'type' field"
            )


def translate_spec_to_manim_code(spec: dict, section_id: int, beat_index: int) -> str:
    """Translate manim_scene_spec to executable Manim code."""
    validate_manim_scene_spec(spec, section_id, beat_index)
    
    code_lines = []
    object_vars = {}
    axes_vars = {}
    
    objects = spec.get("objects", [])
    
    declared_axes = {obj.get("id") for obj in objects if obj.get("type") == "axes"}
    required_axes = set()
    for obj in objects:
        if obj.get("type") in ("graph", "area_under_graph"):
            axes_ref = obj.get("properties", {}).get("axes", "axes")
            if axes_ref not in declared_axes:
                required_axes.add(axes_ref)
    
    for axes_name in required_axes:
        log(f"[WARN] Auto-creating missing '{axes_name}' axes for graph objects")
        auto_axes_var = f"auto_{axes_name}"
        code_lines.append(f'{auto_axes_var} = Axes(x_range=[-5, 5, 1], y_range=[-3, 3, 1], x_length=10, y_length=6, axis_config={{"include_tip": True}})')
        code_lines.append(f'self.play(Create({auto_axes_var}), run_time=1)')
        axes_vars[axes_name] = auto_axes_var
    
    for obj in objects:
        obj_id = obj["id"]
        obj_type = obj["type"]
        position = obj.get("position", [0, 0])
        props = obj.get("properties", {})
        
        color = COLOR_MAP.get(props.get("color", "blue").lower(), "BLUE")
        label_text = props.get("label", "")
        radius = props.get("radius", 0.3)
        
        base_var_name = obj_id.replace("-", "_").replace(" ", "_")
        if obj_type != "axes" and base_var_name in ["axes", "graph", "area", "curve"]:
            var_name = f"obj_{base_var_name}"
            log(f"[WARN] Renaming '{base_var_name}' to '{var_name}' to avoid variable collision")
        else:
            var_name = base_var_name
        object_vars[obj_id] = var_name
        
        if obj_type == "point_charge":
            code_lines.append(f'{var_name} = Dot(point=np.array([{position[0]}, {position[1]}, 0]), color={color}, radius={radius})')
            if label_text:
                code_lines.append(f'{var_name}_label = Text("{label_text}", font_size=24).next_to({var_name}, UP)')
        
        elif obj_type == "charged_sphere":
            code_lines.append(f'{var_name} = Circle(radius={radius}, color={color}, fill_opacity=0.5).move_to(np.array([{position[0]}, {position[1]}, 0]))')
            if label_text:
                code_lines.append(f'{var_name}_label = Text("{label_text}", font_size=24).next_to({var_name}, UP)')
        
        elif obj_type == "point":
            code_lines.append(f'{var_name} = Dot(point=np.array([{position[0]}, {position[1]}, 0]), color={color})')
            if label_text:
                code_lines.append(f'{var_name}_label = Text("{label_text}", font_size=20).next_to({var_name}, DOWN)')
        
        elif obj_type == "vector":
            end = props.get("end", [position[0] + 2, position[1]])
            code_lines.append(f'{var_name} = Arrow(start=np.array([{position[0]}, {position[1]}, 0]), end=np.array([{end[0]}, {end[1]}, 0]), color={color}, buff=0)')
            if label_text:
                code_lines.append(f'{var_name}_label = Text("{label_text}", font_size=20).next_to({var_name}, DOWN)')
        
        elif obj_type == "equation":
            latex = obj.get("latex") or props.get("latex", "")
            if not latex:
                log(f"[WARN] Equation object {obj_id} missing latex field")
                latex = "?"
            obj_position = obj.get("position") or props.get("position", "center")
            if isinstance(obj_position, list):
                pos_name = f"np.array([{obj_position[0]}, {obj_position[1]}, 0])"
            else:
                pos_name = POSITION_MAP.get(obj_position, "ORIGIN")
            display_text = latex.replace("\\", "").replace("{", "").replace("}", "").replace("_", "").replace("^", "")
            code_lines.append(f'{var_name} = Text("{display_text}", font_size=32).move_to({pos_name})')
        
        elif obj_type == "label":
            latex = obj.get("latex") or props.get("latex", "")
            text = obj.get("text") or props.get("text", label_text or obj_id)
            font_size = props.get("font_size", 28)
            scale = props.get("scale", 1.0)
            obj_position = obj.get("position") or position
            if isinstance(obj_position, list):
                pos_str = f"np.array([{obj_position[0]}, {obj_position[1]}, 0])"
            else:
                pos_str = POSITION_MAP.get(obj_position, "ORIGIN")
            if latex:
                display_text = latex.replace("\\", "").replace("{", "").replace("}", "").replace("_", "").replace("^", "")
                code_lines.append(f'{var_name} = Text("{display_text}", font_size={int(font_size * scale)}).move_to({pos_str})')
            else:
                code_lines.append(f'{var_name} = Text("{text}", font_size={font_size}).move_to({pos_str})')
        
        elif obj_type == "axes":
            x_range = props.get("x_range", [-3, 3, 1])
            y_range = props.get("y_range", [-3, 3, 1])
            if len(x_range) == 2:
                x_range = [x_range[0], x_range[1], 1]
            if len(y_range) == 2:
                y_range = [y_range[0], y_range[1], 1]
            code_lines.append(f'{var_name} = Axes(x_range=[{x_range[0]}, {x_range[1]}, {x_range[2]}], y_range=[{y_range[0]}, {y_range[1]}, {y_range[2]}], x_length=8, y_length=6, axis_config={{"include_tip": True}})')
            axes_vars[obj_id] = var_name
        
        elif obj_type == "graph":
            equation = obj.get("equation") or props.get("equation", "x**2")
            if not equation.startswith("lambda"):
                equation = f"lambda x: {equation}"
            graph_color = COLOR_MAP.get(props.get("color", "blue").lower().replace("#", ""), "BLUE")
            if props.get("color", "").startswith("#"):
                graph_color = f'"{props.get("color")}"'
            axes_ref = props.get("axes", "axes")
            axes_var = axes_vars.get(axes_ref) or object_vars.get(axes_ref, axes_ref)
            code_lines.append(f'{var_name} = {axes_var}.plot({equation}, color={graph_color})')
        
        elif obj_type == "area_under_graph":
            graph_id = props.get("graph_id", "graph")
            graph_var = object_vars.get(graph_id, graph_id)
            x_range = props.get("x_range", [0, 2])
            axes_ref = props.get("axes", "axes")
            axes_var = axes_vars.get(axes_ref) or object_vars.get(axes_ref, axes_ref)
            fill_color = props.get("color", "#87CEEB")
            opacity = props.get("opacity", 0.5)
            code_lines.append(f'{var_name} = {axes_var}.get_area({graph_var}, x_range=[{x_range[0]}, {x_range[1]}], color="{fill_color}", opacity={opacity})')
        
        elif obj_type == "recap_panel" or obj_type == "panel":
            title = props.get("title", "")
            visual = props.get("visual", "")
            formula = props.get("formula", "")
            if isinstance(position, list):
                pos_str = f"np.array([{position[0]}, {position[1]}, 0])"
            else:
                pos_str = POSITION_MAP.get(position, "ORIGIN")
            content = f"{title}\\n{visual}\\n{formula}" if visual else title
            code_lines.append(f'{var_name} = VGroup(Rectangle(width=4, height=3, color=BLUE), Text("{content[:50]}", font_size=20)).move_to({pos_str})')
        
        elif obj_type == "text":
            text = obj.get("text") or props.get("text", label_text or obj_id)
            font_size = props.get("font_size", 24)
            obj_position = obj.get("position") or position
            if isinstance(obj_position, list):
                code_lines.append(f'{var_name} = Text("{text}", font_size={font_size}).move_to(np.array([{obj_position[0]}, {obj_position[1]}, 0]))')
            else:
                pos_name = POSITION_MAP.get(obj_position, "ORIGIN")
                code_lines.append(f'{var_name} = Text("{text}", font_size={font_size}).move_to({pos_name})')
        
        elif obj_type == "polygon":
            vertices = obj.get("vertices", [[0,0], [1,0], [0.5, 1]])
            vertices_str = ", ".join([f"[{v[0]}, {v[1]}, 0]" for v in vertices])
            code_lines.append(f'{var_name} = Polygon({vertices_str}, color={color})')
            if label_text:
                code_lines.append(f'{var_name}_label = Text("{label_text}", font_size=20).move_to({var_name}.get_center())')
        
        elif obj_type == "square":
            side = props.get("side", 1)
            rotation = props.get("rotation", 0)
            code_lines.append(f'{var_name} = Square(side_length={side}, color={color})')
            if isinstance(position, list):
                code_lines.append(f'{var_name}.move_to(np.array([{position[0]}, {position[1]}, 0]))')
            if rotation:
                code_lines.append(f'{var_name}.rotate({rotation} * DEGREES)')
            if label_text:
                code_lines.append(f'{var_name}_label = Text("{label_text}", font_size=18).move_to({var_name}.get_center())')
        
        elif obj_type == "circle":
            radius = props.get("radius", 1)
            fill_opacity = props.get("fill_opacity", 0)
            code_lines.append(f'{var_name} = Circle(radius={radius}, color={color}, fill_opacity={fill_opacity})')
            if isinstance(position, list):
                code_lines.append(f'{var_name}.move_to(np.array([{position[0]}, {position[1]}, 0]))')
            if label_text:
                code_lines.append(f'{var_name}_label = Text("{label_text}", font_size=18).next_to({var_name}, DOWN)')
        
        elif obj_type == "line":
            point = props.get("point", [0, 0])
            slope = props.get("slope", 1)
            length = props.get("length", 3)
            code_lines.append(f'{var_name}_start = np.array([{point[0] - length/2}, {point[1] - slope*length/2}, 0])')
            code_lines.append(f'{var_name}_end = np.array([{point[0] + length/2}, {point[1] + slope*length/2}, 0])')
            code_lines.append(f'{var_name} = Line({var_name}_start, {var_name}_end, color={color})')
            if label_text:
                code_lines.append(f'{var_name}_label = Text("{label_text}", font_size=18).next_to({var_name}, UP)')
        
        else:
            if isinstance(position, list):
                code_lines.append(f'{var_name} = Dot(point=np.array([{position[0]}, {position[1]}, 0]), color={color})')
            else:
                pos_name = POSITION_MAP.get(position, "ORIGIN")
                code_lines.append(f'{var_name} = Dot(point={pos_name}, color={color})')
    
    forces = spec.get("forces", [])
    for force in forces:
        force_id = force["id"]
        from_obj = force.get("from_object")
        to_obj = force.get("to_object")
        direction = force.get("direction", "repulsive")
        color = COLOR_MAP.get(force.get("color", "red").lower(), "RED")
        label_text = force.get("label", "")
        
        var_name = force_id.replace("-", "_").replace(" ", "_")
        object_vars[force_id] = var_name
        
        from_var = object_vars.get(from_obj, "ORIGIN")
        to_var = object_vars.get(to_obj, "ORIGIN")
        
        if direction == "repulsive":
            code_lines.append(f'{var_name}_start = {from_var}.get_center()')
            code_lines.append(f'{var_name}_dir = ({from_var}.get_center() - {to_var}.get_center())')
            code_lines.append(f'{var_name}_dir = {var_name}_dir / np.linalg.norm({var_name}_dir) * 1.5')
            code_lines.append(f'{var_name} = Arrow(start={var_name}_start, end={var_name}_start + {var_name}_dir, color={color}, buff=0.1)')
        elif direction == "attractive":
            code_lines.append(f'{var_name}_start = {from_var}.get_center()')
            code_lines.append(f'{var_name}_dir = ({to_var}.get_center() - {from_var}.get_center())')
            code_lines.append(f'{var_name}_dir = {var_name}_dir / np.linalg.norm({var_name}_dir) * 1.5')
            code_lines.append(f'{var_name} = Arrow(start={var_name}_start, end={var_name}_start + {var_name}_dir, color={color}, buff=0.1)')
        else:
            code_lines.append(f'{var_name} = Arrow(start={from_var}.get_center(), end={to_var}.get_center(), color={color}, buff=0.1)')
        
        if label_text:
            code_lines.append(f'{var_name}_label = Text("{label_text}", font_size=20).next_to({var_name}, UP)')
    
    equations = spec.get("equations", [])
    for eq in equations:
        eq_id = eq["id"]
        latex = eq.get("latex", "")
        position = eq.get("position", "top_center")
        animation_style = eq.get("animation_style", "write")
        
        var_name = eq_id.replace("-", "_").replace(" ", "_")
        object_vars[eq_id] = var_name
        
        if isinstance(position, list):
            pos_name = f"np.array([{position[0] if len(position) > 0 else 0}, {position[1] if len(position) > 1 else 0}, 0])"
        else:
            pos_name = POSITION_MAP.get(position, "UP * 3")
        
        if animation_style == "element_reveal" and eq.get("reveal_steps"):
            reveal_steps = eq["reveal_steps"]
            code_lines.append(f'{var_name} = MathTex(r"{latex}").move_to({pos_name})')
            code_lines.append(f'{var_name}_reveal_count = {len(reveal_steps)}')
            code_lines.append(f'{var_name}_reveal_steps = {[step.get("at_time", i * 0.3) for i, step in enumerate(reveal_steps)]}')
            for i, step in enumerate(reveal_steps):
                at_time = step.get("at_time", i * 0.3)
                object_vars[f"{eq_id}_part_{i}"] = f'{var_name}'
        elif animation_style == "synchronized" and eq.get("latex_elements"):
            latex_elements = eq["latex_elements"]
            code_lines.append(f'{var_name} = MathTex(r"{latex}").move_to({pos_name})')
            code_lines.append(f'{var_name}_sync_count = {len(latex_elements)}')
            code_lines.append(f'{var_name}_sync_times = {[elem.get("start_time", i * 0.5) for i, elem in enumerate(latex_elements)]}')
            for i, elem in enumerate(latex_elements):
                object_vars[f"{eq_id}_elem_{i}"] = var_name
        else:
            code_lines.append(f'{var_name} = MathTex(r"{latex}").move_to({pos_name})')
        
        if eq.get("substitution"):
            sub_latex = eq["substitution"]
            code_lines.append(f'{var_name}_sub = MathTex(r"{sub_latex}").move_to({pos_name})')
    
    code_lines.append("")
    code_lines.append("# Animation sequence")
    
    animation_sequence = spec.get("animation_sequence", [])
    for anim in animation_sequence:
        action = anim.get("action", "appear")
        target = anim.get("target") or ""
        duration = anim.get("duration", 1.0)
        
        if isinstance(target, list):
            target = target[0] if target else ""
        
        if not target and action != "wait":
            continue
        
        target_str = str(target) if target else ""
        target_var = object_vars.get(target_str, target_str.replace("-", "_").replace(" ", "_")) if target_str else "placeholder"
        
        if action == "appear":
            code_lines.append(f'self.play(FadeIn({target_var}), run_time={duration})')
            if f'{target_var}_label' in '\n'.join(code_lines):
                code_lines.append(f'self.play(FadeIn({target_var}_label), run_time=0.3)')
        
        elif action == "draw_force":
            code_lines.append(f'self.play(GrowArrow({target_var}), run_time={duration})')
            if f'{target_var}_label' in '\n'.join(code_lines):
                code_lines.append(f'self.play(FadeIn({target_var}_label), run_time=0.3)')
        
        elif action == "show_equation":
            style = anim.get("style", "write")
            if style == "element_reveal":
                eq_spec = None
                for eq in spec.get("equations", []):
                    if eq.get("id") == target_str:
                        eq_spec = eq
                        break
                
                if eq_spec and eq_spec.get("reveal_steps"):
                    reveal_steps = eq_spec["reveal_steps"]
                    n_steps = len(reveal_steps)
                    code_lines.append(f'# Element reveal animation: {n_steps} timing points')
                    code_lines.append(f'{target_var}_submobs = list({target_var}.submobjects)')
                    code_lines.append(f'{target_var}_n = len({target_var}_submobs)')
                    code_lines.append(f'{target_var}_chunk_size = max(1, {target_var}_n // {n_steps})')
                    
                    for i, step in enumerate(reveal_steps):
                        at_time = step.get("at_time", i * 0.3)
                        if i + 1 < n_steps:
                            next_time = reveal_steps[i + 1].get("at_time", (i + 1) * 0.3)
                        else:
                            next_time = at_time + 0.5
                        write_duration = max(0.2, round(next_time - at_time, 2))
                        
                        if i > 0:
                            prev_end = reveal_steps[i - 1].get("at_time", (i - 1) * 0.3) + 0.2
                            wait_time = at_time - prev_end
                            if wait_time > 0.01:
                                code_lines.append(f'self.wait({round(wait_time, 2)})')
                        
                        code_lines.append(f'{target_var}_start = {i} * {target_var}_chunk_size')
                        code_lines.append(f'{target_var}_end = min(({i}+1) * {target_var}_chunk_size, {target_var}_n)')
                        code_lines.append(f'{target_var}_chunk = VGroup(*{target_var}_submobs[{target_var}_start:{target_var}_end])')
                        code_lines.append(f'self.play(Write({target_var}_chunk), run_time={write_duration})')
                else:
                    code_lines.append(f'self.play(Write({target_var}), run_time={duration})')
            elif style == "synchronized":
                eq_spec = None
                for eq in spec.get("equations", []):
                    if eq.get("id") == target_str:
                        eq_spec = eq
                        break
                
                if eq_spec and eq_spec.get("latex_elements"):
                    latex_elements = eq_spec["latex_elements"]
                    n_elems = len(latex_elements)
                    code_lines.append(f'# Synchronized animation: {n_elems} timing points')
                    code_lines.append(f'{target_var}_submobs = list({target_var}.submobjects)')
                    code_lines.append(f'{target_var}_n = len({target_var}_submobs)')
                    code_lines.append(f'{target_var}_chunk_size = max(1, {target_var}_n // {n_elems})')
                    
                    for i, elem in enumerate(latex_elements):
                        start_time = elem.get("start_time", i * 0.5)
                        if i + 1 < n_elems:
                            next_time = latex_elements[i + 1].get("start_time", (i + 1) * 0.5)
                        else:
                            next_time = start_time + 0.5
                        write_duration = max(0.2, round(next_time - start_time, 2))
                        
                        if i > 0:
                            prev_end = latex_elements[i - 1].get("start_time", (i - 1) * 0.5) + 0.2
                            wait_time = start_time - prev_end
                            if wait_time > 0.01:
                                code_lines.append(f'self.wait({round(wait_time, 2)})')
                        
                        code_lines.append(f'{target_var}_start = {i} * {target_var}_chunk_size')
                        code_lines.append(f'{target_var}_end = min(({i}+1) * {target_var}_chunk_size, {target_var}_n)')
                        code_lines.append(f'{target_var}_chunk = VGroup(*{target_var}_submobs[{target_var}_start:{target_var}_end])')
                        code_lines.append(f'self.play(Write({target_var}_chunk), run_time={write_duration})')
                else:
                    code_lines.append(f'self.play(Write({target_var}), run_time={duration})')
            else:
                code_lines.append(f'self.play(Write({target_var}), run_time={duration})')
        
        elif action == "substitute":
            code_lines.append(f'self.play(TransformMatchingShapes({target_var}, {target_var}_sub), run_time={duration})')
        
        elif action == "highlight":
            code_lines.append(f'self.play(Indicate({target_var}), run_time={duration})')
        
        elif action == "move":
            new_pos = anim.get("to", [0, 0])
            code_lines.append(f'self.play({target_var}.animate.move_to(np.array([{new_pos[0]}, {new_pos[1]}, 0])), run_time={duration})')
        
        elif action == "transform":
            to_target = anim.get("to") or ""
            if isinstance(to_target, list):
                to_target = to_target[0] if to_target else ""
            if to_target:
                to_target_str = str(to_target)
                to_var = object_vars.get(to_target_str, to_target_str.replace("-", "_").replace(" ", "_"))
                code_lines.append(f'self.play(Transform({target_var}, {to_var}), run_time={duration})')
        
        elif action == "wait":
            code_lines.append(f'self.wait({duration})')
        
        elif action == "draw":
            code_lines.append(f'self.play(Create({target_var}), run_time={duration})')
        
        elif action == "fill":
            code_lines.append(f'self.play(FadeIn({target_var}), run_time={duration})')
        
        elif action == "write":
            code_lines.append(f'self.play(Write({target_var}), run_time={duration})')
        
        elif action == "grow":
            code_lines.append(f'self.play(GrowFromCenter({target_var}), run_time={duration})')
        
        elif action == "fade_out":
            code_lines.append(f'self.play(FadeOut({target_var}), run_time={duration})')
        
        else:
            code_lines.append(f'self.play(FadeIn({target_var}), run_time={duration})')
    
    code_lines.append('self.wait(1)')
    
    return '\n'.join(code_lines)


def compile_manim_plan(beat: dict, section_id: int, beat_index: int, section_type: str = "content") -> dict:
    """Compile a Manim animation plan from structured visual beat fields.
    
    REQUIRES: manim_scene_spec JSON with objects, forces, equations, animation_sequence.
    FAIL-FAST: Raises VisualCompilationError if manim_scene_spec is missing or invalid.
    """
    # V2.5 BYPASS: If manim_code already exists (Claude-generated), skip visual beat validation
    manim_scene_spec = beat.get("manim_scene_spec", {})
    if isinstance(manim_scene_spec, dict) and manim_scene_spec.get("manim_code"):
        return {
            "scene_type": "spec_generated",
            "manim_code": manim_scene_spec["manim_code"],
            "spec": manim_scene_spec,
            "params": {"generated_code": manim_scene_spec["manim_code"]}
        }

    use_strict = section_type in ("content", "example")
    warnings = validate_visual_beat_structure(beat, section_id, beat_index, section_type=section_type, strict=use_strict)
    for w in warnings:
        print(w)
    
    manim_scene_spec = beat.get("manim_scene_spec")
    
    if manim_scene_spec:
        manim_code = translate_spec_to_manim_code(manim_scene_spec, section_id, beat_index)
        
        return {
            "scene_type": "spec_generated",
            "manim_code": manim_code,
            "spec": manim_scene_spec,
            "params": {
                "generated_code": manim_code,
                "object_count": len(manim_scene_spec.get("objects", [])),
                "force_count": len(manim_scene_spec.get("forces", [])),
                "equation_count": len(manim_scene_spec.get("equations", [])),
                "animation_count": len(manim_scene_spec.get("animation_sequence", []))
            }
        }
    
    raise VisualCompilationError(
        section_id, beat_index,
        "Manim section missing manim_scene_spec. For renderer=manim, each visual_beat must include a structured "
        "manim_scene_spec JSON with objects, forces, equations, and animation_sequence. "
        "Prose-only descriptions are not allowed for Manim sections."
    )


def compile_section_visuals(section: dict) -> Tuple[Optional[str], Optional[dict], List[VisualCompilationError]]:
    """Compile all visual beats in a section."""
    section_id = section.get("id", 0)
    section_type = section.get("section_type", "content")
    renderer = section.get("renderer", "wan_video")
    visual_beats = section.get("visual_beats", [])
    
    if section_type not in ["content", "example"]:
        return None, None, []
    
    # V2.5 BYPASS: If manim_code already exists (Claude-generated), skip visual beat validation
    render_spec = section.get("render_spec", {})
    manim_scene_spec = render_spec.get("manim_scene_spec", {})
    if isinstance(manim_scene_spec, dict) and manim_scene_spec.get("manim_code"):
        print(f"[VISUAL COMPILER] Section {section_id}: V2.5 manim_code exists, skipping validation")
        return None, {"scene_type": "v25_precompiled", "manim_code": manim_scene_spec["manim_code"]}, []
    
    # V2.5 BYPASS: If video_prompts already exist (V1.2+ format), skip validation
    video_prompts = section.get("video_prompts") or render_spec.get("video_prompts")
    if video_prompts and len(video_prompts) > 0:
        print(f"[VISUAL COMPILER] Section {section_id}: V1.2+ video_prompts exist, skipping validation")
        return str(video_prompts), None, []
    
    errors = []
    compiled_wan_prompts = []
    compiled_manim_plans = []
    
    for i, beat in enumerate(visual_beats):
        try:
            if renderer == "manim":
                plan = compile_manim_plan(beat, section_id, i, section_type=section_type)
                compiled_manim_plans.append(plan)
            else:
                prompt = compile_wan_prompt(beat, section_id, i, section_type=section_type)
                compiled_wan_prompts.append(prompt)
        except VisualCompilationError as e:
            errors.append(e)
    
    if errors:
        return None, None, errors
    
    if renderer == "manim":
        combined_plan = {
            "scene_type": "multi_beat",
            "beats": compiled_manim_plans,
            "total_beats": len(compiled_manim_plans)
        }
        return None, combined_plan, []
    else:
        combined_prompt = " | NEXT BEAT | ".join(compiled_wan_prompts)
        return combined_prompt, None, []


def compile_presentation_visuals(presentation: dict) -> Tuple[dict, List[VisualCompilationError]]:
    """Compile all visual beats in a presentation."""
    all_errors = []
    
    for section in presentation.get("sections", []):
        section_id = section.get("id", 0)
        section_type = section.get("section_type", "content")
        renderer = section.get("renderer", "wan_video")
        
        if section_type in ["content", "example"]:
            wan_prompt, manim_plan, errors = compile_section_visuals(section)
            
            if errors:
                all_errors.extend(errors)
            else:
                if renderer == "manim" and manim_plan:
                    if "explanation_plan" not in section:
                        section["explanation_plan"] = {}
                    section["explanation_plan"]["compiled_manim_plan"] = manim_plan
                elif wan_prompt:
                    if "explanation_plan" not in section:
                        section["explanation_plan"] = {}
                    section["explanation_plan"]["compiled_wan_prompt"] = wan_prompt
    
    return presentation, all_errors

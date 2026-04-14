"""
Manim Video Runner - Generates mathematical animations from visual beats

CRITICAL: NO placeholder fallbacks. Fail if scene is generic.
Each visual beat should produce specific Manim code, not E=mc² defaults.
"""

import os
import subprocess
import tempfile
import shutil
import json
from pathlib import Path
from typing import Union, Optional, List, Dict, Any
from render.render_trace import log_render_prompt


class ManimRenderError(Exception):
    """Raised when Manim rendering fails - NO fallback to placeholders."""

    pass


MANIM_TEMPLATES = {
    "equation": """
from manim import *

class EquationScene(Scene):
    def construct(self):
        equation = MathTex(r"{equation}")
        equation.scale({scale})
        self.play(Write(equation), run_time=2)
        self.wait({wait_time})
""",
    "graph": """
from manim import *

class GraphScene(Scene):
    def construct(self):
        axes = Axes(
            x_range=[{x_min}, {x_max}, 1],
            y_range=[{y_min}, {y_max}, 1],
            axis_config={{"include_numbers": True}}
        )
        graph = axes.plot(lambda x: {function}, color=BLUE)
        label = MathTex(r"{label}").next_to(graph, UP)
        
        self.play(Create(axes), run_time=1.5)
        self.play(Create(graph), run_time=2)
        self.play(Write(label), run_time=1)
        self.wait({wait_time})
""",
    "geometry": """
from manim import *

class GeometryScene(Scene):
    def construct(self):
        shapes = VGroup()
        {shape_code}
        self.play(Create(shapes), run_time=2)
        self.wait({wait_time})
""",
    "derivation": """
from manim import *

class DerivationScene(Scene):
    def construct(self):
        steps = [{steps}]
        current = None
        for i, step in enumerate(steps):
            tex = MathTex(step)
            if current:
                tex.next_to(current, DOWN, buff=0.5)
            self.play(Write(tex), run_time=1.5)
            current = tex
            self.wait(0.5)
        self.wait({wait_time})
""",
}

# Placeholder equations that indicate generic/fallback content
BANNED_PLACEHOLDER_EQUATIONS = [
    "E = mc^2",
    "E=mc^2",
    "e = mc^2",
    "a^2 + b^2 = c^2",
    "x + 1 = 3",
    "f(x) = x",
    "y = x",
    "Step 1",
    "Step 2",
]


def render_manim_video(
    topic: dict,
    output_dir: str,
    dry_run: bool = False,
    trace_output_dir: Optional[str] = None,
) -> Union[str, List[str]]:
    """
    Render Manim video for a section with visual beats.

    FAIL-FAST: No placeholder fallbacks. Raise ManimRenderError if:
    - No compiled_manim_plan available
    - Plan uses generic/placeholder equations
    - Manim execution fails

    v1.2 MODE: If v12_manim_scene_spec is present, render single video for entire section
    using translate_spec_to_manim_code() directly. Bypasses visual_beats iteration.

    Multi-beat rendering: Each visual_beat renders as topic_{id}_beat_{i}.mp4
    Returns list of paths for multi-beat, single path for single-beat.
    """
    from core.visual_compiler import (
        translate_spec_to_manim_code,
        validate_manim_scene_spec,
    )

    topic_id = topic.get("section_id", topic.get("id", 1))
    topic_title = topic.get("title", "Untitled")
    section_type = topic.get("section_type", "content")
    explanation_plan = topic.get("explanation_plan", {})
    visual_beats = topic.get("visual_beats", [])
    duration = topic.get("duration", 30)

    # Extract v1.5 code if present
    v15_manim_code = topic.get("v15_manim_code") or explanation_plan.get(
        "v15_manim_code"
    )

    # Get narration_segments for per-beat duration lookup
    narration_segments = topic.get("narration_segments", [])

    # v1.5/V2.5 MODE: Check for pre-generated Python manim_code (bypasses translation step)
    # Check V2.5 location first (render_spec)
    render_spec = topic.get("render_spec", {})

    # NEW V2.5 SYNC: Check for per-segment Manim specs FIRST
    segment_specs = render_spec.get("segment_specs", [])
    manim_segment_specs = [s for s in segment_specs if s.get("renderer") == "manim"]
    
    # V3 updated schema: LLM outputs an explicit manim_beats array at root of render_spec
    if not manim_segment_specs and ("manim_beats" in render_spec or "manim_segment_specs" in render_spec):
        manim_segment_specs = render_spec.get("manim_beats") or render_spec.get("manim_segment_specs", [])
        for s in manim_segment_specs:
            s["renderer"] = "manim"

    if manim_segment_specs:
        print(
            f"[MANIM V2.5] Section {topic_id}: Rendering {len(manim_segment_specs)} per-segment videos"
        )
        return _render_manim_segment_specs(
            specs=manim_segment_specs,
            topic_id=topic_id,
            topic_title=topic_title,
            output_dir=output_dir,
            dry_run=dry_run,
            trace_output_dir=trace_output_dir,
        )

    # V3 MODE: Check for pre-generated manim code file from V3 pipeline
    manim_code_path = topic.get("manim_code_path")
    if manim_code_path:
        abs_path = Path(output_dir).parent / manim_code_path
        if abs_path.exists():
            print(
                f"[MANIM V3] Section {topic_id}: Using pre-generated code from {manim_code_path}"
            )
            with open(abs_path, "r", encoding="utf-8") as f:
                manim_code = f.read()
            return _render_v3_manim_code(
                manim_code=manim_code,
                topic_id=topic_id,
                topic_title=topic_title,
                output_dir=output_dir,
                dry_run=dry_run,
            )

    if v15_manim_code:
        return _render_v15_manim_code(
            manim_code=v15_manim_code,
            topic_id=topic_id,
            topic_title=topic_title,
            section_type=section_type,
            duration=duration,
            output_dir=output_dir,
            dry_run=dry_run,
            trace_output_dir=trace_output_dir,
        )

    # v1.2 MODE: Check for section-level manim_scene_spec (bypasses visual_beats iteration)
    v12_manim_scene_spec = explanation_plan.get("v12_manim_scene_spec")
    if v12_manim_scene_spec:
        print(
            f"[MANIM v1.2] Section {topic_id}: Using section-level manim_scene_spec directly"
        )
        return _render_v12_manim_spec(
            spec=v12_manim_scene_spec,
            topic_id=topic_id,
            topic_title=topic_title,
            section_type=section_type,
            duration=duration,
            output_dir=output_dir,
            dry_run=dry_run,
            trace_output_dir=trace_output_dir,
        )

    internal_segment_specs = topic.get("_manim_segment_specs", [])
    if internal_segment_specs:
        print(
            f"[MANIM V2.5] Section {topic_id}: Rendering {len(internal_segment_specs)} per-segment videos (internal)"
        )
        return _render_manim_segment_specs(
            specs=internal_segment_specs,
            topic_id=topic_id,
            topic_title=topic_title,
            output_dir=output_dir,
            dry_run=dry_run,
            trace_output_dir=trace_output_dir,
            topic=topic,
        )

    # NEW V2.5 SYNC: Check for sync-split beats (fallback for older code)
    video_prompts = topic.get("video_prompts", [])
    if video_prompts and isinstance(video_prompts, list) and len(video_prompts) > 0:
        print(
            f"[MANIM V2.5] Section {topic_id}: Rendering {len(video_prompts)} sync-split beats"
        )
        # Reuse _render_all_beats logic but adapted for pre-split video_prompts
        return _render_sync_split_manim_beats(
            video_prompts=video_prompts,
            topic_id=topic_id,
            topic_title=topic_title,
            section_type=section_type,
            output_dir=output_dir,
            dry_run=dry_run,
            trace_output_dir=trace_output_dir,
        )

    # STRICT V2.5 GUARD: If we are in V2.5 mode (render_spec exists), DO NOT FALLBACK to V1.x visual beats
    # This ensures we fail fast if code generation failed, rather than producing broken legacy visualizations.
    if topic.get("render_spec") and not topic.get("video_prompts"):
        # Exception: if video_prompts exist, we handled them above (or should have).
        # Double check if we missed them.
        raise ManimRenderError(
            f"Section {topic_id}: Strict V2.5 Check Failed. "
            f"renderer='manim' but no valid manim_code found in render_spec. "
            f"Fallback to legacy visual_beats is FORBIDDEN."
        )

    # Multi-beat rendering: each beat gets its own video file
    if len(visual_beats) > 1:
        return _render_all_beats(
            visual_beats=visual_beats,
            topic_id=topic_id,
            topic_title=topic_title,
            section_type=section_type,
            total_duration=duration,
            narration_segments=narration_segments,
            output_dir=output_dir,
            dry_run=dry_run,
            trace_output_dir=trace_output_dir,
        )

    # Check for compiled Manim plan from visual_compiler
    compiled_manim_plan = explanation_plan.get("compiled_manim_plan")
    legacy_manim_plan = explanation_plan.get("manim_plan", {})

    # Use compiled plan if available, else legacy
    manim_plan = compiled_manim_plan or legacy_manim_plan

    if not manim_plan or not manim_plan.get("scene_type"):
        # Try to compile from visual beats directly
        if visual_beats:
            manim_plan = _compile_beats_to_manim_plan(visual_beats, topic_id)
        else:
            raise ManimRenderError(
                f"Section {topic_id}: No Manim plan available. "
                f"Manim sections must have visual_beats or explicit manim_plan."
            )

    scene_type = manim_plan.get("scene_type", "equation")

    # Handle multi_beat compiled plans with beats array (but no visual_beats)
    if scene_type == "multi_beat":
        beats = manim_plan.get("beats", [])
        if beats and len(beats) > 1:
            return _render_compiled_multi_beat(
                beats=beats,
                topic_id=topic_id,
                topic_title=topic_title,
                section_type=section_type,
                total_duration=duration,
                output_dir=output_dir,
                dry_run=dry_run,
                trace_output_dir=trace_output_dir,
            )

    # Handle spec_generated plans - use pre-generated Manim code
    if scene_type == "spec_generated":
        manim_code = manim_plan.get("manim_code", "")
        params = manim_plan.get("params", {})

        if not manim_code:
            raise ManimRenderError(
                f"Section {topic_id}: spec_generated plan has no manim_code"
            )

        print(
            f"[MANIM] spec_generated: {params.get('object_count', 0)} objects, "
            f"{params.get('force_count', 0)} forces, "
            f"{params.get('equation_count', 0)} equations"
        )

        output_path = str(Path(output_dir) / f"topic_{topic_id}.mp4")

        log_render_prompt(
            section_id=topic_id,
            section_title=topic_title,
            renderer="manim_spec",
            prompt=manim_code,
            output_path=output_path,
            extra_data={
                "section_type": section_type,
                "scene_type": "spec_generated",
                "duration": duration,
                "dry_run": dry_run,
                "spec": manim_plan.get("spec", {}),
                "from_compiled_plan": True,
            },
            trace_output_dir=trace_output_dir,
        )

        if dry_run:
            print(f"[DRY RUN] Manim spec render for section {topic_id}")
            return _create_dry_run_marker(topic_id, output_path, duration, manim_code)

        return _execute_spec_generated_render(
            manim_code=manim_code,
            duration=duration,
            output_path=output_path,
            topic_id=topic_id,
        )

    # Handle multi_beat plans - extract first beat for rendering
    if scene_type == "multi_beat":
        beats = manim_plan.get("beats", [])
        if not beats:
            raise ManimRenderError(f"Section {topic_id}: multi_beat plan has no beats")
        # Check if first beat is spec_generated
        first_beat = beats[0]
        first_scene_type = first_beat.get("scene_type", "equation")

        if first_scene_type == "spec_generated":
            manim_code = first_beat.get("manim_code", "")
            params = first_beat.get("params", {})

            print(
                f"[MANIM] Multi-beat spec_generated: using first of {len(beats)} beats"
            )

            output_path = str(Path(output_dir) / f"topic_{topic_id}.mp4")

            log_render_prompt(
                section_id=topic_id,
                section_title=topic_title,
                renderer="manim_spec",
                prompt=manim_code,
                output_path=output_path,
                extra_data={
                    "section_type": section_type,
                    "scene_type": "spec_generated",
                    "duration": duration,
                    "dry_run": dry_run,
                    "beat_count": len(beats),
                },
                trace_output_dir=trace_output_dir,
            )

            if dry_run:
                print(f"[DRY RUN] Manim spec render for section {topic_id}")
                return _create_dry_run_marker(
                    topic_id, output_path, duration, manim_code
                )

            return _execute_spec_generated_render(
                manim_code=manim_code,
                duration=duration,
                output_path=output_path,
                topic_id=topic_id,
            )

        # Legacy template-based beats
        scene_type = first_scene_type
        params = first_beat.get("params", {})
        print(
            f"[MANIM] Multi-beat plan: using first of {len(beats)} beats (scene_type={scene_type})"
        )
    else:
        params = manim_plan.get("params", {})

    # FAIL-FAST: Check for placeholder/generic content
    _validate_not_placeholder(params, topic_id, topic_title)

    output_path = str(Path(output_dir) / f"topic_{topic_id}.mp4")

    log_render_prompt(
        section_id=topic_id,
        section_title=topic_title,
        renderer="manim",
        prompt=json.dumps(manim_plan, indent=2),
        output_path=output_path,
        extra_data={
            "section_type": section_type,
            "scene_type": scene_type,
            "duration": duration,
            "dry_run": dry_run,
            "params": params,
            "from_compiled_plan": compiled_manim_plan is not None,
        },
        trace_output_dir=trace_output_dir,
    )

    # Generate scene code
    template = MANIM_TEMPLATES.get(scene_type, MANIM_TEMPLATES["equation"])

    # NO DEFAULT PARAMS - use what's provided or fail
    render_params = {"wait_time": max(1, duration - 5), **params}

    try:
        scene_code = template.format(**render_params)
    except KeyError as e:
        raise ManimRenderError(
            f"Section {topic_id}: Missing required Manim parameter: {e}. "
            f"Scene type '{scene_type}' requires specific parameters. "
            f"Provided: {list(params.keys())}"
        )

    # Log generated code
    log_render_prompt(
        section_id=topic_id,
        section_title=f"{topic_title} (generated code)",
        renderer="manim_code",
        prompt=scene_code,
        output_path=output_path,
        extra_data={"scene_type": scene_type, "dry_run": dry_run},
        trace_output_dir=trace_output_dir,
    )

    if dry_run:
        print(f"[DRY RUN] Manim render for section {topic_id}")
        return _create_dry_run_marker(topic_id, output_path, duration, scene_code)

    # Execute Manim render - NO FALLBACK
    result = _execute_manim_render(
        scene_type=scene_type,
        params=params,
        duration=duration,
        output_path=output_path,
        topic_id=topic_id,
        scene_code=scene_code,
    )

    if not result or not os.path.exists(result):
        raise ManimRenderError(
            f"Section {topic_id}: Manim render produced no output. "
            f"Check Manim installation and scene code."
        )

    return result


def _render_v12_manim_spec(
    spec: dict,
    topic_id: int,
    topic_title: str,
    section_type: str,
    duration: float,
    output_dir: str,
    dry_run: bool = False,
    trace_output_dir: Optional[str] = None,
) -> str:
    """
    Render v1.2 section-level manim_scene_spec as a single video.

    v1.2 MODE: The Director LLM provides manim_scene_spec at section level with:
    - objects: List of scene objects with id, type, position, properties
    - animation_sequence: List of animation actions with target, action, duration

    We translate this directly to Manim code using translate_spec_to_manim_code()
    and render a single video for the entire section.
    """
    from core.visual_compiler import (
        translate_spec_to_manim_code,
        VisualCompilationError,
    )

    output_path = str(Path(output_dir) / f"topic_{topic_id}.mp4")

    objects = spec.get("objects", [])
    animations = spec.get("animation_sequence", [])

    print(
        f"[MANIM v1.2] Rendering: {len(objects)} objects, {len(animations)} animations, duration={duration}s"
    )

    try:
        manim_code = translate_spec_to_manim_code(spec, topic_id, 0)
    except VisualCompilationError as e:
        raise ManimRenderError(
            f"Section {topic_id}: v1.2 spec translation failed - {e.reason}"
        )
    except Exception as e:
        raise ManimRenderError(
            f"Section {topic_id}: v1.2 spec translation error - {str(e)}"
        )

    log_render_prompt(
        section_id=topic_id,
        section_title=topic_title,
        renderer="manim_v12",
        prompt=manim_code,
        output_path=output_path,
        extra_data={
            "section_type": section_type,
            "scene_type": "v12_spec_generated",
            "object_count": len(objects),
            "animation_count": len(animations),
            "duration": duration,
            "dry_run": dry_run,
        },
        trace_output_dir=trace_output_dir,
    )

    if dry_run:
        print(f"[DRY RUN] Manim v1.2 render for section {topic_id}")
        return _create_dry_run_marker(topic_id, output_path, duration, manim_code)

    result = _execute_spec_generated_render(
        manim_code=manim_code,
        duration=duration,
        output_path=output_path,
        topic_id=topic_id,
    )

    if not result or not os.path.exists(result):
        raise ManimRenderError(
            f"Section {topic_id}: Manim v1.2 render produced no output. "
            f"Check Manim installation and scene code."
        )

    print(f"[MANIM v1.2] Rendered: {result}")
    return result


def _render_v15_manim_code(
    manim_code: str,
    topic_id: int,
    topic_title: str,
    section_type: str,
    duration: float,
    output_dir: str,
    dry_run: bool = False,
    trace_output_dir: Optional[str] = None,
) -> str:
    """
    Render v1.5 pre-generated Manim Python code.

    v1.5 MODE: Claude Sonnet generates complete Python Manim code directly.
    This bypasses the spec translation step - we execute the code directly.
    """
    output_path = str(Path(output_dir) / f"topic_{topic_id}.mp4")

    print(
        f"[MANIM v1.5] Rendering pre-generated code: {len(manim_code)} chars, duration={duration}s"
    )

    log_render_prompt(
        section_id=topic_id,
        section_title=topic_title,
        renderer="manim_v15",
        prompt=manim_code,
        output_path=output_path,
        extra_data={
            "section_type": section_type,
            "scene_type": "v15_llm_generated",
            "code_length": len(manim_code),
            "duration": duration,
            "dry_run": dry_run,
        },
        trace_output_dir=trace_output_dir,
    )

    if dry_run:
        print(f"[DRY RUN] Manim v1.5 render for section {topic_id}")
        return _create_dry_run_marker(topic_id, output_path, duration, manim_code)

    result = _execute_spec_generated_render(
        manim_code=manim_code,
        duration=duration,
        output_path=output_path,
        topic_id=topic_id,
    )

    if not result or not os.path.exists(result):
        raise ManimRenderError(
            f"Section {topic_id}: Manim v1.5 render produced no output. "
            f"Check Manim installation and generated code."
        )

    print(f"[MANIM v1.5] Rendered: {result}")
    return result


def _render_v3_manim_code(
    manim_code: str,
    topic_id: int,
    topic_title: str,
    output_dir: str,
    dry_run: bool = False,
) -> str:
    """
    Render pre-generated V3 manim Python code from file.

    V3 MODE: The V3 pipeline generates complete Python manim code and stores it
    in a file (manim_code_path). This function reads that file and renders it.
    """
    output_path = str(Path(output_dir) / f"topic_{topic_id}.mp4")

    print(f"[MANIM V3] Rendering V3 pre-generated code: {len(manim_code)} chars")

    if dry_run:
        print(f"[DRY RUN] Manim V3 render for section {topic_id}")
        return output_path

    # The V3 code should be a complete scene
    # Execute it using _execute_spec_generated_render
    result = _execute_spec_generated_render(
        manim_code=manim_code,
        duration=0,  # Duration from code itself
        output_path=output_path,
        topic_id=topic_id,
    )

    if not result or not os.path.exists(result):
        raise ManimRenderError(
            f"Section {topic_id}: Manim V3 render produced no output. "
            f"Check Manim installation and generated code."
        )

    print(f"[MANIM V3] Rendered: {result}")
    return result


def _get_beat_duration(
    beat_index: int, visual_beats: list, narration_segments: list, total_duration: float
) -> float:
    """
    Get duration for a specific beat from LLM-provided data.

    Priority:
    1. visual_beat.duration (if LLM provided it)
    2. Matching narration_segment.duration (by segment_id)
    3. Fallback: total_duration / beat_count

    NOTE: Preserves fractional durations - LLM timing is authoritative.
    """
    beat = visual_beats[beat_index] if beat_index < len(visual_beats) else {}

    # Check beat-level duration (preserve float)
    if beat.get("duration"):
        return float(beat["duration"])

    # Check matching narration segment (segment_id is 1-indexed usually)
    segment_id = beat.get("segment_id", beat_index + 1)
    for seg in narration_segments:
        if seg.get("id") == segment_id:
            if seg.get("duration"):
                return float(seg["duration"])

    # Fallback: uniform distribution (preserve float)
    return (
        float(total_duration) / len(visual_beats)
        if visual_beats
        else float(total_duration)
    )


def _render_all_beats(
    visual_beats: list,
    topic_id: int,
    topic_title: str,
    section_type: str,
    total_duration: float,
    narration_segments: list,
    output_dir: str,
    dry_run: bool = False,
    trace_output_dir: Optional[str] = None,
) -> List[str]:
    """
    Render ALL visual beats as separate video files.

    Each beat renders as topic_{id}_beat_{i}.mp4 where i is 0-indexed.
    The player detects these files and switches between them based on timing.

    STANDALONE BEAT RULE: Each beat's manim_scene_spec is a complete snapshot
    of what should be visible at that moment. The LLM decides what persists;
    we just render each beat independently.

    Duration is sourced from LLM-provided visual_beat.duration or narration_segments.
    """
    from core.visual_compiler import compile_manim_plan, VisualCompilationError

    rendered_paths = []

    print(
        f"[MANIM] Multi-beat rendering: {len(visual_beats)} beats for section {topic_id}"
    )

    for beat_index, beat in enumerate(visual_beats):
        output_path = str(Path(output_dir) / f"topic_{topic_id}_beat_{beat_index}.mp4")

        # Get duration from LLM-provided data (not uniform division)
        beat_duration = _get_beat_duration(
            beat_index, visual_beats, narration_segments, total_duration
        )

        try:
            plan = compile_manim_plan(beat, topic_id, beat_index)
        except VisualCompilationError as e:
            raise ManimRenderError(
                f"Section {topic_id} beat {beat_index}: Compilation failed - {e.reason}"
            )

        scene_type = plan.get("scene_type", "equation")

        if scene_type == "spec_generated":
            manim_code = plan.get("manim_code", "")
            params = plan.get("params", {})

            if not manim_code:
                raise ManimRenderError(
                    f"Section {topic_id} beat {beat_index}: spec_generated has no manim_code"
                )

            print(
                f"[MANIM] Beat {beat_index}: {params.get('object_count', 0)} objects, "
                f"{params.get('force_count', 0)} forces, "
                f"{params.get('equation_count', 0)} equations, duration={beat_duration}s"
            )

            log_render_prompt(
                section_id=topic_id,
                section_title=f"{topic_title} (beat {beat_index})",
                renderer="manim_spec",
                prompt=manim_code,
                output_path=output_path,
                extra_data={
                    "section_type": section_type,
                    "scene_type": "spec_generated",
                    "beat_index": beat_index,
                    "beat_count": len(visual_beats),
                    "duration": beat_duration,
                    "dry_run": dry_run,
                },
                trace_output_dir=trace_output_dir,
            )

            if dry_run:
                print(f"[DRY RUN] Manim beat {beat_index} for section {topic_id}")
                marker_path = _create_dry_run_marker(
                    topic_id, output_path, beat_duration, manim_code
                )
                rendered_paths.append(marker_path)
            else:
                result = _execute_spec_generated_render(
                    manim_code=manim_code,
                    duration=beat_duration,
                    output_path=output_path,
                    topic_id=topic_id,
                )
                rendered_paths.append(result)
                print(f"[MANIM] Rendered beat {beat_index}: {result}")
        else:
            # Legacy template-based rendering
            params = plan.get("params", {})
            _validate_not_placeholder(params, topic_id, topic_title)

            template = MANIM_TEMPLATES.get(scene_type, MANIM_TEMPLATES["equation"])
            render_params = {"wait_time": max(1, beat_duration - 5), **params}

            try:
                scene_code = template.format(**render_params)
            except KeyError as e:
                raise ManimRenderError(
                    f"Section {topic_id} beat {beat_index}: Missing Manim parameter: {e}"
                )

            log_render_prompt(
                section_id=topic_id,
                section_title=f"{topic_title} (beat {beat_index})",
                renderer="manim_code",
                prompt=scene_code,
                output_path=output_path,
                extra_data={
                    "scene_type": scene_type,
                    "beat_index": beat_index,
                    "duration": beat_duration,
                    "dry_run": dry_run,
                },
                trace_output_dir=trace_output_dir,
            )

            if dry_run:
                print(f"[DRY RUN] Manim beat {beat_index} for section {topic_id}")
                marker_path = _create_dry_run_marker(
                    topic_id, output_path, beat_duration, scene_code
                )
                rendered_paths.append(marker_path)
            else:
                result = _execute_manim_render(
                    scene_type=scene_type,
                    params=params,
                    duration=beat_duration,
                    output_path=output_path,
                    topic_id=topic_id,
                    scene_code=scene_code,
                )
                rendered_paths.append(result)
                print(f"[MANIM] Rendered beat {beat_index}: {result}")

    print(f"[MANIM] Completed {len(rendered_paths)} beat videos for section {topic_id}")
    return rendered_paths


def _render_manim_segment_specs(
    specs: list,
    topic_id: int,
    topic_title: str,
    output_dir: str,
    dry_run: bool = False,
    trace_output_dir: Optional[str] = None,
    topic: Optional[dict] = None,
    aspect_ratio: str = "16:9",
) -> List[str]:
    """
    Render per-segment Manim videos.

    V3 MODE: Each spec has py_path (pre-generated .py from Phase 3.5).
             Reads the file and renders it — no LLM call.
    V2 MODE: Each spec has manim_scene_spec.
             Calls ManimCodeGenerator to generate code, then renders.

    In both modes, stores result in seg.beat_videos[] for player sync.
    """
    from core.agents.manim_code_generator import ManimCodeGenerator

    generator = ManimCodeGenerator()
    rendered_paths = []

    for idx, spec in enumerate(specs):
        seg_id = spec.get("segment_id", f"beat_{idx}")
        # Prefer explicit beat_id (e.g. "eq_beat_1" from explanation_visual) so
        # quiz beats don't overwrite main-section beat_0, beat_1 files.
        # Falls back to index-based name for normal content beats.
        beat_id = spec.get("beat_id") or f"beat_{idx}"
        import re as _re
        safe_beat = _re.sub(r"[^\w\-]", "_", str(beat_id))
        output_path = str(Path(output_dir) / f"topic_{topic_id}_{safe_beat}.mp4")

        # Duration lookup
        duration = spec.get("duration_seconds")
        seg_text = "Visualizing segment content"

        if topic:
            narration_segs = topic.get("narration", {}).get("segments", [])
            for seg in narration_segs:
                if seg.get("segment_id") == seg_id:
                    if not duration:
                        duration = seg.get("duration_seconds")
                    seg_text = seg.get("text", seg_text)
                    break

        if not duration:
            duration = 15.0  # Fallback

        if dry_run:
            result = _create_dry_run_marker(
                f"{topic_id}_{idx}", output_path, duration,
                f"Segment {seg_id} (dry run)"
            )
        else:
            try:
                # Skip if output already exists (idempotent retry)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    print(f"  [MANIM] Skipping existing beat: {output_path}")
                    result = output_path
                else:
                    # ── V3 MODE: py_path pre-generated in Phase 3.5 ──────
                    py_path = spec.get("py_path")

                    # DOCKER PATH FIX: stored path may use /app/... container prefix.
                    # If the path doesn't exist as-is, reconstruct it from the filename
                    # relative to the manim/ dir next to output_dir (videos/).
                    if py_path and not os.path.exists(py_path):
                        filename = os.path.basename(py_path)
                        # output_dir is typically .../videos/; manim/ is at the same level
                        manim_dir_candidate = Path(output_dir).parent / "manim"
                        remapped = manim_dir_candidate / filename
                        if remapped.exists():
                            print(f"  [MANIM V3] Docker path remapped: {py_path} → {remapped}")
                            py_path = str(remapped)

                    if py_path and os.path.exists(py_path):
                        print(f"  [MANIM V3] Using pre-generated code: {py_path}")
                        with open(py_path, "r", encoding="utf-8") as fh:
                            manim_code = fh.read()
                    else:
                        # ── V2 MODE: generate code from manim_scene_spec ──
                        manim_spec = spec.get("manim_scene_spec", "")
                        if not manim_spec:
                            raise ManimRenderError(
                                f"Segment {seg_id}: no py_path and no manim_scene_spec"
                            )
                        beat_data = {
                            "section_title": f"{topic_title} - {seg_id}",
                            "manim_spec": manim_spec,
                            "narration_segments": [
                                {"text": seg_text, "duration": duration}
                            ],
                            "duration": duration,
                            "target_duration_seconds": duration,
                        }
                        manim_code = generator.generate_code(beat_data)
                        if not manim_code:
                            raise ManimRenderError(
                                f"Segment {seg_id} code gen returned empty code"
                            )

                    # Execute render
                    result = _execute_spec_generated_render(
                        manim_code=manim_code,
                        duration=duration,
                        output_path=output_path,
                        topic_id=f"{topic_id}_{idx}",
                        aspect_ratio=aspect_ratio,
                    )
            except Exception as e:
                print(f"  [MANIM FAIL] Segment {seg_id}: {e} — skipping beat, continuing remaining beats")
                continue  # do not raise; let other beats in this section proceed

        rendered_paths.append(result)

        # CRITICAL: Update segment-level beat_videos for player sync
        if topic:
            narration_segs = topic.get("narration", {}).get("segments", [])
            for seg in narration_segs:
                if seg.get("segment_id") == seg_id:
                    video_filename = os.path.basename(result)
                    seg["beat_videos"] = [f"videos/{video_filename}"]
                    seg["video_path"] = f"videos/{video_filename}"
                    print(
                        f"  [MANIM] Linked beat {idx} → segment {seg_id}: {seg['video_path']}"
                    )
                    break

        print(f"  [MANIM] Finalized beat {idx} ({seg_id}): {result}")

    return rendered_paths


def _render_sync_split_manim_beats(
    video_prompts: list,
    topic_id: int,
    topic_title: str,
    section_type: str,
    output_dir: str,
    dry_run: bool = False,
    trace_output_dir: Optional[str] = None,
) -> List[str]:
    """
    Render sync-split Manim beats from video_prompts.

    V2.5 Sync Flow: Each beat's 'prompt' is a high-level text description
    (Manim spec) that needs to be converted to Python code via Claude.
    """
    from core.agents.manim_code_generator import ManimCodeGenerator

    generator = ManimCodeGenerator()
    rendered_paths = []

    print(
        f"[MANIM V2.5] Rendering {len(video_prompts)} sync-split beats for section {topic_id}"
    )

    for i, beat in enumerate(video_prompts):
        prompt_string = beat.get("prompt", "")
        duration = float(beat.get("duration_hint", 15.0))
        output_path = str(Path(output_dir) / f"topic_{topic_id}_beat_{i}.mp4")

        # Prepare data for code generator
        # We wrap the beat-specific prompt into a format the generator understands
        beat_data = {
            "section_title": f"{topic_title} (Part {i + 1})",
            "manim_spec": prompt_string,
            "narration_segments": [
                {"text": "Visualizing synchronized beat", "duration": duration}
            ],
            "duration": duration,
        }

        print(
            f"  [MANIM V2.5] Coding beat {i + 1}/{len(video_prompts)}: {len(prompt_string)} chars"
        )

        if dry_run:
            dry_marker = _create_dry_run_marker(
                f"{topic_id}_beat_{i}",
                output_path,
                duration,
                f"LLM Code Gen for: {prompt_string}",
            )
            rendered_paths.append(dry_marker)
            continue

        # Call the generator (performing the LLM compilation)
        try:
            manim_code, errors = generator.generate(beat_data)
        except Exception as e:
            raise ManimRenderError(
                f"Section {topic_id} beat {i + 1} code gen failed with exception: {e}"
            )

        if errors:
            raise ManimRenderError(
                f"Section {topic_id} beat {i + 1} code gen failed: {errors}"
            )

        # Execute the render
        result = _execute_spec_generated_render(
            manim_code=manim_code,
            duration=duration,
            output_path=output_path,
            topic_id=f"{topic_id}_beat_{i}",
        )

        rendered_paths.append(result)
        print(f"  [MANIM V2.5] Completed beat {i + 1}: {result}")

    return rendered_paths


def _render_compiled_multi_beat(
    beats: list,
    topic_id: int,
    topic_title: str,
    section_type: str,
    total_duration: float,
    output_dir: str,
    dry_run: bool = False,
    trace_output_dir: Optional[str] = None,
) -> List[str]:
    """
    Render compiled multi-beat plans (from manim_plan['beats'] array).

    This handles the case where visual_beats is empty but manim_plan contains
    a pre-compiled 'beats' array with scene_type="multi_beat".

    NOTE: Preserves fractional durations - LLM timing is authoritative.
    """
    rendered_paths = []
    beat_count = len(beats)

    print(
        f"[MANIM] Compiled multi-beat rendering: {beat_count} beats for section {topic_id}"
    )

    for beat_index, beat_plan in enumerate(beats):
        output_path = str(Path(output_dir) / f"topic_{topic_id}_beat_{beat_index}.mp4")

        # Get duration from beat plan or uniform fallback (preserve float)
        beat_duration = float(
            beat_plan.get("duration", float(total_duration) / beat_count)
        )
        scene_type = beat_plan.get("scene_type", "equation")

        if scene_type == "spec_generated":
            manim_code = beat_plan.get("manim_code", "")
            params = beat_plan.get("params", {})

            if not manim_code:
                raise ManimRenderError(
                    f"Section {topic_id} beat {beat_index}: spec_generated has no manim_code"
                )

            print(f"[MANIM] Compiled beat {beat_index}: duration={beat_duration}s")

            log_render_prompt(
                section_id=topic_id,
                section_title=f"{topic_title} (compiled beat {beat_index})",
                renderer="manim_spec",
                prompt=manim_code,
                output_path=output_path,
                extra_data={
                    "section_type": section_type,
                    "scene_type": "spec_generated",
                    "beat_index": beat_index,
                    "beat_count": beat_count,
                    "duration": beat_duration,
                    "dry_run": dry_run,
                },
                trace_output_dir=trace_output_dir,
            )

            if dry_run:
                print(
                    f"[DRY RUN] Compiled Manim beat {beat_index} for section {topic_id}"
                )
                marker_path = _create_dry_run_marker(
                    topic_id, output_path, beat_duration, manim_code
                )
                rendered_paths.append(marker_path)
            else:
                result = _execute_spec_generated_render(
                    manim_code=manim_code,
                    duration=beat_duration,
                    output_path=output_path,
                    topic_id=topic_id,
                )
                rendered_paths.append(result)
                print(f"[MANIM] Rendered compiled beat {beat_index}: {result}")
        else:
            # Legacy template-based rendering
            params = beat_plan.get("params", {})
            _validate_not_placeholder(params, topic_id, topic_title)

            template = MANIM_TEMPLATES.get(scene_type, MANIM_TEMPLATES["equation"])
            render_params = {"wait_time": max(1, beat_duration - 5), **params}

            try:
                scene_code = template.format(**render_params)
            except KeyError as e:
                raise ManimRenderError(
                    f"Section {topic_id} beat {beat_index}: Missing Manim parameter: {e}"
                )

            log_render_prompt(
                section_id=topic_id,
                section_title=f"{topic_title} (compiled beat {beat_index})",
                renderer="manim_code",
                prompt=scene_code,
                output_path=output_path,
                extra_data={
                    "scene_type": scene_type,
                    "beat_index": beat_index,
                    "duration": beat_duration,
                    "dry_run": dry_run,
                },
                trace_output_dir=trace_output_dir,
            )

            if dry_run:
                print(
                    f"[DRY RUN] Compiled Manim beat {beat_index} for section {topic_id}"
                )
                marker_path = _create_dry_run_marker(
                    topic_id, output_path, beat_duration, scene_code
                )
                rendered_paths.append(marker_path)
            else:
                result = _execute_manim_render(
                    scene_type=scene_type,
                    params=params,
                    duration=beat_duration,
                    output_path=output_path,
                    topic_id=topic_id,
                    scene_code=scene_code,
                )
                rendered_paths.append(result)
                print(f"[MANIM] Rendered compiled beat {beat_index}: {result}")

    print(
        f"[MANIM] Completed {len(rendered_paths)} compiled beat videos for section {topic_id}"
    )
    return rendered_paths


def _compile_beats_to_manim_plan(visual_beats: list, topic_id: int) -> dict:
    """Compile a single visual beat into a Manim plan."""
    from core.visual_compiler import compile_manim_plan, VisualCompilationError

    if not visual_beats:
        raise ManimRenderError(f"Section {topic_id}: No visual beats to compile")

    # Compile first beat for single-beat rendering
    beat = visual_beats[0]

    try:
        plan = compile_manim_plan(beat, topic_id, 0)
        return plan
    except VisualCompilationError as e:
        raise ManimRenderError(
            f"Section {topic_id}: Visual beat compilation failed - {e.reason}"
        )


def _validate_not_placeholder(params: dict, topic_id: int, topic_title: str):
    """Fail if params contain placeholder/generic content."""

    equation = params.get("equation", "")
    steps = params.get("steps", "")
    shape_code = params.get("shape_code", "")

    # Check equation
    for banned in BANNED_PLACEHOLDER_EQUATIONS:
        if banned.lower() in equation.lower():
            raise ManimRenderError(
                f"Section {topic_id} '{topic_title}': Generic placeholder equation detected: '{equation}'. "
                f"LLM must generate specific equations based on the topic, not fallback defaults."
            )

    # Check steps
    for banned in BANNED_PLACEHOLDER_EQUATIONS:
        if banned.lower() in steps.lower():
            raise ManimRenderError(
                f"Section {topic_id} '{topic_title}': Generic placeholder steps detected: '{steps}'. "
                f"LLM must generate specific derivation steps."
            )

    # Check shape code
    if shape_code == "shapes.add(Circle(radius=1, color=BLUE))":
        raise ManimRenderError(
            f"Section {topic_id} '{topic_title}': Generic placeholder geometry detected. "
            f"LLM must generate specific shape code for this topic."
        )


def _sanitize_manim_code(manim_code: str) -> str:
    """
    Sanitize Manim code to fix common LaTeX issues.

    Fixes:
    1. Replace \text{} with \textrm{} in MathTex (works better in math mode)
    2. Escape problematic characters in text content
    """
    import re

    lines = manim_code.split("\n")
    fixed_lines = []

    for line in lines:
        if r"\text{" in line:
            line = line.replace(r"\text{", r"\textrm{")

        # Scrub invalid waits as a fail-safe
        if "self.wait(0.0)" in line or "self.wait(0)" in line:
            if re.search(r"^\s*self\.wait\(\s*0?\.?0\s*\)\s*(#.*)?$", line):
                continue  # Strip entirely if it's the whole line
            else:
                line = re.sub(r"self\.wait\(\s*0?\.?0\s*\)", "", line)

        # Fix zero run_time in self.play() calls - Manim requires run_time > 0
        # LLM sometimes generates run_time=0.0 for instant transitions, replace with minimum 0.1
        if "run_time=0.0" in line or "run_time=0)" in line or "run_time= 0" in line:
            line = re.sub(r"run_time\s*=\s*0\.0", "run_time=0.1", line)
            line = re.sub(r"run_time\s*=\s*0([,\)])", r"run_time=0.1\1", line)
            print(f"[MANIM SANITIZER] Fixed zero run_time: {line.strip()[:60]}...")

        fixed_lines.append(line)

    # Ensure every construct method ends with a small wait (v2.5 rule for stability)
    last_idx = -1
    for i in range(len(fixed_lines) - 1, -1, -1):
        if fixed_lines[i].strip():
            last_idx = i
            break

    if last_idx >= 0:
        indent_match = re.match(r"^(\s*)", fixed_lines[last_idx])
        indent = indent_match.group(1) if indent_match else "        "
        fixed_lines.insert(
            last_idx + 1, f"{indent}self.wait(0.1) # Terminal stabilizer"
        )
        print(f"[MANIM SANITIZER] Added terminal stabilizer wait(0.1)")

    return "\n".join(fixed_lines)


def _get_texinputs_env() -> dict:
    """Get environment with TEXINPUTS including vendored LaTeX files."""
    import os

    templates_dir = Path(__file__).parent / "templates"
    current_texinputs = os.environ.get("TEXINPUTS", "")
    new_texinputs = (
        f"{templates_dir}:{current_texinputs}:"
        if current_texinputs
        else f"{templates_dir}::"
    )
    env = os.environ.copy()
    env["TEXINPUTS"] = new_texinputs
    return env


def _execute_spec_generated_render(
    manim_code: str, duration: float, output_path: str, topic_id: int,
    aspect_ratio: str = "16:9",
) -> str:
    """Execute Manim render from spec-generated code."""

    # Sanitize the code to fix common LaTeX issues
    sanitized_code = _sanitize_manim_code(manim_code)

    # Inject aspect_ratio so the LLM code doesn't crash if it references it
    if "from manim import *" in sanitized_code:
        sanitized_code = sanitized_code.replace("from manim import *", f"from manim import *\naspect_ratio = '{aspect_ratio}'")
    else:
        sanitized_code = f"aspect_ratio = '{aspect_ratio}'\n" + sanitized_code

    # V2 FULL CODE CHECK: If code is already a full scene, use it directly
    is_full_code = (
        "class " in sanitized_code
        and "(Scene):" in sanitized_code
        and "def construct" in sanitized_code
    )

    if is_full_code:
        scene_wrapper = sanitized_code
        scene_class_name = "MainScene"  # Default for V2
        # Try to find actual class name if different
        import re

        match = re.search(r"class\s+(\w+)\(.*?Scene\):", sanitized_code)
        if match:
            scene_class_name = match.group(1)
    else:
        # Legacy V1: Wrap logic fragment
        scene_wrapper = f"""
from manim import *
import numpy as np

class SpecGeneratedScene(Scene):
    def construct(self):
{chr(10).join("        " + line for line in sanitized_code.split(chr(10)))}
"""
        scene_class_name = "SpecGeneratedScene"

    # PERSISTENCE: Save code to job/manim_code/section_{id}.py using output_dir context
    # output_dir is typically .../jobs/{job_id}/videos
    try:
        job_dir = Path(output_path).parent.parent
        code_dir = job_dir / "manim_code"
        code_dir.mkdir(parents=True, exist_ok=True)
        persistent_file = code_dir / f"section_{topic_id}.py"
        with open(persistent_file, "w", encoding="utf-8") as f:
            f.write(scene_wrapper)
        print(f"[MANIM V2] Saved source code to: {persistent_file}")
    except Exception as e:
        print(f"[MANIM V2] Warning: Could not save persistent code: {e}")

    # Get environment with vendored LaTeX files
    env = _get_texinputs_env()

    with tempfile.TemporaryDirectory() as tmpdir:
        scene_file = Path(tmpdir) / "scene.py"
        with open(scene_file, "w", encoding="utf-8") as f:
            f.write(scene_wrapper)

        resolution_flags = ["--resolution", "720,1280"] if aspect_ratio == "9:16" else []

        cmd = [
            "manim",
            "render",
            "-q",
            "m",
            "--fps",
            "30",
            *resolution_flags,
            "-o",
            "output.mp4",
            "--media_dir",
            tmpdir,
            str(scene_file),
            scene_class_name,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=300,  # Increased timeout
                cwd=tmpdir,
                env=env,
            )

            if result.returncode != 0:
                print(
                    f"[MANIM DEBUG] Section {topic_id} stdout: {result.stdout[:1000]}"
                )
                print(
                    f"[MANIM DEBUG] Section {topic_id} stderr: {result.stderr[:1000]}"
                )
                print(f"[MANIM DEBUG] Generated code:\n{scene_wrapper[:2000]}")

                # CRASH LOGGING
                try:
                    crash_log = Path(output_path).parent / f"manim_crash_{topic_id}.log"
                    with open(crash_log, "w", encoding="utf-8") as f:
                        f.write(f"EXIT CODE: {result.returncode}\n")
                        f.write(f"STDOUT:\n{result.stdout}\n")
                        f.write(f"STDERR:\n{result.stderr}\n")
                        f.write(f"CODE:\n{scene_wrapper}\n")
                    print(f"[MANIM] Saved crash log to {crash_log}")
                except Exception as e:
                    print(f"Failed to save crash log: {e}")

                raise ManimRenderError(
                    f"Section {topic_id}: Manim spec render failed. "
                    f"Return code: {result.returncode}. "
                    f"Stderr: {result.stderr[:500]}"
                )

            # Find output video - v2.5 sweet spot path
            # manim -qm produces 720p30 directory
            video_files = list(Path(tmpdir).rglob("output.mp4"))
            if video_files:
                import shutil

                shutil.copy(video_files[0], output_path)
                return output_path

            raise ManimRenderError(
                f"Section {topic_id}: Manim spec render produced no output video"
            )

        except subprocess.TimeoutExpired:
            raise ManimRenderError(
                f"Section {topic_id}: Manim spec render timed out after 300s"
            )


def _execute_manim_render(
    scene_type: str,
    params: dict,
    duration: float,
    output_path: str,
    topic_id: int,
    scene_code: str,
) -> str:
    """Execute Manim render - raises ManimRenderError on failure."""

    # Get environment with vendored LaTeX files
    env = _get_texinputs_env()

    with tempfile.TemporaryDirectory() as tmpdir:
        scene_file = Path(tmpdir) / "scene.py"
        with open(scene_file, "w") as f:
            f.write(scene_code)

        scene_class = {
            "equation": "EquationScene",
            "graph": "GraphScene",
            "geometry": "GeometryScene",
            "derivation": "DerivationScene",
        }.get(scene_type, "EquationScene")

        cmd = [
            "manim",
            "render",
            "-q",
            "m",
            "--fps",
            "30",  # Medium quality (Sweet Spot: 720p 30fps)
            "-o",
            "output.mp4",
            "--media_dir",
            tmpdir,
            str(scene_file),
            scene_class,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=300,  # Increased timeout
                cwd=tmpdir,
                env=env,
            )

            if result.returncode != 0:
                raise ManimRenderError(
                    f"Section {topic_id}: Manim execution failed. "
                    f"Return code: {result.returncode}. "
                    f"Stderr: {result.stderr[:500]}"
                )

            # Find output video
            # Manim -qm output structure: videos/scene/720p30/...
            # We use rglob to find it safely regardless of resolution folder name
            media_path = Path(tmpdir) / "videos"
            found_video = None
            for video_file in media_path.rglob("output.mp4"):
                found_video = video_file
                break

            if found_video:
                shutil.copy(found_video, output_path)
                print(f"[MANIM] Generated: {output_path}")
                return output_path

            raise ManimRenderError(
                f"Section {topic_id}: Manim produced no video output in {media_path}"
            )

        except subprocess.TimeoutExpired:
            raise ManimRenderError(
                f"Section {topic_id}: Manim render timed out after 300s"
            )
        except FileNotFoundError:
            raise ManimRenderError(
                f"Section {topic_id}: Manim not installed or not in PATH"
            )


def _create_dry_run_marker(
    topic_id: int, output_path: str, duration: float, scene_code: str
) -> str:
    """Create marker file for dry run mode with full scene code."""
    marker_path = output_path.replace(".mp4", ".dry_run.txt")
    with open(marker_path, "w") as f:
        f.write(f"DRY RUN - Manim section {topic_id}\n")
        f.write(f"Duration: {duration}s\n")
        f.write(f"Output would be: {output_path}\n")
        f.write(f"\n--- SCENE CODE ---\n")
        f.write(scene_code)
    print(f"[DRY RUN] Created marker: {marker_path}")
    return marker_path

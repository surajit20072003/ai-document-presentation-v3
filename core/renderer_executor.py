import os
import json
import logging
import traceback
import concurrent.futures
from pathlib import Path
from core.dry_run_validator import (
    DryRunValidationResult,
    validate_presentation_dry_run,
    format_validation_report,
)
from render.wan.wan_runner import render_wan_video
from render.manim.manim_runner import render_manim_video

try:
    from core.agents.threejs_code_generator import ThreejsCodeGenerator
except ImportError:
    ThreejsCodeGenerator = None

logger = logging.getLogger(__name__)

try:
    from render.ltx.ltx_runner import render_ltx_video
except ImportError:
    render_ltx_video = None

from core.locks import presentation_lock, analytics_lock


TEXT_ONLY_SECTION_TYPES = ["intro", "summary", "memory", "quiz"]


def _render_videos_parallel(
    beats: list,
    output_dir: str,
    dry_run: bool = False,
    use_local_gpu: bool = True,
    topic_id: str = "",
) -> dict:
    """
    Render videos in parallel using Local GPU (max_workers=3).
    No fallback - fails immediately on error.

    Args:
        beats: List of dicts with 'beat_id', 'beat_idx', 'prompt', 'duration',
               'image_path' (start frame, optional), 'image_path_end' (end frame, optional)
        output_dir: Output directory
        dry_run: Skip generation
        use_local_gpu: True=Local GPU (required, no Kie/WAN fallback)
        topic_id: Section ID prefix for filename (e.g. "6" → topic_6_seg_1_beat_0.mp4)

    Returns:
        dict: {'success': [video_paths], 'failed': [beat_ids]}
    """
    results = {"success": [], "failed": []}

    if dry_run:
        print(f"[GPU-PARALLEL] DRY RUN: Would process {len(beats)} beats in parallel")
        for beat in beats:
            print(
                f"  - {beat.get('beat_id', 'beat')}: {len(beat.get('prompt', ''))} chars"
            )
        return results

    # GPU availability check
    from render.wan.local_gpu_client import LocalGPUClient

    client = LocalGPUClient()
    if not client.is_available():
        raise Exception("Local GPU server unavailable")

    print(f"[GPU-PARALLEL] Using Local GPU (max_workers=3) for {len(beats)} beats")

    # Parallel execution
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_beat = {}

        for beat in beats:
            beat_id = beat.get("beat_id", "beat")
            beat_idx = beat.get("beat_idx", 0)
            prompt = beat.get("prompt") or beat.get("video_prompt", "")
            duration = int(beat.get("duration", 15))
            image_path = beat.get("image_path")  # start frame
            image_path_end = beat.get("image_path_end")  # end frame (new)

            # Filename: topic_{section_id}_{beat_id}.mp4
            # e.g. topic_6_seg_1.mp4 (no double beat suffix)
            prefix = f"topic_{topic_id}_" if topic_id else ""
            out_path = str(Path(output_dir) / f"{prefix}{beat_id}.mp4")

            future = executor.submit(
                client.generate_video,
                prompt=prompt,
                duration=duration,
                output_path=out_path,
                image_path=image_path,
                image_path_end=image_path_end,  # ← pass end frame
            )
            future_to_beat[future] = beat_id

        # Collect results
        for future in concurrent.futures.as_completed(future_to_beat):
            beat_id = future_to_beat[future]
            try:
                video_path = future.result()
                if video_path and Path(video_path).exists():
                    results["success"].append(video_path)
                    print(f"[GPU-PARALLEL] ✓ {beat_id}: {Path(video_path).name}")
                else:
                    results["failed"].append(beat_id)
                    print(f"[GPU-PARALLEL] ✗ {beat_id}: No output")
                    raise Exception(f"Video generation failed for {beat_id}")
            except Exception as e:
                results["failed"].append(beat_id)
                print(f"[GPU-PARALLEL] ✗ {beat_id}: {e}")
                raise  # Fail immediately

    return results


def enforce_renderer_policy(presentation: dict) -> dict:
    """Enforce renderer selection based on section type.

    POLICY (as agreed):
    - INTRO/SUMMARY/MEMORY: TEXT-ONLY (no video rendering)
    - CONTENT/EXAMPLE: Use LLM Director's choice (WAN for physics concepts, Manim for math/LaTeX)
    - RECAP: Always WAN (5 storyboard scenes)

    This enforces text-only sections but trusts the LLM Director for content/example.
    """
    sections = presentation.get("sections", presentation.get("topics", []))
    changes_made = 0

    for section in sections:
        # Safety: Skip if section is not a dict
        if not isinstance(section, dict):
            print(
                f"[RENDERER POLICY] WARNING: Section is type {type(section)}, expected dict. Skipping."
            )
            continue

        section_type = section.get("section_type", "content")
        current_renderer = section.get("renderer", "wan_video")

        if section_type in TEXT_ONLY_SECTION_TYPES:
            if current_renderer and current_renderer != "none":
                section["renderer"] = "none"
                section["renderer_override_reason"] = (
                    f"Section type '{section_type}' is text-only (no video rendering)"
                )
                changes_made += 1
                print(
                    f"[RENDERER POLICY] Section {section.get('id')} ({section_type}): Forced to TEXT-ONLY"
                )

        elif section_type == "recap":
            if current_renderer != "video":
                section["renderer"] = "video"
                section["renderer_override_reason"] = (
                    "V2.5 Bible: Recap sections strictly use 'video' renderer"
                )
                changes_made += 1
                print(
                    f"[RENDERER POLICY] Section {section.get('id')}: Forced to 'video' (recap)"
                )

        # V3: 'manim' and 'threejs' are valid renderers for content/example — never override
        elif current_renderer in ("manim", "threejs") and section_type in (
            "content",
            "example",
        ):
            pass  # Allow Manim/Three.js renderer through unchanged

        # V3: 'infographic' is valid for memory_infographic — never override
        elif current_renderer == "infographic" and section_type == "memory_infographic":
            pass  # Allow infographic renderer through unchanged

    if changes_made > 0:
        print(f"[RENDERER POLICY] Applied {changes_made} renderer overrides")

    return presentation


def _process_segment_specs_individually(
    topic: dict,
    segment_specs: list,
    output_dir: str,
    dry_run: bool = False,
    skip_wan: bool = False,
    trace_output_dir: str = "",
    video_provider: str = "ltx",
) -> dict:
    """
    Process each segment_spec individually based on its renderer type.
    text_to_video / image_to_video / video → PARALLEL (max_workers=3).
    manim / infographic / image / none     → serial (no GPU benefit).
    """
    from render.ltx.ltx_client import LtxClient
    from render.image.image_generator import generate_image_for_beat

    topic_id = topic.get("section_id", "unknown")
    results = {"success": [], "failed": [], "skipped": []}

    images_dir = Path(output_dir).parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    job_id = str(Path(output_dir).parent.name)

    print(
        f"[PROCESS INDIVIDUAL] Section {topic_id}: Processing {len(segment_specs)} segments..."
    )

    # ── Split specs ──────────────────────────────────────────────────────────────
    video_specs = []
    other_specs = []
    for i, spec in enumerate(segment_specs):
        renderer = spec.get("renderer", "")
        if renderer in ("text_to_video", "video", "image_to_video"):
            video_specs.append((i, spec))
        else:
            other_specs.append((i, spec))

    # ── Helper: one video segment (runs inside thread pool) ──────────────────────
    def _render_video_spec(i_spec):
        i, spec = i_spec
        seg_id = spec.get("segment_id", f"seg_{i}")
        renderer = spec.get("renderer", "")
        print(f"  [{seg_id}] Renderer: {renderer} [parallel]")
        try:
            if renderer in ("text_to_video", "video"):
                video_prompt = spec.get("video_prompt", "")
                if not video_prompt:
                    return {
                        "type": "failed",
                        "segment_id": seg_id,
                        "reason": "no video_prompt",
                    }
                duration = spec.get("segment_duration_seconds", 15)
                video_output = str(Path(output_dir) / f"topic_{topic_id}_{seg_id}.mp4")
                if dry_run:
                    return {
                        "type": "skipped",
                        "segment_id": seg_id,
                        "reason": "dry_run",
                    }
                client = LtxClient()
                video_path = client.generate_video(
                    prompt=video_prompt,
                    duration=int(duration),
                    output_path=video_output,
                )
                if video_path:
                    spec["video_path"] = f"videos/{Path(video_path).name}"
                    return {
                        "type": "success",
                        "segment_id": seg_id,
                        "video_path": video_path,
                    }
                return {
                    "type": "failed",
                    "segment_id": seg_id,
                    "reason": "generation failed",
                }

            elif renderer == "image_to_video":
                image_prompt = spec.get("image_prompt", "")
                video_prompt = spec.get("video_prompt", "")
                if not image_prompt:
                    return {
                        "type": "failed",
                        "segment_id": seg_id,
                        "reason": "no image_prompt",
                    }
                if dry_run:
                    return {
                        "type": "skipped",
                        "segment_id": seg_id,
                        "reason": "dry_run",
                    }
                beat_data = {"beat_id": seg_id, "image_prompt": image_prompt}
                image_path = generate_image_for_beat(
                    beat_data, job_id, topic_id, str(images_dir)
                )
                if not image_path:
                    return {
                        "type": "failed",
                        "segment_id": seg_id,
                        "reason": "image gen failed",
                    }
                spec["image_path"] = f"images/{Path(image_path).name}"
                duration = spec.get("segment_duration_seconds", 15)
                video_output = str(Path(output_dir) / f"topic_{topic_id}_{seg_id}.mp4")
                client = LtxClient()
                video_path = client.generate_video_from_image(
                    prompt=video_prompt,
                    image_path=image_path,
                    output_path=video_output,
                    duration=duration,
                )
                if video_path:
                    spec["video_path"] = f"videos/{Path(video_path).name}"
                    return {
                        "type": "success",
                        "segment_id": seg_id,
                        "video_path": video_path,
                    }
                return {
                    "type": "failed",
                    "segment_id": seg_id,
                    "reason": "video gen failed",
                }
        except Exception as e:
            return {"type": "failed", "segment_id": seg_id, "error": str(e)}
        return {"type": "skipped", "segment_id": seg_id, "reason": "no match"}

    # ── Parallel: video segments ─────────────────────────────────────────────────
    if video_specs:
        print(
            f"[PROCESS INDIVIDUAL] Section {topic_id}: Firing {len(video_specs)} video segments in parallel (max_workers=3)"
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(_render_video_spec, i_spec) for i_spec in video_specs
            ]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                results[res["type"]].append(res)

    # ── Serial: manim / infographic / image / none ───────────────────────────────
    for i, spec in other_specs:
        seg_id = spec.get("segment_id", f"seg_{i}")
        renderer = spec.get("renderer", "")
        print(f"  [{seg_id}] Renderer: {renderer}")

        if renderer in ("none", "") or not renderer:
            results["skipped"].append({"segment_id": seg_id, "reason": "none renderer"})
            continue

        try:
            if renderer == "infographic":
                image_prompt = spec.get("image_prompt", "")
                if not image_prompt:
                    results["failed"].append(
                        {"segment_id": seg_id, "reason": "no image_prompt"}
                    )
                    continue
                if dry_run:
                    continue
                beat_data = {"beat_id": seg_id, "image_prompt": image_prompt}
                image_path = generate_image_for_beat(
                    beat_data, job_id, topic_id, str(images_dir)
                )
                if image_path:
                    spec["image_path"] = f"images/{Path(image_path).name}"
                    results["success"].append(
                        {"segment_id": seg_id, "image_path": image_path}
                    )
                else:
                    results["failed"].append(
                        {"segment_id": seg_id, "reason": "image gen failed"}
                    )

            elif renderer == "image":
                image_source = spec.get("image_source", "")
                if image_source:
                    spec["image_path"] = image_source
                    results["success"].append(
                        {"segment_id": seg_id, "image_source": image_source}
                    )
                else:
                    results["failed"].append(
                        {"segment_id": seg_id, "reason": "no image_source"}
                    )

            elif renderer == "manim":
                manim_scene_spec = spec.get("manim_scene_spec")
                if not manim_scene_spec:
                    results["failed"].append(
                        {"segment_id": seg_id, "reason": "no manim_scene_spec"}
                    )
                    continue

                if dry_run:
                    results["skipped"].append(
                        {"segment_id": seg_id, "reason": "dry_run"}
                    )
                    continue

                print(f"  [{seg_id}] Rendering manim segment...")
                try:
                    from render.manim.manim_runner import render_manim_video

                    # Build a mini-topic dict so render_manim_video → _render_manim_segment_specs
                    # can find the manim segment in render_spec.segment_specs
                    mini_topic = {
                        "section_id": topic_id,
                        "title": str(topic_id),
                        "section_type": "content",
                        "render_spec": {
                            "segment_specs": [spec]  # only this one manim segment
                        },
                        "narration": topic.get("narration", {}),
                    }
                    manim_result = render_manim_video(mini_topic, output_dir)
                    # result is a path string or list of paths
                    if isinstance(manim_result, list):
                        manim_path = manim_result[0] if manim_result else None
                    else:
                        manim_path = manim_result

                    if manim_path and Path(manim_path).exists():
                        spec["video_path"] = f"videos/{Path(manim_path).name}"
                        results["success"].append(
                            {"segment_id": seg_id, "video_path": manim_path}
                        )
                        print(f"  [{seg_id}] Manim done: {manim_path}")
                    else:
                        results["failed"].append(
                            {"segment_id": seg_id, "reason": "manim produced no output"}
                        )
                except Exception as manim_err:
                    print(f"  [{seg_id}] Manim FAILED: {manim_err}")
                    results["failed"].append(
                        {"segment_id": seg_id, "error": str(manim_err)}
                    )

            else:
                results["skipped"].append(
                    {"segment_id": seg_id, "reason": f"unknown: {renderer}"}
                )

        except Exception as e:
            results["failed"].append({"segment_id": seg_id, "error": str(e)})

    return {
        "topic_id": topic_id,
        "renderer": "mixed",
        "status": "completed",
        "results": results,
    }


def execute_renderer(
    topic: dict,
    output_dir: str,
    dry_run: bool = False,
    skip_wan: bool = False,
    trace_output_dir: str = "",
    strict_mode: bool = True,
    video_provider: str = "ltx",
) -> dict:
    """
    V3 Section-Level Renderer Executor.

    Routing priority:
    1. render_spec.renderer (new section-level format): manim | image_to_video | text_to_video | infographic
    2. render_spec.segment_specs[] (old beat-level format): for backward compatibility
    3. Legacy fallbacks: video_prompts, manim_scene_spec
    4. explanation_visual structure: renderer at top level (for quiz explanation_visual)
    """
    os.makedirs(output_dir, exist_ok=True)

    topic_id = topic.get("section_id", topic.get("id", 1))
    section_type = topic.get("section_type", "content")
    visual_beats = topic.get("visual_beats", [])

    render_spec = topic.get("render_spec") or {}

    # NEW FORMAT: Check section-level renderer first
    renderer = render_spec.get("renderer")

    # Check top-level renderer (for explanation_visual structure)
    # explanation_visual has renderer directly at top level, not inside render_spec
    if not renderer:
        renderer = topic.get("renderer", "")

    # Log renderer choice reason if available
    renderer_reason = render_spec.get("renderer_reason", "") or topic.get(
        "renderer_reason", ""
    )
    if renderer_reason:
        print(f"  [{topic_id}] Renderer reason: {renderer_reason}")

    # If no section-level renderer, fall back to old detection
    if not renderer or renderer == "video":
        segment_specs = render_spec.get("segment_specs", [])
        if segment_specs:
            renderers_in_segments = set(
                s.get("renderer") for s in segment_specs if s.get("renderer")
            )
            if renderers_in_segments:
                if "image_to_video" in renderers_in_segments:
                    renderer = "image_to_video"
                elif "infographic" in renderers_in_segments:
                    renderer = "infographic"
                elif "text_to_video" in renderers_in_segments:
                    renderer = "wan_video"
                elif "manim" in renderers_in_segments:
                    renderer = "manim"
                elif "video" in renderers_in_segments:
                    renderer = "wan_video"

        # Legacy fallback
        if not renderer or renderer == "video":
            if topic.get("renderer") == "manim":
                renderer = "manim"
            elif topic.get("renderer") in ("wan", "wan_video"):
                renderer = "wan_video"
            elif section_type not in TEXT_ONLY_SECTION_TYPES:
                video_prompts = topic.get("video_prompts", [])
                if video_prompts:
                    renderer = "wan_video"

    # Default to none if still not set
    if not renderer:
        renderer = "none"

    # Skip text-only section types
    if section_type in TEXT_ONLY_SECTION_TYPES or renderer == "none":
        reason = (
            f"Section type '{section_type}' is text-only"
            if section_type in TEXT_ONLY_SECTION_TYPES
            else "Renderer explicitly set to 'none'"
        )
        return {
            "topic_id": topic_id,
            "section_type": section_type,
            "renderer": renderer,
            "status": "skipped",
            "video_path": None,
            "reason": reason,
        }

    # Check for specs at both render_spec level and top level (for explanation_visual)
    manim_scene_spec = (
        render_spec.get("manim_scene_spec")
        or render_spec.get("manim_beats")
        or topic.get("manim_scene_spec", "")
        or topic.get("manim_beats", [])
    )
    video_prompts = render_spec.get("video_prompts") or topic.get("video_prompts", [])
    image_to_video_beats = render_spec.get("image_to_video_beats") or topic.get(
        "image_to_video_beats", []
    )
    has_v12_specs = (
        bool(manim_scene_spec) or bool(video_prompts) or bool(image_to_video_beats)
    )

    if visual_beats:
        if "explanation_plan" not in topic:
            topic["explanation_plan"] = {}
        topic["explanation_plan"]["visual_beats"] = visual_beats

    result = {
        "topic_id": topic_id,
        "section_type": section_type,
        "renderer": renderer,
        "status": "pending",
        "video_path": None,
        "error": None,
        "visual_beats_used": len(visual_beats) if visual_beats else 0,
        "dry_run": dry_run,
        "compilation_errors": [],
        "v12_specs_used": has_v12_specs,
    }

    if has_v12_specs:
        print(
            f"[v1.2 MODE] Section {topic_id} has pre-compiled renderer specs - bypassing Visual Compiler"
        )

    import time

    render_start = time.time()
    try:
        # Log renderer choice reasons for all segment_specs
        segment_specs_all = topic.get("render_spec", {}).get("segment_specs", [])
        for spec in segment_specs_all:
            if spec.get("renderer") == "manim":
                reason = spec.get("renderer_choice_reason", "No reason provided")
                print(f"    [{spec.get('segment_id')}] Reason: {reason}")

        if renderer == "manim":
            video_path = render_manim_video(
                topic, output_dir, dry_run=dry_run, trace_output_dir=trace_output_dir
            )
        elif renderer == "threejs":
            # V3: Generate Three.js .js file instead of rendering a video
            if ThreejsCodeGenerator is None:
                raise ImportError("ThreejsCodeGenerator could not be imported")
            if dry_run:
                print(
                    f"[DRY RUN] Section {topic_id}: Would generate Three.js file (threejs_spec present: {bool(topic.get('threejs_spec'))})"
                )
                return {
                    "topic_id": topic_id,
                    "section_type": section_type,
                    "renderer": "threejs",
                    "status": "skipped",
                    "video_path": None,
                    "reason": "dry_run",
                }
            print(f"[RENDER] Section {topic_id}: Generating Three.js scene")
            gen = ThreejsCodeGenerator()
            js_code, errors = gen.generate(topic)
            if js_code:
                js_path = gen.save_js_file(
                    js_code,
                    output_dir,
                    job_id=str(Path(output_dir).parent.name),
                    topic_id=str(topic_id),
                    beat_idx=0,
                )
                # Store relative path so presentation.json stitch can pick it up
                topic["threejs_file"] = f"threejs/topic_{topic_id}_beat_0.js"
                # Also update the segment_spec (segment-level per V3 schema)
                render_spec = topic.get("render_spec", {})
                for spec in render_spec.get("segment_specs", []):
                    if spec.get("renderer") == "threejs":
                        spec["threejs_file"] = f"threejs/topic_{topic_id}_beat_0.js"
                result["status"] = "success"
                result["threejs_file"] = js_path
                result["video_path"] = None  # No video — player loads .js directly
                print(f"  [{topic_id}] -> Three.js scene saved: {js_path}")
            else:
                result["status"] = "failed"
                result["error"] = str(errors)
                print(f"  [{topic_id}] -> Three.js generation FAILED: {errors}")
            return result

        elif renderer == "image_to_video":
            # V3: Generate image first (Gemini), then animate with Local GPU in parallel
            print(f"[RENDER] Section {topic_id}: Processing image_to_video...")

            if dry_run:
                print(f"[DRY RUN] Section {topic_id}: Would generate image_to_video")
                return {
                    "topic_id": topic_id,
                    "section_type": section_type,
                    "renderer": "image_to_video",
                    "status": "skipped",
                    "video_path": None,
                    "reason": "dry_run",
                }

            # Build beats list for parallel processing
            # Check for image_prompts[] and video_prompts[] arrays first (NEW FORMAT - one per segment)
            image_prompts = render_spec.get("image_prompts", [])
            video_prompts = render_spec.get("video_prompts", [])

            if image_prompts and isinstance(image_prompts, list):
                # NEW FORMAT: image_prompts[] array - one image per segment
                # Match with video_prompts if available
                beats = []
                for i, img_p in enumerate(image_prompts):
                    vid_p = video_prompts[i] if i < len(video_prompts) else {}

                    img_prompt_text = (
                        img_p if isinstance(img_p, str) else img_p.get("prompt", "")
                    )
                    beat_id = (
                        f"seg_{i + 1}"
                        if isinstance(img_p, str)
                        else img_p.get("segment_id", f"seg_{i + 1}")
                    )
                    duration = (
                        15 if isinstance(img_p, str) else img_p.get("duration", 15)
                    )

                    vid_prompt_text = (
                        vid_p
                        if isinstance(vid_p, str)
                        else (
                            vid_p.get("prompt", "") if isinstance(vid_p, dict) else ""
                        )
                    )

                    beats.append(
                        {
                            "beat_id": beat_id,
                            "beat_idx": i,
                            "image_prompt": img_prompt_text,
                            "prompt": vid_prompt_text,
                            "duration": duration,
                        }
                    )
                print(
                    f"[IMAGE_TO_VIDEO] Section {topic_id}: Using image_prompts[] + video_prompts[] arrays ({len(beats)} videos)"
                )
            elif video_prompts and isinstance(video_prompts, list):
                # Only video_prompts[] - need to generate images from video prompts
                beats = []
                for i, vid_p in enumerate(video_prompts):
                    beat_id = (
                        f"seg_{i + 1}"
                        if isinstance(vid_p, str)
                        else vid_p.get("segment_id", f"seg_{i + 1}")
                    )
                    vid_prompt_text = (
                        vid_p if isinstance(vid_p, str) else vid_p.get("prompt", "")
                    )
                    duration = (
                        15 if isinstance(vid_p, str) else vid_p.get("duration", 15)
                    )

                    beats.append(
                        {
                            "beat_id": beat_id,
                            "beat_idx": i,
                            "image_prompt": f"Reference image for scene: {vid_prompt_text[:200]}...",
                            "prompt": vid_prompt_text,
                            "duration": duration,
                        }
                    )
                print(
                    f"[IMAGE_TO_VIDEO] Section {topic_id}: Using video_prompts[] (auto-generating images)"
                )
            elif image_to_video_beats and isinstance(image_to_video_beats, list):
                # EXPLANATION_VISUAL FORMAT: image_to_video_beats[] from quiz explanation_visual
                beats = []
                for i, beat in enumerate(image_to_video_beats):
                    # Keep start and end image prompts SEPARATE — generate 2 images per beat
                    beats.append(
                        {
                            "beat_id": beat.get("beat_id", f"beat_{i + 1}"),
                            "beat_idx": i,
                            "image_prompt_start": beat.get("image_prompt_start", ""),
                            "image_prompt_end": beat.get("image_prompt_end", ""),
                            "prompt": beat.get("video_prompt", ""),
                            "duration": beat.get("duration", 15),
                        }
                    )
                print(
                    f"[IMAGE_TO_VIDEO] Section {topic_id}: Using image_to_video_beats[] from explanation_visual ({len(beats)} videos)"
                )
            else:
                # FALLBACK: Single image_prompt + video_prompt for entire section
                image_prompt = render_spec.get("image_prompt", "")
                video_prompt = render_spec.get("video_prompt", "")
                duration = render_spec.get("total_duration_seconds", 15)

                if image_prompt:
                    beats = [
                        {
                            "beat_id": "seg_1",
                            "beat_idx": 0,
                            "image_prompt": image_prompt,
                            "prompt": video_prompt,
                            "duration": duration,
                        }
                    ]
                    print(
                        f"[IMAGE_TO_VIDEO] Section {topic_id}: Using single image_prompt (fallback)"
                    )
                else:
                    # OLD FORMAT: Check segment_specs
                    segment_specs = render_spec.get("segment_specs", [])
                    i2v_specs = [
                        s
                        for s in segment_specs
                        if s.get("renderer") == "image_to_video"
                    ]
                    if i2v_specs:
                        beats = [
                            {
                                "beat_id": s.get("segment_id", f"seg_{i + 1}"),
                                "beat_idx": i,
                                "image_prompt": s.get("image_prompt", ""),
                                "prompt": s.get("video_prompt", ""),
                                "duration": s.get("segment_duration_seconds", 15),
                            }
                            for i, s in enumerate(i2v_specs)
                        ]
                    else:
                        result["status"] = "failed"
                        result["error"] = (
                            "No image_prompt or image_prompts[] in render_spec"
                        )
                        return result

            # Step 1: Generate all reference images in parallel
            print(
                f"[IMAGE_TO_VIDEO] Section {topic_id}: Generating {len(beats)} reference images in parallel..."
            )

            from render.image.image_generator import generate_image_for_beat

            image_paths = {}
            job_id = str(Path(output_dir).parent.name)

            # Generate 2 images per beat in parallel: start frame + end frame
            # image_paths[beat_id] = {"start": path, "end": path_or_None}
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                future_to_key = {}  # future → (beat_id, "start"|"end")
                for beat in beats:
                    beat_id = beat.get("beat_id")
                    for slot in ("start", "end"):
                        img_prompt = beat.get(f"image_prompt_{slot}", "")
                        if not img_prompt:
                            continue
                        future = executor.submit(
                            generate_image_for_beat,
                            beat={
                                "beat_id": f"{beat_id}_{slot}",
                                "image_prompt": img_prompt,
                            },
                            job_id=job_id,
                            section_id=str(topic_id),
                            output_dir=output_dir,
                        )
                        future_to_key[future] = (beat_id, slot)

                for future in concurrent.futures.as_completed(future_to_key):
                    beat_id, slot = future_to_key[future]
                    try:
                        img_path = future.result()
                        if img_path:
                            image_paths.setdefault(beat_id, {})[slot] = img_path
                            print(
                                f"[IMAGE_TO_VIDEO] ✓ Image {beat_id}_{slot}: {Path(img_path).name}"
                            )
                    except Exception as e:
                        print(f"[IMAGE_TO_VIDEO] ✗ Image {beat_id}_{slot}: {e}")

            # ── OUTER RETRY: Re-attempt failed image slots (up to 2 rounds) ───────
            IMAGE_OUTER_RETRIES = 2
            for retry_round in range(IMAGE_OUTER_RETRIES):
                # Collect all (beat_id, slot) pairs that still have no image
                failed_slots = []
                for beat in beats:
                    bid = beat.get("beat_id")
                    for slot in ("start", "end"):
                        img_prompt = beat.get(f"image_prompt_{slot}", "")
                        if not img_prompt:
                            continue  # slot not used
                        if image_paths.get(bid, {}).get(slot):
                            continue  # already succeeded
                        failed_slots.append((bid, slot, img_prompt))

                if not failed_slots:
                    break  # nothing left to retry

                print(
                    f"[IMAGE_TO_VIDEO] Outer retry round {retry_round + 1}/{IMAGE_OUTER_RETRIES}: "
                    f"{len(failed_slots)} image slot(s) still missing — retrying in parallel..."
                )
                with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                    retry_future_to_key = {}
                    for bid, slot, img_prompt in failed_slots:
                        future = executor.submit(
                            generate_image_for_beat,
                            beat={
                                "beat_id": f"{bid}_{slot}",
                                "image_prompt": img_prompt,
                            },
                            job_id=job_id,
                            section_id=str(topic_id),
                            output_dir=output_dir,
                        )
                        retry_future_to_key[future] = (bid, slot)

                    for future in concurrent.futures.as_completed(retry_future_to_key):
                        bid, slot = retry_future_to_key[future]
                        try:
                            img_path = future.result()
                            if img_path:
                                image_paths.setdefault(bid, {})[slot] = img_path
                                print(
                                    f"[IMAGE_TO_VIDEO] ✓ Outer retry {retry_round + 1} succeeded: "
                                    f"{bid}_{slot} → {Path(img_path).name}"
                                )
                        except Exception as e:
                            print(
                                f"[IMAGE_TO_VIDEO] ✗ Outer retry {retry_round + 1} failed: "
                                f"{bid}_{slot}: {e}"
                            )
            # ── END OUTER RETRY ───────────────────────────────────────────────────

            # Step 2: Generate videos in parallel using start + end reference images
            video_beats = []
            for beat in beats:
                beat_id = beat.get("beat_id")
                imgs = image_paths.get(beat_id, {})
                if imgs.get("start"):  # must have at least the start frame
                    # FIX: resolve relative paths to absolute.
                    # generate_image_for_beat() returns relative like "images/job_beat_1_start.jpg"
                    # but LocalGPUClient checks Path(image_path).exists() from CWD, not output_dir.
                    start_path = imgs["start"]
                    if not Path(start_path).is_absolute():
                        start_path = str(Path(output_dir) / start_path)
                    end_path = imgs.get("end")
                    if end_path and not Path(end_path).is_absolute():
                        end_path = str(Path(output_dir) / end_path)
                    video_beats.append(
                        {
                            "beat_id": beat_id,
                            "prompt": beat.get("prompt", ""),
                            "duration": beat.get("duration", 15),
                            "image_path": start_path,  # start frame (absolute)
                            "image_path_end": end_path,  # end frame (absolute, may be None)
                        }
                    )

            if not video_beats:
                result["status"] = "failed"
                result["error"] = "No images generated successfully"
                return result

            # POLICY: image_to_video ALWAYS uses Local GPU (port 8000) to support
            # image_start_token + image_end_token dual-frame API.
            # Kie.ai WAN does NOT support dual-image. Hard-enforce here.
            use_local = True
            if topic.get("use_local_gpu") is False:
                print(
                    f"[IMAGE_TO_VIDEO] Section {topic_id}: use_local_gpu overridden to True "
                    f"(policy: image_to_video always uses Local GPU for dual-frame support)"
                )
            print(
                f"[IMAGE_TO_VIDEO] Section {topic_id}: Rendering {len(video_beats)} videos → Local GPU"
            )

            # Render videos in parallel
            try:
                render_results = _render_videos_parallel(
                    beats=video_beats,
                    output_dir=output_dir,
                    dry_run=dry_run,
                    use_local_gpu=use_local,
                    topic_id=str(topic_id),
                )

                if render_results["success"]:
                    result["status"] = "success"
                    result["all_video_paths"] = render_results["success"]
                    result["all_image_paths"] = list(image_paths.values())

                    # ── WRITEBACK: update narration segments + video_prompts ──
                    import re

                    narration_segs = topic.get("narration", {}).get("segments", [])
                    narr_by_id = {
                        s["segment_id"]: s for s in narration_segs if "segment_id" in s
                    }
                    # Build vp_by_id from whichever source had the prompts
                    all_vps = (
                        image_prompts
                        if image_prompts
                        else (video_prompts if video_prompts else [])
                    )
                    vp_by_id = {
                        p.get("segment_id"): p
                        for p in all_vps
                        if isinstance(all_vps, list) and p.get("segment_id")
                    }

                    # FIX 1: Sort success list by filename so beat_1 is always first
                    render_results["success"].sort(key=lambda p: Path(p).name)

                    beat_video_map = {}
                    for video_path_abs in render_results["success"]:
                        fname = Path(video_path_abs).name  # e.g. topic_4_beat_1.mp4
                        rel_path = f"videos/{fname}"
                        m = re.search(rf"topic_{topic_id}_(.+)\.mp4", fname)
                        extracted_id = m.group(1) if m else None
                        if extracted_id:
                            beat_video_map[extracted_id] = rel_path

                    # 1. Update visual_beats
                    for beat in topic.get("visual_beats", []):
                        bid = beat.get("beat_id")
                        if bid and bid in beat_video_map:
                            beat["video_path"] = beat_video_map[bid]
                            print(
                                f"  [I2V WRITEBACK] visual_beat {bid} → {beat_video_map[bid]}"
                            )

                    # 2. Update narration by beat_id match
                    for eid, rel_path in beat_video_map.items():
                        if eid in narr_by_id:
                            narr_by_id[eid]["video_path"] = rel_path
                            narr_by_id[eid]["beat_videos"] = [rel_path]
                        if eid in vp_by_id:
                            vp_by_id[eid]["video_path"] = rel_path

                    # FIX 3: Index-based fallback (beat_ids != narration seg_ids for image_to_video)
                    # Map i-th video to i-th narration segment when regex id match fails
                    sorted_beat_paths = sorted(beat_video_map.values())
                    for i, seg in enumerate(narration_segs):
                        if seg.get("video_path") is None and i < len(sorted_beat_paths):
                            seg["video_path"] = sorted_beat_paths[i]
                            seg["beat_videos"] = [sorted_beat_paths[i]]
                            print(
                                f"  [I2V WRITEBACK] narr_seg[{i}] fallback → {sorted_beat_paths[i]}"
                            )

                    # FIX 2: Write beat_video_paths + video_path into topic dict (saves to presentation.json)
                    rel_paths = sorted(beat_video_map.values())
                    topic["beat_video_paths"] = rel_paths
                    topic["video_path"] = rel_paths[0] if rel_paths else None
                    result["beat_video_paths"] = rel_paths
                    result["video_path"] = topic["video_path"]

                else:
                    result["status"] = "failed"
                    result["error"] = "All video generations failed"

            except Exception as e:
                result["status"] = "failed"
                result["error"] = str(e)

            return result

        elif renderer == "text_to_video":
            # V3: Generate video from text prompt using Local GPU in parallel
            print(f"[RENDER] Section {topic_id}: Processing text_to_video...")

            if dry_run:
                print(f"[DRY RUN] Section {topic_id}: Would generate text_to_video")
                return {
                    "topic_id": topic_id,
                    "section_type": section_type,
                    "renderer": "text_to_video",
                    "status": "skipped",
                    "video_path": None,
                    "reason": "dry_run",
                }

            # Build beats list for parallel processing
            # Check for video_prompts[] array first (NEW FORMAT - one prompt per segment)
            video_prompts = render_spec.get("video_prompts", [])

            if video_prompts and isinstance(video_prompts, list):
                # NEW FORMAT: video_prompts[] array - one video per segment
                beats = []
                for i, p in enumerate(video_prompts):
                    beat_id = (
                        f"seg_{i + 1}"
                        if isinstance(p, str)
                        else p.get("segment_id", f"seg_{i + 1}")
                    )
                    prompt_text = p if isinstance(p, str) else p.get("prompt", "")
                    duration = 15 if isinstance(p, str) else p.get("duration", 15)
                    beats.append(
                        {
                            "beat_id": beat_id,
                            "beat_idx": i,
                            "prompt": prompt_text,
                            "duration": duration,
                        }
                    )
                print(
                    f"[TEXT_TO_VIDEO] Section {topic_id}: Using video_prompts[] array ({len(beats)} videos)"
                )
            else:
                # FALLBACK: Single video_prompt for entire section
                video_prompt = render_spec.get("video_prompt", "")
                duration = render_spec.get("total_duration_seconds", 15)

                if video_prompt:
                    beats = [
                        {
                            "beat_id": f"seg_1",
                            "beat_idx": 0,
                            "prompt": video_prompt,
                            "duration": duration,
                        }
                    ]
                    print(
                        f"[TEXT_TO_VIDEO] Section {topic_id}: Using single video_prompt (fallback)"
                    )
                else:
                    # OLD FORMAT: Check segment_specs
                    segment_specs = render_spec.get("segment_specs", [])
                    t2v_specs = [
                        s
                        for s in segment_specs
                        if s.get("renderer") in ("text_to_video", "video")
                    ]
                    if t2v_specs:
                        beats = [
                            {
                                "beat_id": s.get("segment_id", f"seg_{i + 1}"),
                                "beat_idx": i,
                                "prompt": s.get("video_prompt", ""),
                                "duration": s.get("segment_duration_seconds", 15),
                            }
                            for i, s in enumerate(t2v_specs)
                        ]
                    else:
                        result["status"] = "failed"
                        result["error"] = (
                            "No video_prompt or video_prompts[] in render_spec"
                        )
                        return result

            # POLICY: text_to_video ALWAYS uses Local GPU (port 8000) for consistency.
            # If Director mistakenly sets use_local_gpu=False, we override it here.
            use_local = True
            if topic.get("use_local_gpu") is False:
                print(
                    f"[TEXT_TO_VIDEO] Section {topic_id}: use_local_gpu overridden to True "
                    f"(policy: text_to_video always uses Local GPU)"
                )
            print(
                f"[TEXT_TO_VIDEO] Section {topic_id}: {len(beats)} videos → Local GPU"
            )

            # Render in parallel using GPU
            try:
                render_results = _render_videos_parallel(
                    beats=beats,
                    output_dir=output_dir,
                    dry_run=dry_run,
                    use_local_gpu=use_local,
                    topic_id=str(topic_id),
                )

                if render_results["success"]:
                    result["status"] = "success"
                    result["all_video_paths"] = render_results["success"]

                    # ── WRITEBACK: update narration segments + video_prompts ──
                    narration_segs = topic.get("narration", {}).get("segments", [])
                    narr_by_id = {
                        s["segment_id"]: s for s in narration_segs if "segment_id" in s
                    }
                    vp_by_id = {
                        p.get("segment_id"): p
                        for p in video_prompts
                        if isinstance(video_prompts, list) and p.get("segment_id")
                    }

                    import re

                    # FIX 1: Sort success list by filename so seg_1 is always first
                    render_results["success"].sort(key=lambda p: Path(p).name)

                    beat_video_map = {}
                    for video_path_abs in render_results["success"]:
                        fname = Path(video_path_abs).name  # e.g. topic_6_seg_1.mp4
                        rel_path = f"videos/{fname}"
                        m = re.search(rf"topic_{topic_id}_(.+)\.mp4", fname)
                        extracted_id = m.group(1) if m else None
                        if extracted_id:
                            beat_video_map[extracted_id] = rel_path

                    # 1. Update visual_beats
                    for beat in topic.get("visual_beats", []):
                        bid = beat.get("beat_id")
                        if bid and bid in beat_video_map:
                            beat["video_path"] = beat_video_map[bid]
                            print(
                                f"  [T2V WRITEBACK] visual_beat {bid} → {beat_video_map[bid]}"
                            )

                    # 2. Update narration / video_prompts
                    for eid, rel_path in beat_video_map.items():
                        if eid in narr_by_id:
                            narr_by_id[eid]["video_path"] = rel_path
                            narr_by_id[eid]["beat_videos"] = [rel_path]
                            print(f"  [T2V WRITEBACK] narr_seg {eid} → {rel_path}")
                        if eid in vp_by_id:
                            vp_by_id[eid]["video_path"] = rel_path

                    # FIX 2: Write beat_video_paths + video_path into topic dict (saves to presentation.json)
                    rel_paths = sorted(beat_video_map.values())
                    topic["beat_video_paths"] = rel_paths
                    topic["video_path"] = rel_paths[0] if rel_paths else None
                    result["beat_video_paths"] = rel_paths
                    result["video_path"] = topic["video_path"]

                else:
                    result["status"] = "failed"
                    result["error"] = "All video generations failed"

            except Exception as e:
                result["status"] = "failed"
                result["error"] = str(e)

            return result

        elif renderer == "infographic":
            # V3: Generate static image only (no video animation)
            print(f"[RENDER] Section {topic_id}: Processing infographic...")

            if dry_run:
                print(f"[DRY RUN] Section {topic_id}: Would generate infographic")
                return {
                    "topic_id": topic_id,
                    "section_type": section_type,
                    "renderer": "infographic",
                    "status": "skipped",
                    "image_path": None,
                    "reason": "dry_run",
                }

            # NEW FORMAT: Use render_spec.infographic_beats directly
            infographic_beats = render_spec.get("infographic_beats", [])

            # OLD FORMAT: Check segment_specs for infographic specs
            segment_specs = render_spec.get("segment_specs", [])
            info_specs_old = [
                s for s in segment_specs if s.get("renderer") == "infographic"
            ]

            # If infographic_beats exist, use new format
            if infographic_beats:
                beats_data = infographic_beats
            elif info_specs_old:
                # Use old format from segment_specs
                beats_data = info_specs_old
            else:
                result["status"] = "failed"
                result["error"] = "No infographic_beats in render_spec"
                return result

            # Import image generator
            try:
                from render.image.image_generator import generate_image_for_beat
            except ImportError as e:
                logger.error(f"[Renderer] Image generator import failed: {e}")
                result["status"] = "failed"
                result["error"] = f"Image generator not available: {e}"
                return result

            image_paths = []
            # job_id: output_dir is the job root (e.g. .../jobs/JOB_ID), so .name gives the job ID directly
            job_id = str(Path(output_dir).name)

            for beat in beats_data:
                beat_id = beat.get("beat_id", f"inf_{len(image_paths)}")
                image_prompt = beat.get("image_prompt", "")

                if not image_prompt:
                    logger.warning(f"[Renderer] No image_prompt for {beat_id}")
                    continue

                # Generate static image
                beat_data = {"beat_id": beat_id, "image_prompt": image_prompt}

                image_path = generate_image_for_beat(
                    beat_data, job_id, topic_id, output_dir
                )

                if image_path:
                    image_paths.append(image_path)
                    # Write path back into the beat dict (Bug fix: was `spec`, stale ref from outer loop)
                    beat["image_path"] = f"images/{Path(image_path).name}"
                    print(f"  [{beat_id}] -> infographic complete: {image_path}")

            if image_paths:
                result["status"] = "success"
                result["image_path"] = (
                    image_paths[0] if len(image_paths) == 1 else image_paths
                )
                result["all_image_paths"] = image_paths
            else:
                result["status"] = "failed"
                result["error"] = "No images generated"

            return result

        elif renderer == "image":
            # V3: Use existing source image (no generation needed)
            print(f"[RENDER] Section {topic_id}: Using source image (no generation)")
            render_spec = topic.get("render_spec", {})
            segment_specs = render_spec.get("segment_specs", [])

            image_paths = []
            for spec in segment_specs:
                if spec.get("renderer") == "image":
                    image_source = spec.get("image_source")
                    if image_source:
                        image_paths.append(image_source)
                        print(
                            f"  [{spec.get('segment_id')}] -> source image: {image_source}"
                        )

            if image_paths:
                result["status"] = "success"
                result["image_path"] = image_paths[0]
                result["all_image_paths"] = image_paths
            else:
                result["status"] = "skipped"
                result["reason"] = "no source images provided"

            return result

        else:
            # Route based on video_provider
            # Log renderer choice reasons for text_to_video segments
            segment_specs = topic.get("render_spec", {}).get("segment_specs", [])
            for spec in segment_specs:
                if spec.get("renderer") in ("text_to_video", "video", "wan_video"):
                    reason = spec.get("renderer_choice_reason", "No reason provided")
                    print(f"    [{spec.get('segment_id')}] Reason: {reason}")

            if video_provider == "ltx":
                if render_ltx_video is None:
                    raise ImportError("LTX runner could not be imported")
                print(f"[RENDER] Section {topic_id}: Using LTX provider")
                video_path = render_ltx_video(
                    topic,
                    output_dir,
                    dry_run=dry_run,
                    skip_wan=skip_wan,
                    trace_output_dir=trace_output_dir,
                )
            else:
                # Default to Kie/WAN
                print(f"[RENDER] Section {topic_id}: Using Kie/WAN provider")
                video_path = render_wan_video(
                    topic,
                    output_dir,
                    dry_run=dry_run,
                    skip_wan=skip_wan,
                    trace_output_dir=trace_output_dir,
                )

        # ISS-093 FIX: Handle different return types from renderers
        # FIX: Also handle None returns (failed generation - no placeholder)
        if isinstance(video_path, list):
            # Filter out None values (failed beats)
            valid_paths = [p for p in video_path if p is not None]
            failed_count = len(video_path) - len(valid_paths)

            if valid_paths:
                result["video_path"] = f"videos/{Path(valid_paths[0]).name}"
                result["beat_video_paths"] = [
                    f"videos/{Path(p).name}" for p in valid_paths
                ]
                result["beat_videos"] = result["beat_video_paths"]
                result["all_video_paths"] = valid_paths
                result["status"] = "success" if failed_count == 0 else "partial"
                if failed_count > 0:
                    result["video_status"] = (
                        f"partial_failure_{failed_count}_of_{len(video_path)}_failed"
                    )
                print(
                    f"[RENDER] Manim multi-beat: {len(valid_paths)}/{len(video_path)} beat videos for section {topic_id}"
                )

                # --- NEW WRITEBACK LOGIC for MANIM ---
                beat_video_map = {}
                import re

                for path_str in valid_paths:
                    fname = Path(path_str).name
                    rel_path = f"videos/{fname}"
                    m = re.search(rf"topic_{topic_id}_(.+)\.mp4", fname)
                    if m:
                        beat_video_map[m.group(1)] = rel_path

                # Update visual_beats
                for beat in topic.get("visual_beats", []):
                    bid = beat.get("beat_id")
                    if bid and bid in beat_video_map:
                        beat["video_path"] = beat_video_map[bid]

                # Update narration
                narr_segs = topic.get("narration", {}).get("segments", [])
                for seg in narr_segs:
                    eid = seg.get("segment_id")
                    if eid in beat_video_map:
                        seg["video_path"] = beat_video_map[eid]
                        seg["beat_videos"] = [beat_video_map[eid]]

                # FIX: Index-based fallback for manim (manim outputs beat_0, beat_1... but json has beat_1, seg_1)
                sorted_beat_paths = sorted(beat_video_map.values())

                # 1. Fallback for visual_beats
                for i, beat in enumerate(topic.get("visual_beats", [])):
                    if beat.get("video_path") is None and i < len(sorted_beat_paths):
                        beat["video_path"] = sorted_beat_paths[i]

                # 2. Fallback for narration
                for i, seg in enumerate(narr_segs):
                    if seg.get("video_path") is None and i < len(sorted_beat_paths):
                        seg["video_path"] = sorted_beat_paths[i]
                        seg["beat_videos"] = [sorted_beat_paths[i]]
                # ------------------------------------
            else:
                result["status"] = "failed"
                result["video_status"] = "generation_failed"
                result["error"] = "All video generations failed"
                print(
                    f"[RENDER] Section {topic_id}: ALL beat videos failed to generate"
                )

        elif isinstance(video_path, dict):
            all_paths = video_path.get("all_paths", [])
            valid_paths = [p for p in all_paths if p is not None]
            failed_count = len(all_paths) - len(valid_paths)

            if valid_paths:
                result["video_path"] = valid_paths[0]
                result["recap_video_paths"] = valid_paths
                result["status"] = "success" if failed_count == 0 else "partial"
                if failed_count > 0:
                    result["video_status"] = (
                        f"partial_failure_{failed_count}_of_{len(all_paths)}_failed"
                    )
                print(
                    f"[RENDER] WAN recap: {len(valid_paths)}/{len(all_paths)} videos for section {topic_id}"
                )
            else:
                result["status"] = "failed"
                result["video_status"] = "generation_failed"
                result["error"] = "All recap video generations failed"
                print(
                    f"[RENDER] Section {topic_id}: ALL recap videos failed to generate"
                )

        elif video_path is None:
            # Single video failed
            result["status"] = "failed"
            result["video_status"] = "generation_failed"
            result["error"] = "Video generation failed - no video created"
            print(
                f"[RENDER] Section {topic_id}: Video generation FAILED (no placeholder)"
            )
        else:
            result["video_path"] = video_path
            result["status"] = "success"

        if topic.get("_recap_video_paths"):
            recap_paths = topic["_recap_video_paths"]
            valid_recap = [p for p in recap_paths if p is not None]
            if valid_recap:
                result["recap_video_paths"] = valid_recap

        if topic.get("_beat_video_paths"):
            beat_paths = topic["_beat_video_paths"]
            valid_beats = [p for p in beat_paths if p is not None]
            if valid_beats:
                result["beat_video_paths"] = valid_beats
                print(
                    f"[RENDER] Captured {len(valid_beats)} content beat paths for section {topic_id}"
                )
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        print(f"Error rendering topic {topic_id}: {e}")

    result["duration_seconds"] = round(time.time() - render_start, 2)
    return result


def validate_before_render(
    presentation: dict, output_dir: str, strict_v13: bool = True
) -> DryRunValidationResult:
    """
    ISS-078 FIX: Run comprehensive validation before rendering.

    This validates all render specs are complete:
    - WAN prompts have 80+ words (v1.3 per Director Bible)
    - Manim scene specs are complete
    - Display directives are present
    - Renderer-subject matches are valid

    Args:
        presentation: The presentation dict
        output_dir: Output directory for videos
        strict_v13: Enforce v1.3 requirements

    Returns:
        DryRunValidationResult with all errors and warnings
    """
    result = validate_presentation_dry_run(
        presentation, output_dir, strict_v13=strict_v13
    )

    report = format_validation_report(result)
    print(report)

    report_path = Path(output_dir).parent / "dry_run_validation.txt"
    try:
        with open(report_path, "w") as f:
            f.write(report)
        print(f"[DRY RUN] Validation report saved to: {report_path}")
    except Exception as e:
        print(f"[DRY RUN] Could not save report: {e}")

    return result


def render_all_topics(
    presentation: dict,
    output_dir: str,
    dry_run: bool = False,
    skip_wan: bool = False,
    output_dir_base: str = "",
    strict_mode: bool = True,
    renderer_filter: str = None,
    video_provider: str = "ltx",
) -> list:
    os.makedirs(output_dir, exist_ok=True)

    # Reset WAN hash cache at start of each render job to prevent cross-job duplicate detection
    if not dry_run and not skip_wan:
        try:
            from render.wan.wan_runner import reset_wan_session

            reset_wan_session()
        except ImportError:
            pass  # WAN module not available

    trace_output_dir = output_dir_base or str(Path(output_dir).parent)

    if dry_run:
        print("[DRY RUN] Running comprehensive validation before render simulation...")
        validation_result = validate_before_render(
            presentation, output_dir, strict_v13=strict_mode
        )

        if not validation_result.is_valid:
            print(
                f"[DRY RUN] VALIDATION FAILED with {len(validation_result.errors)} errors (PROCEEDING AS REQUESTED)"
            )
        else:
            print(
                f"[DRY RUN] Validation PASSED ({len(validation_result.warnings)} warnings)"
            )

    topics = presentation.get("sections", presentation.get("topics", []))
    success_count = 0
    fail_count = 0
    compile_fail_count = 0

    mode_label = "[DRY RUN] " if dry_run else ""
    skip_label = "[SKIP WAN] " if skip_wan else ""
    strict_label = "[STRICT] " if strict_mode else ""

    logger.info(
        f"{mode_label}{skip_label}{strict_label}Starting Parallel Render for {len(topics)} topics..."
    )

    # Filter topics if requested (e.g., only run "manim" in blocking phase)
    if renderer_filter:
        filtered_topics = []
        for t in topics:
            r = t.get("renderer", "none")
            if renderer_filter == "manim" and r == "manim":
                filtered_topics.append(t)
            elif renderer_filter == "wan" and r in ["wan", "wan_video"]:
                filtered_topics.append(t)
            elif renderer_filter == "threejs" and r == "threejs":
                filtered_topics.append(t)
        topics = filtered_topics
        logger.info(f"Filtered topics for '{renderer_filter}': {len(topics)} remaining")

    import concurrent.futures

    rendered_videos = [None] * len(topics)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_idx = {
            executor.submit(
                execute_renderer,
                topic,
                output_dir,
                dry_run,
                skip_wan,
                trace_output_dir,
                strict_mode,
                video_provider,
            ): i
            for i, topic in enumerate(topics)
        }

        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            topic_id = topics[idx].get("section_id", topics[idx].get("id", idx + 1))
            try:
                result = future.result()
                rendered_videos[idx] = result

                if result["status"] == "success":
                    success_count += 1
                    print(f"  [{topic_id}] -> Success: {result['video_path']}")
                elif result["status"] == "skipped":
                    success_count += 1
                    print(
                        f"  [{topic_id}] -> Skipped: {result.get('reason', 'No video needed')}"
                    )
                elif result["status"] == "compilation_failed":
                    compile_fail_count += 1
                    print(f"  [{topic_id}] -> Compilation Failed: {result['error']}")
                else:
                    fail_count += 1
                    print(
                        f"  [{topic_id}] -> Failed: {result.get('error', 'Unknown error')}"
                    )
            except Exception as e:
                fail_count += 1
                logger.error(f"  [{topic_id}] -> Execution Critical Error: {e}")
                rendered_videos[idx] = {
                    "status": "failed",
                    "error": str(e),
                    "topic_id": topic_id,
                }

    print(
        f"{mode_label}{skip_label}{strict_label}Rendering complete: {success_count} success, {compile_fail_count} compilation failures, {fail_count} render failures"
    )
    return rendered_videos


def submit_wan_background_job(
    presentation: dict,
    output_dir: str,
    job_id: str,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    video_provider: str = "ltx",
):
    """
    Submits video generation tasks to Kie.ai or LTX.
    Routing: sections with use_local_gpu=True → Local GPU server
             sections with use_local_gpu=False (or missing) → Kie.ai WAN
    """
    try:
        from render.wan.kie_batch_generator import KieBatchGenerator
        from render.wan.local_gpu_client import LocalGPUClient
        from render.render_trace import log_render_prompt, set_trace_output_dir

        try:
            from core.job_manager import job_manager

            if job_manager and not skip_wan:
                job_manager.update_job(
                    job_id,
                    {
                        "status": "processing",
                        "current_step_name": f"Generating Video ({video_provider.upper()})...",
                        "current_phase_key": "video_generation",
                    },
                    persist=True,
                )
        except:
            pass

        print(
            f"[BG-JOB] Starting background generation for job {job_id} using {video_provider}"
        )

        topics = presentation.get("sections", [])

        # ── Routing: split beats by use_local_gpu flag ─────────────────────────
        # kie_beats  → Kie.ai WAN API (biology/anatomy or use_local_gpu=False)
        # local_beats_by_topic → Local GPU server (general content, use_local_gpu=True)
        kie_beats = []
        local_beats_by_topic = []  # list of (topic, sanitized_beats)
        topic_id_to_beats = {}  # shared: section_id → [beat_ids] for result mapping

        job_output_dir = Path(output_dir).parent
        set_trace_output_dir(str(job_output_dir))

        for topic in topics:
            renderer = topic.get("renderer", "none")
            if renderer not in ["wan", "wan_video", "video"]:
                continue

            # V3 FIX: Also check render_spec.segment_specs for V3-style sections
            # V3 stores beat-level prompts in segment_specs, not video_prompts at section level
            beats = topic.get("video_prompts", [])
            segment_specs = (topic.get("render_spec") or {}).get("segment_specs", [])

            # If no video_prompts but segment_specs exist, extract beats from segment_specs
            if not beats and segment_specs:
                beats = []
                for seg in segment_specs:
                    seg_renderer = seg.get("renderer", "")
                    # Only include segments that need WAN/LTX video generation
                    if seg_renderer in ["image_to_video", "text_to_video"]:
                        video_prompt = seg.get("video_prompt", "")
                        if video_prompt:
                            beats.append(
                                {
                                    "beat_id": seg.get(
                                        "segment_id", f"beat_{len(beats)}"
                                    ),
                                    "prompt": video_prompt,
                                    "renderer": seg_renderer,
                                }
                            )
                    elif seg_renderer == "video":
                        # Fallback: check for video_prompt at segment level
                        video_prompt = seg.get("video_prompt", "")
                        if video_prompt:
                            beats.append(
                                {
                                    "beat_id": seg.get(
                                        "segment_id", f"beat_{len(beats)}"
                                    ),
                                    "prompt": video_prompt,
                                    "renderer": "video",
                                }
                            )
                if beats:
                    print(
                        f"[BG-JOB] V3: Extracted {len(beats)} beats from segment_specs for section {topic.get('section_id')}"
                    )

            if not beats:
                continue

            # Sanitize beats
            sanitized_beats = []
            for b in beats:
                if isinstance(b, str):
                    sanitized_beats.append(
                        {"beat_id": f"beat_{len(sanitized_beats)}", "prompt": b}
                    )
                elif isinstance(b, dict):
                    sanitized_beats.append(b)

            topic_id_to_beats[topic.get("section_id")] = [
                b.get("beat_id") for b in sanitized_beats
            ]

            # Log prompts for debugging
            for beat in sanitized_beats:
                log_render_prompt(
                    section_id=topic.get("section_id"),
                    section_title=topic.get("title", "Unknown"),
                    renderer="wan_background",
                    prompt=beat.get("prompt", ""),
                    output_path=str(Path(output_dir) / f"{beat.get('beat_id')}.mp4"),
                    extra_data={"job_id": job_id, "source": "background_retry"},
                )

            # ROUTING DECISION: use_local_gpu field set by Director LLM
            # Default is True (Local GPU) — Director LLM only sets False for biology/anatomy
            use_local = topic.get("use_local_gpu", True)
            if use_local:
                print(
                    f"[ROUTER] Section {topic.get('section_id')} '{topic.get('title', '?')}' → Local GPU"
                )
                local_beats_by_topic.append((topic, sanitized_beats))
            else:
                print(
                    f"[ROUTER] Section {topic.get('section_id')} '{topic.get('title', '?')}' → Kie.ai WAN (use_local_gpu=False, biology/anatomy)"
                )
                kie_beats.extend(sanitized_beats)

        total_beats = len(kie_beats) + sum(len(b) for _, b in local_beats_by_topic)
        print(
            f"[BG-JOB] Found {total_beats} total beats: {len(kie_beats)} → Kie.ai, {total_beats - len(kie_beats)} → Local GPU"
        )

        if not total_beats:
            logger.info(f"[BG-JOB] No beats found for job {job_id}")
            if skip_avatar:
                try:
                    from core.job_manager import job_manager

                    if job_manager:
                        job_manager.complete_job(job_id)
                except:
                    pass
            return

        if skip_wan:
            logger.info(f"[BG-JOB] Video generation skipped per request")
            if skip_avatar:
                try:
                    from core.job_manager import job_manager

                    if job_manager:
                        job_manager.complete_job(job_id)
                except:
                    pass
            return

        results = {}  # beat_id → path (merged from all providers)
        all_sanitized_beats = []  # track all beats for final presentation update

        # ── Step A: Local GPU beats ────────────────────────────────────────────
        if local_beats_by_topic:
            local_client = LocalGPUClient()
            gpu_available = local_client.is_available()
            if not gpu_available:
                print(
                    f"[ROUTER] Local GPU unavailable — falling back all local beats to Kie.ai WAN"
                )

            # Collect all individual beats for parallel processing
            all_local_beats = []
            for topic, beats in local_beats_by_topic:
                for beat in beats:
                    all_local_beats.append((topic, beat))

            if gpu_available:
                print(
                    f"[LocalGPU] Processing {len(all_local_beats)} beats in parallel (max_workers=3)"
                )
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    # beat_id -> (future, beat_obj)
                    future_to_beat = {}
                    for topic, beat in all_local_beats:
                        beat_id = beat.get("beat_id", "")
                        prompt = (
                            beat.get("prompt")
                            or beat.get("video_prompt")
                            or beat.get("wan_prompt")
                            or beat.get(
                                "description"
                            )  # recap/video_prompts uses 'description'
                            or ""
                        )
                        if not prompt:
                            print(
                                f"[LocalGPU] Beat {beat_id}: No prompt text found, keys={list(beat.keys())}. Skipping."
                            )
                            continue
                        # V2.6: Use duration_seconds if available (narration sync), else duration_hint
                        duration = int(
                            beat.get("duration_seconds")
                            or beat.get("duration_hint")
                            or 5
                        )
                        out_path = str(Path(output_dir) / f"{beat_id}.mp4")

                        future = executor.submit(
                            local_client.generate_video,
                            prompt,
                            duration=duration,
                            output_path=out_path,
                        )
                        future_to_beat[future] = (beat, beat_id)

                    for future in concurrent.futures.as_completed(future_to_beat):
                        beat, beat_id = future_to_beat[future]
                        try:
                            video_path = future.result()
                            if video_path:
                                results[beat_id] = video_path
                                all_sanitized_beats.append(beat)
                                print(f"[LocalGPU] ✓ Beat {beat_id} done: {video_path}")
                            else:
                                # Individual beat fallback to Kie.ai
                                print(
                                    f"[LocalGPU] ✗ Beat {beat_id} failed → falling back to Kie.ai"
                                )
                                kie_beats.append(beat)
                        except Exception as e:
                            print(
                                f"[LocalGPU] ✗ Beat {beat_id} execution error: {e} → falling back to Kie.ai"
                            )
                            kie_beats.append(beat)
            else:
                # GPU not available at all, fallback everything
                for topic, beat in all_local_beats:
                    kie_beats.append(beat)

        # ── Step B: Kie.ai WAN beats (biology/anatomy + any Local GPU fallbacks) ─
        if video_provider == "ltx":
            from render.ltx.ltx_client import LtxClient

            client = LtxClient()
            logger.info(f"[LTX-BG] Starting processing of {len(kie_beats)} beats...")
            for i, beat_obj in enumerate(kie_beats):
                prompt = (
                    beat_obj.get("prompt")
                    or beat_obj.get("video_prompt")
                    or beat_obj.get("wan_prompt")
                    or ""
                )
                beat_id = beat_obj.get("beat_id", f"beat_{i}")
                duration = int(
                    beat_obj.get("duration_seconds")
                    or beat_obj.get("duration_hint")
                    or 5
                )

                # Check if file already exists (resume capability)
                vid_filename = f"ltx_{job_id}_{beat_id}.mp4"
                out_path = Path(output_dir) / vid_filename

                if out_path.exists():
                    print(f"[LTX-BG] Skipping existing: {out_path}")
                    results[beat_id] = str(out_path)
                    continue

                try:
                    print(
                        f"[LTX-BG] ▶ Processing beat {i + 1}/{len(kie_beats)}: {beat_id} (duration={duration}s)"
                    )
                    print(f"[LTX-BG]   Prompt: {prompt[:80]}...")
                    p = client.generate_video(
                        prompt, output_path=str(out_path), duration=duration
                    )
                    results[beat_id] = p
                    print(f"[LTX-BG] ✓ Beat {beat_id} complete: {p}")
                except Exception as e:
                    logger.error(f"[LTX-BG] ✗ Error generating beat {beat_id}: {e}")

            all_sanitized_beats.extend(kie_beats)
            logger.info(f"[LTX-BG] All beats processed.")

        else:
            # Kie.ai WAN batch (biology/anatomy sections + Local GPU fallbacks)
            if kie_beats:
                wan_status_path = Path(output_dir).parent / "wan_status.json"
                batch_gen = KieBatchGenerator(status_file_path=str(wan_status_path))
                kie_results = batch_gen.generate_batch(kie_beats, output_dir)
                results.update(kie_results)
                all_sanitized_beats.extend(kie_beats)

        # 2. Update sanitized prompts back (kie_beats may have been rewritten by safety LLM)
        for beat in all_sanitized_beats:
            beat_id = beat.get("beat_id")
            result = results.get(beat_id)

            # Results now contain: {"path": "...", "prompt": "sanitized_prompt"}
            if isinstance(result, dict) and "prompt" in result:
                original_prompt = beat.get("prompt")
                sanitized_prompt = result["prompt"]

                if original_prompt != sanitized_prompt:
                    # Prompt was sanitized - update the beat object
                    beat["prompt"] = sanitized_prompt
                    logger.info(
                        f"[NSFW-FIX] Updated prompt for {beat_id}: '{original_prompt[:40]}...' -> '{sanitized_prompt[:40]}...'"
                    )

        # 3. Update Files (Shared Logic)
        pres_path = Path(output_dir).parent / "presentation.json"

        for topic_id, beat_ids in topic_id_to_beats.items():
            # For each topic, find the corresponding results
            topic_results = {
                bid: results.get(bid) for bid in beat_ids if bid in results
            }
            if topic_results:
                # Extract paths for file update (maintain backward compatibility)
                first_result = list(topic_results.values())[0]
                video_path = (
                    first_result["path"]
                    if isinstance(first_result, dict)
                    else first_result
                )

                _update_presentation_safely(
                    pres_path,
                    topic_id,
                    video_path,
                    {
                        "status": "success",
                        "beat_video_paths": [
                            r["path"] if isinstance(r, dict) else r
                            for r in topic_results.values()
                        ],
                        "topic_results": topic_results,
                        "wan_beats": all_sanitized_beats,  # Pass updated beats with sanitized prompts
                    },
                )
                _update_analytics_safely(
                    pres_path.parent / "analytics.json",
                    topic_id,
                    {"status": "success", "duration_seconds": 0},
                )

        logger.info(f"[BG-JOB] All tasks complete for job {job_id}")

        if skip_avatar:
            try:
                from core.job_manager import job_manager

                if job_manager:
                    job_manager.complete_job(job_id)
                    print(f"[BG-JOB] Job {job_id} marked as completed (Avatar skipped)")
            except:
                pass

    except Exception as e:
        logger.error(f"[BG-JOB] Fatal error in background thread: {e}")
        traceback.print_exc()


def _update_presentation_safely(
    pres_path: Path, section_id: str, video_path: str, result: dict
):
    """Helper to safely update presentation.json with new video paths."""
    try:
        if not pres_path.exists():
            return

        import json

        # Use a global lock to prevent race conditions during parallel updates
        with presentation_lock:
            with open(pres_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            updated = False
            for section in data.get("sections", []):
                # ISS-ID-FIX: Cast both to string to ensure matching regardless of type (int vs str)
                if str(section.get("section_id")) == str(section_id):
                    # Update paths
                    rel_path = Path(video_path).name
                    section["video_path"] = f"videos/{rel_path}"

                    # ── V3 FIX: Write segment_specs video_path back to disk ────────
                    # Background job generates video as ltx_{job_id}_{beat_id}.mp4
                    # where beat_id = "topic_N_seg_X_beat_1". Match and write back.
                    topic_results = result.get("topic_results", {})
                    if topic_results:
                        render_spec = section.get("render_spec", {})
                        seg_specs = render_spec.get("segment_specs", [])
                        for seg in seg_specs:
                            seg_id = seg.get("segment_id", "")
                            # beat_id in background job is topic_{topic_id}_{seg_id}_beat_1
                            beat_id_pattern = f"topic_{section_id}_{seg_id}_beat_1"
                            for bid, bpath in topic_results.items():
                                if bid == beat_id_pattern or bid.endswith(
                                    f"_{seg_id}_beat_1"
                                ):
                                    actual_path = (
                                        bpath["path"]
                                        if isinstance(bpath, dict)
                                        else bpath
                                    )
                                    if actual_path:
                                        seg["video_path"] = (
                                            f"videos/{Path(actual_path).name}"
                                        )
                                        print(
                                            f"  [V3-UPDATE] Wrote video_path for {seg_id}: {seg['video_path']}"
                                        )
                                    break
                    # ──────────────────────────────────────────────────────────────

                    beat_videos = result.get("beat_videos", [])
                    recap_video_paths = result.get("recap_video_paths", [])
                    content_beat_paths = result.get("beat_video_paths", [])

                    # V2.5 Logic: If we have multiple content beats, map them back to segments
                    if content_beat_paths:
                        # Build a map of beat_id -> path using the section's video_prompts
                        v_prompts = section.get("video_prompts", [])
                        beat_id_to_path = {}
                        for i, p_obj in enumerate(v_prompts):
                            if i < len(content_beat_paths):
                                b_id = (
                                    p_obj.get("beat_id")
                                    if isinstance(p_obj, dict)
                                    else f"beat_{i}"
                                )
                                b_path = f"videos/{Path(content_beat_paths[i]).name}"
                                beat_id_to_path[b_id] = b_path

                        # Ensure strict alignment with segments for Player V2 compatibility
                        aligned_paths = []
                        if (
                            "narration" in section
                            and "segments" in section["narration"]
                        ):
                            for seg in section["narration"]["segments"]:
                                seg_path = None
                                if "beat_videos" in seg:
                                    # Convert IDs to Paths and pull the first one for the segment-level alignment list
                                    resolved_paths = []
                                    for bid in seg["beat_videos"]:
                                        p = beat_id_to_path.get(bid)
                                        if p:
                                            resolved_paths.append(p)
                                        else:
                                            resolved_paths.append(
                                                bid
                                            )  # Keep ID if not found

                                    seg["beat_videos"] = resolved_paths
                                    if resolved_paths and resolved_paths[0].startswith(
                                        "videos/"
                                    ):
                                        seg_path = resolved_paths[0]

                                aligned_paths.append(seg_path)

                        # Only apply aligned_paths if at least one path was successfully mapped
                        if aligned_paths and any(p is not None for p in aligned_paths):
                            section["beat_video_paths"] = aligned_paths
                        else:
                            # Fallback to the raw sequential paths (e.g. for recap sections)
                            section["beat_video_paths"] = [
                                f"videos/{Path(p).name}" for p in content_beat_paths
                            ]
                        print(
                            f"  [BC-UPDATE] Mapped {len(beat_id_to_path)} beat videos to segments in section {section_id}"
                        )

                    if beat_videos and not content_beat_paths:
                        section["beat_videos"] = [
                            f"videos/{Path(p).name}" for p in beat_videos
                        ]
                    if recap_video_paths:
                        section["recap_video_paths"] = [
                            f"videos/{Path(p).name}" for p in recap_video_paths
                        ]

                    # NEW: Update video_prompts with sanitized versions (NSFW fix)
                    wan_beats = result.get("wan_beats", [])
                    if wan_beats and "video_prompts" in section:
                        prompts_updated = 0
                        for beat in wan_beats:
                            beat_id = beat.get("beat_id")
                            sanitized_prompt = beat.get("prompt")

                            # Find matching prompt in section and update
                            for vp in section["video_prompts"]:
                                if (
                                    isinstance(vp, dict)
                                    and vp.get("beat_id") == beat_id
                                ):
                                    if vp.get("prompt") != sanitized_prompt:
                                        vp["prompt"] = sanitized_prompt
                                        prompts_updated += 1
                                        logger.info(
                                            f"[JSON-SAVE] Persisted sanitized prompt for {beat_id}"
                                        )

                        if prompts_updated > 0:
                            logger.info(
                                f"[NSFW-FIX] Updated {prompts_updated} prompts in presentation.json for section {section_id}"
                            )

                    updated = True
                    break

            if updated:
                with open(pres_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)

    except Exception as e:
        logger.error(f"Failed to update presentation.json: {e}")


def _update_analytics_safely(analytics_path: Path, section_id: str, result: dict):
    """Helper to safely update analytics.json with new render results."""
    try:
        if not analytics_path.exists():
            return

        import json
        from datetime import datetime

        with analytics_lock:
            with open(analytics_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Update renderer metrics (Standard Schema)
            if "renderer" not in data:
                data["renderer"] = {
                    "manim_videos": 0,
                    "wan_videos": 0,
                    "static_slides": 0,
                    "failed_renders": 0,
                    "section_renders": [],
                }

            metrics = data["renderer"]

            if result["status"] == "success":
                # Assuming WAN since this is the WAN BG job
                beat_count = len(result.get("beat_video_paths", [])) or 1
                metrics["wan_videos"] = metrics.get("wan_videos", 0) + beat_count
            else:
                metrics["failed_renders"] = metrics.get("failed_renders", 0) + 1

            # Add detailed entry to 'section_renders' list
            if "section_renders" not in metrics:
                metrics["section_renders"] = []

            detail = {
                "section_id": section_id,
                "section_type": result.get(
                    "section_type", "content"
                ),  # Capture type if available
                "renderer": "wan",  # We know this is WAN context
                "duration_seconds": round(result.get("duration_seconds", 0), 2),
                "status": result["status"],
                "timestamp": datetime.utcnow().isoformat(),
            }

            if result.get("error"):
                detail["metadata"] = {"error": result["error"]}

            metrics["section_renders"].append(detail)

            with open(analytics_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

    except Exception as e:
        logger.error(f"Failed to update analytics.json: {e}")

    topic_id = topic.get("section_id", "unknown")
    results = {"success": [], "failed": [], "skipped": []}

    # Create images folder
    images_dir = Path(output_dir).parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    job_id = str(Path(output_dir).parent.name)

    print(
        f"[PROCESS INDIVIDUAL] Section {topic_id}: Processing {len(segment_specs)} segments..."
    )

    for i, spec in enumerate(segment_specs):
        seg_id = spec.get("segment_id", f"seg_{i}")
        renderer = spec.get("renderer", "")

        print(f"  [{seg_id}] Processing renderer: {renderer}")

        if renderer == "none" or not renderer:
            print(f"    -> Skipping (none renderer)")
            results["skipped"].append({"segment_id": seg_id, "reason": "none renderer"})
            continue

        try:
            if renderer == "text_to_video" or renderer == "video":
                # Text-to-video using LTX
                video_prompt = spec.get("video_prompt", "")
                if not video_prompt:
                    print(f"    -> ERROR: No video_prompt")
                    results["failed"].append(
                        {"segment_id": seg_id, "reason": "no video_prompt"}
                    )
                    continue

                duration = spec.get("segment_duration_seconds", 15)
                video_output = str(Path(output_dir) / f"topic_{topic_id}_{seg_id}.mp4")

                if dry_run:
                    print(f"    -> DRY RUN: Would generate text_to_video")
                    continue

                client = LtxClient()
                video_path = client.generate_video(
                    prompt=video_prompt,
                    duration=int(duration),
                    output_path=video_output,
                )

                if video_path:
                    spec["video_path"] = f"videos/{Path(video_path).name}"
                    print(f"    -> SUCCESS: {video_path}")
                    results["success"].append(
                        {"segment_id": seg_id, "video_path": video_path}
                    )
                else:
                    results["failed"].append(
                        {"segment_id": seg_id, "reason": "generation failed"}
                    )

            elif renderer == "image_to_video":
                # Image-to-video: Generate image first, then video
                image_prompt = spec.get("image_prompt", "")
                video_prompt = spec.get("video_prompt", "")

                if not image_prompt:
                    print(f"    -> ERROR: No image_prompt")
                    results["failed"].append(
                        {"segment_id": seg_id, "reason": "no image_prompt"}
                    )
                    continue

                if dry_run:
                    print(f"    -> DRY RUN: Would generate image_to_video")
                    continue

                # Step 1: Generate image
                beat_data = {
                    "beat_id": seg_id,
                    "image_prompt": image_prompt,
                }
                image_path = generate_image_for_beat(
                    beat_data, job_id, topic_id, str(images_dir)
                )

                if not image_path:
                    print(f"    -> ERROR: Image generation failed")
                    results["failed"].append(
                        {"segment_id": seg_id, "reason": "image generation failed"}
                    )
                    continue

                spec["image_path"] = f"images/{Path(image_path).name}"

                # Step 2: Generate video from image
                duration = spec.get("segment_duration_seconds", 15)
                video_output = str(Path(output_dir) / f"topic_{topic_id}_{seg_id}.mp4")

                client = LtxClient()
                video_path = client.generate_video_from_image(
                    prompt=video_prompt,
                    image_path=image_path,
                    output_path=video_output,
                    duration=duration,
                )

                if video_path:
                    spec["video_path"] = f"videos/{Path(video_path).name}"
                    print(f"    -> SUCCESS: {video_path}")
                    results["success"].append(
                        {"segment_id": seg_id, "video_path": video_path}
                    )
                else:
                    results["failed"].append(
                        {"segment_id": seg_id, "reason": "video generation failed"}
                    )

            elif renderer == "infographic":
                # Infographic: Generate static image only
                image_prompt = spec.get("image_prompt", "")

                if not image_prompt:
                    print(f"    -> ERROR: No image_prompt")
                    results["failed"].append(
                        {"segment_id": seg_id, "reason": "no image_prompt"}
                    )
                    continue

                if dry_run:
                    print(f"    -> DRY RUN: Would generate infographic")
                    continue

                beat_data = {
                    "beat_id": seg_id,
                    "image_prompt": image_prompt,
                }
                image_path = generate_image_for_beat(
                    beat_data, job_id, topic_id, str(images_dir)
                )

                if image_path:
                    spec["image_path"] = f"images/{Path(image_path).name}"
                    print(f"    -> SUCCESS: {image_path}")
                    results["success"].append(
                        {"segment_id": seg_id, "image_path": image_path}
                    )
                else:
                    results["failed"].append(
                        {"segment_id": seg_id, "reason": "image generation failed"}
                    )

            elif renderer == "image":
                # Source image: Use existing image
                image_source = spec.get("image_source", "")
                if image_source:
                    spec["image_path"] = image_source
                    print(f"    -> Using source image: {image_source}")
                    results["success"].append(
                        {"segment_id": seg_id, "image_source": image_source}
                    )
                else:
                    print(f"    -> ERROR: No image_source")
                    results["failed"].append(
                        {"segment_id": seg_id, "reason": "no image_source"}
                    )

            elif renderer == "manim":
                # Manim: Mark as pending for separate rendering pass
                manim_spec = spec.get("manim_scene_spec", "")
                if not manim_spec:
                    print(f"    -> ERROR: No manim_scene_spec")
                    results["failed"].append(
                        {"segment_id": seg_id, "reason": "no manim_scene_spec"}
                    )
                else:
                    # Mark as pending for manim render pass
                    spec["status"] = "pending_manim_render"
                    print(f"    -> PENDING: Manim render queued")
                    results["success"].append(
                        {"segment_id": seg_id, "status": "pending_manim_render"}
                    )

            else:
                print(f"    -> UNKNOWN renderer: {renderer}")
                results["skipped"].append(
                    {"segment_id": seg_id, "reason": f"unknown renderer: {renderer}"}
                )

        except Exception as e:
            print(f"    -> ERROR: {e}")
            results["failed"].append({"segment_id": seg_id, "error": str(e)})

    print(
        f"[PROCESS INDIVIDUAL] Section {topic_id} complete: {len(results['success'])} success, {len(results['failed'])} failed, {len(results['skipped'])} skipped"
    )

    return {
        "topic_id": topic_id,
        "renderer": "mixed",
        "status": "completed",
        "results": results,
    }


def submit_v3_segment_background_job(
    presentation: dict,
    job_id: str,
    output_dir: str,
    dry_run: bool = False,
) -> dict:
    """
    V3 Visual Pipeline - Generate all visual assets for content sections.

    Implements 6 fixes from VISUAL-001:
    1. Section filter checks segment_specs existence
    2. image renderer handling
    3. explanation_visual processing from quizzes
    4. Parallel Gemini image generation
    5. Update visual_beats with generated paths
    6. Batch LTX video generation (3 concurrent)

    Args:
        presentation: Full presentation JSON
        job_id: Job identifier
        output_dir: Path to job output directory
        dry_run: If True, skip actual generation

    Returns:
        Summary dict with success/failed/skipped counts
    """
    import shutil
    from render.image.image_generator import generate_image_for_beat
    from render.ltx.ltx_client import LtxClient

    output_path = Path(output_dir)
    images_dir = output_path / "images"
    videos_dir = output_path / "videos"
    images_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    results = {"success": 0, "failed": 0, "skipped": 0, "details": []}

    sections = presentation.get("sections", [])
    if not sections:
        print("[V3 BG] No sections found in presentation")
        return results

    segments_by_renderer = {
        "text_to_video": [],
        "image_to_video": [],
        "infographic": [],
        "manim": [],
        "image": [],
    }

    for section in sections:
        section_id = section.get("section_id")
        section_type = section.get("section_type", "")

        if section_type in ("intro", "summary", "memory"):
            continue

        segment_specs = (section.get("render_spec") or {}).get("segment_specs", [])

        for spec in segment_specs:
            renderer = spec.get("renderer", "")
            if renderer in segments_by_renderer:
                spec["_section_id"] = section_id
                segments_by_renderer[renderer].append(spec)

        # 3. explanation_visual processing from quizzes
        quiz_sources = []
        quiz = section.get("understanding_quiz", {})
        if quiz:
            quiz_sources.append(("explanation", quiz))
            # Also check nested questions in quiz
            for qi, q in enumerate(quiz.get("questions", [])):
                quiz_sources.append((f"q{qi + 1}_explanation", q))

        # Also check section level questions (sometimes Director puts them there)
        for qi, q in enumerate(section.get("questions", [])):
            quiz_sources.append((f"sec_q{qi + 1}_explanation", q))

        for suffix, source in quiz_sources:
            exp = source.get("explanation_visual", {})
            if not exp or not isinstance(exp, dict):
                continue

            renderer = exp.get("renderer", "")
            if renderer not in segments_by_renderer:
                continue

            # Handle multi-beat explanation visuals by flattening them for the queue
            # (image_to_video_beats, video_prompts, etc.)
            sub_beats = (
                exp.get("image_to_video_beats")
                or exp.get("video_prompts")
                or exp.get("manim_beats")
                or []
            )

            if sub_beats and isinstance(sub_beats, list):
                for bi, beat in enumerate(sub_beats):
                    # Create a flattened spec for the background job
                    flat_spec = beat.copy()
                    flat_spec["_section_id"] = section_id
                    flat_spec["segment_id"] = f"quiz_{section_id}_{suffix}_b{bi + 1}"
                    flat_spec["renderer"] = renderer
                    # Map duration keys
                    if (
                        "duration" in flat_spec
                        and "segment_duration_seconds" not in flat_spec
                    ):
                        flat_spec["segment_duration_seconds"] = flat_spec["duration"]
                    elif (
                        "duration_seconds" in flat_spec
                        and "segment_duration_seconds" not in flat_spec
                    ):
                        flat_spec["segment_duration_seconds"] = flat_spec[
                            "duration_seconds"
                        ]

                    segments_by_renderer[renderer].append(flat_spec)

                    # Ensure image_prompt is set for the background task if using dual prompts
                    if (
                        "image_prompt_start" in flat_spec
                        and "image_prompt" not in flat_spec
                    ):
                        flat_spec["image_prompt"] = flat_spec["image_prompt_start"]
            else:
                # Single beat explanation visual
                exp["_section_id"] = section_id
                exp["segment_id"] = f"quiz_{section_id}_{suffix}"
                # Map duration keys
                if "duration_seconds" in exp and "segment_duration_seconds" not in exp:
                    exp["segment_duration_seconds"] = exp["duration_seconds"]

                # Ensure image_prompt is set
                if "image_prompt_start" in exp and "image_prompt" not in exp:
                    exp["image_prompt"] = exp["image_prompt_start"]

                segments_by_renderer[renderer].append(exp)

    for renderer, specs in segments_by_renderer.items():
        if specs:
            print(f"[V3 BG] {renderer}: {len(specs)} segments")

    for spec in segments_by_renderer["image"]:
        source = spec.get("image_source")
        seg_id = spec.get("segment_id", "unknown")
        if source:
            source_path = Path(source)
            if source_path.exists():
                dest = images_dir / f"topic_{spec['_section_id']}_{seg_id}.png"
                shutil.copy(source_path, dest)
                spec["image_path"] = f"images/{dest.name}"
                results["success"] += 1
                print(f"[V3 BG] image: Copied {source} -> {dest}")
            else:
                results["failed"] += 1
                print(f"[V3 BG] image: Source not found {source}")
        else:
            results["skipped"] += 1
            print(f"[V3 BG] image: No image_source for {seg_id}")

    def generate_image_task(spec):
        seg_id = spec.get("segment_id", "unknown")
        section_id = spec.get("_section_id", "unknown")
        image_prompt = spec.get("image_prompt", "")
        if not image_prompt:
            return seg_id, None
        beat_data = {"beat_id": seg_id, "image_prompt": image_prompt}
        image_path = generate_image_for_beat(
            beat_data, job_id, section_id, str(images_dir)
        )
        return seg_id, image_path

    image_specs = (
        segments_by_renderer["infographic"] + segments_by_renderer["image_to_video"]
    )
    image_promises = {}

    if image_specs and not dry_run:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(generate_image_task, spec) for spec in image_specs
            ]
            for future in concurrent.futures.as_completed(futures):
                seg_id, image_path = future.result()
                if image_path:
                    image_promises[seg_id] = image_path

    for seg_id, image_path in image_promises.items():
        for spec in image_specs:
            if spec.get("segment_id") == seg_id:
                spec["image_path"] = f"images/{Path(image_path).name}"
                results["success"] += 1
                print(f"[V3 BG] Gemini: {seg_id} -> {image_path}")

    def generate_video_task(spec, image_path=None):
        seg_id = spec.get("segment_id", "unknown")
        section_id = spec.get("_section_id", "unknown")
        video_prompt = spec.get("video_prompt", "")
        duration = spec.get("segment_duration_seconds", 15)
        video_output = str(videos_dir / f"topic_{section_id}_{seg_id}.mp4")

        client = LtxClient()
        if image_path:
            video_path = client.generate_video_from_image(
                prompt=video_prompt,
                image_path=image_path,
                output_path=video_output,
                duration=duration,
            )
        else:
            video_path = client.generate_video(
                prompt=video_prompt,
                duration=int(duration),
                output_path=video_output,
            )
        return seg_id, video_path

    video_tasks = []
    for spec in segments_by_renderer["text_to_video"]:
        video_tasks.append((spec, None))

    for spec in segments_by_renderer["image_to_video"]:
        seg_id = spec.get("segment_id", "unknown")
        image_path = image_promises.get(seg_id)
        if image_path:
            video_tasks.append((spec, image_path))

    if video_tasks and not dry_run:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(generate_video_task, spec, img_path)
                for spec, img_path in video_tasks
            ]
            for future in concurrent.futures.as_completed(futures):
                seg_id, video_path = future.result()
                if video_path:
                    for spec, _ in video_tasks:
                        if spec.get("segment_id") == seg_id:
                            spec["video_path"] = f"videos/{Path(video_path).name}"
                            break
                    results["success"] += 1
                    print(f"[V3 BG] LTX: {seg_id} -> {video_path}")
                else:
                    results["failed"] += 1
                    print(f"[V3 BG] LTX: {seg_id} FAILED")

    for spec in segments_by_renderer["manim"]:
        seg_id = spec.get("segment_id", "unknown")
        spec["status"] = "pending_manim_render"
        results["skipped"] += 1
        print(f"[V3 BG] Manim: {seg_id} -> queued for separate render pass")

    for section in sections:
        beats = section.get("visual_beats", [])
        specs = section.get("render_spec", {}).get("segment_specs", [])
        spec_lookup = {s.get("segment_id"): s for s in specs}

        for beat in beats:
            seg_id = beat.get("segment_id")
            spec = spec_lookup.get(seg_id)
            if not spec:
                continue
            if spec.get("video_path"):
                beat["video_path"] = spec["video_path"]
            if spec.get("image_path"):
                beat["image_path"] = spec["image_path"]

    print(
        f"[V3 BG] Complete: {results['success']} success, {results['failed']} failed, {results['skipped']} skipped"
    )
    return results

"""
WAN Video Runner - Generates videos from visual beats using Kie.ai API

CRITICAL: Each visual beat becomes a separate video segment.
NO fallback to generic prompts - fail if visual beats are missing.

ISS-076 FIX: Production runs now validate 300+ word prompts before API calls.
"""
from pathlib import Path
from typing import List
from .wan_client import WANClient
from render.render_trace import log_render_prompt
from core.wan_prompt_validator import hard_fail_on_short_prompts, WanPromptHardFailError, truncate_video_prompts, truncate_wan_prompt, expand_video_prompts


class WanRenderError(Exception):
    """Raised when WAN rendering fails and no fallback is allowed."""
    pass


def reset_wan_session():
    """Reset WAN client hash cache at start of each job to prevent cross-job duplicate detection."""
    WANClient.reset_hash_cache()


def _select_video_client(use_local_gpu: bool, dry_run: bool, skip_wan: bool):
    """
    Return the appropriate video client for recap sections.

    use_local_gpu=True  → LocalGPUClient (falls back to WANClient if unavailable)
    use_local_gpu=False → WANClient (biology/anatomy subjects)
    dry_run / skip_wan  → None (no real API calls needed)
    """
    if dry_run or skip_wan:
        return None
    if use_local_gpu:
        try:
            from render.wan.local_gpu_client import LocalGPUClient
            client = LocalGPUClient()
            if client.is_available():
                print("[ROUTER] Recap → Local GPU client selected")
                return client
            print("[ROUTER] Local GPU unavailable — falling back to Kie.ai WAN for recap")
        except Exception as e:
            print(f"[ROUTER] LocalGPUClient import error: {e} — falling back to WAN")
    print("[ROUTER] Recap → Kie.ai WAN client selected")
    return WANClient()


def render_wan_video(topic: dict, output_dir: str, dry_run: bool = False, skip_wan: bool = False, trace_output_dir: str = None) -> str:
    """
    Render WAN video for a section.
    
    For content/example sections with visual_beats:
      - Each beat becomes a separate video segment
      - Returns path to first video (others follow naming pattern)
      
    For intro/summary/memory/recap sections:
      - Uses section-level wan_prompt if provided
      - Fails if no prompt available (no fallback to generic)
    """
    topic_id = topic.get("section_id", topic.get("id", 1))
    topic_title = topic.get("title", "Untitled")
    section_type = topic.get("section_type", "content")
    explanation_plan = topic.get("explanation_plan", {})
    visual_beats = topic.get("visual_beats", [])
    duration = topic.get("duration", 30)
    
    # Check for compiled WAN prompt from visual_compiler
    compiled_wan_prompt = explanation_plan.get("compiled_wan_prompt")
    
    # ISS-084 FIX: Check for video_prompts at section level first (where llm_client stores them),
    # then fall back to explanation_plan (legacy ISS-067 location)
    video_prompts = topic.get("video_prompts", []) or explanation_plan.get("video_prompts", [])
    
    # For content/example sections, use visual beats (or pre-compiled video_prompts)
    if section_type in ["content", "example"] and (visual_beats or video_prompts):
        # ISS-200: Return all paths for content sections so each segment can find its video
        recap_result = _render_visual_beats(
            topic_id=topic_id,
            topic_title=topic_title,
            section_type=section_type,
            visual_beats=visual_beats,
            output_dir=output_dir,
            dry_run=dry_run,
            skip_wan=skip_wan,
            trace_output_dir=trace_output_dir,
            duration=duration,
            video_prompts=video_prompts,
            return_all_paths=True
        )
        # Store all paths on the topic for reconciliation (like recap does)
        topic["_beat_video_paths"] = recap_result.get("all_paths", [])
        return recap_result.get("first_path")
    
    # For recap sections: pick the right video client based on use_local_gpu flag.
    # use_local_gpu is set by merge_step.py based on subject (biology/anatomy → WAN, else → Local GPU).
    use_local_gpu = topic.get("use_local_gpu", True)
    video_client = _select_video_client(use_local_gpu, dry_run, skip_wan)

    # For recap sections, render each recap_scene as a separate video
    recap_scenes = topic.get("recap_scenes", [])
    if section_type == "recap" and recap_scenes:
        # ISS-092 FIX: _render_recap_scenes now returns dict with all paths
        recap_result = _render_recap_scenes(
            topic_id=topic_id,
            topic_title=topic_title,
            recap_scenes=recap_scenes,
            output_dir=output_dir,
            dry_run=dry_run,
            skip_wan=skip_wan,
            trace_output_dir=trace_output_dir,
            video_client=video_client
        )
        # Store all paths on the topic for reconciliation
        topic["_recap_video_paths"] = recap_result.get("all_paths", [])
        return recap_result.get("first_path")
    
    # ISS-161 FIX: Handle recap sections with video_prompts (not recap_scenes)
    # RecapAgent outputs video_prompts as list of 5 beat dicts, each with ~700 char prompt
    # ISS-199 FIX: Use narration segment durations for WAN videos (capped at 15 sec for WAN 2.6)
    # ISS-200 FIX: Set _recap_video_paths so player can sequence through all 5 videos
    if section_type == "recap" and video_prompts and len(video_prompts) > 0:
        print(f"[ROUTER] ISS-161: Recap section {topic_id} has {len(video_prompts)} video_prompts — {'Local GPU' if use_local_gpu else 'Kie.ai WAN'}")
        
        # Get narration segment durations to sync video length with narration
        narration = topic.get("narration", {})
        segments = narration.get("segments", [])
        
        # Override video_prompt durations with narration durations (capped at 15 for WAN 2.6)
        for i, vp in enumerate(video_prompts):
            if i < len(segments):
                narration_duration = segments[i].get("duration_seconds", 8)
                # Cap at 15 seconds (WAN 2.6 max), minimum 5 seconds
                capped_duration = max(5, min(15, int(narration_duration)))
                original = vp.get("duration_seconds", 8)
                vp["duration_seconds"] = capped_duration
                print(f"  [Beat {i}] Narration: {narration_duration:.1f}s -> Video: {capped_duration}s (was {original}s)")
        
        # ISS-200 FIX: Use return_all_paths to get actual generated paths (handles dry_run correctly)
        recap_result = _render_visual_beats(
            topic_id=topic_id,
            topic_title=topic_title,
            section_type=section_type,
            visual_beats=[],  # No visual_beats for recap
            output_dir=output_dir,
            dry_run=dry_run,
            skip_wan=skip_wan,
            trace_output_dir=trace_output_dir,
            duration=duration,
            video_prompts=video_prompts,
            return_all_paths=True,  # ISS-200: Get all paths for recap sequencing
            video_client=video_client
        )
        
        # Store all paths on the topic for reconciliation (same as recap_scenes path)
        topic["_recap_video_paths"] = recap_result.get("all_paths", [])
        print(f"[WAN] ISS-200: Set {len(topic['_recap_video_paths'])} recap video paths for player sequencing")
        
        return recap_result.get("first_path")
    
    # For other section types, use section-level prompt
    wan_prompt = explanation_plan.get("wan_prompt")
    
    if not wan_prompt and not compiled_wan_prompt:
        raise WanRenderError(
            f"Section {topic_id} ({section_type}): No WAN prompt available. "
            f"Content/example sections must have visual_beats. "
            f"Other sections need explicit wan_prompt in explanation_plan."
        )
    
    # Use compiled prompt if available, else section-level
    prompt = compiled_wan_prompt or wan_prompt
    
    output_path = str(Path(output_dir) / f"topic_{topic_id}.mp4")
    
    log_render_prompt(
        section_id=topic_id,
        section_title=topic_title,
        renderer="wan",
        prompt=prompt,
        output_path=output_path,
        extra_data={
            "section_type": section_type,
            "duration": duration, 
            "dry_run": dry_run, 
            "skip_wan": skip_wan,
            "source": "section_level"
        },
        trace_output_dir=trace_output_dir
    )
    
    if dry_run:
        print(f"[DRY RUN] WAN video for section {topic_id}")
        return _create_dry_run_placeholder(topic_id, output_path, duration)
    
    if skip_wan:
        print(f"[SKIP WAN] Placeholder for section {topic_id}")
        return _create_placeholder_video(topic_id, topic_title, output_path, duration)
    
    # ISS-158 FIX: Truncate section-level prompt BEFORE validation
    prompt = truncate_wan_prompt(prompt)
    
    # Auto-expand short prompts before validation
    from core.wan_prompt_validator import expand_short_prompt
    prompt = expand_short_prompt(prompt)
    
    # ISS-076 FIX: Validate section-level prompt before API call
    try:
        hard_fail_on_short_prompts([{"prompt": prompt}], topic_id)
    except WanPromptHardFailError as e:
        raise WanRenderError(f"Section-level WAN prompt validation failed: {e}")
    
    client = WANClient()
    result_path = client.generate_video(
        prompt=prompt,
        duration=min(duration, 60),
        output_path=output_path
    )

    # FIX: Return None if generation failed (no placeholder)
    if result_path is None:
        print(f"[WAN] Section {topic_id} video generation failed - no placeholder created")
    return result_path


def _render_visual_beats(
    topic_id: int,
    topic_title: str,
    section_type: str,
    visual_beats: list,
    output_dir: str,
    dry_run: bool,
    skip_wan: bool,
    trace_output_dir: str,
    duration: int,
    video_prompts: list = None,
    return_all_paths: bool = False,
    **kwargs
):
    """
    Render each visual beat as a separate video segment.
    
    Returns path to first video segment (default), or dict with all paths if return_all_paths=True.
    Creates: topic_{id}_beat_{0..n}.mp4
    
    ISS-067 FIX: If video_prompts are provided (pre-compiled by LLM),
    use them directly instead of calling visual_compiler.
    
    ISS-200 FIX: Added return_all_paths option to return {"first_path": str, "all_paths": list}
    for recap sections that need all video paths for sequential playback.
    """
    from core.visual_compiler import compile_wan_prompt, VisualCompilationError
    
    if not visual_beats and not video_prompts:
        raise WanRenderError(
            f"Section {topic_id}: {section_type} section has no visual_beats or video_prompts. "
            f"LLM must generate visual beats for content/example sections."
        )
    
    # ISS-067: Check if we have pre-compiled video_prompts
    use_precompiled = video_prompts and len(video_prompts) > 0
    num_beats = len(video_prompts) if use_precompiled else len(visual_beats)
    
    if use_precompiled:
        print(f"[WAN] Using {len(video_prompts)} pre-compiled video_prompts for section {topic_id} (bypassing visual_compiler)")
    else:
        print(f"[WAN] Rendering {len(visual_beats)} visual beats for section {topic_id}")
    
    # ISS-158 FIX: Truncate prompts BEFORE validation (production mode only)
    if not dry_run and not skip_wan and use_precompiled:
        print(f"[DEBUG] video_prompt[0] keys: {video_prompts[0].keys() if isinstance(video_prompts[0], dict) else 'Not a dict'}")
        print(f"[DEBUG] video_prompt[0] raw: {str(video_prompts[0])[:200]}")
        # Helper to safely extract prompt text from various keys
        def _get_p_text(p):
            if isinstance(p, str): return p
            return p.get("prompt") or p.get("wan_prompt") or p.get("text") or p.get("video_prompt") or ""

        original_lengths = [len(_get_p_text(p)) for p in video_prompts]
        print(f"[WAN] video_prompts BEFORE truncation: {original_lengths} chars")
        video_prompts = truncate_video_prompts(video_prompts)
        truncated_lengths = [len(_get_p_text(p)) for p in video_prompts]
        print(f"[WAN] video_prompts AFTER truncation: {truncated_lengths} chars (max 800)")
        
        # Auto-expand short prompts before validation
        video_prompts = expand_video_prompts(video_prompts)
        
        try:
            hard_fail_on_short_prompts(video_prompts, topic_id)
        except WanPromptHardFailError as e:
            raise WanRenderError(f"WAN prompt validation failed: {e}")
    
    default_beat_duration = max(5, duration // num_beats)
    video_paths = []
    # Use caller-supplied client if provided (recap routing), else default to WANClient
    client = kwargs.get("video_client") if kwargs.get("video_client") else (WANClient() if not skip_wan and not dry_run else None)
    
    for beat_idx in range(num_beats):
        # ISS-067: Use pre-compiled prompts if available, otherwise compile from visual_beats
        if use_precompiled:
            prompt_obj = video_prompts[beat_idx]
            if isinstance(prompt_obj, str):
                wan_prompt = prompt_obj
            else:
                wan_prompt = prompt_obj.get("prompt") or prompt_obj.get("wan_prompt") or prompt_obj.get("text") or prompt_obj.get("video_prompt") or str(prompt_obj)
            
            # V2.5 DOUBLE-RESILIENT FIX: Skip if this is a known garbage fallback prompt 
            # (Ensures old jobs benefit from the fix even without regenerating the plan)
            if wan_prompt.strip() == "Cinematic educational visualization.":
                print(f"  [Beat {beat_idx}] SKIP: Detected garbage fallback prompt for hidden segment.")
                video_paths.append(None)
                continue

            # ISS-199: Use per-prompt duration if available (set by narration sync)
            beat_duration = prompt_obj.get("duration_seconds", default_beat_duration)
            beat = visual_beats[beat_idx] if beat_idx < len(visual_beats) else {}
        else:
            beat = visual_beats[beat_idx]
            beat_duration = default_beat_duration  # Use default for compiled prompts
            # Compile the visual beat into a WAN prompt
            try:
                wan_prompt = compile_wan_prompt(beat, topic_id, beat_idx)
            except VisualCompilationError as e:
                raise WanRenderError(
                    f"Section {topic_id}, Beat {beat_idx}: Visual beat compilation failed. "
                    f"Reason: {e.reason}"
                )
            
            # ISS-158 FIX: Truncate and validate compiled prompt (production only)
            if not dry_run and not skip_wan:
                original_len = len(wan_prompt)
                wan_prompt = truncate_wan_prompt(wan_prompt)
                print(f"[WAN] Beat {beat_idx} compiled prompt: {original_len} -> {len(wan_prompt)} chars")
                word_count = len(wan_prompt.split()) if wan_prompt else 0
                if word_count < 80:
                    raise WanRenderError(
                        f"Section {topic_id}, Beat {beat_idx}: Compiled WAN prompt has {word_count} words, "
                        f"v1.5 REQUIRES 80+ words. Prompt preview: '{wan_prompt[:80]}...'"
                    )
        
        # Generate output path for this beat
        beat_output_path = str(Path(output_dir) / f"topic_{topic_id}_beat_{beat_idx}.mp4")
        
        # Log the compiled prompt
        log_render_prompt(
            section_id=topic_id,
            section_title=f"{topic_title} - Beat {beat_idx}",
            renderer="wan_beat",
            prompt=wan_prompt,
            output_path=beat_output_path,
            extra_data={
                "section_type": section_type,
                "beat_index": beat_idx,
                "beat_total": len(visual_beats),
                "duration": beat_duration,
                "dry_run": dry_run,
                "skip_wan": skip_wan,
                "visual_beat_fields": list(beat.keys())
            },
            trace_output_dir=trace_output_dir
        )
        
        print(f"  [Beat {beat_idx}] Prompt: {wan_prompt[:80]}...")
        
        if dry_run:
            marker_path = beat_output_path.replace(".mp4", ".dry_run.txt")
            with open(marker_path, "w") as f:
                f.write(f"DRY RUN - Section {topic_id}, Beat {beat_idx}\n")
                f.write(f"Prompt: {wan_prompt}\n")
            video_paths.append(marker_path)
            continue
        
        if skip_wan:
            _create_beat_placeholder(beat_idx, topic_id, beat_output_path, beat_duration)
            video_paths.append(beat_output_path)
            continue
        
        # V2.6 IDEMPOTENT: Skip if valid file already exists (like Avatar)
        beat_file = Path(beat_output_path)
        if beat_file.exists() and beat_file.stat().st_size > 10000:
            print(f"  [Beat {beat_idx}] SKIP: Valid file exists ({beat_file.stat().st_size // 1024}KB)")
            video_paths.append(beat_output_path)
            continue
        
        # Generate actual video
        result_path = client.generate_video(
            prompt=wan_prompt,
            duration=beat_duration,
            output_path=beat_output_path
        )
        # FIX: Handle None (failed) - append None to track failure, no placeholder
        if result_path is None:
            print(f"  [Beat {beat_idx}] FAILED: Video generation failed - no placeholder")
        video_paths.append(result_path)

    # Count successful vs failed
    successful = sum(1 for p in video_paths if p is not None)
    failed = len(video_paths) - successful
    print(f"[WAN] Completed {successful}/{len(video_paths)} beat videos for section {topic_id} ({failed} failed)")
    
    # ISS-200 FIX: Optionally return all paths for recap sequencing
    if return_all_paths:
        return {
            "first_path": video_paths[0] if video_paths else None,
            "all_paths": video_paths
        }
    
    # Return path to first beat (player will handle stitching or sequencing)
    return video_paths[0] if video_paths else None


def _render_recap_scenes(
    topic_id: int,
    topic_title: str,
    recap_scenes: list,
    output_dir: str,
    dry_run: bool,
    skip_wan: bool,
    trace_output_dir: str,
    video_client=None
) -> dict:
    """
    Render each recap scene as a separate WAN video.
    
    Recap sections have exactly 5 scenes, each covering one key concept.
    Each scene has: concept_title, description, wan_prompt, narration
    
    Creates: recap_{topic_id}_scene_{1..5}.mp4
    
    ISS-092 FIX: Returns dict with first_path and all_paths for player sequencing.
    Returns: {"first_path": str, "all_paths": [str, str, str, str, str]}
    """
    if not recap_scenes:
        raise WanRenderError(
            f"Section {topic_id}: Recap section has no recap_scenes. "
            f"LLM must generate exactly 5 recap scenes."
        )
    
    if len(recap_scenes) != 5:
        print(f"[WARN] Section {topic_id}: Expected 5 recap scenes, got {len(recap_scenes)}")
    
    print(f"[WAN] Rendering {len(recap_scenes)} recap scenes for section {topic_id}")
    
    # ISS-158 FIX: Truncate THEN validate recap prompts before API calls (production mode only)
    if not dry_run and not skip_wan:
        recap_prompts = [{"prompt": scene.get("wan_prompt", "")} for scene in recap_scenes]
        # Log original lengths for debugging
        original_lengths = [len(p.get("prompt", "")) for p in recap_prompts]
        print(f"[WAN] Recap prompts BEFORE truncation: {original_lengths} chars")
        # Truncate first - this was missing and caused 2901 char failures
        recap_prompts = truncate_video_prompts(recap_prompts)
        # Log truncated lengths
        truncated_lengths = [len(p.get("prompt", "")) for p in recap_prompts]
        print(f"[WAN] Recap prompts AFTER truncation: {truncated_lengths} chars (max 800)")
        # Update original scenes with truncated prompts
        for i, scene in enumerate(recap_scenes):
            if i < len(recap_prompts):
                scene["wan_prompt"] = recap_prompts[i].get("prompt", scene.get("wan_prompt", ""))
        
        # Auto-expand short prompts before validation
        recap_prompts = expand_video_prompts(recap_prompts)
        
        try:
            hard_fail_on_short_prompts(recap_prompts, topic_id)
        except WanPromptHardFailError as e:
            raise WanRenderError(f"Recap prompt validation failed: {e}")
    
    video_paths = []
    # Use caller-supplied client (for smart routing), else default to WANClient
    client = video_client if video_client else (WANClient() if not skip_wan and not dry_run else None)
    scene_duration = 5  # Each recap scene is 5 seconds
    
    for scene_idx, scene in enumerate(recap_scenes):
        scene_num = scene.get("scene", scene_idx + 1)
        concept_title = scene.get("concept_title", f"Concept {scene_num}")
        wan_prompt = scene.get("wan_prompt", "")
        
        if not wan_prompt:
            raise WanRenderError(
                f"Section {topic_id}, Recap Scene {scene_num}: Missing wan_prompt. "
                f"Each recap scene must have a wan_prompt for video generation."
            )
        
        # Generate output path for this scene
        scene_output_path = str(Path(output_dir) / f"recap_{topic_id}_scene_{scene_num}.mp4")
        
        # Log the prompt
        log_render_prompt(
            section_id=topic_id,
            section_title=f"{topic_title} - Recap Scene {scene_num}: {concept_title}",
            renderer="wan_recap",
            prompt=wan_prompt,
            output_path=scene_output_path,
            extra_data={
                "section_type": "recap",
                "scene_number": scene_num,
                "scene_total": len(recap_scenes),
                "concept_title": concept_title,
                "duration": scene_duration,
                "dry_run": dry_run,
                "skip_wan": skip_wan
            },
            trace_output_dir=trace_output_dir
        )
        
        print(f"  [Recap Scene {scene_num}] {concept_title}: {wan_prompt[:60]}...")
        
        if dry_run:
            marker_path = scene_output_path.replace(".mp4", ".dry_run.txt")
            with open(marker_path, "w") as f:
                f.write(f"DRY RUN - Section {topic_id}, Recap Scene {scene_num}\n")
                f.write(f"Concept: {concept_title}\n")
                f.write(f"Prompt: {wan_prompt}\n")
            video_paths.append(marker_path)
            continue
        
        if skip_wan:
            _create_recap_placeholder(scene_num, topic_id, concept_title, scene_output_path, scene_duration)
            video_paths.append(scene_output_path)
            continue
        
        # V2.6 IDEMPOTENT: Skip if valid file already exists (like Avatar)
        scene_file = Path(scene_output_path)
        if scene_file.exists() and scene_file.stat().st_size > 10000:
            print(f"  [Recap Scene {scene_num}] SKIP: Valid file exists ({scene_file.stat().st_size // 1024}KB)")
            video_paths.append(scene_output_path)
            continue
        
        # Generate actual video
        result_path = client.generate_video(
            prompt=wan_prompt,
            duration=scene_duration,
            output_path=scene_output_path
        )
        # FIX: Handle None (failed) - append None to track failure, no placeholder
        if result_path is None:
            print(f"  [Recap Scene {scene_num}] FAILED: Video generation failed - no placeholder")
        video_paths.append(result_path)

    # Count successful vs failed
    successful = sum(1 for p in video_paths if p is not None)
    failed = len(video_paths) - successful
    print(f"[WAN] Completed {successful}/{len(video_paths)} recap scene videos for section {topic_id} ({failed} failed)")
    
    # ISS-092 FIX: Return all paths for player sequencing
    return {
        "first_path": video_paths[0] if video_paths else None,
        "all_paths": video_paths
    }


def _create_recap_placeholder(scene_num: int, topic_id: int, concept_title: str, output_path: str, duration: int) -> str:
    """Create placeholder video for a recap scene."""
    try:
        from moviepy import ColorClip, TextClip, CompositeVideoClip
        
        # Purple/blue gradient colors for recap scenes
        colors = [(60, 30, 90), (45, 45, 100), (30, 60, 90), (50, 40, 95), (40, 50, 90)]
        color = colors[(scene_num - 1) % len(colors)]
        
        bg = ColorClip(size=(1280, 720), color=color, duration=duration)
        
        try:
            txt = TextClip(
                text=f"Recap {scene_num}: {concept_title[:30]}",
                font_size=36,
                color="white",
                size=(1280, 720)
            )
            txt = txt.with_position("center").with_duration(duration)
            video = CompositeVideoClip([bg, txt])
        except Exception:
            video = bg
        
        video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio=False,
            verbose=False,
            logger=None
        )
        video.close()
        return output_path
        
    except Exception as e:
        print(f"Recap placeholder error: {e}")
        return _create_ffmpeg_placeholder(output_path, duration)


def _create_beat_placeholder(beat_idx: int, topic_id: int, output_path: str, duration: int) -> str:
    """Create placeholder video for a single beat."""
    try:
        try:
            from moviepy import ColorClip
        except ImportError:
            from moviepy.editor import ColorClip
        
        # Different colors for different beats to show they're separate
        colors = [(30, 60, 90), (60, 30, 90), (90, 60, 30), (30, 90, 60), (60, 90, 30)]
        color = colors[beat_idx % len(colors)]
        
        bg = ColorClip(size=(1280, 720), color=color, duration=min(duration, 8))
        bg.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio=False,
            verbose=False,
            logger=None
        )
        bg.close()
        return output_path
        
    except Exception as e:
        print(f"Beat placeholder error: {e}")
        return _create_ffmpeg_placeholder(output_path, duration)


def _create_ffmpeg_placeholder(output_path: str, duration: int) -> str:
    """Fallback placeholder using ffmpeg."""
    import subprocess
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c=0x1e3c5a:s=1280x720:d={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        output_path
    ]
    subprocess.run(cmd, capture_output=True)
    return output_path


def _create_dry_run_placeholder(topic_id: int, output_path: str, duration: int) -> str:
    """Create a marker file for dry run mode."""
    marker_path = output_path.replace(".mp4", ".dry_run.txt")
    with open(marker_path, "w") as f:
        f.write(f"DRY RUN placeholder for topic {topic_id}\n")
        f.write(f"Duration: {duration}s\n")
        f.write(f"Output would be: {output_path}\n")
    print(f"[DRY RUN] Created marker: {marker_path}")
    return marker_path


def _create_placeholder_video(topic_id: int, topic_title: str, output_path: str, duration: int) -> str:
    """Create placeholder video when skip_wan is enabled."""
    try:
        from moviepy import ColorClip, TextClip, CompositeVideoClip
        
        bg = ColorClip(size=(1280, 720), color=(30, 60, 90), duration=min(duration, 10))
        
        try:
            txt = TextClip(
                text=f"Section {topic_id}: {topic_title[:40]}",
                font_size=36,
                color="white",
                size=(1280, 720)
            )
            txt = txt.with_position("center").with_duration(min(duration, 10))
            video = CompositeVideoClip([bg, txt])
        except Exception:
            video = bg
        
        video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio=False,
            verbose=False,
            logger=None
        )
        video.close()
        return output_path
        
    except Exception as e:
        print(f"Placeholder error: {e}")
        return _create_ffmpeg_placeholder(output_path, duration)


def render_from_video_prompts(
    section: dict,
    output_dir: str,
    dry_run: bool = False,
    skip_wan: bool = False
) -> list:
    """
    Render videos from pre-generated video_prompts (from LLM).
    
    This bypasses visual_beat compilation since video_prompts already contain
    the full prompt text ready for WAN generation.
    
    Args:
        section: Section dict with video_prompts array
        output_dir: Directory to save generated videos
        dry_run: If True, only create marker files
        skip_wan: If True, create placeholder videos instead of calling API
        
    Returns:
        List of paths to generated video files
    """
    section_id = section.get("section_id") or section.get("id", 1)
    section_type = section.get("section_type", "content")
    video_prompts = section.get("video_prompts", [])
    
    if not video_prompts:
        raise WanRenderError(f"Section {section_id}: No video_prompts available")
    
    print(f"[WAN] Rendering {len(video_prompts)} video prompts for section {section_id}")
    
    # ISS-076 FIX: Validate all prompts before any API calls (production only)
    if not dry_run and not skip_wan:
        # Auto-expand short prompts before validation
        video_prompts = expand_video_prompts(video_prompts)
        
        try:
            hard_fail_on_short_prompts(video_prompts, section_id)
        except WanPromptHardFailError as e:
            raise WanRenderError(f"Video prompts validation failed: {e}")
    
    from pathlib import Path
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    client = WANClient() if not skip_wan and not dry_run else None
    video_paths = []
    
    for i, vp in enumerate(video_prompts):
        # Extract text from dict if needed
        if isinstance(vp, str):
            prompt = vp
        else:
            prompt = vp.get("prompt") or vp.get("wan_prompt") or vp.get("text") or vp.get("video_prompt") or ""
        duration = vp.get("duration_seconds", 8)
        beat_id = vp.get("beat_id", f"{section_id}_{i}")
        
        if not prompt:
            print(f"  [Beat {i}] SKIP: Empty prompt")
            continue
        
        if section_type == "recap":
            video_file = output_path / f"recap_{section_id}_scene_{i+1}.mp4"
        else:
            video_file = output_path / f"topic_{section_id}_beat_{i}.mp4"
        
        print(f"  [Beat {beat_id}] {len(prompt.split())} words, {duration}s")
        print(f"    Preview: {prompt[:80]}...")
        
        if dry_run:
            marker_path = str(video_file).replace(".mp4", ".dry_run.txt")
            with open(marker_path, "w") as f:
                f.write(f"DRY RUN - Section {section_id}, Beat {i}\n")
                f.write(f"Prompt: {prompt}\n")
            video_paths.append(marker_path)
            continue
        
        if skip_wan:
            _create_beat_placeholder(i, section_id, str(video_file), duration)
            video_paths.append(str(video_file))
            continue
        
        try:
            result_path = client.generate_video(
                prompt=prompt,
                duration=min(duration, 10),
                output_path=str(video_file)
            )
            # FIX: Handle None (failed) - no placeholder creation
            if result_path is None:
                print(f"  [Beat {beat_id}] FAILED: Video generation failed - no placeholder")
            video_paths.append(result_path)
        except Exception as e:
            # FIX: Don't create placeholder on error - just log and append None
            print(f"  [Beat {beat_id}] ERROR: {e} - no placeholder created")
            video_paths.append(None)

    # Count successful vs failed
    successful = sum(1 for p in video_paths if p is not None)
    failed = len(video_paths) - successful
    print(f"[WAN] Completed {successful}/{len(video_paths)} videos for section {section_id} ({failed} failed)")
    
    if video_paths and section_type != "recap":
        combined_path = output_path / f"topic_{section_id}.mp4"
        if len(video_paths) == 1:
            import shutil
            shutil.copy(video_paths[0], str(combined_path))
        else:
            _stitch_beat_videos(video_paths, str(combined_path))
        return [str(combined_path)] + video_paths
    
    return video_paths


def _stitch_beat_videos(video_paths: list, output_path: str) -> str:
    """Stitch multiple beat videos into a single video."""
    try:
        try:
            from moviepy import VideoFileClip, concatenate_videoclips
        except ImportError:
            from moviepy.editor import VideoFileClip, concatenate_videoclips
        
        clips = []
        for vp in video_paths:
            if vp and vp.endswith('.mp4') and Path(vp).exists():
                clips.append(VideoFileClip(vp))
        
        if clips:
            final = concatenate_videoclips(clips)
            final.write_videofile(output_path, fps=24, codec="libx264", audio=False, verbose=False, logger=None)
            for c in clips:
                c.close()
            final.close()
            return output_path
    except Exception as e:
        print(f"Stitch error: {e}, returning first video")
    
    if video_paths:
        import shutil
        shutil.copy(video_paths[0], output_path)
    return output_path

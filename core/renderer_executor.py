import os
import json
import logging
import traceback
import concurrent.futures
from pathlib import Path
from core.dry_run_validator import DryRunValidationResult, validate_presentation_dry_run, format_validation_report
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
            print(f"[RENDERER POLICY] WARNING: Section is type {type(section)}, expected dict. Skipping.")
            continue
            
        section_type = section.get("section_type", "content")
        current_renderer = section.get("renderer", "wan_video")
        
        if section_type in TEXT_ONLY_SECTION_TYPES:
            if current_renderer and current_renderer != "none":
                section["renderer"] = "none"
                section["renderer_override_reason"] = f"Section type '{section_type}' is text-only (no video rendering)"
                changes_made += 1
                print(f"[RENDERER POLICY] Section {section.get('id')} ({section_type}): Forced to TEXT-ONLY")
        
        elif section_type == "recap":
            if current_renderer != "video":
                section["renderer"] = "video"
                section["renderer_override_reason"] = "V2.5 Bible: Recap sections strictly use 'video' renderer"
                changes_made += 1
                print(f"[RENDERER POLICY] Section {section.get('id')}: Forced to 'video' (recap)")

        # V3: 'threejs' is a valid renderer for content/example — never override it
        elif current_renderer == "threejs" and section_type in ("content", "example"):
            pass  # Allow Three.js renderer through unchanged
    
    if changes_made > 0:
        print(f"[RENDERER POLICY] Applied {changes_made} renderer overrides")
    
    return presentation


def execute_renderer(topic: dict, output_dir: str, dry_run: bool = False, skip_wan: bool = False, trace_output_dir: str = "", strict_mode: bool = True, video_provider: str = "ltx") -> dict:
    os.makedirs(output_dir, exist_ok=True)
    
    topic_id = topic.get("section_id", topic.get("id", 1))
    renderer = topic.get("renderer", "wan_video")
    section_type = topic.get("section_type", "content")
    visual_beats = topic.get("visual_beats", [])
    
    manim_scene_spec = topic.get("manim_scene_spec") or (topic.get("render_spec") or {}).get("manim_scene_spec")
    video_prompts = topic.get("video_prompts") or (topic.get("render_spec") or {}).get("video_prompts")
    
    is_valid_manim_spec = isinstance(manim_scene_spec, dict) 
    is_valid_wan_spec = bool(video_prompts)
    has_v12_specs = is_valid_manim_spec or is_valid_wan_spec
    
    # V2.5 FIX: Auto-detect renderer if LLM provided content but forgot to set flag
    if renderer == "none" and section_type not in TEXT_ONLY_SECTION_TYPES:
        if video_prompts:
            renderer = "wan_video"
            logger.info(f"[Renderer] Auto-detected WAN content for section {topic_id}. Upgrading renderer to 'wan_video'.")
            print(f"  [{topic_id}] -> Auto-upgraded to WAN (found video_prompts)")
        elif manim_scene_spec:
            renderer = "manim_flow"
            logger.info(f"[Renderer] Auto-detected Manim content for section {topic_id}. Upgrading renderer to 'manim_flow'.")
            print(f"  [{topic_id}] -> Auto-upgraded to Manim (found manim_scene_spec)")

    if renderer == "none" or section_type in TEXT_ONLY_SECTION_TYPES:
        reason = f"Section type '{section_type}' is text-only" if section_type in TEXT_ONLY_SECTION_TYPES else "Renderer explicitly set to 'none'"
        return {
            "topic_id": topic_id,
            "section_type": section_type,
            "renderer": "none",
            "status": "skipped",
            "video_path": None,
            "reason": reason
        }
    
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
        "v12_specs_used": has_v12_specs
    }
    
    if has_v12_specs:
        print(f"[v1.2 MODE] Section {topic_id} has pre-compiled renderer specs - bypassing Visual Compiler")
    
    import time
    render_start = time.time()
    try:
        if renderer == "manim":
            video_path = render_manim_video(topic, output_dir, dry_run=dry_run, trace_output_dir=trace_output_dir)
        elif renderer == "threejs":
            # V3: Generate Three.js .js file instead of rendering a video
            if ThreejsCodeGenerator is None:
                raise ImportError("ThreejsCodeGenerator could not be imported")
            if dry_run:
                print(f"[DRY RUN] Section {topic_id}: Would generate Three.js file (threejs_spec present: {bool(topic.get('threejs_spec'))})")
                return {
                    "topic_id": topic_id, "section_type": section_type,
                    "renderer": "threejs", "status": "skipped",
                    "video_path": None, "reason": "dry_run"
                }
            print(f"[RENDER] Section {topic_id}: Generating Three.js scene")
            gen = ThreejsCodeGenerator()
            js_code, errors = gen.generate(topic)
            if js_code:
                js_path = gen.save_js_file(
                    js_code, output_dir,
                    job_id=str(Path(output_dir).parent.name),
                    topic_id=str(topic_id),
                    beat_idx=0
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
        else:
            # Route based on video_provider
            if video_provider == "ltx":
                if render_ltx_video is None:
                    raise ImportError("LTX runner could not be imported")
                print(f"[RENDER] Section {topic_id}: Using LTX provider")
                video_path = render_ltx_video(topic, output_dir, dry_run=dry_run, skip_wan=skip_wan, trace_output_dir=trace_output_dir)
            else:
                # Default to Kie/WAN
                print(f"[RENDER] Section {topic_id}: Using Kie/WAN provider")
                video_path = render_wan_video(topic, output_dir, dry_run=dry_run, skip_wan=skip_wan, trace_output_dir=trace_output_dir)

        # ISS-093 FIX: Handle different return types from renderers
        # FIX: Also handle None returns (failed generation - no placeholder)
        if isinstance(video_path, list):
            # Filter out None values (failed beats)
            valid_paths = [p for p in video_path if p is not None]
            failed_count = len(video_path) - len(valid_paths)

            if valid_paths:
                result["video_path"] = valid_paths[0]
                result["beat_videos"] = valid_paths
                result["status"] = "success" if failed_count == 0 else "partial"
                if failed_count > 0:
                    result["video_status"] = f"partial_failure_{failed_count}_of_{len(video_path)}_failed"
                print(f"[RENDER] Manim multi-beat: {len(valid_paths)}/{len(video_path)} beat videos for section {topic_id}")
            else:
                result["status"] = "failed"
                result["video_status"] = "generation_failed"
                result["error"] = "All video generations failed"
                print(f"[RENDER] Section {topic_id}: ALL beat videos failed to generate")

        elif isinstance(video_path, dict):
            all_paths = video_path.get("all_paths", [])
            valid_paths = [p for p in all_paths if p is not None]
            failed_count = len(all_paths) - len(valid_paths)

            if valid_paths:
                result["video_path"] = valid_paths[0]
                result["recap_video_paths"] = valid_paths
                result["status"] = "success" if failed_count == 0 else "partial"
                if failed_count > 0:
                    result["video_status"] = f"partial_failure_{failed_count}_of_{len(all_paths)}_failed"
                print(f"[RENDER] WAN recap: {len(valid_paths)}/{len(all_paths)} videos for section {topic_id}")
            else:
                result["status"] = "failed"
                result["video_status"] = "generation_failed"
                result["error"] = "All recap video generations failed"
                print(f"[RENDER] Section {topic_id}: ALL recap videos failed to generate")

        elif video_path is None:
            # Single video failed
            result["status"] = "failed"
            result["video_status"] = "generation_failed"
            result["error"] = "Video generation failed - no video created"
            print(f"[RENDER] Section {topic_id}: Video generation FAILED (no placeholder)")
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
                print(f"[RENDER] Captured {len(valid_beats)} content beat paths for section {topic_id}")
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        print(f"Error rendering topic {topic_id}: {e}")
    
    result["duration_seconds"] = round(time.time() - render_start, 2)
    return result




def validate_before_render(presentation: dict, output_dir: str, strict_v13: bool = True) -> DryRunValidationResult:
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
    result = validate_presentation_dry_run(presentation, output_dir, strict_v13=strict_v13)
    
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


def render_all_topics(presentation: dict, output_dir: str, dry_run: bool = False, skip_wan: bool = False, output_dir_base: str = "", strict_mode: bool = True, renderer_filter: str = None, video_provider: str = "ltx") -> list:
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
            presentation, 
            output_dir, 
            strict_v13=strict_mode
        )
        
        if not validation_result.is_valid:
            print(f"[DRY RUN] VALIDATION FAILED with {len(validation_result.errors)} errors (PROCEEDING AS REQUESTED)")
        else:
            print(f"[DRY RUN] Validation PASSED ({len(validation_result.warnings)} warnings)")
    
    topics = presentation.get("sections", presentation.get("topics", []))
    success_count = 0
    fail_count = 0
    compile_fail_count = 0
    
    mode_label = "[DRY RUN] " if dry_run else ""
    skip_label = "[SKIP WAN] " if skip_wan else ""
    strict_label = "[STRICT] " if strict_mode else ""
    
    logger.info(f"{mode_label}{skip_label}{strict_label}Starting Parallel Render for {len(topics)} topics...")
    
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
                video_provider
            ): i for i, topic in enumerate(topics)
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
                    print(f"  [{topic_id}] -> Skipped: {result.get('reason', 'No video needed')}")
                elif result["status"] == "compilation_failed":
                    compile_fail_count += 1
                    print(f"  [{topic_id}] -> Compilation Failed: {result['error']}")
                else:
                    fail_count += 1
                    print(f"  [{topic_id}] -> Failed: {result.get('error', 'Unknown error')}")
            except Exception as e:
                fail_count += 1
                logger.error(f"  [{topic_id}] -> Execution Critical Error: {e}")
                rendered_videos[idx] = {"status": "failed", "error": str(e), "topic_id": topic_id}
    
    print(f"{mode_label}{skip_label}{strict_label}Rendering complete: {success_count} success, {compile_fail_count} compilation failures, {fail_count} render failures")
    return rendered_videos



def submit_wan_background_job(presentation: dict, output_dir: str, job_id: str, skip_wan: bool = False, skip_avatar: bool = False, video_provider: str = "ltx"):
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
                 job_manager.update_job(job_id, {
                     "status": "processing",
                     "current_step_name": f"Generating Video ({video_provider.upper()})...",
                     "current_phase_key": "video_generation"
                 }, persist=True)
        except: pass
        
        print(f"[BG-JOB] Starting background generation for job {job_id} using {video_provider}")
        
        topics = presentation.get("sections", [])

        # ── Routing: split beats by use_local_gpu flag ─────────────────────────
        # kie_beats  → Kie.ai WAN API (biology/anatomy or use_local_gpu=False)
        # local_beats_by_topic → Local GPU server (general content, use_local_gpu=True)
        kie_beats = []
        local_beats_by_topic = []  # list of (topic, sanitized_beats)
        topic_id_to_beats = {}     # shared: section_id → [beat_ids] for result mapping

        job_output_dir = Path(output_dir).parent
        set_trace_output_dir(str(job_output_dir))

        for topic in topics:
            renderer = topic.get("renderer", "none")
            if renderer not in ["wan", "wan_video", "video"]:
                continue

            beats = topic.get("video_prompts", [])
            if not beats:
                continue

            # Sanitize beats
            sanitized_beats = []
            for b in beats:
                if isinstance(b, str):
                    sanitized_beats.append({"beat_id": f"beat_{len(sanitized_beats)}", "prompt": b})
                elif isinstance(b, dict):
                    sanitized_beats.append(b)

            topic_id_to_beats[topic.get("section_id")] = [b.get("beat_id") for b in sanitized_beats]

            # Log prompts for debugging
            for beat in sanitized_beats:
                log_render_prompt(
                    section_id=topic.get("section_id"),
                    section_title=topic.get("title", "Unknown"),
                    renderer="wan_background",
                    prompt=beat.get("prompt", ""),
                    output_path=str(Path(output_dir) / f"{beat.get('beat_id')}.mp4"),
                    extra_data={"job_id": job_id, "source": "background_retry"}
                )

            # ROUTING DECISION: use_local_gpu field set by Director LLM
            # Default is True (Local GPU) — Director LLM only sets False for biology/anatomy
            use_local = topic.get("use_local_gpu", True)
            if use_local:
                print(f"[ROUTER] Section {topic.get('section_id')} '{topic.get('title','?')}' → Local GPU")
                local_beats_by_topic.append((topic, sanitized_beats))
            else:
                print(f"[ROUTER] Section {topic.get('section_id')} '{topic.get('title','?')}' → Kie.ai WAN (use_local_gpu=False, biology/anatomy)")
                kie_beats.extend(sanitized_beats)

        total_beats = len(kie_beats) + sum(len(b) for _, b in local_beats_by_topic)
        print(f"[BG-JOB] Found {total_beats} total beats: {len(kie_beats)} → Kie.ai, {total_beats - len(kie_beats)} → Local GPU")

        
        if not total_beats:
            logger.info(f"[BG-JOB] No beats found for job {job_id}")
            if skip_avatar:
                try: 
                    from core.job_manager import job_manager
                    if job_manager: job_manager.complete_job(job_id)
                except: pass
            return
            
        if skip_wan:
            logger.info(f"[BG-JOB] Video generation skipped per request")
            if skip_avatar:
                try: 
                    from core.job_manager import job_manager
                    if job_manager: job_manager.complete_job(job_id)
                except: pass
            return

        results = {}  # beat_id → path (merged from all providers)
        all_sanitized_beats = []  # track all beats for final presentation update

        # ── Step A: Local GPU beats ────────────────────────────────────────────
        if local_beats_by_topic:
            local_client = LocalGPUClient()
            gpu_available = local_client.is_available()
            if not gpu_available:
                print(f"[ROUTER] Local GPU unavailable — falling back all local beats to Kie.ai WAN")

            # Collect all individual beats for parallel processing
            all_local_beats = []
            for topic, beats in local_beats_by_topic:
                for beat in beats:
                    all_local_beats.append((topic, beat))

            if gpu_available:
                print(f"[LocalGPU] Processing {len(all_local_beats)} beats in parallel (max_workers=3)")
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    # beat_id -> (future, beat_obj)
                    future_to_beat = {}
                    for topic, beat in all_local_beats:
                        beat_id = beat.get("beat_id", "")
                        prompt = beat.get("prompt") or beat.get("wan_prompt") or ""
                        # V2.6: Use duration_seconds if available (narration sync), else duration_hint
                        duration = int(beat.get("duration_seconds") or beat.get("duration_hint") or 5)
                        out_path = str(Path(output_dir) / f"{beat_id}.mp4")

                        future = executor.submit(local_client.generate_video, prompt, duration=duration, output_path=out_path)
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
                                print(f"[LocalGPU] ✗ Beat {beat_id} failed → falling back to Kie.ai")
                                kie_beats.append(beat)
                        except Exception as e:
                            print(f"[LocalGPU] ✗ Beat {beat_id} execution error: {e} → falling back to Kie.ai")
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
                prompt = beat_obj.get("prompt") or beat_obj.get("wan_prompt") or ""
                beat_id = beat_obj.get("beat_id", f"beat_{i}")
                duration = int(beat_obj.get("duration_seconds") or beat_obj.get("duration_hint") or 5)
                
                # Check if file already exists (resume capability)
                vid_filename = f"ltx_{job_id}_{beat_id}.mp4"
                out_path = Path(output_dir) / vid_filename
                
                if out_path.exists():
                     print(f"[LTX-BG] Skipping existing: {out_path}")
                     results[beat_id] = str(out_path)
                     continue
                     
                try:
                    print(f"[LTX-BG] ▶ Processing beat {i+1}/{len(kie_beats)}: {beat_id} (duration={duration}s)")
                    print(f"[LTX-BG]   Prompt: {prompt[:80]}...")
                    p = client.generate_video(prompt, output_path=str(out_path), duration=duration)
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
                    logger.info(f"[NSFW-FIX] Updated prompt for {beat_id}: '{original_prompt[:40]}...' -> '{sanitized_prompt[:40]}...'")
        
        # 3. Update Files (Shared Logic)
        pres_path = Path(output_dir).parent / "presentation.json"
        
        for topic_id, beat_ids in topic_id_to_beats.items():
            # For each topic, find the corresponding results
            topic_results = {bid: results.get(bid) for bid in beat_ids if bid in results}
            if topic_results:
                # Extract paths for file update (maintain backward compatibility)
                first_result = list(topic_results.values())[0]
                video_path = first_result["path"] if isinstance(first_result, dict) else first_result
                
                _update_presentation_safely(pres_path, topic_id, video_path, {
                    "status": "success", 
                    "beat_video_paths": [r["path"] if isinstance(r, dict) else r for r in topic_results.values()], 
                    "topic_results": topic_results,
                    "wan_beats": all_sanitized_beats  # Pass updated beats with sanitized prompts
                })
                _update_analytics_safely(pres_path.parent / "analytics.json", topic_id, {"status": "success", "duration_seconds": 0}) 
                
        logger.info(f"[BG-JOB] All tasks complete for job {job_id}")
        
        if skip_avatar:
            try: 
                from core.job_manager import job_manager
                if job_manager: 
                    job_manager.complete_job(job_id)
                    print(f"[BG-JOB] Job {job_id} marked as completed (Avatar skipped)")
            except: pass

    except Exception as e:
        logger.error(f"[BG-JOB] Fatal error in background thread: {e}")
        traceback.print_exc()

def _update_presentation_safely(pres_path: Path, section_id: str, video_path: str, result: dict):
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
                    
                    # Handle Recaps/Beats
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
                                b_id = p_obj.get("beat_id") if isinstance(p_obj, dict) else f"beat_{i}"
                                b_path = f"videos/{Path(content_beat_paths[i]).name}"
                                beat_id_to_path[b_id] = b_path
                        
                        # Ensure strict alignment with segments for Player V2 compatibility
                        aligned_paths = []
                        if "narration" in section and "segments" in section["narration"]:
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
                                            resolved_paths.append(bid) # Keep ID if not found
                                    
                                    seg["beat_videos"] = resolved_paths
                                    if resolved_paths and resolved_paths[0].startswith("videos/"):
                                        seg_path = resolved_paths[0]
                                
                                aligned_paths.append(seg_path)
                        
                        # Only apply aligned_paths if at least one path was successfully mapped
                        if aligned_paths and any(p is not None for p in aligned_paths):
                            section["beat_video_paths"] = aligned_paths
                        else:
                            # Fallback to the raw sequential paths (e.g. for recap sections)
                            section["beat_video_paths"] = [f"videos/{Path(p).name}" for p in content_beat_paths]
                        print(f"  [BC-UPDATE] Mapped {len(beat_id_to_path)} beat videos to segments in section {section_id}")

                    if beat_videos and not content_beat_paths:
                         section["beat_videos"] = [f"videos/{Path(p).name}" for p in beat_videos]
                    if recap_video_paths:
                         section["recap_video_paths"] = [f"videos/{Path(p).name}" for p in recap_video_paths]
                    
                    # NEW: Update video_prompts with sanitized versions (NSFW fix)
                    wan_beats = result.get("wan_beats", [])
                    if wan_beats and "video_prompts" in section:
                        prompts_updated = 0
                        for beat in wan_beats:
                            beat_id = beat.get("beat_id")
                            sanitized_prompt = beat.get("prompt")
                            
                            # Find matching prompt in section and update
                            for vp in section["video_prompts"]:
                                if isinstance(vp, dict) and vp.get("beat_id") == beat_id:
                                    if vp.get("prompt") != sanitized_prompt:
                                        vp["prompt"] = sanitized_prompt
                                        prompts_updated += 1
                                        logger.info(f"[JSON-SAVE] Persisted sanitized prompt for {beat_id}")
                        
                        if prompts_updated > 0:
                            logger.info(f"[NSFW-FIX] Updated {prompts_updated} prompts in presentation.json for section {section_id}")
                    
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
                    "section_renders": []
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
                "section_type": result.get("section_type", "content"), # Capture type if available
                "renderer": "wan", # We know this is WAN context
                "duration_seconds": round(result.get("duration_seconds", 0), 2),
                "status": result["status"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if result.get("error"):
                detail["metadata"] = {"error": result["error"]}
                
            metrics["section_renders"].append(detail)
            
            with open(analytics_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            
    except Exception as e:
        logger.error(f"Failed to update analytics.json: {e}")
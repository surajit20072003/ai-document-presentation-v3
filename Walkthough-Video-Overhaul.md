Walkthrough: V2.5 Video Generation Overhaul
This update implements a robust video generation pipeline aligned with the V2.5 Director Bible, specifically addressing the 15-second limit for WAN videos and ensuring unique visual descriptions per segment.

Key Enhancements
1. Multi-Beat WAN Generation
Segments longer than 15 seconds are now automatically split into multiple "beats," each with its own unique prompt and a maximum duration of 15 seconds.

Director Prompt: Updated to enforce 
segment_specs
 array and uniquely generated visual descriptions.
Sync Splitter: Logic in 
PartitionDirectorGenerator
 handles both explicit LLM-provided beats and automatic splitting for long segments.
Continuation Prompts: Auto-split beats use context-aware prompts (e.g., "Keeping the previous scene exactly the same, continue showing...") to ensure visual consistency.
2. Batched Kie.ai Generation
Implemented a high-throughput, rate-limited batch generator for WAN videos.

KieBatchGenerator: Manages up to 15 concurrent requests with a 15-second staggered interval to respect API limits.
Parallel Polling: Status updates for all pending videos are fetched in parallel, drastically reducing overhead.
Background Processing: WAN generation runs asynchronously, allowing the main pipeline to complete quickly.
3. Per-Segment Manim Rendering
Manim sections now follow the same 1-to-1 segment mapping as WAN.

Individual Video Files: Each SHOW segment in a Manim section produces its own .mp4 file, named after the segment ID.
Independent Generation: Each segment's visual specification is separately compiled into Python code, ensuring precise mathematical synchronization.
4. Player V2.5 Integration
The player was updated to handle the new multi-beat structure.

Sequential Playback: The player dynamically builds a playlist of multiple beat videos for a single segment, switching between them seamlessly based on narration timing.
New File Mapping: Supports seg.beat_videos (WAN) and seg.video_file (Manim) structures.
5. Video Regeneration & Error Handling
Added tools to identify and fix failed video assets without restarting the entire job.

VideoRegenerator: Detects missing or corrupt (<10KB) video files.
API Endpoints:
/api/job/<job_id>/regenerate_failed: Retries all failed videos in a job.
/api/job/<job_id>/regenerate_section/<section_id>: Targeted regeneration for a specific section.
Verification Results
Automated Validation
The 
V25Validator
 was enhanced to catch the "Duplicate Prompt" bug. It now verifies:

Presence of 
segment_specs
 for SHOW segments.
Unique visual descriptions (no duplicates across segments).
Prompt length requirements (>80 words).
Verification Script Output:

Testing Case 1 (Duplicates)...
  [ERROR] Section 'Bad Section': DUPLICATE PROMPTS DETECTED! Ensure each segment has a unique visual description.
Testing Case 2 (Unique)...
Validation logic verified!
Component Analysis
Component	Status	Purpose
Sync Splitter	✅ ACTIVE	Maps segments to beats for WAN/Manim
KieBatchGenerator
✅ ACTIVE	15 concurrent / 15s interval batching
VideoRegenerator
✅ ACTIVE	Cleanup and retry of corrupt videos
Player V2.5	✅ READY	Sequential beat playlist support
import os
import logging
import asyncio
    def _apply_sync_splitter(self, section: dict):
        """
        V2.5 Sync Rule: If a narration segment is > 15s (40 words), 
        split the video/animation into multiple 15-second beats.
        
        Supports both WAN ('video') and Manim ('manim') renderers.
        Ensures EVERY segment has a mapping to a beat, even if not split.
        V2.5 Sync Rule: Map SHOW segments to render specs.
        - Manim: 1 spec per segment (no 15s limit).
        - WAN: Multiple beats if segment > 15s.
        - Prioritizes 'segment_specs' array for 1-to-1 mapping.
        """
        if "narration" not in section or "segments" not in section["narration"]:
            return
            
        renderer = section.get("renderer")
        if renderer not in ["video", "manim"]:
            return
            
        render_spec = section.get("render_spec", {})
        segment_specs = render_spec.get("segment_specs", [])
        
        # Determine base prompts (video_prompts for WAN, manim_scene_spec for Manim)
        # V2.5 Fix: Look for prompts in root (Recap) or render_spec (Content)
        # Build segment_id -> spec map
        spec_map = {spec["segment_id"]: spec for spec in segment_specs if "segment_id" in spec}
        
        # Legacy fallbacks
        v_prompts = section.get("video_prompts", []) or render_spec.get("video_prompts", [])
        manim_spec = render_spec.get("manim_scene_spec")
        manim_spec_legacy = render_spec.get("manim_scene_spec")
        
        # Build a complete list of video prompts for the entire section
        # to ensure 1-to-1 mapping and no missing videos for any segment.
        final_video_prompts = []
        final_manim_specs = []  # Specific for manim renderer output
        
        for idx, seg in enumerate(section["narration"]["segments"]):
            seg_id = seg.get('segment_id') or f"seg_{idx + 1}"
            text = seg.get("text", "")
            words = text.split()
            duration = seg.get("duration_seconds", 15) # Should be updated by tts_duration
            
            # Base prompt selection (use director's prompts if available, else default)
            base_prompt = "Cinematic educational visualization, high quality, professional lighting, detailed 4k render." if renderer == "video" else "Mathematical conceptual animation, clear geometry, high contrast."
            # Map spec to segment
            spec = spec_map.get(seg_id)
            
            if renderer == "video":
                if isinstance(v_prompts, list) and v_prompts:
                    base_prompt_obj = v_prompts[idx % len(v_prompts)]
                    if isinstance(base_prompt_obj, dict):
                        base_prompt = base_prompt_obj.get("prompt") or base_prompt_obj.get("text") or base_prompt_obj.get("wan_prompt") or "Cinematic visualization"
                    else:
                        base_prompt = str(base_prompt_obj)
                elif section.get("video_prompt"):
                    base_prompt = section.get("video_prompt")
                elif section.get("video_prompts"): # Fallback for root list if list-proxy failed
                    try:
                        base_prompt = str(section.get("video_prompts")[0])
                    except: pass
            elif renderer == "manim":
                # For manim, prioritize the section-level spec if it exists
                if manim_spec:
                    base_prompt = manim_spec
                elif isinstance(v_prompts, list) and v_prompts:
                    # Some directors might mistakenly put manim specs in video_prompts
                    base_prompt_obj = v_prompts[idx % len(v_prompts)]
                    base_prompt = base_prompt_obj.get("prompt") if isinstance(base_prompt_obj, dict) else str(base_prompt_obj)
            # Fallback for missing segment_id to prevent "None_beat" issue
            seg_id = seg.get('segment_id') or f"seg_{idx + 1}"
            
            if len(words) > 40:
                # Calculate number of beats (15s each)
                num_beats = (len(words) // 40) + 1
                logger.info(f"Sync Splitter ({renderer}): Splitting segment {seg_id} into {num_beats} beats ({len(words)} words)")
            if renderer == "manim":
                # Manim: 1 spec per segment (no 15s limit)
                manim_code_spec = ""
                if spec:
                    manim_code_spec = spec.get("manim_scene_spec", "")
                else:
                    manim_code_spec = manim_spec_legacy or "Mathematical conceptual animation."
                
                # Consistency prefix helps the LLM maintain visual continuity across beats
                consistency_prefix = "Keeping the previous character and setting exactly the same, " if renderer == "video" else ""
                final_manim_specs.append({
                    "segment_id": seg_id,
                    "duration_seconds": duration,
                    "manim_scene_spec": manim_code_spec
                })
                # Link segment to its manim video (per-segment filename)
                seg["video_file"] = f"topic_{section.get('section_id')}_{seg_id}.mp4"
                
                seg_beats = []
                for i in range(num_beats):
                    beat_id = f"{seg_id}_beat_{i+1}"
                    final_video_prompts.append({
                        "beat_id": beat_id,
                        "prompt": f"{consistency_prefix if i > 0 else ''}{base_prompt} (Part {i+1} of {num_beats})",
                        "duration_hint": 15
                    })
                    seg_beats.append(beat_id)
            else:  # video/wan
                # Check for explicit beats provided by LLM
                llm_beats = spec.get("beats", []) if spec else []
                
                # Add beat mapping to segment so player knows to switch
                seg["beat_videos"] = seg_beats
            else:
                # Standard segment: still needs a video beat mapping
                beat_id = f"{seg_id}_beat_1"
                final_video_prompts.append({
                    "beat_id": beat_id,
                    "prompt": base_prompt,
                    "duration_hint": 15
                })
                seg["beat_videos"] = [beat_id]
                if llm_beats:
                    # Use LLM-provided beats
                    for beat in llm_beats:
                        beat["segment_id"] = seg_id
                        final_video_prompts.append(beat)
                    seg["beat_videos"] = [b["beat_id"] for b in llm_beats]
                else:
                    # Auto-split if > 15s or no beats provided
                    video_prompt = ""
                    if spec:
                        video_prompt = spec.get("video_prompt", "")
                    elif v_prompts:
                        # Fallback to cycling through legacy prompts
                        base_obj = v_prompts[idx % len(v_prompts)]
                        video_prompt = base_obj.get("prompt", str(base_obj)) if isinstance(base_obj, dict) else str(base_obj)
                    else:
                        video_prompt = "Cinematic educational visualization."
                        
                    num_beats = max(1, int((duration + 1) // 15)) # Ceiling-ish
                    if duration > 15:
                        logger.info(f"Sync Splitter (WAN): Auto-splitting segment {seg_id} ({duration}s) into {num_beats} beats")
                    
                    beat_ids = []
                    for i in range(num_beats):
                        beat_id = f"{seg_id}_beat_{i+1}"
                        prefix = "" if i == 0 else "Keeping the previous scene exactly the same, continue showing: "
                        suffix = f" (Part {i+1} of {num_beats})" if num_beats > 1 else ""
                        
                        final_video_prompts.append({
                            "beat_id": beat_id,
                            "segment_id": seg_id,
                            "prompt": prefix + video_prompt + suffix,
                            "duration_hint": min(15, duration / num_beats)
                        })
                        beat_ids.append(beat_id)
                    seg["beat_videos"] = beat_ids
        
        # Replace section top-level video_prompts with the complete mapping
        # For Manim, the runner will look for this 'video_prompts' key as well now.
        # Store for downstream processing
        section["video_prompts"] = final_video_prompts
        logger.info(f"Sync Splitter ({renderer}): Generated {len(final_video_prompts)} total beats for section {section.get('section_id')}")
        section["_manim_segment_specs"] = final_manim_specs
        logger.info(f"Sync Splitter ({renderer}): Generated {len(final_video_prompts)} WAN beats / {len(final_manim_specs)} Manim specs for section {section.get('section_id')}")
def generate_director_presentation(
    markdown_content: str,
    # For now, we are fixing PartitionDirectorGenerator.generate_presentation_partitioned.
    
    return generator.generate_presentation_loop(markdown_content, subject, grade, images_list, update_status_callback)
from typing import List, Dict, Any
                             errors.append(f"Quiz '{title}' Q{q_idx+1} Pause segment must contain <pause duration='3'/> tag.")
            if stype in ["content", "example"]:
                # Renderer Check
                # 2. RENDERER & SEGMENT SPECS CHECK
                renderer = sec.get("renderer")
                if not renderer:
                    errors.append(f"Section '{title}' ({stype}) is MISSING 'renderer' key.")
                
                # Check for segment_specs (V2.5 requirement)
                render_spec = sec.get("render_spec", {})
                segment_specs = render_spec.get("segment_specs", [])
                
                # Identify SHOW segments
                segments = sec.get("narration", {}).get("segments", [])
                show_seg_ids = {seg["segment_id"] for seg in segments if seg.get("display_directives", {}).get("visual_layer") == "show"}
                
                if show_seg_ids and not segment_specs:
                    # Legacy fallback check
                    v_prompts = render_spec.get("video_prompts", [])
                    m_spec = render_spec.get("manim_scene_spec")
                    if not v_prompts and not m_spec:
                         errors.append(f"Section '{title}': Missing 'segment_specs' for SHOW segments {show_seg_ids}.")
                
                # Verify each SHOW segment has a spec
                spec_ids = {spec.get("segment_id") for spec in segment_specs if spec.get("segment_id")}
                missing_specs = show_seg_ids - spec_ids
                if missing_specs:
                    errors.append(f"Section '{title}': Missing segment_specs for {missing_specs}.")
                # DUPLICATE PROMPT DETECTION (THE BUG FIX)
                all_prompts = []
                for spec in segment_specs:
                    p = spec.get("video_prompt") or spec.get("manim_scene_spec")
                    if p: all_prompts.append(str(p).strip()[:100].lower()) # Check first 100 chars
                
                if len(all_prompts) > 1 and len(set(all_prompts)) < len(all_prompts):
                    errors.append(f"Section '{title}': DUPLICATE PROMPTS DETECTED! Ensure each segment has a unique visual description.")
                # Manim Spec Check
                if renderer == "manim":
                    spec = sec.get("render_spec", {}).get("manim_scene_spec")
                    if not spec:
                        errors.append(f"Section '{title}' has renderer='manim' but missing 'manim_scene_spec'.")
                    elif isinstance(spec, dict):
                         # If it's a dict, it's either legacy V1.2 or empty fallback. 
                         # V2.5 Director Prompt demands a STRING. Check if it's empty.
                         if not spec:
                             errors.append(f"Section '{title}' manim_scene_spec is EMPTY DICT {{}}. Expected String Prompt.")
                         else:
                             # Legacy support fallback? Or strict fail?
                             # Let's fail with clear message:
                             errors.append(f"Section '{title}' manim_scene_spec is a DICT, expected STRING (80+ words). Keys found: {list(spec.keys())}")
                    elif len(spec.split()) < 80:
                        errors.append(f"Section '{title}' manim_scene_spec is too short ({len(spec.split())} words). Must be 80+ words.")
                    # Check individual specs if available, else root spec
                    if segment_specs:
                        for spec in segment_specs:
                            if spec.get("segment_id") in show_seg_ids:
                                p = spec.get("manim_scene_spec", "")
                                if not p or len(str(p).split()) < 80:
                                    errors.append(f"Section '{title}' Manim spec for {spec.get('segment_id')} is too short or missing.")
                    else:
                        spec = render_spec.get("manim_scene_spec")
                        if not spec or len(str(spec).split()) < 80:
                            errors.append(f"Section '{title}' root manim_scene_spec is too short or missing.")
                        
                # Video Prompt Check
                if renderer == "video":
                    v_prompts = sec.get("render_spec", {}).get("video_prompts", [])
                    if not v_prompts:
                         errors.append(f"Section '{title}' has renderer='video' but MISSING 'video_prompts'.")
                    if segment_specs:
                        for spec in segment_specs:
                            if spec.get("segment_id") in show_seg_ids:
                                p = spec.get("video_prompt", "")
                                # If beat-based, check beats
                                beats = spec.get("beats", [])
                                if beats:
                                    for b in beats:
                                        if len(str(b.get("prompt", "")).split()) < 80:
                                            errors.append(f"Section '{title}' WAN Beat {b.get('beat_id')} prompt too short.")
                                elif not p or len(str(p).split()) < 80:
                                    errors.append(f"Section '{title}' WAN prompt for {spec.get('segment_id')} is too short or missing.")
                    else:
                        for idx, vp in enumerate(v_prompts):
                            prompt_text = vp if isinstance(vp, str) else str(vp)
                            wc = len(prompt_text.split())
                            if wc < 80:
                                errors.append(f"Section '{title}' video_prompt {idx} is too short ({wc} words). Must be 80+ words.")
                        v_prompts = render_spec.get("video_prompts", [])
                        if not v_prompts:
                             errors.append(f"Section '{title}' missing video_prompts.")
                        else:
                            for idx, vp in enumerate(v_prompts):
                                if len(str(vp).split()) < 80:
                                    errors.append(f"Section '{title}' video_prompt {idx} too short.")
                # VERBATIM POINTER CHECK - DISABLED PER USER FEEDBACK (Trust LLM)
                # if source_text:
                #    visual_beats = sec.get("visual_beats", [])
                #    for beat in visual_beats:
                #        ptr = beat.get("markdown_pointer")
                #        if ptr:
                #            start = ptr.get("start_phrase", "").strip()
                #            end = ptr.get("end_phrase", "").strip()
                #            
                #            if start and start not in source_text:
                #                errors.append(f"Section '{title}': Pointer start_phrase '{start[:20]}...' NOT FOUND in source text.")
                #            if end and end not in source_text:
                #                errors.append(f"Section '{title}': Pointer end_phrase '{end[:20]}...' NOT FOUND in source text.")
                
                pass
        return errors
"""
Manim Video Runner - Generates mathematical animations from visual beats
            trace_output_dir=trace_output_dir
        )
    
    # NEW V2.5 SYNC: Check for sync-split beats in video_prompts (from Sync Splitter)
    # This allows Manim to support the same 1-to-1 segment mapping as WAN
    # NEW V2.5 SYNC: Check for per-segment Manim specs
    manim_segment_specs = topic.get("_manim_segment_specs", [])
    if manim_segment_specs:
        print(f"[MANIM V2.5] Section {topic_id}: Rendering {len(manim_segment_specs)} per-segment videos")
        return _render_manim_segment_specs(
            specs=manim_segment_specs,
            topic_id=topic_id,
            topic_title=topic_title,
            output_dir=output_dir,
            dry_run=dry_run,
            trace_output_dir=trace_output_dir
        )
    
    # NEW V2.5 SYNC: Check for sync-split beats (fallback for older code)
    video_prompts = topic.get("video_prompts", [])
    if video_prompts and isinstance(video_prompts, list) and len(video_prompts) > 0:
        print(f"[MANIM V2.5] Section {topic_id}: Rendering {len(video_prompts)} sync-split beats")
    return rendered_paths
def _render_manim_segment_specs(
    specs: list,
    topic_id: int,
    topic_title: str,
    output_dir: str,
    dry_run: bool = False,
    trace_output_dir: str | None = None
) -> list[str]:
    """
    Render per-segment Manim videos.
    Each spec has: segment_id, duration_seconds, manim_scene_spec
    """
    from core.agents.manim_code_generator import ManimCodeGenerator
    
    generator = ManimCodeGenerator()
    rendered_paths = []
    
    for spec in specs:
        seg_id = spec["segment_id"]
        # Filename format: topic_{topic_id}_{seg_id}.mp4
        output_path = str(Path(output_dir) / f"topic_{topic_id}_{seg_id}.mp4")
        duration = spec["duration_seconds"]
        manim_spec = spec["manim_scene_spec"]
        
        # Prepare data for code generator
        beat_data = {
            "section_title": f"{topic_title} - {seg_id}",
            "manim_spec": manim_spec,
            "narration_segments": [{"text": "Visualizing segment content", "duration": duration}],
            "duration": duration
        }
        
        if dry_run:
            dry_marker = _create_dry_run_marker(f"{topic_id}_{seg_id}", output_path, duration, f"Manim Spec: {manim_spec}")
            rendered_paths.append(dry_marker)
            continue
            
        try:
            # Generate code
            manim_code, errors = generator.generate(beat_data)
            if errors:
                raise ManimRenderError(f"Segment {seg_id} code gen failed: {errors}")
                
            # Execute render
            result = _execute_spec_generated_render(
                manim_code=manim_code,
                duration=duration,
                output_path=output_path,
                topic_id=f"{topic_id}_{seg_id}"
            )
            rendered_paths.append(result)
        except Exception as e:
            print(f"  [MANIM FAIL] Segment {seg_id}: {e}")
            # In V2.5 we don't fallback to placeholder usually, but for segments we might want to continue
            # For now, let's keep it strict or raise
            raise
            
    return rendered_paths
def _render_sync_split_manim_beats(
    video_prompts: list,
    topic_id: int,
        f.write(scene_code)
    print(f"[DRY RUN] Created marker: {marker_path}")
    return marker_path
/**
 * PLAYER V2.5 - Director Bible Compliant
 * Clean, compliant implementation following V2.5 Architecture
// BEAT VIDEO HANDLING
// ============================================
function buildBeatPlaylistWithTiming(slide) {
  const beatVideoPaths = slide.beat_video_paths || [];
  const segments = slide.narration?.segments || [];
  const playlist = [];
  let accumulatedTime = 0;
  segments.forEach((seg, i) => {
    const duration = seg.duration_seconds || 5;
    const videoPath = beatVideoPaths[i];
    if (videoPath) {
    const segDuration = seg.duration_seconds || 5;
    
    // V2.5 Logic: Handle multiple beat videos per segment (WAN) OR individual video file (Manim)
    const beatVideos = seg.beat_videos || [];
    const manimVideo = seg.video_file;
    
    if (beatVideos.length > 0) {
      // Distributed segment duration across its beats
      const beatDuration = segDuration / beatVideos.length;
      beatVideos.forEach((videoPath, j) => {
        playlist.push({
          videoPath: resolveMediaPath(videoPath, 'video'),
          startTime: accumulatedTime + (j * beatDuration),
          endTime: accumulatedTime + ((j + 1) * beatDuration),
          segmentIndex: i
        });
      });
      console.log(`[V2.5] Segment ${i}: Added ${beatVideos.length} WAN beats to playlist`);
    } else if (manimVideo) {
      // Single Manim video for this segment
      playlist.push({
        videoPath: resolveMediaPath(videoPath, 'video'),
        videoPath: resolveMediaPath(manimVideo, 'video'),
        startTime: accumulatedTime,
        endTime: accumulatedTime + duration,
        endTime: accumulatedTime + segDuration,
        segmentIndex: i
      });
      console.log(`[V2.5] Segment ${i}: Added Manim video to playlist`);
    }
    accumulatedTime += duration;
    accumulatedTime += segDuration;
  });
  return playlist;
    }
  }
}, 500);
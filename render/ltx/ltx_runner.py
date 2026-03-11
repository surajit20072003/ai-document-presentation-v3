"""
LTX Runner - Generates videos using LTX Client
Functions mirrored from wan_runner.py but adapted for LTX.
"""
import os
from pathlib import Path
from render.ltx.ltx_client import LtxClient
from render.render_trace import log_render_prompt
from core.wan_prompt_validator import hard_fail_on_short_prompts, WanPromptHardFailError, truncate_video_prompts, truncate_wan_prompt, expand_video_prompts

class LtxRenderError(Exception):
    pass

def render_ltx_video(topic: dict, output_dir: str, dry_run: bool = False, skip_wan: bool = False, trace_output_dir: str = None) -> str:
    """
    Render video for a section using LTX.
    """
    topic_id = topic.get("section_id", topic.get("id", 1))
    topic_title = topic.get("title", "Untitled")
    section_type = topic.get("section_type", "content")
    explanation_plan = topic.get("explanation_plan", {})
    visual_beats = topic.get("visual_beats", [])
    
    # 1. Content/Example Sections (Visual Beats)
    compiled_wan_prompt = explanation_plan.get("compiled_wan_prompt")
    video_prompts = topic.get("video_prompts", []) or explanation_plan.get("video_prompts", [])
    
    if section_type in ["content", "example"] and (visual_beats or video_prompts):
        result = _render_ltx_beats(
            topic_id, topic_title, section_type, visual_beats, output_dir, 
            dry_run, skip_wan, trace_output_dir, video_prompts, return_all_paths=True
        )
        topic["_beat_video_paths"] = result.get("all_paths", [])
        return result.get("first_path")

    # 2. Recap Sections
    recap_scenes = topic.get("recap_scenes", [])
    if section_type == "recap":
        # Handle recap scenes logic (similar to WAN)
        if recap_scenes:
            result = _render_ltx_recap(
                topic_id, topic_title, recap_scenes, output_dir, 
                dry_run, skip_wan, trace_output_dir
            )
            topic["_recap_video_paths"] = result.get("all_paths", [])
            return result.get("first_path")
        elif video_prompts:
             # Handle recap with video_prompts list
             result = _render_ltx_beats(
                topic_id, topic_title, section_type, [], output_dir, 
                dry_run, skip_wan, trace_output_dir, video_prompts, return_all_paths=True
            )
             topic["_recap_video_paths"] = result.get("all_paths", [])
             return result.get("first_path")
             
    # 3. Fallback/Single Prompt
    # For now, LTX integration mainly targets content/recap. 
    # If general prompt exists:
    ltx_prompt = explanation_plan.get("wan_prompt") or compiled_wan_prompt
    if not ltx_prompt:
         raise LtxRenderError(f"Section {topic_id}: No prompt found for LTX.")
         
    output_path = str(Path(output_dir) / f"topic_{topic_id}.mp4")
    
    if dry_run:
        return _create_dry_run_marker(output_path, ltx_prompt)
    if skip_wan:
        return _create_placeholder(output_path, topic_title)
        
    client = LtxClient()
    # Validate prompt length logic here if needed (reuse wan validator for consistency)
    
    return client.generate_video(prompt=ltx_prompt, output_path=output_path)


def _render_ltx_beats(topic_id, topic_title, section_type, visual_beats, output_dir, dry_run, skip_wan, trace_output_dir, video_prompts=None, return_all_paths=False):
    """Render multiple beats."""
    use_precompiled = video_prompts and len(video_prompts) > 0
    num_beats = len(video_prompts) if use_precompiled else len(visual_beats)
    
    video_paths = []
    client = LtxClient() if not dry_run and not skip_wan else None
    
    for i in range(num_beats):
        if use_precompiled:
            p_obj = video_prompts[i]
            prompt = p_obj if isinstance(p_obj, str) else p_obj.get("prompt", "")
            duration = 5 if isinstance(p_obj, str) else int(p_obj.get("duration_seconds") or p_obj.get("duration_hint") or 5)
        else:
            # MVP: Assuming compiled or extraction logic from visual beats if needed
            # For strict LTX MVP, we might rely on video_prompts being present from LLM
            beat = visual_beats[i]
            prompt = beat.get("description", "") # simplified fallback
            duration = 5
            
        output_path = str(Path(output_dir) / f"topic_{topic_id}_beat_{i}.mp4")
        
        if dry_run:
            video_paths.append(_create_dry_run_marker(output_path, prompt))
            continue
        if skip_wan:
            video_paths.append(_create_placeholder(output_path, f"Beat {i}"))
            continue
            
        try:
            path = client.generate_video(prompt=prompt, output_path=output_path, duration=duration)
            video_paths.append(path)
        except Exception as e:
            print(f"[LTX] Failed beat {i}: {e}")
            raise # No silent fallback as requested
            
    return {
        "first_path": video_paths[0] if video_paths else None,
        "all_paths": video_paths
    }

def _render_ltx_recap(topic_id, topic_title, recap_scenes, output_dir, dry_run, skip_wan, trace_output_dir):
    """Render recap scenes."""
    video_paths = []
    client = LtxClient() if not dry_run and not skip_wan else None
    
    for i, scene in enumerate(recap_scenes):
        prompt = scene.get("wan_prompt", "")
        duration = int(scene.get("duration_seconds") or scene.get("duration_hint") or 15)
        output_path = str(Path(output_dir) / f"recap_{topic_id}_scene_{i+1}.mp4")
        
        if dry_run:
            video_paths.append(_create_dry_run_marker(output_path, prompt))
            continue
        if skip_wan:
            video_paths.append(_create_placeholder(output_path, f"Recap {i+1}"))
            continue
            
        try:
            path = client.generate_video(prompt=prompt, output_path=output_path, duration=duration)
            video_paths.append(path)
        except Exception as e:
            print(f"[LTX] Failed recap scene {i+1}: {e}")
            raise

    return {
        "first_path": video_paths[0] if video_paths else None,
        "all_paths": video_paths
    }

def _create_dry_run_marker(path, prompt):
    with open(path + ".dry_run", "w") as f:
        f.write(f"Prompt: {prompt}")
    return path + ".dry_run"

def _create_placeholder(path, text):
    # Simple placeholder logic, maybe create empty file for now or copy generic
    # For MVP just robust string return
    return path

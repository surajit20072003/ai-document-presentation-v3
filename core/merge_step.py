"""
Merge Step v1.4 - Deterministic Output Combination

Merges Content Director output + Recap Director output into a single
presentation.json that is v1.3 schema compliant.

This is pure Python logic - NO LLM calls.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


TEXT_ONLY_SECTION_TYPES = ["intro", "summary", "memory"]

# Keywords that trigger WAN routing (use_local_gpu=False) for recap sections.
# Matches the same logic in director_partition_prompt.txt.
BIOLOGY_ANATOMY_KEYWORDS = [
    "biology", "anatomy", "human body", "organ", "cell", "tissue",
    "physiology", "genetics", "microbiology", "botany", "zoology",
    "nervous system", "digestive", "respiratory", "circulatory"
]


def _is_biology_anatomy(subject: str) -> bool:
    """Return True if the subject should be routed to WAN (not Local GPU)."""
    subject_lower = subject.lower()
    return any(kw in subject_lower for kw in BIOLOGY_ANATOMY_KEYWORDS)


def merge_director_outputs(
    content_output: Dict,
    recap_output: Dict,
    subject: str,
    grade: str
) -> Dict:
    """
    Deterministic merge of Content Director + Recap Director outputs.
    No LLM calls - pure Python logic.
    
    Operations:
    1. Combine sections array: content_sections + [memory, recap]
    2. Assign sequential section_ids
    3. Preserve all fields from both outputs
    4. Set spec_version: "v1.4"
    5. Add generation metadata
    6. ISS-113 FIX: Enforce renderer policy (intro/summary/memory = none)
    
    Args:
        content_output: Output from Content Director (intro/summary/content/example/quiz)
        recap_output: Output from Recap Director (memory/recap)
        subject: Subject area
        grade: Grade level
        
    Returns:
        Complete presentation.json dict (v1.3 schema compliant)
    """
    logger.info("[Merge Step] Combining Content + Recap Director outputs")
    
    content_sections = content_output.get("sections", [])
    recap_sections = recap_output.get("sections", [])
    
    logger.info(f"[Merge Step] Content sections: {len(content_sections)}, Recap sections: {len(recap_sections)}")
    
    ordered_sections = _order_sections(content_sections, recap_sections, subject)
    
    for i, section in enumerate(ordered_sections, start=1):
        section["section_id"] = f"section_{i}"
        
        section_type = section.get("section_type", "")
        if section_type in TEXT_ONLY_SECTION_TYPES:
            old_renderer = section.get("renderer", "")
            if old_renderer != "none":
                section["renderer"] = "none"
                section["renderer_override_reason"] = f"ISS-113: {section_type} is text-only, forced from '{old_renderer}' to 'none'"
                logger.info(f"[Merge Step] ISS-113 FIX: Section {i} ({section_type}) renderer '{old_renderer}' -> 'none'")
    
    title = content_output.get("title", f"{subject} Lesson")
    
    presentation = {
        "spec_version": "v1.4",
        "title": title,
        "subject": subject,
        "grade": grade,
        "sections": ordered_sections,
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "pipeline_version": "v1.4",
            "content_director_model": "google/gemini-2.5-pro",
            "recap_director_model": "google/gemini-2.5-pro",
            "section_count": len(ordered_sections),
            "section_types": [s.get("section_type") for s in ordered_sections]
        }
    }
    
    _validate_merged_output(presentation)
    
    logger.info(f"[Merge Step] Successfully merged {len(ordered_sections)} sections")
    return presentation


RECAP_SCENE_ORDER = ["recap_scene_1", "recap_scene_2", "recap_scene_3", "recap_scene_4", "recap_scene_5"]


def _normalize_segment(segment: Dict, scene_idx: int, seg_idx: int) -> Dict:
    """
    Normalize segment format to match Content Director output.
    Ensures all segments have consistent fields for TTS and player.
    
    Input formats:
    - Recap Director: {start, end, text, start_time, end_time}
    - Content Director: {segment_id, text, duration_estimate, display_directives, ...}
    
    Output format (normalized):
    - {segment_id, text, duration_estimate, display_directives, ...}
    """
    normalized = {}
    
    text = segment.get("text", "")
    normalized["text"] = text
    
    segment_id = segment.get("segment_id") or f"recap_{scene_idx}_seg_{seg_idx}"
    normalized["segment_id"] = segment_id
    
    if "duration_estimate" in segment:
        normalized["duration_estimate"] = segment["duration_estimate"]
    elif "start" in segment and "end" in segment:
        duration = segment["end"] - segment["start"]
        normalized["duration_estimate"] = max(1.0, duration)
    else:
        word_count = len(text.split())
        normalized["duration_estimate"] = max(1.0, word_count / 2.2)
    
    if "display_directives" in segment:
        normalized["display_directives"] = segment["display_directives"]
    else:
        normalized["display_directives"] = {
            "text_layer": "hide",
            "visual_layer": "show",
            "avatar_layer": "hide",
            "flip_timing_sec": None  # ISS-160: null = no flip
        }
    
    # ISS-160: Propagate visual_content fields if present
    if "visual_content" in segment:
        normalized["visual_content"] = segment["visual_content"]
    
    if "start" in segment:
        normalized["start"] = segment["start"]
    if "end" in segment:
        normalized["end"] = segment["end"]
    if "start_time" in segment:
        normalized["start_time"] = segment["start_time"]
    if "end_time" in segment:
        normalized["end_time"] = segment["end_time"]
    
    return normalized


def _normalize_memory_section(memory: Dict) -> Dict:
    """
    Normalize memory section segments to have consistent format.
    Memory flashcards don't need segments normalized as heavily,
    but we ensure duration_estimate is present.
    """
    narration = memory.get("narration", {})
    segments = narration.get("segments", [])
    
    normalized_segments = []
    for idx, seg in enumerate(segments, 1):
        normalized = _normalize_segment(seg, 0, idx)
        normalized_segments.append(normalized)
    
    if normalized_segments:
        memory["narration"]["segments"] = normalized_segments
        total_dur = sum(s.get("duration_estimate", 0) for s in normalized_segments)
        memory["narration"]["total_duration_seconds"] = round(total_dur, 2)
    
    return memory


def _order_sections(content_sections: List[Dict], recap_sections: List[Dict], subject: str = "") -> List[Dict]:
    """
    Order sections in pedagogical sequence:
    1. intro
    2. summary
    3. content/example/quiz (in original order)
    4. memory
    5. recap (SINGLE section with 5 scenes merged from recap_scene_1..5)
    
    IMPORTANT: The player expects ONE 'recap' section with visual_beats/recap_scenes array.
    The Split Director outputs 5 separate recap_scene_N sections which we MERGE here
    into a single player-compatible recap section.
    """
    ordered = []
    
    intro = None
    summary = None
    other_content = []
    
    for section in content_sections:
        section_type = section.get("section_type")
        if section_type == "intro":
            intro = section
        elif section_type == "summary":
            summary = section
        else:
            other_content.append(section)
    
    if intro:
        ordered.append(intro)
    if summary:
        ordered.append(summary)
    
    ordered.extend(other_content)
    
    memory = None
    recap_scene_sections = {}
    
    for section in recap_sections:
        section_type = section.get("section_type")
        if section_type == "memory":
            memory = section
        elif section_type in RECAP_SCENE_ORDER:
            recap_scene_sections[section_type] = section
    
    if memory:
        memory = _normalize_memory_section(memory)
        ordered.append(memory)
    
    merged_recap = _merge_recap_scenes_to_single_section(recap_scene_sections, subject)
    if merged_recap:
        ordered.append(merged_recap)
    
    return ordered


def _merge_recap_scenes_to_single_section(recap_scene_sections: Dict[str, Dict], subject: str = "") -> Optional[Dict]:
    """
    Convert 5 separate recap_scene_N sections into ONE 'recap' section.
    
    This maintains player compatibility while allowing the LLM to generate
    smaller, more manageable sections.
    
    Input: {"recap_scene_1": {...}, "recap_scene_2": {...}, ...}
    Output: Single section with section_type="recap" containing:
      - Merged narration from all scenes
      - visual_beats array with all scene prompts
      - recap_scenes array for video paths
    """
    if not recap_scene_sections:
        logger.warning("[Merge Step] No recap scenes to merge")
        return None
    
    all_narration_text = []
    all_segments = []
    visual_beats = []
    recap_scenes = []
    total_duration = 0.0
    
    for scene_type in RECAP_SCENE_ORDER:
        if scene_type not in recap_scene_sections:
            logger.warning(f"[Merge Step] Missing {scene_type}")
            continue
        
        scene = recap_scene_sections[scene_type]
        scene_index = RECAP_SCENE_ORDER.index(scene_type) + 1
        
        narration = scene.get("narration", {})
        scene_text = narration.get("full_text", "") or scene.get("narration_text", "")
        if scene_text:
            all_narration_text.append(scene_text)
        
        segments = narration.get("segments", [])
        for seg_idx, seg in enumerate(segments):
            adjusted_seg = _normalize_segment(seg, scene_index, seg_idx + 1)
            adjusted_seg["start_time"] = adjusted_seg.get("start_time", 0) + total_duration
            adjusted_seg["end_time"] = adjusted_seg.get("end_time", 0) + total_duration
            all_segments.append(adjusted_seg)
        
        scene_duration = narration.get("total_duration", 0) or scene.get("duration", 30)
        
        # v1.4 FIX: Handle both video_prompt (legacy) and visual_beats (new v1.4)
        video_prompt = scene.get("video_prompt", "")
        if isinstance(video_prompt, dict):
            video_prompt = video_prompt.get("prompt", "") or video_prompt.get("description", "")
        
        # If no video_prompt, check visual_beats (new v1.4 format)
        if not video_prompt:
            scene_visual_beats = scene.get("visual_beats", [])
            if scene_visual_beats and len(scene_visual_beats) > 0:
                first_beat = scene_visual_beats[0]
                if isinstance(first_beat, dict):
                    video_prompt = first_beat.get("description", "") or first_beat.get("prompt", "")
        
        visual_beats.append({
            "scene_id": scene_index,
            "time": total_duration,
            "description": video_prompt,
            "video_prompt": video_prompt,
            "duration": scene_duration
        })
        
        recap_scenes.append({
            "scene_id": scene_index,
            "scene": scene_index,
            "wan_prompt": video_prompt,
            "video_prompt": video_prompt,
            "narration_text": scene_text,
            "duration": scene_duration
        })
        
        total_duration += scene_duration
    
    if not visual_beats:
        logger.warning("[Merge Step] No visual beats generated from recap scenes")
        return None

    # Routing: biology/anatomy → WAN (Kie.ai), everything else → Local GPU.
    # Mirrors the same rule in director_partition_prompt.txt for content sections.
    use_local_gpu = not _is_biology_anatomy(subject)
    routing_label = "Local GPU" if use_local_gpu else "Kie.ai WAN (biology/anatomy)"
    logger.info(f"[Merge Step] Recap routing for subject '{subject}': {routing_label} (use_local_gpu={use_local_gpu})")

    # Build video_prompts so the background job router (renderer_executor.py) can
    # find and submit these beats.  Each entry must have beat_id + prompt.
    video_prompts = []
    for i, scene in enumerate(recap_scenes):
        prompt_text = scene.get("wan_prompt") or scene.get("video_prompt") or ""
        video_prompts.append({
            "beat_id": f"recap_scene_{i + 1}",
            "prompt": prompt_text,
            "duration_hint": scene.get("duration", 5)
        })

    merged_recap = {
        "section_type": "recap",
        "section_title": "Lesson Recap",
        "layout": {"avatar_position": "hidden"},
        "renderer": "video",
        "renderer_reasoning": "WAN video for cinematic recap visualization",
        "use_local_gpu": use_local_gpu,
        "narration": {
            "full_text": " ".join(all_narration_text),
            "segments": all_segments,
            "total_duration": total_duration
        },
        "visual_beats": visual_beats,
        "recap_scenes": recap_scenes,
        "video_prompts": video_prompts,
        "avatar": {
            "visible": False,
            "position": "hidden"
        }
    }
    
    logger.info(f"[Merge Step] Merged {len(visual_beats)} recap scenes into single recap section (duration: {total_duration}s)")
    return merged_recap


def _validate_merged_output(presentation: Dict) -> None:
    """
    Final validation of merged output.
    Logs warnings for any issues but doesn't raise errors
    (validation should have been done by Directors).
    
    NOTE: After merging, recap_scene_1..5 become ONE 'recap' section.
    """
    sections = presentation.get("sections", [])
    section_types = [s.get("section_type") for s in sections]
    
    required_types = ["intro", "summary", "memory", "recap"]
    missing = [t for t in required_types if t not in section_types]
    
    if missing:
        logger.warning(f"[Merge Step] Warning: Missing required section types: {missing}")
    
    content_count = sum(1 for t in section_types if t in ["content", "example"])
    if content_count == 0:
        logger.warning("[Merge Step] Warning: No content or example sections found")
    
    for i, section in enumerate(sections):
        if "section_id" not in section:
            logger.warning(f"[Merge Step] Section {i} missing section_id")
        if "renderer" not in section:
            logger.warning(f"[Merge Step] Section {i} missing renderer")
        if "narration" not in section:
            logger.warning(f"[Merge Step] Section {i} missing narration")


def get_section_stats(presentation: Dict) -> Dict:
    """
    Get statistics about the merged presentation.
    
    Returns:
        Dict with section counts and types
    """
    sections = presentation.get("sections", [])
    
    type_counts = {}
    renderer_counts = {}
    total_segments = 0
    
    for section in sections:
        section_type = section.get("section_type", "unknown")
        renderer = section.get("renderer", "unknown")
        
        type_counts[section_type] = type_counts.get(section_type, 0) + 1
        renderer_counts[renderer] = renderer_counts.get(renderer, 0) + 1
        
        segments = section.get("narration", {}).get("segments", [])
        total_segments += len(segments)
    
    return {
        "total_sections": len(sections),
        "total_segments": total_segments,
        "section_types": type_counts,
        "renderers": renderer_counts
    }

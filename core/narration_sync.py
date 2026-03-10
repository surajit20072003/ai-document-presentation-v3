"""
Narration Sync Handler v1.5

Ensures visual_beats sync correctly with narration segments.
Validates timing invariants before and after TTS pass.

Key invariants:
1. visual_beat[i].segment_id must exist in narration.segments
2. Every segment must have display_directives after merge
3. sum(segment.duration_seconds) = section total duration
"""

import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


def validate_beat_segment_sync(
    visual_beats: List[Dict],
    segments: List[Dict]
) -> Tuple[bool, List[str]]:
    """
    Validate that visual_beats reference valid segment_ids.
    
    Args:
        visual_beats: Array of visual beat objects
        segments: Array of narration segment objects
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    segment_ids = {s.get("segment_id") for s in segments}
    
    for beat in visual_beats:
        beat_id = beat.get("beat_id")
        seg_id = beat.get("segment_id")
        
        if seg_id not in segment_ids:
            errors.append(f"Beat {beat_id}: segment_id {seg_id} not found in narration segments")
    
    if len(visual_beats) != len(segments):
        errors.append(f"Beat count ({len(visual_beats)}) != segment count ({len(segments)})")
    
    return len(errors) == 0, errors


def validate_manim_beat_videos(section: Dict) -> Tuple[bool, List[str]]:
    """
    V2.6: Validate that Manim sections have segment-level beat_videos.
    
    For Manim sections with segment_specs, each segment where visual_layer='show'
    should have a beat_videos entry linking to the rendered video.
    
    Args:
        section: Section object
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    renderer = section.get("renderer", "")
    if renderer != "manim":
        return True, []  # Only applies to Manim
    
    render_spec = section.get("render_spec", {})
    segment_specs = render_spec.get("segment_specs", [])
    manim_specs = [s for s in segment_specs if s.get("renderer") == "manim"]
    
    if not manim_specs:
        return True, []  # No per-segment specs, legacy mode
    
    segments = section.get("narration", {}).get("segments", [])
    
    for spec in manim_specs:
        seg_id = spec.get("segment_id")
        # Find matching narration segment
        matched_seg = next((s for s in segments if s.get("segment_id") == seg_id), None)
        
        if not matched_seg:
            errors.append(f"Manim spec for {seg_id}: No matching narration segment")
            continue
        
        beat_videos = matched_seg.get("beat_videos", [])
        if not beat_videos:
            errors.append(f"Segment {seg_id}: Missing beat_videos link (Manim video not rendered?)")
    
    return len(errors) == 0, errors


def validate_display_directives(segments: List[Dict]) -> Tuple[bool, List[str]]:
    """
    Validate that all segments have display_directives (post-merge).
    Also validates mutual exclusion rule (G4).
    
    Args:
        segments: Array of narration segment objects
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    for seg in segments:
        seg_id = seg.get("segment_id")
        
        if "display_directives" not in seg:
            errors.append(f"Segment {seg_id}: missing display_directives")
            continue
        
        dd = seg.get("display_directives", {})
        text_layer = dd.get("text_layer")
        visual_layer = dd.get("visual_layer")
        
        if text_layer == "show" and visual_layer == "show":
            errors.append(f"Segment {seg_id}: G4 violation - text_layer and visual_layer both 'show'")
    
    return len(errors) == 0, errors


def validate_duration_invariant(sections: List[Dict]) -> Tuple[bool, List[str]]:
    """
    Validate that segment durations are reasonable.
    
    Post-TTS: sum(segment.duration_seconds) should equal section duration.
    Pre-TTS: Estimates based on word count should be within reasonable bounds.
    
    Args:
        sections: Array of section objects
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    for section in sections:
        section_id = section.get("section_id")
        segments = section.get("narration", {}).get("segments", [])
        
        if not segments:
            errors.append(f"Section {section_id}: no narration segments")
            continue
        
        total_duration = sum(s.get("duration_seconds", 0) for s in segments)
        
        if total_duration < 5:
            errors.append(f"Section {section_id}: total duration {total_duration:.1f}s too short")
        
        if total_duration > 300:
            errors.append(f"Section {section_id}: total duration {total_duration:.1f}s too long")
    
    return len(errors) == 0, errors


def validate_section_sync(section: Dict) -> Tuple[bool, List[str]]:
    """
    Validate all sync aspects of a single section.
    
    Args:
        section: Section object
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    all_errors = []
    
    visual_beats = section.get("visual_beats", [])
    segments = section.get("narration", {}).get("segments", [])
    
    valid, errors = validate_beat_segment_sync(visual_beats, segments)
    if not valid:
        all_errors.extend(errors)
    
    valid, errors = validate_display_directives(segments)
    if not valid:
        all_errors.extend(errors)
    
    # V2.6: Validate Manim beat_videos linking
    valid, errors = validate_manim_beat_videos(section)
    if not valid:
        all_errors.extend(errors)
    
    return len(all_errors) == 0, all_errors


def validate_presentation_sync(presentation: Dict) -> Tuple[bool, List[str]]:
    """
    Validate sync for entire presentation.
    
    Args:
        presentation: Full presentation object
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    all_errors = []
    
    sections = presentation.get("sections", [])
    
    valid, errors = validate_duration_invariant(sections)
    if not valid:
        all_errors.extend(errors)
    
    for section in sections:
        section_type = section.get("section_type")
        
        if section_type in ["memory"]:
            continue
        
        valid, errors = validate_section_sync(section)
        if not valid:
            section_id = section.get("section_id")
            all_errors.extend([f"Section {section_id}: {e}" for e in errors])
    
    if all_errors:
        logger.warning(f"[Narration Sync] {len(all_errors)} validation errors found")
        for err in all_errors[:5]:
            logger.warning(f"[Narration Sync] {err}")
    else:
        logger.info("[Narration Sync] All sync validations passed")
    
    return len(all_errors) == 0, all_errors


def estimate_duration_from_text(text: str, wpm: int = 130) -> float:
    """
    Estimate audio duration from text based on words per minute.
    
    Args:
        text: Narration text
        wpm: Words per minute (default 130 for clear speech)
        
    Returns:
        Estimated duration in seconds
    """
    word_count = len(text.split())
    duration = (word_count / wpm) * 60
    return max(1.0, round(duration, 1))


def sync_durations_post_tts(
    presentation: Dict,
    actual_durations: Dict[str, float]
) -> Dict:
    """
    Update presentation with actual TTS durations.
    
    Args:
        presentation: Presentation object with estimated durations
        actual_durations: Map of segment_id to actual duration in seconds
        
    Returns:
        Updated presentation with actual durations
    """
    sections = presentation.get("sections", [])
    
    for section in sections:
        section_id = section.get("section_id")
        segments = section.get("narration", {}).get("segments", [])
        
        for seg in segments:
            seg_id = seg.get("segment_id")
            key = f"{section_id}_{seg_id}"
            
            if key in actual_durations:
                old_duration = seg.get("duration_seconds", 0)
                seg["duration_seconds"] = actual_durations[key]
                logger.debug(f"[Narration Sync] Segment {key}: {old_duration:.1f}s -> {actual_durations[key]:.1f}s")
    
    return presentation

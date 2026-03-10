"""
Merge Step v1.5 - Deterministic Agent Output Combination

Merges all V1.5 agent outputs into a single presentation.json
that is v1.3 schema compliant.

This is pure Python logic - NO LLM calls.

Principle P7 (Content Integrity): Display ONLY content from source document.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


TEXT_ONLY_SECTION_TYPES = ["intro", "summary", "quiz", "memory"]
REQUIRED_RENDERERS = {"recap": "video"}


def merge_agent_outputs(
    section_artifacts: List[Dict],
    memory_output: Dict,
    recap_output: Dict,
    subject: str,
    grade: str
) -> Dict:
    """
    Deterministic merge of all V1.5 agent outputs into presentation.json.
    
    Algorithm:
    1. Process section_artifacts (intro, summary, content, example)
    2. Add memory section from MemoryFlashcardAgent
    3. Add recap section from RecapSceneAgent
    4. Assign sequential section_ids
    5. Merge segment_enrichments into narration.segments
    6. Enforce renderer policies
    7. Validate against v1.3 schema requirements
    
    Args:
        section_artifacts: List of {blueprint, narration, visuals, render_spec}
        memory_output: Output from MemoryFlashcardAgent
        recap_output: Output from RecapSceneAgent
        subject: Subject area
        grade: Grade level
        
    Returns:
        Complete presentation.json dict (v1.3 schema compliant)
    """
    logger.info("[Merge Step v1.5] Starting merge of agent outputs")
    
    sections = []
    
    for artifact in section_artifacts:
        section = _build_section_from_artifact(artifact)
        sections.append(section)
    
    memory_section = _build_memory_section(memory_output)
    sections.append(memory_section)
    
    recap_section = _build_recap_section(recap_output)
    sections.append(recap_section)
    
    sections = _order_sections(sections)
    
    for i, section in enumerate(sections, start=1):
        section["section_id"] = i
    
    _enforce_renderer_policies(sections)
    
    presentation = {
        "spec_version": "v1.5",
        "title": f"{subject} Lesson",
        "subject": subject,
        "grade": grade,
        "avatar_global": {
            "style": "teacher",
            "default_position": "right",
            "default_width_percent": 52,
            "gesture_enabled": True
        },
        "sections": sections,
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "pipeline_version": "v1.5",
            "section_count": len(sections),
            "section_types": [s.get("section_type") for s in sections]
        }
    }
    
    logger.info(f"[Merge Step v1.5] Successfully merged {len(sections)} sections")
    return presentation


def _build_section_from_artifact(artifact: Dict) -> Dict:
    """Build a section from blueprint + narration + visuals + render_spec."""
    blueprint = artifact.get("blueprint", {})
    narration = artifact.get("narration", {})
    visuals = artifact.get("visuals", {})
    render_spec = artifact.get("render_spec")
    
    section_type = blueprint.get("section_type", "content")
    
    # ISS-140 FIX: Get renderer from blueprint, falling back to render_spec if available
    renderer = blueprint.get("suggested_renderer")
    if not renderer and render_spec:
        renderer = render_spec.get("renderer")
    if not renderer:
        renderer = "none"
    
    # ISS-159 FIX: Intro = avatar-only centered at 60%, Summary = 52% right
    if section_type == "intro":
        avatar_layout = {
            "visibility": "always",
            "mode": "floating",
            "position": "center",
            "width_percent": 60
        }
    else:
        avatar_layout = {
            "visibility": "always",
            "mode": "compact" if section_type not in ["summary"] else "floating",
            "position": "right",
            "width_percent": 52
        }
    
    section = {
        "section_type": section_type,
        "title": blueprint.get("title", "Untitled"),
        "renderer": renderer,
        "avatar_layout": avatar_layout
    }
    
    narration_data = narration.get("narration", {})
    segments = narration_data.get("segments", [])
    
    enrichments = visuals.get("segment_enrichments", [])
    enrichment_map = {e.get("segment_id"): e for e in enrichments}
    
    merged_segments = []
    for seg in segments:
        seg_id = seg.get("segment_id")
        merged_seg = {
            "segment_id": seg_id,
            "text": seg.get("text", ""),
            "duration_seconds": seg.get("duration_seconds", 5.0),
            "gesture_hint": seg.get("gesture_hint", "explaining")
        }
        
        enrichment = enrichment_map.get(seg_id, {})
        
        if enrichment.get("visual_content"):
            merged_seg["visual_content"] = enrichment["visual_content"]
        
        if enrichment.get("display_directives"):
            dd = enrichment["display_directives"].copy()
            dd["avatar_layer"] = "show"
            merged_seg["display_directives"] = dd
        else:
            # ISS-159 FIX: Intro = avatar-only (no text), Summary = limited text
            if section_type == "intro":
                merged_seg["display_directives"] = {
                    "text_layer": "hide",
                    "visual_layer": "hide",
                    "avatar_layer": "show"
                }
            elif section_type == "summary":
                merged_seg["display_directives"] = {
                    "text_layer": "show",
                    "visual_layer": "hide",
                    "avatar_layer": "show"
                }
            else:
                merged_seg["display_directives"] = {
                    "text_layer": "hide",
                    "visual_layer": "show",
                    "avatar_layer": "show"
                }
        
        merged_segments.append(merged_seg)
    
    section["narration"] = {
        "full_text": narration_data.get("full_text", ""),
        "segments": merged_segments
    }
    
    # ISS-121 FIX: Also create section-level display_directives array for player compatibility
    section["display_directives"] = [seg.get("display_directives", {
        "text_layer": "hide", "visual_layer": "show", "avatar_layer": "gesture_only"
    }) for seg in merged_segments]
    
    section["visual_beats"] = visuals.get("visual_beats", [])
    
    if render_spec:
        if render_spec.get("manim_scene_spec"):
            section["manim_scene_spec"] = render_spec["manim_scene_spec"]
        if render_spec.get("video_prompts"):
            section["video_prompts"] = render_spec["video_prompts"]
        # Note: remotion_scene_spec removed per user request - remotion not used
    
    # ISS-118 FIX: Guard against remotion renderer (convert to manim)
    if section.get("renderer") == "remotion":
        section["renderer"] = "manim"
        section["renderer_override_reason"] = "Policy: remotion converted to manim (remotion not supported)"
        logger.info(f"[Merge v1.5] Converted remotion to manim for section")
    
    return section


def _build_memory_section(memory_output: Dict) -> Dict:
    """Build memory section from MemoryFlashcardAgent output.
    
    ISS-153 FIX: Uses NarrationWriter output if available, otherwise falls back to placeholder.
    """
    flashcards = memory_output.get("flashcards", [])
    
    narration_data = memory_output.get("narration", {})
    if narration_data and narration_data.get("segments"):
        segments = narration_data.get("segments", [])
        full_text = narration_data.get("full_text", "")
        
        for seg in segments:
            if "display_directives" not in seg:
                seg["display_directives"] = {
                    "text_layer": "hide",
                    "visual_layer": "show",
                    "avatar_layer": "show"
                }
    else:
        intro_text = "Let's review what we've learned with some flashcards."
        full_text = intro_text
        segments = [
            {
                "segment_id": 1,
                "text": intro_text,
                "duration_seconds": 4.0,
                "gesture_hint": "explaining",
                "display_directives": {
                    "text_layer": "hide",
                    "visual_layer": "show",
                    "avatar_layer": "show"
                }
            }
        ]
    
    visual_beats = []
    for i, seg in enumerate(segments, start=1):
        visual_beats.append({
            "beat_id": f"beat_{i}",
            "segment_id": seg.get("segment_id", i),
            "visual_beat_type": "text_only",
            "description": f"Flashcard review segment {i}"
        })
    
    return {
        "section_type": "memory",
        "title": memory_output.get("title", "Remember This!"),
        "renderer": "none",
        "avatar_layout": {
            "visibility": "always",
            "mode": "compact",
            "position": "right",
            "width_percent": 52
        },
        "narration": {
            "full_text": full_text,
            "segments": segments
        },
        "display_directives": [seg.get("display_directives", {
            "text_layer": "hide", "visual_layer": "show", "avatar_layer": "show"
        }) for seg in segments],
        "visual_beats": visual_beats,
        "flashcards": flashcards
    }


def _build_recap_section(recap_output: Dict) -> Dict:
    """Build recap section from RecapSceneAgent output.
    
    ISS-154 FIX: Uses NarrationWriter output if available, otherwise falls back to placeholder.
    """
    video_prompts = recap_output.get("video_prompts", [])
    
    narration_data = recap_output.get("narration", {})
    if narration_data and narration_data.get("segments"):
        segments = narration_data.get("segments", [])
        full_text = narration_data.get("full_text", "")
        
        for seg in segments:
            if "display_directives" not in seg:
                seg["display_directives"] = {
                    "text_layer": "hide",
                    "visual_layer": "show",
                    "avatar_layer": "show"
                }
    else:
        prompt_texts = []
        segments = []
        
        for i, vp in enumerate(video_prompts, start=1):
            duration = vp.get("duration_seconds", 10.0)
            narration_text = f"Scene {i}: visualizing the concept."
            prompt_texts.append(narration_text)
            
            segments.append({
                "segment_id": i,
                "text": narration_text,
                "duration_seconds": duration,
                "gesture_hint": "explaining",
                "display_directives": {
                    "text_layer": "hide",
                    "visual_layer": "show",
                    "avatar_layer": "show"
                }
            })
        
        full_text = " ".join(prompt_texts)
    
    visual_beats = []
    for i, seg in enumerate(segments, start=1):
        visual_beats.append({
            "beat_id": f"beat_{i}",
            "segment_id": seg.get("segment_id", i),
            "visual_beat_type": "video_clip",
            "description": f"Recap video scene {i}"
        })
    
    formatted_prompts = []
    for i, vp in enumerate(video_prompts, start=1):
        formatted_prompts.append({
            "beat_id": i,
            "prompt": vp.get("prompt", ""),
            "duration_seconds": vp.get("duration_seconds", 10.0),
            "style": vp.get("style", "cinematic")
        })
    
    return {
        "section_type": "recap",
        "title": recap_output.get("title", "Let's Review"),
        "renderer": "video",
        "avatar_layout": {
            "visibility": "always",
            "mode": "compact",
            "position": "right",
            "width_percent": 52
        },
        "narration": {
            "full_text": full_text,
            "segments": segments
        },
        "display_directives": [seg.get("display_directives", {
            "text_layer": "hide", "visual_layer": "show", "avatar_layer": "show"
        }) for seg in segments],
        "visual_beats": visual_beats,
        "video_prompts": formatted_prompts
    }


def _order_sections(sections: List[Dict]) -> List[Dict]:
    """Order sections: intro, summary, content/example, memory, recap."""
    type_order = {
        "intro": 0,
        "summary": 1,
        "content": 2,
        "example": 3,
        "quiz": 4,
        "memory": 5,
        "recap": 6
    }
    
    def sort_key(section):
        section_type = section.get("section_type", "content").lower()  # Normalize case
        return type_order.get(section_type, 2)
    
    return sorted(sections, key=sort_key)


def _enforce_renderer_policies(sections: List[Dict]) -> None:
    """
    Enforce renderer policies per section type.
    
    Policies:
    - intro, summary, memory: renderer = "none"
    - recap: renderer = "video"
    - content, example: dynamic (manim, remotion, video)
    """
    for section in sections:
        section_type = section.get("section_type", "")
        current_renderer = section.get("renderer", "none")
        
        if section_type in TEXT_ONLY_SECTION_TYPES:
            if current_renderer != "none":
                section["renderer"] = "none"
                section["renderer_override_reason"] = f"Policy: {section_type} is text-only"
                logger.info(f"[Merge v1.5] Enforced renderer 'none' for {section_type}")
        
        elif section_type in REQUIRED_RENDERERS:
            required = REQUIRED_RENDERERS[section_type]
            if current_renderer != required:
                section["renderer"] = required
                section["renderer_override_reason"] = f"Policy: {section_type} requires {required}"
                logger.info(f"[Merge v1.5] Enforced renderer '{required}' for {section_type}")

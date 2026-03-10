"""
Dry Run Validator - Validates all render specs before actual video generation.

ISS-078 FIX: Dry run should validate everything except actual API calls.
This module ensures all prompts, specs, and paths are complete and valid.

Validations:
1. WAN prompt word count (80+ words for v1.3)
2. Manim scene spec completeness
3. Display directives presence
4. Visual content extraction
5. Expected asset paths are determinable
"""

import re
from typing import Dict, List, Tuple, Any
from pathlib import Path

MIN_WAN_PROMPT_WORDS = 80
MIN_WAN_PROMPT_WORDS_V13 = 80

FORBIDDEN_VAGUE_PHRASES = [
    "clear diagram", "appropriate animation", "educational visualization",
    "relevant imagery", "suitable graphics", "show a diagram of",
    "illustrate the concept", "visual representation", "properly animated",
    "generic visual", "typical animation", "standard display"
]


class DryRunValidationError:
    def __init__(self, section_id: int, category: str, message: str, severity: str = "error"):
        self.section_id = section_id
        self.category = category
        self.message = message
        self.severity = severity
    
    def __str__(self):
        return f"[{self.severity.upper()}] Section {self.section_id} - {self.category}: {self.message}"


class DryRunValidationResult:
    def __init__(self):
        self.is_valid = True
        self.errors: List[DryRunValidationError] = []
        self.warnings: List[DryRunValidationError] = []
        self.summary: Dict[str, Any] = {}
    
    def add_error(self, section_id: int, category: str, message: str):
        self.is_valid = False
        self.errors.append(DryRunValidationError(section_id, category, message, "error"))
    
    def add_warning(self, section_id: int, category: str, message: str):
        self.warnings.append(DryRunValidationError(section_id, category, message, "warning"))


def count_words(text: str) -> int:
    if not text:
        return 0
    return len(text.split())


def validate_wan_prompt_words(prompt: str, section_id: int, beat_idx: int, min_words: int = MIN_WAN_PROMPT_WORDS) -> Tuple[bool, str]:
    """Validate WAN prompt has sufficient word count."""
    word_count = count_words(prompt)
    if word_count < min_words:
        return False, f"Beat {beat_idx}: Prompt has {word_count} words, minimum {min_words} required"
    return True, None


def check_forbidden_phrases(prompt: str) -> List[str]:
    """Check for vague/forbidden phrases in prompt."""
    found = []
    prompt_lower = prompt.lower()
    for phrase in FORBIDDEN_VAGUE_PHRASES:
        if phrase in prompt_lower:
            found.append(phrase)
    return found


def validate_video_prompts(section: dict, result: DryRunValidationResult, min_words: int = MIN_WAN_PROMPT_WORDS):
    """Validate video_prompts array for a section.
    
    v1.3 REQUIRES: Each beat must have min_words (80 for v1.3 per Director Bible).
    This function uses the passed min_words for BOTH per-beat AND average checks.
    """
    section_id = section.get("section_id") or section.get("id", 0)
    video_prompts = section.get("video_prompts", [])
    section_type = section.get("section_type", "content")
    
    if not video_prompts:
        if section_type in ["content", "example"] and section.get("renderer") in ["video", "wan", "wan_video"]:
            result.add_error(section_id, "video_prompts", "Video section missing video_prompts array")
        return
    
    total_words = 0
    for i, vp in enumerate(video_prompts):
        prompt = vp.get("prompt", "") if isinstance(vp, dict) else str(vp)
        word_count = count_words(prompt)
        total_words += word_count
        
        if word_count < min_words:
            result.add_error(
                section_id, "video_prompts", 
                f"Beat {i}: Prompt has {word_count} words, REQUIRES {min_words}+ words"
            )
        
        forbidden = check_forbidden_phrases(prompt)
        if forbidden:
            result.add_warning(section_id, "video_prompts", f"Beat {i}: Contains vague phrases: {forbidden[:3]}")
    
    if len(video_prompts) > 0:
        avg_words = total_words / len(video_prompts)
        if avg_words < min_words:
            result.add_error(
                section_id, "video_prompts",
                f"Average prompt length ({avg_words:.0f} words) below minimum ({min_words})"
            )


def validate_manim_scene_spec(section: dict, result: DryRunValidationResult):
    """Validate manim_scene_spec completeness."""
    section_id = section.get("section_id") or section.get("id", 0)
    renderer = section.get("renderer", "")
    section_type = section.get("section_type", "content")
    
    if renderer != "manim" or section_type not in ["content", "example"]:
        return
    
    manim_spec = section.get("manim_scene_spec")
    # ISS-162 FIX: Check nested render_spec as well (V2.5 standard)
    if not manim_spec:
        manim_spec = section.get("render_spec", {}).get("manim_scene_spec")
        
    if not manim_spec:
        result.add_error(section_id, "manim_scene_spec", "Manim section missing manim_scene_spec")
        return
    
    
    # [DEBUG] Diagnose V2.5 Validation Failure
    print(f"[DEBUG VALIDATOR] Section {section_id} Manim Spec Type: {type(manim_spec)}")
    if isinstance(manim_spec, dict):
        print(f"[DEBUG VALIDATOR] Keys: {list(manim_spec.keys())}")
    else:
        print(f"[DEBUG VALIDATOR] Content Start: {str(manim_spec)[:50]}...")

    # V2.5 Support: Manim Spec can be a string (Prompt) or a Dict (V1.2 Blueprint)
    if isinstance(manim_spec, str):
        # V2.5 String Mode -> Just check word count
        word_count = count_words(manim_spec)
        if word_count < 80:
             result.add_error(section_id, "manim_scene_spec", f"Manim spec is too short ({word_count} words). Minimum 80.")
        return # Skip structure checks for string mode
        
    # V2.5 Generated Code Mode -> If we have manim_code, we are good!
    if isinstance(manim_spec, dict) and (manim_spec.get("manim_code") or manim_spec.get("code")):
        return
        
    # V1.2 Dict Mode -> Check keys
    objects = manim_spec.get("objects", [])
    equations = manim_spec.get("equations", [])
    animation_seq = manim_spec.get("animation_sequence", [])
    
    if not objects and not equations:
        result.add_error(section_id, "manim_scene_spec", "No objects or equations defined")
    
    if not animation_seq:
        result.add_error(section_id, "manim_scene_spec", "No animation_sequence defined")
    
    for i, anim in enumerate(animation_seq):
        if not anim.get("type"):
            result.add_warning(section_id, "manim_scene_spec", f"Animation {i} missing 'type' field")
        if not anim.get("target") and anim.get("type") not in ["wait", "fade_out_all"]:
            result.add_warning(section_id, "manim_scene_spec", f"Animation {i} missing 'target' field")


def validate_display_directives(section: dict, result: DryRunValidationResult):
    """Validate display_directives presence for v1.3."""
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "content")
    
    narration = section.get("narration", {})
    segments = narration.get("segments", []) if isinstance(narration, dict) else section.get("narration_segments", [])
    
    if not segments:
        return
    
    missing_count = 0
    for i, seg in enumerate(segments):
        directives = seg.get("display_directives")
        if not directives:
            missing_count += 1
        elif isinstance(directives, dict):
            required_layers = ["text_layer", "visual_layer", "avatar_layer"]
            for layer in required_layers:
                if layer not in directives:
                    result.add_warning(section_id, "display_directives", f"Segment {i} missing '{layer}'")
    
    if missing_count > 0:
        result.add_error(
            section_id, "display_directives",
            f"{missing_count}/{len(segments)} segments missing display_directives"
        )


def validate_visual_content(section: dict, result: DryRunValidationResult):
    """Validate visual_content extraction for content sections (ISS-077)."""
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "content")
    
    if section_type not in ["content", "example"]:
        return
    
    visual_content = section.get("visual_content", {})
    narration = section.get("narration", {})
    segments = narration.get("segments", []) if isinstance(narration, dict) else section.get("narration_segments", [])
    
    has_section_level = bool(visual_content.get("bullet_points") or visual_content.get("formula"))
    
    segment_visual_content_count = 0
    for seg in segments:
        seg_vc = seg.get("visual_content", {})
        if seg_vc and (seg_vc.get("bullet_points") or seg_vc.get("formula") or seg_vc.get("labels")):
            segment_visual_content_count += 1
    
    if not has_section_level and segment_visual_content_count == 0:
        result.add_warning(
            section_id, "visual_content",
            "No visual_content defined (bullet_points, formula). Text display will fall back to narration."
        )


def validate_expected_paths(section: dict, output_dir: str, result: DryRunValidationResult):
    """Validate that expected video paths can be determined."""
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "content")
    renderer = section.get("renderer", "")
    
    if renderer == "none" or section_type in ["intro", "summary", "memory"]:
        return
    
    expected_paths = []
    videos_dir = Path(output_dir) / "videos"
    
    if section_type == "recap":
        recap_scenes = section.get("recap_scenes", []) or section.get("visual_beats", [])
        for i in range(len(recap_scenes)):
            expected_paths.append(videos_dir / f"recap_{section_id}_scene_{i+1}.mp4")
    elif renderer == "manim":
        expected_paths.append(videos_dir / f"topic_{section_id}.mp4")
    else:
        video_prompts = section.get("video_prompts", [])
        visual_beats = section.get("visual_beats", [])
        num_beats = max(len(video_prompts), len(visual_beats), 1)
        for i in range(num_beats):
            expected_paths.append(videos_dir / f"topic_{section_id}_beat_{i}.mp4")
    
    result.summary[f"section_{section_id}_expected_videos"] = [str(p) for p in expected_paths]


def validate_renderer_subject_match(section: dict, subject: str, result: DryRunValidationResult):
    """Validate renderer matches subject matter (ISS-075)."""
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "content")
    renderer = section.get("renderer", "")
    
    subject_lower = (subject or "").lower()
    
    if subject_lower == "biology" and renderer == "manim":
        result.add_error(
            section_id, "renderer_subject",
            "Biology content must use 'video' renderer, not 'manim'"
        )
    
    if section_type == "recap" and renderer not in ["video", "wan", "wan_video", "none", ""]:
        result.add_error(
            section_id, "renderer_subject",
            f"Recap sections must use 'video' renderer, got '{renderer}'"
        )


def validate_presentation_dry_run(
    presentation: dict,
    output_dir: str,
    strict_v13: bool = True
) -> DryRunValidationResult:
    """
    Run comprehensive dry run validation on presentation.
    
    Args:
        presentation: The presentation dict
        output_dir: Expected output directory
        strict_v13: If True, enforce v1.3 requirements (80+ words for WAN per Director Bible)
    
    Returns:
        DryRunValidationResult with all errors and warnings
    """
    result = DryRunValidationResult()
    sections = presentation.get("sections", [])
    subject = presentation.get("subject", "")
    spec_version = presentation.get("spec_version", "")
    
    is_v13 = spec_version.startswith("v1.3") or strict_v13
    min_wan_words = MIN_WAN_PROMPT_WORDS_V13 if is_v13 else MIN_WAN_PROMPT_WORDS
    
    result.summary["total_sections"] = len(sections)
    result.summary["spec_version"] = spec_version
    result.summary["subject"] = subject
    result.summary["min_wan_words"] = min_wan_words
    
    # Check if this is V2.5 Director Mode (uses markdown_pointer instead of display_directives)
    generated_by = presentation.get("metadata", {}).get("generated_by", "")
    is_v25_director = generated_by == "v1.5-v2.5-director"
    
    if is_v25_director:
        result.add_warning(0, "validation", "V2.5 Director Mode detected - Using Strict V2.5 Validator")
        try:
            from core.validators.v25_validator import V25Validator
            
            # 1. Validate Global Sections
            global_errors = V25Validator.validate_global_response(presentation)
            for err in global_errors:
                result.add_error(0, "v2.5_global", err)
                
            # 2. Validate Content Sections
            # We don't have source text easily here for pointer check, but we can check structure
            for section in sections:
                if section.get("section_type") in ["content", "example", "quiz"]:
                    # Wrap single section in dict for validator compatibility
                    chunk_data = {"sections": [section]} 
                    chunk_errors = V25Validator.validate_content_chunk(chunk_data, source_text="") # Empty source skips pointer check
                    for err in chunk_errors:
                         result.add_error(section.get("id"), "v2.5_content", err)
            
            # If V2.5, we SKIP the legacy checks below to avoid conflicts
            result.summary["error_count"] = len(result.errors)
            result.summary["warning_count"] = len(result.warnings)
            return result
            
        except ImportError:
            result.add_warning(0, "system", "Could not import V25Validator - falling back to legacy checks")
    
    if is_v25_director:
        result.add_warning(0, "validation", "V2.5 Director Mode detected - skipping display_directives validation")
    
    for section in sections:
        section_type = section.get("section_type", "content")
        renderer = section.get("renderer", "")
        
        # Skip display_directives check for V2.5 Director (uses markdown_pointer instead)
        if not is_v25_director:
            validate_display_directives(section, result)
        
        validate_renderer_subject_match(section, subject, result)
        
        if renderer in ["video", "wan", "wan_video"]:
            validate_video_prompts(section, result, min_words=min_wan_words)
        
        if renderer == "manim":
            validate_manim_scene_spec(section, result)
        
        validate_visual_content(section, result)
        
        validate_expected_paths(section, output_dir, result)
    
    result.summary["error_count"] = len(result.errors)
    result.summary["warning_count"] = len(result.warnings)
    
    return result


def format_validation_report(result: DryRunValidationResult) -> str:
    """Format validation result into a readable report."""
    lines = [
        "=" * 60,
        "DRY RUN VALIDATION REPORT",
        "=" * 60,
        f"Status: {'PASS' if result.is_valid else 'FAIL'}",
        f"Errors: {len(result.errors)}",
        f"Warnings: {len(result.warnings)}",
        ""
    ]
    
    if result.errors:
        lines.append("ERRORS:")
        for err in result.errors:
            lines.append(f"  {err}")
        lines.append("")
    
    if result.warnings:
        lines.append("WARNINGS:")
        for warn in result.warnings:
            lines.append(f"  {warn}")
        lines.append("")
    
    lines.append("=" * 60)
    return "\n".join(lines)

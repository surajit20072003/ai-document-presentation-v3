"""
V3 Recap Agent

Specialized agent for recap section — outputs a DYNAMIC number of image_to_video beats
(LLM decides count based on content; each beat is exactly 15 seconds / 40-60 words).
Each beat must have image_prompt_start (100+ words), image_prompt_end (100+ words),
video_prompt (80+ words), and duration: 15.
"""
import logging
from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent, STRONG_MODEL

logger = logging.getLogger(__name__)


class RecapSceneAgent(BaseAgent):
    """
    Recap Scene Agent — Creates image_to_video beats for the recap section.

    Input: source_markdown, subject, key_concepts
    Output: section_id, section_type, title, image_to_video_beats (dynamic count, each 15s)
    """

    name = "RecapScene"
    system_prompt_file = "recap_scene_system_v1.5.txt"
    user_prompt_file = "recap_scene_user_v1.5.txt"
    model = STRONG_MODEL
    temperature = 0.5
    structural_retries = 2
    semantic_retries = 2

    BANNED_PHRASES = [
        "etc", "and more", "various", "beautiful", "amazing",
        "stunning", "conceptual visualization", "dynamic visuals"
    ]

    def validate_structural(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate recap image_to_video_beats structure."""
        errors = []

        if output.get("section_type") != "recap":
            errors.append("section_type must be 'recap'")

        beats = output.get("image_to_video_beats", [])
        if not beats:
            # Also accept legacy video_prompts (fallback only)
            if not output.get("video_prompts"):
                errors.append("Missing 'image_to_video_beats' array")
                return False, errors
            else:
                logger.warning("[RecapScene] Received legacy video_prompts — expected image_to_video_beats")
                return True, []

        if not isinstance(beats, list):
            errors.append("'image_to_video_beats' must be an array")
            return False, errors

        if len(beats) < 1:
            errors.append("Must have at least 1 beat in image_to_video_beats")

        for i, beat in enumerate(beats):
            if "beat_id" not in beat:
                errors.append(f"image_to_video_beats[{i}]: missing 'beat_id'")
            if "image_prompt_start" not in beat:
                errors.append(f"image_to_video_beats[{i}]: missing 'image_prompt_start'")
            if "image_prompt_end" not in beat:
                errors.append(f"image_to_video_beats[{i}]: missing 'image_prompt_end'")
            if "video_prompt" not in beat:
                errors.append(f"image_to_video_beats[{i}]: missing 'video_prompt'")
            if "duration" not in beat:
                errors.append(f"image_to_video_beats[{i}]: missing 'duration'")

        return len(errors) == 0, errors

    def validate_semantic(self, output: Dict[str, Any], input_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate image_to_video beat quality — 100+ words for image prompts, 80+ words for video_prompt."""
        errors = []
        warnings = []

        beats = output.get("image_to_video_beats", [])
        if not beats:
            # Skip semantic for legacy format
            return True, []

        for i, beat in enumerate(beats):
            img_start = beat.get("image_prompt_start", "")
            img_end = beat.get("image_prompt_end", "")
            vid_prompt = beat.get("video_prompt", "")
            duration = beat.get("duration", 0)

            start_wc = len(img_start.split())
            end_wc = len(img_end.split())
            vid_wc = len(vid_prompt.split())

            if start_wc < 100:
                errors.append(f"beats[{i}] image_prompt_start: {start_wc} words (min 100)")
            if end_wc < 100:
                errors.append(f"beats[{i}] image_prompt_end: {end_wc} words (min 100)")
            if vid_wc < 80:
                errors.append(f"beats[{i}] video_prompt: {vid_wc} words (min 80)")

            if len(vid_prompt) > 800:
                warnings.append(f"beats[{i}] video_prompt: {len(vid_prompt)} chars — may exceed API limit (800)")

            if duration != 15:
                warnings.append(f"beats[{i}] duration={duration} — expected 15s")

            for phrase in self.BANNED_PHRASES:
                for field, text in [("image_prompt_start", img_start), ("video_prompt", vid_prompt)]:
                    if phrase.lower() in text.lower():
                        warnings.append(f"beats[{i}] {field}: contains vague phrase '{phrase}'")

        if warnings:
            logger.warning(f"[RecapScene] Quality warnings: {warnings}")

        return len(errors) == 0, errors

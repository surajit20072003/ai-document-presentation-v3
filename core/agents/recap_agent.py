"""
V1.5 Recap Scene Agent (REQ-015)

Specialized agent for recap section - outputs exactly 5 video prompts (80-150 words, max 800 chars each).
"""
import logging
from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent, STRONG_MODEL

logger = logging.getLogger(__name__)


class RecapSceneAgent(BaseAgent):
    """
    Recap Scene Agent - Creates video prompts for the recap section.
    
    Input: source_markdown, subject, key_concepts
    Output: section_id, section_type, title, video_prompts (exactly 5, 80-150 words each, max 800 chars)
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
        """Validate recap video prompts structure."""
        errors = []
        
        if output.get("section_type") != "recap":
            errors.append("section_type must be 'recap'")
        
        if "video_prompts" not in output:
            errors.append("Missing 'video_prompts' array")
            return False, errors
        
        prompts = output.get("video_prompts", [])
        if not isinstance(prompts, list):
            errors.append("'video_prompts' must be an array")
            return False, errors
        
        if len(prompts) != 5:
            errors.append(f"Must have exactly 5 video_prompts, got {len(prompts)}")
        
        for i, p in enumerate(prompts):
            if "prompt_id" not in p:
                errors.append(f"video_prompt {i}: missing 'prompt_id'")
            if "prompt" not in p:
                errors.append(f"video_prompt {i}: missing 'prompt'")
            if "duration_seconds" not in p:
                errors.append(f"video_prompt {i}: missing 'duration_seconds'")
            if "style" not in p:
                errors.append(f"video_prompt {i}: missing 'style'")
        
        return len(errors) == 0, errors
    
    def validate_semantic(self, output: Dict[str, Any], input_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate video prompt quality - 80-150 words, max 800 chars, no banned phrases."""
        errors = []
        warnings = []
        
        prompts = output.get("video_prompts", [])
        
        for i, p in enumerate(prompts):
            prompt_text = p.get("prompt", "")
            word_count = len(prompt_text.split())
            char_count = len(prompt_text)
            
            if word_count < 80:
                errors.append(f"video_prompt {i}: only {word_count} words (min 80)")
            elif word_count < 100:
                warnings.append(f"video_prompt {i}: only {word_count} words (recommended 100+)")
            
            if char_count > 800:
                errors.append(f"video_prompt {i}: {char_count} chars exceeds API limit (max 800)")
            
            for phrase in self.BANNED_PHRASES:
                if phrase.lower() in prompt_text.lower():
                    warnings.append(f"video_prompt {i}: contains vague phrase '{phrase}'")
        
        ids = [p.get("prompt_id") for p in prompts]
        if ids != list(range(1, 6)):
            errors.append(f"prompt_ids must be 1-5 in order, got {ids}")
        
        if warnings:
            logger.warning(f"[RecapScene] Quality warnings: {warnings}")
        
        return len(errors) == 0, errors

"""
V1.5 SpecialSectionsAgent - Combined Memory + Recap

Optimization: Combines MemoryFlashcardAgent + RecapSceneAgent into single LLM call.
This reduces 2 LLM calls to 1, generating both memory flashcards and recap video scenes.

Memory Section: 3 flashcards with mnemonic format ("3 Keys to Remember")
Recap Section: 5 video prompts for WAN generation (80-150 words, max 800 chars)

Output is compatible with existing MergeStep - produces same fields.
"""
import logging
from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent, STRONG_MODEL

logger = logging.getLogger(__name__)


class SpecialSectionsAgent(BaseAgent):
    """
    SpecialSectionsAgent - Creates Memory flashcards + Recap video prompts.
    
    Input: source_markdown, subject, key_concepts
    Output: memory_section (3 flashcards), recap_section (5 video prompts + narration)
    
    Replaces: MemoryFlashcardAgent + RecapSceneAgent (2 LLM calls → 1)
    """
    
    name = "SpecialSections"
    system_prompt_file = "special_sections_system_v1.5.txt"
    user_prompt_file = "special_sections_user_v1.5.txt"
    output_schema_file = "special_sections.schema.json"
    model = STRONG_MODEL
    temperature = 0.5
    structural_retries = 2
    semantic_retries = 2
    
    BANNED_PHRASES = [
        "etc", "and more", "various", "beautiful", "amazing", 
        "stunning", "conceptual visualization", "dynamic visuals"
    ]
    
    def validate_structural(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate combined memory + recap structure."""
        errors = []
        
        if "memory_section" not in output:
            errors.append("Missing 'memory_section' object")
        else:
            memory = output.get("memory_section", {})
            
            if memory.get("section_type") != "memory":
                errors.append("memory_section.section_type must be 'memory'")
            
            if "title" not in memory:
                errors.append("memory_section: missing 'title'")
            
            if "flashcards" not in memory:
                errors.append("memory_section: missing 'flashcards' array")
            else:
                flashcards = memory.get("flashcards", [])
                if not isinstance(flashcards, list):
                    errors.append("memory_section: 'flashcards' must be an array")
                elif len(flashcards) != 3:
                    errors.append(f"memory_section: must have exactly 3 flashcards (got {len(flashcards)})")
                else:
                    for i, card in enumerate(flashcards):
                        if "flashcard_id" not in card:
                            errors.append(f"Flashcard {i}: missing 'flashcard_id'")
                        if "front" not in card:
                            errors.append(f"Flashcard {i}: missing 'front'")
                        if "back" not in card:
                            errors.append(f"Flashcard {i}: missing 'back'")
                        if "category" not in card:
                            errors.append(f"Flashcard {i}: missing 'category'")
            
            if "narration" not in memory:
                errors.append("memory_section: missing 'narration' object")
            else:
                narr = memory.get("narration", {})
                if "full_text" not in narr:
                    errors.append("memory_section.narration: missing 'full_text'")
                if "segments" not in narr:
                    errors.append("memory_section.narration: missing 'segments'")
                elif len(narr.get("segments", [])) != 3:
                    errors.append(f"memory_section: must have exactly 3 narration segments (got {len(narr.get('segments', []))})")
        
        if "recap_section" not in output:
            errors.append("Missing 'recap_section' object")
        else:
            recap = output.get("recap_section", {})
            
            if recap.get("section_type") != "recap":
                errors.append("recap_section.section_type must be 'recap'")
            
            if "title" not in recap:
                errors.append("recap_section: missing 'title'")
            
            if "video_prompts" not in recap:
                errors.append("recap_section: missing 'video_prompts' array")
            else:
                prompts = recap.get("video_prompts", [])
                if not isinstance(prompts, list):
                    errors.append("recap_section: 'video_prompts' must be an array")
                elif len(prompts) != 5:
                    errors.append(f"recap_section: must have exactly 5 video_prompts (got {len(prompts)})")
                else:
                    for i, p in enumerate(prompts):
                        if "prompt_id" not in p:
                            errors.append(f"video_prompt {i}: missing 'prompt_id'")
                        if "prompt" not in p:
                            errors.append(f"video_prompt {i}: missing 'prompt'")
                        if "duration_seconds" not in p:
                            errors.append(f"video_prompt {i}: missing 'duration_seconds'")
                        if "style" not in p:
                            errors.append(f"video_prompt {i}: missing 'style'")
            
            if "narration" not in recap:
                errors.append("recap_section: missing 'narration' object")
            else:
                narr = recap.get("narration", {})
                if "full_text" not in narr:
                    errors.append("recap_section.narration: missing 'full_text'")
                if "segments" not in narr:
                    errors.append("recap_section.narration: missing 'segments'")
                elif len(narr.get("segments", [])) != 5:
                    errors.append(f"recap_section: must have exactly 5 narration segments to match 5 videos (got {len(narr.get('segments', []))})")
        
        return len(errors) == 0, errors
    
    def validate_semantic(self, output: Dict[str, Any], input_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate semantic quality of memory and recap content."""
        errors = []
        warnings = []
        
        memory = output.get("memory_section", {})
        flashcards = memory.get("flashcards", [])
        
        for i, card in enumerate(flashcards):
            front = card.get("front", "")
            back = card.get("back", "")
            
            if len(front) < 10:
                errors.append(f"Flashcard {i}: front too short (min 10 chars)")
            if len(back) < 10:
                errors.append(f"Flashcard {i}: back too short (min 10 chars)")
            if len(front) > 150:
                errors.append(f"Flashcard {i}: front too long (max 150 chars)")
            if len(back) > 250:
                errors.append(f"Flashcard {i}: back too long (max 250 chars)")
        
        flashcard_ids = [c.get("flashcard_id") for c in flashcards]
        if flashcard_ids != list(range(1, 4)):
            errors.append(f"flashcard_ids must be 1-3 in order, got {flashcard_ids}")
        
        memory_narr = memory.get("narration", {})
        memory_full_text = memory_narr.get("full_text", "")
        memory_segments = memory_narr.get("segments", [])
        memory_word_count = len(memory_full_text.split())
        
        if memory_word_count < 30:
            errors.append(f"Memory narration too short: {memory_word_count} words (min 30)")
        if memory_word_count > 100:
            errors.append(f"Memory narration too long: {memory_word_count} words (max 100)")
        
        memory_seg_words = sum(len(s.get("text", "").split()) for s in memory_segments)
        if abs(memory_seg_words - memory_word_count) > 5:
            errors.append(f"Memory segment words ({memory_seg_words}) don't match full_text ({memory_word_count})")
        
        recap = output.get("recap_section", {})
        prompts = recap.get("video_prompts", [])
        
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
        
        prompt_ids = [p.get("prompt_id") for p in prompts]
        if prompt_ids != list(range(1, 6)):
            errors.append(f"prompt_ids must be 1-5 in order, got {prompt_ids}")
        
        recap_narr = recap.get("narration", {})
        recap_full_text = recap_narr.get("full_text", "")
        recap_segments = recap_narr.get("segments", [])
        recap_word_count = len(recap_full_text.split())
        
        if recap_word_count < 150:
            errors.append(f"Recap narration too short: {recap_word_count} words (min 150)")
        if recap_word_count > 350:
            errors.append(f"Recap narration too long: {recap_word_count} words (max 350)")
        
        recap_seg_words = sum(len(s.get("text", "").split()) for s in recap_segments)
        if abs(recap_seg_words - recap_word_count) > 10:
            errors.append(f"Recap segment words ({recap_seg_words}) don't match full_text ({recap_word_count})")
        
        if warnings:
            logger.warning(f"[SpecialSections] Quality warnings: {warnings}")
        
        return len(errors) == 0, errors

"""
V1.5 Memory Flashcard Agent (REQ-014)

Specialized agent for memory section - outputs exactly 5 flashcards.
"""
from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent


class MemoryFlashcardAgent(BaseAgent):
    """
    Memory Flashcard Agent - Creates flashcards for the memory section.
    
    Input: source_markdown, subject
    Output: section_id, section_type, title, flashcards (exactly 5)
    """
    
    name = "MemoryFlashcard"
    system_prompt_file = "memory_flashcard_system_v1.5.txt"
    user_prompt_file = "memory_flashcard_user_v1.5.txt"
    model = "google/gemini-2.5-flash"
    temperature = 0.3
    
    def validate_structural(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate flashcard structure."""
        errors = []
        
        if output.get("section_type") != "memory":
            errors.append("section_type must be 'memory'")
        
        if "flashcards" not in output:
            errors.append("Missing 'flashcards' array")
            return False, errors
        
        flashcards = output.get("flashcards", [])
        if not isinstance(flashcards, list):
            errors.append("'flashcards' must be an array")
            return False, errors
        
        if len(flashcards) != 5:
            errors.append(f"Must have exactly 5 flashcards, got {len(flashcards)}")
        
        for i, card in enumerate(flashcards):
            if "flashcard_id" not in card:
                errors.append(f"Flashcard {i}: missing 'flashcard_id'")
            if "front" not in card:
                errors.append(f"Flashcard {i}: missing 'front'")
            if "back" not in card:
                errors.append(f"Flashcard {i}: missing 'back'")
            if "category" not in card:
                errors.append(f"Flashcard {i}: missing 'category'")
        
        return len(errors) == 0, errors
    
    def validate_semantic(self, output: Dict[str, Any], input_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate flashcard content quality."""
        errors = []
        
        flashcards = output.get("flashcards", [])
        
        for i, card in enumerate(flashcards):
            front = card.get("front", "")
            back = card.get("back", "")
            
            if len(front) < 10:
                errors.append(f"Flashcard {i}: front too short (min 10 chars)")
            if len(back) < 10:
                errors.append(f"Flashcard {i}: back too short (min 10 chars)")
            if len(front) > 200:
                errors.append(f"Flashcard {i}: front too long (max 200 chars)")
            if len(back) > 300:
                errors.append(f"Flashcard {i}: back too long (max 300 chars)")
        
        ids = [c.get("flashcard_id") for c in flashcards]
        if ids != list(range(1, 6)):
            errors.append(f"flashcard_ids must be 1-5 in order, got {ids}")
        
        return len(errors) == 0, errors

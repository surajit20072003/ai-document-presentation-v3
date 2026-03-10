"""
Tier 2 - SEMANTIC RETRY Validator (Repairable Content Gaps)

Purpose: Fix content completeness once structure is correct.
If Tier 2 fails → trigger SEMANTIC RETRY (max 1).

Tier-2 checks (repairable):
- content narration < 150 words
- example narration < 100 words
- recap narration < 200 or > 500 words
- formula mentioned but no visual beat

These are LLM-expandable problems, not structural errors.
Tier-2 failures preserve structure, only expand/add missing content.
"""

import re
from typing import List, Dict, Any

CONTENT_MIN_WORDS = 150
EXAMPLE_MIN_WORDS = 100
RECAP_MIN_WORDS = 200
RECAP_MAX_WORDS = 500

FORMULA_PATTERNS = [
    r'F\s*=\s*m\s*[*×·]\s*a',
    r'E\s*=\s*m\s*c\s*²',
    r'v\s*=\s*u\s*[+\-]\s*a\s*t',
    r's\s*=\s*ut\s*[+\-]',
    r'[A-Z]\s*=\s*[A-Z0-9\s\+\-\*/\^]{3,}',
    r'\\frac\{',
    r'\\sum',
    r'\\int',
    r'\bformula\b',
    r'\bequation\b',
    r'\bcalculate the\b',
    r'\bcompute the\b',
    r'\bderivation\b',
]


class SemanticError:
    """Semantic validation error - triggers content retry."""
    def __init__(self, code: str, section_id: int, details: str, fix_hint: str = ""):
        self.code = code
        self.section_id = section_id
        self.details = details
        self.fix_hint = fix_hint
    
    def __str__(self):
        hint = f" [Fix: {self.fix_hint}]" if self.fix_hint else ""
        return f"[SEMANTIC] {self.code} (section {self.section_id}): {self.details}{hint}"


def validate_semantic(presentation: dict) -> List[SemanticError]:
    """
    Run all Tier-2 semantic checks.
    
    Returns list of SemanticError (empty if valid).
    """
    errors = []
    sections = presentation.get("sections", [])
    
    for section in sections:
        errors.extend(_check_narration_word_counts(section))
        errors.extend(_check_formula_visualization(section))
    
    return errors


def _count_words(text: str) -> int:
    """Count words in text."""
    if not text:
        return 0
    return len(text.split())


def _get_narration_text(section: Dict) -> str:
    """Extract full narration text from section."""
    narration = section.get("narration", "")
    
    if isinstance(narration, dict):
        full_text = narration.get("full_text", "")
        if full_text:
            return full_text
        segments = narration.get("segments", [])
        return " ".join(seg.get("text", "") for seg in segments)
    
    return narration or ""


def _check_narration_word_counts(section: Dict) -> List[SemanticError]:
    """Check minimum/maximum word counts per section type."""
    errors = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "")
    
    narration_text = _get_narration_text(section)
    word_count = _count_words(narration_text)
    
    if section_type == "content":
        if word_count < CONTENT_MIN_WORDS:
            errors.append(SemanticError(
                "content_narration_below_minimum",
                section_id,
                f"Content section has {word_count} words, minimum is {CONTENT_MIN_WORDS}",
                f"Expand narration by {CONTENT_MIN_WORDS - word_count} words"
            ))
    
    if section_type == "example":
        if word_count < EXAMPLE_MIN_WORDS:
            errors.append(SemanticError(
                "example_narration_below_minimum",
                section_id,
                f"Example section has {word_count} words, minimum is {EXAMPLE_MIN_WORDS}",
                f"Expand narration by {EXAMPLE_MIN_WORDS - word_count} words"
            ))
    
    if section_type == "recap":
        narration = section.get("narration", {})
        if isinstance(narration, dict):
            segments = narration.get("segments", [])
            total_words = sum(_count_words(seg.get("text", "")) for seg in segments)
        else:
            recap_scenes = section.get("recap_scenes", []) or section.get("visual_beats", [])
            total_words = sum(_count_words(scene.get("narration", "")) for scene in recap_scenes)
        
        if total_words < RECAP_MIN_WORDS:
            errors.append(SemanticError(
                "recap_narration_below_minimum",
                section_id,
                f"Recap total narration is {total_words} words, minimum is {RECAP_MIN_WORDS}",
                f"Expand narration by {RECAP_MIN_WORDS - total_words} words"
            ))
        
        if total_words > RECAP_MAX_WORDS:
            errors.append(SemanticError(
                "recap_narration_above_maximum",
                section_id,
                f"Recap total narration is {total_words} words, maximum is {RECAP_MAX_WORDS}",
                f"Reduce narration by {total_words - RECAP_MAX_WORDS} words"
            ))
    
    return errors


def _check_formula_in_narration(narration: str) -> bool:
    """Check if narration mentions formulas/equations."""
    if not narration:
        return False
    for pattern in FORMULA_PATTERNS:
        if re.search(pattern, narration, re.IGNORECASE):
            return True
    return False


def _check_formula_visualization(section: Dict) -> List[SemanticError]:
    """Check that mentioned formulas have visual representation."""
    errors = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "")
    
    if section_type not in ["content", "example"]:
        return errors
    
    narration_text = _get_narration_text(section)
    
    if not _check_formula_in_narration(narration_text):
        return errors
    
    has_formula_visual = False
    
    section_manim_spec = section.get("manim_scene_spec", {})
    if section_manim_spec:
        objects = section_manim_spec.get("objects", [])
        for obj in objects:
            if obj.get("type") == "equation" or obj.get("properties", {}).get("latex"):
                has_formula_visual = True
                break
    
    if not has_formula_visual:
        visual_beats = section.get("visual_beats", [])
        for beat in visual_beats:
            if not isinstance(beat, dict):
                continue
            labels = beat.get("labels_and_text", "") or beat.get("description", "")
            manim_spec = beat.get("manim_scene_spec", {})
            equations = manim_spec.get("equations", []) if manim_spec else []
            
            if equations or re.search(r'[a-zA-Z]\s*=', labels):
                has_formula_visual = True
                break
    
    if not has_formula_visual:
        errors.append(SemanticError(
            "formula_mentioned_but_not_visualized",
            section_id,
            "Narration mentions formulas/equations but no visual beat shows them",
            "Add visual beat with equation/formula visualization"
        ))
    
    return errors


def format_semantic_errors(errors: List[SemanticError]) -> str:
    """Format semantic errors for retry prompt."""
    if not errors:
        return ""
    
    lines = ["SEMANTIC ERRORS (Tier 2 - Content Retry):"]
    for err in errors:
        lines.append(f"  - {err}")
    return "\n".join(lines)

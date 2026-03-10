"""
WAN Prompt Quality Validator - Ensures video prompts are specific enough for quality generation.

CRITICAL: This module validates that WAN (video) prompts are concrete and actionable,
not vague or abstract. Vague prompts lead to poor video generation.

Validation checks:
1. Banned vague phrases detection
2. Minimum prompt length
3. Required specificity elements (subject, action, context)

ISS-076 FIX: Added hard_fail_on_short_prompts() for production enforcement.
"""

import re
from typing import List, Dict, Tuple


# ISS-120: Updated from 300 to 80 to match new 80-150 word prompt limits
MIN_WAN_PROMPT_WORDS = 80
MAX_WAN_PROMPT_WORDS = 150
MIN_WAN_PROMPT_WORDS_V13 = 80  # Legacy alias for backwards compatibility


class WanPromptHardFailError(Exception):
    """Raised when WAN prompt validation fails hard (no fallback allowed)."""
    def __init__(self, section_id: int, message: str):
        self.section_id = section_id
        super().__init__(f"Section {section_id}: {message}")


BANNED_VAGUE_PHRASES = [
    "something like",
    "kind of",
    "sort of",
    "maybe show",
    "perhaps",
    "some sort of",
    "somehow",
    "in some way",
    "various things",
    "different elements",
    "multiple aspects",
    "general concept",
    "abstract representation",
    "symbolic visualization",
    "conceptual imagery",
    "vague outline",
    "rough idea",
    "generic scene",
    "unspecified",
    "etc",
    "and so on",
    "and more",
    "things like that",
    "stuff like",
    "whatever",
    "anything",
    "everything",
]

QUALITY_INDICATORS = [
    r"\b(zoom|pan|fade|transition|close-up|wide shot|medium shot)\b",
    r"\b(left|right|center|top|bottom|foreground|background)\b",
    r"\b(slowly|quickly|gradually|smoothly|rapidly)\b",
    r"\b(color|colour|bright|dark|glow|shadow|light)\b",
    r"\b(animate|move|rotate|transform|morph|grow|shrink)\b",
]

MIN_PROMPT_LENGTH = 50
MAX_PROMPT_LENGTH = 800  # ISS-120: Increased to match API limit

# Generic expansion sentences used to pad short prompts
WAN_GENERIC_EXPANSIONS = [
    "The scene is rendered in high-definition cinematic quality with professional lighting.",
    "Smooth camera movements guide the viewer through each visual element.",
    "Colors are vibrant and carefully chosen to enhance educational clarity.",
    "The animation uses clear visual hierarchy to maintain viewer focus.",
    "Transitions between elements are fluid and professionally executed.",
    "The overall aesthetic is modern, clean, and suitable for educational content.",
    "Visual elements are precisely positioned for optimal comprehension.",
    "The pacing allows viewers to absorb information naturally.",
    "All textures and models are rendered with high accuracy to ensure professional results.",
]


class WanPromptValidationResult:
    def __init__(self):
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.quality_score = 0.0
    
    def add_error(self, msg: str):
        self.is_valid = False
        self.errors.append(msg)
    
    def add_warning(self, msg: str):
        self.warnings.append(msg)


def validate_wan_prompt(prompt: str, section_id: int = 0, beat_index: int = 0) -> WanPromptValidationResult:
    """Validate a single WAN prompt for quality and specificity.
    
    Args:
        prompt: The video generation prompt text
        section_id: Section identifier for error messages
        beat_index: Beat index for error messages
    
    Returns:
        WanPromptValidationResult with validation status and messages
    """
    result = WanPromptValidationResult()
    prefix = f"Section {section_id}, Beat {beat_index}"
    
    if not prompt or not prompt.strip():
        result.add_error(f"{prefix}: Empty prompt")
        return result
    
    prompt_lower = prompt.lower()
    prompt_len = len(prompt.strip())
    
    if prompt_len < MIN_PROMPT_LENGTH:
        result.add_error(
            f"{prefix}: Prompt too short ({prompt_len} chars). "
            f"Minimum {MIN_PROMPT_LENGTH} chars required for quality video generation."
        )
    
    if prompt_len > MAX_PROMPT_LENGTH:
        result.add_warning(
            f"{prefix}: Prompt very long ({prompt_len} chars). "
            f"Consider condensing to improve generation focus."
        )
    
    found_vague = []
    for phrase in BANNED_VAGUE_PHRASES:
        if phrase in prompt_lower:
            found_vague.append(phrase)
    
    if found_vague:
        result.add_error(
            f"{prefix}: Contains vague phrases: {found_vague}. "
            "Replace with specific, concrete descriptions."
        )
    
    quality_matches = 0
    for pattern in QUALITY_INDICATORS:
        if re.search(pattern, prompt_lower):
            quality_matches += 1
    
    quality_score = min(1.0, quality_matches / len(QUALITY_INDICATORS))
    result.quality_score = quality_score
    
    if quality_matches == 0:
        result.add_warning(
            f"{prefix}: Prompt lacks cinematographic direction. "
            "Consider adding camera directions (zoom, pan) or motion descriptors."
        )
    
    return result


def validate_video_prompts(video_prompts: List[Dict], section_id: int = 0, strict: bool = False) -> Tuple[bool, List[str], List[str]]:
    """Validate all video prompts for a section.
    
    Args:
        video_prompts: List of video prompt dicts with 'prompt' field
        section_id: Section identifier
        strict: If True, warnings become errors
    
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    all_errors = []
    all_warnings = []
    
    if not video_prompts:
        return True, [], ["No video prompts to validate"]
    
    for i, vp in enumerate(video_prompts):
        prompt = vp.get("prompt", "") if isinstance(vp, dict) else str(vp)
        result = validate_wan_prompt(prompt, section_id, i)
        
        all_errors.extend(result.errors)
        if strict:
            all_errors.extend(result.warnings)
        else:
            all_warnings.extend(result.warnings)
    
    return len(all_errors) == 0, all_errors, all_warnings


def log_prompt_quality_summary(video_prompts: List[Dict], section_id: int = 0) -> Dict:
    """Generate a quality summary for video prompts without failing.
    
    Args:
        video_prompts: List of video prompt dicts
        section_id: Section identifier
    
    Returns:
        Summary dict with quality metrics
    """
    if not video_prompts:
        return {"prompt_count": 0, "avg_quality": 0, "issues": []}
    
    total_quality = 0.0
    issues = []
    
    for i, vp in enumerate(video_prompts):
        prompt = vp.get("prompt", "") if isinstance(vp, dict) else str(vp)
        result = validate_wan_prompt(prompt, section_id, i)
        total_quality += result.quality_score
        issues.extend(result.errors + result.warnings)
    
    return {
        "prompt_count": len(video_prompts),
        "avg_quality": round(total_quality / len(video_prompts), 2),
        "issues": issues
    }


def truncate_wan_prompt(prompt: str, max_chars: int = MAX_PROMPT_LENGTH) -> str:
    """
    Surgical Truncation: Prioritize removing generic filler before hacking the core prompt.
    """
    if not prompt or len(prompt) <= max_chars:
        return prompt
    
    original_prompt = prompt
    
    # Step 1: Try to remove generic expansions first if they exist
    for expansion in reversed(WAN_GENERIC_EXPANSIONS):
        if len(prompt) <= max_chars:
            break
        if expansion in prompt:
            prompt = prompt.replace(" " + expansion, "").replace(expansion, "").strip()
    
    if len(prompt) <= max_chars:
        print(f"[WAN WARNING] Prompt reduced from {len(original_prompt)} to {len(prompt)} chars by removing generic filler.")
        return prompt

    # Step 2: If still too long, apply sentence-aware truncation
    print(f"[WAN WARNING] Surgical truncation failed to hit limit. Applying hard truncation to {len(prompt)} -> {max_chars} chars.")
    print(f"  [CAUTION] This may affect visual quality. LLM should generate more concisely.")
    
    truncated = prompt[:max_chars]
    last_period = truncated.rfind('.')
    last_exclaim = truncated.rfind('!')
    last_sentence_end = max(last_period, last_exclaim)
    
    if last_sentence_end > max_chars * 0.6:
        truncated = truncated[:last_sentence_end + 1]
    else:
        last_space = truncated.rfind(' ')
        if last_space > max_chars * 0.8:
            truncated = truncated[:last_space]
    
    return truncated.strip()


def truncate_video_prompts(video_prompts: List[Dict], max_chars: int = MAX_PROMPT_LENGTH) -> List[Dict]:
    """
    SAFETY NET: Truncate video prompts if LLM exceeded character limit.
    
    ISS-158 FIX: LLM prompts now instruct 80-150 words / 800 chars.
    Truncation here is a fallback for when LLM doesn't follow instructions.
    """
    truncated = []
    for vp in video_prompts:
        if isinstance(vp, dict):
            new_vp = vp.copy()
            if "prompt" in new_vp:
                original_len = len(new_vp["prompt"])
                new_vp["prompt"] = truncate_wan_prompt(new_vp["prompt"], max_chars)
            truncated.append(new_vp)
        else:
            truncated.append({"prompt": truncate_wan_prompt(str(vp), max_chars)})
    return truncated


def expand_short_prompt(prompt: str, min_words: int = MIN_WAN_PROMPT_WORDS) -> str:
    """
    SMART EXPANDER: Only pad generic one-liners. Trust detailed Director prompts.
    """
    word_count = len(prompt.split()) if prompt else 0
    
    # Rule 1: Custom/Detailed prompts (>= 60 words) are trusted as-is even if < 80
    if word_count >= 60:
        return prompt
    
    # Rule 2: If it's already over the min, don't touch it
    if word_count >= min_words:
        return prompt
    
    # Rule 3: Only expand very short or extremely generic prompts
    # If it contains specific technical/subject terms, we lean towards trusting it
    technical_indicators = ["eye", "medical", "physics", "math", "diagram", "process", "cycle", "formula", "equation", "scientific"]
    has_specifics = any(term in prompt.lower() for term in technical_indicators)
    
    if word_count >= 40 and has_specifics:
        return prompt
    
    # Expand generic prompts
    expanded = prompt.rstrip()
    if not expanded.endswith('.'):
        expanded += '.'
    
    for expansion in WAN_GENERIC_EXPANSIONS:
        if len(expanded.split()) >= min_words:
            break
        expanded += " " + expansion
    
    print(f"[WAN Expander] Padding generic prompt: {word_count} -> {len(expanded.split())} words")
    return expanded


def expand_video_prompts(video_prompts: List[Dict], min_words: int = MIN_WAN_PROMPT_WORDS) -> List[Dict]:
    """
    Auto-expand all short video prompts to meet minimum word requirement.
    
    Args:
        video_prompts: List of video prompt dicts
        min_words: Minimum words required per prompt
    
    Returns:
        List of prompts with short ones expanded
    """
    expanded = []
    for vp in video_prompts:
        if isinstance(vp, dict):
            new_vp = vp.copy()
            if "prompt" in new_vp:
                new_vp["prompt"] = expand_short_prompt(new_vp["prompt"], min_words)
            expanded.append(new_vp)
        else:
            expanded.append({"prompt": expand_short_prompt(str(vp), min_words)})
    return expanded


def hard_fail_on_short_prompts(video_prompts: List[Dict], section_id: int, min_words: int = MIN_WAN_PROMPT_WORDS) -> None:
    """
    ISS-076 FIX: Hard fail validation for WAN prompts.
    ISS-120 UPDATE: Now validates 80-150 words and max 800 chars.
    
    Raises WanPromptHardFailError if any prompt is below minimum word count
    or exceeds maximum character limit.
    This should be called before production WAN API calls.
    
    Args:
        video_prompts: List of video prompt dicts
        section_id: Section identifier
        min_words: Minimum words required per prompt (default 80)
    
    Raises:
        WanPromptHardFailError: If any prompt fails validation
    """
    if not video_prompts:
        raise WanPromptHardFailError(section_id, "No video_prompts provided")
    
    for i, vp in enumerate(video_prompts):
        prompt = vp.get("prompt", "") if isinstance(vp, dict) else str(vp)
        word_count = len(prompt.split()) if prompt else 0
        char_count = len(prompt) if prompt else 0
        
        if word_count < min_words:
            raise WanPromptHardFailError(
                section_id,
                f"Beat {i}: Prompt has {word_count} words, minimum {min_words} required. "
                f"Prompt preview: '{prompt[:100]}...'"
            )
        
        if char_count > MAX_PROMPT_LENGTH:
            raise WanPromptHardFailError(
                section_id,
                f"Beat {i}: Prompt has {char_count} chars, maximum {MAX_PROMPT_LENGTH} allowed. "
                f"Truncate or condense the prompt."
            )
    
    print(f"[WAN Validator] Section {section_id}: All {len(video_prompts)} prompts meet {min_words}+ word / {MAX_PROMPT_LENGTH} char requirement")

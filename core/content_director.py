"""
Content Director v1.4 - Pass 1a: Lesson Structure

Generates intro/summary/content/example/quiz sections with:
- Avatar placement and display_directives
- Timing and duration estimates
- Visual content (bullet_points, formulas, labels)
- Narration text and segments

Does NOT generate memory or recap sections (handled by Recap Director).
Uses Gemini 2.5 Pro with structured output.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from openai import OpenAI

from core.json_repair import repair_and_parse_json, validate_json_structure
from core.analytics import AnalyticsTracker

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL
)

PROMPTS_DIR = Path(__file__).parent / "prompts"

MODEL = "google/gemini-2.5-pro"

MAX_STRUCTURAL_RETRIES = 4
MAX_SEMANTIC_RETRIES = 2

VALID_SECTION_TYPES = ["intro", "summary", "content", "example", "quiz"]
VALID_RENDERERS = ["remotion", "manim", "video"]
VALID_TEXT_LAYERS = ["show", "hide", "highlight"]
VALID_VISUAL_LAYERS = ["show", "hide", "replace"]
VALID_AVATAR_LAYERS = ["show", "hide", "gesture_only"]


def load_prompt(name: str) -> str:
    """Load a prompt file."""
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(path, "r") as f:
        return f.read()


def call_content_director(
    topics: List[Dict],
    subject: str,
    grade: str,
    tracker: Optional[AnalyticsTracker] = None,
    max_structural_retries: int = MAX_STRUCTURAL_RETRIES,
    max_semantic_retries: int = MAX_SEMANTIC_RETRIES
) -> Dict:
    """
    PASS 1a: Generate lesson structure sections.
    
    Generates: intro, summary, content, example, quiz sections.
    Does NOT generate: memory, recap (handled by Recap Director).
    
    Args:
        topics: Topic blocks from Smart Chunker
        subject: Subject area (e.g., "Biology", "Physics")
        grade: Grade level (e.g., "Grade 10")
        tracker: Analytics tracker
        max_structural_retries: Max retries for structural errors (default 4)
        max_semantic_retries: Max retries for semantic errors (default 2)
        
    Returns:
        Dict with title and sections array
        
    Raises:
        ContentDirectorError: If generation fails after all retries
    """
    logger.info(f"[Content Director] Starting lesson structure for {subject} {grade}")
    
    system_prompt = load_prompt("content_director_system_v1.4")
    user_prompt_template = load_prompt("content_director_user_v1.4")
    
    user_prompt = user_prompt_template.format(
        subject=subject,
        grade=grade,
        topics_json=json.dumps(topics, indent=2)
    )
    
    structural_attempts = 0
    semantic_attempts = 0
    last_error = None
    total_input_tokens = 0
    total_output_tokens = 0
    
    if tracker:
        tracker.start_phase("content_director", MODEL)
    
    while True:
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=32000,
                response_format={"type": "json_object"}
            )
            
            raw_response = response.choices[0].message.content or ""
            
            if not raw_response:
                raise ContentDirectorError("Empty response from LLM")
            
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            
            result = repair_and_parse_json(raw_response)
            
            structural_errors = _validate_structure(result)
            if structural_errors:
                structural_attempts += 1
                if structural_attempts > max_structural_retries:
                    if tracker:
                        tracker.end_phase("content_director", total_input_tokens, total_output_tokens)
                    raise StructuralValidationError(structural_errors)
                logger.warning(f"[Content Director] Structural retry {structural_attempts}/{max_structural_retries}")
                user_prompt = _get_structural_retry_prompt(user_prompt, structural_errors)
                continue
            
            semantic_errors = _validate_semantics(result)
            if semantic_errors:
                semantic_attempts += 1
                if semantic_attempts > max_semantic_retries:
                    if tracker:
                        tracker.end_phase("content_director", total_input_tokens, total_output_tokens)
                    raise SemanticValidationError(semantic_errors)
                logger.warning(f"[Content Director] Semantic retry {semantic_attempts}/{max_semantic_retries}")
                user_prompt = _get_semantic_retry_prompt(user_prompt, semantic_errors)
                continue
            
            if tracker:
                tracker.end_phase("content_director", total_input_tokens, total_output_tokens)
            
            section_count = len(result.get("sections", []))
            logger.info(f"[Content Director] Successfully generated {section_count} sections")
            return result
            
        except (json.JSONDecodeError) as e:
            structural_attempts += 1
            last_error = e
            if structural_attempts > max_structural_retries:
                if tracker:
                    tracker.end_phase("content_director", total_input_tokens, total_output_tokens)
                raise ContentDirectorError(f"JSON parse failed: {e}")
            logger.warning(f"[Content Director] JSON retry {structural_attempts}/{max_structural_retries}: {e}")
            user_prompt = _get_json_repair_prompt(user_prompt, str(e))
            
        except (StructuralValidationError, SemanticValidationError) as e:
            last_error = e
            if tracker:
                tracker.end_phase("content_director", total_input_tokens, total_output_tokens)
            raise ContentDirectorError(f"Validation failed: {e}")
            
        except Exception as e:
            logger.error(f"[Content Director] Unexpected error: {e}")
            if tracker:
                tracker.end_phase("content_director", total_input_tokens, total_output_tokens)
            raise ContentDirectorError(f"Unexpected error: {e}")


def _validate_structure(data: Dict) -> List[str]:
    """Validate structural requirements."""
    errors = []
    
    if "sections" not in data:
        errors.append("Missing 'sections' array")
        return errors
    
    sections = data.get("sections", [])
    if not sections:
        errors.append("sections array is empty")
        return errors
    
    has_intro = any(s.get("section_type") == "intro" for s in sections)
    has_summary = any(s.get("section_type") == "summary" for s in sections)
    
    if not has_intro:
        errors.append("Missing required 'intro' section")
    if not has_summary:
        errors.append("Missing required 'summary' section")
    
    for i, section in enumerate(sections):
        section_errors = _validate_section_structure(section, i)
        errors.extend(section_errors)
    
    return errors


def _validate_section_structure(section: Dict, index: int) -> List[str]:
    """Validate structure of a single section."""
    errors = []
    prefix = f"sections[{index}]"
    
    required = ["section_id", "section_type", "renderer", "narration"]
    for field in required:
        if field not in section:
            errors.append(f"{prefix}: missing required field '{field}'")
    
    section_type = section.get("section_type")
    if section_type and section_type not in VALID_SECTION_TYPES:
        errors.append(f"{prefix}: invalid section_type '{section_type}' (must be one of {VALID_SECTION_TYPES})")
    
    if section_type in ["memory", "recap"]:
        errors.append(f"{prefix}: section_type '{section_type}' not allowed in Content Director (use Recap Director)")
    
    renderer = section.get("renderer")
    if renderer and renderer not in VALID_RENDERERS:
        errors.append(f"{prefix}: invalid renderer '{renderer}'")
    
    if renderer == "manim":
        if "manim_scene_spec" not in section:
            errors.append(f"{prefix}: manim renderer requires 'manim_scene_spec' field")
        else:
            manim_spec = section.get("manim_scene_spec", {})
            if not isinstance(manim_spec, dict):
                errors.append(f"{prefix}: manim_scene_spec must be an object")
            elif "objects" not in manim_spec or "animation_sequence" not in manim_spec:
                errors.append(f"{prefix}: manim_scene_spec must have 'objects' and 'animation_sequence' arrays")
        
        if "visual_beats" not in section or not section.get("visual_beats"):
            errors.append(f"{prefix}: manim renderer requires at least one visual_beat")
    
    if renderer == "video":
        if "visual_beats" not in section or not section.get("visual_beats"):
            errors.append(f"{prefix}: video renderer requires at least one visual_beat")
    
    narration = section.get("narration", {})
    if not isinstance(narration, dict):
        errors.append(f"{prefix}: narration must be an object")
    else:
        if "segments" not in narration:
            errors.append(f"{prefix}: narration missing 'segments' array")
        else:
            segments = narration.get("segments", [])
            for j, seg in enumerate(segments):
                seg_errors = _validate_segment_structure(seg, index, j)
                errors.extend(seg_errors)
    
    return errors


def _validate_segment_structure(segment: Dict, section_idx: int, segment_idx: int) -> List[str]:
    """Validate structure of a narration segment."""
    errors = []
    prefix = f"sections[{section_idx}].narration.segments[{segment_idx}]"
    
    required = ["segment_id", "text", "display_directives"]
    for field in required:
        if field not in segment:
            errors.append(f"{prefix}: missing required field '{field}'")
    
    dd = segment.get("display_directives", {})
    if not isinstance(dd, dict):
        errors.append(f"{prefix}: display_directives must be an object")
    else:
        for layer, valid_values in [
            ("text_layer", VALID_TEXT_LAYERS),
            ("visual_layer", VALID_VISUAL_LAYERS),
            ("avatar_layer", VALID_AVATAR_LAYERS)
        ]:
            if layer not in dd:
                errors.append(f"{prefix}.display_directives: missing '{layer}'")
            elif dd[layer] not in valid_values:
                errors.append(f"{prefix}.display_directives.{layer}: invalid value '{dd[layer]}'")
    
    return errors


def _validate_semantics(data: Dict) -> List[str]:
    """Validate semantic requirements (content rules)."""
    errors = []
    
    sections = data.get("sections", [])
    
    for i, section in enumerate(sections):
        prefix = f"sections[{i}]"
        section_type = section.get("section_type")
        
        narration = section.get("narration", {})
        if not isinstance(narration, dict):
            narration = {}
        full_text = narration.get("full_text", "")
        if not isinstance(full_text, str):
            full_text = str(full_text) if full_text else ""
        word_count = len(full_text.split())
        
        if section_type == "content" and word_count < 100:
            errors.append(f"{prefix}: content section narration too short ({word_count} words, minimum 100)")
        
        segments = narration.get("segments", [])
        for j, seg in enumerate(segments):
            dd = seg.get("display_directives", {})
            text_layer = dd.get("text_layer")
            visual_layer = dd.get("visual_layer")
            
            if text_layer == "show" and visual_layer == "show":
                errors.append(f"{prefix}.segments[{j}]: mutual exclusion violation - text_layer and visual_layer both 'show'")
        
        if section_type == "intro":
            layout = section.get("layout", {})
            avatar_pos = layout.get("avatar_position")
            avatar_width = layout.get("avatar_width_percent", 0)
            
            if avatar_pos == "hidden":
                errors.append(f"{prefix}: intro section must have visible avatar")
            if avatar_width < 50:
                errors.append(f"{prefix}: intro avatar_width_percent should be ≥50% (got {avatar_width}%)")
    
    return errors


def _get_structural_retry_prompt(original_prompt: str, errors: List[str]) -> str:
    """Generate retry prompt for structural errors."""
    error_list = "\n".join(f"- {e}" for e in errors)
    return original_prompt + f"""

---
STRUCTURAL ERRORS - RETRY REQUIRED:
{error_list}

Fix these structural issues:
1. Ensure all required fields are present
2. Use only valid section_types: intro, summary, content, example, quiz
3. Do NOT include memory or recap sections
4. Every segment must have display_directives with text_layer, visual_layer, avatar_layer
5. Manim sections MUST have manim_scene_spec with objects and animation_sequence arrays
6. Manim and Video sections MUST have at least one visual_beat
---
"""


def _get_semantic_retry_prompt(original_prompt: str, errors: List[str]) -> str:
    """Generate retry prompt for semantic errors."""
    error_list = "\n".join(f"- {e}" for e in errors)
    return original_prompt + f"""

---
SEMANTIC ERRORS - RETRY REQUIRED:
{error_list}

Fix these content issues:
1. text_layer and visual_layer CANNOT both be 'show' in the same segment
2. Content sections need at least 100 words of narration
3. Intro section must have visible avatar (position not 'hidden') with width ≥50%
---
"""


def _get_json_repair_prompt(original_prompt: str, error: str) -> str:
    """Generate retry prompt for JSON parse errors."""
    return original_prompt + f"""

---
JSON PARSE ERROR - RETRY REQUIRED:
{error}

Ensure your response is valid JSON:
1. No trailing commas before }} or ]]
2. All strings properly quoted
3. No comments in JSON
4. Complete all arrays and objects
---
"""


class ContentDirectorError(Exception):
    """Error raised when Content Director fails."""
    pass


class StructuralValidationError(Exception):
    """Error raised for structural validation failures."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Structural errors: {', '.join(errors)}")


class SemanticValidationError(Exception):
    """Error raised for semantic validation failures."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Semantic errors: {', '.join(errors)}")

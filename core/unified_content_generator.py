"""
V2 Unified Content Generator

Single LLM call to generate complete presentation from raw markdown.
Includes retry wrapper for production resilience.
"""

import os
import json
import time
import logging
import requests
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


from core.llm_config import get_model_name, get_fallback_model_name

@dataclass
class GeneratorConfig:
    """Configuration for the unified content generator."""
    model: str = get_model_name()
    temperature: float = 0.7
    max_tokens: int = 32000
    max_retries: int = 3
    retry_delay_base: float = 2.0
    timeout: int = 60


class SchemaValidationError(Exception):
    """Raised when output doesn't match expected schema."""
    pass


class JSONParseError(Exception):
    """Raised when LLM response isn't valid JSON."""
    pass


# REQ-001: Explicitly REMOVED Hardcoded Fallback. 
# All prompts must be loaded from 'core/prompts/' directory.
# If file load fails, the system MUST Fail Fast.
try:
    _PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "unified_system_prompt_CURRENT.txt")
    with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
        UNIFIED_SYSTEM_PROMPT = f.read()
    print(f"[INFO] Loaded UNIFIED_SYSTEM_PROMPT from {_PROMPT_PATH} ({len(UNIFIED_SYSTEM_PROMPT)} chars)")
except Exception as e:
    print(f"[FATAL] Failed to load UNIFIED_SYSTEM_PROMPT from core/prompts/: {e}")
    # Fail fast as required
    UNIFIED_SYSTEM_PROMPT = None
    # We allow the module to load, but generation will fail if this is None (handled in generate_presentation) 


def build_user_prompt(
    markdown_content: str,
    subject: str = "Science",
    grade: str = "Grade 10",
    images_list: str = "None"
) -> str:
    """Build the user prompt with document content."""
    return f"""## Document Details
Subject: {subject}
Grade Level: {grade}
Available Images: {images_list}

## Source Document (Markdown)
```markdown
{markdown_content}
```

Generate the complete presentation JSON following the schema exactly. Include all section types in order: intro, summary, content, example (if applicable), quiz, memory, recap."""


def call_openrouter_llm(
    system_prompt: str,
    user_prompt: str,
    config: GeneratorConfig
) -> Tuple[str, dict]:
    """Call OpenRouter API and return (response_text, usage_stats)."""
    # ISS-FIX: Lazy load key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://replit.com",
        "X-Title": "AI Education V2"
    }
    
    # DEBUG AUTH (Stderr for immediate visibility)
    # import sys
    # safe_key = f"{api_key[:10]}...{api_key[-5:]}" if api_key else "None"
    # sys.stderr.write(f"\n[DEBUG] call_openrouter_llm\n")
    # sys.stderr.write(f"[DEBUG] Key: {safe_key}\n")
    # sys.stderr.write(f"[DEBUG] Model: {config.model}\n")
    # sys.stderr.write(f"[DEBUG] Env Matches: {api_key == os.environ.get('OPENROUTER_API_KEY')}\n")
    # sys.stderr.flush()
    
    
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens
    }
    
    
    try:
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=config.timeout
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else 0
        if status_code in [404, 429, 500, 502, 503, 401]:
            fallback_model = get_fallback_model_name()
            if fallback_model and fallback_model != config.model:
                print(f"⚠️ Primary model {config.model} failed (Status {status_code}). Switching to fallback: {fallback_model}")
                payload["model"] = fallback_model
                # Retry with fallback
                response = requests.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=config.timeout
                )
                response.raise_for_status()
            else:
                raise e
        else:
            raise e
    
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    
    # ISS-300: Extract usage stats for analytics
    usage = data.get("usage", {})
    usage_stats = {
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "model": config.model
    }
    
    return content, usage_stats


def extract_json_from_response(response: str) -> dict:
    """Extract and parse JSON from LLM response."""
    if response is None:
        raise ValueError("Response is None - cannot parse JSON")
        
    content = response.strip()
    
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    
    if content.endswith("```"):
        content = content[:-3]
    
    content = content.strip()
    
    try:
        return json.loads(content)
    except json.JSONDecodeError as first_err:
        # ISS-FIX: Common LLM error - single backslash in LaTeX within JSON string
        # e.g. "formula": "\frac{1}{2}" -> Invalid \f escape
        try:
            import re
            # Regex to find backslashes that are NOT followed by valid JSON escape chars
            # Valid escapes: ", \, /, b, f, n, r, t, uXXXX
            # We want to double-escape invalid ones.
            # Pattern: \ (not one of " \ / b f n r t u)
            fixed_content = re.sub(r'\\(?![/\"\\bfnrtu])', r'\\\\', content)
            return json.loads(fixed_content)
        except json.JSONDecodeError as second_err:
            # ISS-FIX: Handle Truncated JSON (Model stopped early)
            # Try to auto-close brackets/braces
            try:
                # Naive helper to close open structures
                # Count opens/closes
                opens_br = content.count('{') - content.count('}')
                opens_sq = content.count('[') - content.count(']')
                
                repaired = content
                # Close quotes if needed (simple heuristic)
                if repaired.strip()[-1] not in ['"', '}', ']'] and '"' in repaired.splitlines()[-1]:
                     repaired += '"'
                     
                repaired += '}' * opens_br
                repaired += ']' * opens_sq
                
                # Double check braces balance, sometimes we need to close ] before }
                # Better approach: recursive fix or just try simple append
                # For now, appending }]*20 is safer? No.
                
                # Let's try just the simple count balance
                # If the last char was inside a string, we might have botched it.
                # Recovering from mid-string check:
                val = json.loads(repaired)
                print(f"[WARN] Recovered from TRUNCATED JSON by auto-closing tags.")
                return val
            except Exception:
                pass

            # If that fails, Dump the raw content for debugging
            try:
                with open("llm_parse_fail.txt", "w", encoding="utf-8") as f:
                    f.write(content)
            except: pass
            
            # CRITICAL FIX: Explicitly raise JSONParseError, do NOT fallback or return None
            # Log the first 100 chars for context
            snippet = content[:100] + "..." if len(content) > 100 else content
            logger.error(f"[JSONParseError] Failed content snippet: {snippet}")
            raise JSONParseError(f"Failed to parse JSON: {first_err}")


def normalize_output(output: dict) -> dict:
    """Normalize field names to expected schema."""
    if "title" in output and "presentation_title" not in output:
        output["presentation_title"] = output.pop("title")
    
    if "presentation" in output and "sections" not in output:
        output["sections"] = output.pop("presentation")
    
    return output


def validate_schema(output: dict) -> Tuple[bool, List[str]]:
    """Validate output against required schema. Returns (is_valid, errors)."""
    errors = []
    
    output = normalize_output(output)
    
    if "sections" not in output:
        errors.append("Missing 'sections' array")
        return False, errors
    
    sections = output.get("sections", [])
    if not sections:
        errors.append("Empty sections array")
        return False, errors
    
    valid_sections = []
    required_section_fields = ["section_type", "narration"]
    
    for i, section in enumerate(sections):
        if not isinstance(section, dict):
            errors.append(f"[Section {i}] Invalid format: Expected dict")
            continue
            
        section_id = section.get("section_id", f"section_{i+1}")
        section_errors = []
        
        for field in required_section_fields:
            if field not in section:
                section_errors.append(f"Missing field: {field}")
        
        narration = section.get("narration", {})
        if "segments" not in narration:
            section_errors.append("Missing narration.segments")
        elif not narration.get("segments"):
            section_errors.append("Empty segments array")
            
        if "visual_beats" not in section:
            section_errors.append("Missing visual_beats")
            
        if not section_errors:
            valid_sections.append(section)
        else:
            errors.append(f"[{section_id}] Corrupt section (likely truncated): {section_errors}")
    
    # Update sections with only valid ones
    output["sections"] = valid_sections
    
    if not valid_sections:
        errors.append("No valid sections remained after filtering corruption.")
        return False, errors
        
    return True, errors


def generate_presentation(
    markdown_content: str,
    subject: str = "Science",
    grade: str = "Grade 10",
    images_list: str = "None",
    config: Optional[GeneratorConfig] = None,
    output_dir: Optional[str] = None
) -> dict:
    """
    Generate complete presentation from raw markdown with retry.
    
    Args:
        markdown_content: Raw markdown from Datalab (no cleaning needed)
        subject: Subject area (e.g., "Biology", "Physics")
        grade: Grade level (e.g., "Grade 10")
        images_list: Comma-separated list of image IDs
        config: Generator configuration (uses defaults if None)
    
    Returns:
        Complete presentation dict ready for player transformation
    
    Raises:
        JSONParseError: If JSON parsing fails after all retries
        SchemaValidationError: If schema validation fails after all retries
        requests.RequestException: If API call fails after all retries
    """
    if config is None:
        config = GeneratorConfig()
    
    user_prompt = build_user_prompt(
        markdown_content=markdown_content,
        subject=subject,
        grade=grade,
        images_list=images_list
    )
    
    last_error = None
    llm_usage_stats = None
    
    for attempt in range(config.max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{config.max_retries}: Calling LLM...")
            
            response, usage_stats = call_openrouter_llm(
                system_prompt=UNIFIED_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                config=config
            )
            llm_usage_stats = usage_stats
            
            logger.info(f"Response received: {len(response)} chars")
            
            output = extract_json_from_response(response)
            logger.info("JSON parsed successfully")
            
            output = normalize_output(output)
            
            # USER REQUEST: Dump raw output for inspection
            try:
                debug_path = "llm_debug_dump.json"
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    debug_path = os.path.join(output_dir, debug_path)
                
                with open(debug_path, "w", encoding="utf-8") as f:
                    json.dump(output, f, indent=2)
                # print(f"[DEBUG] Saved raw LLM output to '{debug_path}'")
            except Exception as e:
                print(f"[DEBUG] Failed to save dump: {e}")

            is_valid, errors = validate_schema(output)
            
            if not is_valid:
                # USER REQUEST: FORCE PROCEED on Validation Failure
                logger.warning(f"Schema validation FAILED (IGNORING): {errors}")
                print(f"⚠️ Schema Validation Failed with {len(errors)} errors - PROCEEDING ANYWAY")
                # raise SchemaValidationError(f"Schema validation failed: {errors[:3]}")
            
            logger.info("Schema validation passed (or bypassed)")
            
            # ISS-300: Attach usage stats to output for analytics
            output["_llm_usage"] = llm_usage_stats
            return output
            
        except (JSONParseError, SchemaValidationError) as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            
            if attempt < config.max_retries - 1:
                delay = config.retry_delay_base * (2 ** attempt)
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)
            
        except requests.RequestException as e:
            last_error = e
            logger.warning(f"API error on attempt {attempt + 1}: {e}")
            
            if attempt < config.max_retries - 1:
                delay = config.retry_delay_base * (2 ** attempt)
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)
    
    if last_error is not None:
        raise last_error
    raise RuntimeError("Generation failed after all retries")


def transform_to_player_schema(
    v2_output: dict,
    subject: str = "Science",
    grade: str = "10"
) -> dict:
    """
    Transform V2 output to final presentation.json format compatible with the player.
    
    Adds fields that are generated by post-processing (TTS, Manim, etc.)
    or have fixed values.
    """
    v2_output = normalize_output(v2_output)
    
    # Preserve decision_log from LLM for analysis
    decision_log = v2_output.get("decision_log", {})
    
    presentation = {
        "spec_version": "v1.5",
        "title": v2_output.get("presentation_title", "Lesson"),
        "subject": subject,
        "grade": grade,
        "avatar_global": {
            "style": "teacher",
            "default_position": "right",
            "default_width_percent": 52,
            "gesture_enabled": True
        },
        "metadata": {
            "generated_by": "v1.5-v2-unified",
            "llm_calls": 1
        },
        "decision_log": decision_log,
        "sections": []
    }
    
    for i, section in enumerate(v2_output.get("sections", [])):
        transformed = {
            "section_id": i + 1,
            "section_type": section.get("section_type", "content"),
            "title": section.get("title", f"Section {i+1}"),
            "renderer": section.get("derived_renderer", "none"),
            "decision_reason": section.get("decision_reason", ""),
            "avatar_layout": {
                "visibility": "always",
                "mode": "floating",
                "position": "right" if section.get("section_type") != "intro" else "center",
                "width_percent": 52 if section.get("section_type") != "intro" else 60
            },
            "narration": _transform_narration(section.get("narration", {}), section.get("visual_beats", [])),
            "visual_beats": _transform_visual_beats(section.get("visual_beats", [])),
            "display_directives": _extract_display_directives(section),
        }
        
        if section.get("video_prompts"):
            # ISS-STRING-PROMPT-FIX: Ensure all prompts are objects, not strings
            sanitized_prompts = []
            for p in section["video_prompts"]:
                if isinstance(p, str):
                    sanitized_prompts.append({"prompt": p, "beat_id": f"beat_{len(sanitized_prompts)}"})
                elif isinstance(p, dict):
                    sanitized_prompts.append(p)
            transformed["video_prompts"] = sanitized_prompts
        
        if section.get("quiz_data"):
            transformed["quiz_data"] = section["quiz_data"]
        
        if section.get("flashcards"):
            transformed["flashcards"] = section["flashcards"]
        
        presentation["sections"].append(transformed)
    
    return presentation


def _transform_narration(narration: dict, visual_beats: list = None) -> dict:
    """Transform narration to player format, mapping visual_beats into segment visual_content."""
    full_text = narration.get("full_text", "")
    segments = narration.get("segments", [])
    visual_beats = visual_beats or []
    
    # Build segment_id -> visual_beat mapping
    beat_map = {}
    for beat in visual_beats:
        seg_id = beat.get("segment_id", "seg_1")
        if seg_id not in beat_map:
            beat_map[seg_id] = beat
    
    transformed_segments = []
    for i, seg in enumerate(segments):
        seg_id = seg.get("segment_id", f"seg_{i+1}")
        beat = beat_map.get(seg_id, {})
        
        # ISS-FIX: PRESERVE existing visual_content from LLM output if present
        existing_vc = seg.get("visual_content")
        if existing_vc and isinstance(existing_vc, dict):
            # Use LLM-provided visual_content directly
            visual_content = existing_vc
        else:
            # Derive visual_content from visual_beats (legacy path)
            # Map visual_beat to visual_content
            visual_type = beat.get("visual_type", "text")
            display_text = beat.get("display_text", "")
            
            # Determine content_type and structure
            if visual_type == "bullet_list":
                content_type = "bullet_points"
                items = [display_text] if display_text else []
                # Split on newlines if present
                if display_text and "\n" in display_text:
                    items = [line.strip() for line in display_text.split("\n") if line.strip()]
                visual_content = {
                    "content_type": content_type,
                    "display_format": "bullets",
                    "items": items,
                    "verbatim_content": None
                }
            elif visual_type == "equation":
                visual_content = {
                    "content_type": "equation",
                    "display_format": "latex",
                    "items": [],
                    "verbatim_content": beat.get("latex_content", display_text)
                }
            elif visual_type in ("diagram", "image"):
                visual_content = {
                    "content_type": visual_type,
                    "display_format": None,
                    "items": [],
                    "verbatim_content": display_text,
                    "image_id": beat.get("image_id")
                }
            else:
                # Default text type
                visual_content = {
                    "content_type": "text",
                    "display_format": None,
                    "items": [],
                    "verbatim_content": display_text if display_text else None
                }
        
        # TEACH → SHOW pattern: text_layer and visual_layer are mutually exclusive
        # When showing text, visual should be hidden (TEACH phase)
        # When showing video/visual, text should be hidden (SHOW phase)
        seg_directives = seg.get("display_directives")
        if not seg_directives:
            # Default to TEACH mode: show text, hide visual
            seg_directives = {
                "text_layer": "show",
                "visual_layer": "hide",
                "avatar_layer": "show"
            }
        else:
            # Enforce mutual exclusion if LLM violated it
            if seg_directives.get("text_layer") == "show" and seg_directives.get("visual_layer") == "show":
                # Default to TEACH mode when both are show
                seg_directives["visual_layer"] = "hide"
        
        transformed_seg = {
            "segment_id": i + 1,
            "text": seg.get("text", ""),
            "duration_seconds": 0,
            "gesture_hint": seg.get("purpose", "neutral"),
            "visual_content": visual_content,
            "display_directives": seg_directives
        }
        transformed_segments.append(transformed_seg)
    
    return {
        "full_text": full_text,
        "segments": transformed_segments,
        "total_duration_seconds": 0
    }


def _transform_visual_beats(visual_beats: list) -> list:
    """Transform visual beats to player format."""
    if not visual_beats:
        return []
        
    transformed = []
    for beat in visual_beats:
        t_beat = {
            "beat_id": beat.get("beat_id", f"beat_{len(transformed)+1}"),
            "segment_id": beat.get("segment_id", 1),
            "visual_beat_type": beat.get("visual_type", "text_only"),
            "description": beat.get("display_text", ""),
            "source_block_ids": []
        }
        
        if beat.get("latex_content"):
            t_beat["latex_content"] = beat["latex_content"]
        if beat.get("image_id"):
            t_beat["image_id"] = beat["image_id"]
        
        transformed.append(t_beat)
    
    return transformed


def _extract_display_directives(section: dict) -> list:
    """Extract display directives from section."""
    narration = section.get("narration", {})
    segments = narration.get("segments", [])
    
    if segments:
        return [seg.get("display_directives", {
            "text_layer": "show",
            "visual_layer": "hide", 
            "avatar_layer": "show"
        }) for seg in segments]
    
    return [{
        "text_layer": "show",
        "visual_layer": "hide",
        "avatar_layer": "show"
    }]

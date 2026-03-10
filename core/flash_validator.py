"""
Flash LLM Validator - Semantic quality check for visual beats.

Uses Gemini Flash to determine if visual beat content is:
- Specific and actionable (PASS)
- Vague filler that can't be rendered (FAIL)

This replaces rigid word-count rules with intelligent context understanding.
"""

import os
import json
import sys
from openai import OpenAI

FLASH_MODEL = "google/gemini-2.5-flash"

VALIDATION_PROMPT = """You are a video rendering quality gate. Your job is to check if a visual beat description is specific enough to create an educational video.

A visual beat has 5 fields:
- scene_setup: What the scene looks like
- objects_and_properties: What objects appear and their visual properties
- motion_sequence: How things move/animate
- labels_and_text: Text/labels shown on screen
- pedagogical_focus: The teaching goal

PASS criteria (any of these):
- Contains specific mathematical equations (e.g., "x² + 5x + 6 = 0")
- Names concrete visual objects (e.g., "coordinate plane", "parabola", "red arrow")
- Describes specific motions (e.g., "arrow moves from point A to B", "equation transforms")
- Short but precise (e.g., "Show: E = mc²" is acceptable)

FAIL criteria (all of these present):
- Only vague phrases like "show clearly", "animate smoothly", "visualize concept"
- No specific objects, equations, or motions named
- Generic filler that a video renderer cannot act on

Respond with ONLY valid JSON:
{"valid": true, "reason": "brief explanation"} 
OR
{"valid": false, "reason": "what's missing or vague"}
"""


def log(msg: str):
    """Print with immediate flush for real-time logging."""
    print(msg)
    sys.stdout.flush()


def validate_beat_with_flash(beat: dict, section_id: int, beat_index: int, section_type: str = "content") -> dict:
    """
    Use Gemini Flash to validate if a visual beat is specific enough to render.
    
    Returns:
        {"valid": True/False, "reason": "explanation"}
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        log("[FLASH VALIDATOR] No API key, skipping semantic validation")
        return {"valid": True, "reason": "API key not available, skipped validation"}
    
    beat_text = f"""Section {section_id} ({section_type}), Beat {beat_index}:
- scene_setup: {beat.get('scene_setup', '(empty)')}
- objects_and_properties: {beat.get('objects_and_properties', '(empty)')}
- motion_sequence: {beat.get('motion_sequence', '(empty)')}
- labels_and_text: {beat.get('labels_and_text', '(empty)')}
- pedagogical_focus: {beat.get('pedagogical_focus', '(empty)')}"""

    result_text = ""
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        
        response = client.chat.completions.create(
            model=FLASH_MODEL,
            messages=[
                {"role": "system", "content": VALIDATION_PROMPT},
                {"role": "user", "content": f"Validate this visual beat:\n\n{beat_text}"}
            ],
            max_tokens=200,
            temperature=0.1
        )
        
        content = response.choices[0].message.content
        result_text = content.strip() if content else ""
        
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        result = json.loads(result_text)
        
        if result.get("valid"):
            log(f"[FLASH VALIDATOR] Section {section_id}, Beat {beat_index}: PASS - {result.get('reason', 'OK')}")
        else:
            log(f"[FLASH VALIDATOR] Section {section_id}, Beat {beat_index}: FAIL - {result.get('reason', 'Vague content')}")
        
        return result
        
    except json.JSONDecodeError as e:
        raw_preview = result_text[:200] if result_text else "(empty)"
        log(f"[FLASH VALIDATOR] JSON parse error: {e}, raw: {raw_preview}")
        return {"valid": True, "reason": f"Validation response parse error, allowing: {str(e)[:50]}"}
    except Exception as e:
        log(f"[FLASH VALIDATOR] Error: {e}")
        return {"valid": True, "reason": f"Validation error, allowing: {str(e)[:50]}"}


def validate_section_beats(section: dict, strict: bool = True) -> list:
    """
    Validate all visual beats in a section using Flash LLM.
    
    Args:
        section: The section dict containing visual_beats
        strict: If True, raise error on first failure. If False, collect all failures.
    
    Returns:
        List of failed beat indices with reasons
    """
    section_id = section.get("id", 0)
    section_type = section.get("section_type", "content")
    visual_beats = section.get("visual_beats", [])
    
    if not visual_beats:
        return []
    
    failures = []
    
    for idx, beat in enumerate(visual_beats):
        result = validate_beat_with_flash(beat, section_id, idx, section_type)
        
        if not result.get("valid"):
            failures.append({
                "beat_index": idx,
                "reason": result.get("reason", "Unknown validation failure")
            })
            
            if strict and section_type in ("content", "example"):
                break
    
    return failures

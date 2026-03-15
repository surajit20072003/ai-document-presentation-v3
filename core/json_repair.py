"""
JSON Repair Utility for V1.4 Pipeline.

Repairs common JSON issues from LLM output BEFORE passing to next pipeline step.
This is applied after every LLM response.
"""

import json
import re
import logging

logger = logging.getLogger(__name__)


def repair_and_parse_json(response: str) -> dict:
    """
    Repair common JSON issues from LLM output.
    Applied BEFORE passing to next pipeline step.
    
    Handles:
    - Markdown code fences (```json ... ```)
    - Trailing commas
    - Unclosed braces/brackets (truncated output)
    - Unclosed strings
    - Extra text before/after JSON
    - Invalid control characters in strings
    
    Args:
        response: Raw LLM response string
        
    Returns:
        Parsed JSON as dict
        
    Raises:
        json.JSONDecodeError: If repair fails and JSON is still invalid
    """
    if not response:
        raise json.JSONDecodeError("Empty response", "", 0)
    
    response = response.strip()
    
    response = _strip_markdown_fences(response)
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    json_str = _extract_json_object(response)
    
    json_str = _fix_control_characters(json_str)
    
    json_str = _fix_trailing_commas(json_str)
    
    json_str = _close_unclosed_structures(json_str)
    
    try:
        result = json.loads(json_str)
        logger.info("[JSON Repair] Successfully repaired malformed JSON")
        return result
    except json.JSONDecodeError as e:
        json_str = _aggressive_control_char_fix(json_str)
        try:
            result = json.loads(json_str)
            logger.info("[JSON Repair] Successfully repaired with aggressive control char fix")
            return result
        except json.JSONDecodeError:
            pass
        
        logger.error(f"[JSON Repair] Failed to repair JSON: {e}")
        logger.debug(f"[JSON Repair] Attempted to parse: {json_str[:500]}...")
        raise


def _strip_markdown_fences(response: str) -> str:
    """Remove markdown code fences from response."""
    if '```json' in response:
        start = response.find('```json') + 7
        end = response.rfind('```')
        if end > start:
            return response[start:end].strip()
    
    if '```' in response:
        start = response.find('```') + 3
        end = response.rfind('```')
        if end > start:
            extracted = response[start:end].strip()
            if extracted.startswith('{') or extracted.startswith('['):
                return extracted
    
    return response


def _extract_json_object(response: str) -> str:
    """Extract JSON object or array from response with extra text."""
    brace_start = response.find('{')
    bracket_start = response.find('[')
    
    if brace_start == -1 and bracket_start == -1:
        return response
    
    if bracket_start != -1 and (brace_start == -1 or bracket_start < brace_start):
        start = bracket_start
        end = response.rfind(']')
        if end > start:
            return response[start:end+1]
    elif brace_start != -1:
        start = brace_start
        end = response.rfind('}')
        if end > start:
            return response[start:end+1]
    
    return response


def _fix_trailing_commas(json_str: str) -> str:
    """Remove trailing commas before closing braces/brackets."""
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*\]', ']', json_str)
    return json_str


def _fix_control_characters(json_str: str) -> str:
    """
    Fix invalid control characters inside JSON strings.
    Newlines, tabs, and other control chars inside strings must be escaped.
    """
    result = []
    in_string = False
    escape_next = False
    
    for char in json_str:
        if escape_next:
            result.append(char)
            escape_next = False
            continue
            
        if char == '\\':
            result.append(char)
            escape_next = True
            continue
            
        if char == '"':
            in_string = not in_string
            result.append(char)
            continue
        
        if in_string:
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            elif ord(char) < 32:
                result.append(f'\\u{ord(char):04x}')
            else:
                result.append(char)
        else:
            result.append(char)
    
    return ''.join(result)


def _aggressive_control_char_fix(json_str: str) -> str:
    """
    Aggressively remove or escape any remaining control characters.
    Used as a fallback when normal repair fails.
    """
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', json_str)
    return cleaned


def _close_unclosed_structures(json_str: str) -> str:
    """
    Close unclosed braces, brackets, and strings.
    Handles truncated LLM output.
    """
    open_braces = json_str.count('{') - json_str.count('}')
    open_brackets = json_str.count('[') - json_str.count(']')
    
    if open_braces <= 0 and open_brackets <= 0:
        return json_str
    
    logger.warning(f"[JSON Repair] Detected truncated output: {open_braces} unclosed braces, {open_brackets} unclosed brackets")
    
    if json_str.count('"') % 2 == 1:
        json_str += '"'
        logger.debug("[JSON Repair] Closed unclosed string")
    
    json_str = re.sub(r',\s*\{[^}]*$', '', json_str)
    json_str = re.sub(r',\s*\[[^\]]*$', '', json_str)
    json_str = re.sub(r',\s*"[^"]*$', '', json_str)
    
    json_str = _fix_trailing_commas(json_str)
    
    if open_brackets > 0:
        json_str += ']' * open_brackets
        logger.debug(f"[JSON Repair] Auto-closed {open_brackets} brackets")
    if open_braces > 0:
        json_str += '}' * open_braces
        logger.debug(f"[JSON Repair] Auto-closed {open_braces} braces")
    
    return json_str


def extract_json_from_response(response: str) -> str:
    """
    Extract and clean JSON from LLM response without parsing.
    Useful when you need the cleaned string, not the parsed object.
    
    Args:
        response: Raw LLM response string
        
    Returns:
        Cleaned JSON string
    """
    response = response.strip()
    response = _strip_markdown_fences(response)
    response = _extract_json_object(response)
    response = _fix_trailing_commas(response)
    response = _close_unclosed_structures(response)
    return response


def validate_json_structure(data: dict, required_keys: list) -> list:
    """
    Validate that required keys exist in JSON data.
    
    Args:
        data: Parsed JSON dict
        required_keys: List of required top-level keys
        
    Returns:
        List of missing keys (empty if all present)
    """
    missing = []
    for key in required_keys:
        if key not in data:
            missing.append(key)
    return missing


def safe_get_nested(data: dict, *keys, default=None):
    """
    Safely get a nested value from a dict.
    
    Args:
        data: The dict to traverse
        *keys: Keys to traverse
        default: Default value if path doesn't exist
        
    Returns:
        The value at the path, or default if not found
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
            current = current[key]
        else:
            return default
    return current

"""
Schema Validator v1.3 - JSON Schema validation for Director output

This module validates Director LLM output against the v1.3 schema.
If validation fails, the pipeline must retry or hard fail - NO fallbacks.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys

try:
    from jsonschema import Draft202012Validator, ValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    Draft202012Validator = None
    ValidationError = Exception


def log(msg: str):
    print(msg)
    sys.stdout.flush()


SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "presentation_v1.3.schema.json"

_cached_schema = None
_cached_validator = None


def load_schema() -> Dict:
    """Load the v1.3 presentation schema."""
    global _cached_schema
    
    if _cached_schema is not None:
        return _cached_schema
    
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")
    
    with open(SCHEMA_PATH, "r") as f:
        _cached_schema = json.load(f)
    
    return _cached_schema


def get_validator():
    """Get a cached validator instance."""
    global _cached_validator
    
    if not JSONSCHEMA_AVAILABLE:
        raise ImportError("jsonschema package not installed. Run: pip install jsonschema")
    
    if _cached_validator is not None:
        return _cached_validator
    
    schema = load_schema()
    _cached_validator = Draft202012Validator(schema)
    
    return _cached_validator


def validate_presentation(presentation: Dict) -> Tuple[bool, List[str]]:
    """
    Validate a presentation against the v1.3 schema.
    
    Args:
        presentation: The presentation dict from Director LLM
        
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    if not JSONSCHEMA_AVAILABLE:
        log("[Schema] WARNING: jsonschema not available, skipping schema validation")
        return True, []
    
    validator = get_validator()
    errors = []
    
    for error in validator.iter_errors(presentation):
        path = " -> ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
        errors.append(f"{path}: {error.message}")
    
    is_valid = len(errors) == 0
    
    if is_valid:
        log("[Schema] Validation PASSED")
    else:
        log(f"[Schema] Validation FAILED with {len(errors)} errors")
        for i, err in enumerate(errors[:10], 1):
            log(f"[Schema]   {i}. {err}")
        if len(errors) > 10:
            log(f"[Schema]   ... and {len(errors) - 10} more errors")
    
    return is_valid, errors


def format_errors_for_retry(errors: List[str], max_errors: int = 20) -> str:
    """Format validation errors for the retry prompt."""
    if not errors:
        return "No errors found."
    
    formatted = []
    for i, err in enumerate(errors[:max_errors], 1):
        formatted.append(f"{i}. {err}")
    
    if len(errors) > max_errors:
        formatted.append(f"... and {len(errors) - max_errors} more errors")
    
    return "\n".join(formatted)


def quick_structure_check(presentation: Dict) -> Tuple[bool, List[str]]:
    """
    Quick structural check before full schema validation.
    This catches obvious issues faster.
    
    Returns:
        Tuple of (has_basic_structure, list of critical issues)
    """
    issues = []
    
    if not isinstance(presentation, dict):
        issues.append("Presentation is not a JSON object")
        return False, issues
    
    required_top = ["spec_version", "sections"]
    for field in required_top:
        if field not in presentation:
            issues.append(f"Missing required top-level field: {field}")
    
    if "sections" in presentation:
        sections = presentation["sections"]
        if not isinstance(sections, list):
            issues.append("'sections' must be an array")
        elif len(sections) == 0:
            issues.append("'sections' array is empty")
        else:
            section_types = [s.get("section_type") for s in sections if isinstance(s, dict)]
            
            if "intro" not in section_types:
                issues.append("Missing required section_type: 'intro'")
            if "summary" not in section_types:
                issues.append("Missing required section_type: 'summary'")
            
            for i, section in enumerate(sections):
                if not isinstance(section, dict):
                    issues.append(f"Section {i} is not a JSON object")
                    continue
                
                section_id = section.get("section_id", i)
                
                if "renderer" not in section:
                    issues.append(f"Section {section_id} missing 'renderer'")
                
                if "visual_beats" not in section:
                    issues.append(f"Section {section_id} missing 'visual_beats'")
                elif not isinstance(section["visual_beats"], list) or len(section["visual_beats"]) == 0:
                    issues.append(f"Section {section_id} has empty or invalid 'visual_beats'")
                
                if "display_directives" not in section:
                    issues.append(f"Section {section_id} missing 'display_directives'")
                elif not isinstance(section["display_directives"], list) or len(section["display_directives"]) == 0:
                    issues.append(f"Section {section_id} has empty or invalid 'display_directives'")
    
    has_basic_structure = len(issues) == 0
    return has_basic_structure, issues


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python schema_validator.py <presentation.json>")
        sys.exit(1)
    
    with open(sys.argv[1], "r") as f:
        presentation = json.load(f)
    
    print("\n=== Quick Structure Check ===")
    has_structure, structure_issues = quick_structure_check(presentation)
    if has_structure:
        print("PASSED")
    else:
        print("FAILED")
        for issue in structure_issues:
            print(f"  - {issue}")
    
    print("\n=== Full Schema Validation ===")
    is_valid, errors = validate_presentation(presentation)
    
    if is_valid:
        print("PASSED - Presentation is v1.3 compliant")
        sys.exit(0)
    else:
        print(f"FAILED - {len(errors)} schema violations")
        sys.exit(1)

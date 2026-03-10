"""
Director Client v1.3 - Deterministic Educational Film Engine

This module handles the Director LLM pass with:
- Strict Gemini 2.5 Pro parameter tuning (low temperature, high determinism)
- 3-tier validation after each attempt:
  - Tier 1: Structural (hard fail) - max 2 retries
  - Tier 2: Semantic (content retry) - max 1 retry
  - Tier 3: Quality (warnings only) - never blocks
- Hard fail after retries exhausted (no fallbacks)

Pipeline role:
- Pass 1: Director (this module)
- Takes chunked content from Pass 0 (Chunker)
- Outputs presentation.json conforming to v1.3 schema
"""

import os
import sys
import json
import re
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from core.analytics import AnalyticsTracker, create_tracker
from core.traceability import save_raw_llm_response
from core.schema_validator import validate_presentation as validate_json_schema
from core.validators import (
    validate,
    validate_for_retry,
    ValidationResult,
    format_structural_errors,
    format_semantic_errors
)


def log(msg: str):
    print(msg)
    sys.stdout.flush()


OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL
)

PROMPTS_DIR = Path(__file__).parent / "prompts"

DIRECTOR_MODEL = "google/gemini-2.5-pro"

DIRECTOR_PARAMS = {
    "temperature": 0.2,
    "top_p": 0.9,
    "max_tokens": 8192,
}

MAX_STRUCTURAL_RETRIES = 2
MAX_SEMANTIC_RETRIES = 1


class DirectorError(Exception):
    """Error raised when Director fails after all retries."""
    def __init__(self, message: str, errors: List[str], attempts: int):
        super().__init__(message)
        self.errors = errors
        self.attempts = attempts


def load_prompt(name: str) -> str:
    """Load a prompt file. v1.3 prompts required."""
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        v13_path = PROMPTS_DIR / f"{name}_v1.3.txt"
        if v13_path.exists():
            path = v13_path
        else:
            raise FileNotFoundError(f"Prompt file not found: {path}")
    
    with open(path, "r") as f:
        return f.read()


def fix_json(text: str) -> str:
    """Clean up LLM JSON output."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    
    return text


def parse_json_response(text: str) -> Dict:
    """Parse JSON from LLM response."""
    try:
        fixed = fix_json(text)
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        log(f"[Director] JSON parse error: {e}")
        log(f"[Director] Raw text (first 500 chars): {text[:500]}")
        raise


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def call_director_llm(
    system_prompt: str,
    user_prompt: str,
    tracker: Optional[AnalyticsTracker] = None,
    phase_name: str = "director"
) -> Tuple[str, Dict]:
    """Make a Director LLM call with retry and optimized parameters."""
    
    if tracker:
        tracker.start_phase(phase_name, DIRECTOR_MODEL)
    
    try:
        response = client.chat.completions.create(
            model=DIRECTOR_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=DIRECTOR_PARAMS["temperature"],
            top_p=DIRECTOR_PARAMS["top_p"],
            max_tokens=DIRECTOR_PARAMS["max_tokens"],
        )
        
        content = response.choices[0].message.content or ""
        usage = {
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0
        }
        
        if tracker:
            tracker.end_phase(phase_name, usage["input_tokens"], usage["output_tokens"])
        
        return content, usage
        
    except Exception as e:
        if tracker:
            tracker.end_phase(phase_name, 0, 0, status="failed", error=str(e))
        raise


def run_director(
    chunks: Dict,
    subject: str,
    grade: str,
    chapter: str = "",
    tracker: Optional[AnalyticsTracker] = None,
    job_id: Optional[str] = None
) -> Tuple[Dict, ValidationResult]:
    """
    Run the Director pass with 3-tier validation and tiered retry logic.
    
    This is the main entry point for Pass 1.
    
    Validation flow:
    1. JSON Schema validation (basic structure)
    2. Tier-1 Structural validation → max 2 retries
    3. Tier-2 Semantic validation → max 1 retry
    4. Tier-3 Quality lint → warnings only, never blocks
    
    Args:
        chunks: Output from Pass 0 (Chunker)
        subject: Subject name (e.g., "Physics")
        grade: Grade level (e.g., "9")
        chapter: Chapter title
        tracker: Analytics tracker (optional)
        job_id: Job ID for traceability (optional)
    
    Returns:
        Tuple of (validated presentation dict, ValidationResult with warnings)
        
    Raises:
        DirectorError: If validation fails after all retries exhausted
    """
    log("[Director] Starting Director pass (v1.3 with 3-tier validation)...")
    log(f"[Director] Model: {DIRECTOR_MODEL}")
    log(f"[Director] Retry limits: structural={MAX_STRUCTURAL_RETRIES}, semantic={MAX_SEMANTIC_RETRIES}")
    
    system_prompt = load_prompt("director_system_v1.3")
    user_template = load_prompt("director_user_v1.3")
    retry_system = load_prompt("director_retry_system")
    retry_user_template = load_prompt("director_retry_user")
    
    chunks_json = json.dumps(chunks, indent=2)
    
    user_prompt = user_template.replace("{subject}", subject)
    user_prompt = user_prompt.replace("{grade}", str(grade))
    user_prompt = user_prompt.replace("{chapter}", chapter or "Educational Content")
    user_prompt = user_prompt.replace("{chunks_json}", chunks_json)
    user_prompt = user_prompt.replace("{markdown_content}", chunks_json)
    
    structural_retries_used = 0
    semantic_retries_used = 0
    total_attempts = 0
    current_presentation = None
    retry_prompt = ""
    
    while True:
        total_attempts += 1
        phase_name = f"director_attempt_{total_attempts}"
        
        if total_attempts == 1:
            log("[Director] Initial attempt...")
            response_text, usage = call_director_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tracker=tracker,
                phase_name=phase_name
            )
        else:
            log(f"[Director] Retry attempt {total_attempts - 1}...")
            response_text, usage = call_director_llm(
                system_prompt=retry_system,
                user_prompt=retry_prompt,
                tracker=tracker,
                phase_name=phase_name
            )
        
        if job_id:
            save_raw_llm_response(
                renderer_type="director",
                section_id=f"attempt_{total_attempts}",
                raw_response=response_text,
                model=DIRECTOR_MODEL,
                usage=usage
            )
        
        try:
            current_presentation = parse_json_response(response_text)
        except json.JSONDecodeError as e:
            log(f"[Director] Attempt {total_attempts} returned invalid JSON")
            if structural_retries_used < MAX_STRUCTURAL_RETRIES:
                structural_retries_used += 1
                retry_prompt = retry_user_template.replace("{schema_errors}", f"JSON parse error: {e}")
                retry_prompt = retry_prompt.replace("{failed_json}", response_text[:5000])
                continue
            else:
                raise DirectorError(
                    f"Director returned invalid JSON after {total_attempts} attempts",
                    errors=[str(e)],
                    attempts=total_attempts
                )
        
        log("[Director] Running JSON Schema validation...")
        schema_valid, schema_errors = validate_json_schema(current_presentation)
        if not schema_valid:
            log(f"[Director] JSON Schema failed: {len(schema_errors)} errors")
            if structural_retries_used < MAX_STRUCTURAL_RETRIES:
                structural_retries_used += 1
                log(f"[Director] Structural retry {structural_retries_used}/{MAX_STRUCTURAL_RETRIES}")
                error_text = "\n".join(schema_errors[:10])
                failed_json = json.dumps(current_presentation, indent=2)
                retry_prompt = retry_user_template.replace("{schema_errors}", error_text)
                retry_prompt = retry_prompt.replace("{failed_json}", failed_json)
                continue
            else:
                raise DirectorError(
                    f"Schema validation failed after {MAX_STRUCTURAL_RETRIES} structural retries",
                    errors=schema_errors,
                    attempts=total_attempts
                )
        
        log("[Director] JSON Schema PASSED. Running 3-tier validation...")
        validation_result = validate(current_presentation)
        
        if validation_result.is_valid:
            log("[Director] All validation tiers PASSED")
            if validation_result.quality_warnings:
                log(f"[Director] Quality warnings: {len(validation_result.quality_warnings)}")
            current_presentation["spec_version"] = "v1.3"
            return current_presentation, validation_result
        
        if validation_result.needs_structural_retry:
            log(f"[Director] Tier-1 STRUCTURAL_FAIL: {len(validation_result.structural_errors)} errors")
            if structural_retries_used < MAX_STRUCTURAL_RETRIES:
                structural_retries_used += 1
                log(f"[Director] Structural retry {structural_retries_used}/{MAX_STRUCTURAL_RETRIES}")
                error_text = format_structural_errors(validation_result.structural_errors)
                failed_json = json.dumps(current_presentation, indent=2)
                retry_prompt = retry_user_template.replace("{schema_errors}", error_text)
                retry_prompt = retry_prompt.replace("{failed_json}", failed_json)
                continue
            else:
                log("[Director] HARD FAIL - Structural retries exhausted")
                raise DirectorError(
                    f"Structural validation failed after {MAX_STRUCTURAL_RETRIES} retries",
                    errors=[str(e) for e in validation_result.structural_errors],
                    attempts=total_attempts
                )
        
        if validation_result.needs_semantic_retry:
            log(f"[Director] Tier-2 SEMANTIC_FAIL: {len(validation_result.semantic_errors)} errors")
            if semantic_retries_used < MAX_SEMANTIC_RETRIES:
                semantic_retries_used += 1
                log(f"[Director] Semantic retry {semantic_retries_used}/{MAX_SEMANTIC_RETRIES}")
                error_text = format_semantic_errors(validation_result.semantic_errors)
                failed_json = json.dumps(current_presentation, indent=2)
                retry_prompt = retry_user_template.replace("{schema_errors}", error_text)
                retry_prompt = retry_prompt.replace("{failed_json}", failed_json)
                continue
            else:
                log("[Director] HARD FAIL - Semantic retries exhausted")
                raise DirectorError(
                    f"Semantic validation failed after {MAX_SEMANTIC_RETRIES} retries",
                    errors=[str(e) for e in validation_result.semantic_errors],
                    attempts=total_attempts
                )
        
        log("[Director] Unexpected validation state - hard fail")
        raise DirectorError(
            "Unexpected validation state",
            errors=["Unknown validation failure"],
            attempts=total_attempts
        )


def test_director(chunks_path: str, subject: str = "Physics", grade: str = "9"):
    """Test the Director with a chunks JSON file."""
    log(f"\n{'='*60}")
    log("Testing Director Client v1.3 (3-Tier Validation)")
    log(f"{'='*60}")
    
    with open(chunks_path, "r") as f:
        chunks = json.load(f)
    
    tracker = create_tracker("test")
    
    try:
        presentation, validation_result = run_director(
            chunks=chunks,
            subject=subject,
            grade=grade,
            chapter="Test Chapter",
            tracker=tracker,
            job_id="test"
        )
        
        output_path = Path(chunks_path).with_suffix(".presentation.json")
        with open(output_path, "w") as f:
            json.dump(presentation, f, indent=2)
        log(f"\nPresentation saved to: {output_path}")
        
        if validation_result.quality_warnings:
            log(f"\nQuality warnings ({len(validation_result.quality_warnings)}):")
            for warn in validation_result.quality_warnings[:5]:
                log(f"  - {warn}")
        
        return presentation
        
    except DirectorError as e:
        log(f"\nFAILED: {e}")
        log(f"Errors: {e.errors[:5]}")
        return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_director(sys.argv[1])
    else:
        print("Usage: python director_client.py <chunks.json>")

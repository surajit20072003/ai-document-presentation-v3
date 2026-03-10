"""
LLM Client v1.3 - Deterministic Educational Film Engine

Pipeline Phases:
- Pass 0: Chunker (Gemini 2.5 Flash) - Split markdown into clean chunks
- Pass 1: Director (Gemini 2.5 Pro) - Create pedagogy, structure, timing, display_directives
- Pass 2: Renderers - Deterministic rendering (NO creative LLM decisions):
    - Manim Renderer (Claude 3.5 Sonnet) - Math/physics code from manim_scene_spec
    - Remotion Renderer (Claude 3.5 Sonnet) - Motion graphics (when enabled)
    - Video Renderer (Gemini 2.5 Pro) - WAN prompts from visual_beats

v1.3 Key Changes:
- display_directives for every narration segment (text_layer, visual_layer, avatar_layer)
- Mandatory intro, summary, memory, recap sections (hard fail if missing)
- Avatar rules per section type (intro=center/large, content=side, recap=hidden)
- Manim sections MUST have manim_scene_spec - prose-only = HARD FAILURE
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from core.analytics import AnalyticsTracker, create_tracker
from core.traceability import save_raw_llm_response


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
SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"

MODELS = {
    "chunker": "google/gemini-2.5-flash",
    "director": "google/gemini-2.5-pro",
    "manim_renderer": "anthropic/claude-sonnet-4",
    "remotion_renderer": "anthropic/claude-sonnet-4",
    "video_renderer": "google/gemini-2.5-pro"
}

DIRECTOR_PARALLEL_MODELS = [
    "google/gemini-2.5-pro",
    "anthropic/claude-sonnet-4",
    "google/gemini-2.0-flash-001",
]

ENABLE_PARALLEL_DIRECTOR = True
ENABLE_STRUCTURED_OUTPUT = True


class PipelineError(Exception):
    """Error raised when pipeline fails."""
    def __init__(self, message: str, phase: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.phase = phase
        self.details = details or {}


def load_prompt(name: str, version: str = "v1.3") -> str:
    """Load a prompt file. Falls back to v1.2 if v1.3 doesn't exist."""
    path = PROMPTS_DIR / f"{name}_{version}.txt"
    if not path.exists():
        fallback_path = PROMPTS_DIR / f"{name}_v1.2.txt"
        if fallback_path.exists():
            log(f"[Prompts] Using v1.2 fallback for {name}")
            path = fallback_path
        else:
            raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(path, "r") as f:
        return f.read()


def fix_json(text: str) -> str:
    """Clean up LLM JSON output with robust error handling."""
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
    
    text = re.sub(r"(?<!\\)'([^']*)'(?=\s*:)", r'"\1"', text)
    
    text = re.sub(r':\s*\'([^\']*)\'\s*([,}\]])', r': "\1"\2', text)
    
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('//') or stripped.startswith('#'):
            continue
        cleaned_lines.append(line)
    text = '\n'.join(cleaned_lines)
    
    if not text.strip().endswith('}') and not text.strip().endswith(']'):
        brace_count = text.count('{') - text.count('}')
        bracket_count = text.count('[') - text.count(']')
        text = text.rstrip().rstrip(',')
        text += ']' * bracket_count + '}' * brace_count
        log(f"[JSON Fix] Auto-closed {brace_count} braces, {bracket_count} brackets")
    
    return text


def parse_json_response(text: str, phase: str) -> Dict:
    """Parse JSON from LLM response with error handling."""
    try:
        fixed = fix_json(text)
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        log(f"[{phase}] JSON parse error: {e}")
        log(f"[{phase}] Raw text (first 500 chars): {text[:500]}")
        raise PipelineError(f"Failed to parse JSON from {phase}", phase, {"error": str(e)})


def load_director_schema() -> Dict:
    """Load simplified JSON schema for structured output."""
    schema_path = SCHEMAS_DIR / "presentation_v1.3.schema.json"
    if schema_path.exists():
        with open(schema_path, "r") as f:
            return json.load(f)
    return {}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def call_llm(
    model: str,
    system_prompt: str,
    user_prompt: str,
    phase: str,
    tracker: Optional[AnalyticsTracker] = None,
    max_tokens: int = 16000,
    temperature: float = 0.3,
    response_format: Optional[Dict] = None
) -> Tuple[str, Dict]:
    """Make an LLM call with retry and analytics tracking.
    
    Args:
        response_format: Optional dict for structured output, e.g.:
            {"type": "json_object"} for basic JSON mode
            {"type": "json_schema", "json_schema": {...}} for strict schema
    """
    
    if tracker:
        tracker.start_phase(phase, model)
    
    try:
        create_kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if response_format:
            create_kwargs["response_format"] = response_format
            create_kwargs["extra_body"] = {
                "provider": {
                    "require_parameters": True
                }
            }
        
        response = client.chat.completions.create(**create_kwargs)
        
        content = response.choices[0].message.content or ""
        usage = {
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0
        }
        
        if tracker:
            tracker.end_phase(phase, usage["input_tokens"], usage["output_tokens"])
        
        return content, usage
        
    except Exception as e:
        if tracker:
            tracker.end_phase(phase, 0, 0, status="failed", error=str(e))
        raise


def pass0_chunker(
    markdown_content: str,
    tracker: Optional[AnalyticsTracker] = None
) -> Dict:
    """Pass 0: Split markdown into teachable chunks."""
    log("[Parse] Starting Chunker...")
    
    system_prompt = load_prompt("chunker_system")
    user_template = load_prompt("chunker_user")
    user_prompt = user_template.replace("{markdown_content}", markdown_content)
    
    response_text, usage = call_llm(
        model=MODELS["chunker"],
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        phase="chunker",
        tracker=tracker
    )
    
    chunks = parse_json_response(response_text, "chunker")
    
    if "chunks" not in chunks:
        if isinstance(chunks, list):
            chunks = {"chunks": chunks}
        else:
            raise PipelineError("Chunker output missing 'chunks' array", "chunker")
    
    chunk_count = len(chunks.get("chunks", []))
    log(f"[Parse] Chunker complete: {chunk_count} chunks created")
    
    return chunks


MAX_STRUCTURAL_RETRIES = 4
MAX_SEMANTIC_RETRIES = 2


def get_director_response_format() -> Optional[Dict]:
    """Get structured output format for Director if enabled."""
    if not ENABLE_STRUCTURED_OUTPUT:
        return None
    
    return {
        "type": "json_object"
    }


def call_director_single_model(
    model: str,
    system_prompt: str,
    user_prompt: str,
    tracker: Optional[AnalyticsTracker],
    phase_suffix: str = ""
) -> Tuple[str, Dict, str]:
    """Call a single model for Director and return (response, usage, model_name)."""
    phase_name = f"director_{model.split('/')[-1]}{phase_suffix}"
    
    response_format = get_director_response_format()
    
    response_text, usage = call_llm(
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        phase=phase_name,
        tracker=tracker,
        max_tokens=32000,
        temperature=0.2,
        response_format=response_format
    )
    
    return response_text, usage, model


def call_director_parallel(
    system_prompt: str,
    user_prompt: str,
    tracker: Optional[AnalyticsTracker] = None,
    phase_suffix: str = ""
) -> Tuple[str, Dict, str]:
    """Fire multiple Director models in parallel, return first successful response.
    
    Uses a race pattern: all models start simultaneously, we take the first
    response that parses as valid JSON.
    """
    if not ENABLE_PARALLEL_DIRECTOR or len(DIRECTOR_PARALLEL_MODELS) <= 1:
        model = MODELS["director"]
        log(f"[Direct] Using single model: {model}")
        return call_director_single_model(
            model, system_prompt, user_prompt, tracker, phase_suffix
        )
    
    log(f"[Direct] Parallel mode: firing {len(DIRECTOR_PARALLEL_MODELS)} models...")
    
    results = []
    errors = []
    
    with ThreadPoolExecutor(max_workers=len(DIRECTOR_PARALLEL_MODELS)) as executor:
        futures = {
            executor.submit(
                call_director_single_model,
                model, system_prompt, user_prompt, tracker, phase_suffix
            ): model
            for model in DIRECTOR_PARALLEL_MODELS
        }
        
        for future in as_completed(futures):
            model = futures[future]
            try:
                response_text, usage, model_name = future.result()
                
                try:
                    fixed = fix_json(response_text)
                    parsed = json.loads(fixed)
                    
                    if "sections" in parsed or "lesson_plan" in parsed or "topics" in parsed:
                        log(f"[Direct] Winner: {model_name} (valid JSON with sections)")
                        return response_text, usage, model_name
                    else:
                        log(f"[Direct] {model_name}: JSON valid but missing sections key")
                        results.append((response_text, usage, model_name))
                        
                except json.JSONDecodeError as e:
                    log(f"[Direct] {model_name}: JSON parse error - {e}")
                    errors.append((model_name, str(e)))
                    
            except Exception as e:
                log(f"[Direct] {model}: API error - {e}")
                errors.append((model, str(e)))
    
    if results:
        log(f"[Direct] Using first result (missing ideal structure)")
        return results[0]
    
    error_summary = "; ".join([f"{m}: {e}" for m, e in errors[:3]])
    raise PipelineError(f"All parallel Director models failed: {error_summary}", "director")


def pass1_director(
    chunks: Dict,
    subject: str,
    grade: str,
    chapter: str = "",
    tracker: Optional[AnalyticsTracker] = None
) -> Dict:
    """Pass 1: Create pedagogy, structure, timing, renderer choices.
    
    Includes 3-tier validation with tiered retries:
    - Tier 1 Structural: max 2 retries
    - Tier 2 Semantic: max 1 retry
    - Tier 3 Quality: warnings only (non-blocking)
    """
    from core.validators import validate as validate_3tier, format_structural_errors, format_semantic_errors
    
    log("[Direct] Starting Director (with 3-tier validation)...")
    
    system_prompt = load_prompt("director_system")
    user_template = load_prompt("director_user")
    retry_system = load_prompt("director_retry_system")
    retry_user_template = load_prompt("director_retry_user")
    
    chunks_json = json.dumps(chunks, indent=2)
    
    user_prompt = user_template.replace("{subject}", subject)
    user_prompt = user_prompt.replace("{grade}", str(grade))
    user_prompt = user_prompt.replace("{chapter}", chapter or "Educational Content")
    user_prompt = user_prompt.replace("{chunks_json}", chunks_json)
    
    structural_retries_used = 0
    semantic_retries_used = 0
    total_attempts = 0
    retry_prompt = ""
    presentation = None
    
    while True:
        total_attempts += 1
        phase_name = f"director" if total_attempts == 1 else f"director_retry_{total_attempts - 1}"
        
        if total_attempts == 1:
            log("[Direct] Initial attempt (parallel mode)...")
            response_text, usage, winning_model = call_director_parallel(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tracker=tracker,
                phase_suffix=""
            )
            log(f"[Direct] Using response from: {winning_model}")
        else:
            log(f"[Direct] Retry attempt {total_attempts - 1}...")
            response_format = get_director_response_format()
            response_text, usage = call_llm(
                model=MODELS["director"],
                system_prompt=retry_system,
                user_prompt=retry_prompt,
                phase=phase_name,
                tracker=tracker,
                max_tokens=32000,
                temperature=0.2,
                response_format=response_format
            )
        
        try:
            presentation = parse_json_response(response_text, "director")
        except Exception as e:
            log(f"[Direct] Attempt {total_attempts} returned invalid JSON: {e}")
            if structural_retries_used < MAX_STRUCTURAL_RETRIES:
                structural_retries_used += 1
                retry_prompt = retry_user_template.replace("{schema_errors}", f"JSON parse error: {e}")
                retry_prompt = retry_prompt.replace("{failed_json}", response_text[:5000])
                continue
            else:
                raise PipelineError(f"Director returned invalid JSON after {total_attempts} attempts", "director")
        
        if "sections" not in presentation:
            if "lesson_plan" in presentation:
                presentation["sections"] = presentation.pop("lesson_plan")
            elif "plan" in presentation:
                presentation["sections"] = presentation.pop("plan")
            elif "topics" in presentation:
                presentation["sections"] = presentation.pop("topics")
            else:
                log(f"[Direct] ERROR: Director returned keys: {list(presentation.keys())}")
                if structural_retries_used < MAX_STRUCTURAL_RETRIES:
                    structural_retries_used += 1
                    retry_prompt = retry_user_template.replace("{schema_errors}", "Missing 'sections' array in output")
                    retry_prompt = retry_prompt.replace("{failed_json}", json.dumps(presentation, indent=2)[:5000])
                    continue
                else:
                    raise PipelineError("Director output missing 'sections' array", "director")
        
        log(f"[Direct] Running 3-tier validation...")
        validation_result = validate_3tier(presentation)
        
        if validation_result.is_valid:
            log("[Direct] All validation tiers PASSED")
            if validation_result.quality_warnings:
                log(f"[Direct] Quality warnings: {len(validation_result.quality_warnings)}")
            break
        
        if validation_result.needs_structural_retry:
            log(f"[Direct] Tier-1 STRUCTURAL_FAIL: {len(validation_result.structural_errors)} errors")
            if structural_retries_used < MAX_STRUCTURAL_RETRIES:
                structural_retries_used += 1
                log(f"[Direct] Structural retry {structural_retries_used}/{MAX_STRUCTURAL_RETRIES}")
                error_text = format_structural_errors(validation_result.structural_errors)
                failed_json = json.dumps(presentation, indent=2)
                retry_prompt = retry_user_template.replace("{schema_errors}", error_text)
                retry_prompt = retry_prompt.replace("{failed_json}", failed_json)
                continue
            else:
                log("[Direct] HARD FAIL - Structural retries exhausted")
                raise PipelineError(
                    f"Structural validation failed after {MAX_STRUCTURAL_RETRIES} retries",
                    "director",
                    {"errors": [str(e) for e in validation_result.structural_errors]}
                )
        
        if validation_result.needs_semantic_retry:
            log(f"[Direct] Tier-2 SEMANTIC_FAIL: {len(validation_result.semantic_errors)} errors")
            if semantic_retries_used < MAX_SEMANTIC_RETRIES:
                semantic_retries_used += 1
                log(f"[Direct] Semantic retry {semantic_retries_used}/{MAX_SEMANTIC_RETRIES}")
                error_text = format_semantic_errors(validation_result.semantic_errors)
                failed_json = json.dumps(presentation, indent=2)
                retry_prompt = retry_user_template.replace("{schema_errors}", error_text)
                retry_prompt = retry_prompt.replace("{failed_json}", failed_json)
                continue
            else:
                log("[Direct] HARD FAIL - Semantic retries exhausted")
                raise PipelineError(
                    f"Semantic validation failed after {MAX_SEMANTIC_RETRIES} retries",
                    "director",
                    {"errors": [str(e) for e in validation_result.semantic_errors]}
                )
        
        log("[Direct] Unexpected validation state - passing through")
        break
    
    section_count = len(presentation.get("sections", []))
    log(f"[Direct] Director complete: {section_count} sections created")
    
    RENDERER_FIELDS = ["manim_scene_spec", "remotion_scene_spec", "video_prompts", "wan_prompt"]
    stripped_count = 0
    renderer_counts = {}
    for section in presentation.get("sections", []):
        for rf in RENDERER_FIELDS:
            if rf in section:
                del section[rf]
                stripped_count += 1
        
        renderer = section.get("renderer", "unknown")
        if isinstance(renderer, dict):
            renderer = renderer.get("type", renderer.get("name", "unknown"))
            section["renderer"] = renderer
        renderer_counts[str(renderer)] = renderer_counts.get(str(renderer), 0) + 1
    
    if stripped_count > 0:
        log(f"[Direct] WARNING: Stripped {stripped_count} renderer fields from Director output (v1.2 violation)")
    log(f"[Direct] Renderer distribution: {renderer_counts}")
    
    return presentation


def pass2_manim_renderer(
    section: Dict,
    tracker: Optional[AnalyticsTracker] = None
) -> Dict:
    """Pass 2a: Generate manim_scene_spec for a section."""
    section_id = section.get("section_id") or section.get("id", 0)
    log(f"[Render:Manim] Section {section_id}...")
    
    system_prompt = load_prompt("manim_renderer_system")
    user_template = load_prompt("manim_renderer_user")
    
    section_json = json.dumps(section, indent=2)
    user_prompt = user_template.replace("{section_json}", section_json)
    
    response_text, usage = call_llm(
        model=MODELS["manim_renderer"],
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        phase=f"manim_renderer_s{section_id}",
        tracker=tracker
    )
    
    save_raw_llm_response(
        renderer_type="manim",
        section_id=str(section_id),
        raw_response=response_text,
        model=MODELS["manim_renderer"],
        usage=usage
    )
    
    result = parse_json_response(response_text, f"manim_renderer_s{section_id}")
    
    if "manim_scene_spec" not in result:
        raise PipelineError(
            f"Manim renderer failed to generate scene_spec for section {section_id}",
            "manim_renderer",
            {"section_id": section_id}
        )
    
    log(f"[Render:Manim] Scene spec generated for section {section_id}")
    return result


def validate_remotion_output(response_text: str, section_id: int) -> tuple:
    """Validate Remotion renderer output is valid JSON with required structure.
    
    Returns: (is_valid, result_or_error_message)
    """
    if not response_text or not response_text.strip():
        return False, "Empty response"
    
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)
    
    try:
        result = parse_json_response(cleaned, f"remotion_renderer_s{section_id}")
        if "remotion_scene_spec" not in result:
            return False, "Missing remotion_scene_spec in response"
        return True, result
    except Exception as e:
        return False, str(e)


def pass2_remotion_renderer(
    section: Dict,
    tracker: Optional[AnalyticsTracker] = None,
    max_retries: int = 1
) -> Dict:
    """Pass 2b: Generate remotion_scene_spec for a section.
    
    v1.3 CHANGE: Added validation with single retry on parse failure.
    """
    section_id = section.get("section_id") or section.get("id", 0)
    log(f"[Render:Remotion] Section {section_id}...")
    
    system_prompt = load_prompt("remotion_renderer_system")
    user_template = load_prompt("remotion_renderer_user")
    
    section_json = json.dumps(section, indent=2)
    user_prompt = user_template.replace("{section_json}", section_json)
    
    last_error = "No attempts made"
    for attempt in range(max_retries + 1):
        phase_name = f"remotion_renderer_s{section_id}" if attempt == 0 else f"remotion_renderer_s{section_id}_retry{attempt}"
        
        response_text, usage = call_llm(
            model=MODELS["remotion_renderer"],
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            phase=phase_name,
            tracker=tracker
        )
        
        save_raw_llm_response(
            renderer_type="remotion",
            section_id=str(section_id) if attempt == 0 else f"{section_id}_retry{attempt}",
            raw_response=response_text,
            model=MODELS["remotion_renderer"],
            usage=usage
        )
        
        is_valid, result_or_error = validate_remotion_output(response_text, section_id)
        
        if is_valid:
            log(f"[Render:Remotion] Scene spec generated for section {section_id}")
            return result_or_error
        
        last_error = result_or_error
        if attempt < max_retries:
            log(f"[Render:Remotion] Section {section_id} parse failed: {result_or_error}. Retrying ({attempt + 1}/{max_retries})...")
        else:
            log(f"[Render:Remotion] Section {section_id} FAILED after {max_retries + 1} attempts: {result_or_error}")
    
    raise PipelineError(
        f"Remotion renderer failed to generate valid JSON for section {section_id} after {max_retries + 1} attempts",
        "remotion_renderer",
        {"section_id": section_id, "last_error": last_error}
    )


VAGUE_PHRASES = [
    "clear diagram",
    "appropriate animation",
    "educational visualization",
    "relevant imagery",
    "suitable graphics",
    "show a diagram of",
    "illustrate the concept",
    "visual representation",
    "display showing",
    "demonstrate the",
    "animation explaining",
    "etc",
    "and so on",
    "and more",
]

MIN_WAN_PROMPT_WORDS = 100


def validate_video_prompts(result: Dict, section_id: int) -> tuple:
    """Validate video renderer output meets WAN requirements.
    
    Checks:
    1. video_prompts key exists
    2. Each prompt has at least MIN_WAN_PROMPT_WORDS words
    3. No vague phrases
    
    Returns: (is_valid, error_message_or_none)
    """
    if "video_prompts" not in result:
        return False, "Missing video_prompts key"
    
    prompts = result["video_prompts"]
    if not prompts or len(prompts) == 0:
        return False, "Empty video_prompts array"
    
    issues = []
    for i, beat in enumerate(prompts):
        prompt_text = beat.get("prompt", "")
        word_count = len(prompt_text.split())
        
        if word_count < MIN_WAN_PROMPT_WORDS:
            issues.append(f"Beat {i + 1}: {word_count} words (minimum {MIN_WAN_PROMPT_WORDS})")
        
        prompt_lower = prompt_text.lower()
        for vague in VAGUE_PHRASES:
            if vague in prompt_lower:
                issues.append(f"Beat {i + 1}: Contains vague phrase '{vague}'")
                break
    
    if issues:
        return False, "; ".join(issues)
    
    return True, None


def pass2_video_renderer(
    section: Dict,
    tracker: Optional[AnalyticsTracker] = None,
    max_retries: int = 2
) -> Dict:
    """Pass 2c: Generate video prompts for a section.
    
    v1.3 CHANGE: Added validation for word count and vague phrases with retry.
    v1.4 CHANGE: Increased max_retries to 2 (3 total attempts) for better 300+ word compliance.
    """
    section_id = section.get("section_id") or section.get("id", 0)
    log(f"[Render:Video] Section {section_id}...")
    
    system_prompt = load_prompt("video_renderer_system")
    user_template = load_prompt("video_renderer_user")
    
    section_json = json.dumps(section, indent=2)
    user_prompt = user_template.replace("{section_json}", section_json)
    
    last_error = "No attempts made"
    for attempt in range(max_retries + 1):
        phase_name = f"video_renderer_s{section_id}" if attempt == 0 else f"video_renderer_s{section_id}_retry{attempt}"
        
        response_text, usage = call_llm(
            model=MODELS["video_renderer"],
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            phase=phase_name,
            tracker=tracker
        )
        
        save_raw_llm_response(
            renderer_type="video",
            section_id=str(section_id) if attempt == 0 else f"{section_id}_retry{attempt}",
            raw_response=response_text,
            model=MODELS["video_renderer"],
            usage=usage
        )
        
        try:
            result = parse_json_response(response_text, phase_name)
        except Exception as e:
            if attempt < max_retries:
                log(f"[Render:Video] Section {section_id} JSON parse failed: {e}. Retrying...")
                continue
            else:
                log(f"[Render:Video] Section {section_id} FAILED: Could not parse JSON")
                return {"video_prompts": []}
        
        is_valid, error = validate_video_prompts(result, section_id)
        
        if is_valid:
            log(f"[Render:Video] Prompts generated for section {section_id} ({len(result.get('video_prompts', []))} beats)")
            return result
        
        last_error = error
        if attempt < max_retries:
            log(f"[Render:Video] Section {section_id} validation failed: {error}. Retrying ({attempt + 1}/{max_retries})...")
        else:
            log(f"[Render:Video] Section {section_id} validation FAILED after {max_retries + 1} attempts: {error}")
    
    raise PipelineError(
        f"WAN renderer failed validation for section {section_id} after {max_retries + 1} attempts: {last_error}",
        "video_renderer",
        {"section_id": section_id, "last_error": last_error}
    )


def pass2_dispatch_renderers(
    presentation: Dict,
    tracker: Optional[AnalyticsTracker] = None,
    use_remotion: bool = True
) -> Dict:
    """Dispatch Render phase to appropriate renderers based on section renderer choice.
    
    v1.3 CHANGE: Director decides renderer. Pipeline obeys. No collapse logic.
    All sections (including intro/summary/memory) now have renderers assigned.
    
    Args:
        use_remotion: v1.3 defaults to True - Remotion is now a required renderer.
    """
    log("[Render v1.3] Dispatching to renderers (Director decides, pipeline obeys)...")
    
    sections = presentation.get("sections", [])
    
    for i, section in enumerate(sections):
        section_id = section.get("section_id") or section.get("id", i + 1)
        renderer = section.get("renderer", "")
        if isinstance(renderer, dict):
            renderer = renderer.get("type", renderer.get("name", ""))
        renderer = str(renderer).lower()
        section_type = section.get("section_type", "")
        
        log(f"[Render v1.3] Section {section_id} ({section_type}): renderer='{renderer}'")
        
        try:
            if renderer == "manim":
                result = pass2_manim_renderer(section, tracker)
                section["manim_scene_spec"] = result.get("manim_scene_spec")
                
            elif renderer == "remotion":
                result = pass2_remotion_renderer(section, tracker)
                section["remotion_scene_spec"] = result.get("remotion_scene_spec")
                
            elif renderer in ["video", "wan", "wan_video"]:
                result = pass2_video_renderer(section, tracker)
                if "video_prompts" in result:
                    section["video_prompts"] = result.get("video_prompts")
                elif "wan_prompt" in result:
                    section["video_prompts"] = [result]
                else:
                    section["video_prompts"] = result
                    
            else:
                log(f"[Render v1.3] WARN: Section {section_id} has unknown renderer '{renderer}'")
                
        except PipelineError as e:
            log(f"[Render v1.3] ERROR in section {section_id}: {e}")
            section["renderer_error"] = str(e)
    
    render_success = 0
    render_errors = 0
    for section in sections:
        section_id = section.get("section_id") or section.get("id", "?")
        renderer = str(section.get("renderer", "")).lower()
        
        if "renderer_error" in section:
            render_errors += 1
            continue
            
        if renderer == "manim" and not section.get("manim_scene_spec"):
            log(f"[Render v1.3] FAIL: Section {section_id} missing manim_scene_spec after render")
            section["renderer_error"] = "manim_scene_spec not generated"
            render_errors += 1
        elif renderer == "remotion" and not section.get("remotion_scene_spec"):
            log(f"[Render v1.3] FAIL: Section {section_id} missing remotion_scene_spec after render")
            section["renderer_error"] = "remotion_scene_spec not generated"
            render_errors += 1
        elif renderer in ["video", "wan", "wan_video"] and not section.get("video_prompts"):
            log(f"[Render v1.3] FAIL: Section {section_id} missing video_prompts after render")
            section["renderer_error"] = "video_prompts not generated"
            render_errors += 1
        else:
            render_success += 1
    
    log(f"[Render v1.3] Dispatch complete: {render_success} success, {render_errors} errors")
    return presentation


def generate_presentation_v12(
    markdown_content: str,
    subject: str = "General Science",
    grade: str = "9",
    chapter: str = "",
    use_remotion: bool = True
) -> Tuple[Dict, AnalyticsTracker]:
    """
    Main entry point for v1.3 3-phase pipeline (Parse → Direct → Render).
    
    v1.3 CHANGE: use_remotion defaults to True. Director decides renderer.
    
    Returns:
        Tuple of (presentation dict, analytics tracker)
    """
    import uuid
    job_id = str(uuid.uuid4())[:8]
    
    tracker = create_tracker(job_id)
    tracker.start_pipeline()
    
    try:
        chunks = pass0_chunker(markdown_content, tracker)
        
        presentation = pass1_director(chunks, subject, grade, chapter, tracker)
        
        presentation = pass2_dispatch_renderers(presentation, tracker, use_remotion=use_remotion)
        
        presentation["subject"] = subject
        presentation["grade"] = grade
        presentation["pipeline_version"] = "1.2"
        presentation["job_id"] = job_id
        
        tracker.end_pipeline(status="completed")
        tracker.print_summary()
        
        return presentation, tracker
        
    except Exception as e:
        tracker.end_pipeline(status="failed", error=str(e))
        tracker.print_summary()
        raise


def test_pipeline(markdown_path: str, subject: str = "General Science", grade: str = "9"):
    """Test the v1.2 pipeline with a markdown file."""
    log(f"\n{'='*60}")
    log("Testing v1.2 3-Pass Pipeline")
    log(f"{'='*60}")
    log(f"Input: {markdown_path}")
    log(f"Subject: {subject}, Grade: {grade}")
    log(f"{'='*60}\n")
    
    with open(markdown_path, "r") as f:
        content = f.read()
    
    presentation, tracker = generate_presentation_v12(content, subject, grade)
    
    output_path = Path(markdown_path).with_suffix(".presentation.json")
    with open(output_path, "w") as f:
        json.dump(presentation, f, indent=2)
    log(f"\nPresentation saved to: {output_path}")
    
    analytics_path = Path(markdown_path).with_suffix(".analytics.json")
    tracker.save_to_file(str(analytics_path))
    log(f"Analytics saved to: {analytics_path}")
    
    return presentation, tracker


def rerender_sections_wan(
    presentation: Dict,
    section_ids: List[int],
    tracker: Optional[AnalyticsTracker] = None
) -> Dict:
    """Re-render specific sections using WAN video renderer.
    
    Overrides the renderer to 'wan_video' for specified sections and regenerates video_prompts.
    
    Args:
        presentation: The presentation dict with sections
        section_ids: List of section IDs to re-render
        tracker: Optional analytics tracker
        
    Returns:
        Updated presentation dict with new video_prompts
    """
    log(f"[ReRender] Re-rendering sections {section_ids} with WAN...")
    
    sections = presentation.get("sections", [])
    
    for section in sections:
        section_id = section.get("section_id") or section.get("id", 0)
        
        if section_id not in section_ids:
            continue
            
        log(f"[ReRender] Section {section_id}: Overriding renderer to 'wan_video'")
        old_renderer = section.get("renderer", "none")
        section["renderer"] = "wan_video"
        section["renderer_override"] = f"Changed from {old_renderer} to wan_video for re-render"
        
        try:
            result = pass2_video_renderer(section, tracker)
            
            if "video_prompts" in result:
                section["video_prompts"] = result.get("video_prompts")
                section["has_content_video"] = True
                log(f"[ReRender] Section {section_id}: Generated {len(section['video_prompts'])} video prompts")
            else:
                log(f"[ReRender] Section {section_id}: No video_prompts in result")
                
        except PipelineError as e:
            log(f"[ReRender] Section {section_id} ERROR: {e}")
            section["renderer_error"] = str(e)
    
    return presentation


def generate_presentation_v14_hybrid(
    markdown_content: str,
    subject: str = "General Science",
    grade: str = "9",
    chapter: str = "",
    use_remotion: bool = True,
    status_callback: Optional[callable] = None
) -> Tuple[Dict, AnalyticsTracker]:
    """
    V1.4 HYBRID: Split Directors + V1.3 Rendering Infrastructure.
    
    This function uses the v1.4 Split Director approach (Content Director + Recap Director)
    while keeping the v1.3 rendering pipeline (Manim, Remotion, WAN).
    
    Pipeline:
    - Pass 0: Chunker (same as v1.3)
    - Pass 1a: Content Director (intro, summary, content, example, quiz)
    - Pass 1b: Recap Director (memory + 5 recap scenes)
    - Merge: Combine Content + Recap outputs (returns full presentation Dict)
    - Pass 2: Dispatch Renderers (same as v1.3)
    
    Args:
        markdown_content: Source markdown
        subject: Subject area
        grade: Grade level
        chapter: Chapter name
        use_remotion: Enable Remotion renderer
        status_callback: Optional callback(phase, message) for progress updates
    
    Returns:
        Tuple of (presentation dict, analytics tracker)
    """
    from core.smart_chunker import call_smart_chunker
    from core.content_director import call_content_director
    from core.recap_director import call_recap_director
    from core.merge_step import merge_director_outputs
    
    import uuid
    job_id = str(uuid.uuid4())[:8]
    
    tracker = create_tracker(job_id)
    tracker.start_pipeline()
    
    def update_status(phase: str, message: str):
        """Internal helper to call status callback if provided."""
        log(f"[V1.4 Hybrid] {phase}: {message}")
        if status_callback:
            try:
                status_callback(phase, message)
            except Exception as e:
                log(f"[V1.4 Hybrid] Status callback error: {e}")
    
    try:
        update_status("chunker", "Parsing content into logical topics...")
        chunker_output = call_smart_chunker(
            markdown_content=markdown_content,
            subject=subject,
            tracker=tracker,
            max_retries=2
        )
        
        topics = chunker_output.get("topics", [])
        log(f"[V1.4 Hybrid] Smart Chunker produced {len(topics)} topics")
        
        update_status("director", "Content Director planning lesson structure...")
        content_output = call_content_director(
            topics=topics,
            subject=subject,
            grade=grade,
            tracker=tracker,
            max_structural_retries=2,
            max_semantic_retries=1
        )
        
        update_status("director", "Recap Director creating memory and recap scenes...")
        recap_output = call_recap_director(
            full_markdown=markdown_content,
            subject=subject,
            grade=grade,
            tracker=tracker,
            max_structural_retries=2,
            max_semantic_retries=1
        )
        
        update_status("validation", "Merging Content + Recap outputs...")
        presentation = merge_director_outputs(
            content_output=content_output,
            recap_output=recap_output,
            subject=subject,
            grade=grade
        )
        
        presentation["metadata"]["chunker_topics"] = len(chunker_output.get("topics", []))
        presentation["metadata"]["content_sections"] = len(content_output.get("sections", []))
        presentation["metadata"]["recap_sections"] = len(recap_output.get("sections", []))
        
        update_status("remotion_renderer", "Dispatching to renderers...")
        presentation = pass2_dispatch_renderers(presentation, tracker, use_remotion=use_remotion)
        
        presentation["job_id"] = job_id
        
        tracker.end_pipeline(status="completed")
        tracker.print_summary()
        
        update_status("completed", "Pipeline completed successfully!")
        return presentation, tracker
        
    except Exception as e:
        tracker.end_pipeline(status="failed", error=str(e))
        tracker.print_summary()
        update_status("failed", str(e))
        raise


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_pipeline(sys.argv[1])
    else:
        print("Usage: python llm_client_v12.py <markdown_file>")

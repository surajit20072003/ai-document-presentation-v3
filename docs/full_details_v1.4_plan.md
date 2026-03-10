# V1.4 Pipeline Architecture - Full Details Plan

**Version:** 1.4  
**Created:** 2025-12-22  
**Status:** IMPLEMENTED  
**Resolves:** ISS-080 (Director LLM Fails v1.3 Structural Validation Consistently)

---

## Executive Summary

V1.4 introduces a **Split Director Architecture** that divides the cognitive load of the Director LLM into two specialized calls:
1. **Content Director** - Handles intro/summary/content/example/quiz sections with all visual orchestration
2. **Recap Director** - Handles Memory (5 flashcards) + Recap (5 scenes with video prompts) with full markdown context

This architecture guarantees perfect output by:
- Reducing LLM cognitive load (fewer rules per call = better compliance)
- Giving Recap/Memory access to FULL source context (not chunked)
- Enabling targeted retries (retry only the failing component)
- Maintaining v1.3 schema compatibility for downstream components

---

## Problem Statement (ISS-080)

### Current v1.3 Failure Modes
| Error Type | Frequency | Root Cause |
|------------|-----------|------------|
| Missing memory/recap sections | High | LLM overwhelmed with 8+ sections |
| text_layer + visual_layer mutual exclusion | Medium | Too many display_directive rules |
| Memory not having 5 flashcards | High | LLM forgets exact count |
| Recap not having 5 scenes | High | LLM truncates or miscounts |
| Recap avatar_layer not 'hide' | Medium | Buried in prompt rules |

### Why Single Director Fails
- Prompt is ~400 lines with complex interleaved rules
- LLM must track: avatar placement, display_directives, timing, visual_content, renderer selection, AND section-specific rules
- Memory/Recap have unique requirements (exact counts, video prompts) that conflict with content patterns
- Retry prompts don't have context to fix specific missing sections

---

## V1.4 Architecture

### Pipeline Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ PASS 0: SMART CHUNKER                                                           │
│ Model: Gemini 2.5 Pro                                                           │
│ Input: Raw Markdown                                                              │
│ Output: Logical topic blocks with metadata                                       │
│                                                                                  │
│ Retries: 2 structural                                                            │
│ JSON Schema: Enforced via API response_format                                    │
│                                                                                  │
│ Output Format:                                                                   │
│ {                                                                                │
│   "source_topic": "Cell Evolution",                                             │
│   "topics": [                                                                    │
│     {                                                                            │
│       "topic_id": "t1",                                                          │
│       "title": "The Endosymbiotic Theory",                                      │
│       "concept_type": "process|definition|example|formula",                     │
│       "source_blocks": [1, 2, 3],                                               │
│       "key_terms": ["mitochondria", "chloroplasts", "prokaryotic"],             │
│       "has_formula": false,                                                      │
│       "suggested_renderer": "video|manim|remotion"                              │
│     }                                                                            │
│   ]                                                                              │
│ }                                                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ PASS 1a: CONTENT DIRECTOR                                                        │
│ Model: Gemini 2.5 Pro                                                           │
│ Input: Topic blocks from Smart Chunker                                           │
│ Output: intro + summary + content + example + quiz sections                      │
│                                                                                  │
│ Retries: 4 structural + 2 semantic                                               │
│ JSON Schema: Enforced via API response_format                                    │
│                                                                                  │
│ RESPONSIBILITIES:                                                                │
│ ✓ Avatar placement (position, size, visibility per section type)                │
│ ✓ display_directives (text_layer, visual_layer, avatar_layer per segment)       │
│ ✓ Timing/Duration per segment (duration_seconds)                                │
│ ✓ Visual Content (bullet_points, formula, labels, steps)                        │
│ ✓ Narration text + segment timing                                               │
│ ✓ Avatar gestures (gesture_only, show, hide)                                    │
│ ✓ Renderer selection (remotion/manim/video) with reasoning                      │
│ ✓ Layout zones (content_zone, avatar_zone)                                      │
│                                                                                  │
│ DOES NOT GENERATE:                                                               │
│ ✗ memory section                                                                 │
│ ✗ recap section                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ PASS 1b: RECAP DIRECTOR                                                          │
│ Model: Gemini 2.5 Pro                                                           │
│ Input: ORIGINAL MARKDOWN (full context, NOT chunked topics)                      │
│ Output: Memory section + Recap section                                           │
│                                                                                  │
│ Retries: 2 structural + 1 semantic                                               │
│ JSON Schema: Enforced via API response_format                                    │
│                                                                                  │
│ MEMORY SECTION REQUIREMENTS:                                                     │
│ ✓ section_type: "memory"                                                         │
│ ✓ renderer: "remotion"                                                           │
│ ✓ Exactly 5 flashcards (R-A-S mnemonic style)                                   │
│ ✓ Each flashcard: letter, title, description                                    │
│ ✓ full_narration explaining the mnemonic                                        │
│ ✓ avatar_layer: "show" (optional per rules)                                     │
│                                                                                  │
│ RECAP SECTION REQUIREMENTS:                                                      │
│ ✓ section_type: "recap"                                                          │
│ ✓ renderer: "video" (WAN)                                                        │
│ ✓ Exactly 5 scenes/visual_beats                                                 │
│ ✓ Total narration: 300-500 words                                                │
│ ✓ Each scene: video_prompt (300+ words, cinematic, specific)                    │
│ ✓ avatar_layer: "hide" (MANDATORY)                                              │
│ ✓ Mental Movie storytelling style with Indian context                           │
│                                                                                  │
│ VIDEO PROMPTS (NOT Infographics):                                                │
│ - Each video_prompt must be 300+ words                                           │
│ - Cinematic descriptions for WAN video generation                                │
│ - NO image_prompt or infographic_prompt fields                                   │
│ - Sound effects described in narration (WHOOSH, POP, etc.)                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ MERGE STEP (Deterministic - No LLM)                                              │
│                                                                                  │
│ Input: Content Director output + Recap Director output                           │
│ Output: Single presentation.json (v1.3 schema compliant)                         │
│                                                                                  │
│ OPERATIONS:                                                                      │
│ 1. Combine sections array: content_sections + [memory, recap]                   │
│ 2. Assign sequential section_ids (1, 2, 3, ... N)                               │
│ 3. Preserve all fields from both outputs                                        │
│ 4. Set spec_version: "v1.4"                                                      │
│ 5. Add generation metadata (timestamp, models used)                             │
│                                                                                  │
│ NO RETRIES - This is deterministic code, not LLM                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3-TIER VALIDATION (Same as v1.3)                                                 │
│                                                                                  │
│ Runs POST-MERGE on combined presentation.json                                    │
│                                                                                  │
│ Tier 1: Structural Validation                                                    │
│   - All required fields present                                                  │
│   - Section types valid                                                          │
│   - display_directives on every segment                                         │
│   - Renderer fields present for each renderer type                              │
│                                                                                  │
│ Tier 2: Semantic Validation                                                      │
│   - Mutual exclusion (text_layer + visual_layer not both 'show')               │
│   - Narration word counts (content ≥150, recap 300-500)                         │
│   - Memory has exactly 5 flashcards                                             │
│   - Recap has exactly 5 scenes                                                  │
│   - Recap avatar_layer = 'hide'                                                 │
│   - Formula mentioned → visualized                                               │
│                                                                                  │
│ Tier 3: Quality Lint (Warnings only)                                            │
│   - Vague language detection                                                     │
│   - Duration sanity checks                                                       │
│                                                                                  │
│ IF VALIDATION FAILS → HARD FAIL (no fallbacks)                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ PASS 1.5: TTS DURATION MEASUREMENT (NEW in v1.4)                                │
│                                                                                  │
│ Purpose: Replace LLM duration estimates with actual TTS audio durations         │
│                                                                                  │
│ Process:                                                                         │
│ 1. For each narration segment, call Narakeet TTS API                            │
│ 2. Inspect MP3 metadata using mutagen library (no playback needed)              │
│ 3. Update duration_seconds field with actual value                              │
│ 4. Calculate section total_duration_seconds                                      │
│                                                                                  │
│ Implementation:                                                                  │
│   audio = MP3(audio_path)                                                        │
│   duration = audio.info.length  # Microsecond-accurate                          │
│                                                                                  │
│ Fallback:                                                                        │
│ - If Narakeet fails: estimate at 130 words/minute                               │
│ - If NARAKEET_API_KEY not set: use estimates only                               │
│                                                                                  │
│ Benefits:                                                                        │
│ - Accurate timing for player synchronization                                    │
│ - No runtime surprises from duration mismatches                                 │
│ - Audio files cached for later use                                              │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ PASS 2: RENDERERS (Unchanged from v1.3)                                          │
│                                                                                  │
│ Remotion Renderer (Claude Sonnet 4):                                             │
│   - intro, summary, memory, quiz sections                                        │
│   - Generates remotion_scene_spec                                               │
│   - 1 retry on JSON parse failure                                               │
│                                                                                  │
│ Manim Renderer (Claude Sonnet 4):                                                │
│   - Math/physics equations, graphs, geometry                                    │
│   - Generates manim_scene_spec                                                  │
│   - 1 retry on failure                                                           │
│                                                                                  │
│ WAN Video Renderer (Gemini 2.5 Pro):                                             │
│   - Biology, chemistry, physical phenomena, recap                               │
│   - video_prompts already in presentation.json from Directors                   │
│   - Validates prompts are 300+ words                                            │
│   - 1 retry on validation failure                                               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Wiring Details

### Pipeline Orchestration Code Flow

```python
# core/pipeline_v14.py

def process_markdown_to_videos_v14(markdown_content, subject, grade, job_id, ...):
    """
    V1.4 Pipeline with Split Director Architecture.
    """
    tracker = AnalyticsTracker(job_id)
    
    # ═══════════════════════════════════════════════════════════════════
    # PASS 0: SMART CHUNKER
    # ═══════════════════════════════════════════════════════════════════
    update_job_status(job_id, "chunker", "Analyzing content structure...")
    
    chunker_output = call_smart_chunker(
        markdown_content=markdown_content,
        subject=subject,
        tracker=tracker,
        max_retries=2
    )
    # Output: { "source_topic": "...", "topics": [...] }
    
    # ═══════════════════════════════════════════════════════════════════
    # PASS 1a: CONTENT DIRECTOR
    # ═══════════════════════════════════════════════════════════════════
    update_job_status(job_id, "content_director", "Creating lesson structure...")
    
    content_sections = call_content_director(
        topics=chunker_output["topics"],
        subject=subject,
        grade=grade,
        tracker=tracker,
        max_structural_retries=4,
        max_semantic_retries=2
    )
    # Output: { "sections": [intro, summary, content*, example*, quiz*] }
    
    # ═══════════════════════════════════════════════════════════════════
    # PASS 1b: RECAP DIRECTOR
    # ═══════════════════════════════════════════════════════════════════
    update_job_status(job_id, "recap_director", "Creating memory aids and recap...")
    
    recap_sections = call_recap_director(
        full_markdown=markdown_content,  # FULL context, not chunked
        subject=subject,
        grade=grade,
        tracker=tracker,
        max_structural_retries=2,
        max_semantic_retries=1
    )
    # Output: { "sections": [memory, recap] }
    
    # ═══════════════════════════════════════════════════════════════════
    # MERGE STEP (Deterministic)
    # ═══════════════════════════════════════════════════════════════════
    update_job_status(job_id, "merge", "Combining lesson components...")
    
    presentation = merge_director_outputs(
        content_output=content_sections,
        recap_output=recap_sections,
        subject=subject,
        grade=grade
    )
    # Output: Complete presentation.json with sequential section_ids
    
    # ═══════════════════════════════════════════════════════════════════
    # 3-TIER VALIDATION (Same validators as v1.3)
    # ═══════════════════════════════════════════════════════════════════
    update_job_status(job_id, "validation", "Validating lesson structure...")
    
    validation_result = run_three_tier_validation(presentation)
    
    if validation_result.has_errors:
        raise ValidationError(f"Post-merge validation failed: {validation_result.errors}")
    
    # ═══════════════════════════════════════════════════════════════════
    # PASS 2: RENDERERS (Unchanged from v1.3)
    # ═══════════════════════════════════════════════════════════════════
    update_job_status(job_id, "render", "Generating visual content...")
    
    presentation = pass2_dispatch_renderers(
        presentation=presentation,
        tracker=tracker,
        use_remotion=True
    )
    
    return presentation, tracker
```

### Smart Chunker Wiring

```python
# core/smart_chunker.py

def call_smart_chunker(markdown_content, subject, tracker, max_retries=2):
    """
    PASS 0: Extract logical topics from markdown.
    Uses Gemini 2.5 Pro with JSON schema enforcement.
    """
    system_prompt = load_prompt("smart_chunker_system_v1.4")
    user_prompt = load_prompt("smart_chunker_user_v1.4").format(
        markdown_content=markdown_content,
        subject=subject
    )
    
    for attempt in range(max_retries + 1):
        try:
            # Call LLM with JSON schema
            response, usage = call_llm(
                model="google/gemini-2.5-pro",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "smart_chunker_output",
                        "schema": SMART_CHUNKER_SCHEMA
                    }
                }
            )
            
            # JSON repair before parsing
            result = repair_and_parse_json(response)
            
            # Validate output structure
            validate_chunker_output(result)
            
            tracker.log_phase("smart_chunker", usage)
            return result
            
        except (JSONParseError, ValidationError) as e:
            if attempt < max_retries:
                log(f"[Chunker] Retry {attempt + 1}/{max_retries}: {e}")
                user_prompt = get_chunker_retry_prompt(user_prompt, str(e))
            else:
                raise ChunkerError(f"Smart Chunker failed after {max_retries} retries: {e}")
```

### Content Director Wiring

```python
# core/content_director.py

def call_content_director(topics, subject, grade, tracker, max_structural_retries=4, max_semantic_retries=2):
    """
    PASS 1a: Generate intro/summary/content/example/quiz sections.
    Does NOT generate memory or recap.
    """
    system_prompt = load_prompt("content_director_system_v1.4")
    user_prompt = load_prompt("content_director_user_v1.4").format(
        topics_json=json.dumps(topics, indent=2),
        subject=subject,
        grade=grade
    )
    
    structural_attempts = 0
    semantic_attempts = 0
    
    while True:
        try:
            # Call LLM with JSON schema
            response, usage = call_llm(
                model="google/gemini-2.5-pro",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "content_director_output",
                        "schema": CONTENT_DIRECTOR_SCHEMA
                    }
                }
            )
            
            # JSON repair before parsing
            result = repair_and_parse_json(response)
            
            # Tier 1: Structural validation
            structural_errors = validate_content_structure(result)
            if structural_errors:
                structural_attempts += 1
                if structural_attempts > max_structural_retries:
                    raise StructuralValidationError(structural_errors)
                user_prompt = get_structural_retry_prompt(user_prompt, structural_errors)
                continue
            
            # Tier 2: Semantic validation
            semantic_errors = validate_content_semantics(result)
            if semantic_errors:
                semantic_attempts += 1
                if semantic_attempts > max_semantic_retries:
                    raise SemanticValidationError(semantic_errors)
                user_prompt = get_semantic_retry_prompt(user_prompt, semantic_errors)
                continue
            
            tracker.log_phase("content_director", usage)
            return result
            
        except (JSONParseError) as e:
            structural_attempts += 1
            if structural_attempts > max_structural_retries:
                raise ContentDirectorError(f"JSON parse failed: {e}")
            user_prompt = get_json_repair_prompt(user_prompt, str(e))
```

### Recap Director Wiring

```python
# core/recap_director.py

def call_recap_director(full_markdown, subject, grade, tracker, max_structural_retries=2, max_semantic_retries=1):
    """
    PASS 1b: Generate memory (5 flashcards) + recap (5 scenes with video prompts).
    Receives FULL markdown for complete context.
    """
    system_prompt = load_prompt("recap_director_system_v1.4")
    user_prompt = load_prompt("recap_director_user_v1.4").format(
        full_markdown=full_markdown,
        subject=subject,
        grade=grade
    )
    
    structural_attempts = 0
    semantic_attempts = 0
    
    while True:
        try:
            # Call LLM with JSON schema
            response, usage = call_llm(
                model="google/gemini-2.5-pro",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "recap_director_output",
                        "schema": RECAP_DIRECTOR_SCHEMA
                    }
                }
            )
            
            # JSON repair before parsing
            result = repair_and_parse_json(response)
            
            # Tier 1: Structural validation (memory + recap sections exist)
            structural_errors = validate_recap_structure(result)
            if structural_errors:
                structural_attempts += 1
                if structural_attempts > max_structural_retries:
                    raise StructuralValidationError(structural_errors)
                user_prompt = get_recap_structural_retry_prompt(user_prompt, structural_errors)
                continue
            
            # Tier 2: Semantic validation
            # - Memory has exactly 5 flashcards
            # - Recap has exactly 5 scenes
            # - Recap narration is 300-500 words
            # - Recap avatar_layer = 'hide'
            # - Video prompts are 300+ words each
            semantic_errors = validate_recap_semantics(result)
            if semantic_errors:
                semantic_attempts += 1
                if semantic_attempts > max_semantic_retries:
                    raise SemanticValidationError(semantic_errors)
                user_prompt = get_recap_semantic_retry_prompt(user_prompt, semantic_errors)
                continue
            
            tracker.log_phase("recap_director", usage)
            return result
            
        except (JSONParseError) as e:
            structural_attempts += 1
            if structural_attempts > max_structural_retries:
                raise RecapDirectorError(f"JSON parse failed: {e}")
            user_prompt = get_json_repair_prompt(user_prompt, str(e))
```

### Merge Step Wiring

```python
# core/merge_step.py

def merge_director_outputs(content_output, recap_output, subject, grade):
    """
    Deterministic merge of Content Director + Recap Director outputs.
    No LLM calls - pure Python logic.
    """
    # 1. Extract sections from both outputs
    content_sections = content_output.get("sections", [])
    recap_sections = recap_output.get("sections", [])
    
    # 2. Combine in order: content sections first, then memory, then recap
    all_sections = content_sections + recap_sections
    
    # 3. Assign sequential section_ids
    for i, section in enumerate(all_sections, start=1):
        section["section_id"] = f"section_{i}"
    
    # 4. Build final presentation.json
    presentation = {
        "spec_version": "v1.4",
        "title": content_output.get("title", f"{subject} Lesson"),
        "subject": subject,
        "grade": grade,
        "sections": all_sections,
        "metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "pipeline_version": "v1.4",
            "content_director_model": "google/gemini-2.5-pro",
            "recap_director_model": "google/gemini-2.5-pro"
        }
    }
    
    return presentation
```

### JSON Repair Utility

```python
# core/json_repair.py

def repair_and_parse_json(response: str) -> dict:
    """
    Repair common JSON issues from LLM output.
    Applied BEFORE passing to next pipeline step.
    """
    response = response.strip()
    
    # 1. Strip markdown code fences
    if '```json' in response:
        start = response.find('```json') + 7
        end = response.rfind('```')
        if end > start:
            response = response[start:end].strip()
    elif '```' in response:
        start = response.find('```') + 3
        end = response.rfind('```')
        if end > start:
            response = response[start:end].strip()
    
    # 2. Try direct parse first
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # 3. Extract JSON object/array
    json_str = response
    if '{' in response:
        json_str = response[response.find('{'):response.rfind('}')+1]
    elif '[' in response:
        json_str = response[response.find('['):response.rfind(']')+1]
    
    # 4. Remove trailing commas
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*\]', ']', json_str)
    
    # 5. Close unclosed braces/brackets
    open_braces = json_str.count('{') - json_str.count('}')
    open_brackets = json_str.count('[') - json_str.count(']')
    
    if open_braces > 0 or open_brackets > 0:
        # Close open strings first
        if json_str.count('"') % 2 == 1:
            json_str += '"'
        
        # Remove incomplete trailing entries
        json_str = re.sub(r',\s*\{[^}]*$', '', json_str)
        json_str = re.sub(r',\s*\[[^\]]*$', '', json_str)
        
        # Close remaining open brackets
        json_str += ']' * max(0, open_brackets) + '}' * max(0, open_braces)
        
        log(f"[JSON Repair] Auto-closed {open_braces} braces, {open_brackets} brackets")
    
    return json.loads(json_str)
```

---

## Retry Strategy

### Full Retry Matrix

| Component | Structural Retries | Semantic Retries | Total Max | Retry Prompt |
|-----------|-------------------|------------------|-----------|--------------|
| Smart Chunker | 2 | 0 | 2 | JSON structure repair |
| Content Director | 4 | 2 | 6 | Structure-repair with specific errors |
| Recap Director | 2 | 1 | 3 | Memory/Recap specific repair |
| Remotion Renderer | 1 | 0 | 1 | JSON parse repair |
| Manim Renderer | 1 | 0 | 1 | Scene spec repair |
| WAN Renderer | 1 | 0 | 1 | Prompt length/quality repair |

### Retry Flow Diagram

```
Smart Chunker (max 2 retries)
    ├─ Success → Continue to Content Director
    └─ Fail after 2 retries → HARD FAIL

Content Director (max 4 structural + 2 semantic)
    ├─ JSON Parse Error → Structural retry with repair prompt
    ├─ Structural Validation Error → Structural retry with specific errors
    ├─ Structural Pass → Run Semantic Validation
    │   ├─ Semantic Pass → Continue to Recap Director
    │   └─ Semantic Fail → Semantic retry (max 2)
    │       └─ Fail after 2 semantic retries → HARD FAIL
    └─ Fail after 4 structural retries → HARD FAIL

Recap Director (max 2 structural + 1 semantic)
    ├─ JSON Parse Error → Structural retry with repair prompt
    ├─ Structural Validation Error → Structural retry
    ├─ Structural Pass → Run Semantic Validation
    │   ├─ Semantic Pass → Continue to Merge
    │   └─ Semantic Fail → Semantic retry (max 1)
    │       └─ Fail after 1 semantic retry → HARD FAIL
    └─ Fail after 2 structural retries → HARD FAIL

Merge Step (deterministic, no retry)
    └─ Always succeeds if inputs are valid

3-Tier Validation (post-merge)
    ├─ Pass → Continue to Renderers
    └─ Fail → HARD FAIL (no fallbacks)

Renderers (1 retry each)
    ├─ Remotion: 1 retry on JSON parse error
    ├─ Manim: 1 retry on scene spec error
    └─ WAN: 1 retry on prompt validation error
```

---

## JSON Handling Strategy

### 1. API-Level Enforcement (Structured Output)

Every LLM call enforces JSON schema via API:

```python
# For Gemini models
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "smart_chunker_output",
        "schema": {
            "type": "object",
            "properties": {
                "source_topic": {"type": "string"},
                "topics": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Topic"}
                }
            },
            "required": ["source_topic", "topics"]
        }
    }
}

# For Claude models  
response_format = {"type": "json_object"}
```

### 2. JSON Repair (Post-Response, Pre-Validation)

After each LLM response, apply repair BEFORE using output:

```
LLM Response → JSON Repair → Schema Validation → Next Step
                   │
                   ├─ Strip markdown fences (```json ... ```)
                   ├─ Remove trailing commas (, } → })
                   ├─ Close unclosed strings
                   ├─ Close unclosed braces/brackets
                   └─ Remove incomplete trailing entries
```

### 3. Per-Step Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ LLM Call with JSON Schema                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Raw Response                                                     │
│ (may have markdown fences, trailing commas, truncation)         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ JSON Repair (repair_and_parse_json)                              │
│ - Strip fences                                                   │
│ - Fix commas                                                     │
│ - Close brackets                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Parsed JSON Object                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Structural Validation                                            │
│ - Required fields present?                                       │
│ - Correct types?                                                 │
│ - Valid section types?                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          │                                       │
          ▼ (Pass)                                ▼ (Fail)
┌─────────────────────┐               ┌─────────────────────┐
│ Semantic Validation │               │ Retry with specific │
│ (content rules)     │               │ error message       │
└─────────────────────┘               └─────────────────────┘
          │
          ▼ (Pass)
┌─────────────────────────────────────────────────────────────────┐
│ Valid Output → Next Pipeline Step                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## What We ARE Incorporating from V3 Pipeline

| Component | V3 Source | V1.4 Usage |
|-----------|-----------|------------|
| Smart Chunker Concept | `chunker_smart.txt` prompt | Topic-aware extraction with block IDs, concept types, key terms, suggested renderers |
| JSON Repair Logic | `parse_llm_json()` function | Handle truncated/malformed LLM responses before passing to next step |
| Separate LLM Calls | Stage 2 + Stage 4 pattern | Split Content Director + Recap Director for reduced cognitive load |
| Recap Storyboard Structure | `recap_storyboard.txt` prompt | 5 scenes with segment_text, concept_title, duration |

## What We Are NOT Incorporating from V3 Pipeline

| Component | V3 Has | V1.4 Decision | Reason |
|-----------|--------|---------------|--------|
| Infographic Generation | `image_prompt` field in storyboard | ❌ NOT USED | We use WAN video renderer for recap, not static images |
| Stage 5 Image Gen | `VisualEngine.generate_scene_images()` | ❌ NOT USED | Recap uses video (WAN), not PNG images |
| Edge TTS | `generate_audio_for_slide()` | ❌ NOT USED | We keep Narakeet TTS (Indian male voice "ravi") |
| HTML Templates | `slide_v3_*.html` | ❌ NOT USED | We keep our Player + Remotion/Manim/WAN renderers |
| Slides-based Output | `slides[]` array | ❌ NOT USED | We keep sections-based v1.3 schema |

---

## Downstream Impact Analysis

### Components That DO NOT Change

| Component | Impact | Reason |
|-----------|--------|--------|
| **Remotion Renderer** | ✅ No change | Receives same section format from presentation.json |
| **Manim Renderer** | ✅ No change | Receives same section format from presentation.json |
| **WAN Video Renderer** | ✅ No change | Receives same video_prompts format |
| **Player (player.js)** | ✅ No change | Reads same presentation.json schema |
| **TTS (Narakeet)** | ✅ No change | Receives same narration format |
| **3-Tier Validators** | ✅ Reused | Run post-merge with same validation logic |
| **Hard Fail Validator** | ✅ Reused | Same hard fail conditions |
| **Traceability** | ✅ Enhanced | Add per-Director phase logging |
| **Analytics** | ✅ Enhanced | Track per-Director costs separately |

### Schema Compatibility

**presentation.json output remains v1.3 schema compliant:**

```json
{
  "spec_version": "v1.4",  // Backwards compatible with v1.3
  "title": "...",
  "subject": "Biology",
  "grade": "Grade 10",
  "sections": [
    {
      "section_id": "section_1",
      "section_type": "intro",
      "renderer": "remotion",
      "renderer_reasoning": "...",
      "layout": {...},
      "narration": {
        "full_text": "...",
        "segments": [
          {
            "segment_id": "s1",
            "text": "...",
            "duration_seconds": 5,
            "display_directives": {
              "text_layer": "show",
              "visual_layer": "hide",
              "avatar_layer": "show"
            },
            "visual_content": {...}
          }
        ]
      }
    },
    // ... more sections
    {
      "section_id": "section_8",
      "section_type": "memory",
      "renderer": "remotion",
      "visual_content": {
        "flashcards": [/* exactly 5 */]
      }
    },
    {
      "section_id": "section_9",
      "section_type": "recap",
      "renderer": "video",
      "video_prompts": [/* exactly 5 with 300+ words each */]
    }
  ]
}
```

---

## LLM Responsibility Matrix

### Content Director Responsibilities

| Responsibility | Details | Validation |
|----------------|---------|------------|
| **Sections Generated** | intro, summary, content, example, quiz | Structural check |
| **Avatar Placement** | position (left/right/center), size (30-60%), visibility | Per section type rules |
| **display_directives** | text_layer, visual_layer, avatar_layer per segment | Mutual exclusion check |
| **Timing** | duration_seconds per segment and section | Duration sanity check |
| **Visual Content** | bullet_points, formula, labels, steps, diagrams | Required for text_layer=show |
| **Narration** | Full text per segment, pedagogically structured | Word count ≥150 for content |
| **Gestures** | Avatar gestures per segment (show, hide, gesture_only) | Valid gesture values |
| **Renderer Selection** | remotion/manim/video with reasoning | Subject-appropriate check |
| **Layout** | content_zone, avatar_zone dimensions | Valid zone values |

### Recap Director Responsibilities

| Responsibility | Details | Validation |
|----------------|---------|------------|
| **Sections Generated** | memory, recap | Must have exactly 2 sections |
| **Memory Flashcards** | Exactly 5, R-A-S mnemonic style | Count = 5 |
| **Recap Scenes** | Exactly 5, with video_prompts | Count = 5 |
| **Recap Narration** | 300-500 words total, Mental Movie style | Word count check |
| **Avatar (Memory)** | Optional, can be show/hide | Valid value |
| **Avatar (Recap)** | MUST be 'hide' | Hard check |
| **Renderer (Memory)** | Must be 'remotion' | Exact match |
| **Renderer (Recap)** | Must be 'video' (WAN) | Exact match |
| **Video Prompts** | Cinematic, specific, 300+ words each | Word count per prompt |

---

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `core/smart_chunker.py` | Smart Chunker LLM client with topic extraction |
| `core/content_director.py` | Content Director LLM client (intro/summary/content/example/quiz) |
| `core/recap_director.py` | Recap Director LLM client (memory + recap with video prompts) |
| `core/merge_step.py` | Deterministic merge of Content + Recap outputs |
| `core/json_repair.py` | Shared JSON repair utility |
| `core/prompts/smart_chunker_system_v1.4.txt` | Smart Chunker system prompt |
| `core/prompts/smart_chunker_user_v1.4.txt` | Smart Chunker user prompt |
| `core/prompts/content_director_system_v1.4.txt` | Content Director system prompt |
| `core/prompts/content_director_user_v1.4.txt` | Content Director user prompt |
| `core/prompts/recap_director_system_v1.4.txt` | Recap Director system prompt |
| `core/prompts/recap_director_user_v1.4.txt` | Recap Director user prompt |
| `schemas/smart_chunker_output.schema.json` | JSON Schema for Smart Chunker |
| `schemas/content_director_output.schema.json` | JSON Schema for Content Director |
| `schemas/recap_director_output.schema.json` | JSON Schema for Recap Director |

### Modified Files

| File | Changes |
|------|---------|
| `core/pipeline_v12.py` | Add `process_markdown_to_videos_v14()` function with new orchestration |
| `core/llm_client_v12.py` | Add structured output support, import new director modules |
| `core/analytics.py` | Track per-Director phase costs (smart_chunker, content_director, recap_director) |
| `core/traceability.py` | Log per-Director decisions and outputs |
| `api/app.py` | Route to v1.4 pipeline (add pipeline_version parameter) |
| `replit.md` | Update architecture documentation to v1.4 |
| `issues.json` | Mark ISS-080 as resolved with v1.4 solution |

### Backup Files (Before Modification)

| Current File | Backup Location |
|--------------|-----------------|
| `core/prompts/director_system_v1.3.txt` | `core/prompts/v1.3_backup/` |
| `core/prompts/director_user_v1.3.txt` | `core/prompts/v1.3_backup/` |
| `core/prompts/chunker_system_v1.3.txt` | `core/prompts/v1.3_backup/` |
| `core/prompts/chunker_user_v1.3.txt` | `core/prompts/v1.3_backup/` |
| `docs/llm_output_requirements_v1.3.json` | Keep as-is (reference for v1.3 compatibility) |

---

## Benefits vs Risks

### Benefits

| Benefit | Impact |
|---------|--------|
| **Reduced cognitive load** | Fewer rules per LLM call = better compliance |
| **Better Recap/Memory quality** | Full markdown context, specialized prompt |
| **Modular retries** | Retry only failing component, not entire pipeline |
| **Easier debugging** | Isolated failures, clear responsibility per Director |
| **Higher success rate** | Targeted prompts for specific section types |
| **Guaranteed structure** | JSON schema enforcement at API level |
| **Faster iteration** | Can update Content or Recap prompts independently |

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| **2x LLM calls = higher latency/cost** | Track costs per phase, optimize prompts for efficiency |
| **Section ID conflicts** | Merge step assigns sequential IDs deterministically |
| **Duration budget misalignment** | Merge step can reconcile total timing if needed |
| **Divergence between Directors** | Shared subject/grade context, post-merge validation catches issues |
| **Complexity increase** | Clear module separation, comprehensive logging |

---

## Test Plan

### Unit Tests
1. Smart Chunker with Biology content → valid topic blocks
2. Content Director with topic blocks → valid sections (no memory/recap)
3. Recap Director with full markdown → valid memory + recap
4. Merge Step with both outputs → valid presentation.json
5. 3-Tier Validation passes on merged output
6. JSON Repair handles truncated/malformed responses

### Integration Tests
1. Full pipeline: Biology content → presentation.json → renderers → videos
2. Full pipeline: Physics content (with formulas) → manim sections work correctly
3. Full pipeline: Multi-subject content → all section types generated correctly

### Regression Tests
1. Existing v1.3 content still works (v1.3 fallback path if needed)
2. Player renders v1.4 output correctly (spec_version check)
3. All renderers produce valid output from v1.4 presentation.json

---

## Implementation Task List

| # | Task | Status |
|---|------|--------|
| 0 | Create docs/full_details_v1.4_plan.md | ⏳ In Progress |
| 1 | Create Smart Chunker (Gemini 2.5 Pro) with JSON schema + 2 retries | ⬜ Pending |
| 2 | Create Content Director (Gemini 2.5 Pro) with JSON schema for intro/summary/content/example/quiz | ⬜ Pending |
| 3 | Content Director retry logic: 4 structural + 2 semantic retries | ⬜ Pending |
| 4 | Create Recap Director (Gemini 2.5 Pro) with JSON schema for memory + recap | ⬜ Pending |
| 5 | Recap Director retry logic: 2 structural + 1 semantic retries | ⬜ Pending |
| 6 | Implement JSON Repair utility | ⬜ Pending |
| 7 | Build deterministic Merge step | ⬜ Pending |
| 8 | Update pipeline orchestration (Pass0 → Pass1a → Pass1b → Merge → Validate → Render) | ⬜ Pending |
| 9 | Ensure 3-tier validators run post-merge | ⬜ Pending |
| 10 | Test with Biology content to validate perfect output | ⬜ Pending |

---

## Approval Checklist

Please confirm the following before implementation begins:

- [ ] V1.4 Split Director architecture approved
- [ ] Recap uses VIDEO prompts (not infographics) confirmed
- [ ] Downstream components remain unchanged confirmed
- [ ] Retry strategy per component approved
- [ ] JSON schema enforcement at API level approved
- [ ] File creation/modification plan approved

---

**Document Status:** PENDING USER APPROVAL

Once approved, implementation will begin with Task 1 (Smart Chunker).

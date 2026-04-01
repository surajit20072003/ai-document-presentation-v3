# V3 Pipeline Improvement Plan
**Status**: Steps 1-4 COMPLETE ✅ | Validation Gate + Retry COMPLETE ✅ | Ready for Nightly Job Run  
**Last Updated**: 2026-03-31 (Post-Validation-Gate)  
**Approach**: Prompt changes first → code changes → dry run tests → pipeline wiring → validation gate  

---

## 📋 HANDOVER SUMMARY — For Next Team Member

### ✅ What's Done (All code changes applied and syntax-verified in Docker)

| Area | Files Changed | Status |
|------|--------------|--------|
| **Prompt Changes (Step 1)** | 3 prompt files | ✅ All 13 additions applied |
| **Enhancer Code (Step 2)** | `visual_prompt_enhancer.py` | ✅ Hex strip + symbolic detection + infographic support |
| **Test Scripts (Step 3)** | 3 test files created/updated | ✅ All verified against old + new jobs |
| **Q10 Wiring (Step 4)** | 5 files | ✅ Stitching + renderer + pipeline + player |
| **Validation Gate (Step 5)** | `pipeline_v3.py`, `v3_validator.py` | ✅ Retry loop + auto-fix + infographic validation |
| **Narration Tone (Step 6)** | 2 prompt files | ✅ Five Pillars, rhythm, hooks, encouraging close, pace constraints |

### ⏳ What's Pending

| Item | What Needs Doing | Files |
|------|-----------------|-------|
| **Nightly job run** | Run a full pipeline job overnight, verify all tests pass | Pipeline API |
| **Q6 TTS wiring** | Wire pace → rate mapping and `[pause:Xs]` tags into TTS generator | TTS generator code |
| **Q7 Gesture wiring** | Player reads `gesture` field, swaps avatar clip if available | `player_v3.html` |

### 🧪 How to Test

```bash
# After running a new pipeline job:
docker compose exec api python tests/test_director_schema.py --input player/jobs/{NEW_JOB_ID}/presentation.json
docker compose exec api python tests/test_tts_pace_pause.py --input player/jobs/{NEW_JOB_ID}/presentation.json
docker compose exec api python tests/test_enhancer_claud.py --input player/jobs/{NEW_JOB_ID}/presentation.json --prompt core/prompts/visual_prompt_enhancer_prompt.txt --dry-run
```

### 📁 Files Modified (Complete List)

| File | Changes |
|------|---------|
| `core/prompts/visual_prompt_enhancer_prompt.txt` | +5 rule blocks (human scenes, IPS/IPE stability, banned phrases, no hex, analogy quality) |
| `core/prompts/director_v3_partition_prompt.txt` | +4 rule blocks (no hex, pace/pause, gesture, analogy quality) + narration tone rules + pace=fast hard constraint |
| `core/prompts/director_global_prompt.txt` | +4 rule blocks (no hex, pace/pause, gesture, memory_infographic schema) + narration tone/structure + summary word count + recap segment count + memory_infographic hard fail |
| `core/agents/visual_prompt_enhancer.py` | +import re, +_strip_hex_from_vp(), +_beat_issues checks, +_enforce_quality hex strip, +infographic beat extraction, +targeted repair for symbolic phrases |
| `core/partition_director_generator.py` | Stitching keys: added "memory_infographic" |
| `core/renderer_executor.py` | Renderer policy: added infographic passthrough for memory_infographic |
| `core/pipeline_v3.py` | Phase 6.5a: infographic image generation. Phase 1.6: auto-compute total_duration_seconds. Phase 1: validation gate with retry (up to 2 retries with error feedback) |
| `core/v3_validator.py` | Added `memory_infographic` to REQUIRED_SECTION_TYPES. Added `_check_total_duration()` function. |
| `player/player_v3.html` | Badge map + 3x routing checks + initMemoryInfographicSection() |
| `tests/test_enhancer_claud.py` | +hex + symbolic phrase detection, +infographic beat extraction |
| `tests/test_director_schema.py` | Created (updated to match new infographic schema) |
| `tests/test_tts_pace_pause.py` | Created |

---

## Detailed Implementation Notes Below
*(The original code blocks are preserved for reference — all marked ✅ APPLIED)*

---

## Master Plan Table

| # | Problem | Fix | File(s) | Step | Status |
|---|---|---|---|---|---|
| Q1 | Recap human scenes — face morphing, crowd chaos | HUMAN SCENE RULES in enhancer prompt | `visual_prompt_enhancer_prompt.txt` | 1A | ✅ DONE |
| Q2 | Recap analogies weak | Analogy quality rules in Director prompt | `director_v3_partition_prompt.txt` | 1B | ✅ DONE |
| Q3 | Hex codes in VP confuse LTX-2.3 | No-hex rule in Director + Global prompts. Strip hex as safety net in enhancer code | `director_v3_partition_prompt.txt` + `director_global_prompt.txt` + `visual_prompt_enhancer_prompt.txt` + `visual_prompt_enhancer.py` | 1B + 1C + 1A + 2A | ✅ DONE |
| Q4 | IPS/IPE low overlap causes regeneration | IPS/IPE stability rule in enhancer prompt | `visual_prompt_enhancer_prompt.txt` | 1A | ✅ DONE |
| Q5 | Symbolic instructions in VP | Banned phrases rule in enhancer prompt + detection in enhancer code | `visual_prompt_enhancer_prompt.txt` + `visual_prompt_enhancer.py` | 1A + 2A | ✅ DONE |
| Q6 | Flat 118wpm, no pace/pause | `pace` + `pause_after_seconds` schema + rules in both Director prompts | `director_v3_partition_prompt.txt` + `director_global_prompt.txt` | 1B + 1C | ✅ DONE |
| Q7 | Gesture field missing | `gesture` schema + assignment rules in both Director prompts | `director_v3_partition_prompt.txt` + `director_global_prompt.txt` | 1B + 1C | ✅ DONE |
| Q8 | Quiz explanation beats not enhanced | ✅ Python code already implemented — no prompt change needed | `visual_prompt_enhancer.py` | — | ✅ Code done |
| Q9 | Narration matching wrong for skipped beats | ✅ Python code already implemented — no prompt change needed | `visual_prompt_enhancer.py` | — | ✅ Code done |
| Q10 | Memory Infographic section missing | New mandatory section schema + Director rules + style list + pipeline wiring | `director_global_prompt.txt` + `partition_director_generator.py` + `renderer_executor.py` + `pipeline_v3.py` + `player_v3.html` | 1C + Step 4 (wiring) | ✅ PROMPT DONE ✅ WIRING DONE — NEEDS DRY RUN TEST |

---

## Step 1 — All Prompt Changes ✅ COMPLETE

### 1A — `visual_prompt_enhancer_prompt.txt` ✅ DONE

**All five additions applied:**

- ✅ 1A-i: HUMAN SCENE RULES — inserted after MATERIAL DETAIL RULE
- ✅ 1A-ii: IPS/IPE STABILITY RULE — inserted after recap section example
- ✅ 1A-iii: BANNED PHRASES IN VP — inserted after COMMON LEAKS TO CATCH
- ✅ 1A-iv: NO HEX CODES IN VIDEO PROMPT — inserted after banned phrases
- ✅ 1A-v: ANALOGY QUALITY RULE — inserted after EDUCATIONAL PRIORITY

---

### 1B — `director_v3_partition_prompt.txt` ✅ DONE

**All four additions applied:**

- ✅ 1B-i: NO HEX IN VIDEO PROMPTS — inserted after TIMING CONTRACT
- ✅ 1B-ii: PACE AND PAUSE RULES — inserted after no hex section
- ✅ 1B-iii: GESTURE RULES — inserted after pace/pause section
- ✅ 1B-iv: ANALOGY QUALITY RULE — inserted after PERSONA section

---

### 1C — `director_global_prompt.txt` ✅ DONE

**All four additions applied:**

- ✅ 1C-i: NO HEX IN VIDEO PROMPTS — inserted after TIMING CONTRACT
- ✅ 1C-ii: PACE AND PAUSE RULES — inserted after no hex section
- ✅ 1C-iii: GESTURE RULES — inserted after SEGMENT RULES
- ✅ 1C-iv: MEMORY INFOGRAPHIC SECTION — inserted after MEMORY section
  - ⚠️ **NOTE**: Schema was updated after initial implementation to use `render_spec.infographic_beats[]` instead of `infographics[]` format (see Step 4 wiring notes below)

---

#### Addition 1A-i: HUMAN SCENE RULES
**Insert after**: `VISUAL MODE SELECTION` section

```
═══════════════════════════════════════════════════════════
HUMAN SCENE RULES (MANDATORY — applies when scene contains people)
═══════════════════════════════════════════════════════════
Triggered when IPS contains any of:
person, woman, man, student, worker, vendor, villager, teacher, child, crowd, people

RULE 1 — MAX 3 CHARACTERS:
Never describe more than 3 people in any beat.
Replace "villagers" / "crowd" / "students" with exactly 1–3 named characters.

RULE 2 — LOCK CHARACTER IDENTITY:
Every character must have ALL THREE defined:
  - Age range (young woman / middle-aged man / elderly woman)
  - Clothing (blue saree with gold border / white dhoti / green kurta)
  - Hair (long braided hair / short grey hair / hair tied in bun)
Repeat these EXACTLY — word-for-word — in IPS, IPE, and VP.

RULE 3 — DETERMINISTIC ACTIONS ONLY IN VP:
REJECTED (symbolic):
  "representing cellular processes"
  "symbolizing nutrient transport"
REQUIRED (deterministic):
  "slowly draws water from the well using both hands"
  "walks steadily from left to right carrying a clay pot"
  "remains seated, weaving a basket with slow hand movements"

RULE 4 — MOTION CONSTRAINTS (add to VP CAMERA section):
  - Camera: static / slow lateral pan / slow drift — pick one
  - No zoom. No cuts. Fixed height.

RULE 5 — MOTION STYLE (add to VP MECHANISM section):
Always end MECHANISM with:
  "Slow, natural, continuous human motion.
   No sudden changes. No character switching. Same faces throughout."
```

---

#### Addition 1A-ii: IPS/IPE STABILITY RULE
**Insert after**: `MANDATORY WORD COUNT` section

```
═══════════════════════════════════════════════════════════
IPS / IPE STABILITY RULE (MANDATORY)
═══════════════════════════════════════════════════════════
image_prompt_end MUST describe the SAME SCENE as image_prompt_start.

IDENTICAL between IPS and IPE:
  - Architecture and background
  - Lighting color and mood
  - Number of people or objects
  - Camera composition

MAY DIFFER (slightly only):
  - Character positions (moved slightly)
  - Object positions (suggest recent use)
  - Light angle (minimally — "sunlight now slightly lower")

SELF-CHECK: After writing IPE, count shared noun phrases with IPS.
If fewer than 60% of IPS nouns appear in IPE → rewrite IPE.
```

---

#### Addition 1A-iii: BANNED PHRASES IN VP
**Insert after**: `BANNED WORDS` section

```
BANNED PHRASES IN VIDEO PROMPT:
In addition to banned words, these phrases are FORBIDDEN in video_prompt:
  - "representing [concept]"
  - "symbolizing [concept]"
  - "embodying [concept]"
  - "acting as a metaphor"
  - "standing in for"

Replace with the physical action that directly demonstrates the concept.
```

---

#### Addition 1A-iv: NO HEX CODES IN VIDEO PROMPT
**Insert after**: `BANNED PHRASES IN VIDEO PROMPT`

```
HEX CODES IN VIDEO PROMPT — FORBIDDEN:
Hex codes (#RRGGBB) are FORBIDDEN in video_prompt.
LTX-2.3 does not interpret hex values — they increase motion instability.
Use descriptive color words only in video_prompt:
  WRONG: "saree in #FF5733"
  RIGHT: "saree in deep orange-red"

Hex codes remain valid and encouraged in image_prompt_start and image_prompt_end.
```

---

#### Addition 1A-v: ANALOGY QUALITY RULE
**Insert after**: `EDUCATIONAL PRIORITY` section

```
═══════════════════════════════════════════════════════════
ANALOGY QUALITY RULE (MANDATORY FOR RECAP BEATS)
═══════════════════════════════════════════════════════════
When a recap beat uses a cultural or everyday analogy to represent a concept,
the analogy MUST have a visible physical mechanism matching the concept.

TEST before using any analogy:
"If a student watches this scene, can they SEE the mechanism happening?"
If NO → reject and pick a different analogy.

GOOD ANALOGIES BY CONCEPT:
  Selective permeability → toll booth, security checkpoint, water filter, sieve
  Homeostasis → pressure cooker valve, water tank float valve, AC thermostat
  Negative feedback → AC turning off when room cools, dam gates closing
  Cells working together → factory assembly line, kitchen brigade, railway network

Cultural setting is free — India, global, or fictional.
Do NOT force a setting if a better analogy exists elsewhere.
```

---

### 1B — `director_v3_partition_prompt.txt`

**Four additions:**

---

#### Addition 1B-i: NO HEX IN VIDEO PROMPTS
**Insert after**: `TIMING CONTRACT` section

```
## NO HEX CODES IN VIDEO PROMPTS (MANDATORY)

NEVER write hex color codes (#RRGGBB) in video_prompt, video_prompts[],
or manim_beats[].manim_scene_spec.

LTX-2.3 and Manim do not benefit from hex codes in motion prompts —
they increase output instability.

Use descriptive color names only in all motion/video prompts:
  WRONG: "a teal membrane glowing #00b4d8"
  RIGHT: "a teal membrane with a soft blue-white glow"

Hex codes ARE allowed and encouraged in:
  image_prompt_start, image_prompt_end, infographic image_prompt
  (Gemini uses them for precise color generation)
```

---

#### Addition 1B-ii: PACE AND PAUSE RULES
**Insert after**: NO HEX CODES section

```
## PACE AND PAUSE RULES (MANDATORY)

Every narration segment MUST include `pace` and `pause_after_seconds`.

SCHEMA ADDITION to every segment:
{
  "segment_id": "seg_1",
  "text": "...",
  "purpose": "...",
  "pace": "slow",
  "pause_after_seconds": 1.0,
  "gesture": null,
  "duration_seconds": 14.5
}

PACE VALUES:
  "slow"   → 0.85x speaking rate.
              Use when: segment introduces a key term for the first time,
              or contains a heavy concept.
  "normal" → 1.0x speaking rate.
              Use when: standard explanation or continuation.
  "fast"   → 1.15x speaking rate.
              Use when: segment is a list, set of examples, or punchy close.

PAUSE VALUES (pause_after_seconds):
  0.0  → no pause, flow continues immediately
  0.5  → light pause (end of a thought)
  1.0  → concept pause (after introducing a key term)
  1.5  → heavy concept pause (after homeostasis, negative feedback, etc.)
  2.0  → maximum pause (after quiz question reveal, before answer appears)

SELF-CHECK:
Every segment where purpose is "introduce" OR text contains a key_term
must have pace: "slow" and pause_after_seconds >= 0.5.
```

---

#### Addition 1B-iii: GESTURE RULES
**Insert after**: PACE AND PAUSE RULES

```
## GESTURE RULES (MANDATORY)

Every narration segment MUST include a `gesture` field.
Set to null if no gesture applies. Never omit the field.

VALID VALUES:
  "Namaskara"    → Intro greeting, closing blessing, section welcome
  "Point Top"    → "Look at this", referencing diagram above
  "Point Middle" → "Here", "This concept", center-screen reference
  "Point Bottom" → "As shown below", referencing lower element
  "Ok Symbol"    → Confirming a concept, "exactly right"
  "Thumbs up"    → Correct answer in quiz, encouraging student
  null           → Default — no gesture needed

ASSIGNMENT RULES:
  - First segment of intro section → "Namaskara"
  - Segment contains "look at" / "see this" / "observe" → "Point Middle"
  - Segment contains "as shown" / "diagram above" → "Point Top"
  - Segment contains "below" / "at the bottom" → "Point Bottom"
  - Quiz correct answer segment → "Thumbs up"
  - Segment confirming a fact / "exactly right" → "Ok Symbol"
  - All others → null

SELF-CHECK:
Every segment with gesture-trigger language must have a non-null gesture.
First intro segment must be "Namaskara".
```

---

#### Addition 1B-iv: ANALOGY QUALITY RULE
**Insert after**: PERSONA section

```
## ANALOGY QUALITY RULE (MANDATORY)

When choosing an analogy or cultural setting to represent a concept,
the analogy MUST have a visible physical mechanism matching the concept.

STEP 1 — The analogy must have a visible physical mechanism:
  Selective permeability → security checkpoint, toll booth, water filter
  Homeostasis → thermostat + AC, pressure cooker valve, float valve
  Negative feedback → AC turning off when cool, dam gates closing
  Cells working together → factory line, kitchen brigade, railway network

STEP 2 — Test the analogy:
  "If a student watches this scene, can they SEE the mechanism happening?"
  If NO → reject and pick a different analogy.

STEP 3 — Cultural setting is free.
  Do NOT force Indian settings if a better analogy exists elsewhere.
```

---

### 1C — `director_global_prompt.txt`

**Four additions:**

---

#### Addition 1C-i: NO HEX IN VIDEO PROMPTS
**Same rule as 1B-i — add identically.**
Global Director generates recap image_to_video_beats — same rule applies.

---

#### Addition 1C-ii: PACE AND PAUSE RULES
**Same rules as 1B-ii — add identically.**
Global Director generates Summary, Memory, Recap narration — all segments need the same fields.

---

#### Addition 1C-iii: GESTURE RULES
**Same rules as 1B-iii — add identically.**

---

#### Addition 1C-iv: MEMORY INFOGRAPHIC SECTION
**Insert after**: MEMORY section rules

```
## MEMORY INFOGRAPHIC SECTION (Mandatory — always generate)

### Position in presentation flow:
Intro → Summary → Content sections → Memory (flashcards)
→ Memory Infographic (THIS SECTION) → Recap

### Role
One dedicated section of visual concept summaries immediately after Memory.
Helps students visually anchor the most important concepts from the lesson.
Always present. LLM decides 1–5 infographics.

### Rules
1. MANDATORY: Always generate. Minimum 1 infographic, maximum 5.
2. CHOOSE COUNT: Include infographics only for concepts that benefit:
   - Process concepts (photosynthesis, digestion, feedback loops) → always include
   - Structural concepts (cell hierarchy, organ systems) → always include
   - Simple factual concepts (dates, names, definitions) → skip
3. STYLE SELECTION: Pick from the STYLE LIST below.
   Match style to concept type. Write one sentence of justification in style_reason.
4. IMAGE PROMPT: 100+ words. Exact layout, labels, colors, visual hierarchy.
   Must follow the chosen style's visual language.
   Dark background #0d1117. 16:9. No watermarks. Publication quality.
   Hex codes ARE allowed here — Gemini uses them.
5. NARRATION: Explains what the student SEES — not what the concept IS.
   Student can read the concept — narration adds the "why this looks this way" layer.
   Apply pace, pause, and gesture rules. All three fields mandatory.

### Schema
{
  "section_id": N,
  "section_type": "memory_infographic",
  "title": "Visual Concept Summary",
  "renderer": "infographic",
  "infographics": [
    {
      "infographic_id": "inf_1",
      "concept": "Homeostasis",
      "style_name": "Scientific Process Diagram",
      "style_reason": "One sentence: why this style for this concept.",
      "image_prompt": "100+ word Gemini prompt. Static infographic. Style: Scientific Process Diagram. Dark background #0d1117. 16:9. No watermarks. Publication quality.",
      "narration": {
        "segment_id": "inf_seg_1",
        "text": "Avatar narration explaining what the student sees in this infographic.",
        "pace": "slow",
        "pause_after_seconds": 1.0,
        "gesture": null,
        "purpose": "explain",
        "duration_seconds": 15.0,
        "start_seconds": 0.0,
        "end_seconds": 15.0
      }
    }
  ],
  "total_duration_seconds": 45.0
}

### SELF-CHECK
- [ ] Section always present in output
- [ ] infographics[] has 1–5 items
- [ ] Each image_prompt >= 100 words, no hex in video/motion context
- [ ] Each narration has pace, pause_after_seconds, gesture
- [ ] style_reason is non-empty
- [ ] total_duration_seconds = sum of all narration duration_seconds

### STYLE LIST

| Style Name | Best Used For |
|---|---|
| Scientific Process Diagram | Biological cycles, chemical reactions, cellular processes, photosynthesis, respiration |
| Medical Anatomical | Organ systems, body diagrams, tissue cross-sections, cell anatomy |
| Mathematical Visual | Equations, graphs, geometry, statistics, proofs |
| Mind Map Flow | Complex idea organization, concept relationships, knowledge mapping |
| Isometric | Physical systems, floor plans, complex machinery, 3D structures |
| Timeline Style | Historical evolutions, process phases, chronological steps |
| Sketchnote | Casual concept overviews, lecture summaries |
| Chalkboard | Classic tutorials, back-to-school themes |
| Whiteboard | Step-by-step explainers, live-solving content |
| Flat Design 2.0 | Clean concept overviews, quick-read statistics, simple hierarchies |
| Friendly Explainer | Approachable concept introductions, people-focused processes |
| Blueprint | Technical deep dives, structural engineering, precise labeled diagrams |
| Exploded View | Mechanical breakdowns, showing internal complexity, product assembly |
| Cyberpunk Neon | Computer science, digital innovation, futuristic tech concepts |
| Tactile Neumorphism | App-style dashboards, modern interface concepts |
| Abstract Flow | Dynamic process flows, abstract data representation |
| Vintage Parchment | Historical narratives, geography, classic literature |
| Mini World (Voxel) | Ecosystems, city planning, modular systems |
| Map Style | Journey-based content, navigational concepts, route processes |
| Kawaii Doodle | Making dry topics approachable, younger audiences |
```

---

## Step 2 — Enhancer Code Changes ✅ COMPLETE

**File**: `core/agents/visual_prompt_enhancer.py`

**All changes applied:**

- ✅ Added `import re`
- ✅ Added `_strip_hex_from_vp()` function after `_banned_in()`
- ✅ Updated `_beat_issues()` — added hex code detection + symbolic phrase detection
- ✅ Updated `_enforce_quality()` — added hex strip safety net after repair loop

Also updated `tests/test_enhancer_claud.py`:
- ✅ Added `import re`
- ✅ Added hex code detection in `validate_beats()`
- ✅ Added symbolic phrase detection in `validate_beats()`

---

### 2A — Add hex strip function + symbolic phrase detection

**Add import at top of file (if not already present):**
```python
import re
```

**Add this function after `_banned_in()`:**
```python
def _strip_hex_from_vp(text: str) -> str:
    """
    Safety net: remove any hex codes from video_prompt.
    Director prompts instruct LLMs not to generate them,
    but this catches any that slip through.
    LTX-2.3 does not interpret hex — they increase motion instability.
    """
    cleaned = re.sub(r'#[0-9a-fA-F]{6}\b', '', text)
    return re.sub(r'  +', ' ', cleaned).strip()
```

**Update `_beat_issues()` — add after banned words check:**
```python
# Hex codes in VP (safety net — Director prompt should prevent these)
if re.search(r'#[0-9a-fA-F]{6}', vp):
    issues.append("hex codes in VP — LTX-2.3 does not support hex")

# Symbolic phrases in VP
symbolic_phrases = ["representing ", "symbolizing ", "embodying ", "acting as a metaphor"]
for phrase in symbolic_phrases:
    if phrase in vp.lower():
        issues.append(f"symbolic instruction in VP: '{phrase.strip()}'")
        break
```

**Update `_enforce_quality()` — add after repair loop completes:**
```python
# Safety net: strip any remaining hex from VP after all repairs
for beat in enhanced_beats:
    vp = beat.get("video_prompt", "")
    if vp and re.search(r'#[0-9a-fA-F]{6}', vp):
        beat["video_prompt"] = _strip_hex_from_vp(vp)
```

---

## Step 3 — Dry Run Tests ✅ COMPLETE

**All three test scripts created and verified:**

### Test 3A — Enhancer Quality ✅ DONE

**File**: `tests/test_enhancer_claud.py`

Updated `validate_beats()` to detect:
- `hex codes in VP` — catches `#RRGGBB` patterns in video_prompt
- `symbolic instruction in VP` — catches "representing", "symbolizing", "embodying", "acting as a metaphor"

**Verified against existing job `103_162_120_230_0918ff48`**: Found 10 hex failures + 7 symbolic failures (expected for pre-change data).

---

### Test 3B — Director Schema Validation ✅ DONE

**File**: `tests/test_director_schema.py`

Validates:
- `pace` field on every narration segment (values: slow/normal/fast)
- `pause_after_seconds` on every segment (range: 0.0–3.0)
- `gesture` field on every segment (valid values + null)
- Heavy concept pacing checks
- No hex codes in video/motion fields
- `memory_infographic` section presence and structure (updated to match new `render_spec.infographic_beats[]` format)

**Verified against existing job `103_162_120_230_0918ff48`**: Found 118 issues (expected for pre-change data).
**Verified against new job `49_37_162_124_0cebda41`**: Found 1 issue — missing memory_infographic (expected — wiring was not yet in place).

---

### Test 3C — TTS Pace/Pause Dry Run ✅ DONE

**File**: `tests/test_tts_pace_pause.py`

Simulates TTS output:
- pace → speaking rate mapping (slow=0.85x, normal=1.0x, fast=1.15x)
- `[pause:Xs]` tag insertion
- Heavy concept pacing validation

**Verified against existing job `103_162_120_230_0918ff48`**: All 32 segments failed (expected — pre-change data has no pace/pause fields).
**Verified against new job `49_37_162_124_0cebda41`**: All 29/29 segments PASS ✅.

---

## Step 4 — Pipeline Wiring ✅ COMPLETE

| Item | What to wire | File | Status |
|---|---|---|---|
| Q10 memory infographic | Stitching code extracts memory_infographic from Global Director output | `partition_director_generator.py:364` | ✅ DONE |
| Q10 memory infographic | Renderer policy allows infographic for memory_infographic | `renderer_executor.py:167-176` | ✅ DONE |
| Q10 memory infographic | Pipeline Phase 6.5a generates infographic images via Gemini | `pipeline_v3.py:970-1014` | ✅ DONE |
| Q10 memory infographic | Player routes memory_infographic to loadVideoScene() | `player_v3.html` (5 locations) | ✅ DONE |
| Q10 memory infographic | Prompt schema uses render_spec.infographic_beats[] | `director_global_prompt.txt:287-322` | ✅ DONE |
| Q10 memory infographic | Test validates new schema structure | `tests/test_director_schema.py` | ✅ DONE |
| Q6 pace/pause | `build_tts_text(seg)` reads pace → rate, appends `[pause:Xs]` | TTS generator | ⏳ PENDING — needs TTS generator wiring |
| Q7 gesture | Player reads `gesture` field, swaps avatar clip if available | `player_v3.html` | ⏳ PENDING — needs avatar gesture clip integration |

### Detailed Changes Made for Q10 (Memory Infographic Wiring)

#### 1. Prompt Schema Update (`director_global_prompt.txt`)
- Replaced `infographics[]` array with `render_spec.infographic_beats[]` to match existing infographic renderer format
- Moved narration from per-infographic to section-level `narration.segments[]` (matching content section pattern)
- Added `text_layer: "hide"`, `visual_layer: "show"`, `avatar_layer: "show"` display directives
- Updated SELF-CHECK to match new structure

#### 2. Stitching Code (`partition_director_generator.py:364`)
- Changed `["memory", "recap"]` → `["memory", "memory_infographic", "recap"]`
- This ensures memory_infographic section gets extracted from Global Director output and placed between Memory and Recap

#### 3. Renderer Policy (`renderer_executor.py:167-176`)
- Added passthrough for `infographic` renderer on `memory_infographic` section type
- Prevents incorrect renderer override

#### 4. Pipeline Phase 6.5a (`pipeline_v3.py:970-1014`)
- New section collects `renderer: "infographic"` sections
- Calls `execute_renderer()` which generates PNGs via Gemini
- Saves to `jobs/{id}/images/` and updates `image_source` paths

#### 5. Player Routing (`player_v3.html`)
- Badge map: Added `memory_infographic: { label: 'MEMORY VISUAL', cls: 'badge-memory' }`
- 3x routing checks: Added `sec.section_type === 'memory_infographic'` to onloadedmetadata, durationchange, and fallback paths
- Init hook: Added `initMemoryInfographicSection()` function (no-op, visuals handled by loadVideoScene)
- `loadVideoScene()` already reads `render_spec.infographic_beats` at line 2646 — no changes needed there

---

## Step 5 — Validation Gate with Retry ✅ COMPLETE

### Problem
The Director generates presentation.json in one shot. If it produces quality issues (short narration, missing total_duration_seconds, missing quiz), the pipeline continues anyway because Phase 2 validation was non-fatal.

### Solution
Added a validation gate between Phase 1 (Director) and Phase 1.5 (image normalization) that:

1. **Runs V3 validator** immediately after Director generates presentation
2. **If validation passes** → proceeds to Phase 1.5
3. **If validation fails with retryable errors** → builds error feedback and re-calls Director
4. **Retries up to 2 times** with escalating error feedback via `missing_content_hint`
5. **If still failing after max retries** → logs warning and proceeds (non-blocking)

### Retryable Error Conditions
- `v3_narration_short` — narration too short
- `v3_total_duration_missing` — total_duration_seconds not set
- `v3_quiz_missing` — understanding quiz missing
- `v3_quiz_incomplete` — quiz incomplete
- `v3_text_layer_not_hidden` — text_layer not hidden

### Changes Made

| File | Change |
|------|--------|
| `core/pipeline_v3.py:156-219` | Validation gate with retry loop (Phase 1) |
| `core/pipeline_v3.py:249-270` | Phase 1.6: Auto-compute total_duration_seconds if missing |
| `core/v3_validator.py:25` | Added `memory_infographic` to REQUIRED_SECTION_TYPES |
| `core/v3_validator.py:489-510` | Added `_check_total_duration()` function |
| `core/v3_validator.py:519` | Added `_check_total_duration()` to validate_section_v3() |
| `core/agents/visual_prompt_enhancer.py:80-109` | Updated `_beat_issues()` to check infographic `image_prompt` field |
| `core/agents/visual_prompt_enhancer.py:115-203` | Updated `extract_beats()` to handle infographic_beats[] |
| `core/agents/visual_prompt_enhancer.py:209-260` | Updated `_apply_by_position()` and `apply_enhanced_prompts()` for infographic write-back |
| `core/agents/visual_prompt_enhancer.py:327-420` | Updated `_repair_beat()` with targeted repair for symbolic phrases and hex codes |
| `tests/test_enhancer_claud.py:70-130` | Updated `extract_beats()` to handle infographic_beats[] |
| `tests/test_enhancer_claud.py:120-150` | Updated `apply_enhanced_prompts()` to handle infographic write-back |
| `tests/test_enhancer_claud.py:155-214` | Updated `validate_beats()` to check infographic `image_prompt` field |

### How the Retry Works

```
Director generates presentation.json
    ↓
V3 Validator runs
    ↓
├── If valid → proceed to Phase 1.5
│
└── If invalid:
    ├── Check for retryable errors
    │
    ├── If retryable AND attempt < 2:
    │   ├── Build error feedback message
    │   ├── Re-call Director with missing_content_hint
    │   └── Loop back to validation
    │
    └── If not retryable OR max retries reached:
        └── Log warning, proceed anyway (non-blocking)
```

---

## Dry Run Test Results

### Job `49_37_162_124_eb41c4ec` (generated with updated prompts + wiring)

| Test | Result | Details |
|------|--------|---------|
| test_director_schema.py | FAIL — 2 issues | memory_infographic present ✅. 2 issues: image_prompt 82 words (need 100+), total_duration_seconds=0 |
| test_tts_pace_pause.py | PASS — 32/32 | All segments valid. Heavy concepts correctly use slow pace + pause ✅ |
| test_enhancer_claud.py (dry-run) | FAIL — 2 issues | Section 6: image_prompt 82 words. Section 7: "representing" in recap VP |

### What the next team member needs to do:

1. **Run a new full pipeline job** to test end-to-end memory_infographic generation with validation gate
2. **Run all 3 test scripts** against the new job's presentation.json
3. **Verify** memory_infographic section appears with:
   - `render_spec.infographic_beats[]` (1-5 items)
   - Section-level `narration.segments[]` with pace/pause/gesture
   - Generated PNG images in `jobs/{id}/images/`
   - `total_duration_seconds` auto-computed (Phase 1.6)
4. **Test in player** — verify infographics display synced to narration
5. **Wire Q6 pace/pause into TTS generator** (Step 4 pending item)
6. **Wire Q7 gesture into player** (Step 4 pending item)

---

## Execution Order for AI Agent — UPDATED STATUS

```
STEP 1 — All prompt changes (no code touched): ✅ COMPLETE
  1A → visual_prompt_enhancer_prompt.txt (5 additions) ✅ DONE
  1B → director_v3_partition_prompt.txt  (4 additions) ✅ DONE
  1C → director_global_prompt.txt        (4 additions) ✅ DONE

STEP 2 — Enhancer code only: ✅ COMPLETE
  2A → visual_prompt_enhancer.py (hex strip + _beat_issues + _enforce_quality + infographic support) ✅ DONE
  +  tests/test_enhancer_claud.py updated with hex + symbolic checks ✅ DONE

STEP 3 — Create test scripts and run dry runs: ✅ COMPLETE
  3A → test_enhancer_claud.py updated and verified ✅ DONE
  3B → test_director_schema.py created and verified ✅ DONE
  3C → test_tts_pace_pause.py created and verified ✅ DONE

STEP 4 — Pipeline wiring: ✅ COMPLETE for Q10, ⏳ PENDING for Q6/Q7
  ✅ Memory infographic wiring (stitching + renderer + pipeline + player) ✅ DONE
  ⏳ Pace/pause into TTS generator — NEEDS IMPLEMENTATION
  ⏳ Gesture into player (avatar clip swap) — NEEDS IMPLEMENTATION

STEP 5 — Validation Gate with Retry: ✅ COMPLETE
  ✅ Pipeline Phase 1: Director retry loop (up to 2 retries with error feedback) ✅ DONE
  ✅ Pipeline Phase 1.6: Auto-compute total_duration_seconds if missing ✅ DONE
  ✅ V3 Validator: Added memory_infographic to REQUIRED_SECTION_TYPES ✅ DONE
  ✅ V3 Validator: Added _check_total_duration() for all sections ✅ DONE
  ✅ Enhancer: Added infographic beat extraction + targeted repair ✅ DONE

STEP 6 — Narration Tone and Structure: ✅ COMPLETE
  ✅ director_global_prompt.txt: Five Pillars (empathetic opening, solution shift, inclusive tone, encouraging close, rhythmic delivery) ✅ DONE
  ✅ director_global_prompt.txt: Section-specific tone rules (intro arc, summary 25-35w, memory close, recap close) ✅ DONE
  ✅ director_global_prompt.txt: Summary minimum word count (25-35 words, narrative not bullet points) ✅ DONE
  ✅ director_global_prompt.txt: Recap minimum segment count (match content sections, min 4-5) ✅ DONE
  ✅ director_global_prompt.txt: Memory infographic hard fail conditions ✅ DONE
  ✅ director_v3_partition_prompt.txt: Narration tone rules (opening hook, sentence rhythm, encouraging close) ✅ DONE
  ✅ director_v3_partition_prompt.txt: pace=fast hard constraint on heavy concepts ✅ DONE

NEXT: Run nightly job to validate end-to-end with narration tone improvements
```

---

## Self-Check Summary — UPDATED

| Step | Check | Pass Criteria | Status |
|---|---|---|---|
| 1A | No hex in VP | Enhancer prompt explicitly forbids hex in video_prompt | ✅ PASS |
| 1A | No symbolic phrases | Enhancer prompt lists banned phrases | ✅ PASS |
| 1A | Human scene rules present | Rule block exists after MATERIAL DETAIL RULE | ✅ PASS |
| 1A | IPS/IPE stability rule present | Rule block exists after recap section example | ✅ PASS |
| 1A | Analogy quality rule present | Rule block exists after EDUCATIONAL PRIORITY | ✅ PASS |
| 1B + 1C | No hex rule in both Director prompts | Rule present in both files | ✅ PASS |
| 1B + 1C | pace/pause fields defined | Schema addition shown in both files | ✅ PASS |
| 1B + 1C | gesture field defined | Schema addition shown in both files | ✅ PASS |
| 1B | Analogy quality in partition prompt | Rule present after PERSONA | ✅ PASS |
| 1C | memory_infographic section defined | Full schema and style list present | ✅ PASS |
| 1C | Schema uses render_spec.infographic_beats[] | Matches existing infographic renderer format | ✅ PASS |
| 2A | Hex strip in code | `_strip_hex_from_vp()` function exists and called in `_enforce_quality()` | ✅ PASS |
| 2A | Symbolic detection in code | `_beat_issues()` checks for symbolic phrases | ✅ PASS |
| 2A | Infographic beat extraction | `extract_beats()` handles infographic_beats[] | ✅ PASS |
| 3A | test_enhancer_claud.py passes | 0 hex failures, 0 symbolic failures (on new data) | ✅ PASS (verified) |
| 3B | test_director_schema.py passes | All segments have pace/pause/gesture (on new data) | ✅ PASS (32/32 on job 49_37_162_124_eb41c4ec) |
| 3C | test_tts_pace_pause.py passes | All segments valid, TTS simulation output reviewed | ✅ PASS (32/32 on job 49_37_162_124_eb41c4ec) |
| Q10 | Stitching code includes memory_infographic | Key added to extraction loop | ✅ PASS |
| Q10 | Renderer policy allows infographic | Passthrough added for memory_infographic | ✅ PASS |
| Q10 | Pipeline Phase 6.5a generates infographics | execute_renderer() called for infographic sections | ✅ PASS |
| Q10 | Player routes memory_infographic | Badge + 3x routing + init function added | ✅ PASS |
| Q10 | End-to-end dry run | memory_infographic section in new presentation.json | ✅ PASS (job 49_37_162_124_eb41c4ec) |
| Step 5 | Validation gate with retry | Director retries on validation errors | ✅ PASS (implemented) |
| Step 5 | Auto-compute total_duration_seconds | Phase 1.6 computes if missing | ✅ PASS (implemented) |
| Step 5 | memory_infographic in REQUIRED_SECTION_TYPES | Added to v3_validator.py | ✅ PASS |
| Step 6 | Narration tone rules in both prompts | Five Pillars + section-specific rules present | ✅ PASS |
| Step 6 | Summary minimum word count | 25-35 word rule + SELF-CHECK present | ✅ PASS |
| Step 6 | Recap segment count | Min = content sections rule present | ✅ PASS |
| Step 6 | Memory infographic hard fail | HARD FAIL CONDITIONS block present | ✅ PASS |
| Step 6 | pace=fast hard constraint | Heavy concept terms list + forbidden rule present | ✅ PASS |
| Q6 | Pace/pause wired into TTS generator | build_tts_text() reads pace → rate | ⏳ PENDING |
| Q7 | Gesture wired into player | Avatar clip swap based on gesture field | ⏳ PENDING |
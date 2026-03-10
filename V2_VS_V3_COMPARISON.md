# V2 vs V3 — Architecture Comparison

## TL;DR

| Feature | V2.5 | V3 |
|---|---|---|
| **Animation Engine** | Manim (Python) | Three.js (JavaScript) |
| **Renderer** | Server renders `.mp4` video files | Browser renders live 3D scenes |
| **Text on Screen** | ✅ Text overlays allowed | ❌ Zero text — narration only |
| **Quiz** | End-of-presentation only | After every content/example section |
| **Quiz Avatar Clips** | 1 clip (question only) | 3 clips (question + correct + wrong) |
| **Player** | `player_v2.html` (hardcoded) | `player_v3.html` (data-driven from JSON) |
| **Port** | 5005 | 5006 |

---

## Pipeline Comparison

### V2.5 Pipeline
```
Document (PDF/MD)
    ↓
Smart Chunker
    ↓
Director V2.5          ← manim_scene_spec in JSON
    ↓
ManimCodeGenerator     ← Python code → server renders .mp4
    ↓
WAN Video Generator    ← Biology/History sections
    ↓
Avatar Generator       ← 1 clip per section
    ↓
presentation.json
    ↓
player_v2.html   (static layout: avatar left, video right)
```

### V3 Pipeline
```
Document (PDF/MD)
    ↓
Smart Chunker
    ↓
Director V3            ← threejs_spec (100+ words), understanding_quiz
    ↓
ThreejsCodeGenerator   ← JS code → browser renders live 3D
    ↓
Avatar Generator       ← 1 clip per section
    ↓
Quiz Clip Generator    ← 3 clips per question (question/correct/wrong)
    ↓
presentation.json
    ↓
player_v3.html   (fetches JSON dynamically, loads .js files)
```

---

## Key Technical Differences

### 1. Animation Engine

**V2.5 — Manim**
- Python library that renders math animations to `.mp4`
- Rendering happens on **server** (GPU/CPU compute needed)
- LaTeX supported natively
- Output: static video file
- If rendering fails → black screen / error

**V3 — Three.js**
- JavaScript library, runs in **browser** (student's device)
- No server GPU needed for animation
- Labels via Canvas Sprite (no LaTeX)
- Output: live interactive scene
- Student can pinch-zoom, interact with objects

---

### 2. Director Output (JSON Schema)

**V2.5 schema:**
```json
{
  "renderer": "manim",
  "manim_scene_spec": {
    "objects": [...],
    "animation_sequence": [...]
  }
}
```

**V3 schema:**
```json
{
  "renderer": "threejs",
  "threejs_spec": "Show a right triangle... (100+ words)",
  "segment_duration_seconds": 20,
  "understanding_quiz": {
    "question": "What is sin(A)?",
    "options": {"A": "Opp/Hyp", "B": "Adj/Hyp", "C": "Opp/Adj"},
    "correct": "A",
    "explanation": "SOH — Sine = Opposite over Hypotenuse"
  }
}
```

---

### 3. Player

**V2.5 Player (`player_v2.html`)**
- Hardcoded `SECTIONS` array in JS
- Layout: avatar left | video right
- Sab kuch static

**V3 Player (`player_v3.html`)**
- `fetch('presentation.json')` se sab load hota hai
- `<script>` tags dynamically inject karta hai `.js` files
- `initScene(container, duration)` call karta hai
- `avatar.onended` = master clock (avatar finishes → next scene)
- Quiz: A/B/C buttons → correct/wrong avatar clip plays

---

### 4. Quiz Experience

**V2.5:**
- Quiz sirf end mein
- Avatar ek hi clip mein question padhta hai
- Student options click karta hai → static feedback

**V3:**
- Quiz **har content section ke baad**
- 3 separate avatar clips:
  - `quiz_1_q1_question.mp4` — avatar question padhta hai
  - `quiz_1_q1_correct.mp4` — avatar "Bahut accha! Sahi jawab" bolta hai
  - `quiz_1_q1_wrong.mp4` — avatar "Nahi, sahi jawab hai..." explain karta hai

---

## File Locations

| | V2.5 | V3 |
|---|---|---|
| Project | `/ai-document-presentation-v2/` | `/ai-document-presentation-v3/` |
| Director Prompt | `director_partition_prompt.txt` | `director_v3_partition_prompt.txt` |
| Code Generator | `manim_code_generator.py` | `threejs_code_generator.py` |
| Validator | `hard_fail_validator.py` | `v3_validator.py` |
| Player | `player/player_v2.html` | `player/player_v3.html` |
| Generated Files | `jobs/{id}/videos/*.mp4` | `jobs/{id}/threejs/*.js` |
| Port | **5005** | **5006** |

---

## Why V3?

1. **No Manim install needed** — Three.js runs in browser, zero server rendering cost
2. **Interactive** — students can zoom/rotate objects
3. **Faster generation** — JS code gen is faster than Manim video rendering
4. **Better quiz UX** — avatar reacts personally to correct/wrong answers
5. **Mobile friendly** — Three.js works on phones, Manim videos are heavy

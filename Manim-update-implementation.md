✅ FINAL PRODUCTION WORKFLOW (LOCKED)
Narration
 → RendererSpecAgent (Gemini)          [LLM – unchanged]
 → JSON Visual Spec                   [DATA – unchanged]
 → Spec Validator                     [CODE – NEW, hard gate]
 → Geometry Compiler (auto/no-op)     [CODE – NEW, deterministic]
 → Manim Code Generator (Claude)      [LLM – unchanged input format]
 → Manim Renderer                     [ENGINE – unchanged]


⚠️ If Spec Validator fails → STOP + regenerate spec
⚠️ No retries past this point

📦 ENVIRONMENT (MANDATORY, EXACT)
🐍 Python
Python 3.10.x   (DO NOT use 3.11)

🎬 Manim (Community Edition – pinned)
pip install manim==0.19.0


❗ Do NOT use:

manimlib

manimgl

nightly builds

📐 System Dependencies (REQUIRED)
Ubuntu / Debian
sudo apt install -y \
  ffmpeg \
  libcairo2-dev \
  texlive-latex-base \
  texlive-latex-extra \
  texlive-fonts-extra \
  texlive-science \
  sox

Mac (brew)
brew install ffmpeg cairo pango sox
brew install --cask mactex

✅ Verify Manim
manim --version
# Must show: Manim Community v0.19.0

🧱 1️⃣ SPEC VALIDATOR (HARD GATE)

📄 spec_validator.py

ALLOWED_OBJECT_TYPES = {
    "Text", "MathTex", "Polygon", "Circle", "Line",
    "Axes", "VGroup"
}

FORBIDDEN_GEOMETRY_TERMS = {
    "edge", "edges", "side", "hypotenuse",
    "segment", "get_edges", "get_vertices"
}

def validate_spec(spec: dict):
    if "manim_scene_spec" not in spec:
        raise ValueError("Missing manim_scene_spec")

    objects = spec["manim_scene_spec"].get("objects", [])
    if not objects:
        raise ValueError("No objects defined")

    for obj in objects:
        if obj.get("type") not in ALLOWED_OBJECT_TYPES:
            raise ValueError(f"Unsupported object type: {obj.get('type')}")

        props = obj.get("properties", {})

        # ❌ Forbidden geometry language
        serialized = str(props).lower()
        for term in FORBIDDEN_GEOMETRY_TERMS:
            if term in serialized:
                raise ValueError(f"Forbidden geometry term: {term}")

        # ❌ Broken LaTeX
        if obj["type"] == "MathTex":
            latex = props.get("content", "")
            if latex.count("{") != latex.count("}"):
                raise ValueError("Unbalanced LaTeX braces")

    return True


🔒 If this fails → regenerate spec from Gemini


🧮 2️⃣ GEOMETRY COMPILER (DETERMINISTIC)

📄 geometry_compiler.py

import numpy as np

def resolve_anchor(anchor, objects):
    if anchor["type"] == "vertex":
        poly = objects[anchor["object_id"]]
        return np.array(poly["vertices"][anchor["index"]])

    if anchor["type"] == "segment_midpoint":
        poly = objects[anchor["object_id"]]
        i, j = anchor["vertices"]
        v = poly["vertices"]
        return (np.array(v[i]) + np.array(v[j])) / 2

    if anchor["type"] == "absolute":
        return np.array(anchor["position"])

    raise ValueError(f"Unsupported anchor type: {anchor['type']}")

def compile_geometry(spec: dict):
    objects = {
        obj["id"]: obj
        for obj in spec["manim_scene_spec"]["objects"]
    }

    for obj in spec["manim_scene_spec"]["objects"]:
        anchor = obj.get("anchor")
        if not anchor:
            continue

        pos = resolve_anchor(anchor, objects)
        obj["resolved_position"] = pos.tolist()

    return spec


🟢 If no anchors → no-op
🟢 Always safe

🤖 3️⃣ MANIM CODE GENERATOR (UNCHANGED, SAFER INPUT)
Claude now receives:
{
  "type": "MathTex",
  "content": "29",
  "resolved_position": [1.2, 0.6, 0]
}

Claude outputs:
label = MathTex("29").move_to([1.2, 0.6, 0])
self.play(FadeIn(label))


❌ Claude never touches geometry logic
❌ Claude never uses get_edges()
❌ Claude cannot break Manim
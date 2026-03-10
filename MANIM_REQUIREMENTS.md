# MANIM_REQUIREMENTS.md

This document serves as the official reference for the Manim rendering environment. To ensure stable video generation for mathematical and scientific content (STEM), all dependencies listed below must be satisfied.

## 1. System Packages (Linux/Debian)
These low-level libraries are required for graphics, video processing, and math conversion.

```bash
apt-get update && apt-get install -y \
    ffmpeg \                # Core video processor
    libcairo2-dev \         # 2D graphics library
    libpango1.0-dev \       # Text layout and rendering
    pkg-config \            # Manages library path for compilers
    build-essential \       # GCC/G++ compilers
    python3-dev \           # Python header files
    dvipng \                # Converts DVI to PNG
    dvisvgm \               # Required for MathTex (TeX to SVG)
```

## 2. LaTeX STEM Distribution
Mathematical formulas require a heavy LaTeX installation. **Standard texlive is NOT enough for specialized symbols.**

```bash
apt-get install -y \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-science \             # CRITICAL for Trigonometry/Math symbols
    cm-super                      # High quality font rendering
```

## 3. Python Dependencies
Add these to your `requirements.txt`:
- `manim>=0.19.0` (The core engine)
- `pydantic` (Data validation)
- `moviepy` (Video assembly)
- `mutagen` (Audio metadata)
- `edge-tts` (Voice generation)

## 4. Hardware Recommendations
- **RAM**: 4GB Minimum (8GB Recommended for parallel rendering)
- **CPU**: 2+ Core (Rendering is CPU intensive)
- **Storage**: ~2GB for full LaTeX suite.

---
## ✅ Verification Checklist
Run `check_manim_deps.bat` (Windows) or the equivalent shell commands to verify your setup.
1. `manim --version`
2. `latex --version`
3. `dvisvgm --version`
4. `ffmpeg -version`

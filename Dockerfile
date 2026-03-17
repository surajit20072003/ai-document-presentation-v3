# ==========================================
# V3 Python Backend — Manim & Three.js Pipeline
# ==========================================
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Minimal system deps — only what's needed (includes texlive for Manim)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libcairo2-dev \
    libpango1.0-dev \
    pkg-config \
    build-essential \
    libffi-dev \
    libssl-dev \
    python3-dev \
    sox \
    curl \
    texlive-latex-base \
    texlive-latex-extra \
    dvisvgm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

EXPOSE 5000

CMD ["python", "api/app.py"]

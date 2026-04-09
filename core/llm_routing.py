"""
LLM Routing Module — Per-component provider selection.

Allows each pipeline component to independently use:
  - "openrouter": Cloud APIs via https://openrouter.ai (default)
  - "local": Local Ollama server via LOCAL_LLM_URL in .env

Usage:
    from core.llm_routing import get_llm_config, DEFAULT_ROUTING

    # Build an OpenAI-compatible client for a given component
    config = get_llm_config("chunker", routing={"chunker": "local"})
    # config = {"base_url": ..., "api_key": ..., "model": ...}
"""

import os
from typing import Optional

# ── Read config from .env / environment ────────────────────────────────────────
LOCAL_LLM_URL   = os.environ.get("LOCAL_LLM_URL",    "http://69.197.145.4:11435/v1")
LOCAL_LLM_KEY   = os.environ.get("LOCAL_LLM_API_KEY", "")
LOCAL_LLM_MODEL = os.environ.get("LOCAL_LLM_MODEL",   "qwen3-coder:latest")

OPENROUTER_URL  = "https://openrouter.ai/api/v1"
OPENROUTER_KEY  = os.environ.get("OPENROUTER_API_KEY", "")

# ── Default OpenRouter models per component ────────────────────────────────────
OPENROUTER_MODELS = {
    "chunker":            os.environ.get("CHUNKER_MODEL",   "google/gemini-2.5-flash"),
    "director":           "google/gemini-2.5-pro",
    "manim_renderer":     os.environ.get("MANIM_LLM_MODEL", "anthropic/claude-sonnet-4"),
    "remotion_renderer":  "anthropic/claude-sonnet-4",
    "video_renderer":     "google/gemini-2.5-pro",
    "prompt_enhancer":    os.environ.get("ENHANCER_MODEL",  "openai/gpt-4o"),
}

# ── Default routing (all OpenRouter) — users can override per-component ────────
DEFAULT_ROUTING: dict = {
    "chunker":           "openrouter",
    "director":          "openrouter",
    "manim_renderer":    "openrouter",
    "remotion_renderer": "openrouter",
    "video_renderer":    "openrouter",
    "prompt_enhancer":   "openrouter",
}


def get_llm_config(component: str, routing: Optional[dict] = None) -> dict:
    """
    Return the LLM connection config for a given pipeline component.

    Args:
        component:  One of the keys in DEFAULT_ROUTING
                    (e.g. "chunker", "director", "manim_renderer", …)
        routing:    Per-component routing dict submitted from the dashboard.
                    Keys are component names, values are "openrouter" or "local".
                    Missing keys default to "openrouter".

    Returns:
        dict with keys: base_url, api_key, model
    """
    effective_routing = {**DEFAULT_ROUTING, **(routing or {})}
    provider = effective_routing.get(component, "openrouter")

    if provider == "local":
        return {
            "base_url": LOCAL_LLM_URL,
            "api_key":  LOCAL_LLM_KEY or "dummy-key",
            "model":    LOCAL_LLM_MODEL,
            "provider": "local",
        }
    else:
        return {
            "base_url": OPENROUTER_URL,
            "api_key":  OPENROUTER_KEY,
            "model":    OPENROUTER_MODELS.get(component, "google/gemini-2.5-flash"),
            "provider": "openrouter",
        }


def make_openai_client(component: str, routing: Optional[dict] = None):
    """
    Create an OpenAI-compatible client configured for the given component's provider.

    Returns:
        (client, model_name) tuple
    """
    from openai import OpenAI
    cfg = get_llm_config(component, routing)
    client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
    return client, cfg["model"]


def is_local(component: str, routing: Optional[dict] = None) -> bool:
    """Return True if this component is routed to the local Ollama server."""
    effective = {**DEFAULT_ROUTING, **(routing or {})}
    return effective.get(component, "openrouter") == "local"


def call_llm_routed(
    system_prompt: str,
    user_prompt: str,
    config,  # GeneratorConfig — used for temperature, max_tokens, timeout
    component: str,
    routing: Optional[dict] = None,
) -> tuple:
    """
    Drop-in replacement for call_openrouter_llm that respects llm_routing.

    Routes to local Ollama or OpenRouter based on the routing dict for
    the given component.  Returns (response_text, usage_stats) exactly
    like call_openrouter_llm does.
    """
    cfg = get_llm_config(component, routing)
    provider = cfg["provider"]
    model    = cfg["model"]

    print(f"[LLM-ROUTE] {component} → {provider} ({model})")

    if provider == "local":
        # Use OpenAI-compatible client pointed at Ollama gateway
        from openai import OpenAI
        client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=getattr(config, "temperature", 0.7),
            max_tokens=getattr(config, "max_tokens", 32000),
            timeout=600, # Hard override for slow local inference
        )
        content = resp.choices[0].message.content or ""
        usage = resp.usage or type("U", (), {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})()
        usage_stats = {
            "input_tokens":  getattr(usage, "prompt_tokens", 0),
            "output_tokens": getattr(usage, "completion_tokens", 0),
            "total_tokens":  getattr(usage, "total_tokens", 0),
            "model": model,
        }
        return content, usage_stats
    else:
        # Delegate to existing OpenRouter implementation
        from core.unified_content_generator import call_openrouter_llm
        return call_openrouter_llm(system_prompt, user_prompt, config)

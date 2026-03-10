
import os
import logging
import requests
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Default to Gemini 2.5 Flash (User Request: "Use Flash for everything")
DEFAULT_MODEL = "google/gemini-2.5-flash"
# Fallback model - sticking to Flash as requested
FALLBACK_MODEL = "google/gemini-2.5-flash" 

def get_model_name() -> str:
    """Get the configured model name from environment or default."""
    return os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)

def get_fallback_model_name() -> str:
    """Get the configured fallback model name from environment."""
    return os.environ.get("OPENROUTER_MODEL_FALLBACK", FALLBACK_MODEL)

def get_manim_model_name() -> str:
    """Get the configured Manim model name from environment."""
    # Keeping Claude/Sonnet for Manim Code Generation as it is specialized
    return os.environ.get("MANIM_LLM_MODEL", "anthropic/claude-3.5-sonnet")

def get_api_key() -> Optional[str]:
    """Get the API key from environment."""
    return os.environ.get("OPENROUTER_API_KEY")

def validate_model_access() -> Tuple[bool, str]:
    """
    Pre-flight check to verify:
    1. API Key is present
    2. Connection to OpenRouter works
    3. The specific model is accessible
    
    Returns:
        (is_valid, message)
    """
    api_key = get_api_key()
    if not api_key:
        return False, "OPENROUTER_API_KEY is missing in environment variables."

    model = get_model_name()
    logger.info(f"Pre-flight check: Validating access to model '{model}'...")

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://replit.com",  # Reusing existing referer
                "X-Title": "AI Education V2 Pre-flight"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1
            },
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Pre-flight check passed for {model}.")
            return True, f"Successfully connected to {model}"
        elif response.status_code == 401:
            return False, "401 Unauthorized - Invalid API Key."
        elif response.status_code == 404:
            return False, f"404 Not Found - Model '{model}' may be invalid or unavailable."
        else:
            error_msg = response.text[:200]
            return False, f"API Error {response.status_code}: {error_msg}"
            
    except requests.RequestException as e:
        return False, f"Network Error during pre-flight check: {str(e)}"

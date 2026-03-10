"""
V1.5 Base Agent - Common functionality for all split agents.
Each agent is a pure function: input → LLM call → validate → output
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List, Union
from openai import OpenAI
import jsonschema

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL
)

SCHEMAS_DIR = Path(__file__).parent.parent.parent / "schemas" / "v1.5"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

DEFAULT_MODEL = "google/gemini-2.5-flash"
STRONG_MODEL = "google/gemini-2.5-pro"

def load_prompt(filename: str) -> str:
    """Load a prompt file from the prompts directory."""
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text()

def load_schema(filename: str) -> Dict[str, Any]:
    """Load a JSON schema from the schemas directory."""
    path = SCHEMAS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {path}")
    return json.loads(path.read_text())

def fix_json_response(text: str) -> str:
    """Clean common LLM JSON response issues."""
    import re
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

def parse_json(text: str) -> Dict[str, Any]:
    """Parse JSON from LLM response."""
    cleaned = fix_json_response(text)
    return json.loads(cleaned)

def validate_against_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate data against a JSON schema."""
    validator = jsonschema.Draft7Validator(schema)
    errors = []
    for error in validator.iter_errors(data):
        path = " -> ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
        errors.append(f"{path}: {error.message}")
    return len(errors) == 0, errors


class AgentError(Exception):
    """Raised when an agent fails after retries."""
    def __init__(self, agent_name: str, message: str, errors: List[str], attempts: int):
        self.agent_name = agent_name
        self.message = message
        self.errors = errors
        self.attempts = attempts
        super().__init__(f"[{agent_name}] {message} after {attempts} attempts: {errors}")


class BaseAgent:
    """
    Base class for V1.5 split agents.
    
    Each agent:
    1. Takes a well-defined input contract
    2. Calls LLM with system + user prompts
    3. Validates output against schema
    4. Returns validated output or raises AgentError
    """
    
    name: str = "BaseAgent"
    system_prompt_file: str = ""
    user_prompt_file: str = ""
    output_schema_file: str = ""
    model: str = DEFAULT_MODEL
    temperature: float = 0.3
    max_tokens: Optional[int] = None  # ISS-214: No limit - let API use natural limits
    structural_retries: int = 2
    semantic_retries: int = 1
    
    def __init__(self, tracker=None, log_func=None):
        self.tracker = tracker
        self.log = log_func or print
        self._schema = None
        self._system_prompt = None
        self._user_prompt_template = None
    
    @property
    def schema(self) -> Optional[Dict[str, Any]]:
        if self._schema is None and self.output_schema_file:
            self._schema = load_schema(self.output_schema_file)
        return self._schema
    
    @property
    def system_prompt(self) -> str:
        if self._system_prompt is None:
            self._system_prompt = load_prompt(self.system_prompt_file)
        return self._system_prompt
    
    @property
    def user_prompt_template(self) -> str:
        if self._user_prompt_template is None:
            self._user_prompt_template = load_prompt(self.user_prompt_file)
        return self._user_prompt_template
    
    def build_user_prompt(self, **kwargs) -> str:
        """Build user prompt from template and kwargs."""
        prompt = self.user_prompt_template
        for key, value in kwargs.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, indent=2)
            prompt = prompt.replace(f"{{{key}}}", str(value))
        return prompt
    
    def call_llm(self, system_prompt: str, user_prompt: str) -> Tuple[str, Dict[str, Any]]:
        """Make LLM API call and return response text and usage."""
        # ISS-214: Build kwargs, only include max_tokens if explicitly set
        api_kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature
        }
        if self.max_tokens is not None:
            api_kwargs["max_tokens"] = self.max_tokens
        
        response = client.chat.completions.create(**api_kwargs)
        
        usage: Dict[str, Any] = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        
        if self.tracker:
            self.tracker.add_llm_call(
                phase=f"v15_{self.name}",
                model=self.model,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0)
            )
        
        content = response.choices[0].message.content or ""
        return content, usage
    
    def validate_structural(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate output structure against schema."""
        if self.schema:
            return validate_against_schema(output, self.schema)
        return True, []
    
    def validate_semantic(self, output: Dict[str, Any], input_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate semantic rules. Override in subclasses."""
        return True, []
    
    def _build_semantic_retry_guidance(self, errors: List[str], output: Dict[str, Any], input_data: Dict[str, Any]) -> str:
        """Build specific guidance for semantic retry based on error type."""
        import re
        guidance_parts = []
        
        for error in errors:
            if "too short" in error.lower():
                match = re.search(r'(\d+)\s*words.*min\s*(\d+)', error)
                if match:
                    current = int(match.group(1))
                    minimum = int(match.group(2))
                    delta = minimum - current + 20
                    guidance_parts.append(
                        f"EXPAND your narration by at least {delta} more words. "
                        f"Add more detailed explanations, examples, or elaboration. "
                        f"Keep the same structure but make it more comprehensive."
                    )
                else:
                    guidance_parts.append(
                        "EXPAND your content significantly - add more details and explanations."
                    )
            elif "too long" in error.lower():
                guidance_parts.append(
                    "SHORTEN your content - be more concise while keeping key information."
                )
            elif "doesn't match" in error.lower() and "segment" in error.lower():
                guidance_parts.append(
                    "Ensure segments combine to exactly match full_text word for word."
                )
            elif "text_layer" in error.lower() and "visual_layer" in error.lower():
                guidance_parts.append(
                    "FIX LAYER CONFLICT: text_layer and visual_layer CANNOT both be 'show'. "
                    "For text_only/flashcard/process content: use text_layer='show', visual_layer='hide'. "
                    "For formula/diagram/animation/video: use text_layer='hide', visual_layer='show'."
                )
            else:
                guidance_parts.append(f"Fix: {error}")
        
        return "\n".join(guidance_parts) if guidance_parts else "Address the validation errors above."
    
    def run(self, **input_data) -> Dict[str, Any]:
        """
        Execute the agent with retry logic.
        
        Returns validated output or raises AgentError.
        """
        self.log(f"[{self.name}] Starting...")
        
        user_prompt = self.build_user_prompt(**input_data)
        structural_retries_used = 0
        semantic_retries_used = 0
        total_attempts = 0
        last_errors = []
        
        while True:
            total_attempts += 1
            self.log(f"[{self.name}] Attempt {total_attempts}")
            
            try:
                response_text, usage = self.call_llm(self.system_prompt, user_prompt)
            except Exception as e:
                self.log(f"[{self.name}] LLM call failed: {e}")
                raise AgentError(self.name, "LLM call failed", [str(e)], total_attempts)
            
            try:
                output = parse_json(response_text)
            except json.JSONDecodeError as e:
                self.log(f"[{self.name}] JSON parse failed: {e}")
                if structural_retries_used < self.structural_retries:
                    structural_retries_used += 1
                    original_prompt = self.build_user_prompt(**input_data)
                    user_prompt = f"""{original_prompt}

---
RETRY REQUIRED - YOUR PREVIOUS RESPONSE WAS NOT VALID JSON.
Error: {e}

Please return ONLY valid JSON with no markdown formatting, no extra text, and no trailing commas."""
                    continue
                raise AgentError(self.name, "Invalid JSON response", [str(e)], total_attempts)
            
            valid, errors = self.validate_structural(output)
            if not valid:
                self.log(f"[{self.name}] Structural validation failed: {errors[:3]}")
                if structural_retries_used < self.structural_retries:
                    structural_retries_used += 1
                    original_prompt = self.build_user_prompt(**input_data)
                    user_prompt = f"""{original_prompt}

---
RETRY REQUIRED - YOUR PREVIOUS OUTPUT HAD STRUCTURAL ERRORS:
{json.dumps(errors[:5], indent=2)}

Fix these specific issues while keeping all other content intact. Return the COMPLETE corrected JSON."""
                    continue
                raise AgentError(self.name, "Structural validation failed", errors, total_attempts)
            
            valid, errors = self.validate_semantic(output, input_data)
            if not valid:
                self.log(f"[{self.name}] Semantic validation failed: {errors[:3]}")
                if semantic_retries_used < self.semantic_retries:
                    semantic_retries_used += 1
                    retry_guidance = self._build_semantic_retry_guidance(errors, output, input_data)
                    original_prompt = self.build_user_prompt(**input_data)
                    user_prompt = f"""{original_prompt}

---
RETRY REQUIRED - YOUR PREVIOUS OUTPUT HAD THESE ISSUES:
{json.dumps(errors[:5], indent=2)}

{retry_guidance}

Return the COMPLETE corrected JSON with all required fields."""
                    continue
                raise AgentError(self.name, "Semantic validation failed", errors, total_attempts)
            
            self.log(f"[{self.name}] Success after {total_attempts} attempt(s)")
            return output

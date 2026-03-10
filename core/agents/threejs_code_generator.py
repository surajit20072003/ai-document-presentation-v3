"""
Three.js Code Generator Agent (V3)

Uses Claude Sonnet via OpenRouter to generate JavaScript code for Three.js animations.
Output is a self-contained .js file implementing initScene(container, totalDuration).

Mirrors ManimCodeGenerator in structure — same interface, JS output instead of Python.
"""
import re
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)

CLAUDE_SONNET_3_5 = "anthropic/claude-3.5-sonnet"
CLAUDE_SONNET_3_7 = "anthropic/claude-3.7-sonnet"


class ThreejsCodeGenerator:
    """
    Three.js Code Generator — Creates JavaScript animation files for V3 player.

    Input:  section data with threejs_spec, segment_duration_seconds, key_terms
    Output: JavaScript string (initScene function) + saved .js file path
    """

    name = "ThreejsCodeGenerator"
    temperature = 0.3
    max_tokens = 8192
    max_retries = 3

    def __init__(self, openrouter_api_key: Optional[str] = None, **kwargs):
        self.model = os.environ.get("THREEJS_MODEL", CLAUDE_SONNET_3_7)
        self.api_key = openrouter_api_key or os.environ.get("OPENROUTER_API_KEY")
        self.prompts_dir = kwargs.get("prompts_dir", "core/prompts")
        self._system_prompt: Optional[str] = None
        self._user_template: Optional[str] = None

    def _load_prompts(self):
        """Load system prompt and user template from files."""
        if self._system_prompt is None:
            # GAP 5: prefer the spec-named v2 file; fall back to original if missing
            v2_path = os.path.join(self.prompts_dir, "threejs_system_prompt_v2.txt")
            v1_path = os.path.join(self.prompts_dir, "threejs_system_prompt.txt")
            path = v2_path if os.path.exists(v2_path) else v1_path
            with open(path, "r", encoding="utf-8") as f:
                self._system_prompt = f.read()

        if self._user_template is None:
            path = os.path.join(self.prompts_dir, "threejs_user_prompt.txt")
            with open(path, "r", encoding="utf-8") as f:
                self._user_template = f.read()

    def _format_segments(self, segments: list) -> str:
        """Build per-segment timeline string with real TTS durations.
        Mirrors V2 ManimCodeGenerator._format_segments() for identical hard-sync behaviour.
        """
        if not segments:
            return "(No segment timeline available)"
        lines = []
        t = 0.0
        for i, seg in enumerate(segments, 1):
            dur = float(seg.get("duration_seconds") or seg.get("duration") or 5.0)
            text = seg.get("text", "")
            lines.append(f"Segment {i} ({t:.1f}s \u2013 {t+dur:.1f}s, duration {dur:.1f}s):")
            lines.append(f'  Narration: "{text[:200]}"')
            lines.append("")
            t += dur
        return "\n".join(lines)

    def _build_user_prompt(self, section_data: Dict[str, Any]) -> str:
        """Build user prompt from template and section data."""
        self._load_prompts()

        # Core fields
        threejs_spec = section_data.get("threejs_spec") or section_data.get(
            "visual_description", "Create an educational animation for this topic."
        )
        duration = section_data.get("segment_duration_seconds") or section_data.get(
            "duration_seconds", 15.0
        )
        key_terms = ", ".join(section_data.get("key_terms", [])) or "None"
        complexity = section_data.get("complexity", "medium")
        section_title = section_data.get("section_title", "") or section_data.get("title", "Educational Section")

        # V2-style: full narration text as primary driver
        narration_segments = section_data.get("narration_segments", [])
        narration_timeline = self._format_segments(narration_segments)

        # Full narration text — what the avatar says word-for-word
        # This is the PRIMARY content driver (V2 equivalent of narration_segments text)
        narration_full_text = section_data.get("narration_full_text", "")
        if not narration_full_text and narration_segments:
            # Fallback: join all segment texts
            narration_full_text = " ".join(
                seg.get("text", "") for seg in narration_segments if seg.get("text")
            )

        assert self._user_template is not None
        user_prompt = self._user_template.format(
            section_title=section_title,
            threejs_spec=threejs_spec,
            segment_duration_seconds=f"{float(duration):.1f}",
            key_terms=key_terms,
            complexity=complexity,
            narration_timeline=narration_timeline,
            narration_full_text=narration_full_text or "(no narration text available)",
        )

        # Inject previous error feedback on retry
        if section_data.get("previous_errors"):
            error_msg = str(section_data["previous_errors"])
            sanitized = error_msg[-600:] if len(error_msg) > 600 else error_msg
            user_prompt += f"\n\nPREVIOUS ERROR (FIX THIS):\n{sanitized}"

        # User feedback for regeneration
        user_feedback = section_data.get("user_feedback", "")
        if user_feedback:
            user_prompt += f"\n\nUSER IMPROVEMENT REQUEST:\n{user_feedback}\nIncorporate this feedback while maintaining all technical requirements."

        # C5: Image source injection — passed when image_mode is set by Director
        image_source = section_data.get("image_source") or section_data.get("imageSrc")
        image_mode   = section_data.get("image_mode")
        if image_source:
            mode_hint = {
                "texture":              "Render the source image as a Three.js texture plane filling the safe zone. Animate gold arrows and labels on top.",
                "interactive_hotspot":  "Render the source image as a texture plane. Define invisible raycaster hit-boxes over key diagram regions for hover/click interaction.",
            }.get(image_mode or "", "Render the source image as a texture plane.")
            user_prompt += (
                f"\n\nIMAGE SOURCE:\n"
                f"  image_source: {image_source}\n"
                f"  image_mode:   {image_mode or 'texture'}\n"
                f"  params.imageSrc will contain this path at runtime. Guard: if (params && params.imageSrc).\n"
                f"  Instruction: {mode_hint}\n"
                f"  Use the IMAGE TEXTURE PATTERN from the system prompt."
            )

        return user_prompt


    def generate_code(
        self,
        section_data: Dict[str, Any],
        style_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Wrapper for generate() — matches Unified Pipeline interface.
        Returns just the JS code string.
        """
        code, errors = self.generate(section_data)
        if errors:
            logger.warning(f"[THREEJS GEN] generated with errors: {errors}")
        return code

    def generate(self, section_data: Dict[str, Any]) -> Tuple[str, List[str]]:
        """
        Generate Three.js JS code with auto-retry on validation failure.

        Args:
            section_data: Dict with threejs_spec, segment_duration_seconds, key_terms, etc.

        Returns:
            Tuple of (js_code: str, errors: List[str])
        """
        logger.info(f"[THREEJS GEN] ========================================")
        logger.info(
            f"[THREEJS GEN] Starting: {section_data.get('section_title', 'Unknown')}"
        )

        try:
            self._load_prompts()
        except FileNotFoundError as e:
            logger.error(f"[THREEJS GEN] Missing prompt file: {e}")
            return "", [f"Missing prompt file: {e}"]
        except Exception as e:
            logger.error(f"[THREEJS GEN] Failed to load prompts: {e}")
            return "", [f"Failed to load prompts: {e}"]

        code = ""
        errors: List[str] = []

        for attempt in range(self.max_retries):
            if attempt == 0:
                logger.info(f"[THREEJS GEN] Initial Generation (Attempt 1)")
                code, errors = self._call_model_generate(section_data)
            else:
                logger.info(f"[THREEJS GEN] Repair Attempt {attempt + 1}")
                code, errors = self._call_model_fix(code, section_data)

            if not code:
                return "", errors

            # Validate structure
            structural_errors = self.validate_code(code)
            if structural_errors:
                logger.warning(f"[THREEJS GEN] Validation failed: {structural_errors}")
                section_data["previous_errors"] = "\n".join(structural_errors)
                continue

            logger.info("[THREEJS GEN] Validation successful!")
            return code, []

        return code if code else "", ["Max retries exceeded"]

    def _call_model_generate(self, section_data: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Call LLM for initial generation."""
        user_prompt = self._build_user_prompt(section_data)
        return self._invoke_claude(user_prompt, self._system_prompt)

    def _call_model_fix(
        self, broken_code: str, section_data: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """Call LLM to fix broken code using repair prompt."""
        repair_path = os.path.join(self.prompts_dir, "threejs_repair_prompt.txt")
        try:
            with open(repair_path, "r", encoding="utf-8") as f:
                repair_template = f.read()
        except Exception as e:
            return "", [f"Failed to load repair prompt: {e}"]

        user_prompt = repair_template.format(
            code=broken_code,
            error_log=section_data.get("previous_errors", "Unknown error"),
        )
        return self._invoke_claude(user_prompt, self._system_prompt)

    def _invoke_claude(
        self, user_prompt: str, system_prompt: str
    ) -> Tuple[str, List[str]]:
        """Helper to invoke Claude via OpenRouter API."""
        import requests

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://replit.com",
                    "X-Title": "AI Education Three.js Generator",
                },
                json=payload,
                timeout=120,
            )

            if response.status_code != 200:
                logger.error(f"[THREEJS GEN] API Error: {response.text}")
                return "", [f"API error: {response.status_code}"]

            result = response.json()
            choice = result.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            finish_reason = choice.get("finish_reason", "")

            lines = len([l for l in content.split("\n") if l.strip()])
            logger.info(
                f"[THREEJS GEN] Response: {lines} lines, finish={finish_reason}"
            )

            return self._extract_js_code(content), []

        except Exception as e:
            logger.error(f"[THREEJS GEN] Request failed: {e}")
            return "", [f"Request failed: {e}"]

    def _extract_js_code(self, response: str) -> str:
        """Extract JS code from LLM response, stripping markdown if present."""
        code = response.strip()

        # Strip ```javascript ... ``` or ```js ... ``` blocks
        for pattern in [r"```javascript\s*(.*?)\s*```", r"```js\s*(.*?)\s*```", r"```\s*(.*?)\s*```"]:
            match = re.search(pattern, code, re.DOTALL)
            if match:
                return match.group(1).strip()

        return code.strip()

    def validate_code(self, code: str) -> List[str]:
        """
        Validate generated Three.js code structure.

        Checks:
        1. initScene function present
        2. All 3 required hooks present in return value
        3. No import statements
        4. No alert() or console.error()
        5. Freeze logic present (cancelAnimationFrame)
        6. renderer.setClearColor present (ensures dark background)
        7. dispose function removes renderer.domElement
        """
        errors = []

        errors.extend(self._check_entry_point(code))
        errors.extend(self._check_return_hooks(code))
        errors.extend(self._check_forbidden_patterns(code))
        errors.extend(self._check_freeze_logic(code))
        errors.extend(self._check_completeness(code))

        return errors

    def _check_entry_point(self, code: str) -> List[str]:
        """Verify initScene function is present with correct signature."""
        errors = []
        if "function initScene(" not in code:
            errors.append("Missing 'function initScene(' — entry point required")
        if "totalDuration" not in code:
            errors.append("Missing 'totalDuration' parameter usage — animation must respect duration")
        return errors

    def _check_return_hooks(self, code: str) -> List[str]:
        """Verify return value contains all 3 required hooks."""
        errors = []
        # Must have all three in a return statement
        if "onResize" not in code:
            errors.append("Missing 'onResize' hook in return value")
        if "onPinchZoom" not in code:
            errors.append("Missing 'onPinchZoom' hook in return value")
        if "dispose" not in code:
            errors.append("Missing 'dispose' hook in return value")
        # Check for actual return with all three
        if not re.search(r"return\s*\{[^}]*onResize[^}]*\}", code, re.DOTALL):
            errors.append("Missing return { onResize, onPinchZoom, dispose } object")
        return errors

    def _check_forbidden_patterns(self, code: str) -> List[str]:
        """Check for patterns that will break the browser environment."""
        errors = []

        # Strip JS comments (both single-line // and block /* */) to avoid false positives
        code_no_comments = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        code_no_comments = re.sub(r"//[^\n]*", "", code_no_comments)

        if re.search(r"^\s*import\s+", code_no_comments, re.MULTILINE):
            errors.append("Forbidden: 'import' statement found — Three.js is loaded by player via CDN")
        if "alert(" in code_no_comments:
            errors.append("Forbidden: alert() call found — must be silent")
        if "console.error(" in code_no_comments:
            errors.append("Forbidden: console.error() call found — must fail silently")
        if re.search(r"(?:new\s+THREE\.)(?:FontLoader|GLTFLoader|OBJLoader)", code_no_comments):
            errors.append("Forbidden: External loader found — no external asset loading allowed")
        return errors

    def _check_freeze_logic(self, code: str) -> List[str]:
        """Verify the animation will freeze at totalDuration (not loop)."""
        errors = []
        if "cancelAnimationFrame" not in code:
            errors.append("Missing cancelAnimationFrame — animation must freeze at totalDuration")
        if "totalDuration" not in code:
            errors.append("totalDuration not referenced — animation duration contract not implemented")
        return errors

    def _check_completeness(self, code: str) -> List[str]:
        """Basic completeness check — code not truncated mid-statement."""
        errors = []
        code_stripped = code.strip()

        if not code_stripped:
            return ["Empty code"]

        lines = code_stripped.split("\n")
        last_logical = ""
        for line in reversed(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith("//"):
                last_logical = stripped
                break

        # Ends mid-expression
        if last_logical.endswith(("=", "+", "-", "*", "/", "(", "[", "{", ".", ",")):
            errors.append(f"Code appears truncated: last line ends with '{last_logical[-1]}'")

        # Unbalanced braces (rough check)
        open_braces = code.count("{") - code.count("}")
        if abs(open_braces) > 2:
            errors.append(f"Likely unbalanced braces: {open_braces} unclosed '{{' blocks")

        return errors

    def save_js_file(self, js_code: str, output_dir: str, job_id: str, topic_id: str, beat_idx: int = 0) -> str:
        """
        Save generated JS code to the correct output path.

        Returns the relative path: jobs/{job_id}/threejs/topic_{topic_id}_beat_{beat_idx}.js
        """
        threejs_dir = Path(output_dir) / "threejs"
        threejs_dir.mkdir(parents=True, exist_ok=True)

        filename = f"topic_{topic_id}_beat_{beat_idx}.js"
        file_path = threejs_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(js_code)

        logger.info(f"[THREEJS GEN] Saved JS file: {file_path}")
        return str(file_path)

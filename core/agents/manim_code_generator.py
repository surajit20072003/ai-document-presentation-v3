"""
Manim Code Generator Agent (REQ-060 through REQ-068)

Uses Claude Sonnet 3.5 via OpenRouter to generate Python code for Manim animations.
Output is raw Python code for construct(self) method body, not JSON spec.

ISS-151: Enhanced with proper AST validation, retry logic, and graceful failure handling.
"""
import re
import os
import ast
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)

CLAUDE_SONNET_3_5 = "anthropic/claude-3.5-sonnet"
CLAUDE_SONNET_4_5 = "anthropic/claude-sonnet-4-20250514"

class ManimCodeGenerator:
    """
    Manim Code Generator - Creates Python code for Manim animations.
    
    Input: section data with TTS timing and visual descriptions
    Output: Python code string for construct(self) method body
    """
    
    name = "ManimCodeGenerator"
    temperature = 0.3
    max_tokens = 8192  # Claude Sonnet 4.5 output limit
    max_retries = 3
    
    def __init__(self, openrouter_api_key: Optional[str] = None, **kwargs):
        from core.llm_config import get_manim_model_name
        self.model = get_manim_model_name()
        self.api_key = openrouter_api_key or os.environ.get("OPENROUTER_API_KEY")
        self.prompts_dir = kwargs.get("prompts_dir", "core/prompts")
        self._system_prompt: Optional[str] = None
        self._user_template: Optional[str] = None
        
    def _load_prompts(self):
        """Load system prompt and user template from files."""
        if self._system_prompt is None:
            # V2.5 PROMPT: Use v25 prompts for Manim generation
            system_path = os.path.join(self.prompts_dir, "manim_system_prompt_v25.txt")
            if not os.path.exists(system_path):
                system_path = os.path.join(self.prompts_dir, "manim_system_prompt_v25.txt")
            
            with open(system_path, "r", encoding="utf-8") as f:
                self._system_prompt = f.read()
        
        if self._user_template is None:
            template_path = os.path.join(self.prompts_dir, "manim_user_prompt_v25.txt")
            if not os.path.exists(template_path):
                 template_path = os.path.join(self.prompts_dir, "manim_user_prompt_v25.txt")
                 
            with open(template_path, "r", encoding="utf-8") as f:
                self._user_template = f.read()
    
    def _build_user_prompt(self, section_data: Dict[str, Any]) -> str:
        """Build user prompt from template and section data."""
        self._load_prompts()
        
        # FIX 1: Send cleaner segments (without per-segment visual noise)
        narration_segments_text = self._format_segments(section_data.get("narration_segments", []))
        
        # FIX 2: Soften the Director's spec to allow for Simplification
        raw_visual = section_data.get("manim_spec") or section_data.get("visual_description", "Create appropriate visualization")
        visual_description = f"VISUAL GUIDE (SIMPLIFY AS NEEDED):\n{raw_visual}"

        formulas = ", ".join(section_data.get("formulas", [])) or "None"
        key_terms = ", ".join(section_data.get("key_terms", [])) or "None"
        
        # Calculate strict duration
        total_duration = sum(seg.get("duration_seconds") or seg.get("duration", 5.0) for seg in section_data.get("narration_segments", []))
        
        special_requirements = section_data.get("special_requirements", "None")
        
        # FIX 3: Truncate error logs to prevent Context Window overflow
        if section_data.get("previous_errors"):
            error_msg = str(section_data['previous_errors'])
            # Only keep the last 500 chars (usually contains the actual error)
            sanitized_error = error_msg[-500:] if len(error_msg) > 500 else error_msg
            special_requirements += f"\n\nPREVIOUS ERROR (FIX THIS): {sanitized_error}"
        
        # Axes ranges - use defaults if not specified
        x_min = section_data.get("x_min", -5)
        x_max = section_data.get("x_max", 5)

        assert self._user_template is not None, "User template not loaded"
        user_prompt = self._user_template.format(
            section_title=section_data.get("section_title", "Educational Section"),
            narration_segments=narration_segments_text,
            visual_description=visual_description,
            formulas=formulas,
            key_terms=key_terms,
            total_duration=f"{total_duration:.1f}",
            special_requirements=special_requirements
        )
        
        # NEW FEATURE: User feedback for regeneration
        user_feedback = section_data.get("user_feedback", "")
        if user_feedback:
            user_prompt += f"""

---
USER'S IMPROVEMENT REQUEST:
{user_feedback}

IMPORTANT: The user has specifically requested the above improvements. Please revise the animation to incorporate this feedback while maintaining all technical requirements and narration timing.
---
"""
        
        return user_prompt
    
    def _format_segments(self, segments: List[Dict]) -> str:
        """Format narration segments for the prompt."""
        lines = []
        current_time = 0.0
        
        for i, seg in enumerate(segments, 1):
            duration = seg.get("duration_seconds") or seg.get("duration", 5.0)
            text = seg.get("text", "")
            # FIX 1 (Part B): Do NOT append 'Visual:' here. It duplicates the global plan.
            
            end_time = current_time + duration
            
            lines.append(f"Segment {i} ({current_time:.1f}s - {end_time:.1f}s, duration {duration:.1f}s):")
            lines.append(f"  Narration: \"{text}\"")
            lines.append("")
            
            current_time = end_time
        
        return "\n".join(lines)

    def generate_code(self, section_data: Dict[str, Any], style_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Wrapper for generate() to match Unified Pipeline interface.
        Returns just the code string.
        """
        code, errors = self.generate(section_data)
        if errors:
             logger.warning(f"[MANIM GEN] generated with errors: {errors}")
        return code
    
    def generate(self, section_data: Dict[str, Any]) -> Tuple[str, List[str]]:
        """
        Generate Manim code for a section with auto-retry on validation failure.
        
        Args:
            section_data: Dict containing section_title, narration_segments, visual_description, etc.
            
        Returns:
            Tuple of (python_code: str, errors: List[str])
            If successful, errors will be empty.
        """
        import requests
        
        # Debug: Log generation start
        logger.info(f"[MANIM GEN] ========================================")
        logger.info(f"[MANIM GEN] Starting generation for section: {section_data.get('section_title', 'Unknown')}")
        logger.debug(f"[MANIM GEN] Narration segments: {len(section_data.get('narration_segments', []))}")
        logger.debug(f"[MANIM GEN] Visual description: {section_data.get('visual_description', 'None')[:100]}")
        
        try:
            self._load_prompts()
        except FileNotFoundError as e:
            logger.error(f"[MANIM GEN] Missing prompt file: {e}")
            return "", [f"Missing prompt file: {e}"]
        except Exception as e:
            logger.error(f"[MANIM GEN] Failed to load prompts: {e}")
            return "", [f"Failed to load prompts: {e}"]
        
        code = ""
        errors: List[str] = []
        
        for attempt in range(self.max_retries):
            if attempt == 0:
                # First attempt: Generation
                logger.info(f"[MANIM GEN] Initial Generation (Attempt {attempt + 1})")
                code, errors = self._call_model_generate(section_data)
            else:
                # Subsequent attempts: Correction
                logger.info(f"[MANIM GEN] Correction Attempt {attempt + 1}")
                logger.warning(f"[MANIM GEN] Previous errors to fix: {section_data.get('previous_errors')}")
                code, errors = self._call_model_fix(code, section_data)
            
            if not code:
                return "", errors

            # NEW: Validate RAW code BEFORE timing sync to catch truncation
            # This prevents _enforce_timing from masking truncated code with balanced wait() calls
            raw_completeness_errors = self._check_completeness(code)
            if raw_completeness_errors:
                logger.warning(f"[MANIM GEN] RAW Completeness check failed: {raw_completeness_errors}")
                section_data["previous_errors"] = f"Code appears truncated or incomplete:\n" + "\n".join(raw_completeness_errors)
                continue

            # HARD SYNC ENFORCEMENT (V2 Feature)
            # We programmatically inject self.wait() to match narration timing perfectly
            # V2.6: Also injects FadeOut to ensure clean screen between segments
            has_sync = False
            if code and "# Segment" in code:
                try:
                    logger.info("[MANIM GEN] Applying Hard Sync timing enforcement...")
                    code = self._enforce_timing(code, section_data)
                    has_sync = True
                    logger.debug("[MANIM GEN] Hard Sync applied successfully")
                except Exception as e:
                    logger.warning(f"[MANIM GEN] Hard Sync failed (proceeding with raw code): {e}")
            else:
                 logger.debug("[MANIM GEN] Skipping Hard Sync: No '# Segment' markers found.")

            # Final Validation Phase
            # 1. Structural Validation (V2.6: Skip timing check if Hard Sync was applied)
            structural_errors = self.validate_code(code, section_data, skip_timing=has_sync)
            if structural_errors:
                logger.warning(f"[MANIM GEN] Final validation failed: {structural_errors}")
                section_data["previous_errors"] = "\n".join(structural_errors)
                continue
            
            # 2. Dry-Run Render Validation (New Robustness Feature)
            # Only run if structure is valid. This catches Manim-specific runtime errors.
            runtime_error = self._validate_runtime(code, section_data)
            if runtime_error:
                logger.warning(f"[MANIM GEN] Runtime validation failed: {runtime_error}")
                section_data["previous_errors"] = f"Runtime Error:\n{runtime_error}"
                continue
                
            # NEW: Post-processing scrubber for wait(0.0) which crashes Manim 0.19
            code = self._scrub_invalid_waits(code)

            # If we got here, code is valid!
            logger.info("[MANIM GEN] Validation successful!")
            return code, []

        
        return code if code else "", ["Max retries exceeded"]

    def _call_model_generate(self, section_data: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Call LLM for initial generation."""
        user_prompt = self._build_user_prompt(section_data)
        return self._invoke_claude(user_prompt, self._system_prompt)

    def _call_model_fix(self, broken_code: str, section_data: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Call LLM to fix broken code."""
        # Load repair prompt
        repair_template_path = os.path.join(self.prompts_dir, "manim_repair_prompt.txt")
        try:
            with open(repair_template_path, "r", encoding="utf-8") as f:
                repair_template = f.read()
        except Exception as e:
            return "", [f"Failed to load repair prompt: {e}"]
            
        user_prompt = repair_template.format(
            code=broken_code,
            error_log=section_data.get("previous_errors", "Unknown error")
        )
        # Use same system prompt
        return self._invoke_claude(user_prompt, self._system_prompt)

    def _invoke_claude(self, user_prompt: str, system_prompt: str) -> Tuple[str, List[str]]:
        """Helper to invoke Claude API."""
        import requests
        
        request_payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens or 8192
        }
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://replit.com",
                    "X-Title": "AI Education Manim Generator"
                },
                json=request_payload,
                timeout=120
            )
            
            if response.status_code != 200:
                logger.error(f"[MANIM GEN] API Error: {response.text}")
                return "", [f"API error: {response.status_code}"]
                
            result = response.json()
            choice = result.get("choices", [{}])[0]
            code = choice.get("message", {}).get("content", "")
            finish_reason = choice.get("finish_reason", "")
            
            # Log Code Stats
            lines = len([l for l in code.split('\n') if l.strip()])
            logger.info(f"[MANIM SONNET 4.5] Code stats: {lines} lines, Finish: {finish_reason}")
            
            return self._extract_python_code(code), []
        except Exception as e:
            logger.error(f"[MANIM GEN] Request failed: {e}")
            return "", [f"Request failed: {e}"]
            
    def _validate_runtime(self, code: str, section_data: Dict[str, Any]) -> Optional[str]:
        """
        Run a dry-run render of the code using manim command.
        Returns error string if failed, None if success.
        Can be skipped via SKIP_MANIM_VALIDATION=true env var.
        """
        # OPTIMIZATION: Skip validation if requested
        import os
        if os.environ.get("SKIP_MANIM_VALIDATION", "").lower() == "true":
            logger.info("[MANIM GEN] Skipping runtime validation (configured via env).")
            return None # Return None for success, as per original return type
        
        # Check if this is already full code (V2) or needs wrapping
        is_full_code = "class " in code and "Scene" in code and "def construct" in code
        import tempfile
        import subprocess
        
        # V2 FULL CODE CHECK: If code already has imports and class, DO NOT WRAP IT
        if "from manim import" in code and "class " in code and "(Scene):" in code:
             full_scene_code = code
        else:
             # Legacy V1 behavior: Wrap body in TestScene
             full_scene_code = "from manim import *\n\nclass TestScene(Scene):\n    def construct(self):\n"
             indented_body = "\n".join("        " + line for line in code.split("\n"))
             full_scene_code += indented_body
        
        try:
            with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
                tmp.write(full_scene_code)
                tmp_path = tmp.name
                
            # Run Manim dry-run
            # -q l: Low quality (fast)
            # --dry_run: Don't actually render video frames, just setup scenes (checking logic)
            # --disable_caching: Ensure we check fresh
            cmd = ["manim", "-q", "l", "--dry_run", "--disable_caching", tmp_path, "TestScene"]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30  # Should be fast for dry-run
            )
            
            os.unlink(tmp_path)
            
            if result.returncode != 0:
                # Extract relevant error from stderr
                stderr = result.stderr
                # Try to get the last few lines which usually contain the Traceback
                return f"Manim Dry-Run Failed (RC={result.returncode}):\n{stderr[-1000:]}"
            
            return None
            
        except Exception as e:
            return f"Validation harness error: {str(e)}"
    
    def _scrub_invalid_waits(self, code: str) -> str:
        """Remove self.wait(0) and self.wait(0.0) which cause Manim crashes."""
        # Match wait(0) or wait(0.0) with optional whitespace
        # More explicit regex than before
        cleaned = re.sub(r'self\.wait\(\s*0(?:\.0)?\s*\)', '', code)
        return cleaned

    def _extract_python_code(self, response: str) -> str:

        """Extract Python code from LLM response, removing markdown if present."""
        code = response.strip()
        
        if "```python" in code:
            match = re.search(r"```python\s*(.*?)\s*```", code, re.DOTALL)
            if match:
                code = match.group(1)
        elif "```" in code:
            match = re.search(r"```\s*(.*?)\s*```", code, re.DOTALL)
            if match:
                code = match.group(1)
        
        return code.strip()
    
    def validate_code(self, code: str, section_data: Dict[str, Any], skip_timing: bool = False) -> List[str]:
        """
        Validate generated Manim code.
        
        Checks:
        1. Syntax validity (compile test)
        2. No Dot() placeholders
        3. Timing matches segment durations (±0.5s tolerance) - Opt-out via skip_timing
        4. No variable overwrites (e.g., axes = axes.plot())
        5. No common runtime error patterns
        6. Code completeness
        """
        errors = []
        
        errors.extend(self._check_syntax(code))
        
        errors.extend(self._check_placeholders(code))
        
        # V2.5 HARD SYNC: Granular Segment Timing & Cleanup Validation
        # V2.6: Skip if programmatically enforced
        if not skip_timing:
            errors.extend(self._check_granular_timing(code, section_data))
        else:
            logger.info("[MANIM GEN] Skipping timing validation (Hard Sync applied)")
        
        errors.extend(self._check_variable_overwrites(code))
        
        errors.extend(self._check_runtime_patterns(code))
        
        errors.extend(self._check_completeness(code))
        
        errors.extend(self._check_structure(code))
        
        errors.extend(self._check_forbidden_chars(code))
        
        return errors
    
    def _check_structure(self, code: str) -> List[str]:
        """Check for mandatory Manim structure."""
        errors = []
        if "from manim import *" not in code:
            errors.append("Missing 'from manim import *'")
        
        # Check for class definition (allow any name inheriting from Scene)
        if not re.search(r'class\s+\w+\(.*Scene\):', code):
            errors.append("Missing Class definition inheriting from Scene (e.g. 'class MainScene(Scene):')")
            
        if "def construct(self):" not in code:
            errors.append("Missing 'def construct(self):' method")
            
        return errors

    def _check_forbidden_chars(self, code: str) -> List[str]:
        """Check for non-ASCII characters that cause Manim/LaTeX crashes."""
        errors = []
        forbidden = ['₹', '•', '…', '“', '”', '‘', '’', '×', '÷', '°']
        
        for char in forbidden:
            if char in code:
                errors.append(f"Forbidden character detected: '{char}' (Replace with standard ASCII)")
                
        # General non-ASCII check (excluding comments if possible, but safer to ban all for now)
        # We allow basic Latin-1 supplement if needed, but strictly no multi-byte unicode symbols
        try:
            code.encode('ascii')
        except UnicodeEncodeError as e:
            # Find the specific character
            bad_char = code[e.start:e.end]
            if bad_char not in forbidden: # Avoid duplicate error if already caught
                 errors.append(f"Non-ASCII character detected at position {e.start}: '{bad_char}'")
        
        return errors
    
    def _check_runtime_patterns(self, code: str) -> List[str]:
        """Check for patterns that cause runtime errors in Manim."""
        errors = []
        
        # Check for animate on Axes range properties (these are lists, not animatable)
        if re.search(r'axes\.x_range\[?\d*\]?\.animate', code):
            errors.append("Cannot animate axes.x_range - use ValueTracker instead")
        if re.search(r'axes\.y_range\[?\d*\]?\.animate', code):
            errors.append("Cannot animate axes.y_range - use ValueTracker instead")
        
        # Note: VGroup[index].animate IS valid in Manim, so we don't block general list indexing
        
        # Check for always_redraw referencing undefined trackers
        always_redraw_matches = re.findall(r'always_redraw\s*\([^)]*(\w+)\.get_value', code)
        for tracker in always_redraw_matches:
            if not re.search(rf'{tracker}\s*=\s*ValueTracker', code):
                errors.append(f"always_redraw references '{tracker}' but no ValueTracker with that name found")
        
        return errors
    
    def _check_completeness(self, code: str) -> List[str]:
        """
        Check if code is complete (not truncated mid-statement).
        
        Checks:
        1. Control structures without bodies
        2. Bare identifiers on last line (truncation artifact)
        3. Lines ending with operators (truncation artifact)
        4. compile() syntax check as final catch-all
        """
        errors = []
        
        lines = code.strip().split('\n')
        if not lines:
            return ["Empty code"]
        
        # 1. Check for truly incomplete control structures
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
                
            if stripped.endswith(':'):
                has_body = False
                for next_line in lines[i+1:]:
                    next_stripped = next_line.strip()
                    if next_stripped and not next_stripped.startswith('#'):
                        has_body = True
                        break
                
                if not has_body:
                    errors.append(f"Control structure at line {i+1} has no body: '{stripped[:60]}...'")
        
        # 2. Check for truncated last logical line
        last_logical = ""
        last_logical_idx = 0
        for i in range(len(lines) - 1, -1, -1):
            stripped = lines[i].strip()
            if stripped and not stripped.startswith('#'):
                last_logical = stripped
                last_logical_idx = i + 1
                break
        
        if last_logical:
            import keyword
            # Bare identifier (e.g. 'n' from truncated 'n_box = ...')
            if (last_logical.isidentifier() 
                and not keyword.iskeyword(last_logical) 
                and last_logical not in ('self', 'pass', 'True', 'False', 'None')):
                errors.append(f"Code appears truncated at line {last_logical_idx}: bare identifier '{last_logical}'")
            
            # Lines ending with operators
            if last_logical.endswith(('=', '+', '-', '*', '/', '(', '[', '{', '.', '\\')):
                errors.append(f"Code appears truncated at line {last_logical_idx}: ends with '{last_logical[-1]}'")
        
        # 3. compile() as final syntax check
        try:
            compile(code, "<completeness_check>", "exec")
        except SyntaxError as e:
            errors.append(f"Syntax error (possible truncation) at line {e.lineno}: {e.msg}")
        
        return errors
    
    def _check_syntax(self, code: str) -> List[str]:
        """Check Python syntax validity using AST parsing (ISS-151)."""
        errors = []
        
        try:
            compile(code, "<string>", "exec")
        except SyntaxError as e:
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
            return errors
        
        try:
            tree = ast.parse(code)
            
            undefined_names = self._check_undefined_names(tree, code)
            if undefined_names:
                # RELAXATION: Only log as warning to console, don't block.
                # Let dry-run + LLM fix it if it's a real error.
                logger.info(f"[MANIM GEN] Validation note - potentially unknown names: {undefined_names[:5]}")
        except Exception as e:
            logger.warning(f"AST analysis warning: {e}")
        
        return errors
    
    def _check_undefined_names(self, tree: ast.AST, code: str) -> List[str]:
        """Check for potentially undefined variable names in the code."""
        defined_names = set()
        used_names = set()
        
        manim_builtins = {
            # Mobjects - shapes
            'Text', 'MathTex', 'Tex', 'Circle', 'Rectangle', 'Arrow', 'Line',
            'Dot', 'Square', 'Triangle', 'Polygon', 'Arc', 'Ellipse', 'Annulus',
            'DashedLine', 'DoubleArrow', 'Vector', 'CurvedArrow', 'CurvedDoubleArrow',
            'NumberLine', 'Axes', 'NumberPlane', 'Graph', 'VGroup', 'Group', 'VMobject',
            'ThreeDAxes', 'Surface', 'Sphere', 'Cube', 'Prism', 'Cone', 'Cylinder',
            # Labels and annotations
            'Brace', 'BraceLabel', 'BraceText', 'BraceBetweenPoints',
            'DecimalNumber', 'Integer', 'Variable', 'MathTable', 'Table',
            'SurroundingRectangle', 'BackgroundRectangle', 'Cross', 'Underline',
            'Title', 'Paragraph', 'MarkupText', 'Code',
            # Animations - creation
            'Write', 'FadeIn', 'FadeOut', 'Transform', 'ReplacementTransform',
            'MoveToTarget', 'Indicate', 'Circumscribe', 'Create', 'Uncreate',
            'GrowFromCenter', 'SpinInFromNothing', 'ShrinkToCenter', 'DrawBorderThenFill',
            'ShowCreation', 'ShowPassingFlash', 'ApplyWave', 'Wiggle',
            'GrowArrow', 'GrowFromPoint', 'GrowFromEdge', 'ShowIncreasingSubsets',
            'AddTextLetterByLetter', 'RemoveTextLetterByLetter',
            # Animations - transforms
            'ApplyMethod', 'ApplyPointwiseFunction', 'ApplyMatrix', 'Rotate',
            'ScaleInPlace', 'AnimationGroup', 'Succession', 'LaggedStart', 'LaggedStartMap',
            'Wait', 'Homotopy', 'TransformMatchingShapes', 'TransformMatchingTex',
            # Directions and positions
            'UP', 'DOWN', 'LEFT', 'RIGHT', 'ORIGIN', 'UL', 'UR', 'DL', 'DR',
            'OUT', 'IN', 'SMALL_BUFF', 'MED_SMALL_BUFF', 'MED_LARGE_BUFF', 'LARGE_BUFF',
            # Constants
            'PI', 'TAU', 'DEGREES', 'DEFAULT_FONT_SIZE',
            # Colors
            'WHITE', 'BLACK', 'RED', 'GREEN', 'BLUE', 'YELLOW', 'ORANGE', 'PURPLE', 
            'PINK', 'GRAY', 'GREY', 'GOLD', 'TEAL', 'MAROON', 'LIGHT_GRAY', 'DARK_GRAY',
            'RED_A', 'RED_B', 'RED_C', 'RED_D', 'RED_E', 'BLUE_A', 'BLUE_B', 'BLUE_C', 
            'BLUE_D', 'BLUE_E', 'GREEN_A', 'GREEN_B', 'GREEN_C', 'GREEN_D', 'GREEN_E',
            'YELLOW_A', 'YELLOW_B', 'YELLOW_C', 'YELLOW_D', 'YELLOW_E',
            # Python builtins
            'self', 'range', 'len', 'str', 'int', 'float', 'list', 'dict', 'tuple', 'set',
            'True', 'False', 'None', 'lambda', 'abs', 'min', 'max', 'sum', 'zip', 'map',
            'filter', 'enumerate', 'sorted', 'reversed', 'round', 'print', 'isinstance',
            # Manim utilities
            'ValueTracker', 'always_redraw', 'Updater', 'UpdateFromFunc',
            'TracedPath', 'ParametricFunction', 'FunctionGraph',
            'rate_functions', 'linear', 'smooth', 'there_and_back', 'rush_into', 'rush_from',
            # External modules commonly used
            'np', 'numpy', 'math', 'config', 'interpolate'
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_names.add(target.id)
                    elif isinstance(target, ast.Tuple):
                        for elt in target.elts:
                            if isinstance(elt, ast.Name):
                                defined_names.add(elt.id)
            elif isinstance(node, ast.For):
                if isinstance(node.target, ast.Name):
                    defined_names.add(node.target.id)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
        
        undefined = used_names - defined_names - manim_builtins
        return list(undefined)
    
    def _check_placeholders(self, code: str) -> List[str]:
        """Check for Dot() placeholder usage."""
        errors = []
        
        dot_pattern = re.compile(r'\bDot\s*\(\s*\)')
        
        for i, line in enumerate(code.split("\n"), 1):
            if dot_pattern.search(line):
                errors.append(f"Line {i}: Dot() placeholder detected - use actual Manim objects instead")
        
        return errors
    
    def _check_granular_timing(self, code: str, section_data: Dict[str, Any]) -> List[str]:
        """
        V2.5 Specialized Validator: Timing, Pacing, and Cleanup.
        Uses manim_timing_validator.py to perform segment-level checks.
        """
        import tempfile
        import os
        from core.manim_timing_validator import validate_manim_timing
        
        errors = []
        
        # We need a temp file with the code to run the validator
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as tmp:
            tmp.write(code)
            tmp_path = tmp.name
            
        try:
            # Capture print output from the validator if it fails
            from io import StringIO
            import sys
            
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            
            # Prepare external budgets for the validator
            budgets = {}
            narration_segments = section_data.get("narration_segments", [])
            for i, seg in enumerate(narration_segments, 1):
                # ISS-FIX: Support both 'duration' (LLM) and 'duration_seconds' (Pipeline) keys
                dur = seg.get("duration") or seg.get("duration_seconds") or 0.0
                budgets[i] = float(dur)
                
            success = validate_manim_timing(tmp_path, external_budgets=budgets)
            
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout
            
            if not success:
                # Extract [FAIL] lines from output
                fail_lines = [line for line in output.split("\n") if "[FAIL]" in line]
                if fail_lines:
                    errors.extend(fail_lines)
                else:
                    errors.append("Manim timing validation failed (segments mismatched or cleanup violated)")
            
        except Exception as e:
            logger.error(f"[MANIM GEN] Granular validation error: {e}")
            errors.append(f"Internal validation error: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
        return errors
    
    def _check_variable_overwrites(self, code: str) -> List[str]:
        """Check for problematic variable overwrites like 'axes = axes.plot()'."""
        errors = []
        
        overwrite_pattern = re.compile(r'^(\s*)(\w+)\s*=\s*\2\.', re.MULTILINE)
        
        for match in overwrite_pattern.finditer(code):
            var_name = match.group(2)
            if var_name not in ("self",):
                line_num = code[:match.start()].count("\n") + 1
                errors.append(
                    f"Line {line_num}: Variable '{var_name}' overwrites itself - "
                    f"use a different name like '{var_name}_new' or 'new_{var_name}'"
                )
        
        return errors

    def _enforce_timing(self, code: str, section_data: Dict[str, Any]) -> str:
        """
        Programmatically enforce strict timing synchronization.
        Parses # Segment X comments and injects self.wait() to match audio duration.
        """
        segments = section_data.get("narration_segments", [])
        if not segments:
            return code

        lines = code.split('\n')
        new_lines = []
        
        current_segment_idx = -1
        segment_lines = []
        
        # Helper to process a finished segment block
        def process_block(lines_in_block, seg_idx):
            if seg_idx < 0 or seg_idx >= len(segments):
                return lines_in_block
            
            block_content = "\n".join(lines_in_block)
            
            # Calculate current animation duration
            run_time_matches = re.findall(r'run_time\s*=\s*([\d\.]+)', block_content)
            run_time_sum = sum(float(x) for x in run_time_matches)
            
            wait_matches = re.findall(r'self\.wait\s*\(\s*([\d\.]+)', block_content)
            wait_sum = sum(float(x) for x in wait_matches)
            
            actual_duration = run_time_sum + wait_sum
            
            # Get target duration (handle both duration formats)
            seg = segments[seg_idx]
            target_duration = float(seg.get("duration", seg.get("duration_seconds", 0)))
            
            deficit = target_duration - actual_duration
            
            # Find indentation of the last line to match
            indent = "        " # Default
            last_logical_line = ""
            for line in reversed(lines_in_block):
                if line.strip():
                    # Check for truncation BEFORE appending sync comments
                    if not last_logical_line:
                        last_logical_line = line.split('#')[0].strip()
                        if last_logical_line.endswith(('=', ',', '(', '+', '-', '*')):
                            lines_in_block.append(f"{' ' * (len(line) - len(line.lstrip()))}# TRUNCATION DETECTED: Code ends mid-statement")
                    
                    leading_spaces = len(line) - len(line.lstrip())
                    indent = line[:leading_spaces]
                    break
            
            # Injection Logic
            # V2.6: Strict Transition Cleanup (FadeOut)
            # We always inject a FadeOut if not present, and then adjust the wait
            has_fadeout = "FadeOut(" in block_content and "run_time=" in block_content
            
            # Recalculate duration including injected FadeOut if needed
            fadeout_duration = 0.5
            if not has_fadeout:
                lines_in_block.append(f"{indent}# V2.6: Clear screen for clean transition")
                lines_in_block.append(f"{indent}self.play(FadeOut(*self.mobjects), run_time={fadeout_duration})")
                actual_duration += fadeout_duration
            
            deficit = target_duration - actual_duration
            
            # Injection Logic for Remaining Deficit
            if deficit > 0.05: # Use 0.05 as threshold to avoid tiny waits
                lines_in_block.append(f"{indent}# Hard Sync: Injected wait to match audio ({actual_duration:.2f}s -> {target_duration:.2f}s)")
                lines_in_block.append(f"{indent}self.wait({deficit:.3f})")
            elif deficit < -0.5:
                 lines_in_block.append(f"{indent}# Hard Sync WARNING: Animation exceeds audio by {abs(deficit):.2f}s")
            
            return lines_in_block

        # Parsing Loop
        for line in lines:
            # Check for segment start marker
            # We look for "# Segment X" (case insensitive)
            seg_match = re.search(r'#\s*Segment\s*(\d+)', line, re.IGNORECASE)
            
            if seg_match:
                # Process previous segment if exists
                if current_segment_idx >= 0:
                    processed = process_block(segment_lines, current_segment_idx)
                    new_lines.extend(processed)
                    segment_lines = []
                
                # Start new segment
                try:
                    current_segment_idx = int(seg_match.group(1)) - 1 # 1-based to 0-based
                except:
                    current_segment_idx = -1
                
                # Only trust it if valid range
                if current_segment_idx < 0: current_segment_idx = -1
            
            if current_segment_idx >= 0:
                segment_lines.append(line)
            else:
                new_lines.append(line) # Header/Imports before first segment
        
        # Process final segment
        if current_segment_idx >= 0 and segment_lines:
             processed = process_block(segment_lines, current_segment_idx)
             new_lines.extend(processed)
        
        return "\n".join(new_lines)


def build_manim_section_data(
    section: Dict[str, Any],
    narration_segments: List[Dict],
    visual_beats: List[Dict],
    segment_enrichments: List[Dict]
) -> Dict[str, Any]:
    """
    Build the input data structure for ManimCodeGenerator from V1.5 pipeline outputs.
    
    Args:
        section: Section plan from SectionPlanner
        narration_segments: Segments from NarrationWriter + TTS timing update
            Each segment has 'duration_seconds' (from TTS) - this is the authoritative timing
        visual_beats: Visual beats from VisualSpecArtist
        segment_enrichments: Enrichments from VisualSpecArtist
        
    Returns:
        Dict suitable for ManimCodeGenerator.generate()
        
    Note: This function maps 'duration_seconds' to 'duration' for the prompt template,
    as the ManimCodeGenerator expects 'duration' field in segments.
    """
    combined_segments = []
    
    def _ensure_str(val):
        """Convert value to string, handling lists."""
        if isinstance(val, list):
            return " ".join(str(v) for v in val)
        return str(val) if val else ""
    
    for i, seg in enumerate(narration_segments):
        visual_desc = ""
        
        if i < len(visual_beats):
            visual_desc = _ensure_str(visual_beats[i].get("description", ""))
        
        if i < len(segment_enrichments):
            enrich = segment_enrichments[i]
            visual_content = enrich.get("visual_content", {})
        
        seg_duration = seg.get("duration_seconds") or seg.get("duration") or 5.0
        
        combined_segments.append({
            "text": seg.get("text", ""),
            "duration": float(seg_duration),
            "visual": visual_desc
        })
    
    all_formulas = []
    all_labels = []
    for enrich in segment_enrichments:
        vc = enrich.get("visual_content", {})
        if vc.get("formula"):
            all_formulas.append(vc["formula"])
        if vc.get("labels"):
            all_labels.extend(vc["labels"])
    
    return {
        "section_title": section.get("title", "Educational Topic"),
        "narration_segments": combined_segments,
        "visual_description": " ".join(_ensure_str(vb.get("description", "")) for vb in visual_beats),
        "formulas": list(set(filter(None, all_formulas))),
        "key_terms": list(set(all_labels)),
        "special_requirements": ""
    }


def integrate_manim_code_into_section(
    section: Dict[str, Any],
    manim_code: str
) -> Dict[str, Any]:
    """
    Add generated Manim code to a section's render_spec.
    
    This function is called after ManimCodeGenerator.generate() to integrate
    the Python code into the section structure for later rendering.
    
    Args:
        section: The section dictionary (with existing render_spec if any)
        manim_code: The generated Python code for construct() method
        
    Returns:
        Updated section with manim_code added to render_spec
    """
    if not section.get("render_spec"):
        section["render_spec"] = {}
    
    render_spec = section["render_spec"]
    
    # V2.5 Compatibility: If manim_scene_spec is a string, convert to dict
    if not render_spec.get("manim_scene_spec"):
        render_spec["manim_scene_spec"] = {}
    elif isinstance(render_spec["manim_scene_spec"], str):
        # Save the original spec string as a description, convert container to dict
        original_spec = render_spec["manim_scene_spec"]
        render_spec["manim_scene_spec"] = {
            "description": original_spec
        }
    
    render_spec["manim_scene_spec"]["manim_code"] = manim_code
    render_spec["manim_scene_spec"]["code_type"] = "construct_body"
    
    # [V2.5 FIX] Removed destructive layer reset. 
    # We now trust the Director's "Teach -> Show" pattern.
    # The Director correctly sets text_layer="show" for Teach segments and "hide" for Show segments.
    # Overwriting this here caused the "Missing Text" bug.
    
    return section

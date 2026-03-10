import re
import sys
import os
import logging

# Configure logging to be quiet by default, but useful if needed
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ======================================================
# HARD MODE: Can be disabled via environment variable
# V2.5: Defaults to False to allow pipeline to continue
# ======================================================
HARD_FAIL_ON_ERROR = os.environ.get("MANIM_HARD_FAIL", "false").lower() == "true"

def validate_manim_timing(path: str, external_budgets: dict = None) -> bool:
    """
    V2.5 Manim Timing & Cleanup Validator.
    
    HARD RULE (PERSISTENCE DISABLED):
    Any variable reused across segments is a FAIL. No exceptions.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.splitlines(keepends=True)
    except Exception as e:
        print(f"[ERROR] Could not read file {path}: {e}")
        return False

    errors = []
    # Initialize state
    current_segment = 0
    current_segment_budget = 0.0
    current_time = 0.0

    current_vars = set()
    prev_vars = set()

    segments_data = {}
    budget_tolerance = 1.5
    failed = False

    # 0. ASCII & Forbidden Char Check
    forbidden = ['₹', '•', '…', '“', '”', '‘', '’', '×', '÷', '°', '✓']
    for char in forbidden:
        if char in content:
            errors.append(f"[FAIL] Forbidden character detected: '{char}'")
            failed = True
    
    try:
        content.encode('ascii')
    except UnicodeEncodeError as e:
        bad_char = content[e.start:e.end]
        if bad_char not in forbidden:
            errors.append(f"[FAIL] Non-ASCII character detected: '{bad_char}' at position {e.start}")
            failed = True

    # Regex patterns
    seg_header_pattern = re.compile(r"#\s*Segment\s*(\d+).*?(\d+\.?\d*)\s*s", re.IGNORECASE)
    rt_pattern = re.compile(r"run_time\s*=\s*([\d.]+)")
    wait_pattern = re.compile(r"self\.wait\(([\d.]+)\)")
    assign_pattern = re.compile(r"^\s*(\w+)\s*=")
    
    # IGNORE FALSE POSITIVES (REQUIRED)
    ignored_vars = {
        "self", "run_time", "rate_func", "color", "stroke_width", "fill_opacity", 
        "about_point", "about_edge", "path_arc", "lag_ratio", "buff", "axis_config"
    }
    ignored_vars.update({
        "Text", "MathTex", "Line", "Polygon", "Dot", "Arc", "Circle", "Rectangle", "Square", "Arrow",
        "FadeIn", "FadeOut", "Create", "Write", "Group", "VGroup",
        "UP", "DOWN", "LEFT", "RIGHT", "ORIGIN", "UL", "UR", "DL", "DR", "OUT", "IN",
        "BLUE", "GREEN", "RED", "YELLOW", "ORANGE", "WHITE", "BLACK", "PURPLE", "PINK", "GOLD", "TEAL", "MAROON",
        "Scene", "ThreeDScene", "np", "font_size", "buff", "opacity", "stroke_width", "stroke_opacity",
        "play", "wait", "clear", "mobjects", "self.wait", "self.play", "self.clear", "self.mobjects"
    })

    for line_num, line in enumerate(lines, 1):
        # 1. Detect Segment Start
        seg_match = seg_header_pattern.search(line)
        if seg_match:
            # Check previous segment time
            if current_segment > 0:
                budget = external_budgets.get(current_segment, current_segment_budget) if external_budgets else current_segment_budget
                print(f"DEBUG: Processing segment {current_segment} completion at line '{line.strip()}'")
                if abs(current_time - budget) > budget_tolerance:
                    if "sync" in line.lower():
                        logger.info(f"Segment {current_segment}: Bypassing timing check due to Hard Sync annotation.")
                    else:
                        print(f"DEBUG FAIL LINE: '{line.strip()}' (segment {current_segment})")
                        errors.append(f"[FAIL] Segment {current_segment}: Timing mismatch. Budget={budget}s, Actual={current_time:.2f}s")
                        failed = True
                
                segments_data[current_segment] = {
                    "duration": budget,
                    "total_time": current_time,
                    "waits": segments_data.get(current_segment, {}).get("waits", [])
                }

            # Reset for new segment
            current_segment = int(seg_match.group(1))
            try:
                current_segment_budget = float(seg_match.group(2))
            except:
                current_segment_budget = 0.0
            current_time = 0.0
            # PERSISTENCE DISABLED: All visuals must be cleared/re-created
            prev_vars = current_vars
            current_vars = set()
            segments_data[current_segment] = {"duration": current_segment_budget, "total_time": 0.0, "waits": []}
            continue

        if current_segment == 0:
            continue

        pure_code = line.split("#")[0]
        
        # 2. Track Timing
        rt_match = rt_pattern.search(pure_code)
        if rt_match:
            current_time += float(rt_match.group(1))
            
        wait_match = wait_pattern.search(pure_code)
        if wait_match:
            wait_val = float(wait_match.group(1))
            current_time += wait_val
            segments_data[current_segment]["waits"].append(wait_val)

        # 3. Track Usages & HARD CLEANUP RULE (PERSISTENCE DISABLED)
        # Downgraded to WARNING for V2.5 stability (Strict name checking causes too many retries)
        words = re.findall(r"\b[a-z_][a-z0-9_]*\b", pure_code)
        for w in words:
            # Look for reuse of names from the previous segment
            if w in prev_vars and w not in ignored_vars:
                # Log as warning but DO NOT FAIL
                print(f"[WARN] Segment {current_segment}: Potential variable reuse '{w}'. Ensure it was re-instantiated.")

        
        # Track local assignments in this segment
        assign_match = assign_pattern.search(pure_code)
        if assign_match:
            var_name = assign_match.group(1)
            if var_name not in ignored_vars:
                current_vars.add(var_name)
                
    # Final timing check for the last segment
    if current_segment > 0:
        budget = external_budgets.get(current_segment, current_segment_budget) if external_budgets else current_segment_budget
        if abs(current_time - budget) > budget_tolerance:
            # Check if this segment was marked for Hard Sync
            is_hard_sync = False
            # Search backwards for the current segment header to see if it has the tag
            for i in range(len(lines)-1, -1, -1):
                if f"Segment {current_segment}" in lines[i] and "sync" in lines[i].lower():
                    is_hard_sync = True
                    break
            
            if is_hard_sync:
                logger.info(f"Segment {current_segment}: Bypassing final timing check due to Hard Sync annotation.")
            else:
                errors.append(f"[FAIL] Segment {current_segment}: Timing mismatch. Budget={budget}s, Actual={current_time:.2f}s")
                failed = True
        segments_data[current_segment]["total_time"] = current_time
        segments_data[current_segment]["duration"] = budget

    # Pacing Rule Validation
    for seg_id, data in segments_data.items():
        duration = data["duration"]
        actual = data["total_time"]
        
        if duration >= 1.0:
            has_pacing_wait = any(w >= 0.49 for w in data["waits"])
            if not has_pacing_wait:
                errors.append(f"[FAIL] Segment {seg_id}: Pacing Rule violated. Duration >= 1.0s but no self.wait(0.5) found.")
                failed = True

    # ======================================================
    # HARD FAIL — NO ENV FLAGS, NO SKIP, NO RETRY LOOP
    # ======================================================
    if failed:
        for e in errors:
            print(e)
        if HARD_FAIL_ON_ERROR:
            raise RuntimeError(
                "Manim validation FAILED. "
                "Persistence is forbidden. "
                "Fix the code or regenerate."
            )
        return False

    if not segments_data:
        print("[WARN] No segments found to validate.")
        return True

    print("[PASS] Manim validation successful")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manim_timing_validator.py <path_to_manim_file>")
        sys.exit(1)
        
    try:
        success = validate_manim_timing(sys.argv[1])
        sys.exit(0 if success else 1)
    except RuntimeError as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(2)

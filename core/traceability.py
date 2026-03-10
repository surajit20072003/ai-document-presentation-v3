"""
Traceability Logging - Implements v1.1 traceability requirements.

Reference: docs/llm_output_requirements.json traceability

Requirements:
- generation_trace_required: true
- render_prompts_logged: true
- renderer_decisions_logged: true
- validation_results_logged: true
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class TraceabilityLogger:
    """Structured logging for generation pipeline traceability."""
    
    def __init__(self, job_id: str, output_dir: str):
        self.job_id = job_id
        self.output_dir = Path(output_dir)
        self.trace_file = self.output_dir / "generation_trace.json"
        self.start_time = time.time()
        
        self.trace = {
            "job_id": job_id,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "duration_seconds": None,
            "status": "in_progress",
            "generation_events": [],
            "render_prompts": [],
            "renderer_decisions": [],
            "validation_results": [],
            "errors": [],
            "warnings": []
        }
    
    def log_event(self, event_type: str, details: Dict[str, Any]):
        """Log a generation event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(time.time() - self.start_time, 2),
            "event_type": event_type,
            "details": details
        }
        self.trace["generation_events"].append(event)
        self._save()
    
    def log_llm_call(self, model: str, prompt_type: str, input_tokens: int, output_tokens: int, 
                     success: bool, error: Optional[str] = None):
        """Log an LLM API call."""
        self.log_event("llm_call", {
            "model": model,
            "prompt_type": prompt_type,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "success": success,
            "error": error
        })
    
    def log_render_prompt(self, section_id, beat_index: int, renderer: str, 
                          prompt: str, prompt_type: str = None):
        """Log a render prompt for traceability.
        
        Args:
            section_id: Section identifier (can be string like 'content_01' or int)
            beat_index: Beat index within the section
            renderer: Renderer type ('manim', 'video', 'wan')
            prompt: Full prompt/spec content
            prompt_type: Override prompt type, auto-detected if None
        """
        if prompt_type is None:
            if renderer == "manim":
                prompt_type = "manim_scene_spec"
            elif renderer == "video":
                prompt_type = "wan_video_prompt"
            else:
                prompt_type = f"{renderer}_prompt"
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "section_id": section_id,
            "beat_index": beat_index,
            "renderer": renderer,
            "prompt_type": prompt_type,
            "prompt_preview": prompt[:500] if len(prompt) > 500 else prompt,
            "prompt_length": len(prompt),
            "full_prompt": prompt
        }
        self.trace["render_prompts"].append(entry)
        self._save()
    
    def log_renderer_decision(self, section_id: int, section_type: str, 
                               chosen_renderer: str, reasoning: str):
        """Log a renderer decision with reasoning."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "section_id": section_id,
            "section_type": section_type,
            "chosen_renderer": chosen_renderer,
            "reasoning": reasoning
        }
        self.trace["renderer_decisions"].append(entry)
        self._save()
    
    def log_validation_result(self, validation_type: str, section_id: Optional[int],
                               passed: bool, errors: List[str], warnings: List[str]):
        """Log validation results."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "validation_type": validation_type,
            "section_id": section_id,
            "passed": passed,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors[:10],
            "warnings": warnings[:10]
        }
        self.trace["validation_results"].append(entry)
        self._save()
    
    def log_hard_fail(self, condition: str, section_id: int, details: str):
        """Log a hard fail condition."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "condition": condition,
            "section_id": section_id,
            "details": details
        }
        self.trace["errors"].append({
            "type": "hard_fail",
            "data": entry
        })
        self._save()
    
    def log_warning(self, warning_type: str, section_id: Optional[int], message: str):
        """Log a warning."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "warning_type": warning_type,
            "section_id": section_id,
            "message": message
        }
        self.trace["warnings"].append(entry)
        self._save()
    
    def log_error(self, error_type: str, message: str, details: Optional[Dict] = None):
        """Log an error."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "message": message,
            "details": details or {}
        }
        self.trace["errors"].append(entry)
        self._save()
    
    def complete(self, status: str = "completed"):
        """Mark the trace as complete."""
        self.trace["completed_at"] = datetime.now().isoformat()
        self.trace["duration_seconds"] = round(time.time() - self.start_time, 2)
        self.trace["status"] = status
        self._save()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the trace."""
        return {
            "job_id": self.job_id,
            "status": self.trace["status"],
            "duration_seconds": self.trace["duration_seconds"],
            "total_events": len(self.trace["generation_events"]),
            "render_prompts_logged": len(self.trace["render_prompts"]),
            "renderer_decisions_logged": len(self.trace["renderer_decisions"]),
            "validation_results_logged": len(self.trace["validation_results"]),
            "error_count": len(self.trace["errors"]),
            "warning_count": len(self.trace["warnings"])
        }
    
    def _save(self):
        """Save trace to file."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            with open(self.trace_file, 'w') as f:
                json.dump(self.trace, f, indent=2)
        except Exception as e:
            print(f"[TRACE] Failed to save trace: {e}")


_current_logger: Optional[TraceabilityLogger] = None


def init_traceability(job_id: str, output_dir: str) -> TraceabilityLogger:
    """Initialize traceability logging for a job."""
    global _current_logger
    _current_logger = TraceabilityLogger(job_id, output_dir)
    return _current_logger


def get_logger() -> Optional[TraceabilityLogger]:
    """Get the current traceability logger."""
    return _current_logger


def log_event(event_type: str, details: Dict[str, Any]):
    """Log an event to the current logger."""
    if _current_logger:
        _current_logger.log_event(event_type, details)


def log_render_prompt(section_id: int, beat_index: int, renderer: str, prompt: str):
    """Log a render prompt."""
    if _current_logger:
        _current_logger.log_render_prompt(section_id, beat_index, renderer, prompt)


def log_renderer_decision(section_id: int, section_type: str, renderer: str, reasoning: str):
    """Log a renderer decision."""
    if _current_logger:
        _current_logger.log_renderer_decision(section_id, section_type, renderer, reasoning)


def log_validation(validation_type: str, section_id: Optional[int], 
                   passed: bool, errors: List[str], warnings: List[str]):
    """Log validation results."""
    if _current_logger:
        _current_logger.log_validation_result(validation_type, section_id, passed, errors, warnings)


def log_hard_fail(condition: str, section_id: int, details: str):
    """Log a hard fail."""
    if _current_logger:
        _current_logger.log_hard_fail(condition, section_id, details)


def complete_trace(status: str = "completed"):
    """Complete the current trace."""
    if _current_logger:
        _current_logger.complete(status)


def save_render_prompts_json():
    """Save render prompts to a separate JSON file for easy auditing."""
    if _current_logger and _current_logger.trace["render_prompts"]:
        render_prompts_file = _current_logger.output_dir / "render_prompts.json"
        try:
            with open(render_prompts_file, 'w') as f:
                json.dump({
                    "job_id": _current_logger.job_id,
                    "generated_at": datetime.now().isoformat(),
                    "total_prompts": len(_current_logger.trace["render_prompts"]),
                    "prompts": _current_logger.trace["render_prompts"]
                }, f, indent=2)
            print(f"[TRACE] Saved {len(_current_logger.trace['render_prompts'])} render prompts to {render_prompts_file}")
        except Exception as e:
            print(f"[TRACE] Failed to save render_prompts.json: {e}")


def save_raw_llm_response(
    renderer_type: str,
    section_id: str,
    raw_response: str,
    model: str,
    usage: Dict[str, Any],
    parsed_result: Optional[Dict] = None
):
    """Save raw LLM response to job folder for debugging and validation.
    
    Creates: llm_responses/{renderer_type}_section_{id}_raw.json
    
    Args:
        renderer_type: 'manim', 'video', 'remotion', 'chunker', 'director'
        section_id: Section identifier
        raw_response: The raw text returned by LLM before parsing
        model: The model used
        usage: Token usage dict
        parsed_result: The parsed JSON result (optional, for comparison)
    """
    if not _current_logger:
        print(f"[TRACE] No logger initialized, skipping raw response save for {renderer_type}")
        return
    
    llm_responses_dir = _current_logger.output_dir / "llm_responses"
    llm_responses_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{renderer_type}_section_{section_id}_raw.json"
    filepath = llm_responses_dir / filename
    
    response_data = {
        "timestamp": datetime.now().isoformat(),
        "job_id": _current_logger.job_id,
        "renderer_type": renderer_type,
        "section_id": section_id,
        "model": model,
        "usage": usage,
        "raw_response_length": len(raw_response),
        "raw_response": raw_response,
    }
    
    if parsed_result:
        response_data["parsed_result"] = parsed_result
    
    try:
        with open(filepath, 'w') as f:
            json.dump(response_data, f, indent=2)
        print(f"[TRACE] Saved raw {renderer_type} response for section {section_id}: {filepath}")
    except Exception as e:
        print(f"[TRACE] Failed to save raw response: {e}")

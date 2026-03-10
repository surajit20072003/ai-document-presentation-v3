"""
Validator Orchestrator - Orchestrates 3-tier validation.

Validation flow:
1. Tier-1 Structural → Hard fail if errors
2. Tier-2 Semantic → Trigger semantic retry (max 1) if errors  
3. Tier-3 Quality → Log warnings, never block

Returns ValidationResult with status and appropriate data.
"""

import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .tier1_structural import (
    validate_structural, 
    StructuralError, 
    format_structural_errors
)
from .tier2_semantic import (
    validate_semantic, 
    SemanticError, 
    format_semantic_errors
)
from .tier3_quality import (
    validate_quality, 
    QualityWarning, 
    format_quality_warnings
)


def log(msg: str):
    print(msg)
    sys.stdout.flush()


@dataclass
class ValidationResult:
    """Result of 3-tier validation."""
    status: str  # "PASS", "STRUCTURAL_FAIL", "SEMANTIC_FAIL"
    structural_errors: List[StructuralError] = field(default_factory=list)
    semantic_errors: List[SemanticError] = field(default_factory=list)
    quality_warnings: List[QualityWarning] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        return self.status == "PASS"
    
    @property
    def needs_structural_retry(self) -> bool:
        return self.status == "STRUCTURAL_FAIL"
    
    @property
    def needs_semantic_retry(self) -> bool:
        return self.status == "SEMANTIC_FAIL"
    
    def get_retry_prompt(self) -> str:
        """Generate retry prompt based on validation failures."""
        lines = []
        
        if self.structural_errors:
            lines.append(format_structural_errors(self.structural_errors))
        
        if self.semantic_errors:
            lines.append(format_semantic_errors(self.semantic_errors))
        
        return "\n\n".join(lines)
    
    def get_summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Validation Status: {self.status}",
            f"  Structural Errors: {len(self.structural_errors)}",
            f"  Semantic Errors: {len(self.semantic_errors)}",
            f"  Quality Warnings: {len(self.quality_warnings)}"
        ]
        return "\n".join(lines)


def validate(presentation: dict) -> ValidationResult:
    """
    Run 3-tier validation on presentation.
    
    Order:
    1. Tier-1 Structural (hard fail) - stops if errors
    2. Tier-2 Semantic (retry once) - stops if errors
    3. Tier-3 Quality (warnings only) - always runs
    
    Returns ValidationResult with status and all findings.
    """
    log("[Validator] Running Tier-1 Structural validation...")
    structural_errors = validate_structural(presentation)
    
    if structural_errors:
        log(f"[Validator] STRUCTURAL_FAIL: {len(structural_errors)} errors")
        for err in structural_errors[:5]:
            log(f"  - {err}")
        if len(structural_errors) > 5:
            log(f"  ... and {len(structural_errors) - 5} more")
        
        return ValidationResult(
            status="STRUCTURAL_FAIL",
            structural_errors=structural_errors
        )
    
    log("[Validator] Tier-1 PASSED. Running Tier-2 Semantic validation...")
    semantic_errors = validate_semantic(presentation)
    
    if semantic_errors:
        log(f"[Validator] SEMANTIC_FAIL: {len(semantic_errors)} errors")
        for err in semantic_errors[:5]:
            log(f"  - {err}")
        
        return ValidationResult(
            status="SEMANTIC_FAIL",
            semantic_errors=semantic_errors
        )
    
    log("[Validator] Tier-2 PASSED. Running Tier-3 Quality lint...")
    quality_warnings = validate_quality(presentation)
    
    if quality_warnings:
        log(f"[Validator] Quality warnings: {len(quality_warnings)}")
        for warn in quality_warnings[:3]:
            log(f"  - {warn}")
        if len(quality_warnings) > 3:
            log(f"  ... and {len(quality_warnings) - 3} more")
    else:
        log("[Validator] No quality warnings")
    
    log("[Validator] Validation PASSED")
    
    return ValidationResult(
        status="PASS",
        quality_warnings=quality_warnings
    )


def validate_for_retry(presentation: dict, max_structural_retries: int = 2, max_semantic_retries: int = 1) -> Dict[str, Any]:
    """
    Validate and return retry guidance.
    
    Returns dict with:
    - valid: bool
    - retry_type: "structural" | "semantic" | None
    - retry_prompt: str (errors formatted for LLM)
    - warnings: list of quality warnings
    """
    result = validate(presentation)
    
    return {
        "valid": result.is_valid,
        "retry_type": "structural" if result.needs_structural_retry else ("semantic" if result.needs_semantic_retry else None),
        "retry_prompt": result.get_retry_prompt(),
        "warnings": [str(w) for w in result.quality_warnings],
        "structural_error_count": len(result.structural_errors),
        "semantic_error_count": len(result.semantic_errors),
        "quality_warning_count": len(result.quality_warnings)
    }

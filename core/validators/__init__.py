"""
3-Tier Validator Package

Tier 1 - Structural (Hard Fail): Missing sections, layer logic, renderer contracts
Tier 2 - Semantic (Retry Once): Word counts, formula visualization  
Tier 3 - Quality (Warnings): Vague language, style issues
"""

from .validator_orchestrator import (
    validate,
    validate_for_retry,
    ValidationResult
)
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

__all__ = [
    "validate",
    "validate_for_retry",
    "ValidationResult",
    "validate_structural",
    "StructuralError",
    "format_structural_errors",
    "validate_semantic",
    "SemanticError", 
    "format_semantic_errors",
    "validate_quality",
    "QualityWarning",
    "format_quality_warnings"
]

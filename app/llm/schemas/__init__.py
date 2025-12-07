"""LLM response schemas."""

from app.llm.schemas.analysis import NorwoodAnalysisResult
from app.llm.schemas.certification import CertificationDiagnosis, PhotoValidationResult
from app.llm.schemas.cock import CockAnalysisResult

__all__ = [
    "NorwoodAnalysisResult",
    "PhotoValidationResult",
    "CertificationDiagnosis",
    "CockAnalysisResult",
]

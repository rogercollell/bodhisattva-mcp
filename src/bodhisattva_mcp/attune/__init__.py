"""Vendored Attune core from loving-deer.

Keep files in this package byte-identical to upstream. Email-specific
extensions live outside this package (see ``email_prompt.py``).
"""

from bodhisattva_mcp.attune.karma_filter import carries_karma, needs_wisdom_frame
from bodhisattva_mcp.attune.models import (
    Domain,
    EvaluationStatus,
    Modification,
    SensitivityLevel,
    WisdomFrame,
)
from bodhisattva_mcp.attune.wisdom_frame import build_wisdom_frame

__all__ = [
    "Domain",
    "EvaluationStatus",
    "Modification",
    "SensitivityLevel",
    "WisdomFrame",
    "build_wisdom_frame",
    "carries_karma",
    "needs_wisdom_frame",
]

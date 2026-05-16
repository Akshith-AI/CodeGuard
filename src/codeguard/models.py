"""Shared result models for security findings."""

from dataclasses import dataclass
from typing import Literal

Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]


@dataclass(frozen=True)
class Finding:
    vulnerability_type: str
    severity: Severity
    file_path: str
    affected_line: int
    description: str
    suggested_fix: str

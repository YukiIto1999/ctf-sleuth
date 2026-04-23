from __future__ import annotations

from enum import StrEnum


class Severity(StrEnum):
    """所見の深刻度区分"""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

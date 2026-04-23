from __future__ import annotations

from dataclasses import dataclass

from .evidence import Evidence
from .severity import Severity


@dataclass(frozen=True, slots=True)
class Finding:
    """単一の有用事実

    Attributes:
        summary: 所見の要約
        severity: 深刻度
        evidence: 所見を支える Evidence 群
        recommendation: 推奨アクション
    """

    summary: str
    severity: Severity
    evidence: tuple[Evidence, ...] = ()
    recommendation: str = ""

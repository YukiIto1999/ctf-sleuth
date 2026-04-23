from __future__ import annotations

from dataclasses import dataclass

from .evidence import Evidence
from .finding import Finding


@dataclass(frozen=True, slots=True)
class FindingsCollected:
    """所見収集結果を表す TaskResult variant

    Attributes:
        findings: 得られた所見
        evidence: 所見に紐付かない付随 Evidence
    """

    findings: tuple[Finding, ...]
    evidence: tuple[Evidence, ...] = ()

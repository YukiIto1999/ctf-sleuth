from __future__ import annotations

from dataclasses import dataclass, field

from .evidence import Evidence


@dataclass(frozen=True, slots=True)
class AnalysisReport:
    """解析レポートを表す TaskResult variant

    Attributes:
        summary: 解析の要約
        sections: セクション名と本文のタプル列
        evidence: 裏付け Evidence
    """

    summary: str
    sections: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)

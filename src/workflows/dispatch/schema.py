from __future__ import annotations

from dataclasses import dataclass

AUTO_RUN_CONFIDENCE = 0.8
MIN_CONFIDENCE = 0.5


@dataclass(frozen=True, slots=True)
class DispatchConfig:
    """dispatch の閾値と対話可否設定

    Attributes:
        auto_run_confidence: 自動実行可能な下限信頼度
        min_confidence: 実行許容可能な下限信頼度
        ambiguity_margin: 曖昧判定の閾値
        interactive: 対話確認の可否
    """

    auto_run_confidence: float = AUTO_RUN_CONFIDENCE
    min_confidence: float = MIN_CONFIDENCE
    ambiguity_margin: float = 0.3
    interactive: bool = True

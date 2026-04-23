from __future__ import annotations

from dataclasses import dataclass

from shared.probe import InputProbe
from shared.task import Classification

from ..services import Classifier
from .heuristic import classify_heuristic


@dataclass(frozen=True, slots=True)
class HybridConfig:
    """Hybrid 分類器の設定

    Attributes:
        escalate_below: LLM 委譲判定の信頼度下限
        escalate_if_ambiguous: 次点との差が小さい場合の LLM 委譲フラグ
        llm_timeout_seconds: LLM 呼出タイムアウト秒数
    """

    escalate_below: float = 0.75
    escalate_if_ambiguous: bool = True
    llm_timeout_seconds: float = 20.0


class HybridClassifier:
    """規則ベース + LLM 委譲の合成分類器"""

    def __init__(self, llm: Classifier, *, config: HybridConfig | None = None) -> None:
        """Hybrid 分類器の初期化

        Args:
            llm: 委譲先の LLM 分類器
            config: 委譲判定の設定
        """
        self._llm = llm
        self._config = config or HybridConfig()

    async def classify(self, probe: InputProbe) -> Classification:
        """ヒューリスティックと LLM の合成分類

        Args:
            probe: 入力観測結果

        Returns:
            heuristic もしくは LLM 由来の Classification
        """
        heuristic = classify_heuristic(probe)
        if not self._should_escalate(heuristic):
            return heuristic
        try:
            return await self._llm.classify(probe)
        except Exception as e:  # noqa: BLE001
            return Classification(
                task_type=heuristic.task_type,
                confidence=heuristic.confidence,
                required_params=heuristic.required_params,
                alternatives=heuristic.alternatives,
                reasoning=(
                    f"{heuristic.reasoning} [llm escalation failed: "
                    f"{type(e).__name__}: {e}]"
                ),
            )

    def _should_escalate(self, h: Classification) -> bool:
        """LLM 委譲の要否判定

        Args:
            h: ヒューリスティック分類結果

        Returns:
            LLM 委譲が必要な場合 True
        """
        if h.confidence < self._config.escalate_below:
            return True
        return bool(self._config.escalate_if_ambiguous and h.is_ambiguous())

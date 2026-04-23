from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .session import SessionMetrics


@dataclass
class MetricsAccumulator:
    """session 中の可変メトリクス集計器

    Attributes:
        started_at: 集計開始時刻
        cost_usd: 累積コスト (USD)
        turns: 累積ターン数
        input_tokens: 累積入力トークン数
        output_tokens: 累積出力トークン数
        cache_read_tokens: 累積キャッシュ読込トークン数
        cache_creation_tokens: 累積キャッシュ生成トークン数
    """

    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    cost_usd: float = 0.0
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    def record_result_message(self, message: Any) -> None:
        """ResultMessage からの cost と usage 取込

        Args:
            message: SDK の ResultMessage 相当オブジェクト
        """
        cost = getattr(message, "total_cost_usd", None)
        if cost:
            try:
                self.cost_usd += float(cost)
            except (TypeError, ValueError):
                pass
        self.turns += 1
        usage = getattr(message, "usage", None) or {}
        if not isinstance(usage, dict):
            usage = getattr(usage, "__dict__", {}) or {}
        self.input_tokens += _int(usage.get("input_tokens"))
        self.output_tokens += _int(usage.get("output_tokens"))
        self.cache_read_tokens += _int(
            usage.get("cache_read_input_tokens") or usage.get("cache_read_tokens")
        )
        self.cache_creation_tokens += _int(
            usage.get("cache_creation_input_tokens") or usage.get("cache_creation_tokens")
        )

    def finalize(self) -> SessionMetrics:
        """現集計値の不変スナップショット取得

        Returns:
            集計完了時刻付き SessionMetrics
        """
        return SessionMetrics(
            cost_usd=self.cost_usd,
            turns=self.turns,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cache_read_tokens=self.cache_read_tokens,
            cache_creation_tokens=self.cache_creation_tokens,
            started_at=self.started_at,
            completed_at=datetime.now(UTC),
        )


def _int(v: Any) -> int:
    """値の安全な整数化

    Args:
        v: 整数化対象の値

    Returns:
        int 化結果もしくは 0
    """
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0

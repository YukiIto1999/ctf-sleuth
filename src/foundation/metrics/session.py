from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class SessionMetrics:
    """1 run 全体の計測値の不変表現

    Attributes:
        cost_usd: 合計コスト (USD)
        turns: 完了ターン数
        input_tokens: 入力トークン数
        output_tokens: 出力トークン数
        cache_read_tokens: キャッシュ読込トークン数
        cache_creation_tokens: キャッシュ生成トークン数
        started_at: 集計開始時刻
        completed_at: 集計終了時刻
    """

    cost_usd: float
    turns: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    started_at: datetime
    completed_at: datetime

    @property
    def duration_seconds(self) -> float:
        """started_at から completed_at までの秒数"""
        return (self.completed_at - self.started_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """JSON 互換辞書への変換

        Returns:
            丸め済の数値を持つ dict
        """
        return {
            "cost_usd": round(self.cost_usd, 6),
            "turns": self.turns,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "duration_seconds": round(self.duration_seconds, 3),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
        }

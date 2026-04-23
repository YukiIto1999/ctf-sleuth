from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .flag import Flag


@dataclass(frozen=True, slots=True)
class FlagSubmitted:
    """フラグ提出結果を表す TaskResult variant

    Attributes:
        flag: 提出フラグ
        accepted: 受理判定
        verdict_at: 判定時刻
        attempts: 提出回数
        note: 補足メモ
    """

    flag: Flag
    accepted: bool
    verdict_at: datetime
    attempts: int = 1
    note: str = ""

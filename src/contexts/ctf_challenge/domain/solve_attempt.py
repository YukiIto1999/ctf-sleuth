from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class FlagVerdict(StrEnum):
    """flag 提出の検証結果区分"""

    CORRECT = "correct"
    ALREADY_SOLVED = "already_solved"
    INCORRECT = "incorrect"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SolveAttempt:
    """flag 提出 1 試行の不変記録

    Attributes:
        challenge_name: 対象 challenge 名
        flag: 提出したフラグ文字列
        verdict: 判定結果
        message: サーバメッセージ
        submitted_at: 提出時刻
    """

    challenge_name: str
    flag: str
    verdict: FlagVerdict
    message: str
    submitted_at: datetime

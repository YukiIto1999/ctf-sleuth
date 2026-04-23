from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Difficulty(StrEnum):
    """HTB の公式難易度区分"""

    VERY_EASY = "very_easy"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    INSANE = "insane"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Machine:
    """HTB machine の不変表現

    Attributes:
        id: HTB 内部の machine ID
        name: machine 名
        ip: 対象の IP
        os: OS 識別子
        difficulty: HTB 公式難易度
    """

    id: int
    name: str
    ip: str
    os: str
    difficulty: Difficulty = Difficulty.UNKNOWN

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Flag:
    """提出対象のフラグ文字列

    Attributes:
        value: フラグ本体
    """

    value: str

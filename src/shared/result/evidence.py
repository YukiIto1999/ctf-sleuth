from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Evidence:
    """観察データの不変単位

    Attributes:
        source: 取得元識別子
        captured_at: 取得時刻
        content: 生データ本体
        note: 補足メモ
    """

    source: str
    captured_at: datetime
    content: str
    note: str = ""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .own_type import OwnType


@dataclass(frozen=True, slots=True)
class HtbAttempt:
    """HTB flag 提出 1 試行の不変記録

    Attributes:
        machine_name: 対象 machine 名
        own_type: own 種別
        flag: 提出フラグ文字列
        accepted: 受理判定
        message: HTB 応答メッセージ
        submitted_at: 提出時刻
    """

    machine_name: str
    own_type: OwnType
    flag: str
    accepted: bool
    message: str
    submitted_at: datetime

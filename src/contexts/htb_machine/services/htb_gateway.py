from __future__ import annotations

from typing import Protocol

from ..domain import HtbAttempt, OwnType


class HtbGateway(Protocol):
    """HTB API 境界の Protocol"""

    async def submit_flag(
        self,
        *,
        machine_id: int,
        machine_name: str,
        own_type: OwnType,
        flag: str,
        difficulty: int = 5,
    ) -> HtbAttempt:
        """flag 提出と HtbAttempt 生成

        Args:
            machine_id: HTB machine ID
            machine_name: machine 名
            own_type: own 種別
            flag: 提出フラグ文字列
            difficulty: 提出時の難易度値

        Returns:
            判定結果を含む HtbAttempt
        """
        ...

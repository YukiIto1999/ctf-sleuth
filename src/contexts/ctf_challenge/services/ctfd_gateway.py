from __future__ import annotations

from typing import Protocol

from ..domain import ChallengeSet, SolveAttempt


class CtfdGateway(Protocol):
    """CTFd REST API 境界の Protocol"""

    async def fetch_all(self) -> ChallengeSet:
        """全 challenge と solved 名集合の取得

        Returns:
            ChallengeSet
        """
        ...

    async def submit_flag(self, challenge_name: str, flag: str) -> SolveAttempt:
        """flag 提出と SolveAttempt 生成

        Args:
            challenge_name: 対象 challenge 名
            flag: 提出するフラグ文字列

        Returns:
            判定結果を含む SolveAttempt
        """
        ...

    async def download_distfile(self, url: str) -> bytes:
        """配布ファイルの取得

        Args:
            url: 相対もしくは絶対の URL

        Returns:
            取得した生バイト列
        """
        ...

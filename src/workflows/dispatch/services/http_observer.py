from __future__ import annotations

from typing import Protocol

from shared.probe import HttpProbe


class HttpObserver(Protocol):
    """HTTP 観測の Protocol"""

    async def observe(self, url: str) -> HttpProbe:
        """指定 URL に対する HTTP 観測

        Args:
            url: 観測対象の URL

        Returns:
            観測結果の HttpProbe
        """
        ...

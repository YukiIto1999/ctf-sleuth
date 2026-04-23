from __future__ import annotations

from typing import Protocol, runtime_checkable

from shared.probe import InputProbe
from shared.task import Classification


@runtime_checkable
class Classifier(Protocol):
    """InputProbe から Classification を返す契約"""

    async def classify(self, probe: InputProbe) -> Classification:
        """入力観測に対する分類

        Args:
            probe: 入力観測結果

        Returns:
            分類結果の Classification
        """
        ...

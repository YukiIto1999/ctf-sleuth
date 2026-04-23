from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class ErrorMetadata:
    """エラー分類の付帯情報

    Attributes:
        retryable: Resilience の再試行判定
        severity: ログ出力時の深刻度区分
    """

    retryable: bool
    severity: Literal["error", "warning"]

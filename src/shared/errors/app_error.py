from __future__ import annotations

from typing import ClassVar

from .metadata import ErrorMetadata


class AppError(Exception):
    """フレームワーク固有例外の基底

    Attributes:
        metadata: 再試行可否と severity を示す分類メタデータ
    """

    metadata: ClassVar[ErrorMetadata] = ErrorMetadata(retryable=False, severity="error")

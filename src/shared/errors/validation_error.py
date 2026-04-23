from __future__ import annotations

from typing import ClassVar

from .app_error import AppError
from .metadata import ErrorMetadata


class ValidationError(AppError):
    """入力検証失敗の基底"""

    metadata: ClassVar[ErrorMetadata] = ErrorMetadata(retryable=False, severity="warning")


class MissingRequiredParamError(ValidationError):
    """必須パラメータの欠落

    Attributes:
        missing: 不足しているパラメータ名のタプル
    """

    metadata: ClassVar[ErrorMetadata] = ErrorMetadata(retryable=False, severity="warning")

    def __init__(self, missing: tuple[str, ...]) -> None:
        """例外の初期化

        Args:
            missing: 不足しているパラメータ名のタプル
        """
        super().__init__(f"missing required params: {', '.join(missing)}")
        self.missing = missing

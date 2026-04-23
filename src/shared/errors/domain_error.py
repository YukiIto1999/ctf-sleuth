from __future__ import annotations

from typing import ClassVar

from .app_error import AppError
from .metadata import ErrorMetadata


class DomainError(AppError):
    """業務ルール違反の基底"""

    metadata: ClassVar[ErrorMetadata] = ErrorMetadata(retryable=False, severity="error")


class ClassificationUnderconfidentError(DomainError):
    """分類信頼度が下限閾値未満"""

    metadata: ClassVar[ErrorMetadata] = ErrorMetadata(retryable=False, severity="warning")


class AmbiguousClassificationError(DomainError):
    """候補間の信頼度差が小さく自動判定不能"""

    metadata: ClassVar[ErrorMetadata] = ErrorMetadata(retryable=False, severity="warning")

from __future__ import annotations

from typing import ClassVar

from .app_error import AppError
from .metadata import ErrorMetadata


class InfrastructureError(AppError):
    """内部基盤障害の基底"""

    metadata: ClassVar[ErrorMetadata] = ErrorMetadata(retryable=True, severity="error")


class NonInteractiveShellError(InfrastructureError):
    """非 TTY で対話確認が必要な状況"""

    metadata: ClassVar[ErrorMetadata] = ErrorMetadata(retryable=False, severity="error")

from __future__ import annotations

from typing import ClassVar

from .app_error import AppError
from .metadata import ErrorMetadata


class IntegrationError(AppError):
    """外部 API または外部システム障害の基底"""

    metadata: ClassVar[ErrorMetadata] = ErrorMetadata(retryable=True, severity="error")

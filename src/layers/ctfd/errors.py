from __future__ import annotations

from typing import ClassVar

from shared.errors import ErrorMetadata, IntegrationError


class CtfdError(IntegrationError):
    """CTFd 境界で発生する例外"""

    metadata: ClassVar[ErrorMetadata] = ErrorMetadata(retryable=True, severity="error")

from __future__ import annotations

from typing import ClassVar

from shared.errors import ErrorMetadata, IntegrationError


class HtbError(IntegrationError):
    """HTB API 境界で発生する例外"""

    metadata: ClassVar[ErrorMetadata] = ErrorMetadata(retryable=True, severity="error")

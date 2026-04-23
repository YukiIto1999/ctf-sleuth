from __future__ import annotations

from typing import ClassVar

from shared.errors import ErrorMetadata, InfrastructureError


class SandboxError(InfrastructureError):
    """Sandbox 境界で発生する例外の基底"""

    metadata: ClassVar[ErrorMetadata] = ErrorMetadata(retryable=True, severity="error")


class SandboxNotStartedError(SandboxError):
    """未起動 sandbox への操作"""

    metadata: ClassVar[ErrorMetadata] = ErrorMetadata(retryable=False, severity="error")


class SandboxStartupError(SandboxError):
    """container 起動失敗"""

    metadata: ClassVar[ErrorMetadata] = ErrorMetadata(retryable=True, severity="error")

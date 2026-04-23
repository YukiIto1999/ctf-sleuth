from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..domain import Artifact


class ArtifactInspector(Protocol):
    """Artifact 観測器の Protocol"""

    def __call__(self, path: Path) -> Artifact:
        """ファイル観測による Artifact の生成

        Args:
            path: 解析対象ファイルパス

        Returns:
            sha256 と FileKind を持つ Artifact
        """
        ...

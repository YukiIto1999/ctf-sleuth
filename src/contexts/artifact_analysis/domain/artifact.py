from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shared.probe import FileKind


@dataclass(frozen=True, slots=True)
class Artifact:
    """解析対象ファイルの不変表現

    Attributes:
        path: host 上の絶対パス
        kind: 推定される FileKind
        size_bytes: ファイルサイズ
        sha256: 全内容の sha256 hex digest
    """

    path: Path
    kind: FileKind
    size_bytes: int
    sha256: str

    def filename(self) -> str:
        """ファイル名の取得

        Returns:
            path 末尾のファイル名
        """
        return self.path.name

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MountSpec:
    """host から container へのマウント仕様

    Attributes:
        source: host 側パス
        target: container 側パス
        read_only: 読取専用フラグ
    """

    source: Path
    target: str
    read_only: bool = True

    def as_bind(self) -> str:
        """docker bind 形式文字列の生成

        Returns:
            source:target:mode 形式の bind 表記
        """
        mode = "ro" if self.read_only else "rw"
        return f"{self.source}:{self.target}:{mode}"

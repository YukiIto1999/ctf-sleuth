from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ArchiveResult:
    """archive slice の結果

    Attributes:
        challenge_dirs: 作成もしくは更新された challenge ディレクトリのタプル
    """

    challenge_dirs: tuple[Path, ...]

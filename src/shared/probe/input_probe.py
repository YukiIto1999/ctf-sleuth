from __future__ import annotations

from dataclasses import dataclass

from .file_kind import FileKind
from .http_probe import HttpProbe
from .input_shape import InputShape


@dataclass(frozen=True, slots=True)
class InputProbe:
    """入力観測の総合結果

    Attributes:
        shape: 純粋判定部分
        is_existing_path: ローカルパス実在の真偽
        file_kind: ファイル種別
        http: HTTP 観測結果
    """

    shape: InputShape
    is_existing_path: bool
    file_kind: FileKind | None
    http: HttpProbe | None

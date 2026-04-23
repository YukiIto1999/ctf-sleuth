from __future__ import annotations

from dataclasses import dataclass

from .target_kind import TargetKind


@dataclass(frozen=True, slots=True)
class Target:
    """調査対象の不変表現

    Attributes:
        raw: 元の入力文字列
        kind: 推定された TargetKind
    """

    raw: str
    kind: TargetKind

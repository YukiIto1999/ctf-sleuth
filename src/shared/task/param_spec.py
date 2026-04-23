from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParamSpec:
    """タスク種別が要求するパラメータの仕様

    Attributes:
        name: パラメータ名
        required: 必須フラグ
        description: パラメータの意味
    """

    name: str
    required: bool
    description: str

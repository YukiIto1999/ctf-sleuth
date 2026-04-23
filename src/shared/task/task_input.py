from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .task_type import TaskType


def _frozen_mapping(d: Mapping[str, str] | None) -> Mapping[str, str]:
    """Mapping の不変化

    Args:
        d: 変換元の Mapping もしくは None

    Returns:
        不変 Mapping
    """
    return MappingProxyType(dict(d or {}))


@dataclass(frozen=True, slots=True)
class TaskInput:
    """ユーザ入力の不変表現

    Attributes:
        raw: 入力文字列
        flags: 明示指定フラグの不変 Mapping
    """

    raw: str
    flags: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        """flags の不変 Mapping 正規化"""
        object.__setattr__(self, "flags", _frozen_mapping(self.flags))

    def explicit_type(self) -> TaskType | None:
        """明示指定された TaskType の取得

        Returns:
            `--type` フラグに対応する TaskType もしくは None
        """
        t = self.flags.get("type")
        if t is None:
            return None
        return TaskType(t)

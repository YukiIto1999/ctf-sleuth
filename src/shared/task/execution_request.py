from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .task_input import TaskInput
from .task_type import TaskType


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    """分類済タスクの実行要求

    Attributes:
        task_type: タスク種別
        input: 元の TaskInput
        params: 必須パラメータの不変 Mapping
        model_spec: Claude モデル識別子
        reasoning: 分類根拠
    """

    task_type: TaskType
    input: TaskInput
    params: Mapping[str, object]
    model_spec: str
    reasoning: str = ""

    def __post_init__(self) -> None:
        """params の不変 Mapping 正規化"""
        object.__setattr__(self, "params", MappingProxyType(dict(self.params)))

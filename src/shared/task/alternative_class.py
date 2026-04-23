from __future__ import annotations

from dataclasses import dataclass

from .task_type import TaskType


@dataclass(frozen=True, slots=True)
class AlternativeClass:
    """次点候補の分類

    Attributes:
        task_type: 候補の TaskType
        confidence: 候補の信頼度
    """

    task_type: TaskType
    confidence: float

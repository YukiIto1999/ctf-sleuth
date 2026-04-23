from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from .alternative_class import AlternativeClass
from .param_spec import ParamSpec
from .task_type import TaskType

_FLOAT_TOL = 1e-9


@dataclass(frozen=True, slots=True)
class Classification:
    """分類結果の不変値

    Attributes:
        task_type: 採用された TaskType
        confidence: 0.0 から 1.0 の信頼度
        required_params: 実行時に要求されるパラメータ仕様
        alternatives: 信頼度降順の次点候補
        reasoning: 判定理由の文字列
    """

    task_type: TaskType
    confidence: float
    required_params: tuple[ParamSpec, ...]
    alternatives: tuple[AlternativeClass, ...] = ()
    reasoning: str = ""

    def missing_params(self, supplied: Mapping[str, object]) -> tuple[ParamSpec, ...]:
        """欠けている必須パラメータの抽出

        Args:
            supplied: 実行時に供給されたパラメータ

        Returns:
            supplied に存在しない必須 ParamSpec のタプル
        """
        return tuple(p for p in self.required_params if p.required and p.name not in supplied)

    def is_ambiguous(self, margin: float = 0.3) -> bool:
        """次点との信頼度差に基づく曖昧判定

        Args:
            margin: 曖昧と判断する閾値

        Returns:
            次点との差が margin 以下なら True
        """
        if not self.alternatives:
            return False
        top = self.confidence
        second = max(a.confidence for a in self.alternatives)
        gap = top - second
        return gap < margin or math.isclose(gap, margin, abs_tol=_FLOAT_TOL)

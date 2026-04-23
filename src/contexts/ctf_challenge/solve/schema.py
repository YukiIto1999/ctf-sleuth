from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shared.result import Flag

from ..domain import SolveAttempt


@dataclass(frozen=True, slots=True)
class SolverOutput:
    """Solver 1 session の成果

    Attributes:
        flag: 確定したフラグ
        attempts: 提出試行のタプル
        confirmed: CORRECT もしくは ALREADY_SOLVED の到達判定
        reasoning: 推論ログ抜粋
        step_count: 実行ステップ数
    """

    flag: Flag | None
    attempts: tuple[SolveAttempt, ...] = ()
    confirmed: bool = False
    reasoning: str = ""
    step_count: int = 0


SOLVER_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": ["flag_found"]},
        "flag": {"type": "string"},
        "method": {"type": "string"},
    },
    "required": ["type", "flag", "method"],
    "additionalProperties": False,
}

from __future__ import annotations

from dataclasses import dataclass

from ..domain import HtbAttempt


@dataclass(frozen=True, slots=True)
class AttackerOutput:
    """Attacker 1 session の成果

    Attributes:
        user_flag: 取得した user flag
        root_flag: 取得した root flag
        attempts: 提出試行のタプル
        summary: 実行まとめ文字列
        chain: 実行ステップ列のタプル
    """

    user_flag: str | None
    root_flag: str | None
    attempts: tuple[HtbAttempt, ...]
    summary: str
    chain: tuple[str, ...]


HTB_OUTPUT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "user_flag": {"type": ["string", "null"]},
        "root_flag": {"type": ["string", "null"]},
        "summary": {"type": "string"},
        "chain": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["summary", "chain"],
    "additionalProperties": False,
}

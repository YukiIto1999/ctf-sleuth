from __future__ import annotations

import logging
import re
import shlex
from dataclasses import dataclass, field
from typing import Any, Protocol

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKClient,
    HookMatcher,
    ResultMessage,
    TextBlock,
)

from foundation.metrics import record_result_message
from layers.claude_sdk import (
    allow_replace_command,
    build_options,
    compose_bash_rewriters,
    make_pre_tool_hook,
    sandbox_bash_rewrite,
)
from shared.result import Flag
from shared.sandbox import ExecResult, Sandbox

from ..domain import Challenge, FlagVerdict, SolveAttempt
from ..services import FlagSubmitter
from .prompts import build_system_prompt
from .schema import SOLVER_OUTPUT_SCHEMA, SolverOutput

logger = logging.getLogger(__name__)

_SUBMIT_FLAG_RE = re.compile(r"^submit_flag\s+['\"]?(.+?)['\"]?\s*$")


class _SdkClientFactory(Protocol):
    """ClaudeSDKClient 互換のファクトリ Protocol"""

    def __call__(self, *, options: Any) -> Any:
        """SDK クライアントの生成

        Args:
            options: ClaudeAgentOptions 相当

        Returns:
            SDK クライアント
        """
        ...


@dataclass
class Solver:
    """1 challenge 1 session の Solver

    Attributes:
        challenge: 対象 Challenge
        sandbox: 実行 sandbox
        flag_submitter: submit_flag 実行時の非同期 callback
        model_spec: Claude モデル識別子
        distfile_names: 同梱 distfile 名のタプル
        container_arch: container の arch 文字列
        allowed_tools: 許可ツール名のタプル
        client_factory: SDK クライアントのファクトリ
    """

    challenge: Challenge
    sandbox: Sandbox
    flag_submitter: FlagSubmitter
    model_spec: str = "claude-opus-4-6"
    distfile_names: tuple[str, ...] = ()
    container_arch: str = "unknown"
    allowed_tools: tuple[str, ...] = ("Bash", "WebFetch", "WebSearch")
    client_factory: _SdkClientFactory = field(default=ClaudeSDKClient)

    _step_count: int = field(default=0, init=False)
    _attempts: list[SolveAttempt] = field(default_factory=list, init=False)
    _confirmed: bool = field(default=False, init=False)
    _flag_value: str | None = field(default=None, init=False)

    async def solve(self) -> SolverOutput:
        """1 session の実行

        Returns:
            session 結果を含む SolverOutput
        """
        system_prompt = build_system_prompt(
            challenge=self.challenge,
            distfile_names=self.distfile_names,
            container_arch=self.container_arch,
        )
        bash_rewrite = compose_bash_rewriters(
            self._submit_flag_rewriter,
            sandbox_bash_rewrite(self.sandbox),
        )
        hook = make_pre_tool_hook(
            allowed_tools=self.allowed_tools,
            bash_rewrite=bash_rewrite,
        )

        options = build_options(
            model_spec=self.model_spec,
            system_prompt=system_prompt,
            allowed_tools=list(self.allowed_tools),
            output_format={"type": "json_schema", "schema": SOLVER_OUTPUT_SCHEMA},
            hooks={"PreToolUse": [HookMatcher(hooks=[hook])]},
        )

        reasoning: str = ""
        async with self.client_factory(options=options) as client:
            await client.query("Solve this CTF challenge.")
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            reasoning = block.text[:2000]
                elif isinstance(message, ResultMessage):
                    record_result_message(message)
                    structured = getattr(message, "structured_output", None) or {}
                    if structured.get("type") == "flag_found":
                        self._flag_value = structured.get("flag") or self._flag_value
                        reasoning = structured.get("method", "") or reasoning

        flag = Flag(value=self._flag_value) if self._flag_value else None
        return SolverOutput(
            flag=flag,
            attempts=tuple(self._attempts),
            confirmed=self._confirmed,
            reasoning=reasoning,
            step_count=self._step_count,
        )

    async def _submit_flag_rewriter(self, tool_input: dict) -> dict | None:
        """submit_flag コマンドの検出と echo 置換

        Args:
            tool_input: SDK 由来の tool 入力

        Returns:
            submit_flag 検出時の allow 返り値もしくは None
        """
        self._step_count += 1
        command = str(tool_input.get("command", ""))
        m = _SUBMIT_FLAG_RE.match(command.strip())
        if not m:
            return None
        flag_value = m.group(1).strip()
        attempt = await self.flag_submitter(self.challenge.name, flag_value)
        self._attempts.append(attempt)
        if attempt.verdict in (FlagVerdict.CORRECT, FlagVerdict.ALREADY_SOLVED):
            self._confirmed = True
            self._flag_value = flag_value
        echoed = f"echo {shlex.quote(_format_attempt(attempt))}"
        return allow_replace_command(tool_input, echoed)


def _format_attempt(attempt: SolveAttempt) -> str:
    """SolveAttempt の 1 行整形

    Args:
        attempt: 提出試行

    Returns:
        判定ラベル付きの単一行文字列
    """
    label = {
        FlagVerdict.CORRECT: "CORRECT",
        FlagVerdict.ALREADY_SOLVED: "ALREADY SOLVED",
        FlagVerdict.INCORRECT: "INCORRECT",
        FlagVerdict.UNKNOWN: "UNKNOWN",
    }[attempt.verdict]
    msg = f"{label} — flag={attempt.flag!r}"
    if attempt.message:
        msg += f" | {attempt.message}"
    return msg


def describe_exec_result(result: ExecResult) -> str:
    """ExecResult の 1 文字列整形

    Args:
        result: 実行結果

    Returns:
        stdout/stderr/exit を結合した文字列
    """
    parts: list[str] = []
    if result.stdout:
        parts.append(result.stdout)
    if result.stderr:
        parts.append(f"[stderr]\n{result.stderr}")
    if result.exit_code != 0:
        parts.append(f"[exit {result.exit_code}]")
    if result.timed_out:
        parts.append("[timed out]")
    return "\n".join(parts) or "(no output)"

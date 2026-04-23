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
from shared.sandbox import Sandbox

from ..domain import HtbAttempt, Machine, OwnType
from ..services import HtbFlagSubmitter
from .prompts import build_system_prompt
from .schema import HTB_OUTPUT_SCHEMA, AttackerOutput

logger = logging.getLogger(__name__)

_SUBMIT_RE = re.compile(r"^submit_flag\s+(user|root)\s+['\"]?([^'\"]+)['\"]?\s*$", re.IGNORECASE)


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
class Attacker:
    """1 machine 1 session の HTB Attacker

    Attributes:
        machine: 対象 Machine
        sandbox: 実行 sandbox
        flag_submitter: submit_flag 用 callback
        model_spec: Claude モデル識別子
        allowed_tools: 許可ツール名のタプル
        client_factory: SDK クライアントのファクトリ
    """

    machine: Machine
    sandbox: Sandbox
    flag_submitter: HtbFlagSubmitter
    model_spec: str = "claude-opus-4-6"
    allowed_tools: tuple[str, ...] = ("Bash", "WebFetch", "WebSearch")
    client_factory: _SdkClientFactory = field(default=ClaudeSDKClient)

    _attempts: list[HtbAttempt] = field(default_factory=list, init=False)
    _user_flag: str | None = field(default=None, init=False)
    _root_flag: str | None = field(default=None, init=False)
    _step_count: int = field(default=0, init=False)

    async def attack(self) -> AttackerOutput:
        """1 session の実行

        Returns:
            session 結果を含む AttackerOutput
        """
        system_prompt = build_system_prompt(self.machine)
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
            output_format={"type": "json_schema", "schema": HTB_OUTPUT_SCHEMA},
            hooks={"PreToolUse": [HookMatcher(hooks=[hook])]},
        )

        summary = ""
        chain: tuple[str, ...] = ()
        last_text = ""

        async with self.client_factory(options=options) as client:
            await client.query(
                f"Attack HTB machine `{self.machine.name}` at IP {self.machine.ip}."
            )
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            last_text = block.text[:2000]
                elif isinstance(message, ResultMessage):
                    record_result_message(message)
                    structured = getattr(message, "structured_output", None) or {}
                    if structured:
                        summary = str(structured.get("summary") or summary)
                        raw_chain = structured.get("chain") or []
                        chain = tuple(str(s) for s in raw_chain if isinstance(s, str))
                        if self._user_flag is None:
                            u = structured.get("user_flag")
                            if isinstance(u, str) and u:
                                self._user_flag = u
                        if self._root_flag is None:
                            r = structured.get("root_flag")
                            if isinstance(r, str) and r:
                                self._root_flag = r

        if not summary:
            summary = last_text[:500] or "(no summary)"
        return AttackerOutput(
            user_flag=self._user_flag,
            root_flag=self._root_flag,
            attempts=tuple(self._attempts),
            summary=summary,
            chain=chain,
        )

    async def _submit_flag_rewriter(self, tool_input: dict) -> dict | None:
        """submit_flag user|root <FLAG> の傍受と echo 置換

        Args:
            tool_input: SDK 由来の tool 入力

        Returns:
            submit_flag 検出時の allow 返り値もしくは None
        """
        self._step_count += 1
        command = str(tool_input.get("command", ""))
        m = _SUBMIT_RE.match(command.strip())
        if not m:
            return None
        own_type = OwnType(m.group(1).lower())
        flag_value = m.group(2).strip()
        attempt = await self.flag_submitter(own_type, flag_value)
        self._attempts.append(attempt)
        if attempt.accepted:
            if own_type is OwnType.USER:
                self._user_flag = flag_value
            else:
                self._root_flag = flag_value
        echoed = f"echo {shlex.quote(_format_attempt(attempt))}"
        return allow_replace_command(tool_input, echoed)


def _format_attempt(attempt: HtbAttempt) -> str:
    """HtbAttempt の 1 行整形

    Args:
        attempt: 提出試行

    Returns:
        判定ラベル付きの単一行文字列
    """
    status = "ACCEPTED" if attempt.accepted else "REJECTED"
    return f"{status} — {attempt.own_type.value} flag={attempt.flag!r} | {attempt.message}"

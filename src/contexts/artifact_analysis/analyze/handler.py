from __future__ import annotations

import logging
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
from layers.claude_sdk import build_options, make_pre_tool_hook, sandbox_bash_rewrite
from shared.result import AnalysisReport, Evidence
from shared.sandbox import Sandbox

from ..domain import Artifact
from .prompts import build_system_prompt
from .schema import ANALYSIS_OUTPUT_SCHEMA

logger = logging.getLogger(__name__)


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
class Analyzer:
    """1 artifact 1 session の Analyzer

    Attributes:
        artifact: 解析対象 Artifact
        sandbox: 実行 sandbox
        container_path: container 内 artifact パス
        model_spec: Claude モデル識別子
        container_arch: sandbox の arch 文字列
        allowed_tools: 許可ツール名のタプル
        client_factory: SDK クライアントのファクトリ
    """

    artifact: Artifact
    sandbox: Sandbox
    container_path: str
    model_spec: str = "claude-opus-4-6"
    container_arch: str = "unknown"
    allowed_tools: tuple[str, ...] = ("Bash", "WebFetch", "WebSearch")
    client_factory: _SdkClientFactory = field(default=ClaudeSDKClient)

    _step_count: int = field(default=0, init=False)

    async def analyze(self) -> AnalysisReport:
        """1 session の実行

        Returns:
            生成された AnalysisReport
        """
        system_prompt = build_system_prompt(
            self.artifact,
            container_path=self.container_path,
            container_arch=self.container_arch,
        )
        hook = make_pre_tool_hook(
            allowed_tools=self.allowed_tools,
            bash_rewrite=sandbox_bash_rewrite(self.sandbox),
        )
        options = build_options(
            model_spec=self.model_spec,
            system_prompt=system_prompt,
            allowed_tools=list(self.allowed_tools),
            output_format={"type": "json_schema", "schema": ANALYSIS_OUTPUT_SCHEMA},
            hooks={"PreToolUse": [HookMatcher(hooks=[hook])]},
        )

        summary = "(no analysis produced)"
        sections: tuple[tuple[str, str], ...] = ()
        last_text = ""

        async with self.client_factory(options=options) as client:
            await client.query(
                f"Analyze the artifact `{self.container_path}` and return the JSON report."
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
                        raw_sections = structured.get("sections") or []
                        sections = tuple(
                            (str(s.get("title", "")), str(s.get("body", "")))
                            for s in raw_sections
                            if isinstance(s, dict)
                        )

        evidence = (
            Evidence(
                source=f"artifact:{self.artifact.filename()}",
                captured_at=_now_utc(),
                content=(
                    f"sha256={self.artifact.sha256} "
                    f"size={self.artifact.size_bytes} kind={self.artifact.kind.value}"
                ),
                note=last_text[:500],
            ),
        )
        return AnalysisReport(summary=summary, sections=sections, evidence=evidence)


def _now_utc():
    """UTC 現在時刻の取得

    Returns:
        現在の UTC datetime
    """
    from datetime import UTC, datetime

    return datetime.now(UTC)

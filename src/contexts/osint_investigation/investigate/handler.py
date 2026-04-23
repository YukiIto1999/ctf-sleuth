from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKClient,
    HookMatcher,
    ResultMessage,
    TextBlock,
)

from foundation.metrics import record_result_message
from layers.claude_sdk import build_options, make_pre_tool_hook
from shared.result import Evidence, Finding, FindingsCollected, Severity

from ..domain import Target
from .prompts import build_system_prompt
from .schema import INVESTIGATION_OUTPUT_SCHEMA

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
class Investigator:
    """1 target 1 session の OSINT Investigator

    Attributes:
        target: 調査対象 Target
        model_spec: Claude モデル識別子
        allowed_tools: 許可ツール名のタプル
        client_factory: SDK クライアントのファクトリ
    """

    target: Target
    model_spec: str = "claude-opus-4-6"
    allowed_tools: tuple[str, ...] = ("WebFetch", "WebSearch")
    client_factory: _SdkClientFactory = field(default=ClaudeSDKClient)

    async def investigate(self) -> FindingsCollected:
        """1 session の実行

        Returns:
            findings と evidence を持つ FindingsCollected
        """
        system_prompt = build_system_prompt(self.target)
        hook = make_pre_tool_hook(
            allowed_tools=self.allowed_tools,
            bash_rewrite=None,
        )

        options = build_options(
            model_spec=self.model_spec,
            system_prompt=system_prompt,
            allowed_tools=list(self.allowed_tools),
            output_format={"type": "json_schema", "schema": INVESTIGATION_OUTPUT_SCHEMA},
            hooks={"PreToolUse": [HookMatcher(hooks=[hook])]},
        )

        findings: tuple[Finding, ...] = ()
        evidence_pool: list[Evidence] = []
        now = datetime.now(UTC)

        async with self.client_factory(options=options) as client:
            await client.query(
                f"Investigate the {self.target.kind.value} target `{self.target.raw}` "
                "using public information only. Return the JSON findings."
            )
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            _ = block.text
                elif isinstance(message, ResultMessage):
                    record_result_message(message)
                    structured = getattr(message, "structured_output", None) or {}
                    if structured:
                        raw = structured.get("findings") or []
                        findings, extra_evidence = _findings_from_payload(raw, now)
                        evidence_pool.extend(extra_evidence)

        return FindingsCollected(
            findings=findings,
            evidence=tuple(evidence_pool),
        )


def _findings_from_payload(
    raw: list[Any],
    captured_at: datetime,
) -> tuple[tuple[Finding, ...], list[Evidence]]:
    """structured_output の findings 分解

    Args:
        raw: findings 配列
        captured_at: Evidence に付与する時刻

    Returns:
        Finding タプルと Evidence リストの組
    """
    findings: list[Finding] = []
    evidence: list[Evidence] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        summary = str(item.get("summary") or "").strip()
        if not summary:
            continue
        severity = _severity_from_str(str(item.get("severity") or "info"))
        recommendation = str(item.get("recommendation") or "")
        raw_evidence = item.get("evidence") or []
        ev_list: list[Evidence] = []
        for e in raw_evidence:
            if not isinstance(e, str) or not e.strip():
                continue
            ev = Evidence(
                source=f"finding[{i}]",
                captured_at=captured_at,
                content=e.strip(),
            )
            ev_list.append(ev)
            evidence.append(ev)
        findings.append(
            Finding(
                summary=summary,
                severity=severity,
                evidence=tuple(ev_list),
                recommendation=recommendation,
            )
        )
    return tuple(findings), evidence


def _severity_from_str(s: str) -> Severity:
    """文字列からの Severity 解決

    Args:
        s: severity 文字列

    Returns:
        対応する Severity もしくは INFO
    """
    try:
        return Severity(s.lower())
    except ValueError:
        return Severity.INFO

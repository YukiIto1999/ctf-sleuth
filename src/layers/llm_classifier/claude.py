from __future__ import annotations

import json
from typing import Any, Protocol

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

from layers.claude_sdk import build_options
from shared.probe import InputProbe
from shared.task import AlternativeClass, Classification, TaskType

DEFAULT_CLASSIFIER_MODEL = "claude-haiku-4-5"

_CLASSIFY_SYSTEM_PROMPT = """You classify inputs for a security AI framework.

Given observed facts about a user-supplied input, pick exactly one of:

- `ctf_challenge`: a CTFd-hosted competitive problem; the framework will
  pull the challenge set and submit flags. Signals: URL with CTFd API
  reachable, user mentions "CTF event / token / challenge set".
- `htb_machine`: a HackTheBox machine. Signals: IP in 10.10.x.x or
  10.129.x.x, mention of "machine", "root.txt", "user.txt".
- `artifact_analysis`: analyze a local file (binary / pcap / memory dump /
  disk image / document) to produce a structured report. Signals: existing
  file path, file kind = elf / pe / pcap / pdf / pcapng / memory_dump.
- `osint_investigation`: gather public information about a real-world
  target (domain, person, company, question). Default when nothing else
  clearly fits.

Respond with ONLY valid JSON matching this schema — no prose:

{
  "task_type": "ctf_challenge" | "htb_machine" | "artifact_analysis" | "osint_investigation",
  "confidence": <float 0.0..1.0>,
  "reasoning": "<one sentence>",
  "alternatives": [
    {"task_type": "<one of the four>", "confidence": <float>}
  ]
}

Use confidence >= 0.85 only when signals are strong and unambiguous.
Use confidence 0.6-0.8 for reasonable but uncertain guesses. Use
alternatives to record the next-best candidate when meaningful.
"""


_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["task_type", "confidence", "reasoning", "alternatives"],
    "additionalProperties": False,
    "properties": {
        "task_type": {
            "type": "string",
            "enum": [t.value for t in TaskType],
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reasoning": {"type": "string"},
        "alternatives": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["task_type", "confidence"],
                "additionalProperties": False,
                "properties": {
                    "task_type": {
                        "type": "string",
                        "enum": [t.value for t in TaskType],
                    },
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                },
            },
        },
    },
}


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


def _format_probe_summary(probe: InputProbe) -> str:
    """probe の平文要約化

    Args:
        probe: 入力観測結果

    Returns:
        LLM に渡す複数行の要約
    """
    shape = probe.shape
    lines: list[str] = [
        f"raw input: {shape.raw!r}",
        f"is_http_url: {shape.is_http_url}",
        f"is_ip: {shape.is_ip}",
        f"is_domain: {shape.is_domain}",
        f"looks_like_question: {shape.looks_like_question}",
        f"htb_hint: {shape.htb_hint}",
        f"is_existing_path: {probe.is_existing_path}",
        f"file_kind: {probe.file_kind.value if probe.file_kind else 'none'}",
    ]
    if probe.http is not None:
        lines += [
            f"http.status: {probe.http.status}",
            f"http.server_header: {probe.http.server_header}",
            f"http.ctfd_api_ok: {probe.http.ctfd_api_ok}",
            f"http.final_url: {probe.http.final_url}",
        ]
    return "\n".join(lines)


def _parse_classification(raw_json: str) -> Classification:
    """JSON 文字列からの Classification 復元

    Args:
        raw_json: LLM 出力の JSON 文字列

    Returns:
        復元された Classification
    """
    from shared.task import REQUIRED_PARAMS_BY_TYPE

    data = json.loads(raw_json)
    task_type = TaskType(data["task_type"])
    alts = tuple(
        AlternativeClass(TaskType(a["task_type"]), float(a["confidence"]))
        for a in data.get("alternatives", [])
    )
    return Classification(
        task_type=task_type,
        confidence=float(data["confidence"]),
        required_params=REQUIRED_PARAMS_BY_TYPE[task_type],
        alternatives=alts,
        reasoning=str(data.get("reasoning", "")),
    )


class LlmClassifier:
    """Claude Agent SDK を介した 1-shot 分類器"""

    def __init__(
        self,
        *,
        model_spec: str = DEFAULT_CLASSIFIER_MODEL,
        client_factory: _SdkClientFactory | None = None,
    ) -> None:
        """LLM 分類器の初期化

        Args:
            model_spec: 使用する Claude モデル識別子
            client_factory: ClaudeSDKClient 互換のファクトリ
        """
        self._model_spec = model_spec
        self._client_factory = client_factory or ClaudeSDKClient

    async def classify(self, probe: InputProbe) -> Classification:
        """LLM 呼出による分類

        Args:
            probe: 入力観測結果

        Returns:
            LLM 由来の Classification

        Raises:
            RuntimeError: 構造化出力と素テキスト双方の復元に失敗した場合
        """
        options = build_options(
            model_spec=self._model_spec,
            system_prompt=_CLASSIFY_SYSTEM_PROMPT,
            allowed_tools=[],
            skills=None,
            output_format={"type": "json_schema", "schema": _OUTPUT_SCHEMA},
        )
        summary = _format_probe_summary(probe)

        async with self._client_factory(options=options) as client:
            await client.query(summary)
            structured: dict[str, Any] | None = None
            text_fallback: str | None = None

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock) and text_fallback is None:
                            text_fallback = block.text
                elif isinstance(message, ResultMessage):
                    candidate = getattr(message, "structured_output", None)
                    if candidate:
                        structured = candidate

        if structured is not None:
            return _parse_classification(json.dumps(structured))
        if text_fallback is not None:
            return _parse_classification(text_fallback.strip())

        raise RuntimeError("LLM classifier produced no parseable output")

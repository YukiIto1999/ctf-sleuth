from __future__ import annotations

from typing import Any, Literal

from claude_agent_sdk import ClaudeAgentOptions

SkillsValue = list[str] | Literal["all"] | None


def build_options(
    *,
    model_spec: str,
    system_prompt: str,
    allowed_tools: list[str] | None = None,
    skills: SkillsValue = "all",
    mcp_extra: dict[str, Any] | None = None,
    hooks: dict[str, Any] | None = None,
    output_format: dict[str, Any] | None = None,
    effort: str | None = None,
) -> ClaudeAgentOptions:
    """ClaudeAgentOptions の共通構築

    Args:
        model_spec: Claude モデル識別子
        system_prompt: 挿入する system prompt
        allowed_tools: 許可ツール名の一覧
        skills: skill の有効化範囲
        mcp_extra: 追加登録する MCP server の定義
        hooks: PreToolUse/PostToolUse の hook 設定
        output_format: 構造化出力の schema 指定
        effort: reasoning effort 指定

    Returns:
        構築済みの ClaudeAgentOptions
    """
    kwargs: dict[str, Any] = {
        "model": model_spec,
        "system_prompt": system_prompt,
        "allowed_tools": list(allowed_tools or []),
        "mcp_servers": mcp_extra or {},
        "permission_mode": "bypassPermissions",
        "env": {"CLAUDECODE": ""},
        "hooks": hooks or {},
    }
    if skills is not None:
        kwargs["skills"] = skills
        kwargs["setting_sources"] = ["project"]
    if effort is not None:
        kwargs["effort"] = effort
    if output_format is not None:
        kwargs["output_format"] = output_format
    return ClaudeAgentOptions(**kwargs)

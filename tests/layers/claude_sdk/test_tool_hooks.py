from __future__ import annotations

import pytest

from layers.claude_sdk.tool_hooks import (
    allow_replace_command,
    compose_bash_rewriters,
    make_pre_tool_hook,
    sandbox_bash_rewrite,
)
from layers.sandbox import StubSandbox


@pytest.mark.asyncio
async def test_wrong_event_returns_empty() -> None:
    """PreToolUse 以外のイベントの素通し"""
    hook = make_pre_tool_hook(allowed_tools=("Bash",))
    out = await hook({"hook_event_name": "PostToolUse"}, "tid", None)
    assert out == {}


@pytest.mark.asyncio
async def test_allowed_non_bash_passes_through() -> None:
    """許可済非 Bash ツールの allow 化"""
    hook = make_pre_tool_hook(allowed_tools=("WebFetch", "WebSearch"))
    out = await hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "WebFetch",
            "tool_input": {"url": "https://x"},
        },
        "tid",
        None,
    )
    assert out == {}


@pytest.mark.asyncio
async def test_unknown_tool_is_denied() -> None:
    """未許可ツールの deny"""
    hook = make_pre_tool_hook(allowed_tools=("Bash",))
    out = await hook(
        {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {}},
        "tid",
        None,
    )
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Read" in out["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.asyncio
async def test_structured_output_is_always_allowed() -> None:
    """StructuredOutput の常時 allow"""
    hook = make_pre_tool_hook(allowed_tools=("WebFetch",))
    out = await hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "StructuredOutput",
            "tool_input": {},
        },
        "tid",
        None,
    )
    assert out == {}


@pytest.mark.asyncio
async def test_bash_without_rewrite_is_denied() -> None:
    """rewriter 未指定下の Bash deny"""
    hook = make_pre_tool_hook(allowed_tools=("WebFetch",), bash_rewrite=None)
    out = await hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        },
        "tid",
        None,
    )
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.asyncio
async def test_bash_with_rewrite_returns_result() -> None:
    """rewriter 結果の素通し"""

    async def rewrite(tool_input: dict) -> dict:
        """テスト用固定 rewriter

        Args:
            tool_input: tool 入力

        Returns:
            固定の allow dict
        """
        return {"hookSpecificOutput": {"permissionDecision": "allow", "marker": "rewritten"}}

    hook = make_pre_tool_hook(allowed_tools=(), bash_rewrite=rewrite)
    out = await hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        },
        "tid",
        None,
    )
    assert out["hookSpecificOutput"]["marker"] == "rewritten"


@pytest.mark.asyncio
async def test_bash_rewrite_returning_none_is_denied() -> None:
    """rewriter が None を返した場合の deny"""

    async def rewrite(tool_input: dict) -> None:
        """常に None を返す rewriter

        Args:
            tool_input: tool 入力

        Returns:
            None
        """
        return None

    hook = make_pre_tool_hook(allowed_tools=(), bash_rewrite=rewrite)
    out = await hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        },
        "tid",
        None,
    )
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.asyncio
async def test_bash_rewrite_exception_is_swallowed_to_deny() -> None:
    """rewriter 例外の deny 変換"""

    async def rewrite(tool_input: dict):
        """常に例外を投げる rewriter

        Args:
            tool_input: tool 入力

        Raises:
            RuntimeError: 常に送出
        """
        raise RuntimeError("boom")

    hook = make_pre_tool_hook(allowed_tools=(), bash_rewrite=rewrite)
    out = await hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        },
        "tid",
        None,
    )
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "bash handler error" in out["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.asyncio
async def test_sandbox_rewrite_wraps_in_docker_exec() -> None:
    """sandbox_bash_rewrite による docker exec 包み"""
    sandbox = StubSandbox()
    await sandbox.start()
    rewrite = sandbox_bash_rewrite(sandbox)
    result = await rewrite({"command": "ls -la /tmp"})
    cmd = result["hookSpecificOutput"]["updatedInput"]["command"]
    assert cmd.startswith("docker exec -i stub-container bash -c")
    assert "'ls -la /tmp'" in cmd


@pytest.mark.asyncio
async def test_compose_uses_first_non_none() -> None:
    """compose_bash_rewriters の先勝ち優先"""
    called: list[str] = []

    async def a(inp: dict) -> None:
        """None を返す第 1 rewriter

        Args:
            inp: tool 入力

        Returns:
            None
        """
        called.append("a")
        return None

    async def b(inp: dict) -> dict:
        """固定 dict を返す第 2 rewriter

        Args:
            inp: tool 入力

        Returns:
            from=b の dict
        """
        called.append("b")
        return {"from": "b"}

    async def c(inp: dict) -> dict:
        """呼ばれないはずの第 3 rewriter

        Args:
            inp: tool 入力

        Returns:
            from=c の dict
        """
        called.append("c")
        return {"from": "c"}

    composed = compose_bash_rewriters(a, b, c)
    result = await composed({})
    assert result == {"from": "b"}
    assert called == ["a", "b"]


@pytest.mark.asyncio
async def test_compose_returns_none_if_all_none() -> None:
    """全 rewriter が None の場合の None 返却"""

    async def none_handler(inp: dict) -> None:
        """常に None を返す rewriter

        Args:
            inp: tool 入力

        Returns:
            None
        """
        return None

    composed = compose_bash_rewriters(none_handler, none_handler)
    assert await composed({}) is None


def test_allow_replace_command_overwrites_command() -> None:
    """allow_replace_command の command 置換"""
    out = allow_replace_command({"command": "ls", "other": "keep"}, "echo ok")
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"
    updated = out["hookSpecificOutput"]["updatedInput"]
    assert updated["command"] == "echo ok"
    assert updated["other"] == "keep"

from __future__ import annotations

import logging
import shlex
from collections.abc import Awaitable, Callable
from typing import Any

from shared.sandbox import Sandbox

logger = logging.getLogger(__name__)


FRAMEWORK_TOOLS: frozenset[str] = frozenset({"StructuredOutput"})


BashRewriter = Callable[[dict], Awaitable[dict | None]]

PreToolHook = Callable[[dict, str, Any], Awaitable[dict]]


def make_pre_tool_hook(
    *,
    allowed_tools: tuple[str, ...],
    bash_rewrite: BashRewriter | None = None,
) -> PreToolHook:
    """PreToolUse hook の生成

    Args:
        allowed_tools: allow 対象のツール名タプル
        bash_rewrite: Bash 用 rewriter

    Returns:
        PreToolUse 用の hook 関数
    """
    allowed = set(allowed_tools)

    async def hook(input_data: dict, tool_use_id: str, context: Any) -> dict:
        """PreToolUse 判定処理

        Args:
            input_data: SDK から渡される入力辞書
            tool_use_id: tool 呼出 ID
            context: SDK コンテキスト

        Returns:
            allow/deny の hook 返り値辞書
        """
        if input_data.get("hook_event_name") != "PreToolUse":
            return {}
        tool_name = str(input_data.get("tool_name", ""))
        tool_input = input_data.get("tool_input") or {}

        if tool_name in FRAMEWORK_TOOLS:
            return {}

        if tool_name == "Bash":
            if bash_rewrite is None:
                return _deny(tool_name, hint="Bash is not permitted for this session.")
            try:
                result = await bash_rewrite(tool_input)
            except Exception as e:  # noqa: BLE001
                logger.warning("bash_rewrite raised: %s", e)
                return _deny(tool_name, hint=f"bash handler error: {e}")
            if result is None:
                return _deny(tool_name, hint="bash handler produced no result")
            return result

        if tool_name in allowed:
            return {}

        return _deny(tool_name)

    return hook


def sandbox_bash_rewrite(sandbox: Sandbox) -> BashRewriter:
    """sandbox 内実行への Bash 書換器

    Args:
        sandbox: 対象の Sandbox

    Returns:
        docker exec 形式に置換する BashRewriter
    """

    async def handler(tool_input: dict) -> dict:
        """Bash 入力の書換処理

        Args:
            tool_input: SDK 由来の tool 入力

        Returns:
            書換後の allow 返り値
        """
        command = str(tool_input.get("command", ""))
        rewritten = f"docker exec -i {sandbox.container_id} bash -c {shlex.quote(command)}"
        return _allow_updated(tool_input, command=rewritten)

    return handler


def compose_bash_rewriters(*handlers: BashRewriter) -> BashRewriter:
    """複数 rewriter の合成

    Args:
        *handlers: 順に試行する BashRewriter 群

    Returns:
        最初に非 None を返した結果を採用する合成 rewriter
    """

    async def composed(tool_input: dict) -> dict | None:
        """合成された書換処理

        Args:
            tool_input: SDK 由来の tool 入力

        Returns:
            いずれかの rewriter 結果もしくは None
        """
        for h in handlers:
            result = await h(tool_input)
            if result is not None:
                return result
        return None

    return composed


def _deny(tool_name: str, *, hint: str = "") -> dict:
    """deny 返り値の構築

    Args:
        tool_name: deny 対象のツール名
        hint: 追加説明

    Returns:
        PreToolUse の deny 返り値辞書
    """
    reason = f"{tool_name} is not allowed in this session."
    if hint:
        reason = f"{reason} {hint}"
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _allow_updated(tool_input: dict, **replacements: str) -> dict:
    """allow + 入力差替の返り値構築

    Args:
        tool_input: 元の tool 入力
        **replacements: 上書きするキー値

    Returns:
        PreToolUse の allow 返り値辞書
    """
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {**tool_input, **replacements},
        }
    }


def allow_replace_command(tool_input: dict, command: str) -> dict:
    """Bash command 置換の allow 返り値構築

    Args:
        tool_input: 元の tool 入力
        command: 置換先コマンド

    Returns:
        PreToolUse の allow 返り値辞書
    """
    return _allow_updated(tool_input, command=command)

#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

from layers.claude_sdk.options import build_options
from layers.claude_sdk.tool_hooks import make_pre_tool_hook
from contexts.osint_investigation.domain import Target, TargetKind
from contexts.osint_investigation.investigate import INVESTIGATION_OUTPUT_SCHEMA
from contexts.osint_investigation.investigate.prompts import build_system_prompt


async def main() -> int:
    """OSINT debug smoke test のエントリ

    Returns:
        終了コード
    """
    from claude_agent_sdk import ClaudeSDKClient, HookMatcher

    target = Target(raw="example.com", kind=TargetKind.DOMAIN)

    async def logging_hook(input_data: dict, tool_use_id, context) -> dict:
        """ログ付き PreToolUse hook

        Args:
            input_data: SDK 由来の入力辞書
            tool_use_id: tool 呼出 ID
            context: SDK コンテキスト

        Returns:
            内部 hook の判定結果
        """
        inner = make_pre_tool_hook(
            allowed_tools=("WebFetch", "WebSearch"), bash_rewrite=None
        )
        result = await inner(input_data, tool_use_id, context)
        print(
            f"  [hook] tool={input_data.get('tool_name')!r} "
            f"result={result.get('hookSpecificOutput', {}).get('permissionDecision', 'allow_passthrough')}"
        )
        return result

    options = build_options(
        model_spec="claude-haiku-4-5",
        system_prompt=build_system_prompt(target),
        allowed_tools=["WebFetch", "WebSearch"],
        output_format={"type": "json_schema", "schema": INVESTIGATION_OUTPUT_SCHEMA},
        hooks={"PreToolUse": [HookMatcher(hooks=[logging_hook])]},
    )

    print("→ running session...")
    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            f"Investigate the domain `{target.raw}` using public information only. "
            "Return the JSON findings."
        )
        async for message in client.receive_response():
            type_name = type(message).__name__
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"  [assistant/text] {block.text[:200]}")
                    else:
                        print(f"  [assistant/{type(block).__name__}]")
            elif isinstance(message, ResultMessage):
                so = getattr(message, "structured_output", None)
                print(f"  [result] structured_output keys: {list(so.keys()) if so else None}")
                if so:
                    print(f"  [result] payload: {so}")
                cost = getattr(message, "total_cost_usd", 0)
                print(f"  [result] cost=${cost:.4f}")
            else:
                print(f"  [{type_name}]")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

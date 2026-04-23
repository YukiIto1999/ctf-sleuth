#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

from layers.claude_sdk.options import build_options


async def main() -> int:
    """Claude SDK nested session の smoke test

    Returns:
        終了コード
    """
    options = build_options(
        model_spec="claude-haiku-4-5",
        system_prompt="You are a smoke-test helper. Answer in one short sentence.",
        allowed_tools=[],
        skills=None,
    )

    print("→ opening ClaudeSDKClient (nested session; CLAUDECODE cleared)...")
    async with ClaudeSDKClient(options=options) as client:
        print("→ sending query...")
        await client.query("Reply with exactly the string 'smoke-ok'.")

        got_assistant = False
        got_result = False
        cost_usd: float = 0.0

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                got_assistant = True
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"  assistant: {block.text!r}")
            elif isinstance(message, ResultMessage):
                got_result = True
                cost_usd = float(getattr(message, "total_cost_usd", 0) or 0)
                print(f"  result: cost=${cost_usd:.4f}")

        if got_assistant and got_result:
            print("✓ smoke test passed")
            return 0
        print(f"✗ incomplete: assistant={got_assistant} result={got_result}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

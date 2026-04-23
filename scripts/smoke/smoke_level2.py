#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime

from layers.sandbox import DockerSandbox, SandboxConfig
from contexts.ctf_challenge.domain import (
    Challenge,
    ChallengeId,
    FlagVerdict,
    SolveAttempt,
)
from contexts.ctf_challenge.solve import Solver

SANDBOX_IMAGE = "sleuth-smoke-sandbox"


def _build_challenge() -> Challenge:
    """smoke 用 Challenge の生成

    Returns:
        固定 flag を含む Challenge
    """
    return Challenge(
        id=ChallengeId(1),
        name="smoke-test",
        category_raw="misc",
        strategy=None,
        description=(
            "This is a smoke test. The flag is the literal string "
            "`FLAG{smoke-test-ok}`. Submit it using `submit_flag FLAG{smoke-test-ok}` "
            "via bash. Do not perform any other analysis."
        ),
        value=1,
    )


async def _fake_submitter(challenge_name: str, flag: str) -> SolveAttempt:
    """固定 flag 照合の偽 submitter

    Args:
        challenge_name: challenge 名
        flag: 提出フラグ

    Returns:
        判定済 SolveAttempt
    """
    expected = "FLAG{smoke-test-ok}"
    verdict = FlagVerdict.CORRECT if flag == expected else FlagVerdict.INCORRECT
    print(f"  [submitter] received flag={flag!r} verdict={verdict.value}")
    return SolveAttempt(
        challenge_name=challenge_name,
        flag=flag,
        verdict=verdict,
        message="smoke-test ok" if verdict is FlagVerdict.CORRECT else "smoke-test mismatch",
        submitted_at=datetime.now(UTC),
    )


async def main() -> int:
    """Level 2 smoke test のエントリ

    Returns:
        終了コード
    """
    challenge = _build_challenge()
    sandbox = DockerSandbox(SandboxConfig(image=SANDBOX_IMAGE))

    print(f"→ starting sandbox ({SANDBOX_IMAGE})...")
    await sandbox.start()
    print(f"  container: {sandbox.container_id[:12]}")

    try:
        solver = Solver(
            challenge=challenge,
            sandbox=sandbox,
            flag_submitter=_fake_submitter,
            model_spec="claude-haiku-4-5",  # 安価で smoke 用
        )
        print("→ running Claude session...")
        output = await solver.solve()
    finally:
        print("→ stopping sandbox...")
        await sandbox.stop()

    print("\n=== Result ===")
    print(f"  flag         : {output.flag.value if output.flag else None}")
    print(f"  confirmed    : {output.confirmed}")
    print(f"  attempts     : {len(output.attempts)}")
    print(f"  step_count   : {output.step_count}")
    print(f"  reasoning    : {output.reasoning[:200]}")

    if output.confirmed and output.flag and output.flag.value == "FLAG{smoke-test-ok}":
        print("\n✓ smoke Level 2 passed")
        return 0
    print("\n✗ smoke Level 2 incomplete")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

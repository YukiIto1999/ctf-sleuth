#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys

from contexts.osint_investigation.domain import Target, TargetKind
from contexts.osint_investigation.investigate import Investigator


async def main() -> int:
    """OSINT smoke test のエントリ

    Returns:
        終了コード
    """
    target = Target(raw="example.com", kind=TargetKind.DOMAIN)
    investigator = Investigator(target=target, model_spec="claude-haiku-4-5")

    print(f"→ investigating {target.kind.value} `{target.raw}` ...")
    result = await investigator.investigate()

    print(f"\n=== Findings ({len(result.findings)}) ===")
    for i, f in enumerate(result.findings, start=1):
        print(f"  {i}. [{f.severity.value}] {f.summary}")
        if f.evidence:
            for e in f.evidence[:2]:
                print(f"      - {e.content[:120]}")

    if result.findings:
        print("\n✓ smoke OSINT passed")
        return 0
    print("\n✗ no findings returned")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

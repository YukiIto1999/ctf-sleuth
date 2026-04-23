from __future__ import annotations

import asyncio

import pytest

from layers.sandbox import SandboxPool


class TestSandboxPool:
    """SandboxPool の挙動検証"""

    def test_invalid_max_concurrent(self) -> None:
        """max_concurrent=0 の例外"""
        with pytest.raises(ValueError):
            SandboxPool(max_concurrent=0)

    @pytest.mark.asyncio
    async def test_active_tracks_inside_context(self) -> None:
        """context 内外での active 変動"""
        pool = SandboxPool(max_concurrent=2)
        assert pool.active == 0
        async with pool.acquire_start_slot():
            assert pool.active == 1
        assert pool.active == 0

    @pytest.mark.asyncio
    async def test_concurrent_acquires_respect_limit(self) -> None:
        """同時取得の上限遵守"""
        pool = SandboxPool(max_concurrent=2)
        observed: list[int] = []

        async def worker() -> None:
            """スロット取得後に active を記録するワーカ"""
            async with pool.acquire_start_slot():
                observed.append(pool.active)
                await asyncio.sleep(0.01)

        await asyncio.gather(*(worker() for _ in range(5)))
        assert max(observed) <= 2

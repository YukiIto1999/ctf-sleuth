from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from .config import CONTAINER_LABEL

logger = logging.getLogger(__name__)


class SandboxPool:
    """並行 sandbox 起動の流量制御"""

    def __init__(self, *, max_concurrent: int = 50, warn_thresholds: tuple[int, ...] = (100, 200, 500)) -> None:
        """プールの初期化

        Args:
            max_concurrent: 同時起動上限
            warn_thresholds: 警告を出すアクティブ数の閾値

        Raises:
            ValueError: max_concurrent が 1 未満
        """
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be >= 1")
        self._sem = asyncio.Semaphore(max_concurrent)
        self._active = 0
        self._lock = asyncio.Lock()
        self._warn_thresholds = frozenset(warn_thresholds)

    @property
    def active(self) -> int:
        """現在のアクティブ sandbox 数"""
        return self._active

    @asynccontextmanager
    async def acquire_start_slot(self):
        """起動スロット取得の async context manager

        Yields:
            スロット保持のための None
        """
        await self._sem.acquire()
        try:
            await self._inc()
            yield
        finally:
            await self._dec()
            self._sem.release()

    async def _inc(self) -> None:
        """アクティブ数の加算と閾値警告"""
        async with self._lock:
            self._active += 1
            if self._active in self._warn_thresholds:
                logger.warning("active sandboxes: %d", self._active)

    async def _dec(self) -> None:
        """アクティブ数の減算"""
        async with self._lock:
            self._active = max(0, self._active - 1)


async def cleanup_orphans(*, label: str = CONTAINER_LABEL) -> int:
    """残存 sandbox container の一括削除

    Args:
        label: 対象とする識別ラベル

    Returns:
        削除した container 数
    """
    try:
        import aiodocker
    except ImportError:
        logger.warning("aiodocker not installed; skipping orphan cleanup")
        return 0

    docker = aiodocker.Docker()
    try:
        containers = await docker.containers.list(
            all=True,
            filters={"label": [label]},
        )
        for c in containers:
            try:
                await c.delete(force=True)
            except Exception as e:
                logger.warning("failed to delete orphan %s: %s", c.id[:12], e)
        if containers:
            logger.info("cleaned up %d orphan container(s)", len(containers))
        return len(containers)
    finally:
        try:
            await docker.close()
        except Exception:
            pass

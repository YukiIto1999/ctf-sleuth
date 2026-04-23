from __future__ import annotations

from pathlib import Path

import pytest

from layers.sandbox import SandboxConfig
from shared.sandbox import MountSpec


class TestSandboxConfig:
    """SandboxConfig の挙動検証"""

    def test_minimum_fields(self) -> None:
        """最小フィールドでの初期化"""
        cfg = SandboxConfig(image="x:latest")
        assert cfg.image == "x:latest"
        assert cfg.mounts == ()
        assert cfg.memory_limit_bytes == 16 * 1024**3

    def test_is_frozen(self) -> None:
        """SandboxConfig が frozen であることの検証"""
        cfg = SandboxConfig(image="x")
        with pytest.raises((AttributeError, TypeError)):
            cfg.image = "y"  # type: ignore[misc]

    def test_mounts_preserved(self) -> None:
        """mounts フィールドの保持"""
        m = MountSpec(source=Path("/host"), target="/container")
        cfg = SandboxConfig(image="x", mounts=(m,))
        assert cfg.mounts == (m,)

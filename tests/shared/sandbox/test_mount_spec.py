from __future__ import annotations

from pathlib import Path

import pytest

from shared.sandbox import MountSpec


class TestMountSpec:
    """MountSpec の挙動検証"""

    def test_as_bind_readonly(self) -> None:
        """read-only 時の bind 文字列"""
        m = MountSpec(source=Path("/host"), target="/container")
        assert m.as_bind() == "/host:/container:ro"

    def test_as_bind_rw(self) -> None:
        """read-write 時の bind 文字列"""
        m = MountSpec(source=Path("/host"), target="/container", read_only=False)
        assert m.as_bind() == "/host:/container:rw"

    def test_is_frozen(self) -> None:
        """MountSpec が frozen であることの検証"""
        m = MountSpec(source=Path("/a"), target="/b")
        with pytest.raises((AttributeError, TypeError)):
            m.target = "/c"  # type: ignore[misc]

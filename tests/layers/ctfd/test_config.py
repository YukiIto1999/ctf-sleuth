from __future__ import annotations

import pytest

from layers.ctfd import CtfdConfig


class TestCtfdConfig:
    """CtfdConfig の __post_init__ 検証"""

    def test_token_suffices(self) -> None:
        """token のみで成立"""
        cfg = CtfdConfig(base_url="https://x", token="t")
        assert cfg.token == "t"

    def test_username_password_suffices(self) -> None:
        """username と password の組で成立"""
        cfg = CtfdConfig(base_url="https://x", username="u", password="p")
        assert cfg.username == "u"

    def test_nothing_raises(self) -> None:
        """token も認証情報も無い時の ValueError"""
        with pytest.raises(ValueError):
            CtfdConfig(base_url="https://x")

    def test_username_only_raises(self) -> None:
        """username のみで password 欠落の ValueError"""
        with pytest.raises(ValueError):
            CtfdConfig(base_url="https://x", username="u")

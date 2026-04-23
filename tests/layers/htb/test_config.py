from __future__ import annotations

import pytest

from layers.htb import HtbConfig


class TestHtbConfig:
    """HtbConfig の検証"""

    def test_empty_token_raises(self) -> None:
        """空 token 時の ValueError"""
        with pytest.raises(ValueError):
            HtbConfig(token="")

    def test_valid_token_succeeds(self) -> None:
        """有効 token での成立"""
        cfg = HtbConfig(token="abc")
        assert cfg.token == "abc"

from __future__ import annotations

import pytest

from shared.probe import InputProbe, InputShape


class TestInputProbe:
    """InputProbe の不変性検証"""

    def test_is_frozen(self) -> None:
        """InputProbe が frozen であることの検証"""
        shape = InputShape(
            raw="x",
            is_http_url=False,
            is_ip=False,
            is_domain=False,
            looks_like_question=False,
            htb_hint=False,
        )
        p = InputProbe(shape=shape, is_existing_path=False, file_kind=None, http=None)
        with pytest.raises((AttributeError, TypeError)):
            p.is_existing_path = True  # type: ignore[misc]

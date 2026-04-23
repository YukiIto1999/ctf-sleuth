from __future__ import annotations

from shared.probe import HttpProbe


class TestHttpProbe:
    """HttpProbe の値保持検証"""

    def test_value_preservation(self) -> None:
        """初期化値の保持"""
        hp = HttpProbe(status=200, server_header=None, ctfd_api_ok=False, final_url="https://x/")
        assert hp.status == 200
        assert not hp.ctfd_api_ok

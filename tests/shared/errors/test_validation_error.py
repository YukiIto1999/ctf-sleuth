from __future__ import annotations

import pytest

from shared.errors import MissingRequiredParamError, ValidationError


class TestMissingRequiredParamError:
    """MissingRequiredParamError の挙動検証"""

    def test_records_missing_tuple(self) -> None:
        """missing 属性への記録"""
        e = MissingRequiredParamError(("url", "token"))
        assert e.missing == ("url", "token")

    def test_message_contains_names(self) -> None:
        """メッセージへの name 埋込"""
        e = MissingRequiredParamError(("url",))
        assert "url" in str(e)

    def test_inherits_validation_error(self) -> None:
        """ValidationError からの派生"""
        with pytest.raises(ValidationError):
            raise MissingRequiredParamError(("x",))

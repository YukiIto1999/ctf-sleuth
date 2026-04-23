from __future__ import annotations

import pytest

from shared.sandbox import ExecResult


class TestExecResult:
    """ExecResult の挙動検証"""

    def test_defaults(self) -> None:
        """timed_out のデフォルト値"""
        r = ExecResult(exit_code=0, stdout="ok", stderr="")
        assert not r.timed_out

    def test_is_frozen(self) -> None:
        """ExecResult が frozen であることの検証"""
        r = ExecResult(exit_code=0, stdout="", stderr="")
        with pytest.raises((AttributeError, TypeError)):
            r.exit_code = 1  # type: ignore[misc]

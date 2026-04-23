from __future__ import annotations

import pytest

from contexts.osint_investigation.runner import run_osint_investigation
from shared.errors import MissingRequiredParamError
from shared.task import ExecutionRequest, TaskInput, TaskType


def _req(*, target: str = "", raw: str = "") -> ExecutionRequest:
    """テスト用 ExecutionRequest の生成

    Args:
        target: params.target 値
        raw: input.raw 値

    Returns:
        OSINT_INVESTIGATION 固定の ExecutionRequest
    """
    params = {"target": target} if target else {}
    return ExecutionRequest(
        task_type=TaskType.OSINT_INVESTIGATION,
        input=TaskInput(raw=raw),
        params=params,
        model_spec="claude-opus-4-6",
    )


class TestRunOsintInvestigation:
    """run_osint_investigation の境界検証"""

    @pytest.mark.asyncio
    async def test_missing_target_raises(self) -> None:
        """params.target と input.raw 双方が空時の例外"""
        with pytest.raises(MissingRequiredParamError) as exc:
            await run_osint_investigation(_req())
        assert "target" in exc.value.missing

    @pytest.mark.asyncio
    async def test_whitespace_only_target_raises(self) -> None:
        """空白のみ target の例外"""
        with pytest.raises(MissingRequiredParamError):
            await run_osint_investigation(_req(target="   "))

from __future__ import annotations

import pytest

from foundation.metrics import metrics_scope, record_result_message


class _FakeResult:
    """ResultMessage 互換の偽オブジェクト"""

    def __init__(
        self,
        *,
        total_cost_usd: float | None = None,
        usage: dict[str, int] | None = None,
    ) -> None:
        """偽 result の初期化

        Args:
            total_cost_usd: コスト値
            usage: トークン使用量 dict
        """
        if total_cost_usd is not None:
            self.total_cost_usd = total_cost_usd
        if usage is not None:
            self.usage = usage


def test_record_without_scope_is_noop() -> None:
    """scope 外 record の no-op 動作"""
    record_result_message(_FakeResult(total_cost_usd=1.0))


def test_scope_activates_accumulator() -> None:
    """scope 内 record の集計"""
    with metrics_scope() as acc:
        record_result_message(_FakeResult(total_cost_usd=0.5, usage={"input_tokens": 20}))
        record_result_message(_FakeResult(total_cost_usd=0.5, usage={"input_tokens": 30}))
    assert acc.cost_usd == pytest.approx(1.0)
    assert acc.turns == 2
    assert acc.input_tokens == 50


def test_scope_is_isolated() -> None:
    """scope 外 record の影響隔離"""
    with metrics_scope() as acc:
        record_result_message(_FakeResult(total_cost_usd=0.1))
    record_result_message(_FakeResult(total_cost_usd=99.0))
    assert acc.cost_usd == pytest.approx(0.1)


def test_nested_scopes_use_innermost() -> None:
    """入れ子 scope での内側優先"""
    with metrics_scope() as outer:
        record_result_message(_FakeResult(total_cost_usd=1.0))
        with metrics_scope() as inner:
            record_result_message(_FakeResult(total_cost_usd=5.0))
        record_result_message(_FakeResult(total_cost_usd=2.0))
    assert inner.cost_usd == pytest.approx(5.0)
    assert outer.cost_usd == pytest.approx(3.0)

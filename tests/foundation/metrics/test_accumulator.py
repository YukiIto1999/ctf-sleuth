from __future__ import annotations

from datetime import UTC, datetime

import pytest

from foundation.metrics import MetricsAccumulator, SessionMetrics


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


class TestMetricsAccumulator:
    """MetricsAccumulator の挙動検証"""

    def test_starts_empty(self) -> None:
        """初期化直後の空状態"""
        acc = MetricsAccumulator()
        assert acc.cost_usd == 0.0
        assert acc.turns == 0
        assert acc.input_tokens == 0
        assert acc.output_tokens == 0

    def test_record_single_result(self) -> None:
        """単一 result の取込"""
        acc = MetricsAccumulator()
        acc.record_result_message(
            _FakeResult(
                total_cost_usd=0.042,
                usage={
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_read_input_tokens": 10,
                    "cache_creation_input_tokens": 5,
                },
            )
        )
        assert acc.cost_usd == pytest.approx(0.042)
        assert acc.turns == 1
        assert acc.input_tokens == 100
        assert acc.output_tokens == 50
        assert acc.cache_read_tokens == 10
        assert acc.cache_creation_tokens == 5

    def test_record_accumulates(self) -> None:
        """複数 result の累積"""
        acc = MetricsAccumulator()
        acc.record_result_message(_FakeResult(total_cost_usd=0.1, usage={"input_tokens": 10}))
        acc.record_result_message(_FakeResult(total_cost_usd=0.2, usage={"input_tokens": 20}))
        assert acc.cost_usd == pytest.approx(0.3)
        assert acc.turns == 2
        assert acc.input_tokens == 30

    def test_record_handles_missing_fields(self) -> None:
        """欠落フィールドに対する堅牢性"""
        acc = MetricsAccumulator()
        acc.record_result_message(_FakeResult())
        assert acc.turns == 1
        assert acc.cost_usd == 0.0

    def test_record_handles_non_dict_usage(self) -> None:
        """dict 以外の usage に対する __dict__ 経由処理"""

        class _UsageObj:
            """属性として input_tokens を持つ usage"""

            def __init__(self) -> None:
                """usage オブジェクトの初期化"""
                self.input_tokens = 42

        class _ResultWithObjUsage:
            """usage がオブジェクトの偽 result"""

            total_cost_usd = 0.01
            usage = _UsageObj()

        acc = MetricsAccumulator()
        acc.record_result_message(_ResultWithObjUsage())
        assert acc.input_tokens == 42

    def test_finalize_returns_immutable_snapshot(self) -> None:
        """finalize の不変スナップショット生成"""
        acc = MetricsAccumulator()
        acc.record_result_message(_FakeResult(total_cost_usd=0.5, usage={"input_tokens": 10}))
        metrics = acc.finalize()
        assert isinstance(metrics, SessionMetrics)
        assert metrics.cost_usd == 0.5
        with pytest.raises((AttributeError, TypeError)):
            metrics.cost_usd = 0.0  # type: ignore[misc]

    def test_finalize_duration_is_positive(self) -> None:
        """finalize duration の非負性"""
        acc = MetricsAccumulator()
        metrics = acc.finalize()
        assert metrics.duration_seconds >= 0.0
        assert isinstance(metrics.started_at, datetime)
        assert metrics.started_at.tzinfo is UTC

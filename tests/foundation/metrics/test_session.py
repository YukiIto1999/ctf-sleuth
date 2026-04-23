from __future__ import annotations

from datetime import UTC, datetime

from foundation.metrics import SessionMetrics


class TestSessionMetrics:
    """SessionMetrics の挙動検証"""

    def test_to_dict_includes_all_fields(self) -> None:
        """to_dict の全フィールド包含"""
        m = SessionMetrics(
            cost_usd=1.5,
            turns=3,
            input_tokens=100,
            output_tokens=50,
            cache_read_tokens=10,
            cache_creation_tokens=5,
            started_at=datetime(2026, 4, 22, 10, tzinfo=UTC),
            completed_at=datetime(2026, 4, 22, 10, 0, 30, tzinfo=UTC),
        )
        d = m.to_dict()
        assert d["cost_usd"] == 1.5
        assert d["turns"] == 3
        assert d["duration_seconds"] == 30.0

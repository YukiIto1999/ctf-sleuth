from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from foundation.metrics import SessionMetrics, append_to_project_log


def test_append_creates_and_appends(tmp_path: Path) -> None:
    """_metrics.jsonl の作成と追記

    Args:
        tmp_path: pytest tmp_path fixture
    """
    metrics = SessionMetrics(
        cost_usd=0.5,
        turns=2,
        input_tokens=100,
        output_tokens=50,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        started_at=datetime(2026, 4, 22, tzinfo=UTC),
        completed_at=datetime(2026, 4, 22, 0, 1, tzinfo=UTC),
    )
    append_to_project_log(
        metrics,
        session_id="session-1",
        task_type="ctf_challenge",
        writeups_dir=tmp_path,
    )
    append_to_project_log(
        metrics,
        session_id="session-2",
        task_type="osint_investigation",
        writeups_dir=tmp_path,
    )
    log = (tmp_path / "_metrics.jsonl").read_text().splitlines()
    assert len(log) == 2
    r1 = json.loads(log[0])
    r2 = json.loads(log[1])
    assert r1["session_id"] == "session-1"
    assert r1["task_type"] == "ctf_challenge"
    assert r1["cost_usd"] == 0.5
    assert r2["task_type"] == "osint_investigation"

from __future__ import annotations

import json
from pathlib import Path

from .session import SessionMetrics


def append_to_project_log(
    metrics: SessionMetrics,
    *,
    session_id: str,
    task_type: str,
    writeups_dir: Path,
) -> None:
    """project の _metrics.jsonl への追記

    Args:
        metrics: 追記対象の SessionMetrics
        session_id: session 識別子
        task_type: タスク種別値
        writeups_dir: writeups ルートディレクトリ
    """
    writeups_dir.mkdir(parents=True, exist_ok=True)
    log_path = writeups_dir / "_metrics.jsonl"
    record = {
        "session_id": session_id,
        "task_type": task_type,
        **metrics.to_dict(),
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

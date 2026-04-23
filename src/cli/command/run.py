from __future__ import annotations

from foundation.metrics import SessionMetrics, append_to_project_log, metrics_scope
from layers.writeups import DEFAULT_WRITEUPS_DIR, persist_task_result
from shared.result import AnalysisReport, FindingsCollected, FlagSubmitted
from shared.task import TaskInput
from workflows.dispatch import default_classifier, execute, plan

from ..bootstrap import make_config, make_runners


async def cmd_run(task_input: TaskInput, *, non_interactive: bool) -> int:
    """run サブコマンドの実装

    Args:
        task_input: 入力
        non_interactive: 対話無効化フラグ

    Returns:
        終了コード
    """
    request = await plan(
        task_input,
        classifier=default_classifier(),
        config=make_config(non_interactive),
    )
    runners = make_runners()
    with metrics_scope() as acc:
        result = await execute(request, runners=runners)
    metrics = acc.finalize()
    _print_result(result)
    _print_metrics(metrics)
    dest = persist_task_result(
        request,
        result,
        writeups_dir=DEFAULT_WRITEUPS_DIR,
        metrics=metrics,
    )
    append_to_project_log(
        metrics,
        session_id=dest.name,
        task_type=request.task_type.value,
        writeups_dir=DEFAULT_WRITEUPS_DIR,
    )
    print(f"\nreport saved: {dest}")
    return 0


def _print_metrics(metrics: SessionMetrics) -> None:
    """SessionMetrics の 1 行表示

    Args:
        metrics: 表示対象の SessionMetrics
    """
    print(
        f"\nmetrics: cost=${metrics.cost_usd:.4f} "
        f"turns={metrics.turns} "
        f"tokens(in/out)={metrics.input_tokens}/{metrics.output_tokens} "
        f"duration={metrics.duration_seconds:.1f}s"
    )


def _print_result(result: object) -> None:
    """TaskResult variant の標準出力表示

    Args:
        result: 表示対象の TaskResult
    """
    if isinstance(result, FlagSubmitted):
        print("result: FlagSubmitted")
        print(f"  flag: {result.flag.value}")
        print(f"  accepted: {result.accepted}")
        print(f"  attempts: {result.attempts}")
        if result.note:
            print(f"  note: {result.note}")
    elif isinstance(result, FindingsCollected):
        print(f"result: FindingsCollected ({len(result.findings)} findings)")
        for f in result.findings:
            print(f"  [{f.severity.value}] {f.summary}")
    elif isinstance(result, AnalysisReport):
        print("result: AnalysisReport")
        print(f"  summary: {result.summary}")
        for title, body in result.sections:
            print(f"  --- {title} ---")
            for line in body.splitlines():
                print(f"    {line}")
    else:
        print(f"result: {result}")

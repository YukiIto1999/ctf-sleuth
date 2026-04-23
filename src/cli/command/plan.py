from __future__ import annotations

from shared.task import TaskInput
from workflows.dispatch import default_classifier, plan

from ..bootstrap import make_config


async def cmd_plan(task_input: TaskInput, *, non_interactive: bool) -> int:
    """plan サブコマンドの実装

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
    print(f"task_type: {request.task_type.value}")
    print(f"model: {request.model_spec}")
    print(f"reasoning: {request.reasoning}")
    print("params:")
    for k, v in request.params.items():
        print(f"  {k}: {v}")
    return 0

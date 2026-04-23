from __future__ import annotations

import argparse
import asyncio
import sys

from shared.errors import (
    AmbiguousClassificationError,
    ClassificationUnderconfidentError,
    MissingRequiredParamError,
    NonInteractiveShellError,
)
from shared.task import TaskType

from .command import cmd_plan, cmd_run
from .dto import to_task_input


def _add_common_task_flags(p: argparse.ArgumentParser) -> None:
    """plan と run サブコマンド共通のフラグ追加

    Args:
        p: 追加対象の ArgumentParser
    """
    p.add_argument("input", help="対象 (URL / ファイルパス / ドメイン / 自由テキスト)")
    p.add_argument(
        "--type",
        dest="task_type",
        choices=[t.value for t in TaskType],
        help="自動分類をスキップして明示指定",
    )
    p.add_argument("--url", help="ctf_challenge: CTFd base URL")
    p.add_argument("--token", help="ctf_challenge/htb_machine: API token")
    p.add_argument("--machine", help="htb_machine: machine id")
    p.add_argument("--ip", help="htb_machine: target IP (VPN connected)")
    p.add_argument("--model", help="LLM model spec を上書き")
    p.add_argument(
        "--non-interactive",
        dest="non_interactive",
        action="store_true",
        help="曖昧時に対話確認せず失敗させる",
    )


def _build_parser() -> argparse.ArgumentParser:
    """CLI parser の構築

    Returns:
        run と plan を持つ ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="sleuth",
        description="Task-driven AI security framework (CTF / OSINT / analysis / HTB)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="分類 (自動) または --type で明示実行")
    _add_common_task_flags(run_p)

    plan_p = sub.add_parser("plan", help="分類結果と ExecutionRequest を表示するのみ (実行しない)")
    _add_common_task_flags(plan_p)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI エントリポイント

    Args:
        argv: 引数列

    Returns:
        終了コード
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    task_input = to_task_input(args)
    non_interactive = bool(getattr(args, "non_interactive", False))

    try:
        if args.command == "plan":
            return asyncio.run(cmd_plan(task_input, non_interactive=non_interactive))
        if args.command == "run":
            return asyncio.run(cmd_run(task_input, non_interactive=non_interactive))
    except ClassificationUnderconfidentError as e:
        print(f"error: classification underconfident — {e}", file=sys.stderr)
        return 2
    except MissingRequiredParamError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except (AmbiguousClassificationError, NonInteractiveShellError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except NotImplementedError as e:
        print(f"not yet implemented: {e}", file=sys.stderr)
        return 3

    parser.error("unknown command")
    return 1


if __name__ == "__main__":
    sys.exit(main())

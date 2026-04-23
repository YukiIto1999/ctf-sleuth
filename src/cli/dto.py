from __future__ import annotations

import argparse
from types import MappingProxyType

from shared.task import TaskInput


def collect_flags(args: argparse.Namespace) -> dict[str, str]:
    """argparse Namespace からのフラグ抽出

    Args:
        args: 解析済引数

    Returns:
        TaskInput に渡すフラグ dict
    """
    flags: dict[str, str] = {}
    if getattr(args, "task_type", None):
        flags["type"] = args.task_type
    for key in ("url", "token", "machine", "ip", "model"):
        value = getattr(args, key, None)
        if value:
            flags[key] = value
    return flags


def to_task_input(args: argparse.Namespace) -> TaskInput:
    """argparse Namespace から TaskInput への変換

    Args:
        args: 解析済引数

    Returns:
        不変 flags を持つ TaskInput
    """
    return TaskInput(raw=args.input, flags=MappingProxyType(collect_flags(args)))

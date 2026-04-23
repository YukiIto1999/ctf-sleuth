from __future__ import annotations

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from .accumulator import MetricsAccumulator

_metrics_ctx: contextvars.ContextVar[MetricsAccumulator | None] = contextvars.ContextVar(
    "ctf_sleuth_metrics_accumulator", default=None
)


@contextmanager
def metrics_scope() -> Iterator[MetricsAccumulator]:
    """MetricsAccumulator を ContextVar に束ねる scope

    Yields:
        scope 内で active な MetricsAccumulator
    """
    acc = MetricsAccumulator()
    token = _metrics_ctx.set(acc)
    try:
        yield acc
    finally:
        _metrics_ctx.reset(token)


def record_result_message(message: Any) -> None:
    """active scope への ResultMessage 集計

    Args:
        message: SDK の ResultMessage 相当オブジェクト
    """
    acc = _metrics_ctx.get()
    if acc is not None:
        acc.record_result_message(message)

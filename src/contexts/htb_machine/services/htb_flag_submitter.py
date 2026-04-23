from __future__ import annotations

from collections.abc import Awaitable, Callable

from ..domain import HtbAttempt, OwnType

HtbFlagSubmitter = Callable[[OwnType, str], Awaitable[HtbAttempt]]

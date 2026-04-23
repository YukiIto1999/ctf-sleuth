from __future__ import annotations

from collections.abc import Awaitable, Callable

from ..domain import SolveAttempt

FlagSubmitter = Callable[[str, str], Awaitable[SolveAttempt]]

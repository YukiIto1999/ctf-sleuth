from __future__ import annotations

import logging

from shared.errors import MissingRequiredParamError
from shared.result import FindingsCollected
from shared.task import ExecutionRequest

from .investigate import Investigator
from .policies import classify_target

logger = logging.getLogger(__name__)


async def run_osint_investigation(request: ExecutionRequest) -> FindingsCollected:
    """osint_investigation の実行エントリ

    Args:
        request: 実行要求

    Returns:
        Investigator 由来の FindingsCollected

    Raises:
        MissingRequiredParamError: target が未指定
    """
    raw = str(request.params.get("target") or request.input.raw).strip()
    if not raw:
        raise MissingRequiredParamError(("target",))

    target = classify_target(raw)
    logger.info("OSINT target: kind=%s raw=%r", target.kind.value, target.raw)

    investigator = Investigator(
        target=target,
        model_spec=request.model_spec,
    )
    return await investigator.investigate()

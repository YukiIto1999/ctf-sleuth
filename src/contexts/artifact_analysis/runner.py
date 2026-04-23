from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from shared.errors import MissingRequiredParamError
from shared.result import AnalysisReport
from shared.sandbox import Sandbox
from shared.task import ExecutionRequest

from .analyze import Analyzer
from .domain import Artifact
from .services import ArtifactInspector

logger = logging.getLogger(__name__)

CONTAINER_ARTIFACT_DIR = "/artifact"

ArtifactSandboxFactory = Callable[[Artifact, str], Sandbox]


async def run_artifact_analysis(
    request: ExecutionRequest,
    *,
    artifact_inspector: ArtifactInspector,
    sandbox_factory: ArtifactSandboxFactory,
) -> AnalysisReport:
    """artifact_analysis の実行エントリ

    Args:
        request: 実行要求
        artifact_inspector: ファイルパスから Artifact を生成する observer
        sandbox_factory: Artifact と container 内パスから Sandbox を生成するファクトリ

    Returns:
        Analyzer 由来の AnalysisReport
    """
    artifact_path = _artifact_path_from_request(request)
    artifact = artifact_inspector(artifact_path)

    container_path = f"{CONTAINER_ARTIFACT_DIR}/{artifact.filename()}"
    sandbox = sandbox_factory(artifact, container_path)

    try:
        await sandbox.start()
        analyzer = Analyzer(
            artifact=artifact,
            sandbox=sandbox,
            container_path=container_path,
            model_spec=request.model_spec,
        )
        return await analyzer.analyze()
    finally:
        try:
            await sandbox.stop()
        except Exception as e:  # noqa: BLE001
            logger.warning("sandbox.stop() failed: %s", e)


def _artifact_path_from_request(request: ExecutionRequest) -> Path:
    """ExecutionRequest からの artifact パス解決

    Args:
        request: 実行要求

    Returns:
        存在確認済のファイルパス

    Raises:
        MissingRequiredParamError: パスが未指定
        FileNotFoundError: 指定パスの不在
        ValueError: 通常ファイルではないパス
    """
    raw = request.params.get("path") or request.input.raw.strip()
    if not raw:
        raise MissingRequiredParamError(("path",))
    path = Path(str(raw))
    if not path.exists():
        raise FileNotFoundError(f"artifact not found: {path}")
    if not path.is_file():
        raise ValueError(f"artifact is not a regular file: {path}")
    return path

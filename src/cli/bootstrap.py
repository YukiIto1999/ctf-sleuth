from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from functools import partial
from pathlib import Path

from contexts.artifact_analysis import run_artifact_analysis
from contexts.artifact_analysis.domain import Artifact
from contexts.ctf_challenge import run_ctf_challenge
from contexts.ctf_challenge.domain import Challenge
from contexts.ctf_challenge.services import CtfdGateway
from contexts.htb_machine import run_htb_machine
from contexts.htb_machine.services import HtbGateway
from contexts.osint_investigation import run_osint_investigation
from layers.artifact_inspector import inspect_artifact
from layers.ctfd import CtfdClient, CtfdConfig
from layers.htb import HtbClient, HtbConfig
from layers.sandbox import DockerSandbox, SandboxConfig
from shared.result import TaskResult
from shared.sandbox import MountSpec, Sandbox
from shared.task import ExecutionRequest, TaskType
from workflows.dispatch import DispatchConfig

TaskRunner = Callable[[ExecutionRequest], Awaitable[TaskResult]]

DEFAULT_SANDBOX_IMAGE = "ctf-sandbox"
DEFAULT_CHALLENGES_DIR = Path("challenges")


def make_runners(
    *,
    sandbox_image: str = DEFAULT_SANDBOX_IMAGE,
    challenges_dir: Path = DEFAULT_CHALLENGES_DIR,
) -> dict[TaskType, TaskRunner]:
    """TaskType 別 runner の組立

    Args:
        sandbox_image: sandbox に使う Docker image 名
        challenges_dir: challenge 永続化先ディレクトリ

    Returns:
        TaskType から runner 関数への不変写像
    """
    return {
        TaskType.CTF_CHALLENGE: partial(
            run_ctf_challenge,
            ctfd_factory=_ctfd_factory,
            sandbox_factory=partial(_ctf_sandbox_factory, image=sandbox_image),
            challenges_dir=challenges_dir,
        ),
        TaskType.HTB_MACHINE: partial(
            run_htb_machine,
            htb_factory=_htb_factory,
            sandbox_factory=partial(_htb_sandbox_factory, image=sandbox_image),
        ),
        TaskType.ARTIFACT_ANALYSIS: partial(
            run_artifact_analysis,
            artifact_inspector=inspect_artifact,
            sandbox_factory=partial(_artifact_sandbox_factory, image=sandbox_image),
        ),
        TaskType.OSINT_INVESTIGATION: run_osint_investigation,
    }


def make_config(non_interactive: bool) -> DispatchConfig:
    """DispatchConfig の組立

    Args:
        non_interactive: 対話無効化フラグ

    Returns:
        interactive 反転済の DispatchConfig
    """
    return DispatchConfig(interactive=not non_interactive)


def _ctfd_factory(url: str, token: str) -> AbstractAsyncContextManager[CtfdGateway]:
    """CTFd ゲートウェイの生成

    Args:
        url: CTFd base URL
        token: API token

    Returns:
        CtfdClient の async context manager
    """
    return CtfdClient(CtfdConfig(base_url=url, token=token))


def _htb_factory(token: str) -> AbstractAsyncContextManager[HtbGateway]:
    """HTB ゲートウェイの生成

    Args:
        token: HTB API token

    Returns:
        HtbClient の async context manager
    """
    return HtbClient(HtbConfig(token=token))


def _ctf_sandbox_factory(challenge: Challenge, challenges_dir: Path, *, image: str) -> Sandbox:
    """ctf_challenge 用 Sandbox の生成

    Args:
        challenge: 対象 Challenge
        challenges_dir: challenge 永続化ディレクトリ
        image: 使用 Docker image 名

    Returns:
        mount 付きの DockerSandbox
    """
    ch_dir = challenges_dir / challenge.slug()
    mounts: list[MountSpec] = []
    distfiles = ch_dir / "distfiles"
    if distfiles.exists():
        mounts.append(MountSpec(source=distfiles.resolve(), target="/challenge/distfiles", read_only=True))
    metadata = ch_dir / "metadata.yml"
    if metadata.exists():
        mounts.append(MountSpec(source=metadata.resolve(), target="/challenge/metadata.yml", read_only=True))
    config = SandboxConfig(image=image, mounts=tuple(mounts))
    return DockerSandbox(config)


def _htb_sandbox_factory(*, image: str) -> Sandbox:
    """htb_machine 用 Sandbox の生成

    Args:
        image: 使用 Docker image 名

    Returns:
        mount なしの DockerSandbox
    """
    return DockerSandbox(SandboxConfig(image=image, mounts=()))


def _artifact_sandbox_factory(artifact: Artifact, container_path: str, *, image: str) -> Sandbox:
    """artifact_analysis 用 Sandbox の生成

    Args:
        artifact: 対象 Artifact
        container_path: container 内 artifact 絶対パス
        image: 使用 Docker image 名

    Returns:
        read-only mount 付き DockerSandbox
    """
    mounts = (MountSpec(source=artifact.path, target=container_path, read_only=True),)
    return DockerSandbox(SandboxConfig(image=image, mounts=mounts))

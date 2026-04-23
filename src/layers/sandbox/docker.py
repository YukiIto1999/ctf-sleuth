from __future__ import annotations

import asyncio
import io
import logging
import shlex
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shared.sandbox import ExecResult

from .config import SandboxConfig
from .errors import SandboxNotStartedError, SandboxStartupError

logger = logging.getLogger(__name__)


@dataclass
class DockerSandbox:
    """aiodocker を使う Sandbox 実装

    Attributes:
        config: 起動設定
    """

    config: SandboxConfig
    _container: Any = field(default=None, init=False, repr=False)
    _docker: Any = field(default=None, init=False, repr=False)
    _workspace_host_dir: str = field(default="", init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    @property
    def container_id(self) -> str:
        """起動中 container の ID

        Returns:
            docker が払い出した container ID

        Raises:
            SandboxNotStartedError: 未起動時の参照
        """
        if not self._container:
            raise SandboxNotStartedError("DockerSandbox.start() not called")
        return self._container.id

    async def start(self) -> None:
        """container 起動と workspace 確保

        Raises:
            SandboxStartupError: aiodocker 未導入もしくは container 起動失敗
        """
        try:
            import aiodocker
        except ImportError as e:
            raise SandboxStartupError("aiodocker not installed") from e

        self._docker = aiodocker.Docker()
        self._workspace_host_dir = tempfile.mkdtemp(prefix="ctf-workspace-")

        binds = [
            f"{self._workspace_host_dir}:/challenge/workspace:rw",
            *(m.as_bind() for m in self.config.mounts),
        ]
        docker_config = {
            "Image": self.config.image,
            "Cmd": list(self.config.command),
            "WorkingDir": self.config.working_dir,
            "Tty": False,
            "Labels": {self.config.label: "true"},
            "HostConfig": {
                "Binds": binds,
                "ExtraHosts": [f"{host}:{target}" for host, target in self.config.extra_hosts.items()],
                "CapAdd": list(self.config.cap_add),
                "SecurityOpt": list(self.config.security_opt),
                "Memory": self.config.memory_limit_bytes,
                "NanoCpus": self.config.cpu_nanocpus,
            },
        }

        try:
            self._container = await self._docker.containers.create(docker_config)
            await self._container.start()
        except Exception as e:
            await self._cleanup_docker_client()
            raise SandboxStartupError(f"container start failed: {e}") from e

        logger.info("sandbox started: %s", self._container.id[:12])

    async def exec(self, command: str, *, timeout_seconds: int = 300) -> ExecResult:
        """container 内コマンド実行

        Args:
            command: 実行対象コマンド
            timeout_seconds: タイムアウト秒数

        Returns:
            実行結果の ExecResult

        Raises:
            SandboxNotStartedError: 未起動時の呼出
        """
        if not self._container:
            raise SandboxNotStartedError("DockerSandbox.start() not called")

        async with self._lock:
            return await self._exec_inner(command, timeout_seconds)

    async def _exec_inner(self, command: str, timeout_s: int) -> ExecResult:
        """Lock 取得済の内側 exec 処理

        Args:
            command: 実行対象コマンド
            timeout_s: タイムアウト秒数

        Returns:
            実行結果の ExecResult
        """
        import aiodocker

        wrapped = f"timeout --signal=KILL --kill-after=5 {timeout_s} bash -c {shlex.quote(command)}"
        try:
            exec_instance = await self._container.exec(
                cmd=["bash", "-c", wrapped],
                stdout=True,
                stderr=True,
                tty=False,
            )
        except aiodocker.exceptions.DockerError as e:
            return ExecResult(exit_code=-1, stdout="", stderr=f"container gone: {e}")

        stream = exec_instance.start(detach=False)
        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []

        async def _collect() -> None:
            """exec ストリームの収集ループ"""
            while True:
                msg = await stream.read_out()
                if msg is None:
                    break
                if msg.stream == 1:
                    stdout_chunks.append(msg.data)
                else:
                    stderr_chunks.append(msg.data)

        try:
            await asyncio.wait_for(_collect(), timeout=timeout_s + 30)
        except TimeoutError:
            try:
                await stream.close()
            except Exception:
                pass
            return ExecResult(
                exit_code=-1,
                stdout=b"".join(stdout_chunks).decode("utf-8", errors="replace"),
                stderr="command timed out",
                timed_out=True,
            )

        inspect = await exec_instance.inspect()
        exit_code = inspect.get("ExitCode", 0) or 0
        return ExecResult(
            exit_code=exit_code,
            stdout=b"".join(stdout_chunks).decode("utf-8", errors="replace"),
            stderr=b"".join(stderr_chunks).decode("utf-8", errors="replace"),
        )

    async def read_file(self, path: str) -> bytes:
        """container 内ファイルの tar 経由読取

        Args:
            path: container 内絶対パス

        Returns:
            ファイルの生バイト列

        Raises:
            SandboxNotStartedError: 未起動時の呼出
            TimeoutError: 取得が所定時間内に終わらない場合
            FileNotFoundError: 該当ファイルの不在
        """
        if not self._container:
            raise SandboxNotStartedError("DockerSandbox.start() not called")
        try:
            tar = await asyncio.wait_for(self._container.get_archive(path), timeout=30)
        except TimeoutError as e:
            raise TimeoutError(f"timed out reading {path}") from e

        with tar:
            for member in tar:
                if member.isfile():
                    f = tar.extractfile(member)
                    if f:
                        return f.read()
        raise FileNotFoundError(path)

    async def write_file(self, path: str, content: bytes | str) -> None:
        """container 内ファイルへの tar 経由書込

        Args:
            path: container 内絶対パス
            content: 書込内容

        Raises:
            SandboxNotStartedError: 未起動時の呼出
            TimeoutError: 所定時間内に put が終わらない場合
        """
        if not self._container:
            raise SandboxNotStartedError("DockerSandbox.start() not called")
        if isinstance(content, str):
            content = content.encode("utf-8")

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            info = tarfile.TarInfo(name=Path(path).name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
        buf.seek(0)

        try:
            await asyncio.wait_for(
                self._container.put_archive(str(Path(path).parent), buf.getvalue()),
                timeout=30,
            )
        except TimeoutError as e:
            raise TimeoutError(f"timed out writing {path}") from e

    async def stop(self) -> None:
        """container の停止と workspace 撤去"""
        if self._container is not None:
            try:
                await self._container.delete(force=True)
            except Exception:
                pass
            self._container = None

        await self._cleanup_docker_client()

        if self._workspace_host_dir:
            import shutil

            shutil.rmtree(self._workspace_host_dir, ignore_errors=True)
            self._workspace_host_dir = ""
        logger.info("sandbox stopped")

    async def _cleanup_docker_client(self) -> None:
        """aiodocker クライアントのクローズ"""
        if self._docker is not None:
            try:
                await self._docker.close()
            except Exception:
                pass
            self._docker = None

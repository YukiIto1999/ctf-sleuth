from __future__ import annotations

from collections.abc import Callable

from shared.sandbox import ExecResult

from .errors import SandboxNotStartedError

ExecHandler = Callable[[str, int], ExecResult]


class StubSandbox:
    """テスト用の in-memory Sandbox 実装"""

    def __init__(
        self,
        *,
        exec_handler: ExecHandler | None = None,
        files: dict[str, bytes] | None = None,
    ) -> None:
        """Stub sandbox の初期化

        Args:
            exec_handler: コマンド入力に対する ExecResult 返却関数
            files: 事前配置するファイル
        """
        self._started = False
        self._stopped = False
        self._exec_handler = exec_handler or (lambda cmd, timeout: ExecResult(0, "", ""))
        self._files: dict[str, bytes] = dict(files or {})
        self.exec_calls: list[tuple[str, int]] = []

    @property
    def container_id(self) -> str:
        """stub 用の固定 container ID

        Returns:
            固定文字列 stub-container

        Raises:
            SandboxNotStartedError: 未起動状態での参照
        """
        if not self._started:
            raise SandboxNotStartedError("StubSandbox.start() not called")
        return "stub-container"

    async def start(self) -> None:
        """stub の起動状態化"""
        self._started = True

    async def exec(self, command: str, *, timeout_seconds: int = 300) -> ExecResult:
        """事前定義ハンドラによる擬似実行

        Args:
            command: 実行対象コマンド
            timeout_seconds: タイムアウト秒数

        Returns:
            ハンドラが返す ExecResult

        Raises:
            SandboxNotStartedError: 未起動時の呼出
        """
        if not self._started:
            raise SandboxNotStartedError("StubSandbox not started")
        self.exec_calls.append((command, timeout_seconds))
        return self._exec_handler(command, timeout_seconds)

    async def read_file(self, path: str) -> bytes:
        """in-memory ファイルの読取

        Args:
            path: ファイルパス

        Returns:
            保持しているバイト列

        Raises:
            SandboxNotStartedError: 未起動時の呼出
            FileNotFoundError: 該当ファイルの不在
        """
        if not self._started:
            raise SandboxNotStartedError("StubSandbox not started")
        if path not in self._files:
            raise FileNotFoundError(path)
        return self._files[path]

    async def write_file(self, path: str, content: bytes | str) -> None:
        """in-memory ファイルへの書込

        Args:
            path: ファイルパス
            content: 書込内容

        Raises:
            SandboxNotStartedError: 未起動時の呼出
        """
        if not self._started:
            raise SandboxNotStartedError("StubSandbox not started")
        if isinstance(content, str):
            content = content.encode("utf-8")
        self._files[path] = content

    async def stop(self) -> None:
        """stub の停止フラグ設定"""
        self._stopped = True

from __future__ import annotations

from typing import Protocol

from .exec_result import ExecResult


class Sandbox(Protocol):
    """sandbox 契約の Protocol"""

    async def start(self) -> None:
        """container の起動"""
        ...

    async def exec(self, command: str, *, timeout_seconds: int = 300) -> ExecResult:
        """container 内コマンド実行

        Args:
            command: 実行するシェルコマンド
            timeout_seconds: タイムアウト秒数

        Returns:
            実行結果の ExecResult
        """
        ...

    async def read_file(self, path: str) -> bytes:
        """container 内ファイルの読取

        Args:
            path: container 内の絶対パス

        Returns:
            ファイルの生バイト列
        """
        ...

    async def write_file(self, path: str, content: bytes | str) -> None:
        """container 内ファイルへの書込

        Args:
            path: container 内の絶対パス
            content: 書込内容
        """
        ...

    async def stop(self) -> None:
        """container の停止と片付け"""
        ...

    @property
    def container_id(self) -> str:
        """起動中 container の ID"""
        ...

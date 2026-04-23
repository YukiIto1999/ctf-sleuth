from __future__ import annotations

import pytest

from layers.sandbox import SandboxNotStartedError, StubSandbox
from shared.sandbox import ExecResult


class TestStubSandbox:
    """StubSandbox の挙動検証"""

    @pytest.mark.asyncio
    async def test_start_enables_exec(self) -> None:
        """start 後の exec 可能化"""
        s = StubSandbox()
        await s.start()
        r = await s.exec("ls")
        assert r.exit_code == 0

    @pytest.mark.asyncio
    async def test_exec_before_start_raises(self) -> None:
        """未 start exec の例外"""
        s = StubSandbox()
        with pytest.raises(SandboxNotStartedError):
            await s.exec("ls")

    @pytest.mark.asyncio
    async def test_exec_records_calls(self) -> None:
        """exec 呼出履歴の記録"""
        s = StubSandbox()
        await s.start()
        await s.exec("pwd", timeout_seconds=10)
        await s.exec("ls -l", timeout_seconds=30)
        assert s.exec_calls == [("pwd", 10), ("ls -l", 30)]

    @pytest.mark.asyncio
    async def test_exec_handler_can_return_custom(self) -> None:
        """exec_handler による挙動差替"""
        s = StubSandbox(
            exec_handler=lambda cmd, t: ExecResult(
                exit_code=42, stdout=f"ran {cmd}", stderr=""
            ),
        )
        await s.start()
        r = await s.exec("echo hi")
        assert r.exit_code == 42
        assert r.stdout == "ran echo hi"

    @pytest.mark.asyncio
    async def test_write_read_roundtrip(self) -> None:
        """in-memory ファイルの write と read"""
        s = StubSandbox()
        await s.start()
        await s.write_file("/tmp/x", "hello")
        assert await s.read_file("/tmp/x") == b"hello"

    @pytest.mark.asyncio
    async def test_read_missing_raises(self) -> None:
        """不在ファイル read の FileNotFoundError"""
        s = StubSandbox()
        await s.start()
        with pytest.raises(FileNotFoundError):
            await s.read_file("/nowhere")

    @pytest.mark.asyncio
    async def test_container_id_requires_start(self) -> None:
        """未 start container_id 参照の例外"""
        s = StubSandbox()
        with pytest.raises(SandboxNotStartedError):
            _ = s.container_id

    @pytest.mark.asyncio
    async def test_stop_marks_stopped(self) -> None:
        """stop の冪等性"""
        s = StubSandbox()
        await s.start()
        await s.stop()
        await s.stop()

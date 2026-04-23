from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExecResult:
    """container 内コマンド実行結果

    Attributes:
        exit_code: 終了コード
        stdout: 標準出力
        stderr: 標準エラー
        timed_out: タイムアウト判定フラグ
    """

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

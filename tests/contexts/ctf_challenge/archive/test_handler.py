from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from contexts.ctf_challenge.archive import list_distfiles, persist_challenges
from contexts.ctf_challenge.domain import (
    Challenge,
    ChallengeId,
    ChallengeSet,
    Hint,
)
from shared.task import Strategy


class _FakeCtfd:
    """distfile 取得を記録する偽 CtfdClient"""

    def __init__(self, files: dict[str, bytes]) -> None:
        """偽クライアントの初期化

        Args:
            files: URL から bytes への写像
        """
        self._files = files
        self.download_calls: list[str] = []

    async def download_distfile(self, url: str) -> bytes:
        """記録付き擬似ダウンロード

        Args:
            url: 取得対象 URL

        Returns:
            事前登録のバイト列

        Raises:
            FileNotFoundError: 未登録 URL
        """
        self.download_calls.append(url)
        if url not in self._files:
            raise FileNotFoundError(url)
        return self._files[url]


def _ch(
    id_: int,
    name: str,
    *,
    distfile_urls: tuple[str, ...] = (),
    hints: tuple[Hint, ...] = (),
) -> Challenge:
    """テスト用 Challenge の生成

    Args:
        id_: challenge ID
        name: challenge 名
        distfile_urls: distfile URL のタプル
        hints: Hint のタプル

    Returns:
        Pwn 固定の Challenge
    """
    return Challenge(
        id=ChallengeId(id_),
        name=name,
        category_raw="Pwn",
        strategy=Strategy.PWN,
        description="desc",
        value=100,
        connection_info="nc host 1234",
        tags=("warmup",),
        hints=hints,
        distfile_urls=distfile_urls,
    )


@pytest.mark.asyncio
async def test_persist_writes_metadata_and_distfiles(tmp_path: Path) -> None:
    """metadata と distfile の書出

    Args:
        tmp_path: pytest tmp_path fixture
    """
    ctfd = _FakeCtfd({"/files/abc/binary": b"\x7fELF..."})
    cs = ChallengeSet(
        challenges=(
            _ch(
                1,
                "pwn-baby",
                distfile_urls=("/files/abc/binary",),
                hints=(Hint("try strings", 0),),
            ),
        )
    )

    dirs = await persist_challenges(ctfd, cs, tmp_path)
    assert len(dirs) == 1
    ch_dir = dirs[0]
    assert ch_dir == tmp_path / "pwn-baby"

    meta = yaml.safe_load((ch_dir / "metadata.yml").read_text())
    assert meta["name"] == "pwn-baby"
    assert meta["id"] == 1
    assert meta["strategy"] == "pwn"
    assert meta["tags"] == ["warmup"]
    assert meta["hints"] == [{"content": "try strings", "cost": 0}]

    binary = ch_dir / "distfiles" / "binary"
    assert binary.exists()
    assert binary.read_bytes().startswith(b"\x7fELF")


@pytest.mark.asyncio
async def test_persist_is_idempotent_for_distfiles(tmp_path: Path) -> None:
    """再実行時の distfile 再ダウンロード回避

    Args:
        tmp_path: pytest tmp_path fixture
    """
    ctfd = _FakeCtfd({"/files/a/binary": b"first"})
    cs = ChallengeSet(challenges=(_ch(1, "x", distfile_urls=("/files/a/binary",)),))

    await persist_challenges(ctfd, cs, tmp_path)
    assert ctfd.download_calls == ["/files/a/binary"]

    await persist_challenges(ctfd, cs, tmp_path)
    assert ctfd.download_calls == ["/files/a/binary"]


@pytest.mark.asyncio
async def test_persist_handles_download_failure_gracefully(tmp_path: Path) -> None:
    """ダウンロード失敗時の部分成功

    Args:
        tmp_path: pytest tmp_path fixture
    """

    class _FailingCtfd:
        """常にネットワーク失敗を返す偽 CtfdClient"""

        async def download_distfile(self, url: str) -> bytes:
            """例外送出の擬似ダウンロード

            Args:
                url: 無視される URL

            Raises:
                RuntimeError: 常に送出
            """
            raise RuntimeError("network down")

    cs = ChallengeSet(challenges=(_ch(1, "x", distfile_urls=("/files/a/binary",)),))
    dirs = await persist_challenges(_FailingCtfd(), cs, tmp_path)
    assert (dirs[0] / "metadata.yml").exists()
    assert not (dirs[0] / "distfiles" / "binary").exists()


def test_list_distfiles(tmp_path: Path) -> None:
    """distfile 一覧のソート済取得

    Args:
        tmp_path: pytest tmp_path fixture
    """
    ch_dir = tmp_path / "ch"
    distfiles = ch_dir / "distfiles"
    distfiles.mkdir(parents=True)
    (distfiles / "b.bin").write_bytes(b"")
    (distfiles / "a.txt").write_bytes(b"")
    (distfiles / "sub").mkdir()
    assert list_distfiles(ch_dir) == ("a.txt", "b.bin")


def test_list_distfiles_missing_returns_empty(tmp_path: Path) -> None:
    """distfile ディレクトリ不在時の空タプル

    Args:
        tmp_path: pytest tmp_path fixture
    """
    assert list_distfiles(tmp_path / "missing") == ()

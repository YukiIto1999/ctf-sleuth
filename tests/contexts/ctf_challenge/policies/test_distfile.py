from __future__ import annotations

from contexts.ctf_challenge.policies import filename_from_url


class TestFilenameFromUrl:
    """filename_from_url の挙動検証"""

    def test_extracts_last_segment(self) -> None:
        """末尾パス要素の抽出"""
        assert filename_from_url("/files/abc/binary") == "binary"

    def test_handles_absolute_url(self) -> None:
        """絶対 URL の末尾抽出"""
        assert filename_from_url("https://ctf.example.com/files/x/bin.tar.gz") == "bin.tar.gz"

    def test_empty_path_falls_back_to_file(self) -> None:
        """パス空時の file fallback"""
        assert filename_from_url("/") == "file"

    def test_strips_unsafe_chars(self) -> None:
        """危険文字の除去"""
        assert filename_from_url("/files/with:bad*chars.bin") == "withbadchars.bin"

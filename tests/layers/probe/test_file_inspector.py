from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from layers.probe.file_inspector import detect_file_kind
from shared.probe import FileKind


class TestDetectFileKind:
    """detect_file_kind のマジックバイト判定"""

    @pytest.mark.parametrize(
        "magic, expected",
        [
            (b"\x7fELF\x02\x01\x01", FileKind.ELF),
            (b"MZ\x90\x00", FileKind.PE),
            (b"\xcf\xfa\xed\xfe", FileKind.MACH_O),
            (b"\xd4\xc3\xb2\xa1\x02\x00", FileKind.PCAP),
            (b"\x0a\x0d\x0d\x0a" + b"\x00" * 10, FileKind.PCAPNG),
            (b"%PDF-1.4", FileKind.PDF),
            (b"PK\x03\x04", FileKind.ARCHIVE),
            (b"\x89PNG\r\n", FileKind.IMAGE),
            (b"GIF89a", FileKind.IMAGE),
            (b"RIFF....WAVE", FileKind.AUDIO),
        ],
    )
    def test_detects_known_magic(
        self, tmp_path: Path, magic: bytes, expected: FileKind
    ) -> None:
        """既知マジックの識別

        Args:
            tmp_path: pytest tmp_path fixture
            magic: 先頭バイト列
            expected: 期待 FileKind
        """
        p = tmp_path / "x"
        p.write_bytes(magic)
        assert detect_file_kind(p) == expected

    def test_unknown_binary_returns_unknown(self, tmp_path: Path) -> None:
        """未知 binary マジックの UNKNOWN 返却

        Args:
            tmp_path: pytest tmp_path fixture
        """
        p = tmp_path / "x"
        p.write_bytes(b"\x00\x01\xff\xfe\x02\x03\x04\x05")
        assert detect_file_kind(p) == FileKind.UNKNOWN

    def test_ascii_text_returns_text(self, tmp_path: Path) -> None:
        """印字可能 ASCII の TEXT 判定

        Args:
            tmp_path: pytest tmp_path fixture
        """
        p = tmp_path / "x"
        p.write_bytes(b"just random text")
        assert detect_file_kind(p) == FileKind.TEXT

    def test_empty_file_returns_unknown(self, tmp_path: Path) -> None:
        """空ファイルの UNKNOWN 返却

        Args:
            tmp_path: pytest tmp_path fixture
        """
        p = tmp_path / "empty"
        p.write_bytes(b"")
        assert detect_file_kind(p) == FileKind.UNKNOWN

    def test_zip_with_android_manifest_returns_apk(self, tmp_path: Path) -> None:
        """ZIP 内に AndroidManifest.xml があれば APK と判定

        Args:
            tmp_path: pytest tmp_path fixture
        """
        p = tmp_path / "app.apk"
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr("AndroidManifest.xml", b"\x03\x00\x08\x00")
            zf.writestr("classes.dex", b"dex\n035\x00")
        assert detect_file_kind(p) == FileKind.APK

    def test_zip_with_ios_payload_returns_ipa(self, tmp_path: Path) -> None:
        """ZIP 内に Payload/<name>.app/Info.plist があれば IPA と判定

        Args:
            tmp_path: pytest tmp_path fixture
        """
        p = tmp_path / "app.ipa"
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr("Payload/MyApp.app/Info.plist", b"<plist/>")
        assert detect_file_kind(p) == FileKind.IPA

    def test_plain_zip_returns_archive(self, tmp_path: Path) -> None:
        """通常 ZIP は ARCHIVE のまま

        Args:
            tmp_path: pytest tmp_path fixture
        """
        p = tmp_path / "x.zip"
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr("hello.txt", b"hi")
        assert detect_file_kind(p) == FileKind.ARCHIVE

    @pytest.mark.parametrize(
        "magic",
        [
            b"hsqs\x00\x00\x00\x00",
            b"sqsh\x00\x00\x00\x00",
            b"UBI#\x00\x00\x00\x00",
            b"\x27\x05\x19\x56",
            b"\x1f\x8b\x08\x00",
        ],
    )
    def test_firmware_magic_returns_firmware(self, tmp_path: Path, magic: bytes) -> None:
        """firmware 系マジックの FIRMWARE 判定

        Args:
            tmp_path: pytest tmp_path fixture
            magic: firmware 種別のマジック
        """
        p = tmp_path / "fw.bin"
        p.write_bytes(magic)
        assert detect_file_kind(p) == FileKind.FIRMWARE

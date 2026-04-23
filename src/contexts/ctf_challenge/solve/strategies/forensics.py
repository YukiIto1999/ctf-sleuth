from __future__ import annotations

from .hints import StrategyHints

HINTS = StrategyHints(
    skill_names=(
        # methodology
        "dfir",
        "blue-teamer",
        "essential-tools",
        # memory
        "memory-analysis",
        # disk / filesystem
        "disk-forensics",
        # log
        "endpoint-forensics",
        # container
        "container-forensics",
        # network forensics (詳細は network-analyzer)
        "network-analyzer",
        "network-hunter",
        "performing-ssl-tls-security-assessment",
        "network-analyzer",
        "replay-attack",
        # cloud forensics
        "cloud-forensics",
        "detection-cloud-anomalies",
        # malware-flavored forensics
        "ioc-hunting",
        "rootkit-analysis",
        # AD / windows lateral
        "system",
        "detecting-kerberoasting-attacks",
    ),
    tool_focus=(
        "volatility3",
        "wireshark",
        "tshark",
        "binwalk",
        "foremost",
        "exiftool",
        "steghide",
        "zsteg",
        "autopsy",
        "sleuthkit",
        "tesseract",
    ),
    prompt_section=(
        "## Forensics strategy\n\n"
        "1. artefact の種別判定 → 先頭マジックを確認 (`file`, `xxd | head`).\n"
        "2. 画像: `exiftool`, `strings`, `steghide extract`, `zsteg`, `binwalk -e`.\n"
        "3. PCAP: `tshark -r` で protocol ごとに filter (`-Y http`, `-Y dns`).\n"
        "4. Memory: `volatility3 -f dump.raw windows.pslist` → malfind, dumpfiles.\n"
        "5. Disk image: `fls`, `icat`, `mmls` (sleuthkit); carving は `foremost`.\n"
        "6. OCR が必要なら `tesseract image.png stdout`.\n"
        "7. タイムスタンプは UTC に揃える. AM/PM の罠に注意 (12AM=00:XX)."
    ),
)

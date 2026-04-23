from __future__ import annotations

from .hints import StrategyHints

HINTS = StrategyHints(
    skill_names=(
        # general rev (variant 別深掘りは references/ 内)
        "reverse-engineering",
        "source-code-scanning",
        "essential-tools",
        # kernel / rootkit / firmware
        "rootkit-analysis",
        "firmware-iot-security",
        # mobile
        "android-security",
        "ios-security",
        # malware-flavored rev
        "ioc-hunting",
    ),
    tool_focus=(
        "ghidra",
        "radare2",
        "objdump",
        "strings",
        "ltrace",
        "strace",
        "angr",
        "capstone",
    ),
    prompt_section=(
        "## Reverse engineering strategy\n\n"
        "1. `file`, `strings -n 8`, `readelf -a`, `objdump -d` で素性確認.\n"
        "2. UPX 等で packed なら `upx -d`. 検知は `file` 出力か `strings` の偏り.\n"
        "3. ghidra を headless で起動して decompile 結果を取得 (pyghidra 使用可).\n"
        "4. 対称鍵や XOR key は `entropy` 解析や文字列相関で特定.\n"
        "5. 動的解析が必要なら qemu-user, gdb, strace, ltrace を使う.\n"
        "6. angr で symbolic execution (小さい binary に限定)."
    ),
)

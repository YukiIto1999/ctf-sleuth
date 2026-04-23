from __future__ import annotations

from .hints import StrategyHints

HINTS = StrategyHints(
    skill_names=(
        # core exploit / rev
        "cve-exploitation",
        "reverse-engineering",
        # heap / spray (memory-analysis の references/heap-spray.md で深掘り想定)
        "memory-analysis",
        # kernel / rootkit class problems
        "rootkit-analysis",
        # firmware-flavored pwn
        "firmware-iot-security",
        # tooling
        "essential-tools",
        "patt-fetcher",
        "script-generator",
    ),
    tool_focus=(
        "pwntools",
        "gdb",
        "radare2",
        "angr",
        "ROPgadget",
        "one_gadget",
    ),
    prompt_section=(
        "## Pwn strategy\n\n"
        "1. `checksec` (pwntools) で保護状況を把握 (NX / PIE / Canary / RELRO).\n"
        "2. `strings`, `ghidra --headless`, `radare2 -A` で制御フローを掴む.\n"
        "3. libc leak → `ret2libc` / `ret2system`; No leak → `ROP` chain.\n"
        "4. heap 系は glibc バージョン確認 (`ldd`), tcache/fastbin を確認.\n"
        "5. `stty raw -echo` を nc の前に置く (TTY echo で壊れるため).\n"
        "6. exploit 開発は pwntools: `from pwn import *; p = remote(host, port)` → "
        "offset 特定 → payload 組立 → `p.interactive()`."
    ),
)

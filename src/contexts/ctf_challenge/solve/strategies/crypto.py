from __future__ import annotations

from .hints import StrategyHints

HINTS = StrategyHints(
    skill_names=(
        # core crypto
        "performing-cryptographic-audit-of-application",
        "phishing-investigation",
        # JWT / token-cryptography (overlap with web)
        "testing-jwt-token-security",
        # blockchain / smart-contract
        "blockchain-security",
        # ransomware crypto reverse
        "reverse-engineering",
        # tooling
        "essential-tools",
        "script-generator",
    ),
    tool_focus=(
        "sage",
        "pycryptodome",
        "gmpy2",
        "z3-solver",
        "fpylll",
        "RsaCtfTool",
        "cado-nfs",
        "hashcat",
    ),
    prompt_section=(
        "## Crypto strategy\n\n"
        "1. 暗号種別を特定: 対称 (AES/ChaCha) / 非対称 (RSA/ECC) / hash / stream.\n"
        "2. RSA は `RsaCtfTool -n N -e E --attack all`. 大合成数は `cado-nfs` / `ecm`.\n"
        "3. AES は mode 確認 (ECB パターン, CBC padding oracle, CTR nonce 再利用).\n"
        "4. ECC は weak curve, invalid curve, small subgroup, nonce reuse (ECDSA).\n"
        "5. 格子: `fpylll` / sage の `LLL`, Coppersmith 系は sage が定番.\n"
        "6. PRNG 復元: LCG / MT19937 state recovery.\n"
        "7. CyberChef で簡単なエンコーディング (base64, URL, hex, rot) を一気に通す."
    ),
)

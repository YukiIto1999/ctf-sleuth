from __future__ import annotations

from .hints import StrategyHints

HINTS = StrategyHints(
    skill_names=(
        # methodology
        "web-pentester",
        "api-security",
        "web-app-logic",
        "authentication",
        "client-side",
        "server-side",
        "techstack-identification",
        "essential-tools",
        # injection family
        "injection",
        # auth / token
        "testing-jwt-token-security",
        "testing-oauth2-implementation-flaws",
        # defensive understanding (often informs attack vectors)
        "detection-web",
        # AI / LLM CTF
        "ai-threat-testing",
        # bug bounty cross-pollination
        "bug-bounter",
        "web-bounty",
        "patt-fetcher",
    ),
    tool_focus=(
        "curl",
        "requests",
        "ffuf",
        "gobuster",
        "sqlmap",
        "nuclei",
        "burp",
        "jwt_tool",
    ),
    prompt_section=(
        "## Web strategy\n\n"
        "1. `curl -sI` でヘッダ確認 (server, cookies, CSP, auth scheme).\n"
        "2. `/robots.txt`, `/sitemap.xml`, `/.git/HEAD`, `/api`, `/.env` の初手確認.\n"
        "3. `ffuf -u URL/FUZZ -w wordlist -mc all -fs <default_size>` で列挙.\n"
        "4. JWT: alg 混乱攻撃, kid injection, 弱鍵 HMAC; `jwt_tool` が便利.\n"
        "5. SQL 注入: `sqlmap` は基本. 手動なら UNION / time-based を試す.\n"
        "6. SSRF: gopher, file, internal cloud metadata (169.254.169.254).\n"
        "7. 認証フローの business logic (race, state, MFA bypass) も検討."
    ),
)

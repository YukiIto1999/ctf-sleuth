from __future__ import annotations

from .hints import StrategyHints

HINTS = StrategyHints(
    skill_names=(
        "osint",
        "reconnaissance",
        "github-workflow",
        "techstack-identification",
        "social-engineering",
        "threat-intel",
        "phishing-investigation",
        "threat-intel",
        "phishing-investigation",
        "ioc-hunting",
        "essential-tools",
    ),
    tool_focus=(
        "curl",
        "whois",
        "dig",
        "exiftool",
        "WebFetch",
        "WebSearch",
        "crt.sh",
    ),
    prompt_section=(
        "## OSINT strategy\n\n"
        "1. 画像: exif 確認 (`exiftool`), 背景/看板/車種/植生で geolocation 絞込.\n"
        "2. username/email: sherlock 風の横断検索, haveibeenpwned, holehe.\n"
        "3. ドメイン: `whois`, `dig`, certificate transparency (`crt.sh`).\n"
        "4. Wayback Machine (archive.org), archive.today で過去 snapshot.\n"
        "5. SNS pivoting: フォロー/いいね/投稿時刻で関連アカウント推定.\n"
        "6. 航空機 ADS-B (FlightRadar24), 船舶 AIS (MarineTraffic).\n"
        "7. 検索時は複数言語で試す. 現地語の方が情報量が多いことが多い."
    ),
)

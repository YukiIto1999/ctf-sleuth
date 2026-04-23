---
name: script-generator
description: 攻撃 / 解析 / 自動化のための ad-hoc script を 言語別 (Python / Bash / PowerShell / JavaScript) で 構文検証付きで生成する。CTF / pentest / engagement の補助に発火。
category: general
tags:
  - script
  - automation
  - python
  - bash
  - powershell
  - syntax-check
---

# Script Generator (on-demand)

## When to Use

- exploit / PoC / 自動化 script を 短時間で生成
- 観察 / 確認 / 加工 script (curl + jq + awk 等)
- payload encode / decode / mutate 用 helper

**使わない場面**: 完成された tool が公式で存在する場合 (→ そちらを使う)。

## Approach / Workflow

### Phase 1 — language selection

```
Python:    汎用 / 充実 lib (requests / cryptography / scapy / pwntools)
Bash:      pipe 系 / 環境内 tool 連携
PowerShell: Windows / AD 操作
JavaScript: browser DOM / fetch / Puppeteer / Playwright
Go:        高速 / 並列 / static binary
Rust:      memory safe / performance
```

target 環境と必要 lib で選ぶ。

### Phase 2 — Python の典型 PoC template

```python
#!/usr/bin/env python3
"""
PoC for <vulnerability>
Usage: ./poc.py <target>
"""
import sys, requests, base64, hmac, hashlib

def main(target: str) -> None:
    url = f"https://{target}/api/x"
    payload = {"id": "1' OR 1=1--"}
    r = requests.post(url, json=payload, timeout=5, verify=False)
    if 'admin' in r.text:
        print("[+] Vulnerable:", r.status_code)
    else:
        print("[-] Not vulnerable")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "target.example.com")
```

### Phase 3 — Bash の典型 helper

```bash
#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-target.example.com}"
for path in robots.txt sitemap.xml .git/HEAD .env; do
    code=$(curl -s -o /dev/null -w '%{http_code}' "https://${TARGET}/${path}")
    echo "${path} ${code}"
done
```

### Phase 4 — PowerShell

```powershell
$ErrorActionPreference = 'Stop'
$creds = Get-Credential
$session = New-PSSession -ComputerName <host> -Credential $creds
Invoke-Command -Session $session -ScriptBlock {
    Get-Process | Where-Object { $_.CPU -gt 100 }
}
Remove-PSSession $session
```

### Phase 5 — script の品質確認

```
- shebang 適切?
- error handling (set -e / try-except)
- timeout / retry
- input validation
- output format (machine-readable / human-readable)
- secrets を hardcode しない (env / arg)
- destructive 操作の confirmation
```

```bash
# syntax check
python -m py_compile script.py
bash -n script.sh
pwsh -Command "Get-Command -Syntax script.ps1"
```

### Phase 6 — encoding / hashing helper

```python
import base64, hashlib, urllib.parse, hmac, json
b64 = base64.urlsafe_b64encode(b"x").decode().rstrip('=')
sha = hashlib.sha256(b"x").hexdigest()
url = urllib.parse.quote("a b/c", safe='')
mac = hmac.new(b"key", b"data", hashlib.sha256).hexdigest()
```

### Phase 7 — 並列 / batch

```python
import concurrent.futures
def task(host): return requests.get(f"https://{host}").status_code
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    for h, status in zip(hosts, ex.map(task, hosts)):
        print(h, status)
```

```bash
parallel -j 10 'curl -s -o /dev/null -w "{} %{http_code}\n" https://{}' :::: hosts.txt
```

### Phase 8 — secret 取扱

```
- env var で渡す: os.getenv('TOKEN')
- argparse で arg / config 区別
- 取得した secret を log に出さない
- script 公開前に redact
```

## Tools

```
python / bash / powershell / node / go / rust
shellcheck / pylint / ruff
WebFetch / WebSearch
Bash (sandbox)
```

## Related Skills

- `essential-tools`, `coordination`, `patt-fetcher`
- `cve-exploitation`
- `bug-bounter`, `web-bounty`, `red-teamer`, `web-pentester`

## Rules

1. **destructive 操作に confirm** — 削除 / 上書き / 大量 request は要確認
2. **secrets を hardcode しない**
3. **scope** — script 実行は scope 内のみ
4. **syntax check** — generation 後に必ず lint / compile

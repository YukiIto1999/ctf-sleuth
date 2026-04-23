---
name: essential-tools
description: pentest / bug bounty / CTF / DFIR で 共通的に使う core tool (Burp / mitmproxy / Playwright / nmap / ffuf / sqlmap / nuclei 等) の使い方と組合せ。CTF / pentest / engagement の入口で発火。
category: general
tags:
  - tools
  - methodology
  - burp
  - playwright
  - nmap
  - nuclei
---

# Essential Tools (Methodology)

## When to Use

- engagement 開始時の tool 選択 / 設定
- どの tool で何を解くかの reference
- 自前 setup / docker container の準備

**使わない場面**: 各 tool の specific deep dive (→ 該当 specific skill)、特定 task の手順 (→ 該当 task skill)。

## Approach / Workflow

### Phase 1 — proxy / interception

```
Burp Suite (Pro / Community):
  - Proxy / Repeater / Intruder / Decoder / Comparer
  - Scanner (Pro)
  - Extensions: JWT Editor / Param Miner / Hackvertor / Backslash Powered Scanner / Active Scan++ / Logger++
  - Browser 内蔵 (CA pre-trusted)

mitmproxy:
  - CLI / web ui / Python addon で柔軟 hook
  - mobile / IoT 評価で proxy 設定が GUI より楽

OWASP ZAP:
  - 無料、Burp 代替
  - automation 機能が強い
```

### Phase 2 — recon / discovery

```
nmap:        port + service + script (NSE)
masscan:     超高速 SYN scan (followup を nmap に)
naabu:       Go 製 高速 port scan
rustscan:    Rust 製
amass:       active + passive subdomain enum
subfinder:   passive subdomain enum
dnsx:        高速 resolver
httpx:       URL probe + tech detect
nuclei:      template-based vulnerability scanner
```

### Phase 3 — fuzz / brute

```
ffuf:        高速 web fuzz (path / param / vhost)
gobuster:    classic dir / dns / vhost
wfuzz:       Python ベース
hydra:       protocol brute force (許可 scope のみ)
patator:     hydra 代替、より柔軟
medusa:
```

### Phase 4 — exploit / payload

```
sqlmap:      SQL injection 自動
NoSQLMap:    NoSQL
commix:      OS command injection
xsstrike / dalfox / xsser:    XSS
metasploit:  exploit framework
ysoserial / ysoserial.net / phpggc:    deserialization gadget
gopherus:    SSRF gopher
PayloadsAllTheThings:    payload リファレンス (patt-fetcher で取得)
SecLists:    wordlist / payload 集
```

### Phase 5 — browser automation

```
Playwright (推奨):
  - Chromium / Firefox / WebKit を 1 API で
  - Network intercept / route / mocking
  - 認証 state save / load
  - mobile emulate
  - test runner

Puppeteer:    Chrome 専用
Selenium:     legacy 標準
```

human-like timing (typing 80-200ms / random pause / mouse move) を入れて bot detection bypass。

### Phase 6 — packet / network

```
wireshark / tshark:    GUI / CLI
zeek / suricata:        NSM / IDS
tcpdump / dumpcap:      capture
mitmproxy:              HTTPS interception
ettercap / bettercap:   active MitM
```

### Phase 7 — credential / hash

```
hashcat:    GPU-accelerated cracker
john:        CPU cracker (john format 多)
hydra:       online brute
crunch:      wordlist generation
cupp:        target-specific wordlist
```

### Phase 8 — sandbox / isolation

```
docker / podman:    container 隔離
firejail / bubblewrap:    Linux process isolation
qemu / virtualbox / vmware:    full VM
ANY.RUN / Cuckoo / Hybrid Analysis:    online sandbox (sample 共有時 注意)
```

### Phase 9 — note / 集計

```
CherryTree / Joplin / Obsidian:    note
ttyrec / asciinema:               session record
flameshot / ksnip:                screenshot
notion / Airtable / SQLite:       engagement DB
```

## Tools (まとめ)

```
proxy:     burp / mitmproxy / ZAP
recon:     nmap / masscan / naabu / amass / subfinder / dnsx / httpx / nuclei
fuzz:      ffuf / gobuster / wfuzz / hydra
exploit:   sqlmap / commix / xsstrike / dalfox / metasploit / ysoserial
browser:   Playwright / Puppeteer
network:   wireshark / tshark / zeek / suricata
hash:      hashcat / john
sandbox:   docker / qemu / VirtualBox
WebFetch / WebSearch
Bash (sandbox)
```

## Related Skills

- `coordination`, `script-generator`, `patt-fetcher`
- `bug-bounter`, `web-bounty`, `hackerone`, `red-teamer`, `web-pentester`, `reconnaissance`

## Rules

1. **scope** — 各 tool の使用は 認可済 scope のみ
2. **rate** — production への高頻度 scan を避ける
3. **artefact 保管** — engagement 中の note / screenshot を sealed area
4. **license** — 商用 tool (Burp Pro / Cobalt Strike) の規約遵守

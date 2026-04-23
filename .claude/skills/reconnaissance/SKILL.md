---
name: reconnaissance
description: domain / web 資産の偵察。subdomain enum / port / 技術 stack / 公開 endpoint / OSINT を組合せた通常 pentest / bug bounty / HTB の入口。
category: pentest
tags:
  - recon
  - subdomain
  - osint
  - dns
  - tls
  - portscan
---

# Reconnaissance

## When to Use

- 認可済 organization / domain への 1 回目偵察
- bug bounty で in-scope 資産の網羅
- HTB / Pro Labs の box 偵察

**使わない場面**: 既に foothold ある post-exploit (→ `red-teamer`)、純粋 OSINT investigation (→ `osint`)。

## Approach / Workflow

### Phase 1 — passive (active 通信なし)

```
- WHOIS / RDAP
- DNS records (A / AAAA / MX / TXT / NS / CAA / SRV / DMARC / SPF)
- Certificate Transparency (crt.sh, Censys, ctsearch)
- Wayback Machine (web.archive.org) / Common Crawl
- Github / GitLab org search (leaked secret / config)
- Shodan / Censys / FOFA / Quake host search
- Pastebin / paste.ee (leak)
- LinkedIn (employee / tech stack)
- ASN / BGP (asn.cymru.com)
```

### Phase 2 — subdomain enumeration

```
amass enum -d target.com
subfinder -d target.com -all
assetfinder target.com
crt.sh API + dnsx で resolve
github-subdomains.py -d target.com
```

統合 → resolve → 200/301/302 を出すものを web target 候補に。

### Phase 3 — DNS / IP 範囲

```
- ASN / BGP で IP 範囲推定
- reverse DNS で他 host 発見
- ip → hostname mapping (PTR)
- DMARC / SPF で 関連 mail server
- DNSSEC / NSEC walking で zone enumeration (記憶)
```

### Phase 4 — port / service scan

```
nmap -sS -T4 -p- -Pn -oA scan target           # 全 port (allowed range のみ!)
nmap -sV -sC -p <ports> target -oA service     # version + script
masscan -p- -rate 1000 -oG out.txt target
naabu -host target.com                          # high-speed
```

scope と rate limit を遵守。

### Phase 5 — web crawl & content discovery

```
ffuf -u https://target.com/FUZZ -w wordlist
gobuster dir -u https://target.com/ -w wordlist
katana -u https://target.com -d 5
gospider -s https://target.com
waybackurls target.com | uro
gau target.com | uro
```

JavaScript / sourcemap から endpoint:

```
linkfinder.py -i 'https://target.com/static/*.js'
JSScanner / SecretFinder (api key extraction)
```

### Phase 6 — 技術 stack / version

`techstack-identification` の手順:

```
whatweb / wappalyzer
favicon hash / X-Powered-By / Server header
DOM fingerprint (React/Angular/Vue 識別)
```

### Phase 7 — 公開 leak / config

```
github-search (`org:target` でなく "<target.com>" + "password=" 等)
trufflehog / gitleaks
.git/HEAD 露出 / .env 露出
robots.txt / sitemap.xml
.well-known/security.txt (報告先)
.well-known/openid-configuration (auth endpoint)
.well-known/oauth-authorization-server
```

### Phase 8 — visualize / scope ack

```
- subdomain × port × service の matrix
- attack surface map (web / api / mail / vpn / iot)
- 関連 organization の親子関係 (M&A / 子会社)
- third-party SaaS dependency (Cloudflare / Auth0 / Okta / Stripe / Sendgrid)
```

### Phase 9 — レポート

```
- 期間 / 取得情報量
- subdomain / port / service inventory
- 高 priority target (古い version / 公開管理画面 / 漏洩 secret)
- 推奨 (asset 削除 / patch / 監視)
```

## Tools

```
amass / subfinder / assetfinder / dnsx / shuffledns
nmap / masscan / naabu / rustscan
ffuf / gobuster / katana / gospider / waybackurls / gau / linkfinder
whatweb / wappalyzer / cdncheck
trufflehog / gitleaks / github-search
shodan / censys / fofa
WebFetch
Bash (sandbox)
```

## Related Skills

- `osint`, `techstack-identification`, `github-workflow`
- `web-pentester`, `api-security`, `bug-bounter`, `web-bounty`, `hackerone`
- `red-teamer`, `system`, `infrastructure`, `hackthebox`
- `phishing-investigation`, `threat-intel`
- `essential-tools`, `script-generator`, `patt-fetcher`

## Rules

1. **scope 厳守** — bug bounty program / engagement scope に限定
2. **rate limit** — 公開 service への scan は 帯域 / RPS 制限
3. **PII redaction**
4. **取得情報の sealed area 保管**

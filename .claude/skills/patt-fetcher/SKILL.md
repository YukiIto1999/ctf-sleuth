---
name: patt-fetcher
description: PayloadsAllTheThings (PATT) や類似 cheat sheet repo から、必要な vector の payload を on-demand に取得する。CTF / pentest / bug bounty で payload reference に発火。
category: general
tags:
  - payload
  - cheatsheet
  - patt
  - reference
  - github
---

# PayloadsAllTheThings Fetcher

## When to Use

- 攻撃 vector の payload を quick reference
- bug bounty / pentest 中に SQLi / XSS / SSRF / SSTI などの cheat sheet
- CTF web / pwn での payload set

**使わない場面**: payload を作る判断が固まってから対象 endpoint で実 firing する場面 (→ 各 specific exploit skill)。

## Approach / Workflow

### Phase 1 — 取得方法

```bash
git clone https://github.com/swisskyrepo/PayloadsAllTheThings ~/patt
ls ~/patt
# Top-level: 各 vulnerability class
# Methodology and Resources: methodology
```

更新は `git pull`。クローンせず WebFetch で個別 file を取る方法もある。

### Phase 2 — ディレクトリ構造

```
PayloadsAllTheThings/
├── SQL Injection/
├── XSS Injection/
├── Server Side Template Injection/
├── Server Side Request Forgery/
├── XXE Injection/
├── NoSQL Injection/
├── LDAP Injection/
├── Insecure Deserialization/
├── File Inclusion/
├── Upload Insecure Files/
├── CRLF Injection/
├── CSV Injection/
├── XSLT Injection/
├── Race Condition/
├── XS Search/
├── Open Redirect/
├── Subdomain Takeover/
├── Web Cache Deception/
├── Reverse Shell/
├── Methodology and Resources/  ← AD attack / Linux privesc / Windows privesc 等の cheatsheet
└── ...
```

各 directory に README.md (overview + payload + reference)。

### Phase 3 — 検索 / 抽出

```bash
# specific keyword の payload
grep -ril 'extractvalue' ~/patt/'SQL Injection/' | head
grep -A5 'XSS Polyglot' ~/patt/'XSS Injection/'README.md

# AD attack methodology の節を取得
ls ~/patt/'Methodology and Resources/'
cat ~/patt/'Methodology and Resources/Active Directory Attack.md' | head -50
```

WebFetch で github raw URL 直接取得:

```
https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/SQL%20Injection/README.md
```

### Phase 4 — 関連 reference repo

```
SecLists                       wordlist 集
Awesome-Web-Hacking-Techniques  PortSwigger 風 まとめ
HackTricks                    bug bounty / pentest book
PEASS-NG (linpeas / winPEAS)  privesc helper
GTFOBins                       Linux SUID abuse
LOLBAS                          Windows binary abuse
```

これらを併用すると network / scope / framework を跨ぐ payload 探索が容易。

### Phase 5 — payload 適用前のチェック

```
- target environment に合うか (DB engine / framework / encoding)
- character filter / WAF を考慮した tampering
- payload size / 形式 (URL encoding / form / JSON / multipart)
- 副作用 (unintended state change が起きないか)
- bug bounty / engagement scope での acceptable nature
```

### Phase 6 — 出典 / license

```
- PATT は MIT licensed
- 引用 / 改変は OK だが 配布時 license 維持
- 内部 wiki に丸 copy するときは license 表示
```

### Phase 7 — 自前 cheat sheet build

PATT を base に組織 / 個人特化 cheat sheet を作る:

```
- 自社 stack に合わせた variant
- tag (severity / class / target)
- 検証 stamp (実 production で動作確認 vs theoretical)
- 内部 wiki (Notion / Confluence / Obsidian)
```

## Tools

```
git
ripgrep / grep / jq
WebFetch / WebSearch
Bash (sandbox)
```

## Related Skills

- `essential-tools`, `script-generator`, `coordination`
- `web-pentester`, `injection`, `client-side`, `server-side`, etc.
- `bug-bounter`, `web-bounty`, `hackerone`, `red-teamer`
- `system`, `infrastructure`, `hackthebox`

## Rules

1. **scope** — payload を実 endpoint に投げる前に scope 内か確認
2. **PATT は thinking を外注しない** — 文脈に合わせ payload を選ぶ
3. **license 表示** — 引用 / 配布時に
4. **継続更新** — git pull

---
name: hackerone
description: HackerOne 程度な bug bounty platform 上の運用自動化。scope CSV 取込 / 多 program 並列 hunting / 報告 template / disclosure 管理。`bug-bounter` の platform 自動化版。
category: bug-bounty
tags:
  - hackerone
  - bugcrowd
  - intigriti
  - automation
  - scope
  - disclosure
---

# HackerOne / Bug Bounty Platform Automation

## When to Use

- HackerOne / Bugcrowd / Intigriti / YesWeHack 等で 多 program を 並走
- scope CSV / API を取り込み 自動列挙 → 自動 hunt → 報告
- engagement 管理を script 化

**使わない場面**: 単一 program の手動深掘り (→ `bug-bounter` / `web-bounty`)。

## Approach / Workflow

### Phase 1 — scope の取込

```
HackerOne API:
  GET /v1/hackers/programs                   subscribed program list
  GET /v1/hackers/programs/<handle>/structured_scopes
Bugcrowd: Crowdcontrol API
Intigriti: REST API
YesWeHack: REST API
```

```python
# pseudo
import requests
hcone_token = '...'
programs = requests.get('https://api.hackerone.com/v1/hackers/programs',
                         auth=('user', hcone_token)).json()
for p in programs['data']:
    scope = requests.get(f"https://api.hackerone.com/v1/hackers/programs/{p['attributes']['handle']}/structured_scopes",
                         auth=('user', hcone_token)).json()
    # in-scope の identifier_type / asset_type を抽出
```

### Phase 2 — scope normalization

multi-program の scope を共通 schema に:

```
program       | asset             | type           | bounty_max | last_resolved
program-A     | *.example.com     | URL            | 5000        | 2024-01-15
program-A     | app.example.com   | URL            | 10000       | ...
program-B     | api.foo.com       | URL            | 2000        |
program-B     | foo-mobile-app    | OTHER          | 1000        |
```

これを SQLite / Notion / Airtable に保管。

### Phase 3 — 並列 enumeration

```
- subdomain enum (amass / subfinder) を multi-program に並走
- 結果を per-program / per-asset で保存
- 新規 subdomain alert を notification (Slack / Discord)
```

```bash
parallel -j 5 'amass enum -d {} -o subs/{}.txt' ::: $(cat domains.txt)
```

### Phase 4 — 自動 nuclei / pattern

```
- nuclei の community template / 自前 template
- 重要な CVE / misconfiguration の継続 scan
- alert: rule hit + scope 内 asset
```

```bash
nuclei -l urls.txt -t cves/ -t misconfiguration/ -severity high,critical -o findings.txt
```

rate / 並列度を program 規約内に。

### Phase 5 — 報告 template (program 別)

```
- 各 program の好み (markdown rich / プレーン text / video 必須 / 添付制限)
- severity 算出 (CVSS v3 / 独自)
- bounty range
```

template 化:

```yaml
title: "{vulnerability}"
severity: critical
asset: "{asset}"
description: |
  {description}
steps:
  - {step1}
  - ...
poc: |
  {poc_code}
impact: |
  {impact}
remediation: |
  {fix}
references:
  - {refs}
```

### Phase 6 — disclosure 管理

```
- triage 期限 / fix 期限 / public 期限
- duplicate 確認 (公開済 reports と類似度)
- escalation (program admin への直接連絡)
- payout 管理 / 税務
```

### Phase 7 — KPI / 学習

```
- 成功 / 失敗 finding の analysis
- 受付率 / 報酬 / triage 期間
- 自分の skill set を 弱い category で強化
```

## Tools

```
H1 / Bugcrowd / Intigriti / YesWeHack API
amass / subfinder / nuclei / dalfox / 自前 script
notion / Airtable / SQLite
WebFetch / WebSearch
Bash (sandbox)
```

## Related Skills

- `bug-bounter`, `web-bounty`, `osint`, `reconnaissance`, `techstack-identification`, `github-workflow`
- `web-pentester`, `api-security`, `injection`, `client-side`, `server-side`, `web-app-logic`, `authentication`
- `cve-exploitation`
- `essential-tools`, `coordination`, `script-generator`

## Rules

1. **scope / RoE 厳守**
2. **rate / 並列度** — program 規約内 / 過大 scan 禁止
3. **PII 取扱** — leak data の最小確認 + sealed report
4. **重複報告禁止** — 1 finding 1 report
5. **disclosure timeline 尊重**

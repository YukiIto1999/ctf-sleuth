---
name: github-workflow
description: GitHub OSINT (organization 列挙 / 漏洩 secret / commit history / Actions log / 関連 repo の探索) を体系的に進める。bug bounty / OSINT で発火。
category: osint
tags:
  - github
  - osint
  - secret-scan
  - dorking
  - actions
  - org
---

# GitHub OSINT Workflow

## When to Use

- 対象 organization / individual の GitHub footprint を網羅
- 漏洩 secret / credential の発見
- 公開 repo の脆弱な commit / config 探索

**使わない場面**: source code 解析自体 (→ `source-code-scanning`)、private repo への access (→ scope 違反)。

## Approach / Workflow

### Phase 1 — organization 列挙

```bash
gh api orgs/<org>/repos --paginate --jq '.[].full_name'
gh api orgs/<org>/members --paginate --jq '.[].login'
gh api users/<user>/repos --paginate --jq '.[].full_name'
gh api users/<user>/followers --paginate
```

`github-search-tool` / `github-org-search` 等で 公開 repo を抽出。

### Phase 2 — code search (dorking)

```
"<keyword>" repo:<org>/<repo>
"BEGIN RSA PRIVATE KEY" org:<org>
"AKIA" org:<org>
"password=" org:<org>
"api_key" filename:.env
"DB_PASSWORD" extension:env
"firebase" filename:google-services.json
".pem" path:keys
"ssh-rsa" extension:pub                       # 公開鍵は問題ないが秘密鍵 grep では弾く
".aws/credentials" in:path
"private_key" extension:json (firebase service account)
```

`gh search code` で:

```bash
gh search code 'org:<org> "AKIA"' --json repository,path,html_url
```

### Phase 3 — secret scan ツール

```bash
trufflehog github --org=<org> --only-verified --concurrency=8
gitleaks detect --source <local-clone> --report-format json
```

`--only-verified` で actual valid な credentials のみ。

### Phase 4 — commit history / branch

```
- 古い commit に消した secret が残る (force push 漏れ)
- branch 名 / tag 名から development context (release-2024-Q1 / hotfix-*)
- merged PR のコメント / discussion で credential が露出
```

```bash
git log --all -p | grep -iE 'password|secret|token|api_key' | head
git log --all --diff-filter=D --pretty=format:'%h %s' -- <file>  # 削除 commit
```

### Phase 5 — Actions / CI log

```
- public Actions run の log (encrypted secret は ***)
- artefact (build 出力 / SBOM)
- workflow yaml の env secrets reference
- self-hosted runner が露出していないか
```

### Phase 6 — Issue / PR / Discussion

```
- bug report で攻撃方法が公開されたまま
- security@ 宛て報告が public issue として上がる事故
- 内部 jira link / staging URL の露出
- 過去 PR の review comment で内部 IP / config が共有
```

### Phase 7 — Profile / social

```
- ユーザの bio / location / job title
- 関連 organization / 同僚 (followers / following)
- gist (公開コード片)
- starred repo (興味分野)
- contribution heatmap (active 時間帯 / time zone)
```

### Phase 8 — レポート

```
- 対象 org / user
- 取得情報 (repo / secret / contributor / 関連)
- 漏洩 credential (件数 / verified / redact)
- 推奨 (rotation / private 化 / org policy)
```

## Tools

```
gh CLI / GitHub Search API
trufflehog / gitleaks / detect-secrets
github-search-tool / github-org-search
git
WebFetch / WebSearch
Bash (sandbox)
```

## Related Skills

- `osint`, `reconnaissance`, `techstack-identification`
- `detection-cloud-anomalies`
- `bug-bounter`, `web-bounty`, `hackerone`, `red-teamer`
- `social-engineering` (employee profile から pretext)
- `source-code-scanning`
- `threat-intel`, `ioc-hunting`

## Rules

1. **public repo only** — private / 内部 repo への試験 access はしない
2. **責任ある開示** — 重要 secret 発見時は repo owner に通報 / rotate 推奨
3. **取得情報** — sealed area
4. **rate limit** — gh API tokenは PAT で 5000 req/hour 枠内に

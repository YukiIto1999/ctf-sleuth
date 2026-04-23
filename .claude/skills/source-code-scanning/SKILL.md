---
name: source-code-scanning
description: source code に対する SAST / secret scan / 依存 lib audit / dataflow 解析。CTF rev / bug bounty (open source) / 自社 audit / supply chain で発火。
category: pentest
tags:
  - sast
  - secret-scan
  - dependency
  - dataflow
  - codeql
  - semgrep
---

# Source Code Security Scanning (SAST)

## When to Use

- 自社 / scope 内 OSS の source review
- supply chain 脆弱性確認
- CTF で github repo / source-only 系問題

**使わない場面**: binary だけ (→ `reverse-engineering`)、live web だけ (→ `web-pentester`)。

## Approach / Workflow

### Phase 1 — 言語 / framework 特定

```bash
cloc .                           # 言語別行数
github-linguist .                # github でも判定される定義
ls package.json composer.json pyproject.toml go.mod Cargo.toml pom.xml build.gradle Gemfile
```

主要 framework / version を控え、framework 固有 SAST rule を選ぶ。

### Phase 2 — secret / credential scan

```
gitleaks detect --source . --report-format json -r leaks.json
trufflehog filesystem . --only-verified
detect-secrets scan > .secrets.baseline
```

Github org 全体なら trufflehog `github --org=`。

### Phase 3 — 依存 audit (SBOM + CVE)

```
syft .  -o spdx-json -f sbom.json
grype sbom.json -o table
osv-scanner --sbom sbom.json
trivy fs .
npm audit / pnpm audit / yarn audit
pip-audit
cargo audit
go list -json -m all | nancy sleuth
```

### Phase 4 — SAST (一般)

```
semgrep --config auto .                      # community rule
semgrep --config p/owasp-top-ten .
semgrep --config p/security-audit .
```

CodeQL (GitHub):

```
codeql database create db --language=python
codeql database analyze db --format=sarif-latest --output=results.sarif <suite>
```

商用 SAST: SonarQube / Checkmarx / Veracode / Fortify。

### Phase 5 — 言語別 deep dive

```
JavaScript:    eslint security plugin / nodejsscan
TypeScript:    tsec / typescript-eslint security
Python:        bandit / pylint security
Java:          spotbugs + find-sec-bugs / pmd
Ruby:          brakeman (Rails 専用)
PHP:           psalm / phpstan
Go:            gosec / staticcheck
Rust:          cargo-audit / clippy
.NET:          security code scan
```

### Phase 6 — 観点別 review

```
- input validation (sources): query / form / cookie / header / json / xml
- escape / encode (sinks): SQL / shell / template / XPath / LDAP
- authn / authz: 各 endpoint で実施されてる?
- session / token: lifetime / rotate / scope
- crypto: 自前実装 / weak alg / hard-coded key
- file IO: path traversal / upload validation
- deserialization: trusted-only?
- logging: PII redaction / log injection 防御
- error handling: stack trace 漏洩なし
- third-party: SDK 構成
```

### Phase 7 — dataflow / taint 分析

CodeQL や semgrep の `taint mode` で source → sink の経路を tracking:

```yaml
# semgrep taint
mode: taint
pattern-sources:
  - pattern: request.GET.get($X)
pattern-sinks:
  - pattern: cursor.execute(...)
```

入力が消毒なしで sink に到達するのを検出。

### Phase 8 — manual diff / hot spot

```
- 認証 / 認可 module
- 入金 / 残高 / 状態変更 endpoint
- file upload / archive 解凍
- deserialization
- shell execution
- regex / template engine 経由 RCE
- 自前 crypto
```

### Phase 9 — CI への組込み

```
GitHub Actions / GitLab CI で:
  - on push に semgrep / gitleaks / grype / dependabot
  - PR に対して new finding のみ blocking
  - SARIF 出力で Github Code Scanning に表示
```

### Phase 10 — レポート

```
- 対象 repo / commit hash / 言語比率
- finding 件数 (severity 別 / category 別)
- 上位 critical 抜粋 (file:line + 修正例)
- 依存 CVE 一覧
- secret 漏洩 (verified)
- 推奨 (sanitizer / encode / framework 設定 / dependency upgrade)
```

## Tools

```
semgrep / codeql / sonarqube / checkmarx
bandit / brakeman / spotbugs / gosec / clippy / nodejsscan / phpstan
gitleaks / trufflehog / detect-secrets
syft / grype / trivy / osv-scanner
WebFetch
Bash (sandbox)
```

## Related Skills

- `web-pentester`, `api-security`, `client-side`, `server-side`, `web-app-logic`
- `bug-bounter`, `web-bounty`, `hackerone`
- `cve-exploitation`
- `reverse-engineering`, `injection`, `performing-cryptographic-audit-of-application`
- `detection-cloud-anomalies`
- `essential-tools`, `script-generator`, `coordination`

## Rules

1. **scope** — 認可済 repo のみ
2. **secret 取扱** — 検出した secret は sealed area
3. **CI への組込み推奨**
4. **誤検知耐性** — pattern を refine、false positive を allowlist

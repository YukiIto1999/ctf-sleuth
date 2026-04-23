
# AWS Credential Exposure Detection (TruffleHog 系)

`detection-cloud-anomalies` から呼ばれる variant 別 deep dive

## When to Use

- 公開 repo / CI 環境 / 設定 file に AWS access key が漏れていないか確認
- bug bounty でアプリケーション側の credential leak を体系的に探す
- 自前 organization の repo に対する継続スキャン

**使わない場面**: 漏れた key の悪用 / privesc は別 skill (`cloud-pentester`、`cloud-pentester`)。

## Approach / Workflow

### Phase 1 — 対象範囲の確定

```
- public Github repo (org 全体 / specific repo)
- private repo (organization scope)
- CI/CD config (.github/workflows / .gitlab-ci.yml / Jenkinsfile / circleci config)
- Docker image (env / layer 履歴)
- log artefact (CI 実行ログ / k8s pod log)
- pastebin / gist / mirror site (OSINT)
- mobile app build (APK / IPA strings)
```

### Phase 2 — TruffleHog 実行

```bash
# 公開 repo
trufflehog github --repo=https://github.com/<org>/<repo> --only-verified

# org 全体
trufflehog github --org=<org> --only-verified --concurrency=8

# ローカル clone
trufflehog filesystem ./repo --only-verified

# Docker image
trufflehog docker --image=<image:tag> --only-verified

# S3 bucket (object 中身を scan)
trufflehog s3 --bucket=<bucket> --only-verified
```

`--only-verified` は実際に AWS / GitHub / GCP API で valid 確認まで取れた key だけを返す（false positive 削減）。

### Phase 3 — git-secrets / gitleaks の補助

```bash
gitleaks detect --source=. --report-format=json --report-path=leaks.json
git-secrets --scan
git secrets --scan-history
```

複数 detector の結果を merge し、AWS access key (AKIA / ASIA) と secret access key の組合せを相関。

### Phase 4 — AWS-native 検出

```
- IAM Access Analyzer
- AWS Macie (S3 内 secret / PII 検出)
- CloudTrail で 「失敗 STS GetSessionToken」「未知 ASN からの API call」
- GuardDuty: UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration 等
```

### Phase 5 — 漏洩 key の検証

漏れた候補:

```bash
aws sts get-caller-identity --profile leaked
# 成功なら有効。region / account / arn を控える
```

権限把握:

```bash
aws iam get-user --profile leaked
aws iam list-attached-user-policies --user-name <user> --profile leaked
aws iam list-user-policies --user-name <user> --profile leaked
aws iam simulate-principal-policy ...
```

### Phase 6 — 影響評価

```
- account / 環境の規模
- 触れる service (S3 / EC2 / Lambda / IAM)
- DBA / cluster-admin 相当の権限有無
- 横展開可能性 (cross-account assume)
```

### Phase 7 — 通報 / 修正

bug bounty / 自社 org の場合、報告フォーマット:

```
- 発見場所 (URL / commit hash)
- key 形式 (AKIA*** の最初/最後 4 文字)
- 確認した有効性 (sts get-caller-identity の結果概要、ARN は redact)
- 確認した権限範囲
- 推奨対応 (key 即 deactivate / rotate / git history 削除 / IAM 縮小)
```

### Phase 8 — 継続監視

```
- pre-commit hook (gitleaks / detect-secrets)
- Github push protection
- CI step に trufflehog
- Macie + EventBridge alert
```

## Tools

```
trufflehog
gitleaks
git-secrets
detect-secrets
aws cli (検証)
WebFetch
Bash (sandbox)
```

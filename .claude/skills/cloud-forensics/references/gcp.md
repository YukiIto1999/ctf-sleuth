# GCP Cloud Forensics

`cloud-forensics` の Phase 2 / Phase 5 から呼ばれる、GCP project / Workspace の侵害解析。Cloud Audit Logs (Admin Activity / Data Access / System Event / Policy Denied) / VPC Flow Logs / Disk snapshot / Secret Manager 監査の統合。

## いつ切替えるか

- GCP project / Cloud Workspace の侵害解析
- Viewer / IR-only credential での post-incident 解析
- compromised user / SA / workload identity の行動再構成

## Phase 1 — IR 体制

```bash
# IR 用 read-only role
# project: roles/viewer + roles/logging.viewer + roles/iam.securityReviewer
# org: roles/orgpolicy.policyViewer + roles/securitycenter.findingsViewer

gcloud auth login
gcloud config set project <PROJECT>
gcloud projects describe <PROJECT>
```

## Phase 2 — Cloud Audit Logs の triage

```bash
# Admin Activity (常時 ON)
gcloud logging read 'log_id("cloudaudit.googleapis.com/activity")' \
  --freshness=7d --format=json > admin_activity.json

# Data Access (要 ON 化)
gcloud logging read 'log_id("cloudaudit.googleapis.com/data_access")' --freshness=7d

# System Event
gcloud logging read 'log_id("cloudaudit.googleapis.com/system_event")' --freshness=7d

# Policy Denied
gcloud logging read 'log_id("cloudaudit.googleapis.com/policy")' --freshness=7d
```

BigQuery 経由 (sink 設定済) なら SQL で大量分析:

```sql
SELECT timestamp, protoPayload.authenticationInfo.principalEmail, protoPayload.methodName, resource.type
FROM `<project>.<dataset>.cloudaudit_googleapis_com_activity_*`
WHERE _TABLE_SUFFIX BETWEEN '20260101' AND '20260102'
  AND protoPayload.methodName LIKE '%setIamPolicy%'
ORDER BY timestamp;
```

| 観点 | filter |
|---|---|
| IAM 改竄 | `methodName=~"setIamPolicy|create.*Role|delete.*Role"` |
| SA 作成 / key 追加 | `methodName=~"google.iam.admin.v1.CreateServiceAccount(Key)?"` |
| ConsoleLogin (=oauth login) | `methodName="google.cloud.audit.LogIn"` (※実体は別) |
| 大量 GCS download | `methodName="storage.objects.get" AND resource.type="gcs_bucket"` |
| Compute 起動 | `methodName="v1.compute.instances.insert"` |
| BigQuery 大量 query | `protoPayload.metadata.@type=~"BigQueryAuditMetadata"` |
| Logging Sink 改竄 | `methodName=~"google.logging.v2.Configuration.*Sink"` (隠蔽兆候) |

## Phase 3 — Disk / Compute snapshot 取得

```bash
# Persistent disk snapshot
gcloud compute disks snapshot <disk-name> \
  --snapshot-names=ir-<host>-<date> \
  --zone=<zone>

# IR project の volume にアタッチして read-only mount → disk-forensics skill
gcloud compute disks create ir-volume-<date> \
  --source-snapshot=ir-<host>-<date> \
  --zone=<zone> \
  --project=<ir-project>
```

## Phase 4 — VPC Flow Logs / Firewall

```bash
gcloud logging read 'log_id("compute.googleapis.com/vpc_flows")' --freshness=24h
gcloud logging read 'log_id("compute.googleapis.com/firewall")' --freshness=24h
```

外部 IP 接続・metadata server (`metadata.google.internal` = `169.254.169.254`) アクセスの異常を確認。

## Phase 5 — IAM 改竄

```bash
# 現在の IAM policy snapshot
gcloud projects get-iam-policy <project> --format=json > iam-now.json

# Cloud Asset Inventory で過去 policy 取得 (Asset history が要件)
gcloud asset search-all-iam-policies --scope=projects/<project>

# 短時間の policy 変更
gcloud logging read \
  'protoPayload.methodName="SetIamPolicy"' \
  --freshness=7d --format=json
```

`Owner` / `Editor` / 高権限 custom role の追加、外部 domain user / SA への grant、`allUsers` / `allAuthenticatedUsers` への grant を確認。

## Phase 6 — Secret Manager / KMS 監査

```bash
gcloud logging read \
  'protoPayload.methodName="google.cloud.secretmanager.v1.SecretManagerService.AccessSecretVersion"' \
  --freshness=7d
```

短時間の大量 AccessSecretVersion は exfil signal。KMS:

```bash
gcloud logging read \
  'protoPayload.methodName=~"google.cloud.kms.v1.KeyManagementService.(Decrypt|AsymmetricSign)"' \
  --freshness=7d
```

## Phase 7 — Workload identity 行動

GKE / Cloud Run の workload identity が SA を impersonate して GCS / BigQuery に異常 access していないか:

```bash
gcloud logging read \
  'protoPayload.authenticationInfo.principalEmail=~"<sa>@<project>.iam.gserviceaccount.com"' \
  --freshness=24h --format=json | jq '.[] | {time:.timestamp,method:.protoPayload.methodName,resource:.protoPayload.resourceName}'
```

## Phase 8 — timeline / 攻撃 chain

```
時刻       provider event                actor                影響
HH:MM:SS   LogIn (no MFA)               compromised-user     foothold
HH:MM:SS   SetIamPolicy (Editor 付与)   compromised-user     privesc
HH:MM:SS   CreateServiceAccountKey      compromised-user     persistence
HH:MM:SS   AccessSecretVersion x50      compromised-SA       exfil
HH:MM:SS   sinks.update (log 抑制)      compromised-user     隠蔽
```

## Phase 9 — レポート

```
- 環境 (org / project)
- 期間
- 攻撃 chain (MITRE ATT&CK Cloud Matrix)
- 関与した user / SA / workload identity
- 影響範囲 (data plane / control plane)
- 残存リスク (SA key rotation / IAM 縮小 / sink 復旧 / consent 確認)
- 推奨 (Org Policy / VPC SC / SCC alert / IAM Recommender)
```

## Tools

```
gcloud cli
BigQuery (audit log analytics)
Cloud Asset Inventory / Policy Analyzer
Security Command Center
gsutil
WebFetch
Bash (sandbox)
```

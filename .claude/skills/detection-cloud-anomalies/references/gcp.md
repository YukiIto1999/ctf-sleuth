# GCP Anomaly Detection / Hunting

`detection-cloud-anomalies` から呼ばれる、GCP project / org level の不審 IAM / SA key / 大量 storage access / cryptomining / Compute 起動 / log sink 改竄 hunting。

## いつ切替えるか

- GCP project / org の継続 monitoring + behavioral hunting
- SCC findings の 上位 layer として hunting rule を策定
- 自社 GCP の baseline + alerting

## Phase 1 — log source の確保

```
Cloud Audit Logs:
  - Admin Activity (always-on)
  - Data Access (要 ON 化)
  - System Event
  - Policy Denied
sink → BigQuery / Cloud Logging / Cloud Storage に export
```

```bash
# project-level audit log
gcloud logging read 'log_id("cloudaudit.googleapis.com/activity")' --freshness=7d
# org-level
gcloud logging read 'log_id("cloudaudit.googleapis.com/activity")' --organization=<ORG>
```

## Phase 2 — baseline 構築

```
- 通常 API call の per-actor / per-method 件数 (7-30 日)
- 通常 source IP / geo
- SA key 作成頻度 (基本 0 が望ましい)
- SetIamPolicy 頻度
- GCS bucket 公開化頻度
```

## Phase 3 — behavioral hunting

| 観点 | BigQuery SQL (audit log table 前提) |
|---|---|
| 不審 SA key 作成 | `WHERE methodName="google.iam.admin.v1.CreateServiceAccountKey" AND principalEmail NOT IN (allowlist)` |
| Owner / Editor 付与 | `WHERE methodName="SetIamPolicy" AND policy LIKE "%roles/owner%"` |
| 外部 / allUsers grant | `WHERE methodName="SetIamPolicy" AND policy LIKE "%allUsers%"` |
| 大量 Secret access | `WHERE methodName=~"AccessSecretVersion" GROUP BY principalEmail HAVING count(*) > 50` |
| Compute 起動 | `WHERE methodName="v1.compute.instances.insert"` |
| GCS 公開化 | `WHERE methodName="storage.setIamPermissions" AND policy LIKE "%allUsers%"` |
| log sink 改竄 (隠蔽) | `WHERE methodName=~"google.logging.v2.Configuration.*Sink"` |
| GKE workload identity binding | `WHERE methodName="SetIamPolicy" AND policy LIKE "%iam.workloadIdentityUser%"` |

## Phase 4 — cryptomining 兆候

```sql
-- Compute 起動に GPU instance / 高 CPU instance が混入
SELECT principalEmail, resourceName, machineType
FROM `<project>.<dataset>.cloudaudit_googleapis_com_activity_*`
WHERE methodName = "v1.compute.instances.insert"
  AND machineType LIKE "%n1-highcpu%" OR machineType LIKE "%a2-highgpu%"
ORDER BY timestamp DESC;
```

monero / ethermine / xmrig の DNS query (Cloud DNS log + GKE DNS) を併走監視。

## Phase 5 — workload identity 異常

GKE / Cloud Run の workload identity が想定外 SA を impersonate して GCS / BigQuery / Secret Manager にアクセス:

```sql
SELECT 
  protoPayload.authenticationInfo.principalEmail AS actor,
  protoPayload.methodName,
  resource.type,
  COUNT(*) AS n
FROM `<project>.<dataset>.cloudaudit_googleapis_com_data_access_*`
WHERE protoPayload.authenticationInfo.principalEmail LIKE "%@%.iam.gserviceaccount.com"
GROUP BY actor, methodName, resource.type
ORDER BY n DESC
LIMIT 50;
```

## Phase 6 — 隠蔽兆候 (anti-forensics)

```
- DisableProject (project 削除)
- log sink update / delete
- Audit Log Bucket の retention 短縮
- monitoring policy の delete
```

これらは MITRE ATT&CK Cloud T1562.008 (Disable / Modify Cloud Logs) に該当。即 alert。

## Phase 7 — alert / detection rule

- BigQuery scheduled query で nightly 検出
- Security Command Center custom finding source として登録
- Cloud Monitoring alert policy → PagerDuty / Slack
- Chronicle / Sentinel に export して cross-cloud correlation

## Phase 8 — レポート

```
- project / org / period
- hit 件数 (true positive / false positive 別)
- 攻撃 chain (MITRE ATT&CK Cloud Matrix)
- 残存リスク (SA key rotation / IAM 縮小 / sink 復旧)
- 推奨 (Org Policy / VPC SC / Cloud Asset Inventory monitor / IAM Recommender)
```

## Tools

```
gcloud cli
BigQuery (audit log analytics)
Cloud Asset Inventory
Security Command Center
Chronicle (Google SIEM)
WebFetch
Bash (sandbox)
```

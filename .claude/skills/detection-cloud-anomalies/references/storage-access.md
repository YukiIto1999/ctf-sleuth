
# Cloud Storage Access Pattern Analysis

`detection-cloud-anomalies` から呼ばれる variant 別 deep dive

## When to Use

- cloud storage (S3 / Azure Blob / GCS) からの大量 download / 不審 access が疑われる
- ransomware による全 object 削除 / encrypt 試行の追跡
- 公開設定変更 (public ACL / signed URL 期限延長) の調査
- exfil 経路の確認

**使わない場面**: storage 自体の構成不備の事前評価（→ `detection-cloud-anomalies`）、cloud-wide 横断 audit（→ `cloud-forensics`）。

## Approach / Workflow

### Phase 1 — log の取り込み

```
AWS S3:    CloudTrail Data Events (要 enable) / S3 Server Access Logging
Azure Blob: Storage Analytics Logging / Diagnostic Setting → Log Analytics
GCS:       Cloud Audit Logs (DATA_READ / DATA_WRITE)
```

各 provider で data event を有効化していないと object level の操作が見えない。CloudTrail management event のみだと bucket policy 変更しか分からない。

### Phase 2 — 異常 access の指標

```
- 同一 IP / IAM principal が短時間に大量 GetObject / 巨大 size download
- 通常使われない region / endpoint 経由の access
- 国 / ASN が事業範囲外
- user-agent が aws-cli / azcopy / gsutil で 通常 user じゃないもの
- pre-signed URL の生成 ratio が急増 (exfil 用)
- public ACL / SAS / signed URL 設定変更
- DeleteObject / DeleteBucket の大量発火 (ransomware 兆候)
- bucket policy / ACL / Block Public Access の変更
```

### Phase 3 — KQL / SQL クエリ

#### CloudTrail (S3 data events) — Athena

```sql
SELECT
  useridentity.arn as principal,
  sourceipaddress as src_ip,
  count(*) as event_count,
  sum(case when eventname = 'GetObject' then 1 else 0 end) as gets,
  sum(case when eventname = 'PutObject' then 1 else 0 end) as puts,
  sum(case when eventname = 'DeleteObject' then 1 else 0 end) as deletes
FROM cloudtrail
WHERE eventtime BETWEEN '2024-01-01T00:00:00Z' AND '2024-01-02T00:00:00Z'
  AND eventsource = 's3.amazonaws.com'
GROUP BY principal, src_ip
ORDER BY gets DESC
LIMIT 50;
```

#### Azure Storage (KQL)

```kql
StorageBlobLogs
| where TimeGenerated > ago(7d)
| where OperationName in ("GetBlob", "PutBlob", "DeleteBlob")
| summarize Count = count() by AccountName, CallerIpAddress, OperationName
| order by Count desc
```

#### GCS (BigQuery)

```sql
SELECT
  protopayload_auditlog.authenticationInfo.principalEmail AS user,
  protopayload_auditlog.requestMetadata.callerIp AS ip,
  COUNT(*) AS n
FROM `<project>.<dataset>.cloudaudit_googleapis_com_data_access`
WHERE resource.type = "gcs_bucket"
  AND timestamp BETWEEN TIMESTAMP("2024-01-01") AND TIMESTAMP("2024-01-02")
GROUP BY user, ip
ORDER BY n DESC
```

### Phase 4 — exfil の規模推定

```
size 推定 (object size × count)
egress traffic と相関 (VPC Flow Log / NSG flow / VPC Service Controls)
S3: GetObject の bytesTransferred を totals に
```

### Phase 5 — 公開設定変更の検出

CloudTrail で `PutBucketAcl`, `PutBucketPolicy`, `PutBucketPublicAccessBlock`、Azure で `Microsoft.Storage/storageAccounts/blobServices/containers/write` (publicAccess パラメータ確認)、GCS で `storage.buckets.update` (iam policy 変更) を検索。

### Phase 6 — 応答

```
1. principal / token の即時 disable / rotate
2. bucket / container の public access 解除
3. signed URL / SAS の取消し
4. 新規 access policy (deny by default + IP / VPC condition)
5. data event log の audit 化 (engagement 後の baseline)
```

### Phase 7 — レポート

```
- 期間 / object 数 / size
- 関与 principal / IP / region
- 推定攻撃 chain (credential 取得 → S3 列挙 → 大量 download)
- 残存リスク (まだ public な resource / signed URL)
- 推奨対応
```

## Tools

```
Athena (CloudTrail SQL)
Sentinel / Log Analytics (KQL)
BigQuery (GCS audit)
jq / pandas
WebFetch
Bash (sandbox)
```

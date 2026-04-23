
# Cloud Log Forensics with Athena

`detection-cloud-anomalies` から呼ばれる variant 別 deep dive

## When to Use

- 大量 CloudTrail / Flow / access log を SQL で interactive に検索したい
- すでに Athena workgroup が設定済 / すぐ設定可能
- multi-source の log を `JOIN` で相関したい

**使わない場面**: log が S3 に無く CloudWatch Logs Insights のみ参照可能（→ Insights query で代替）、軽量な単発調査（→ jq / awk）。

## Approach / Workflow

### Phase 1 — table 定義

#### CloudTrail

```sql
CREATE EXTERNAL TABLE cloudtrail_logs (
  eventversion STRING,
  useridentity STRUCT<...>,
  eventtime STRING,
  eventsource STRING,
  eventname STRING,
  awsregion STRING,
  sourceipaddress STRING,
  useragent STRING,
  errorcode STRING,
  errormessage STRING,
  requestparameters STRING,
  responseelements STRING,
  additionaleventdata STRING,
  requestid STRING,
  eventid STRING,
  resources ARRAY<STRUCT<arn:STRING,accountid:STRING,type:STRING>>,
  eventtype STRING,
  apiversion STRING,
  readonly STRING,
  recipientaccountid STRING,
  serviceeventdetails STRING,
  sharedeventid STRING,
  vpcendpointid STRING
)
PARTITIONED BY (year STRING, month STRING, day STRING)
ROW FORMAT SERDE 'com.amazon.emr.hive.serde.CloudTrailSerde'
LOCATION 's3://<bucket>/AWSLogs/<acct>/CloudTrail/';
```

VPC Flow / ALB / S3 access log も同様の DDL を AWS docs で取得し作成。Glue Crawler で自動定義も可。

### Phase 2 — 高頻度クエリ

#### 不審 ConsoleLogin

```sql
SELECT eventtime, useridentity.arn AS principal, sourceipaddress, useragent, additionaleventdata
FROM cloudtrail_logs
WHERE eventname = 'ConsoleLogin'
  AND eventtime BETWEEN '2024-01-15T00:00:00Z' AND '2024-01-16T00:00:00Z';
```

#### 高権限 IAM 操作

```sql
SELECT eventtime, useridentity.arn, eventname, requestparameters
FROM cloudtrail_logs
WHERE eventname IN ('CreateUser','CreateAccessKey','AttachUserPolicy','PutUserPolicy','UpdateAssumeRolePolicy','PassRole')
  AND eventtime BETWEEN ? AND ?;
```

#### S3 大量 GetObject

```sql
SELECT useridentity.arn AS principal, sourceipaddress, COUNT(*) AS gets, SUM(bytestransferred) AS total_bytes
FROM s3_access_logs
WHERE eventtime BETWEEN ? AND ?
  AND operation = 'REST.GET.OBJECT'
GROUP BY 1,2
HAVING COUNT(*) > 1000
ORDER BY gets DESC;
```

#### VPC Flow で外部 exfil 候補

```sql
SELECT srcaddr, dstaddr, dstport, SUM(bytes) as total
FROM vpc_flow_logs
WHERE start BETWEEN ? AND ?
  AND action = 'ACCEPT'
  AND srcaddr LIKE '10.%'   -- internal
  AND dstaddr NOT LIKE '10.%' AND dstaddr NOT LIKE '169.254.%'
GROUP BY 1,2,3
HAVING SUM(bytes) > 1073741824   -- 1 GB
ORDER BY total DESC LIMIT 50;
```

#### ALB log で攻撃 pattern

```sql
SELECT request_url, COUNT(*) AS n
FROM alb_logs
WHERE request_url LIKE ANY ('%UNION%','%/etc/passwd%','%169.254.169.254%','%<script%')
GROUP BY 1 ORDER BY n DESC;
```

### Phase 3 — JOIN による相関

```sql
SELECT c.eventtime, c.useridentity.arn AS principal, c.eventname,
       v.dstaddr AS exfil_to, v.bytes
FROM cloudtrail_logs c
JOIN vpc_flow_logs v
  ON v.srcaddr = c.sourceipaddress
WHERE c.eventname = 'GetObject'
  AND v.bytes > 100000000;
```

### Phase 4 — 性能 / コスト

```
- partition pruning: WHERE year='2024' AND month='01' AND day='15'
- columnar 化 (Parquet) で scan size を小さく
- Athena 課金は scan データ量基準
- 大規模 cluster は Snowflake / BigQuery への ETL が向くこともある
```

### Phase 5 — レポート / 自動化

```
- ad-hoc query で出した結果を CSV / Parquet 化して archive
- 重要 query は SavedQuery + EventBridge で定期化
- 結果を SNS / Slack に通知して analyst に届ける
```

## Tools

```
AWS Athena (Console / cli)
Glue Crawler / Catalog
S3 (log 保存)
quicksight / Grafana (可視化)
WebFetch
Bash (sandbox)
```

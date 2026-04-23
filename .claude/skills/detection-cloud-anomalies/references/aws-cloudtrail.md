
# AWS CloudTrail Anomaly Detection

`detection-cloud-anomalies` から呼ばれる variant 別 deep dive

## When to Use

- AWS account の継続監視で「平常から外れる」操作を浮き上がらせたい
- 被疑期間の log で異常を抽出する初動フェーズ
- detection rule (Sentinel / Splunk / OpenSearch) 開発時の baseline 設計

**使わない場面**: 既知 IOC を投げ込む reactive 検索（→ `cloud-forensics`）。

## Approach / Workflow

### Phase 1 — baseline の構築

```
- 30 〜 90 日の log を取得
- principal × eventName × source IP × region でカウント
- 各 principal の「平常 event」「平常 region」「平常 IP/ASN」を作る
- 出現頻度の z-score / IQR を計算
```

```python
import pandas as pd
df = pd.read_json('cloudtrail.jsonl', lines=True)
agg = df.groupby(['userIdentity.arn','eventName','sourceIPAddress']).size().reset_index(name='n')
```

### Phase 2 — 異常 signal

```
- 初出現の eventName (AssumeRole / CreateAccessKey / PassRole 等)
- 初出現の source IP / ASN / country
- 通常使わない region への活動 (ap-east-1, eu-north-1 等)
- 人間 user による短時間大量 API call (script 化兆候)
- service-account-only API を IAM user が叩く (逆も同)
- 失敗 access (errorCode) が急増
- console login が普段使わない IP / 地理
```

### Phase 3 — 高優先 event

```
- ConsoleLogin (no MFA / 不審 IP)
- CreateAccessKey / DeleteAccessKey
- CreateUser / CreateRole
- AttachUserPolicy / PutUserPolicy / AttachRolePolicy
- UpdateAssumeRolePolicy (Principal: * / 第三者 account)
- PassRole + service への role 付与
- AssumeRole の cross-account
- StopLogging / DeleteTrail / UpdateTrail (隠蔽)
- DeleteSnapshot / ModifySnapshotAttribute (Add)
- PutBucketPolicy (public)
- GetSecretValue 連発
- DecryptContext (KMS) 連発
```

### Phase 4 — pattern 検出 ルール例 (Athena SQL)

```sql
-- 短時間に複数 region から API call
SELECT useridentity.arn,
       count(distinct awsregion) as regions,
       array_agg(distinct awsregion) as r,
       date_trunc('hour', from_iso8601_timestamp(eventtime)) as h
FROM cloudtrail
WHERE eventtime BETWEEN ? AND ?
GROUP BY 1, 4
HAVING count(distinct awsregion) > 3;
```

```sql
-- console login no MFA from new IP
SELECT useridentity.arn, sourceipaddress, eventtime
FROM cloudtrail
WHERE eventname = 'ConsoleLogin'
  AND additionaleventdata LIKE '%MFAUsed":"No%'
  AND sourceipaddress NOT IN (SELECT ip FROM known_ips);
```

### Phase 5 — GuardDuty / Detective との相関

GuardDuty findings は CloudTrail 由来の異常を MITRE-mapped で alert。Detective が actor 中心の visual chain を提供。両者の出力と CloudTrail raw を突き合わせる。

### Phase 6 — alert 化と継続監視

```
- 高頻度 baseline 監視 (1 分単位の rolling z-score)
- 重大 event の immediate alert (StopLogging 等は即通知)
- 不審 IP allowlist / blocklist の運用
```

### Phase 7 — レポート / 検出 rule

```
- 期間 / 異常 event 件数
- 関与 principal / IP / region
- 推定攻撃 chain
- 推奨 detection rule (Sentinel / GuardDuty 補完)
- 推奨 IAM 縮小 / SCP 強化
```

## Tools

```
aws cli
Athena
Detective / GuardDuty
boto3 / pandas / numpy
WebFetch
Bash (sandbox)
```

# AWS CloudTrail Forensics

`cloud-forensics` の Phase 2 / Phase 5 から呼ばれる、AWS CloudTrail log を中核とした侵害された AWS 環境の attacker 行動再構成、compromised credentials 特定、IAM 改竄追跡。

## いつ切替えるか

- AWS account の侵害 / 不審活動の調査
- compromised access key / role による行動の追跡
- IAM 改竄 / 永続化機構の検出

## Phase 1 — CloudTrail の有効性

```bash
aws cloudtrail describe-trails
aws cloudtrail get-trail-status --name <trail>
aws cloudtrail get-event-selectors --trail-name <trail>
```

確認項目:

```
- 全 region trail (IsMultiRegionTrail=true)
- 全 log file integrity validation 有効
- management events + data events 両方
- S3 / KMS data event を取っているか
- log file の S3 暗号化と access policy
- 過去に StopLogging されていないか
```

## Phase 2 — log の取り込み

S3 から取得:

```bash
aws s3 sync s3://<trail-bucket>/AWSLogs/<acct>/CloudTrail/us-east-1/2024/01/15/ ./logs/
gunzip ./logs/*.json.gz
jq -s '[.[] | .Records[]]' logs/*.json > all-events.json
```

または Athena 経由で SQL 検索 (`detection-cloud-anomalies` の AWS reference 参照)。

## Phase 3 — actor / event 集約

```bash
# user 別 event 数
jq '.[] | .userIdentity.arn' all-events.json | sort | uniq -c | sort -rn

# event 別頻度
jq '.[] | .eventName' all-events.json | sort | uniq -c | sort -rn

# source IP
jq '.[] | .sourceIPAddress' all-events.json | sort | uniq -c | sort -rn
```

## Phase 4 — 危険 event の検出

```
ConsoleLogin                       MFA 使用有無 / source IP
CreateAccessKey                    新キー生成
DeleteAccessKey
UpdateAccessKey
CreateLoginProfile                 root の login profile (異常)
AttachUserPolicy / PutUserPolicy   権限追加
AttachRolePolicy
PassRole                           権限昇格 chain で頻出
AssumeRole                         cross-account / role 切替
StopLogging / DeleteTrail          log 停止 (隠蔽兆候)
PutBucketPolicy                    S3 公開化
DeleteBucket
RunInstances                       不審 EC2 起動
StartInstances / StopInstances
CreateSnapshot / ModifySnapshotAttribute  snapshot exfil
GetSecretValue                     secrets 大量取得
DecryptContext (KMS)
```

```bash
jq '.[] | select(.eventName == "ConsoleLogin")
        | {time:.eventTime, user:.userIdentity.arn, ip:.sourceIPAddress, mfa:.additionalEventData.MFAUsed}' all-events.json
```

## Phase 5 — IAM 改竄の追跡

```bash
jq '.[] | select(.eventName | IN("CreateUser","CreateAccessKey","AttachUserPolicy","PutUserPolicy","CreateRole","AttachRolePolicy","UpdateAssumeRolePolicy","CreateLoginProfile","AddUserToGroup"))' all-events.json
```

`UpdateAssumeRolePolicy` の AssumeRolePolicy が `Principal: *` 等の異常値になっていないか。

## Phase 6 — 横展開・cross-account

```
AssumeRole 連鎖を追う
  src account → cross-account role → 他 account のリソース
```

```bash
jq '.[] | select(.eventName == "AssumeRole")
        | {time:.eventTime, src:.userIdentity.arn, dst:.requestParameters.roleArn}' all-events.json
```

## Phase 7 — exfiltration 兆候

```
GetObject / S3 大量取得
CreateSnapshot + ModifySnapshotAttribute (Add)  → 別 account への共有
PutBucketPolicy (public) / PutObjectAcl (public-read)
ec2 RunInstances + ImportImage / ExportImage
```

```bash
jq '.[] | select(.eventName == "ModifySnapshotAttribute")
        | select(.requestParameters.createVolumePermission.add != null)' all-events.json
```

## Phase 8 — timeline / 攻撃 chain

```
時刻       event              actor                影響
HH:MM:SS   ConsoleLogin (no MFA) compromised-user 1.2.3.4
HH:MM:SS   CreateAccessKey       compromised-user
HH:MM:SS   AttachUserPolicy AdministratorAccess
HH:MM:SS   AssumeRole admin-role
HH:MM:SS   PutBucketPolicy public S3
HH:MM:SS   ModifySnapshotAttribute share to ext acct
HH:MM:SS   StopLogging
```

## Phase 9 — レポート

```
- 期間 / event 件数
- 関与した user / role / IP
- 攻撃 chain (MITRE ATT&CK Cloud Matrix 番号)
- 影響範囲 (snapshot / S3 / IAM)
- 残存リスク (key / role / policy / public bucket)
- 推奨対応 (key rotate / IAM 縮小 / GuardDuty / detection rule)
```

## Tools

```
aws cli
jq / pandas
Athena (SQL on CloudTrail logs)
GuardDuty findings
Detective (visual chain)
WebFetch
Bash (sandbox)
```

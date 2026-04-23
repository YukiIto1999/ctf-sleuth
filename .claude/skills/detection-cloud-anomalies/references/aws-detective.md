
# AWS Detective Threat Hunting

`detection-cloud-anomalies` から呼ばれる variant 別 deep dive

## When to Use

- GuardDuty / SecurityHub で alert が出て entity 周辺の挙動を可視化したい
- 攻撃 chain を時系列で再構成し IOC を pivot する
- CloudTrail / VPC Flow / DNS query を統合 graph として扱いたい

**使わない場面**: SQL ベースの ad-hoc 検索 (→ `detection-cloud-anomalies`)、構成不備の事前列挙 (→ `cloud-pentester`)。

## Approach / Workflow

### Phase 1 — Detective の有効化

```
- Organization の管理 account で Detective 有効化
- 各 member account を delegated administration で集約
- data sources: CloudTrail / VPC Flow Logs / GuardDuty / EKS audit (opt) / RDS DB Activity (opt)
```

Detective は最大 1 年分の data を behavior graph に蓄積。

### Phase 2 — entity 種別

```
- AWS Account
- IAM User / IAM Role / Federated User
- EC2 Instance
- IP address
- Finding (GuardDuty)
- AWS S3 Bucket
- EKS Cluster
```

各 entity の "profile panel" にアクセスして、24h / 7d / 30d 単位の活動量、ピーク発火、関連 entity を確認。

### Phase 3 — GuardDuty finding triage

```
1. SecurityHub / GuardDuty findings を Detective へ pivot
2. Investigate finding → 関連 entity (principal / IP / instance) を expand
3. timeline で finding 前後の API call 急増 / 失敗を確認
4. graph で 横展開 (assume role / cross-account) の path を検出
```

### Phase 4 — 重要 hunting query

#### 異常 API 急増

```
entity profile → "API call counts" → baseline と比較
24h 内に >>baseline → 列挙活動の兆候
```

#### 通常使わない API

```
entity profile → "Newly observed APIs"
attacker は新しい service を試す傾向 → 新規 API は要 triage
```

#### 海外 IP からの認証

```
entity profile → "Geolocations"
通常 region 外からの sign-in / API call
```

#### 失敗 → 成功遷移

```
"Failed API calls" の急増直後の "Successful API calls" → brute / enum 成功兆候
```

#### IAM Role の credentials が複数 IP

```
Role profile → "Resource interactions"
同 role の credentials が複数 source IP に出ていれば exfil token reuse
```

### Phase 5 — pivot 例

```
Finding (Recon:IAMUser/UserPermissions)
  → IAM user "compromised-u" profile
    → "Newly observed APIs": ListBuckets, GetBucketAcl, ListUsers
    → IP "1.2.3.4" profile
      → 他に何の entity と通信?
        → S3 bucket "secret-bucket" との大量 GetObject
        → EC2 instance i-xxxx (assumed role 経由)
```

### Phase 6 — レポート / 自動化

```
- 重要 finding の Detective URL を保存
- entity の profile snapshot を取得
- timeline を export して timeline.csv に
- 推定 attack chain
- 残存リスク
- 推奨対応 (key rotation / role 縮小 / GuardDuty rule 強化)
```

### Phase 7 — Limitation

```
- リアルタイムではない (data lag 数時間)
- 1 region region per graph (multi-region は別 graph)
- 分析を支援するツールであり、結論は人間が出す
```

## Tools

```
AWS Detective (Console)
GuardDuty
SecurityHub
aws cli (detective subcommands)
WebFetch
Bash (sandbox)
```

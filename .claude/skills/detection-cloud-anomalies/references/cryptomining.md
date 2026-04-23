
# Cryptomining Detection in Cloud

`detection-cloud-anomalies` から呼ばれる variant 別 deep dive

## When to Use

- 異常 cloud 課金が発生した、または GuardDuty / Defender が CryptoCurrency finding を出した
- compromise された credential 経由で大量 EC2 / VM / GPU が起動した疑い
- CTF DFIR で「請求が異常」型問題

**使わない場面**: マイニングそのものの解析（reverse engineering 視点）→ `reverse-engineering` / `ioc-hunting`。

## Approach / Workflow

### Phase 1 — billing 異常検知

```
AWS: Cost Explorer / Budget alert (急増)
     特に EC2-GPU (g4dn / p3 系)、Spot, Lambda 大量実行
Azure: Cost Management + alert
GCP: Billing alert / 予算超過
```

GPU instance / spot fleet が許可されていない account で起きるはずがない費用は要警戒。

### Phase 2 — control plane log

```
AWS CloudTrail:
  RunInstances (大量 / GPU / spot)
  RequestSpotFleet
  CreateFleet
  StartInstances
  CreateAutoScalingGroup
Azure:
  Microsoft.Compute/virtualMachineScaleSets/write
  Microsoft.Compute/virtualMachines/write (大量)
GCP:
  compute.instances.insert (大量)
  GKE NodePool 拡張
```

### Phase 3 — network 兆候

```
- 既知 mining pool への outbound (stratum+tcp:// / port 3333 / 4444 / 14444 等)
- xmrig binary download (github / pastebin / 自前 host)
- DNS query: pool.minexmr.com / xmr.mooo.com / supportxmr.com / ethermine.org
- 同 process が短時間に高 CPU / GPU 使用
```

VPC Flow Logs / NSG flow / VPC Service Controls / Cloud DNS log から抽出。

### Phase 4 — host 兆候

```
- xmrig / cpuminer / nbminer / phoenixminer / ethminer の process
- /tmp / /var/tmp / /dev/shm に dropper (kdevtmpfsi 等)
- cron: */5 * * * * curl http://... | sh
- systemd unit / init.d / .bashrc / cron に wget|curl 系永続化
- AWS metadata に short-lived credential が抜かれ、attacker AWS account で巨大 spot fleet 起動
```

### Phase 5 — IOC

```
file IOC:
  kdevtmpfsi / kinsing / xmrig / xmr-stak / nbminer / minerd / cpuminer
  /tmp/.X11-unix/X (隠し dropper)

network IOC:
  pool ドメイン list (gist で keep-up)
  port 3333 / 4444 / 14444 / 5555 / 7777 outbound

config:
  config.json with "pool": ... wallet: 4...

GuardDuty findings:
  CryptoCurrency:EC2/BitcoinTool.B!DNS
  CryptoCurrency:EC2/MinerActivity
```

### Phase 6 — KQL / SQL

#### CloudTrail Athena

```sql
SELECT useridentity.arn,
       count(*) as runs,
       array_agg(distinct json_extract_scalar(requestparameters, '$.instanceType')) as types
FROM cloudtrail
WHERE eventname IN ('RunInstances','RequestSpotFleet','CreateFleet')
  AND eventtime BETWEEN ? AND ?
GROUP BY useridentity.arn
HAVING count(*) > 5;
```

#### Azure / GCP は同等のログ source で。

### Phase 7 — 応答

```
1. compromise principal の credential rotate / disable
2. instance / fleet の即時 terminate
3. spot fleet / scale set 制限の設定
4. service quota の見直し (GPU instance 上限を 0 に)
5. budget alert + EventBridge / Logic Apps で auto remediation
6. forensic snapshot を取得してから terminate
```

### Phase 8 — レポート

```
- 期間 / 課金影響額
- 関与 principal / IP / instance ids
- attack chain (credential leak → run / fleet → mining)
- IOC (file / pool / wallet)
- 残存リスク
- 推奨対応 + 予防 (quota 制限 / detection rule / SCP)
```

## Tools

```
aws cli / az cli / gcloud
GuardDuty / Defender for Cloud / Security Command Center
Athena / Sentinel / BigQuery
falco (host runtime)
WebFetch
Bash (sandbox)
```

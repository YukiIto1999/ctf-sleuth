
# Cross-source Log Analysis (Forensic)

`endpoint-forensics` から呼ばれる variant 別 deep dive

## When to Use

- 複数 source (Windows event log / Linux syslog / firewall / proxy / app / cloud) を横断する
- timeline 統合 / IOC pivot / actor 行動の再現が必要
- live SIEM の代替として post-incident で log を解析したい

**使わない場面**: 単一 source 深掘り（→ `endpoint-forensics`、`network-analyzer`、`detection-cloud-anomalies` 等）。

## Approach / Workflow

### Phase 1 — log source 棚卸

```
- OS log (Windows EVTX / Linux syslog / journald / macOS unified log)
- 認証 (Active Directory / LDAP / SSO / OAuth provider)
- network (firewall / proxy / IDS / DNS / NetFlow)
- application (web access / app error / DB / message queue)
- endpoint (EDR / antivirus / sysmon)
- cloud (CloudTrail / Activity Log / Audit / Logging)
- email (mail server / spam filter)
```

### Phase 2 — 取得 / 整合性

```bash
sha256sum *.log *.evtx > evidence.sha256
gpg --sign evidence.sha256
```

network から live で取る場合は forwarder (rsyslog / NXLog / fluentd) で 1 ヶ所集約。

### Phase 3 — 正規化

各 source の固有 format を共通 schema に変換:

```
@timestamp        ISO8601 / UTC
host              source host
process / service
event_type        login / network_conn / file_write / process_exec / dns_query / http_req
user / role
src_ip / dst_ip / src_port / dst_port
file_path / file_hash
process_name / cmdline / parent_process
url / domain / status_code
raw_message       元 line
```

ツール:

```
plaso / log2timeline       → super-timeline (多くの source を理解)
splunk / OpenSearch        → ingestion + 検索
ELK (logstash + ES + Kibana)
Elasticsearch ECS schema   → field 共通化
osquery / fleet             → live endpoint クエリ
```

### Phase 4 — 相関分析

```
- 同 IP / user / host で複数 event 発火を相関 (auth → network → file → process)
- timeline を 1 本に並べて actor 行動を時間順に
- 単発 event でなく chain で語る (恐喝 / phishing / lateral 等)
- baseline (平常時 log) との差分
```

代表 query (KQL / SPL 風):

```
EventLog
| where timestamp between (start..end)
| where user == "victim"
| project timestamp, event_type, src_ip, dst_ip, process, cmdline
| sort by timestamp asc
```

### Phase 5 — IOC pivot

抽出した IOC を別 log に投げて広げる:

```
ip 1.2.3.4 → firewall log で他 host への接続を確認
domain x.com → DNS log / proxy log で他 user の query 確認
file_hash X → endpoint log / mail log で他 endpoint 観測
user U → auth log + app log で全アクセス
```

### Phase 6 — 攻撃 chain 再構成

```
1. initial access:    phishing email → 添付実行 / OAuth consent / VPN brute
2. execution:         malware / script / RDP
3. persistence:       autorun / cron / scheduled task / golden ticket
4. privesc:           local exploit / cred theft
5. defense evasion:   log clearing / process hide
6. cred access:       memory dump / keylog
7. discovery:         ローカル列挙 / AD enum
8. lateral:           remote exec / pass-the-hash
9. collection:        file gather / staging
10. exfiltration:     cloud upload / DNS tunnel / HTTP POST
11. impact:           encrypt / sabotage / data leak
```

### Phase 7 — 残存リスク

```
- IOC が他 host にも見えるか
- 永続化機構の網羅的除去状況
- credential reset 状況
- 検知 rule の追加（再発防止）
```

### Phase 8 — レポート

```
- 期間 / log source / 件数
- timeline (UTC)
- 攻撃 chain (MITRE ATT&CK 番号付加)
- IOC 一覧 (file / network / persistence / account)
- 推奨対応 / 検出 rule
- 参考 evidence (chain of custody / hash)
```

## Tools

```
plaso / log2timeline / psort
splunk / OpenSearch / ELK
osquery / fleet
sysmon (Windows)
auditd (Linux)
WebFetch
Bash (sandbox)
jq / awk / pandas
```

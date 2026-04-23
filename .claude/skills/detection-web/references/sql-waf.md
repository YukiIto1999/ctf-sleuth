
# Detecting SQL Injection via WAF Logs

`detection-web` から呼ばれる variant 別 deep dive

## When to Use

- WAF が前段にある対象で、攻撃 campaign のシグネチャを log から逆算する
- WAF が block した SQLi と、すり抜けた SQLi を区別したい
- 攻撃元 IP / payload 特性を IOC として運用に投入する
- CTF DFIR で web 侵害経路の確認

**使わない場面**: WAF を持たない構成（→ `detection-web`）、攻撃側で SQLi を仕掛ける（→ `exploiting-sql-injection-*`）。

## Approach / Workflow

### Phase 1 — log 取り込み

| WAF | 主要 log |
|---|---|
| ModSecurity | audit log (`SecAuditLog`) — `--A--`...`--Z--` ブロック |
| AWS WAF | CloudWatch Logs / Kinesis Firehose → S3 |
| Cloudflare | Logpush / Firewall Event API |
| Imperva | SecureSphere log forwarder |
| GCP Cloud Armor | Stackdriver |
| Akamai Kona | DataStream |

```python
import pandas as pd
df = pd.read_json('waf.log', lines=True)
# 主要 column: ts, ip, country, asn, action (BLOCK/ALLOW/CHALLENGE), rule_id, request_uri, payload
```

### Phase 2 — SQLi rule マッチの抽出

```python
SQLI_RULES = {
  'modsec': ['942100','942110','942120','942130','942140','942150','942160','942170','942180','942190','942200','942210','942220','942230','942240','942250','942260','942270','942280','942290','942300','942310','942320','942330','942340','942350','942360','942361','942370','942380','942390','942400','942410','942420','942430','942440','942450','942460','942470','942480','942490','942500','942510','942511','942520','942530','942540','942550','942560'],
  'aws':    ['AWSManagedRulesSQLiRuleSet','SQLi_*'],
  'cf':     ['100015','100016','100017','100018'],
}
sqli_hits = df[df['rule_id'].isin(SQLI_RULES['modsec']) | df['rule_id'].str.contains('SQLi', na=False)]
```

### Phase 3 — payload 同定

```python
import re
PATTERNS = {
  'union':   re.compile(r'\bUNION\s+SELECT\b', re.I),
  'tautology': re.compile(r"\bOR\s+\d+\s*=\s*\d+", re.I),
  'sleep':   re.compile(r'\b(SLEEP|pg_sleep|WAITFOR\s+DELAY|BENCHMARK)\(', re.I),
  'comment': re.compile(r'(--\s|#|/\*)', re.I),
  'hex':     re.compile(r'\b0x[0-9a-f]+\b', re.I),
  'union_obfusc': re.compile(r'\bUN/\*.*?\*/ION\b', re.I),
}
for name, p in PATTERNS.items():
    print(name, sqli_hits['payload'].str.contains(p).sum())
```

### Phase 4 — block vs allow の比較

```python
sqli_hits.groupby('action')['rule_id'].count()
# BLOCK が多くて 0 件 ALLOW なら防御成立
# ALLOW が混在 → bypass 兆候 (rule false negative or skipped)
```

bypass の典型:

- ASCII alternate (`/*!50000UNION*/`)
- 大量 whitespace / tab で signature 回避
- POST → multipart で content-type の WAF inspection 抜け
- gzip / chunked transfer で WAF が body を見れない
- HTTP/2 で header parsing 不一致
- 別 vhost / 別 path で WAF 適用外 (rule scope 抜け)

### Phase 5 — IOC 抽出

```python
top_ips = sqli_hits.groupby('ip')['ts'].count().sort_values(ascending=False).head(20)
top_uas = sqli_hits.groupby('ua')['ts'].count().sort_values(ascending=False).head(20)
top_paths = sqli_hits.groupby('request_uri')['ts'].count().sort_values(ascending=False).head(20)
```

ASN / country で集約し、botnet / known bad ASN を highlight。

### Phase 6 — 後段ログとの相関

WAF を通った request が後段で 5xx / 200 / 異常応答していないか:

```python
# WAF allow した SQLi request の 5xx 率
allowed = sqli_hits[sqli_hits['action']=='ALLOW']
backend = pd.read_json('app.log', lines=True)
joined = allowed.merge(backend[['request_id','status','latency']], on='request_id', how='left')
joined['status'].value_counts()
```

500 / 異常 latency が出ていれば「WAF 抜けて backend で何か起きた」徴候。

### Phase 7 — alert / IOC 共有

```
- 攻撃元 top IP / ASN / country
- 使用 payload pattern (signature)
- bypass された rule_id
- 影響を受けた endpoint
- 推奨 (rule 強化 / app 側 修正 / IP block)
```

### Phase 8 — レポート

```
- 期間 / 全 SQLi event 件数
- block 率 / bypass 兆候の有無
- IOC (IP / UA / payload / path)
- 後段で発火したか (status code / latency)
- 推奨対応
```

## Tools

```
pandas / numpy
ModSecurity audit log parser
AWS Athena (CloudWatch Logs に対する SQL)
jq
GeoIP2
splunk / OpenSearch
WebFetch
Bash (sandbox)
```

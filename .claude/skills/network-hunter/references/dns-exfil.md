
# DNS Log Exfiltration Analysis

`network-hunter` から呼ばれる variant 別 deep dive

## When to Use

- 大量 DNS log (zeek dns.log / Sysmon DNS / DNS server query log) を解析
- DNS tunnel / exfil / DGA / NXDOMAIN burst の検出
- malware の DNS C2 識別

**使わない場面**: pcap 単発検査 (→ `network-analyzer`、`network-hunter`)。

## Approach / Workflow

### Phase 1 — log source と前処理

```
zeek dns.log:    ts / id.orig_h / id.resp_h / query / qtype_name / answers / rcode
Sysmon EID 22:   QueryName / QueryStatus / QueryResults
DNS server log:  bind 9 query log / unbound debug log
Cloud:           Route53 Resolver query log / GCP Cloud DNS / Azure DNS
```

```bash
zeek-cut ts id.orig_h query qtype_name rcode answers < dns.log > dns.tsv
```

### Phase 2 — exfil 兆候

```
- query 長 > 60 chars
- subdomain part の entropy 高
- 同一 user / host から短時間に大量 query
- TXT / NULL / CNAME 多用
- response code NXDOMAIN 連発 (DGA 兆候)
- query 増加が普段の baseline から大きく外れる
```

```bash
# 長 query
awk '{ if(length($4)>60) print }' dns.tsv | head

# entropy
python -c "
import math, sys
for line in sys.stdin:
    q = line.split('\t')[3]
    if not q: continue
    counts = {}
    for c in q: counts[c]=counts.get(c,0)+1
    e = -sum((v/len(q))*math.log2(v/len(q)) for v in counts.values())
    if e>4.0: print(line.strip(), e)
" < dns.tsv

# NXDOMAIN burst
awk '$5==\"NXDOMAIN\"' dns.tsv | awk '{print $2}' | sort | uniq -c | sort -rn | head
```

### Phase 3 — DGA 検出

DGA: 日付 + seed の hash で domain を生成、attacker は同 algorithm で先回り登録。client は失敗 multi 後に成功 1 つ叩く。

```
- query した domain の TLD 分布 (.top / .xyz / .info 系に偏る)
- 文字数固定 / 連続子音多 / pronounceable でない
- ML 分類器 (DGA detection) に feed
- NXDOMAIN 率高い + 次の 1 つだけ NOERROR
```

`dga_detector.py` 系 OSS / DGArchive (Fraunhofer) との突合で family 推定。

### Phase 4 — DNS tunnel 検出

`network-hunter` の手順を実行。指標:

```
- TXT / NULL の use ratio
- 同一 2nd-level domain への大量 unique subdomain
- query 長の分布が 50-200 に集中
- timing: 自然 traffic は人間操作で間欠、tunnel は連続
```

### Phase 5 — 既知 family fingerprint

```
- DNSpionage / Karkoff
- DnsCat2 (toolkit, port 53 raw)
- Iodine
- DNS-Shell
- COBALT MIRAGE / Pioneer Kitten (state actor)
```

YARA / Suricata / Zeek script の公開 ruleset と突合。

### Phase 6 — 横展開 / 影響評価

```
- 同 internal IP が外部 DNS resolver を bypass しているか (DoH / DoT)
- 異常 query を出している host の他 log (process / network)
- DNS server / resolver の log が改竄されていないか
```

### Phase 7 — 応答

```
- 該当 domain を sinkhole (RPZ / firewall block)
- internal client の network 隔離
- DoH / DoT の internal 利用方針見直し
- DNS server query log retention 強化
```

### Phase 8 — レポート

```
- 期間 / log 件数
- 検出 indicator (長 query / NXDOMAIN burst / DGA cluster / TXT 多用)
- 推定 family
- 関連 host
- 推奨対応 (sinkhole / RPZ / SIEM rule)
```

## Tools

```
zeek (dns.log)
splunk / OpenSearch (KQL/SPL)
DGA detector (公開 OSS)
Pi-hole / RPZ (sinkhole)
WebFetch
Bash (sandbox)
```

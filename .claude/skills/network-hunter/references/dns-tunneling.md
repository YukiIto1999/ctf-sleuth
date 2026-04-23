
# Zeek DNS Tunnel Hunting

`network-hunter` から呼ばれる variant 別 deep dive

## When to Use

- Zeek が dns.log を出している環境
- 継続的な DNS tunnel 検出 rule を運用
- 既知 tool (iodine / dnscat2 / DNSExfiltrator) の identification
- `network-hunter` の Zeek 特化版

**使わない場面**: pcap 単発 (→ `network-analyzer`)、log source が違う環境 (→ `network-hunter`)。

## Approach / Workflow

### Phase 1 — dns.log の field

```
ts                   timestamp
uid                  zeek connection uid
id.orig_h            client
id.resp_h            DNS server
query                DNS query name
qtype_name           A / AAAA / CNAME / TXT / MX / SRV / NULL
answers              array
rcode                NOERROR / NXDOMAIN / SERVFAIL / REFUSED
rejected
rtt                  round trip time
```

### Phase 2 — 検出 metric

```
1. query length distribution
   - 50 chars 超を高頻度に出す client は tunnel 候補
2. unique subdomain count per registered domain
   - 同 SLD に > 100 subdomain は tunnel
3. TXT / NULL 多用
   - 一般 client は AAAA / A / CNAME
4. timing 一定 (beacon)
5. NXDOMAIN burst (DGA)
6. encoding indicator: base32 / base64 / hex 文字列パターン
```

### Phase 3 — Zeek script 検出

```
# detect-dns-tunnel.zeek
@load base/protocols/dns

global query_lengths: table[addr] of vector of count;
event dns_request(c: connection, msg: dns_msg, query: string, qtype: count, qclass: count) {
    local src = c$id$orig_h;
    if (src !in query_lengths) query_lengths[src] = vector();
    query_lengths[src][|query_lengths[src]|] = |query|;
    if (|query| > 100) {
        NOTICE([$note=DNSTunnelLength,
                $msg=fmt("long DNS query length=%d from=%s q=%s",
                         |query|, src, query),
                $conn=c]);
    }
}
```

`zeek -r in.pcap detect-dns-tunnel.zeek` で notice.log に出力。

### Phase 4 — log 後処理 (zeek-cut + pandas)

```bash
zeek-cut ts id.orig_h query qtype_name < dns.log > out.tsv
```

```python
import pandas as pd
df = pd.read_csv('out.tsv', sep='\t', names=['ts','src','q','qt'])
# query 長 distribution per src
df['len'] = df['q'].fillna('').str.len()
df.groupby('src')['len'].describe().sort_values('mean', ascending=False).head()

# unique subdomain per registered domain
df['sld'] = df['q'].str.extract(r'([^.]+\.[^.]+)$')[0]
g = df.groupby(['src','sld'])['q'].nunique().reset_index().sort_values('q', ascending=False)
g.head(20)

# TXT / NULL 比率
ratio = df.groupby('src')['qt'].apply(lambda s: (s.isin(['TXT','NULL'])).mean())
ratio.sort_values(ascending=False).head()
```

### Phase 5 — 既知 tool fingerprint

```
iodine:    特定 subdomain pattern 'i' + base32 + version, NULL/TXT
dnscat2:   subdomain pattern with session id + sequence, TXT
DNSExfiltrator: base64 encoded subdomain, A query
DET / DNSlivery: 自前 stub
DNSStager:  base64 / base32 で payload を chunked
```

YARA-like / sigma で signature 化。

### Phase 6 — 警報 / 対応

```
- notice.log の DNSTunnel 系を SIEM に投入
- 該当 client を network 隔離
- 上流 resolver で SLD を sinkhole / RPZ block
- DNS server に rate limit + query log 強化
```

### Phase 7 — レポート

```
- 期間 / log 件数
- 検出 client / domain
- 推定 tool / family
- exfil 量 (推定 byte)
- 推奨 (sinkhole / FW / SIEM rule)
```

## Tools

```
zeek + zeek-cut
zeek scripting (detect rule)
pandas / numpy
sigma / suricata (rule)
WebFetch
Bash (sandbox)
```

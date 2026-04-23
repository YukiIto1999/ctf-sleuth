
# Zeek-based Traffic Analysis

`network-analyzer` から呼ばれる variant 別 deep dive

## When to Use

- Zeek が既存に展開済み (or 簡単に立てられる) で構造化 log を扱える
- pcap / live を 1 コマンドで多 log に分解
- Sigma / TI feed と連携して継続 hunting
- pcap が大きく tshark の per-packet 処理が重い

**使わない場面**: tshark 単発 (→ `network-analyzer`)、GUI 探索 (→ `network-analyzer`)。

## Approach / Workflow

### Phase 1 — pcap → log 変換

```bash
zeek -r in.pcap LogAscii::use_json=T
ls -la *.log
# conn.log / dns.log / http.log / ssl.log / x509.log / files.log / weird.log / notice.log
```

各 log は 1 record = 1 行 (TSV / JSON)。

### Phase 2 — 主要 log

```
conn.log    : flow 単位 (uid / 始終時刻 / src / dst / proto / orig_bytes / resp_bytes / state)
dns.log     : query / answer / rcode
http.log    : request / response / user-agent / referer / mime / status
ssl.log     : ja3 / ja3s / cert chain hash / SNI
x509.log    : cert 詳細 (subject / issuer / not_before / not_after)
files.log   : transferred file (filename / hash / mime / size / source)
weird.log   : 規格逸脱 (protocol violation 兆候)
notice.log  : built-in detector の alert
software.log: server software identification
```

### Phase 3 — query 例

```bash
# dns 異常 (TXT / 大量 / 長 query)
zeek-cut id.orig_h query qtype_name < dns.log | awk '$3=="TXT" || length($2)>50' | head

# beacon (定間隔 outbound)
zeek-cut ts id.orig_h id.resp_h < conn.log | sort -k2,3 | awk '
  {if(prev_src==$2 && prev_dst==$3) print $1-prev_t; prev_src=$2; prev_dst=$3; prev_t=$1}'

# JA3 fingerprint で 既知 malware client 識別
zeek-cut id.orig_h ja3 < ssl.log | sort | uniq -c | sort -rn

# 怪しい cert (self-signed / 短期 / fake CN)
zeek-cut subject issuer not_before not_after < x509.log
```

### Phase 4 — Zeek script

検出 logic を script (Zeek language) で:

```
# detect-long-dns-tunnel.zeek
event dns_request(c: connection, msg: dns_msg, query: string, qtype: count, qclass: count) {
    if (|query| > 60) {
        NOTICE([$note=Suspicious_DNS_Length,
                $msg=fmt("long DNS query: %s", query),
                $conn=c]);
    }
}
```

`zeek -r in.pcap detect-long-dns-tunnel.zeek` で適用。

### Phase 5 — Suricata / Snort 連携

Zeek + Suricata の組合せが定番。Suricata で signature 検知、Zeek で metadata 化。

```bash
suricata -r in.pcap -c suricata.yaml --runmode autofp
# eve.json に alert / dns / http / tls / fileinfo
```

### Phase 6 — TI / IOC との突合

threat intel feed (MISP / OTX / abuse.ch) の IP / domain / hash と zeek log を突合:

```bash
zeek-cut id.resp_h < conn.log | sort -u | grep -F -f known_bad_ips.txt
zeek-cut query < dns.log | sort -u | grep -F -f known_bad_domains.txt
zeek-cut sha1 < files.log | sort -u | grep -F -f known_bad_hashes.txt
```

### Phase 7 — frequency analysis

```bash
# beacon detection
zeek-cut ts uid id.orig_h id.resp_h orig_bytes resp_bytes < conn.log > flows.tsv
# pandas で:
import pandas as pd
df = pd.read_csv('flows.tsv', sep='\t', names=['ts','uid','src','dst','o','r'])
df['ts'] = pd.to_datetime(df['ts'], unit='s')
g = df.groupby(['src','dst'])
intervals = g['ts'].apply(lambda s: s.diff().dt.total_seconds().dropna())
# 標準偏差が小さく、平均が一定の組合せが beacon 候補
```

詳細: `network-hunter`、`network-hunter`。

### Phase 8 — レポート

```
- pcap / capture 期間 / log 件数
- 上位 talker
- 異常 query / cert / beacon
- IOC 突合結果
- 推奨対応 (signature / FW / SIEM)
```

## Tools

```
zeek (CLI) / zeek-cut
zeekctl (cluster 管理)
suricata (signature)
pandas / numpy (frequency)
WebFetch
Bash (sandbox)
```

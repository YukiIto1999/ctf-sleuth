
# Network Traffic Analysis with tshark (CLI / scripted)

`network-analyzer` から呼ばれる variant 別 deep dive

## When to Use

- 複数 pcap を 1 ショット集計したい
- script に組込んで定期 hunting / report 自動化
- GUI 起動が重く・大規模 pcap を扱う
- pyshark で 高度な per-packet logic を Python で書く

**使わない場面**: GUI で interactive に inspect (→ `network-analyzer`)、Zeek 主軸の hunt (→ `network-analyzer`)。

## Approach / Workflow

### Phase 1 — protocol hierarchy / endpoints

```bash
tshark -r in.pcap -q -z io,phs > stats-phs.txt
tshark -r in.pcap -q -z conv,ip > stats-ip-conv.txt
tshark -r in.pcap -q -z endpoints,tcp > stats-endpoints.txt
tshark -r in.pcap -q -z http,tree > stats-http.txt
tshark -r in.pcap -q -z dns,tree > stats-dns.txt
```

### Phase 2 — fields 抽出 (CSV ライク)

```bash
tshark -r in.pcap -Y 'http.request' \
  -T fields -E header=y -E separator=, -E quote=d \
  -e frame.time -e ip.src -e ip.dst -e http.request.uri -e http.host -e http.user_agent \
  > http-requests.csv

tshark -r in.pcap -Y 'dns.qry.name' \
  -T fields -E header=y -E separator=, \
  -e frame.time -e ip.src -e dns.qry.name -e dns.qry.type \
  > dns-queries.csv

tshark -r in.pcap -Y 'tls.handshake.extensions_server_name' \
  -T fields -E header=y -E separator=, \
  -e frame.time -e ip.src -e ip.dst -e tls.handshake.extensions_server_name \
  > tls-sni.csv
```

### Phase 3 — file 抽出

```bash
tshark -r in.pcap --export-objects http,./out_http
tshark -r in.pcap --export-objects smb,./out_smb
tshark -r in.pcap --export-objects imf,./out_email
```

抽出後 sha256sum + yara で family 推定。

### Phase 4 — 異常 hunt (CSV → pandas)

```python
import pandas as pd
df = pd.read_csv('http-requests.csv')

# 異常 user-agent
df.groupby('http.user_agent').size().sort_values(ascending=False).head(20)

# URI 長 (exfil 兆候)
df['len'] = df['http.request.uri'].fillna('').str.len()
df.sort_values('len', ascending=False).head(20)

# 同じ host への高頻度 / 同じ size の request (beacon 兆候)
df.groupby(['ip.dst', 'http.host']).size().sort_values(ascending=False).head(20)
```

### Phase 5 — pyshark で per-packet ロジック

```python
import pyshark
cap = pyshark.FileCapture('in.pcap', display_filter='dns')
for pkt in cap:
    name = pkt.dns.qry_name
    if len(name) > 60 or '.' in name and name.count('.') > 5:
        print(pkt.frame_info.time, pkt.ip.src, name)
```

`pyshark.LiveCapture` で live 解析も可能 (sandbox 内 sniff)。

### Phase 6 — 既知 hunt パターン

```bash
# 大量 short DNS query (DNS tunnel 兆候)
tshark -r in.pcap -Y 'dns.flags.response==0' \
  -T fields -e ip.src -e dns.qry.name | \
  awk -F. '{print $1, NF, length($0)}' | sort | uniq -c | sort -rn | head

# 定間隔 outbound (beacon)
tshark -r in.pcap -Y 'ip.dst==<dst>' -T fields -e frame.time_epoch | \
  awk 'NR>1{d=$1-prev; print int(d)} {prev=$1}' | sort -n | uniq -c | sort -rn | head

# port scan: 同 src から多数 dst port に SYN
tshark -r in.pcap -Y 'tcp.flags.syn==1 and tcp.flags.ack==0' \
  -T fields -e ip.src -e tcp.dstport | sort | uniq -c | sort -rn | head -50

# JA3 fingerprint
tshark -r in.pcap -Y 'tls.handshake.type==1' \
  -T fields -e ip.src -e tls.handshake.ja3_full | sort -u
```

### Phase 7 — レポート / IOC

```
- 期間 / packet 数 / 主要 protocol
- 上位 talker
- 抽出 artefact / hash
- 異常 hunt の hit
- IOC (IP / domain / hash / JA3 / URI pattern)
- yara / sigma rule の draft
```

## Tools

```
tshark / capinfos / editcap / mergecap
pyshark (Python)
pandas / numpy
zeek (補完的に)
yara
WebFetch
Bash (sandbox)
```

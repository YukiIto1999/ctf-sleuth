
# Network Traffic Analysis with Wireshark

`network-analyzer` から呼ばれる variant 別 deep dive

## When to Use

- pcap evidence の中身を GUI / CLI で精密 dissect
- protocol 異常 (retransmit / out-of-order / RST flood) の確認
- file 抽出 (HTTP object / SMB transfer)
- credential / cookie / authentication 取得

**使わない場面**: 自動化 batch 処理 (→ `network-analyzer` / `network-analyzer`)、概観 triage (→ `network-analyzer`)。

## Approach / Workflow

### Phase 1 — 起動と Display Filter の使い方

```
wireshark capture.pcap
```

主要 display filter:

```
ip.src == 1.2.3.4
ip.addr == 1.2.3.4
tcp.port == 443
tcp.flags.syn==1 and tcp.flags.ack==0     # SYN
tcp.analysis.retransmission                  # 再送
tcp.analysis.out_of_order
http.request.method == "POST"
http.host contains "evil"
dns.qry.name contains "."
dns.qry.type == 16                           # TXT
ssl.handshake.type == 1                      # ClientHello
tls.handshake.extensions_server_name == "example.com"
icmp.type == 8                               # echo request
arp.opcode == 2                              # reply (poisoning 兆候)
frame contains "FLAG{"                       # CTF flag
```

### Phase 2 — Statistics メニュー

```
Statistics → Conversations         IP / TCP / UDP の talker 一覧
Statistics → Endpoints
Statistics → Protocol Hierarchy
Statistics → I/O Graph              throughput 時系列
Statistics → DNS                    DNS query 統計
Statistics → HTTP → Requests
Analyze → Expert Information         プロトコル異常 highlight
```

### Phase 3 — Follow Stream

```
TCP / UDP packet を右クリック → Follow → TCP / UDP / TLS Stream
- HTTP / FTP / Telnet / SMTP の clear-text 内容
- SMB の file transfer
- 独自 protocol の構造把握
```

### Phase 4 — Export Objects

```
File → Export Objects → HTTP / SMB / IMF / TFTP / DICOM
```

抽出した binary は SHA-256 + yara → `ioc-hunting`。

### Phase 5 — TLS 復号

事前条件:

```
1. server / client が NSS Key log (SSLKEYLOGFILE) を出力していた
2. RSA private key が手元にある (PFS でない old TLS のみ)
```

設定: Edit → Preferences → Protocols → TLS → (Pre)-Master-Secret log filename。

### Phase 6 — Custom Dissector

独自 protocol の場合 Lua dissector を書ける:

```lua
local p = Proto("MyProto", "My Custom Protocol")
local f_type = ProtoField.uint8("myproto.type", "Type", base.HEX)
p.fields = { f_type }
function p.dissector(buf, pkt, tree)
    local t = tree:add(p, buf(0, 1))
    t:add(f_type, buf(0, 1))
    pkt.cols.protocol = "MyProto"
end
local tcp_table = DissectorTable.get("tcp.port")
tcp_table:add(12345, p)
```

### Phase 7 — tshark で batch / scripting

```bash
tshark -r capture.pcap -Y 'http.request' -T fields -e frame.time -e ip.src -e http.request.uri -e http.host
tshark -r capture.pcap -Y 'dns.qry.type==16' -T fields -e dns.qry.name -e dns.txt
tshark -r capture.pcap --export-objects http,./out
```

`--export-pdml` で XML 出力、`-T json` で JSON、Python pyshark から読み込み解析。

### Phase 8 — レポート

```
- pcap 概要 (期間 / 件数)
- 主要 protocol 比率
- 検出 indicator (異常 / 攻撃 / exfil)
- 抽出 artefact (file / credential)
- timeline
- 推奨対応
```

## Tools

```
wireshark / tshark / capinfos / editcap / mergecap
pyshark (Python wrapper)
NetworkMiner (補助 GUI)
yara
WebFetch
Bash (sandbox)
```

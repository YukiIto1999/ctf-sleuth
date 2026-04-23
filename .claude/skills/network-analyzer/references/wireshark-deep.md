
# Network Forensics with Wireshark

`network-analyzer` から呼ばれる variant 別 deep dive

## When to Use

- pcap 解析の playbook を 1 セット手順で進める
- IR で network 由来 evidence を統合してレポート化
- CTF forensics で pcap 解析チャレンジ

**使わない場面**: 自動 batch (→ `network-analyzer`)、Zeek 中心の hunt (→ `network-analyzer`)。

## Approach / Workflow

### Phase 0 — capture / 取得

ライブから取る場合:

```bash
sudo tcpdump -i eth0 -s 0 -G 600 -W 144 -w capture-%Y%m%d-%H%M%S.pcap
sudo dumpcap -i eth0 -b duration:600 -w capture.pcap
```

evidence 保全:

```bash
sha256sum capture*.pcap > capture.sha256
```

長時間 capture は `mergecap` で 1 file にまとめる、または `editcap -d` で 重複 packet を除去。

### Phase 1 — 概要把握

```bash
capinfos capture.pcap
tshark -r capture.pcap -q -z io,phs
tshark -r capture.pcap -q -z conv,ip
tshark -r capture.pcap -q -z conv,tcp
```

### Phase 2 — top talker / 異常 protocol

`network-analyzer` Phase 2 と同じ。期間内の baseline からの偏差を highlight。

### Phase 3 — credential / file 抽出

```
File → Export Objects → HTTP / SMB / IMF / TFTP
File → Extract Selected Packets → 別 pcap
tshark --export-objects http,./out_http
tshark -Y 'ftp.request.command in {USER, PASS}' で credential
```

### Phase 4 — TLS 解析

```
SNI: 平文 → 通信先 domain
JA3 / JA4: client fingerprint
証明書: subject / issuer / not_before / not_after
復号: SSLKEYLOGFILE があれば Wireshark の Preferences で key log を指定
```

### Phase 5 — protocol 異常 / 攻撃 pattern

```
- ARP poisoning / spoofing (`network-hunter`)
- DNS exfil / tunnel (`network-hunter`、`network-hunter`)
- C2 beaconing (`network-hunter`)
- port scan / sweep (SYN flood ratio)
- replay / session hijack (`replay-attack`)
- credential stuffing (HTTP login への高頻度 401 / 200 切替)
```

### Phase 6 — 攻撃 chain 再構成

```
時刻       packet       内容
HH:MM:SS   #123         victim → attacker.com   GET /malware.exe
HH:MM:SS   #235         victim → c2.evil.com    HTTP POST /submit (encrypted body)
HH:MM:SS   #498         victim → c2.evil.com    一定間隔 30s で beacon
HH:MM:SS   #1024        victim → 1.2.3.4         SMB 経由 lateral
HH:MM:SS   #2098         victim → exfil.host     大量 HTTPS upload
```

`network-analyzer` Phase 7 / `reverse-engineering` で typology を識別。

### Phase 7 — レポート

```
- pcap 識別 / 期間 / size
- 主要 protocol / talker
- 抽出 file (hash / 推定種別)
- 抽出 credential / token
- 検出 IOC (IP / domain / JA3 / URL pattern)
- 攻撃 chain (時系列)
- 残存リスク
- 推奨対応
```

## Tools

```
wireshark / tshark / tcpdump / dumpcap
mergecap / editcap / capinfos
zeek / suricata (補助)
NetworkMiner
yara
WebFetch
Bash (sandbox)
```

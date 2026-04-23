
# C2 Communication Analysis

`reverse-engineering` から呼ばれる variant 別 deep dive

## When to Use

- 不審 traffic に C2 channel が含まれる疑い
- 既知 family の variant の protocol 改変を確認
- detection rule (Suricata / Zeek / Sigma) を作成

**使わない場面**: malware sample 自体の rev (→ `reverse-engineering`)、fingerprint hunt のみ (→ `network-hunter` 等)。

## Approach / Workflow

### Phase 1 — channel 候補の identification

```
- HTTP / HTTPS                 最多
- DNS (TXT / NULL / CNAME)
- ICMP (data field encode)
- Raw TCP (custom port)
- WebSocket
- IRC                          legacy botnet
- email (IMAP / SMTP)          slow C2
- cloud SaaS (Slack / Discord / Telegram / GitHub Gist) abuse
- DNS over HTTPS (DoH)
- WireGuard / VPN tunneling
```

`zeek conn.log` で 全 talker、`http.log` / `dns.log` / `ssl.log` で protocol 観察。

### Phase 2 — 暗号 layer 同定

```
- 平文 (legacy / custom protocol)
- XOR (固定 key / rolling)
- RC4 (key の前 N byte が共有)
- AES (CBC / CTR / GCM)
- TLS (custom cert / 公開 CA)
- ChaCha20-Poly1305
- 独自 stream cipher
```

XOR / RC4 は payload を high entropy で zero-fill して key 推定。AES は static binary で key を抽出して decrypt。

### Phase 3 — 命令 / 応答の構造

代表 format:

```
[magic 4B] [length 4B] [type 1B] [payload]
[nonce 12B] [encrypted: cmd-id + args + timestamp]
JSON-RPC-like {"cmd":"shell","args":["id"],"id":1}
```

長期 capture から packet sequence と server 応答を pair で観察。

### Phase 4 — heartbeat / sleep 構造

```
- sleep 間隔 (60s / 300s / 3600s 系が多い)
- jitter ±20%
- domain rotation (DGA で日付変える)
- C2 list (primary → fallback → tertiary)
- failover trigger (HTTP 4xx / DNS NXDOMAIN)
```

`network-hunter` で frequency 解析。

### Phase 5 — 既知 protocol family

```
- Cobalt Strike Beacon: HTTP/HTTPS Malleable C2 profile
- Sliver: HTTPS / DNS / WireGuard / mTLS
- Empire: PowerShell + HTTPS
- Metasploit Meterpreter: TLV protocol over TCP/HTTP/HTTPS
- Quasar / AsyncRAT: TCP custom + AES
- njRAT: TCP custom + Base64 wrapper
- DarkComet: 独自 TCP
- Mirai: TCP 23 → /bin/busybox + report-server へ TCP
```

### Phase 6 — DGA (Domain Generation Algorithm)

```
- 日付 + seed の hash で daily domain
- 文字数固定 / TLD 固定パターン
- 抽出後 NXDOMAIN 率で C2 候補を絞る
```

DGA 抽出と algorithm 復元は `network-hunter`。

### Phase 7 — レポート / detection rule

```
- protocol summary (channel / encryption / 命令 format)
- IOC (IP / domain / cert hash / JA3 / URI pattern / User-Agent)
- detection rule の draft (Suricata / Zeek / Sigma)
- 推定 family
- 推奨 (TI feed 投入 / FW block / SIEM rule)
```

## Tools

```
wireshark / tshark / tcpdump
zeek / suricata
mitmproxy (TLS)
yara / sigma converter
WebFetch
Bash (sandbox)
```

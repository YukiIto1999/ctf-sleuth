
# Generic C2 Beacon Hunting

`network-hunter` から呼ばれる variant 別 deep dive

## When to Use

- 既存の SIEM / Zeek 出力から C2 beaconing 候補を 1 セット手順で抽出
- 複数 family / framework を横断して hunt したい
- `network-hunter` (frequency 部) と `network-hunter` (CS 特化) を統合

**使わない場面**: 個別 family deep dive (→ `network-hunter`)、DNS 特化 (→ `network-hunter`)。

## Approach / Workflow

### Phase 1 — input source

```
zeek conn.log / http.log / ssl.log / dns.log
SIEM (Splunk / Elastic) のフィルタ済 indexes
proxy log / firewall log
NetFlow / IPFIX
```

### Phase 2 — beacon scoring (RITA 風)

```
score = w1 * (1/CV(inter-arrival)) +
        w2 * (1/CV(payload size)) +
        w3 * histogram_skewness +
        w4 * connection_count_above_threshold +
        w5 * dst_uniqueness  (新規 / 既知 IP の対比)
```

各候補に score を付け、threshold 以上を triage queue に。

### Phase 3 — protocol layer の hint

| 層 | hunt 対象 |
|---|---|
| HTTP | URI pattern / 高頻度 GET + 同 size response / User-Agent rotation |
| HTTPS | JA3 / JA3S / cert subject / SNI 偽装 |
| DNS | 長 query / TXT 多用 / NXDOMAIN burst (→ `network-hunter`) |
| ICMP | data field 一定 size / 高頻度 echo |
| TCP raw | unusual port + 一定間隔 |
| WebSocket | long-lived + 一定 ping interval |

### Phase 4 — payload size signature

beacon は heartbeat / command 受信 で同 size:

```python
g = df.groupby(['src','dst','dport'])
g['orig_bytes'].agg(lambda s: s.std() / s.mean() if s.mean() else 1)
g['resp_bytes'].agg(lambda s: s.std() / s.mean() if s.mean() else 1)
```

両方 < 0.05 が beacon 強候補。

### Phase 5 — TI feed 突合

```
- abuse.ch SSL / JA3 / URLhaus / threatfox
- AlienVault OTX
- VirusTotal (有料 / API key)
- 公開 yara C2 ruleset
```

candidate dst を TI に問合せ、known bad なら confirmed。

### Phase 6 — 既知 framework

```
Cobalt Strike      → network-hunter
Sliver             → mTLS / DNS / HTTP profile (Sliver-specific JA3 / cert serial pattern)
Empire             → PowerShell encoded payload
Metasploit          → stage payload
Mythic              → 多 profile
Brute Ratel         → custom UA + 既知 cert
Havoc                → 静的 cert pattern
```

各 framework の公開 detection rule (Sigma / Suricata / Yara) を運用。

### Phase 7 — host context

network signal だけでなく endpoint log と pair:

```
- 同 src host で sysmon に不審 process (powershell -enc / rundll32 / regsvr32)
- 不審 service / scheduled task が新規作成
- LSASS / ntds dump 系の event
```

### Phase 8 — レポート / detection rule

```
- 検出 candidate (src / dst / framework / score)
- 関連 endpoint indicator
- 推奨対応 (network block / endpoint isolate / TI feed update)
- detection rule (Sigma / Zeek / Suricata)
```

## Tools

```
zeek / zeek-cut
RITA
pandas / numpy / scipy
suricata / sigma converter
TI feed (abuse.ch / OTX / VT)
WebFetch
Bash (sandbox)
```

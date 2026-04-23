
# Cobalt Strike Beacon Network Hunting

`network-hunter` から呼ばれる variant 別 deep dive

## When to Use

- 継続監視で Cobalt Strike beacon を検出
- malware sandbox 出力 / pcap から network 由来 IOC を抽出
- TI feed / yara / sigma の補完

**使わない場面**: binary config 抽出 (→ `reverse-engineering`)、profile 解析 (→ `reverse-engineering`)。

## Approach / Workflow

### Phase 1 — TLS cert fingerprint

CS team server の default cert は有名:

```
subject:    CN=Major Cobalt Strike, O=cobaltstrike, OU=AdvancedPenTesting
issuer:     同上
not_before / not_after の typical pattern
```

```bash
zeek-cut subject issuer < x509.log | grep -i cobalt
```

modify している attacker は別 cert を使うため、cert pin だけでは不十分。

### Phase 2 — JA3 / JA3S fingerprint

```
JA3 = ClientHello fingerprint
JA3S = ServerHello fingerprint
CS の default JA3:
  72a589da586844d7f0818ce684948eea (Java/8, default profile)
他 modified profile では異なる
```

```bash
zeek-cut id.orig_h ja3 ja3s < ssl.log | sort | uniq -c | sort -rn | head
```

abuse.ch SSL Blacklist / threatfox の JA3 リストと突合。

### Phase 3 — URI pattern

default profile / 公開 profile で出る URI:

```
GET  /pixel.gif / /load / /ca / /xx / /jquery-3.3.1.min.js
POST /submit.php / /submit / /api/getit / /jquery-3.3.2.min.js
```

```bash
zeek-cut id.resp_h uri user_agent < http.log | grep -E '/(pixel\.gif|load|ca|jquery-3\.[0-9]+\.[0-9]+\.min\.js)' | head
```

### Phase 4 — User-Agent pattern

default UA は 通常 browser を装う:

```
Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)
Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)
```

ただし profile で書換可能。組合せで判定。

### Phase 5 — sleep / jitter

`network-hunter` / `network-hunter` の手順で 周期 + jitter を検出。CS default は 60s + 0% (no jitter) → 改造で 60s + 20% / 30s + 30% など。

### Phase 6 — checksum8 path identification

CS の HTTP staging で URI が checksum8 値を持つことが知られている (古い version)。`/<4 byte>` の URI が頻発する場合 staging beacon の可能性。

### Phase 7 — sigma / suricata rule

```
suricata:
  alert tls any any -> any any (
    msg:"CS default cert subject CN";
    tls.cert_subject; content:"Cobalt Strike";
    sid:1000010; rev:1;
  )
zeek:
  event x509_certificate(c, der) {
    if ("Cobalt Strike" in c$subject) NOTICE([...]);
  }
```

### Phase 8 — レポート / IOC

```
- 検出 indicator (cert / JA3 / URI / UA / 周期)
- 推定 actor / watermark (config 抽出と pair で)
- 関連 victim host
- 推奨 (FW / TI feed / SIEM rule)
```

## Tools

```
zeek + zeek-cut
suricata
yara / sigma
abuse.ch (SSL / JA3 list / threatfox)
WebFetch
Bash (sandbox)
```

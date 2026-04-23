
# Cobalt Strike Beacon Configuration Extraction

`reverse-engineering` から呼ばれる variant 別 deep dive

## When to Use

- 不審 binary が Cobalt Strike Beacon の疑い
- pcap / memory dump からの config 抽出
- 既知 actor 識別 (公開 leak/cracked builder vs 私製)

**使わない場面**: Beacon 通信 traffic 自体の解析 (→ `reverse-engineering`、`network-hunter`)。

## Approach / Workflow

### Phase 1 — sample identification

```
- PE shellcode loader (.dll / .exe / .bin)
- payload は AES / xor で encode、loader が runtime decrypt
- famous strings: "%COMSPEC%", "ReflectiveLoader", "rundll32.exe"
- yara CobaltStrike rule (CS-Detect / Volexity / etc)
```

### Phase 2 — config structure

Beacon config は固定 byte sequence:

```
0x0001 0x0001 0x0002       BeaconType
0x0002 0x0001 0x0002       Port
0x0003 0x0002 0x0004       Sleeptime
0x0004 0x0002 0x0004       MaxGetSize
0x0005 0x0002 0x0004       Jitter
0x0007 0x0003 0x0100       PublicKey (RSA 256B)
0x0008 0x0003 0x0100       Server / GET URI
...
```

各 entry: `[id 2B] [type 2B] [length 2B] [value]`、type = 1 (short) / 2 (int) / 3 (binary)。

config 自体は XOR (0x69 / 0x2e ベース) または single-byte XOR で encode されており、pattern matching で sliding XOR で復号。

### Phase 3 — 自動抽出ツール

```bash
# Sentinel-One CobaltStrikeParser
python parse_beacon_config.py beacon.bin

# Didier Stevens 1768.py
python 1768.py beacon.bin

# Mandiant CobaltStrikeScan
csscan beacon.exe

# CobaltStrikeParser (Sentinel-One) は memory dump も対応
python parse_beacon_config.py --pcap traffic.pcap   # pcap から推定
```

### Phase 4 — 主要 config field

```
BeaconType:           HTTP / HTTPS / DNS / SMB / TCP
Port:
Sleeptime + Jitter:    e.g., 60s + 20%
MaxGetSize:
PublicKey:             RSA 公開鍵 (team server の private 鍵で署名)
Server:                C2 host / URI
Watermark:             builder license の hash (actor identification)
SpawnTo / SpawnTo_x86 / x64:    rundll32.exe / svchost.exe etc
KillDate:              YYYYMMDD で 自動 kill
HttpHeaders / GetUri / PostUri / Cookie / Useragent:    Malleable profile 反映
HostHeader:
DNS_Idle / DNS_Sleep:  DNS C2 用
HttpPostChunk:
```

### Phase 5 — Malleable C2 profile

profile は team server で設定するが、beacon 内に GET/POST URI / 期待 header / response の形が埋め込まれる。observed traffic と config を突合して profile reuse を確認。

### Phase 6 — 既知 watermark / family

```
- 公開された default watermark = 開発元
- 0x5e98aa02 / 0x305419c8 等の特定値 = 既知 leaked builder
- watermark 0 = trial / cracked
- 既知 watermark + actor 紐付け表 (Talos / Mandiant / WhichBacon)
```

### Phase 7 — レポート / detection rule

```
- BeaconType / C2 (host / port / URI)
- Sleep / Jitter / KillDate
- watermark + 推定 actor
- profile (GET/POST template, User-Agent)
- yara / sigma / Suricata rule
- TI feed 投入用 IOC
```

## Tools

```
parse_beacon_config.py (Sentinel-One)
1768.py (Didier Stevens)
csscan (Mandiant)
ghidra / IDA (loader rev)
yara
WebFetch
Bash (sandbox)
```

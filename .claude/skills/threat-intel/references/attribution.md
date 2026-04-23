
# Campaign Attribution Analysis

`threat-intel` から呼ばれる variant 別 deep dive

## When to Use

- 検出された incident / campaign を既知 actor / 新規 cluster に紐付ける
- TI feed / 報告書を作成する前の estimation
- IR でのリスク評価補助

**使わない場面**: 単発の IOC 確認 (→ `ioc-hunting`)、actor 別の TTP coverage 評価 (→ `threat-intel`)。

## Approach / Workflow

### Phase 1 — evidence 集約

```
TTP:      MITRE ATT&CK technique 一覧
infra:    IP / domain / TLS cert / hosting / ASN
code:     binary / script / 暗号 routine / 関数 layout
lang:     文字列の言語 / コメント / build path / locale
infra reuse:  過去 campaign と同 IP / domain / cert
timing:   active 時間帯 (timezone hint)
target:   業界 / 地域 / 役職
motivation: financial / espionage / hacktivist / state-sponsored
```

### Phase 2 — Diamond Model

各 incident を Diamond の 4 頂点で記述:

```
Adversary:  推定 actor / cluster
Capability: malware / TTP / 暗号化 routine
Infrastructure: C2 / staging / domain
Victim:     業界 / 地域 / 規模
```

各頂点を 別 incident と比較し overlap で attribution の根拠強度を測る。

### Phase 3 — TTP 比較

ATT&CK ID 単位で 過去 campaign / 既知 actor との一致を計算:

```
Jaccard 類似度 = |共通 TTP| / |Union TTP|
> 0.5 で 強い類似
< 0.2 は弱い類似
```

ただし TTP は actor 間で reused されるので、TTP 一致だけで attribution しない。

### Phase 4 — infra 比較

```
- 同 IP / domain / ASN を別 actor の campaign で使ったか (TI feed 突合)
- TLS cert (subject / issuer / fingerprint) reuse
- domain registration: registrant email / WHOIS pattern
- DNS pattern (DGA seed / TTL)
- C2 software (Cobalt Strike watermark / Sliver fingerprint)
```

infra reuse は actor identification の強力な指標。

### Phase 5 — code 比較

```
- binary similarity (TLSH / ssdeep / imphash / TLSH cluster)
- 関数 layout (BinDiff)
- 暗号 routine の constants / IV / key generation
- string fingerprint (debug paths / pdb name)
- compilation timestamp (PE Rich header / Mach-O LC_BUILD_VERSION)
- protocol-level fingerprint (HTTP magic / packet structure)
```

### Phase 6 — 言語 / 文化的指標

```
- 文字列 / error message の言語 / encoding
- comment 残存 (rare、stripped でも debug path に残る)
- timezone (compile time / active hours)
- holiday pattern (中国 / ロシア / イラン / 北朝鮮の祝祭)
- target geography (露語圏は Russian-speaking actor 系)
```

### Phase 7 — confidence 表記 (ICD 203 風)

```
high confidence:    ≥ 80% — 強い infra reuse + TTP 多重一致 + code reuse
moderate:           50-80% — TTP / infra 一部一致
low:                20-50% — 1-2 indicator のみ
information:        < 20% — 観察のみ
```

attribution はあくまで estimation。偽旗 (false flag) の可能性も検討。

### Phase 8 — レポート

```
- 該当 campaign 概要
- 観測 TTP / infra / code / lang
- 既知 actor との比較 + similarity score
- 推定 actor + confidence (information / low / moderate / high)
- 誤帰属の余地 (reused infra / 偽旗の可能性)
- 推奨 (引き続き hunt / TI feed 投入 / 共有先)
```

## Tools

```
MITRE ATT&CK Navigator
MISP (cluster / event)
TLSH / ssdeep / BinDiff
WHOIS / passive DNS / cert transparency
WebFetch / WebSearch
Bash (sandbox)
```

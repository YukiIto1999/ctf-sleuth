---
name: dfir
description: Digital Forensics と Incident Response の総合 wrapper。Windows event log / Sysmon / memory / disk / network / cloud log を相関し、攻撃 chain と影響範囲を再構成する。CTF DFIR / IR engagement で発火。
category: dfir
tags:
  - dfir
  - incident-response
  - forensics
  - timeline
  - mitre-attack
---

# DFIR (Digital Forensics & Incident Response)

## When to Use

- 検出された incident に対する調査
- 多 source (endpoint / network / cloud / mailbox) の evidence を統合
- IR の playbook 適用 (preparation / identification / containment / eradication / recovery / lessons-learned)

**使わない場面**: 単一 source / artefact の deep dive (→ `memory-analysis`、`disk-forensics` 等の個別 skill)、active 攻撃 (→ `red-teamer`)。

## Approach / Workflow

### Phase 1 — preparation (engagement / 平時)

```
- IR plan の存在 / playbook
- log retention (90+ 日 / 1 年)
- 取得 tool の準備 (winpmem / LiME / FTK Imager / KAPE / dc3dd)
- forensic workstation の整備
- chain of custody form
- 連絡先 (法務 / HR / vendor)
```

### Phase 2 — identification

```
- alert / anomaly 検出 (EDR / SIEM / NDR / DLP / user 報告)
- 影響範囲の初期推定
- prioritization
- 関係者 escalation
```

### Phase 3 — evidence acquisition (揮発性順)

```
1. live RAM dump (`memory-analysis` / `memory-analysis`)
2. process / network / login state スナップショット
3. shell history / log の現状コピー
4. disk image (read-only / write blocker / dc3dd / ewfacquire)
5. cloud control plane log (`cloud-forensics` / `detection-cloud-anomalies`)
6. mailbox (`disk-forensics`)
```

各 artefact に SHA-256 + chain of custody form。

### Phase 4 — Triage 並走

```
memory:    memory-analysis / memory-analysis / memory-analysis
disk:      disk-forensics / disk-forensics / disk-forensics / disk-forensics / disk-forensics / disk-forensics
log:       endpoint-forensics / endpoint-forensics / container-forensics / detection-cloud-anomalies / cloud-forensics / detection-cloud-anomalies
network:   network-analyzer / network-analyzer / network-analyzer / network-analyzer / reverse-engineering / network-hunter / network-hunter
endpoint:  endpoint-forensics / rootkit-analysis / rootkit-analysis
malware:   reverse-engineering / reverse-engineering / reverse-engineering / ioc-hunting / ioc-hunting
cloud:     cloud-forensics / detection-cloud-anomalies / detection-cloud-anomalies / detection-cloud-anomalies / cloud-forensics / cloud-forensics / detection-cloud-anomalies
attribution: threat-intel / threat-intel / threat-intel / threat-intel / ioc-hunting
```

### Phase 5 — 攻撃 chain 再構成 (MITRE ATT&CK Matrix)

```
initial access → execution → persistence → privilege escalation → defense evasion →
credential access → discovery → lateral movement → collection → command and control →
exfiltration → impact
```

各 phase に観測された TTP (T1xxx) を tag。

### Phase 6 — containment

```
- network 隔離 (FW deny / VLAN remove / SDN segment)
- compromised credential の rotation
- cloud token revoke
- 不審 process kill / 隔離
- evidence は残しつつ脅威拡大を止める (snapshot 取得後 isolate)
```

### Phase 7 — eradication / recovery

```
- malware 完全除去 (snapshot ベース restore / OS 再インストール)
- 永続化機構の網羅的除去
- patch 適用 / config hardening
- IDS / EDR rule 強化
- compromised account の reset
- 通信回路 (proxy / FW) のリストア
```

### Phase 8 — lessons-learned

```
- timeline (UTC) 完成
- 攻撃 chain (MITRE)
- impact 評価
- 残存リスク
- detection gap
- 推奨 (rule / control / training)
- regulatory 報告 (GDPR / HIPAA / 他)
```

### Phase 9 — レポート

```
- executive summary (3 段)
- timeline
- 攻撃 chain (MITRE)
- IOC 一覧
- containment / eradication 状況
- 残存リスク
- 推奨対応
- 参考 evidence (chain of custody / hash)
```

## Tools

```
memory: volatility3 / rekall / LiME / winpmem
disk:   dc3dd / ewfacquire / sleuthkit / autopsy / KAPE / plaso / log2timeline
log:    splunk / OpenSearch / sigma / Sentinel / Athena
network: wireshark / tshark / zeek / suricata
endpoint: sysmon / EDR (CrowdStrike / SentinelOne / Defender)
cloud:   AWS CLI / Azure / gcloud / scout-suite / Detective / GuardDuty
threat-intel: MISP / OpenCTI / VirusTotal / abuse.ch
WebFetch / WebSearch
Bash (sandbox)
```

## Related Skills

- `red-teamer` (defensive 視点での反対側理解)
- `essential-tools`, `coordination`

## Rules

1. **integrity** — 全 artefact SHA-256
2. **chain of custody**
3. **timezone** — UTC で統一
4. **PII redaction** — 共有 report で
5. **regulatory compliance** — 国内法 / GDPR / HIPAA / ISO27001 など報告義務確認

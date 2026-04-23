
# Network Traffic Analysis for Incidents

`network-analyzer` から呼ばれる variant 別 deep dive

## When to Use

- 既知 incident に対する pcap 解析（baseline 比較が必要）
- multi-host capture を相関して攻撃 chain を再構成
- SIEM / NDR / EDR の alert と pcap を突合

**使わない場面**: malware 中心の network 解析（→ `reverse-engineering`）、threat hunting (→ `hunting-for-*`)。

## Approach / Workflow

### Phase 1 — incident 範囲

```
- 検出 alert (EDR / SIEM / IDS) の時刻 + IOC
- 関連 host / segment
- 既知 IOC (IP / domain / hash / JA3)
```

### Phase 2 — 時系列 anchor

```bash
# alert 時刻周辺 ±10 min を抽出
editcap -A '2024-01-15 12:50:00' -B '2024-01-15 13:10:00' in.pcap window.pcap

# 該当 host のみ
tshark -r in.pcap -Y 'ip.addr == <victim>' -w victim.pcap
```

### Phase 3 — chain 再構成 (per phase)

```
initial:    どの protocol で attacker が触れた (HTTP / SMB / RDP / SSH)
foothold:   実行された binary が download された経路 / hash
discovery:  内部 scan / SMB 列挙 / DNS query 増加
lateral:    別 host への接続 (SMB / WMI / RDP / SSH)
exfil:      巨大 upload / 不審 cloud storage / DNS tunnel
impact:     ransomware 兆候 (SMB write 異常 / shadow copy delete)
```

### Phase 4 — multi-host correlate

```
zeek conn.log で 全 talker と byte カウント
victim_A → attacker_A → attacker_B → victim_B のパスを描く
時刻順 + protocol で graph 化
```

### Phase 5 — alert との突合

```
- IDS alert ID と pcap の packet (時刻 + 5tuple) を紐付け
- false positive / true positive を判定
- IDS rule の改善余地
```

### Phase 6 — レポート

```
- 期間 / scope / host
- 攻撃 chain (timeline + protocol + IOC)
- 影響範囲 (compromised host / data)
- IDS alert との対応
- 残存リスク
- 推奨 (rule / patch / segmentation)
```

## Tools

```
wireshark / tshark / tcpdump
zeek / suricata
mergecap / editcap
SIEM (splunk / elastic) 連携
WebFetch
Bash (sandbox)
```

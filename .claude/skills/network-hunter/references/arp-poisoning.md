
# ARP Poisoning Detection

`network-hunter` から呼ばれる variant 別 deep dive

## When to Use

- 同一 LAN 内の通信に ARP poisoning / MITM の疑い
- pcap に ARP reply 大量 / IP-MAC mapping の不整合
- 内部 network audit / penetration test の防御視点

**使わない場面**: WAN 経由の MITM (BGP / TLS hijack)、wireless 系 (→ `wifi-security`)。

## Approach / Workflow

### Phase 1 — pcap 解析

```bash
tshark -r capture.pcap -Y 'arp' -T fields \
  -e frame.time -e arp.opcode -e arp.src.proto_ipv4 -e arp.src.hw_mac -e arp.dst.proto_ipv4 -e arp.dst.hw_mac
```

確認:

```
- 同一 IP に対する MAC が短時間に変化
- 1 つの MAC が複数 IP の "owner" を主張
- gratuitous ARP (src=dst の broadcast announce) の連発
- ARP reply が request 無しに発生
- MAC vendor (OUI) が不釣り合い (例: gateway IP に Realtek consumer MAC)
```

### Phase 2 — wireshark expert info

```
Statistics → Resolved Addresses で IP-MAC 一覧
Analyze → Expert Information で ARP 異常 highlight
```

### Phase 3 — live host での検出

```bash
arp -a                                     # 現状 ARP table
ip neigh
arpwatch -d                                 # 変更通知
arping -I eth0 <target_ip>                 # ARP 応答確認

# 監視
tcpdump -i eth0 'arp' -nnvv

# tool
ettercap -T -M arp:remote /// ///         # 攻撃側 (検出/演習用)
arpoison ...                                # 攻撃側
arpspoof ...                                # 攻撃側
```

監視側 tool:

```
arpwatch (notification daemon)
arpalert
shellterm の static ARP entry 設定
```

### Phase 4 — switch 側防御

```
Cisco: Dynamic ARP Inspection (DAI) + DHCP Snooping
       ip arp inspection vlan <id>
       ip dhcp snooping vlan <id>
HP:    Dynamic ARP Protection
Juniper: arp-inspection
```

DAI は untrusted port の ARP を DHCP snooping binding と突合し不一致を drop。

### Phase 5 — TLS / 暗号化通信での影響評価

ARP poisoning 成功 → MITM ができても TLS は HSTS / cert pin / DNSSEC / DoT で防げる。確認:

```
- 内部通信で平文 (HTTP / FTP / Telnet / SNMP v1) があるか
- TLS pinning なしのアプリが LAN 内通信していないか
- HTTPS の internal CA 強制で MITM cert を信用させているか
```

### Phase 6 — レポート / 修正

```
- 期間 / 該当 LAN / VLAN
- 攻撃 / 検出 indicator
- 平文通信の存在
- 推奨 (DAI / DHCP snooping / static ARP / 802.1X / VLAN segmentation)
```

## Tools

```
tshark / wireshark
arpwatch / arpalert
arping / arp / ip neigh
Cisco DAI / Juniper arp-inspection
WebFetch
Bash (sandbox)
```

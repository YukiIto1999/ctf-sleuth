# Active Directory ACL Abuse

`system` の Phase 4 から呼ばれる、AD の ACL misconfiguration (GenericAll / GenericWrite / WriteOwner / WriteDacl / DCSync / ResetPassword 等) の検出と攻撃 path の特定。

## いつ切替えるか

- AD compromise の調査 / pentest 評価
- domain controller 周辺の特権昇格 path 探索
- 自社 AD の継続 audit (tier-zero 隔離)

## Phase 1 — collection

```
SharpHound (Windows):
  SharpHound.exe -c All --zipfilename collection.zip

BloodHound CE (Python):
  bloodhound-python -d <domain> -u <user> -p <pass> -ns <dc_ip> -c All

ldap3 (Python script):
  bind LDAP / S → query (ntSecurityDescriptor / objectSid / memberOf 等)
```

`-c All` は session / share / cert / ADCS まで含む。重い env では `-c DCOnly` で先導。

## Phase 2 — BloodHound import + query

```
Neo4j browser → BloodHound GUI に collection.zip を import
Query:
  - "Find all Domain Admins"
  - "Shortest paths to Domain Admins"
  - "Find Principals with DCSync rights"
  - "Find AS-REP Roastable users"
  - "Find Kerberoastable users"
  - "Find computers without LAPS"
  - "Pre-built queries" メニューから複数試行
  - 自前 cypher: MATCH (n:User)-[r:GenericAll]->(m) RETURN n,m
```

## Phase 3 — 危険 ACL 種別

```
GenericAll:        対象 object 全制御 (password reset / shadow credentials)
GenericWrite:      属性書込 (servicePrincipalName 追加 / msDS-AllowedToDelegateTo)
WriteOwner:        owner を変更 → 自分が GenericAll
WriteDacl:         ACL を変更 → 任意 ACL 追加
ForceChangePassword: password reset
AddSelf:           自分自身を group member に追加
AddMember:         group member 追加
ResetPassword:
DCSync (Replicating Directory Changes + 〃 All):
                   全 user の hash を DRSUAPI 経由 dump
GetChangesAll:     DCSync の subset
ReadGMSAPassword:  Group Managed Service Account の password 読取
ReadLAPSPassword:  LAPS のローカル admin pwd 読取
AllowedToAct (RBCD): Resource-Based Constrained Delegation の登録
```

## Phase 4 — 攻撃 path

```
1. 一般 user → GenericAll → group → group → DA group
2. user → WriteOwner → group → group の member 追加 → 特権
3. user → DCSync (Replicating Directory Changes All) → krbtgt hash → Golden Ticket
4. machine account → AllowedToAct → RBCD → S4U2Self/S4U2Proxy → DA impersonate
5. user → ReadGMSAPassword → service account → service-level admin
6. user → ForceChangePassword → admin user
7. ASREProast → kerberoast → cracked → service account
```

## Phase 5 — exploitation tools

```
Rubeus:                  asreproast / kerberoast / TGT TGS 操作
Mimikatz / dpapi:        DCSync / golden ticket
PowerView / SharpView:   ACL 直接操作
ntlmrelayx (impacket):   relay / RBCD / ADCS attack
Certipy:                 ADCS template / SAN abuse / ESC1-ESC11
NetExec (CrackMapExec):  spray / exec / dump
```

## Phase 6 — 防御 (tier-zero 隔離)

```
- DA group は tier-0 (member 数最小化)
- service account の管理権限 minimization
- LAPS で local admin password 自動 rotation
- gMSA 推奨
- privileged access workstation (PAW)
- Just-in-Time / Just-Enough-Access (JIT/JEA)
- Protected Users group
- adminCount=1 の object を全 audit
- ACL inheritance の review
- ADCS template の SAN supply 制限
```

## Phase 7 — 監査 / 検出

```
event log:
  - 4662  object access (DCSync 検出は 4662 + Replicating Directory Changes properties)
  - 4720  user create
  - 4732  member of security group
  - 5136  directory service object modify
  - 4728  member added to global group
  - 4756  member added to universal group

EDR:
  - Mimikatz / Rubeus / SharpHound 起動 detection
  - LSASS read pattern
  - 子 process 異常 (cmd.exe → powershell.exe -EncodedCommand)
```

## Phase 8 — レポート

```
- collection 期間 / DC / domain
- 危険 ACL 一覧 (severity 別)
- 攻撃 path 抜粋 (最短 path で DA に到達)
- 推奨修正 (個別 ACL 削除 / role 縮小 / LAPS / tier 隔離)
- detection rule の追加
```

## Tools

```
BloodHound + Neo4j / SharpHound / bloodhound-python
ldap3 / windapsearch
PowerView / SharpView
Rubeus / Mimikatz / Certipy / NetExec / impacket
WebFetch
Bash (sandbox)
```

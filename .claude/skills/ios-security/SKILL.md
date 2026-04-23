---
name: ios-security
description: iOS アプリの総合 security assessment を Frida + Objection + IPA static + traffic + keychain + entitlement 確認の組合せで進める。CTF mobile / pentest / bug bounty で発火。Frida / Objection の深掘りは references/ 参照
category: mobile
tags:
  - ios
  - assessment
  - mobile
  - frida
  - objection
  - ipa
---

# iOS Security

## When to Use

- iOS アプリの assessment を 1 セット手順で網羅したい
- bug bounty / pentest engagement で iOS が scope
- artifact_analysis BC `FileKind.IPA` を全方位で評価

**使わない場面**: Android (→ `android-security`)。

variant 別の深掘りは references/ を参照: Objection (Frida ベース runtime toolkit) で jailbreak detection bypass / SSL pinning bypass / keychain dump = `references/objection.md`、Frida dynamic instrumentation で 暗号 key 抽出 / TLS bypass / class method hook = `references/frida.md`。

## Approach / Workflow

### Phase 1 — IPA 入手と static review

```bash
unzip app.ipa -d ipa_unpacked
ls ipa_unpacked/Payload/<App>.app/
# Info.plist / Mach-O binary / resources / Frameworks /
plutil -convert xml1 -o - Info.plist
codesign -dv --entitlements - <App>
```

確認:

```
- bundle-id / version / minimum iOS version
- Capability (entitlement: keychain-access-groups / iCloud / push notification / camera / location / contacts)
- ATS (App Transport Security) 設定 — NSAllowsArbitraryLoads は弱い
- URL Schemes (open URL hijacking 余地)
- Universal Links
- Background Modes
```

### Phase 2 — Mach-O 静的検査

```bash
file <App>          # arm64 / fat
otool -L <App>      # link library
otool -hv <App>     # PIE / nx / canary
nm <App>            # symbol
class-dump-z <App>  # ObjC class info
```

PIE / Stack Canary / ARC は Apple ガイドライン的にデフォルト ON。OFF なら指摘。

### Phase 3 — runtime: Objection で baseline

`references/objection.md` の手順:

```
ios info binary
ios keychain dump
ios cookies get
ios sslpinning disable
ios jailbreak disable
ios hooking list classes
file ls Documents/
```

### Phase 4 — runtime: Frida で深掘り

`references/frida.md` で:

```
- 暗号 routine (CCCrypt / AESEncrypt) の hook + key 抽出
- Login / payment 関連 method の trace
- TLS pinning 関数 / jailbreak detection 関数の精密 bypass
- Swift method の demangle + hook
```

### Phase 5 — traffic 分析

```
- objection ios sslpinning disable で pinning 解除
- mitmproxy / Burp に device proxy
- 観察項目: API endpoint / 認証 header / token 寿命 / cert pinning 形態
```

API 評価は `web-pentester` / `api-security` / `authentication` の手順で深掘り。

### Phase 6 — sensitive data storage

```
keychain               kSecAttrAccessible class が厳しめか
NSUserDefaults         secrets を入れていないか (暗号化なし)
sqlite (Library/...)   暗号化 (SQLCipher) されているか
plist                  password / api key の hard-code
Cache.db               sensitive response を残していないか
WAL / journal         残骸 record 復元 (→ disk-forensics)
```

### Phase 7 — anti-tamper / runtime check

```
- jailbreak detection 関数の存在 / 強度
- ptrace anti-debug
- 完全性 check (own-bundle hash)
- TLS pinning lib (TrustKit / AFNetworking)
- runtime app self-protection (RASP)
```

### Phase 8 — レポート

```
- bundle-id / version / signing
- entitlement / ATS / URL scheme review
- runtime hook 観察
- traffic 分析
- sensitive storage 評価
- jailbreak / pinning bypass の結果
- 重要 finding (severity 別)
- 修正 (keychain class / RASP / pinning / ATS / runtime check)
```

## Tools

```
objection / frida / frida-trace
class-dump-z / Hopper / Ghidra
otool / codesign / plutil
mitmproxy / Burp
sqlite3 / BinaryCookieReader
WebFetch
Bash (sandbox)
```

## Related Skills

- `android-security` (Android 並行)
- `reverse-engineering`
- `web-pentester`, `api-security`, `authentication`, `client-side`
- `performing-cryptographic-audit-of-application`, `testing-jwt-token-security`
- `disk-forensics`

## Rules

1. **明示許可**
2. **device 管理** — jailbroken device は隔離
3. **取得 secret** — sealed area
4. **App Store ToS** — 商用アプリへの試験は ToS / scope 確認

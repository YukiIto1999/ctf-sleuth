
# iOS App Runtime Analysis with Objection

`ios-security` から呼ばれる variant 別 deep dive

## When to Use

- iOS IPA / installed app の runtime 挙動を Frida で hook して試験
- jailbreak detection / TLS pinning / keychain 暗号化の評価
- artifact_analysis BC `FileKind.IPA` 受領後の動的試験

**使わない場面**: Mach-O 単体の static rev (→ `reverse-engineering`)、Frida script 直書きの細かい hook (→ `ios-security`)、総合 assessment (→ `ios-security`)。

## Approach / Workflow

### Phase 1 — 環境

```
- jailbroken iPhone or 専用 emulator (Corellium 等)
- Frida server を device に install
- ホスト: pip install objection frida-tools
```

```bash
frida-ls-devices
objection -g <bundle-id> explore
```

### Phase 2 — 主要コマンド

```
ios info binary             binary 情報 (PIE / canary / ARC / signed)
ios info ipfw               firewall 状況 (jailbreak host)
ios keychain dump            keychain item 列挙
ios cookies get              cookie store
ios nsuserdefaults get       NSUserDefaults
ios plist read <path>        plist 確認
ios sslpinning disable       TLS pinning 解除
ios jailbreak disable        jailbreak detection bypass
ios hooking list classes
ios hooking list class_methods <class>
ios hooking watch class <class>
ios hooking watch method <selector>
file ls / file download      sandbox 内 file
```

### Phase 3 — Jailbreak / TLS pinning 検出と bypass

```
ios jailbreak disable        # 既知 detection 関数を hook
ios sslpinning disable       # NSURLSession / AFNetworking / TrustKit を hook
```

`Detect`/`isJailbroken`/`Cydia`/`MobileSubstrate` を含む method を hook して `false` を返す。

### Phase 4 — Keychain / data protection

```
ios keychain dump --json keychain.json
```

class:

```
kSecAttrAccessibleAlways                    最低 (lock 後も読める)
kSecAttrAccessibleAlwaysThisDeviceOnly
kSecAttrAccessibleAfterFirstUnlock          多い
kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
kSecAttrAccessibleWhenUnlocked              推奨
kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly  最も厳しい
```

クレジットカード / API key 系で `Always` だと NG。

### Phase 5 — code 観察

```
ios hooking list classes
ios hooking watch class MyController
ios hooking watch method "+[NSURL URLWithString:]"
```

method 呼出し時に args / return を log。`generic` argument は ObjC selector / Swift も bridging で見える。

### Phase 6 — file system

```
env                                       Documents / Library / tmp の path
file ls /var/mobile/.../Documents
file download /.../Cookies.binarycookies
```

binarycookies は `BinaryCookieReader` で plain text 化。

### Phase 7 — TLS proxy で通信観察

```
ios sslpinning disable で pinning 解除
ホストに mitmproxy / Burp を立て、device proxy を ホストに向ける
```

API endpoint / 認証 header を観察。`web-pentester` / `api-security` の手順で深掘り。

### Phase 8 — レポート

```
- bundle-id / version
- jailbreak detection / TLS pinning の有無 / bypass 結果
- keychain item の access class
- runtime hook で観察した sensitive 操作
- 推奨 (TLS pinning 強化 / keychain class 厳格化 / runtime check)
```

## Tools

```
objection
frida / frida-tools
mitmproxy / Burp
class-dump (Mach-O class info)
WebFetch
Bash (sandbox)
```

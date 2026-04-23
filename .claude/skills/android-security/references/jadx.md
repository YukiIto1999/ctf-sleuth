
# Android Malware Decompilation with JADX

`android-security` から呼ばれる variant 別 deep dive

## When to Use

- APK の Java / Kotlin source 級まで読みたい
- smali grep だけでは見えない複雑 logic
- artifact_analysis BC `FileKind.APK` の深掘り

**使わない場面**: 表面 grep のみ (→ `android-security`)、SAST 自動化 (→ `android-security`)、動的 (→ `android-security`)。

## Approach / Workflow

### Phase 1 — JADX 起動

```bash
jadx-gui app.apk             # GUI
jadx -d ./out app.apk        # CLI で source 一式 export
jadx --show-bad-code -d ./out app.apk    # 失敗 method もそのまま
```

### Phase 2 — 構造把握

```
out/
├── resources/
├── sources/
│   └── <reverse domain>/<package>/...java
└── ...
```

`AndroidManifest.xml` から entry component (Activity / Service / Receiver / Provider) を identify、対応 java を読みに行く。

### Phase 3 — 重要 API search

```
- HttpURLConnection / OkHttpClient → C2
- WebView / loadUrl / addJavascriptInterface → JS bridge 攻撃
- Base64.decode / AES / Cipher.getInstance → 暗号化 layer
- Build.VERSION / Build.MODEL → device fingerprint
- TelephonyManager.getDeviceId / getImei / getSubscriberId → IMEI 等
- SmsManager / SmsMessage → SMS
- AccessibilityService.onAccessibilityEvent → 画面 hijack
- WindowManager + TYPE_APPLICATION_OVERLAY → overlay
- DexClassLoader / PathClassLoader → 動的 dex 読込
- Runtime.exec / ProcessBuilder → shell
- root: /system/bin/su / Magisk
```

### Phase 4 — obfuscation 対策

```
ProGuard / R8: 関数 / class 名が a, b, c に短縮
DexGuard:      文字列暗号化 + control-flow flattening
allatori-style: 同上
```

JADX の機能:

```
- Tools → Deobfuscation: rename helper
- Tools → String Decoder: 簡単な XOR / base64 を復元
```

複雑な暗号化 (DexGuard) は frida で runtime hook して復号後の文字列を取得 (→ `android-security`)。

### Phase 5 — Kotlin 特有

Kotlin は Java と互換だが decompile 時:

```
- companion object → Java の static inner class
- coroutines → suspend / continuation の state machine 展開
- data class → equals / hashCode / toString 自動生成
- sealed class → enum 風
```

明示しないと読みづらいので、Kotlin 知識を前提に変換しながら読む。

### Phase 6 — config / payload 抽出

```
- 暗号化 string → 復号 method を identify → JADX で input/output 値を逆算
- assets / raw resource / xml に隠した config (encrypted)
- shared preferences key 名
- Firebase / OneSignal の API key (config を C2 認証に使うパターン)
```

### Phase 7 — 既知 family

```
banker:    Cerberus, Anubis, Hydra, Octo, BRATA, FluBot, SharkBot, ERMAC, Vultur, Hook
spyware:   Pegasus (commercial), Predator (commercial), Hermit
RAT:       AhMyth, SpyMax, ScarletSpy, MaliBot
adware/PUP: HiddenAds, Joker, Triada
```

family identification は yara-android ruleset / TLSH / mobsf hash check / VT lookup。

### Phase 8 — レポート / IOC

```
- package id / version / cert SHA-1
- 推定 family
- C2 / 通信 protocol
- 暗号 key / config
- 危険 component / intent
- native .so 連携
- yara / sigma rule draft
```

## Tools

```
jadx-cli / jadx-gui
apktool (manifest / resource を別途用意)
mobsf (補助 SAST)
frida (動的 hook)
yara
WebFetch
Bash (sandbox)
```

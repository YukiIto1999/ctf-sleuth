
# Android APK Analysis with apktool

`android-security` から呼ばれる variant 別 deep dive

## When to Use

- 不審 APK の static triage
- artifact_analysis BC で `FileKind.APK` 判定された対象
- AndroidManifest / smali / resource を grep / 検索したい

**使わない場面**: Java decompile が必要 (→ `android-security`)、動的解析 (→ `android-security`)、SAST (→ `android-security`、`android-security`)。

## Approach / Workflow

### Phase 1 — triage

```bash
file app.apk                           # PK\x03\x04 (zip)
sha256sum app.apk
unzip -l app.apk | head                # 中身一覧
```

確認:

```
- AndroidManifest.xml
- classes.dex (1 つ以上、multi-dex 可)
- resources.arsc
- res/ / assets/
- META-INF/ (signing)
- lib/<arch>/ (native .so)
```

### Phase 2 — apktool で decode

```bash
apktool d app.apk -o ./decoded
```

出力:

```
decoded/
├── AndroidManifest.xml         (decoded)
├── apktool.yml
├── res/
├── smali/                       (decompiled bytecode)
├── smali_classes2/              (multi-dex)
├── assets/
└── unknown/
```

### Phase 3 — manifest 解析

危険シグナル:

```
BIND_ACCESSIBILITY_SERVICE   画面操作 hijack (banker の典型)
SYSTEM_ALERT_WINDOW          overlay attack
READ_SMS / RECEIVE_SMS       SMS interception
READ_CONTACTS / CALL_LOG     個人情報窃取
BIND_DEVICE_ADMIN             デバイス管理者
REQUEST_INSTALL_PACKAGES     dropper
SUPERUSER / android.permission.WRITE_SECURE_SETTINGS  root 必須
exported="true" + intent-filter 緩い  open IPC
```

### Phase 4 — smali grep

```bash
grep -rln 'http://\|https://' decoded/smali*/
grep -rln 'getDeviceId\|getImei\|getSubscriberId' decoded/smali*/
grep -rln 'sendTextMessage\|getMessageBody' decoded/smali*/
grep -rln 'AccessibilityService' decoded/smali*/
grep -rln 'crypto/Cipher' decoded/smali*/
grep -rln 'System\.loadLibrary' decoded/smali*/
grep -rln 'Magisk\|Xposed\|/system/bin/su' decoded/smali*/
```

family hint:

```
Cerberus / Anubis / FluBot: AccessibilityService + SMS hijack + overlay
Joker:                       toll fraud / SMS subscription
TeaBot:                      AccessibilityService + screen capture
SharkBot:                    automatic transfer system (ATS)
```

### Phase 5 — assets / config

```bash
find decoded/assets -type f
file decoded/assets/*
strings -n 8 decoded/assets/* | head
```

隠し APK / 暗号 config を発見することが多い。

### Phase 6 — native .so

```bash
file decoded/lib/arm64-v8a/*.so
# Ghidra で reverse-engineering / reverse-engineering
```

JNI 経由で重要 logic を native に隠すケース。

### Phase 7 — repackage (検証用)

```bash
apktool b decoded -o repacked.apk
apksigner sign --ks debug.keystore repacked.apk
```

CTF / 動作変更が必要な検証のみ。

### Phase 8 — レポート / IOC

```
- package id / version
- 危険 permission リスト
- exported component / intent-filter
- C2 URL / domain / 通信パターン
- 暗号 key / config
- native .so の有無 / role
- 推定 family / 類似度
- yara / sigma rule draft
```

## Tools

```
apktool
unzip / aapt2
jadx
mobsf
yara
WebFetch
Bash (sandbox)
```

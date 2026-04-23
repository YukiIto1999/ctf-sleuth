---
name: android-security
description: Android APK の総合 security 評価 (static SAST / 動的 hook / IPC / business logic / malware 解析) を体系的に進める。CTF mobile / DFIR Android / pentest / bug bounty で発火。tool / 活動別の深掘りは references/ 参照
category: mobile
tags:
  - android
  - apk
  - sast
  - dynamic
  - mobsf
  - frida
  - intent
---

# Android Security

## When to Use

- 認可済 APK の脆弱性 audit / 動的 hook / business logic 検証
- artifact_analysis BC `FileKind.APK` の解析
- 不審 APK (malware) の triage
- bug bounty で Android アプリ評価

**使わない場面**: iOS アプリ (→ `ios-security`)。

variant 別の深掘りは references/ を参照: 静的 decompile 系 = apktool は `references/apktool.md` / jadx は `references/jadx.md`、自動 SAST = `references/mobsf.md`、動的解析 (Frida / Objection / drozer) = `references/dynamic.md`、Intent / IPC 脆弱性 = `references/intents.md`、business logic mapping = `references/logic-mapper.md`。

## Approach / Workflow

### Phase 1 — APK の準備

```bash
file app.apk
sha256sum app.apk
unzip -l app.apk | head
apktool d app.apk -o ./decoded
jadx -d ./out app.apk
```

### Phase 2 — manifest review

`AndroidManifest.xml` で:

```
- android:debuggable="true"   debug 可能 (production NG)
- android:allowBackup="true"  ADB backup で data 抽出可
- android:networkSecurityConfig  cleartextTrafficPermitted 確認
- android:exported  実際の使用箇所と比較
- intent-filter: 受付 action / data / scheme
- 危険 permission の用途確認
- android:taskAffinity / android:launchMode  task hijack
- providers の grantUriPermissions
```

### Phase 3 — code 観点

```
- Cryptography:
  Cipher.getInstance("AES")  // mode 不明 = ECB default (NG)
  Cipher.getInstance("AES/CBC/PKCS5Padding")  // OK だが IV management 確認
  hardcoded key / IV
  weak hash (MD5 / SHA1)

- 認証 / Token:
  shared preferences に password 平文保存
  keystore 利用していない

- Storage:
  getExternalStorageDirectory() で sensitive 保存 (read 可能)
  WebView の addJavascriptInterface (RCE 余地)

- Logging:
  Log.d / println で credential 出力

- Webview:
  setJavaScriptEnabled + setAllowFileAccess + setAllowUniversalAccessFromFileURLs
  loadDataWithBaseURL の content:// scheme 検証

- IPC:
  Binder Service の checkPermission 不在
  exported BroadcastReceiver の input validation
  ContentProvider の query / insert / update 緩い
  PendingIntent の mutable / explicit

- Network:
  cleartextTrafficPermitted = true
  TrustManager で全 cert を accept
  HostnameVerifier で全 host を accept
  certificate pinning なし
```

### Phase 4 — 自動化 SAST

```bash
mobsf                                     # docker compose
qark --apk app.apk                         # quick scan
mariana-trench .                           # facebook OSS taint
semgrep --config p/android-security src/
```

### Phase 5 — native .so

```bash
file decoded/lib/arm64-v8a/*.so
# Ghidra で reverse-engineering / reverse-engineering の手順
```

JNI 経由で重要 logic を native に隠すアプリは多い。string 検索 + JNI signature でエントリ発見。

### Phase 6 — sign / integrity

```bash
apksigner verify -v --print-certs app.apk
# v1 / v2 / v3 / v4 signature の対応確認
```

```
v2: APK Signing Block (信頼性高い)
v1: META-INF/ JAR signing (古い)
debug 用 cert で署名されていれば 開発リーク
```

### Phase 7 — レポート

```
- package id / version / sign info
- 検出 finding (severity 別)
- manifest issue (debug / backup / cleartext / exported)
- code issue (crypto / IPC / webview / network)
- native .so summary
- 推奨修正 (Network Security Config / keystore / pinning)
```

## Tools

```
apktool / jadx / mobsf
qark / mariana-trench / semgrep / drozer (Phase で次の dynamic と接続)
apksigner / aapt2
WebFetch
Bash (sandbox)
```

## Related Skills

- `ios-security` (iOS 並行)
- `reverse-engineering` (native .so 解析)
- `performing-cryptographic-audit-of-application`
- `web-pentester`, `api-security`, `authentication` (バックエンド連携)
- `bug-bounter`, `web-bounty`, `hackerone`

## Rules

1. **隔離 emulator で確認**
2. **integrity** — APK SHA-256
3. **共有禁止**
4. **bug bounty 報告** — 該当 program / Google Play / 開発者へ責任ある開示

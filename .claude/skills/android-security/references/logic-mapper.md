
# Android App Logic Mapping

`android-security` から呼ばれる variant 別 deep dive

## When to Use

- アプリの business logic 流れを把握 (login / payment / chat / file download 等)
- `android-security` の finding を context 化して exploit chain を組む
- bug bounty で logic-flaw を狙う

**使わない場面**: 単純な静的検査 (→ `android-security`)、malware analysis (→ `android-security`)。

## Approach / Workflow

### Phase 1 — entry point 特定

```
Activity:           AndroidManifest <activity android:name="..."> intent-filter で識別
Service:            backgroun work / IPC binder
BroadcastReceiver:  system / app-private intent 受信
ContentProvider:    URI ベース data access
Deep link:          android:scheme="myapp" / Universal Link
WorkManager:        scheduled job
JobService / FCM:   push 起動
```

各 entry の `exported` 属性を控える。

### Phase 2 — Activity 流れ

```
- App 起動 → MainActivity / SplashActivity → LoginActivity → 各 feature Activity
- 各 Activity の onCreate / onResume / onActivityResult / onNewIntent
- startActivity / startActivityForResult の chain
```

JADX でメソッド追跡:

```
- 各 Activity の onCreate を読む
- intent.getStringExtra の input source を控える
- startActivity の Intent 引数を controlled かどうか分類
```

### Phase 3 — IPC graph 構築

```
- exported components 一覧
- 各 component に届く Intent の form
- BroadcastReceiver の action / category
- ContentProvider の URI scheme / authorities
- Service の onBind / onStartCommand
- aidl interface
```

drozer で:

```bash
drozer console connect
> run app.package.attacksurface <package>
> run app.activity.info -a <package>
> run app.broadcast.info -a <package>
> run app.service.info -a <package>
> run app.provider.info -a <package>
> run scanner.provider.injection -a <package>   # SQLi-like
```

### Phase 4 — data flow (taint)

```
sources:
  - intent extra
  - ContentProvider query
  - Bundle savedInstanceState
  - SharedPreferences
  - Network response
  - File / Database read

sinks:
  - WebView.loadUrl
  - JavaScriptInterface.callFromJavascript
  - Runtime.exec / ProcessBuilder
  - ContentResolver.query (SQLi)
  - File path open
  - Crypto Cipher with key
```

source → sink 経路を tracking。`mariana-trench` 等の自動 taint analyzer を併用。

### Phase 5 — 認証 / 認可フロー

```
- Login flow: API endpoint / 認証 method / Token storage
- Token refresh / logout
- multi-factor / biometric prompt
- session invalidation
- per-feature 認可 (premium feature gate)
```

### Phase 6 — sensitive 操作

```
payment:    Stripe / PayPal / Google Pay の SDK 利用法
location:   FusedLocationProvider / 精度 / 取得先
camera / mic: permission 動的取得 / runtime check
contacts:   一括取得 / 上り送信
network:    WebSocket / GraphQL / REST
```

### Phase 7 — exploit chain 組立

map から:

```
exported component で受信 → 内部 sensitive 操作起動
deep link で sensitive Activity 直接起動 → 認証 bypass
WebView の JavaScriptInterface 経由 RCE
ContentProvider で SQLi → DB 内 data 取得
```

### Phase 8 — レポート

```
- アプリ全体 component graph
- 主要 user flow (流れ図)
- exploit chain 候補
- 推奨修正 (exported 縮小 / intent validation / WebView 制限)
```

## Tools

```
jadx / apktool
drozer / objection / Frida (動的補完)
mariana-trench / semgrep
WebFetch
Bash (sandbox)
```

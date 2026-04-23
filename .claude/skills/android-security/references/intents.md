
# Android Intent / IPC Vulnerability Testing

`android-security` から呼ばれる variant 別 deep dive

## When to Use

- exported component を経由した攻撃面評価
- deep link / Universal Link / browsable intent の自由化試験
- ContentProvider への SQLi / path traversal
- PendingIntent の implicit / mutable issue

**使わない場面**: pure SAST (→ `android-security`)、native rev (→ `android-security`)。

## Approach / Workflow

### Phase 1 — exported component 列挙

```bash
adb shell dumpsys package <package>
drozer> run app.package.attacksurface <package>
drozer> run app.activity.info -a <package>
drozer> run app.broadcast.info -a <package>
drozer> run app.service.info -a <package>
drozer> run app.provider.info -a <package>
```

`exported="true"` または `intent-filter` 持ちの component を抽出。

### Phase 2 — Activity hijack / 起動

```bash
am start -n <package>/<activity> --es key value --ei int_key 1
adb shell am start -a <action> -d <data> --es <key> <val>
drozer> run app.activity.start --component <package> <activity>
```

```
- exported activity に sensitive な onCreate logic があれば 認証 bypass
- onActivityResult を抜けて結果を返さない / 偽結果送信
- launchMode singleTask / singleInstance の task hijacking
- taskAffinity 設定で task takeover
```

### Phase 3 — Deep link / Custom Scheme

```
adb shell am start -a android.intent.action.VIEW -d "myapp://path?token=evil"
adb shell am start -a android.intent.action.VIEW -d "https://example.com/path"
```

```
- 任意 deep link で sensitive Activity を直接起動
- WebView の loadUrl の引数として渡るとき XSS / file:// / javascript:
- universal link 検証不在
- intent extra に attacker 制御の URL / file path
```

### Phase 4 — BroadcastReceiver

```bash
adb shell am broadcast -a <action> --es key value
drozer> run app.broadcast.send --action <action> --extra string foo bar
```

不正発火パターン:

```
- system action 偽装 (BOOT_COMPLETED)
- 自前 action で internal data を取得
- attacker app から sensitive callback 起動
```

### Phase 5 — ContentProvider

```bash
drozer> run scanner.provider.injection -a <package>
drozer> run scanner.provider.traversal -a <package>
drozer> run app.provider.read content://<authority>/<path>
drozer> run app.provider.update content://<authority>/<path> --selection ...
drozer> run app.provider.query content://<authority>/<path>
```

```
- SQLi (selection 引数の string concat)
- path traversal (file path 経由 read 不正)
- 過剰 export (READ_EXTERNAL_STORAGE 不要なのに permission 設定なし)
- grantUriPermissions で外向き提供
```

### Phase 6 — PendingIntent 改竄

```
- mutable PendingIntent (Android 11 以前 default mutable)
- attacker app が intent extra を上書き
- 結果として system 権限で任意 action 実行
- UPDATE_CURRENT / NO_CREATE flag の組合せ
```

Android 12+ で `FLAG_IMMUTABLE` 強制になりつつあるが旧 API で残る場合 vulnerable。

### Phase 7 — Service hijack

```
- exported Service の Bind が認可なし
- AIDL interface の input validation 不在
- Service 経由で sensitive 操作 (file write / system call)
```

### Phase 8 — レポート

```
- 対象 component 一覧
- 検出脆弱性 (severity 別)
- exploit chain (PoC adb command)
- 推奨修正 (exported 縮小 / permission 設定 / input validation / immutable PendingIntent)
```

## Tools

```
adb (am start / am broadcast)
drozer
objection
Frida (動的補完)
WebFetch
Bash (sandbox)
```

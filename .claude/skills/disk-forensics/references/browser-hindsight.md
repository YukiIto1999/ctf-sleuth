
# Browser Forensics with Hindsight (Chromium 系)

`disk-forensics` から呼ばれる variant 別 deep dive

## When to Use

- 取得した disk image / live profile から Chromium 系 browser の挙動を再構成する
- 不審 download / phishing アクセス / OAuth consent 経路の追跡
- CTF DFIR で「user が踏んだ URL は何か」型問題

**使わない場面**: Firefox 系（→ `mozregression-cookies` / カスタム手順）、IE / Edge legacy（WebCache.dat 系）。

## Approach / Workflow

### Phase 1 — プロファイルディレクトリの所在

```
Windows: C:\Users\<user>\AppData\Local\Google\Chrome\User Data\Default\
         C:\Users\<user>\AppData\Local\Microsoft\Edge\User Data\Default\
         C:\Users\<user>\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\
         C:\Users\<user>\AppData\Roaming\Opera Software\Opera Stable\

macOS:   ~/Library/Application Support/Google/Chrome/Default/
         ~/Library/Application Support/Microsoft Edge/Default/

Linux:   ~/.config/google-chrome/Default/
         ~/.config/microsoft-edge/Default/
```

各プロファイルに以下の SQLite DB:

```
History               # 訪問 / 検索 / DL
Cookies               # cookie store
Login Data            # 保存 password (encrypted)
Web Data              # autofill / credit card
Bookmarks             # JSON
Top Sites             # 頻度上位
Network Action Predictor
Sessions/             # tab 復元
```

### Phase 2 — Hindsight 起動

```bash
pip install hindsight
hindsight.py -i ~/.config/google-chrome/Default/ -o report --browser_type Chrome
```

GUI 版 (`hindsight_gui.py`) を使うと CSV / SQLite / JSON / HTML 出力を選べる。

### Phase 3 — 出力と分析

Hindsight は次の artefact を抽出:

```
- URL visits (timestamp / typed_count / visit_duration / transition type)
- Downloads (target_path / received_bytes / referrer / state)
- Searches (engine / term / url)
- Cookies (host / name / value / expiration)
- Cache (URL / size / mime_type / file path)
- Autofill (name / value / used count)
- Logins (URL / username, password は Chromium DPAPI 暗号で別途)
- Extensions (id / name / version / homepage)
- Bookmarks
- Local Storage / Session Storage
- Sync settings / IndexedDB / Service Workers
```

### Phase 4 — 重点的に見る項目

```
Download:
  - state = 'INTERRUPTED' / 'CANCELLED' は user が止めた可能性
  - target_path に %TEMP% / %APPDATA% は malware の常套
  - referrer URL がメール / phishing 風 domain

History:
  - typed_count > 0 で URL bar 直接入力 (user 意図が強い)
  - transition LINK / TYPED / RELOAD / FORM_SUBMIT で操作種別判別
  - visit_duration が短く連続 → automated / scripted browsing

Extensions:
  - id がストア掲載されていない (sideload)
  - permissions が all_urls / debugger / cookies (危険拡張の典型)
  - update_url がストアでない

Cookies:
  - 不審 domain への persistent cookie
  - HttpOnly / Secure 属性なしの sensitive cookie
```

### Phase 5 — 復号 (login data)

`Login Data` 内 password は Chromium が DPAPI (Windows) / login keyring (Linux) / Keychain (macOS) で暗号化。

```bash
# Windows (live profile から、調査用 admin 権限想定)
python chromepass-extract.py --master-key %APPDATA%\Local\Google\Chrome\User\ Data\Local\ State

# 一般的に offline では困難 (master key も必要)
```

### Phase 6 — timeline 化

各 artefact の timestamp を 1 本の timeline にまとめる:

```
HH:MM:SS  visit URL X (LINK)
HH:MM:SS  search 'login bypass' on Google
HH:MM:SS  visit phishing URL Y (TYPED)
HH:MM:SS  download Z.exe to %TEMP%
HH:MM:SS  install extension EXT_ID
HH:MM:SS  cookie set for *.attacker.com
```

`hindsight.py --timeline` で plaso 風 super-timeline へ変換も可能。

### Phase 7 — レポート

```
- プロファイル所在 / browser version
- 訪問 URL の重要 entries
- 不審 download artefact (path / hash / referrer)
- 不審拡張 (id / permission / update_url)
- timeline
- 推奨 (拡張削除 / cookie 失効 / IOC block)
```

## Tools

```
hindsight (CLI / GUI)
sqlite3 (生 DB 直読)
plaso / log2timeline (cross-tool timeline)
strings / xxd
WebFetch
Bash (sandbox)
```

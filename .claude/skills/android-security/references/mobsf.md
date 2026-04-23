
# Android SAST with MobSF

`android-security` から呼ばれる variant 別 deep dive

## When to Use

- 認可済 APK の SAST を一発実行
- MobSF レポートを engagement 報告書の base に
- 多 APK の batch 評価

**使わない場面**: manual deep dive (→ `android-security`、`android-security`)。

## Approach / Workflow

### Phase 1 — MobSF の起動

```bash
# docker
docker run -d -p 8000:8000 opensecurity/mobile-security-framework-mobsf

# local
git clone https://github.com/MobSF/Mobile-Security-Framework-MobSF
cd Mobile-Security-Framework-MobSF
./run.sh

# REST API
curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: <api_key>" \
  -F "file=@app.apk"
```

### Phase 2 — 自動解析項目

```
- App info (package id / version / sdk / sign)
- Permissions (危険度別 / abuse case)
- Activities / Services / Receivers / Providers (exported)
- Manifest issue (debug / backup / cleartext)
- Code issue (SAST rule)
  - Cryptography (weak alg / hardcoded key)
  - Insecure storage / logging
  - WebView misuse
  - SQLi / file read
  - Hardcoded secret
- Network Security (cleartext / TrustManager / Hostname)
- Strings (hardcoded URL / token)
- Domain malware check (virustotal / TI)
- Privacy: tracker / firebase
- Reflection / dynamic loading
- Native lib analysis
```

### Phase 3 — score / severity

MobSF は CVSS-like score (0-100) を出す:

```
< 40         high risk
40-60         medium
60-80         low
> 80          good
```

ただし環境特化要因 (B2B internal app は debug 系緩めて OK) は分析者が context 補正。

### Phase 4 — 推奨機能

```
- API endpoint mapping
- DroidBox / Frida の動的解析 trigger (要 emulator)
- Diff 機能で版間比較
- iOS IPA も同 framework で SAST
- M365 / Sentinel への push (REST)
- CI 連携 (PR ごとの APK SAST)
```

### Phase 5 — 出力 format

```
- HTML / PDF / JSON
- Json report は CI 集約に好ましい
- DOC ファイルは regulatory 用途
```

```bash
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Authorization: <key>" -F "scan_type=apk" -F "file_name=app.apk" -F "hash=<hash>"

curl -X POST http://localhost:8000/api/v1/report_pdf \
  -H "Authorization: <key>" -F "hash=<hash>" -o report.pdf
```

### Phase 6 — false positive 仕分け

```
- "Hardcoded secret" は test fixture や public API key の可能性
- "App is debuggable" は build flavor 確認
- "Application may contain dangerous Permissions" は legitimate 用途
```

### Phase 7 — レポート整形 (engagement 用)

```
- summary score
- severity 別 finding 一覧
- 個別 finding に MobSF の rule ID + 推奨修正 + code reference
- 関連 OWASP MASVS / MASTG ref
- 動的試験への bridge (drozer / Frida 連携)
```

### Phase 8 — 自動化

```
- CI 上で MobSF API へ APK upload
- score < threshold で fail
- diff で 新規 finding のみ block
```

## Tools

```
mobsf (REST + Web UI)
apktool / jadx (補完)
drozer / Frida (動的)
WebFetch
Bash (sandbox)
```

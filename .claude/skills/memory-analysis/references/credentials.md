
# Extracting Credentials from Memory Dump

`memory-analysis` から呼ばれる variant 別 deep dive

## When to Use

- LSASS dump (`procdump -ma lsass.exe`) または full memory dump (`.raw`/`.dmp`) を渡された
- Kerberos ticket / golden ticket の確認
- credential reuse / domain impact assessment
- CTF forensics で「memory dump から flag (= password)」型問題

**使わない場面**: ライブシステムでの clear-text 抽出（→ live mimikatz、本 skill scope 外）。

## Approach / Workflow

### Phase 1 — dump 種別の同定

```
LSASS process dump:    .dmp (windows minidump)
Full memory dump:      .raw / .vmem / .lime / .dmp (kernel-mode)
Saved registry hive:   SYSTEM / SECURITY / SAM file
```

LSASS minidump なら mimikatz / pypykatz 直接、フルメモリは Volatility plugin 経由 or 抽出。

### Phase 2 — pypykatz (cross-platform、推奨)

```bash
pypykatz lsa minidump lsass.dmp
pypykatz lsa raw mem.raw                 # 一部 build で動く
```

出力に `MSV` / `Wdigest` / `Kerberos` / `Tspkg` / `Credman` / `LiveSSP` セクション。各 user の NTLM、SHA1、ticket、clear-text (デフォルトで Wdigest 無効化されていなければ) が並ぶ。

### Phase 3 — Volatility 3 plugin

```bash
vol3 -f mem.raw windows.hashdump        # SAM 経由 NTLM
vol3 -f mem.raw windows.cachedump       # MSCASHv2
vol3 -f mem.raw windows.lsadump         # LSA secret (DPAPI master key 等含む)
```

要件: `windows.registry.hivelist` で hive 認識成功すること。Vista+ では SYSTEM bootkey + SAM/SECURITY の組合せが必要。

### Phase 4 — Mimikatz on minidump

Windows ホストで mimikatz を使う:

```
mimikatz # sekurlsa::minidump lsass.dmp
mimikatz # sekurlsa::logonpasswords full
mimikatz # sekurlsa::tickets /export        # Kerberos ticket 出力
mimikatz # lsadump::sam /sam:SAM /system:SYSTEM
mimikatz # lsadump::secrets /system:SYSTEM /security:SECURITY
mimikatz # lsadump::dcsync /domain:lab /user:krbtgt
```

抽出 ticket は `.kirbi` で出る。Linux 側で使うなら `kirbi2ccache.py` で MIT format に変換。

### Phase 5 — registry hive からの抽出

メモリでなく hive ファイル単体の場合:

```bash
secretsdump.py -system SYSTEM -sam SAM -security SECURITY LOCAL
```

domain controller の NTDS.dit があるなら domain 全 hash の dump:

```bash
secretsdump.py -ntds NTDS.dit -system SYSTEM LOCAL
```

### Phase 6 — Kerberos ticket の取扱い

```
TGT (.kirbi) → Pass-the-Ticket / Golden / Silver ticket forging に使える
TGS (.kirbi) → service 別 access
mimikatz# kerberos::ptt ticket.kirbi
```

forensics 文脈では「どの user の TGT が memory に残っていたか」「golden ticket の徴候 (KRBTGT 鍵 hash) があるか」を見る。

### Phase 7 — クリーンアップと redaction

抽出した hash / ticket は機密。レポートに残す場合:

```
- user名: 表示
- ハッシュ: 最初/最後 4 文字 + length
- ticket .kirbi: 件数のみ (本体は sealed evidence)
- domain / hostname: redaction 規程に従う
```

### Phase 8 — 影響評価

```
- どの role / privilege が exposed か (administrator / domain admin / service account)
- 横展開可能性 (Pass-the-Hash / Pass-the-Ticket)
- domain 全体への影響 (krbtgt 鍵 / DCsync 可能 user の有無)
- 推奨 (該当 user reset、krbtgt 二度ローテート、Wdigest 無効化、LSA Protection 有効化)
```

## Tools

```
pypykatz / mimikatz
volatility3 (windows.hashdump / cachedump / lsadump)
secretsdump.py (impacket)
kirbi2ccache.py (MIT ticket 変換)
WebFetch
Bash (sandbox)
```

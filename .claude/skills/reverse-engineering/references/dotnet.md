
# .NET Malware Analysis (dnSpy)

`reverse-engineering` から呼ばれる variant 別 deep dive

## When to Use

- 対象が .NET assembly (PE で `mscoree.dll` import / IL bytecode / `_CorExeMain` entry)
- AsyncRAT / Quasar / Agent Tesla / Lokibot / RedLine 等の典型 .NET malware
- artifact_analysis BC で `FileKind.PE` + .NET 判定された binary

**使わない場面**: native PE C/C++ (→ `reverse-engineering`)、Java / Android (→ `android-security`)。

## Approach / Workflow

### Phase 1 — .NET binary 同定

```bash
file binary
strings binary | grep -E 'mscorlib|System\.Reflection|RuntimePublicKey'
exe-info binary | grep -i \.net
```

`dnSpy` で開けば即 IL / decompiled C# として読める。

### Phase 2 — dnSpy / dnSpyEx 起動

```
File → Open → binary.exe
左側 ツリーに module / namespace / class / method
右側 で IL / C# / VB.NET 表示切替 (View → Languages)
```

メニュー:

```
- Decompile to C#
- Show Tokens (metadata)
- Edit IL Instructions (修正後 reassemble)
- Debug → Start Debugging (debug 開始)
- Tools → Strings (文字列一覧)
- Search → Strings / Members
```

### Phase 3 — 主要観点

```
- Main / Program クラス → entry point
- Settings / Config / Constants → C2 / encryption key の hardcode
- WebClient / HttpClient → C2 通信
- Process.Start / Powershell.Start → command exec
- Cryptography (Aes / Rijndael / Tripledes / Rfc2898DeriveBytes) → 暗号
- Reflection.Assembly.Load / Activator.CreateInstance → 動的 load
- Resources / EmbeddedResources → 隠し payload
- WMI / Registry → persistence
```

### Phase 4 — obfuscator 識別と対策

```
Confuser / ConfuserEx / Confuser2     Constants encryption / Anti-debug / Anti-tamper
.NET Reactor                          Native compile + Anti-debug
Eazfuscator                           Symbol mangling + control flow
Dotfuscator                           商用、軽め
SmartAssembly                         整数定数暗号 + reflection 経由 call
de4dot                                自動 deob (Confuser / Eazfuscator / etc)
```

```bash
de4dot binary -r ./libs              # 自動 detection + deob
# 出力: binary-cleaned.exe
```

ConfuserEx 系: anti-tamper の整合チェック処理を patch / nop で disable する手順あり。

### Phase 5 — 設定 / config 抽出

stealer / RAT は config 文字列を AES / DES で暗号化して `Settings` クラスに格納:

```csharp
public class Settings {
    public static string Hosts = "encrypted...";
    public static string Ports = "encrypted...";
    public static string Key = "...";
    static Settings() {
        // decryption call
    }
}
```

dnSpy の Edit IL で復号 routine の出口に Console.WriteLine を仕込み、Debug 経由で復号文字列を取り出す:

```
1. 復号 method の return 直前に break
2. Debug → Start
3. Locals window で復号 string 確認
4. Copy → 報告書に記録
```

### Phase 6 — ResourcesExtract

埋込 payload (resource):

```
View → Resources → 各 resource を export
PE / DLL の場合は別 binary として再解析
```

stub + payload pattern (loader が resource を runtime 復号して reflection load) はよくある。

### Phase 7 — debugging

```
Debug → Start Debugging (process launch)
breakpoint を任意 method に
Step Into / Over で IL 単位 trace
Locals / Watch で変数確認
```

native code を呼ぶ場合 (P/Invoke) はそこで失敗するため、別 sandbox で動作確認。

### Phase 8 — 既知 family signature

```
- AsyncRAT: AsyncClient namespace, port 6606 default
- Quasar:  ReactiveCommand namespace
- AgentTesla: SmtpClient + クリーンキー文字列
- RedLine: encrypted strings + grabber methods (browsers / wallets)
- Lokibot: ID generation routine
```

yara / cape / configextractor で 自動 config 抽出も。

### Phase 9 — レポート / IOC

```
- assembly identity (公開鍵 token / version / SHA-256)
- 推定 family
- 復号した config (C2 / key / RC4 IV / mutex 名)
- 復号 routine (decompile snippet)
- 永続化 / persistence
- yara / sigma rule の draft
```

## Tools

```
dnSpy / dnSpyEx
de4dot
ILSpy / dotPeek
Ghidra (.NET plugin) / IDA + dotPlumber
PEiD / detect-it-easy
WebFetch
Bash (sandbox)
```

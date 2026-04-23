
# Go Malware Analysis with Ghidra

`reverse-engineering` から呼ばれる variant 別 deep dive

## When to Use

- 対象 binary が Go コンパイル (`runtime.*` 関数 / `Go build ID:` / .gopclntab section)
- BlueShell / Ezuri / Sliver / 各種 Go 製 RAT の解析
- artifact_analysis BC で size 大きい Linux ELF（Go binary は 数 MB が一般）

**使わない場面**: C / C++ 製 (→ `reverse-engineering`)、Rust (→ `reverse-engineering`)。

## Approach / Workflow

### Phase 1 — Go binary の同定

```bash
file binary                                  # "Go BuildID" を含む
strings binary | grep -E '^Go build ID:|^go1\.'
strings binary | grep '/usr/local/go/'
go version binary                            # Go 公式 tool で version 確認
```

特徴:

```
- size が大きい (静的 link で runtime / std lib 全部含む)
- 関数名が `main.*` / `runtime.*` / `<package>.<func>` (stripped でも残ることが多い)
- 文字列が連続したブロックに格納される (Go 文字列 table)
- panic 経路でファイル名 + 行番号が出る
- goroutine / channel が runtime API (runtime.newproc 等) で実装
```

### Phase 2 — Ghidra script で関数復元

stripped 化されると `main.main` 等が消えるが、Go の `.gopclntab` (PC Line Number Table) を解析すれば関数名復元可能:

```
Ghidra Plugin / script:
  - GolangAnalyzerExtension (cubic13)
  - go-symbol (公式に近い実装)
  - goresym (Mandiant)
```

```bash
# goresym で symbol を復元
goresym -t -p binary > symbols.json
# Ghidra に script 経由で apply
```

### Phase 3 — 文字列抽出

Go 文字列は `string{ptr, len}` 構造。strings コマンドだけだと長さ不明で誤抽出。専用:

```
- IDA: GoTools plugin
- Ghidra: GoStringScript
```

または手動:

```python
# offset から指定 length 読む
# Ghidra Python script
addr = currentAddress
ptr = getInt(addr)        # string ptr
length = getInt(addr.add(8))
s = getBytes(toAddr(ptr), length)
print(s.decode('utf-8'))
```

### Phase 4 — type 復元

Go の type は runtime に reflection 用 metadata を持つ:

```
- moduledata 構造体 (._type 配列)
- typelinks section
- 各 _type に kind (struct / interface / chan / func / ...) と string name
```

GolangAnalyzerExtension が moduledata から type 一覧を抽出し、Ghidra の Data Type Manager に登録する。これで struct / interface 名前が decompile に出る。

### Phase 5 — 主要観点

```
- main.main: エントリポイント
- runtime.main: goroutine 起動の本体
- C2 通信: net/http, net.Dial, crypto/tls
- 暗号: crypto/aes, crypto/rsa, golang.org/x/crypto/chacha20
- file: os.Open, os.WriteFile, io/ioutil
- exec: os/exec.Command + .Run()
- persistence: os/exec で systemctl / cron / regedit
- DGA: time, strings, math/rand
```

### Phase 6 — anti-analysis

```
- runtime.GOOS / GOARCH 分岐 (Linux / Windows / macOS で挙動変える)
- syscall 直接呼出し (runtime/cgo は使わない static build が多い)
- ldflags -s -w で symbol 削減
- garble (Go 専用 obfuscator) で関数名 ハッシュ化
- VMProtect / Themida を Go binary に適用 (まれ)
```

`garble` は関数名を hash 化、文字列を runtime 復号する。元 obfuscation 程度は yara で fingerprint。

### Phase 7 — Sliver / 既知 framework

```
Sliver: 静的 link、HTTP/MTLS/DNS/named-pipe profile
Ezuri:  Linux ELF を Go で wrap して runtime 復号
BlueShell: 複数 OS、TLS C2
```

framework 識別は yara rule 集（公開 / 自前）と TLSH / ssdeep。

### Phase 8 — レポート / IOC

```
- Go version / build ID
- 推定 framework / family
- C2 endpoint / TLS pinning 有無
- 暗号化 layer
- 永続化 / 削除回避
- yara / sigma の draft
```

## Tools

```
ghidra + GolangAnalyzerExtension / goresym
go (公式 toolchain で version 確認)
strings / nm
yara / TLSH / ssdeep
WebFetch
Bash (sandbox)
```

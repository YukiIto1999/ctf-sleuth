
# Rust Malware Analysis

`reverse-engineering` から呼ばれる variant 別 deep dive

## When to Use

- 対象 binary が Rust 製 (panic message に `.rs` が含まれる、`__libc_csu_init` 周辺に `core::*` 文字列)
- BlackCat (ALPHV) / RansomEXX (新 variant) / 各種 ランサム / RAT が Rust 化している
- C / Go 製 RE で type が出ない場合に Rust 特有処理を試す

**使わない場面**: C / C++ 製 (→ `reverse-engineering`)、Go 製 (→ `reverse-engineering`)。

## Approach / Workflow

### Phase 1 — Rust binary の同定

```bash
strings binary | grep -E '\.rs$|panicked at|core::|alloc::|std::'
strings binary | grep -E 'rustc-[0-9]'
nm binary 2>&1 | grep -i '_ZN' | head        # itanium mangled rust symbol
```

特徴:

```
- panic 経路で .rs ファイル名 + 行番号 + 'panicked at' が文字列定数に
- 文字列が non-null-terminated (Rust の str は ptr+length)
- vtable が多用される (trait object)
- crate 名 (tokio, reqwest, serde 等) が文字列 / symbol に
- generic を多用するため関数が大量にある
```

### Phase 2 — symbol demangle

Rust mangled symbol (`_ZN6mycrate3foo17h<hash>E` 形式 / 新形式 `_R...`):

```bash
rustfilt < symbols.txt          # rust 専用 demangler
c++filt -n _ZN...               # itanium 互換 demangle (一部のみ)
```

Ghidra:

```
Edit → Tool Options → Demangler → Add Demangler... に rustc demangler を選択
```

IDA:

```
IDC: SetType(...)、Rust plugin (rust-analyzer + idarust)
```

### Phase 3 — 文字列抽出

Rust の `&str` は `(ptr, len)`。Ghidra で:

```python
# Python script
import struct
addr = currentAddress
ptr = currentProgram.getMemory().getInt(addr)
length = currentProgram.getMemory().getInt(addr.add(8))
b = bytes(currentProgram.getMemory().getBytes(toAddr(ptr), length))
print(b.decode('utf-8', errors='replace'))
```

### Phase 4 — control flow

```
- panic を起こす Result::unwrap() が頻出
- match による branch
- closure が関数として展開される
- async/await は state machine に変換 (poll 関数 + state enum)
- vtable 経由 dispatch (trait object: dyn Trait)
- iterator chain が インラインで深く展開
```

decompile 結果は読みづらい。「panic ブランチを除外して main path を読む」が基本姿勢。

### Phase 5 — crate 依存の推定

```
strings | grep -E 'reqwest|tokio|serde|hyper|aes|chacha20|ring|sha2|sha3|x25519-dalek'
```

crate に応じて:

```
reqwest / hyper        HTTP client
tokio                  async runtime
serde                  シリアライズ
ring / aes / sha2      暗号
ssh2 / russh           SSH
zip / tar              archive
```

これらの存在から行動類型を推定。

### Phase 6 — anti-analysis

```
- panic = abort で stack trace 抑止 (公開 binary)
- strip した release binary (-C strip=symbols)
- 文字列 obfuscation (litcrypt 等の crate)
- LLVM 系 obfuscator (obfuscator-llvm)
```

文字列暗号化が掛かっていると `strings` で出ない → memory dump が必要。

### Phase 7 — 既知 family

```
BlackCat / ALPHV     Rust 製 ransomware
Hive (Rust 化版)     ransomware
RansomEXX (new)      Rust port
RustyHermit          PoC
KrustyLoader         Loader
```

family identification には TLSH / ssdeep / yara rule 集合を使う。

### Phase 8 — レポート / IOC

```
- rustc version (panic 文字列から推定)
- 主要 crate
- C2 / config 文字列
- 暗号 algorithm (key / IV)
- 永続化機構
- yara / sigma rule の draft
```

## Tools

```
ghidra (rustc demangler 設定) / IDA + idarust
rustfilt
yara / TLSH / ssdeep
strings / nm
WebFetch
Bash (sandbox)
```

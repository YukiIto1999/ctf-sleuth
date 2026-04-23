
# Malware Reverse Engineering with Ghidra

`reverse-engineering` から呼ばれる variant 別 deep dive

## When to Use

- 不審 ELF / PE / Mach-O / .NET の論理を decompile して読みたい
- C2 protocol / 暗号化 routine / persistence 機構の特定
- CTF rev で flag を抽出するために decompiled C を読む
- pyghidra / headless で多 binary を batch 処理

**使わない場面**: 単純な strings / yara で IOC が出るケース（→ `ioc-hunting`）、source level review（→ `source-code-scanning`）。

## Approach / Workflow

### Phase 1 — project と読込み

```bash
# GUI
ghidraRun
# File → New Project → 名前
# File → Import → binary 選択 → Auto-analyze

# headless
$GHIDRA_HOME/support/analyzeHeadless ./project rev_proj \
  -import malware.exe \
  -postScript decompile.py
```

`decompile.py` (PyGhidra / Ghidrathon) でループ処理:

```python
from ghidra.app.decompiler import DecompInterface
ifc = DecompInterface()
ifc.openProgram(currentProgram)
for func in currentProgram.getFunctionManager().getFunctions(True):
    res = ifc.decompileFunction(func, 60, monitor)
    print(res.getDecompiledFunction().getC())
```

### Phase 2 — symbol / type recovery

```
- Ghidra 自動解析後、function name / signature が一部不明
- import / export を辞書 (Windows API / libc) 突合
- struct / class を Manual で定義 (Data Type Manager)
- typedef を applied して decompile を読みやすく
```

C++ vtable は `Apply Class to Selected Functions`、Rust / Go は demangler / 専用 plugin 適用。

### Phase 3 — control-flow / call graph

```
- Function Graph で 1 関数の basic block 表示
- Call Graph で関数呼出し関係 (Window → Call Graph)
- 重要 entry point から下に follow
- 暗号 / network / file IO を呼ぶ関数を抽出
```

### Phase 4 — 暗号 routine の同定

```
- AES sbox (256 entries の 8-bit)
- SHA-256 K constants
- MD5 K table
- TEA / XTEA shift constants (0x9e3779b9 = golden ratio derivative)
- ChaCha state initial 'expand 32-byte k'
- Curve25519 base point
```

定数 hex を `findcrypt` script や YARA rule で確認:

```
yara -r findcrypt.yar binary
```

key と payload を Ghidra 内 cross-reference で見つけて手動 decrypt。

### Phase 5 — C2 protocol 復元

```
- DNS query 構築 (request / response の format)
- HTTP header (User-Agent / X-Custom-* で識別)
- TCP raw protocol (magic / length / type / payload)
- 平文 / XOR / RC4 / AES の暗号化層
```

Ghidra 内で `send` / `recv` / `wininet` 関連の API 呼出しから back-trace。

### Phase 6 — anti-analysis

```
- IsDebuggerPresent / CheckRemoteDebuggerPresent / NtQueryInformationProcess
- VM 検出 (cpuid eax=1 + ecx hypervisor bit)
- timing (rdtsc 差分)
- API hashing (関数名 → CRC で resolve)
- TLS callback (実行前 hook)
- self-modifying code
```

bypass する場合は Ghidra patch + sandbox で動作確認。

### Phase 7 — IOC / report

```
- C2 ドメイン / IP / port / protocol
- 暗号 algorithm / key / IV
- mutex / file path / registry / scheduled task
- function 一覧 (役割 / hash)
- yara rule の draft
- 推定 family / 既知 sample との類似度 (vt.ai / TLSH)
```

## Tools

```
ghidra (GUI / headless / Ghidrathon)
pyghidra
findcrypt / Cyberchef (検証)
yara
WebFetch
Bash (sandbox)
```


# Packed Malware Unpacking

`reverse-engineering` から呼ばれる variant 別 deep dive

## When to Use

- 解析対象 binary が pack されている疑い (entropy 高 / strings 少 / section 名異常)
- `file` / `die` / `detect-it-easy` で UPX / Themida / VMProtect / ASPack 等の signature
- artifact_analysis BC で受領した binary が packed

**使わない場面**: 通常の解析が直接通る非 packed binary（→ `reverse-engineering` / `reverse-engineering`）。

## Approach / Workflow

### Phase 1 — packed 判定

```bash
# entropy
ent binary | head            # near 8.0 で packed 疑い
diec binary                   # detect-it-easy
exe-info binary               # PE info (PE)
strings -n 6 binary | wc -l  # 少なすぎ / 全部 garbage で packed
```

PE の section 名が `UPX0` `UPX1` `.themida` `.vmp0` `.aspack` 等で identify。ELF も section 名異常で。

### Phase 2 — UPX 標準

```bash
upx -d binary -o unpacked
upx -t binary                 # test (decompress 不可確認)
upx -l binary                 # list 内容
```

UPX 公式 packer なら -d で完了。

### Phase 3 — UPX 改竄対応

UPX magic を消した / header 改造した sample は `upx -d` で `not packed` エラー。

```bash
# magic 修復
xxd binary | grep -i upx       # UPX 文字列の位置
# 多くは `UPX!` magic を消す改造。原本は overlay の最初の 4 byte
```

修復手順:

```
1. section 名 (UPX0 / UPX1) を確認
2. overlay 先頭の 32 byte を解析
3. UPX header の magic + version を復元
4. upx -d で再試行
```

または手動 dump:

```bash
gdb ./binary
(gdb) starti
(gdb) info proc mappings      # メモリレイアウト確認
(gdb) catch syscall mprotect  # OEP 直前の mprotect で停止
(gdb) c
# OEP に近い RIP で停止 → memory dump
(gdb) dump binary memory unpacked.bin <start> <end>
```

`unipacker` (Python) で UPX / FSG / Aspack 等の自動 unpack 試行も可。

### Phase 4 — Themida / VMProtect

これらは VM 化 / mutation pack で `upx -d` 系で解けない。手順:

```
1. anti-debug bypass (ScyllaHide 等の plugin)
2. x64dbg で OEP に到達するまで step over
3. Scylla で IAT 修復 + dump
4. 修復した PE を Ghidra / IDA に投入
```

注意: VM 化で control flow が複雑、type recovery 困難。pyVMP 等の VM 解読 tool が一部有効。

### Phase 5 — その他 packer

```
ASPack:    aspackdie で auto unpack
PECompact: petite / pecompact 用 unpacker
MPRESS:    手動 dump (memory dump → IAT 修復)
Themida:   ScyllaHide + manual
VMProtect: VMP-deobfuscator / 手動
Enigma Protector: 専用 unpacker / manual dump
```

ELF packer (UPX 以外):

```
ezuri:    ELF runtime decryptor (memory dump)
midgetpack: 自作系 (case-by-case)
```

### Phase 6 — 結果検証

unpack 後の binary の確認:

```bash
file unpacked
sha256sum unpacked
strings unpacked | wc -l              # packed 時より大幅増
readelf -h unpacked / objdump -p
```

decompiled が読める段階に達したら、`reverse-engineering` で本格解析。

### Phase 7 — レポート

```
- 元 binary identity
- 検出 packer / 改造箇所
- unpack 手順 (auto / manual)
- unpacked binary identity
- 抽出した IOC / strings / 暗号 routine
```

## Tools

```
upx
unipacker / pestudio / detect-it-easy / pe-bear
gdb / x64dbg / WinDbg
Scylla (IAT 修復)
ScyllaHide (anti-debug bypass)
ghidra / radare2 / IDA
WebFetch
Bash (sandbox)
```

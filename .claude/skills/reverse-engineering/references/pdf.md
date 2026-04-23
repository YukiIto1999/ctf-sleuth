
# Malicious PDF Analysis

`reverse-engineering` から呼ばれる variant 別 deep dive

## When to Use

- phishing email や file share 経由で受領した不審 PDF
- artifact_analysis BC `FileKind.PDF`
- exploit kit 由来 PDF (CVE-2017-... 等)
- CTF forensics で flag が PDF object に隠れているケース

**使わない場面**: 通常 / 安全な PDF（→ `exiftool` で十分）。

## Approach / Workflow

### Phase 1 — triage

```bash
file doc.pdf
sha256sum doc.pdf
pdfid.py doc.pdf
```

PDFiD output:

```
PDF Header: %PDF-1.x
 obj                    n
 endobj                 n
 stream                 n
 endstream              n
 xref                   1
 trailer                1
 startxref              1
 /Page                  n
 /Encrypt               0/1   ← 暗号化
 /ObjStm                n      ← Object Stream (圧縮 object)
 /JS                    n      ← JavaScript
 /JavaScript            n
 /AA                    n      ← Auto Action (Open / Print 時 trigger)
 /OpenAction            0/1   ← 開いた瞬間に発火
 /AcroForm              0/1
 /JBIG2Decode           0/1   ← JBIG2 vuln 系
 /RichMedia             0/1   ← Flash 系 (deprecated)
 /Launch                0/1   ← 外部実行
 /EmbeddedFile          n
 /XFA                   0/1
 /URI                   n
 /Colors > 2^24         0/1
```

`/JS`/`/JavaScript`/`/OpenAction`/`/Launch`/`/EmbeddedFile`/`/AA`が >0 で要 triage。

### Phase 2 — pdf-parser で object 詳細

```bash
pdf-parser.py doc.pdf > parsed.txt           # 全 object
pdf-parser.py doc.pdf -s JavaScript          # JS object 抽出
pdf-parser.py doc.pdf -s OpenAction
pdf-parser.py doc.pdf -o <obj_id> -d out.bin -f --raw   # object dump (filter 解除)
```

Stream filter (`/FlateDecode`, `/ASCII85Decode`, `/LZWDecode`, `/RunLengthDecode`) を解凍し中身を取り出す。

### Phase 3 — JavaScript 抽出と解析

```bash
pdf-parser.py doc.pdf -o <js_obj> -d js.txt -f --raw
```

`js.txt` を:

```
- JS-Beautify で整形
- eval / unescape / String.fromCharCode 経由の難読化を解凍
- shellcode (\x90\x90\xeb...) を抽出
```

shellcode は `scdbg` (sandbox) で API call trace、または radare2 / ghidra で disasm。

### Phase 4 — peepdf (interactive)

```
peepdf doc.pdf -i
> info
> tree
> object <id>
> stream <id>
> js_analyse object <id>
> exploits
```

CVE matching (`peepdf` の DB):

```
- CVE-2008-2992 util.printf
- CVE-2009-0927 Collab.collectEmailInfo
- CVE-2010-0188 LibTIFF
- CVE-2018-4990 jpeg2000 / jbig2
- CVE-2018-15981 Adobe Reader RCE
- CVE-2021-21044 jbig2dec
- CVE-2023-26369 JS heap overflow
```

### Phase 5 — embedded file 抽出

```bash
pdf-parser.py doc.pdf -s EmbeddedFile -d embedded.bin -f --raw
file embedded.bin
```

PDF 内に exe / dropper / 別 PDF / Office を埋込みするパターン。抽出後の binary を別途解析。

### Phase 6 — JBIG2 / 古い CVE

`JBIG2Decode` filter が含まれる場合 CVE-2021-30860 系 (FORCEDENTRY 関連)、`JpxDecode` も同様。Apple iMessage 経由の zero-click として有名。

```bash
pdf-parser.py doc.pdf -s JBIG2
```

該当 object の長さ / 構造で異常パターン (規格範囲外の dimension 等) を確認。

### Phase 7 — phishing 用 PDF

malware と異なり「URL 誘導」だけのケース:

```
/URI   ↔   外部 URL
/A /S /URI  ↔ click Action → URL open
```

`pdf-parser.py doc.pdf -s URI` で抽出、URL を threat intel 検索。

### Phase 8 — レポート / IOC

```
- PDF identity (hash / version / size)
- 危険 keyword の出現数
- JS / OpenAction / Launch / EmbeddedFile の中身
- 推定 CVE / exploit
- shellcode IOC (API call / C2 URL)
- 添付 / 埋込 file の hash
- yara rule の draft
```

## Tools

```
pdfid.py / pdf-parser.py / peepdf (Didier Stevens / Jose Miguel Esparza)
scdbg (shellcode emulator)
js-beautify
yara
WebFetch
Bash (sandbox)
```

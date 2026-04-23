
# Ransomware Encryption Routine Reverse Engineering

`reverse-engineering` から呼ばれる variant 別 deep dive

## When to Use

- ランサム被害時に decryptor 作成可能性を技術評価
- public decryptor が出ている既知 family の確認
- 新規 family の暗号化 logic 解析
- CTF rev で「暗号化 binary」型問題の復号

**使わない場面**: 一般 malware の機能 review (→ `reverse-engineering`)、key を取れない場合の運用判断 (→ IR レポート判断)。

## Approach / Workflow

### Phase 1 — sample triage

```bash
file ransom.exe
sha256sum ransom.exe
strings ransom.exe | grep -iE 'crypt|aes|rsa|chacha|salsa|secp|ecdh'
```

family identification:

```
- yara rule (yara-rules / yara-forge)
- TLSH / ssdeep で 既知 sample との類似度
- VT / Malware Bazaar / TRIA で family 判定
- ID Ransomware (web service) に hash 投入
```

既知 family なら public decryptor (No More Ransom, Avast / Emsisoft / Kaspersky) を確認。

### Phase 2 — static で暗号 routine 同定

```
- AES sbox (256 byte 0x63 0x7c 0x77 ...)
- ChaCha20 magic ("expand 32-byte k")
- SHA-2 K table
- Curve25519 / secp256k1 / secp256r1 の base point
- Salsa20 sigma "expand 32-byte k"
```

`findcrypt` / `signsrch` で 定数 検出。Ghidra / IDA で関数を identify。

### Phase 3 — key 生成 logic

ransom 暗号 chain は典型的に:

```
1. file 暗号: AES-256-CBC / ChaCha20 (per-file random key + IV)
2. file key 暗号: 受信者公開鍵 (RSA-2048 / RSA-4096 / Curve25519) で wrap
3. wrapped key を file footer に embed or registry / network 送信
4. attacker 秘密鍵を持つ者だけが unwrap → 各 file key で復号
```

key 生成不備 (decryptor 可能性):

```
- RNG が rand() / time() ベース → seed 推定で 全 file key 再現
- 公開鍵が hardcode + 短い (RSA-512 / RSA-768) → 因数分解
- Bug で key が file 内 plaintext に残る (古い WannaCry の prime delete bug)
- ECB mode で同一 plaintext block が同一 ciphertext (情報漏洩のみ、復号は別)
- IV / nonce が定数 / 短い (CTR / GCM の repeat)
```

### Phase 4 — dynamic 解析 (隔離 VM)

```
1. 隔離 VM で実行
2. Process Monitor で ファイル変更を追跡
3. Frida (Windows) / cuckoo / hook で CryptoAPI 呼出を log
   - BCryptEncrypt / CryptEncrypt
   - CCCrypt / EVP_EncryptInit
4. メモリから key を dump (実行直後の memory)
```

memory 取得 + volatility で key を探す:

```bash
vol3 -f ramdump.raw windows.malfind
vol3 -f ramdump.raw yarascan.yarascan --yara-rules ransomkey.yar
```

`ransomkey.yar` に AES key の magic prefix / RSA private key footer などを書いて検索。

### Phase 5 — 既知 family chain

```
LockBit (3.0):    ChaCha20 + Curve25519, file ext .lockbit
BlackCat:         ChaCha20 / AES, Rust 製
Play:             AES + RSA
Royal:            AES + RSA
Hive (v5+):       AES-256-GCM + RSA
CL0P:             AES + RSA
Akira:            ChaCha20 + RSA
Ryuk:             AES + RSA (Wizard Spider)
WannaCry:         AES + RSA + key handle bug (古い Win)
```

family 確定後、past sample との比較で reuse / variant 同定。

### Phase 6 — decryptor 可能性判定

```
✓ decryptor 可能:
  - 公開 key が短い / 既知 sample で leaked
  - RNG が予測可能
  - 実行直後に memory dump 取得済 → key 抽出
  - bug で key が file 内に残る

✗ decryptor 不能 (典型):
  - 強い RSA + 安全な RNG + memory 取得失敗
  - hybrid 暗号で attacker 秘密鍵が必要
```

判定後、IR チームに「復号可能性 / 可能なら手順 / 不能なら身代金支払いの法的助言」を共有。

### Phase 7 — レポート

```
- sample identity / 推定 family
- 暗号 algorithm chain
- key 生成 / 配布 logic
- decryptor 可能性 (Yes/No + 根拠)
- 既知 public decryptor の有無
- IOC / yara
- 推奨対応 (バックアップ復元 / 法執行 / 身代金関連助言)
```

## Tools

```
ghidra / IDA / radare2
findcrypt / signsrch
volatility3 + yara
frida / cuckoo / Process Monitor
WebFetch (No More Ransom / VT lookup)
Bash (sandbox)
```

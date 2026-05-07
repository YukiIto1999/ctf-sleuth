---
name: performing-cryptographic-audit-of-application
description: アプリの暗号利用 (algorithm / mode / key management / RNG / signing / TLS pinning / hashing) を体系的に audit する。pentest / 自社 audit / CTF crypto で発火。
category: crypto
tags:
  - crypto-audit
  - aes
  - rsa
  - ecc
  - rng
  - key-management
---

# Cryptographic Audit of Applications

## When to Use

- web / mobile / API / desktop アプリで暗号 routine が使われている
- key management / RNG / hash / signing の妥当性確認
- bug bounty / 自社 audit で crypto bug を狙う
- CTF crypto 実装系問題

**使わない場面**: TLS server config (→ `performing-ssl-tls-security-assessment`)、blockchain (→ `blockchain-security`)、JWT 単独 (→ `testing-jwt-token-security`)。

## Approach / Workflow

### Phase 1 — inventory

source / binary を grep して暗号 routine の存在箇所を特定:

ライブラリ呼出 grep:

```bash
grep -rE 'AES|RSA|ECDSA|ECDH|HMAC|SHA|MD5|RC4|DES|3DES|ChaCha|Poly1305' src/
grep -rE 'random|Random|rand\(|/dev/urandom|/dev/random|secrets\.|os\.urandom|crypto\.randomBytes' src/
grep -rE 'pbkdf2|scrypt|bcrypt|argon2|hkdf' src/
grep -rE 'jwt|JWS|JWE|JOSE' src/
grep -rE 'TLS|SSL|HTTPS|certificate|x509' src/
```

構造 / 演算子 / 自作実装 grep (ライブラリ grep が拾わない anti-pattern を補う):

```bash
grep -rE 'def (encrypt|decrypt|cipher|sign|verify)' src/                          # 自作 cipher / signer
grep -rE '(hmac\.new|hashlib\.).*\.(digest|hexdigest)\(\)\s*==' src/              # timing-leaking compare
grep -rE 'random\.(seed|choice|randint|random|shuffle|sample|getrandbits)' src/   # 非 secure RNG (Python)
grep -rEi '(KEY|SECRET|TOKEN|PASSWORD|API_KEY)\s*=\s*[bru]?["'\''][^"'\'']{8,}' src/  # hard-coded key 候補
grep -rE 'nonce\s*=.*(len\(|time\(|^0$|counter|\\.id)' src/                       # predictable nonce
```

native binary は ghidra / IDA で `findcrypt` / signsrch。

自前 cipher / hard-coded key は SAST 横断観点でも検出対象 (`source-code-scanning` Phase 6 / 8 と併用)。 本 skill は crypto に特化した具体 query を提供する。

### Phase 2 — algorithm 評価

| 種別 | 推奨 | 廃止 / 弱 |
|---|---|---|
| symmetric | AES-256-GCM / ChaCha20-Poly1305 | DES / 3DES / RC4 / AES-ECB |
| asymmetric | RSA-2048+ / Ed25519 / X25519 / P-256 | RSA-1024 / 自前 ECC |
| hash | SHA-256 / SHA-3 / BLAKE2 | MD5 / SHA-1 |
| MAC | HMAC-SHA-256 / Poly1305 | CRC / 自作 keyed hash |
| KDF | Argon2id / scrypt / bcrypt / PBKDF2 | 単純 SHA / 短 iter |
| signing | EdDSA / ECDSA P-256 / RSA-PSS | RSA-PKCS#1 v1.5 (limited cases) |

modern 受入閾値 (2026):

- symmetric: AES key ≥128 bit、 AEAD nonce 96 bit、 nonce 必ず unique
- asymmetric: RSA modulus ≥2048 (3072 推奨)、 ECC ≥P-256
- hash: digest ≥256 bit、 MAC tag ≥128 bit (比較は constant-time)
- KDF: PBKDF2-SHA-256 ≥600k iter (OWASP 2023+) / scrypt N≥2^17 r=8 p=1 / Argon2id t≥2 m≥64MiB p≥1 / bcrypt cost≥12
- signing: Ed25519 default、 signature ≥256 bit、 ECDSA は RFC 6979 (deterministic k) 必須

### Phase 3 — mode / parameter

```
AES:
  ECB: 同 plaintext block が同 ciphertext block (情報漏洩)
  CBC: padding oracle (TLS 1.0 / web app)
  CTR: nonce reuse で 2 つの plaintext XOR
  GCM: nonce reuse で auth tag forgery
  XTS: storage encryption 用、message に使わない

RSA:
  PKCS#1 v1.5 padding: Bleichenbacher oracle / FlipBit / RSA-CRT bug
  OAEP: 推奨

EdDSA:
  Ed25519: 標準
  Ed448: 大きい (TLS 1.3 では主流でない)

ECDSA:
  k (nonce) 再利用で private key 復元
  RFC 6979 (deterministic) を使うべき
```

### Phase 4 — RNG

```
- secure RNG (os.urandom / /dev/urandom / SecureRandom / SystemRandom / crypto/rand)
- non-secure (Math.random / rand() / time() / mt19937 直書き)
- entropy 不足 (boot 直後 / VM 構築直後)
- hard-coded seed (CTF / dev mode の置き忘れ)
```

```bash
grep -rE 'Math\.random|rand\(\)|mt19937|srand\(' src/
```

### Phase 5 — key management

```
- key 生成: secure RNG で生成?
- key storage: KMS (AWS/GCP/Azure KMS) / HSM / file? hard-coded?
- key rotation: rotation 仕組みあるか
- key derivation: master key + salt + KDF
- key wrap: AES-KW / RSA-OAEP / X25519 で wrap
- key destruction: memory 上から消すか (zeroize)
- backup: encryption / split / threshold (Shamir Secret Sharing)
```

### Phase 6 — signing / authentication

```
- signature scheme (Ed25519 / ECDSA / RSA-PSS)
- replay protection (nonce / timestamp / counter)
- domain separation (per-context tag)
- multi-signature (m-of-n, threshold)
- 比較は constant-time: Python `hmac.compare_digest` / Go `crypto/subtle.ConstantTimeCompare` / Node `crypto.timingSafeEqual` / Java `MessageDigest.isEqual`
  → MAC / signature / token / session ID を `==` `equals()` `strcmp()` で比較していたら High (timing side-channel)
```

### Phase 7 — TLS / transport

別 skill `performing-ssl-tls-security-assessment` で網羅。要点:

```
- TLS 1.2 / 1.3 のみ
- 強 cipher suite
- pinning (mobile / IoT)
- HSTS / SCT / OCSP
```

### Phase 8 — protocol level

```
- 暗号化 layer + auth layer の順序 (encrypt-then-MAC が安全)
- session key の derive (HKDF + per-direction key)
- forward secrecy (PFS)
- post-quantum readiness (今は X25519+Kyber 等 hybrid が出始め)
```

### Phase 9 — レポート

```
- 対象 module / 暗号 routine inventory
- 検出 issue (severity 別)
  - weak alg / mode / key size
  - RNG 不適切
  - key 管理不備
  - replay / nonce reuse
- 推奨修正 (具体 algorithm / 推奨 lib)
- migration plan (post-quantum 含む)
```

## Tools

```
findcrypt / signsrch (binary)
semgrep crypto rules / bandit / gosec
openssl / cryptography (Python) / ring / libsodium
WebFetch / WebSearch
Bash (sandbox)

# grep + python3 のみの最低限環境向け fallback:
#   semgrep / bandit / gosec 不在 → 本 Phase 1 の grep panel を直接実行
#   findcrypt / signsrch 不在     → SHA-256 / AES sbox / DES round constant 等の hex literal を
#                                    xxd binary | grep -E '6a09e667|428a2f98|63 7c 77 7b' で検出
#   動的検証                       → python3 -c "from <target> import ...; ..." で PoC スクリプト
```

## Related Skills

- `performing-ssl-tls-security-assessment`, `blockchain-security`
- `testing-jwt-token-security`
- `reverse-engineering`
- `web-pentester`, `api-security`, `authentication`
- `source-code-scanning`
- `bug-bounter`, `web-bounty`, `hackerone`

## Rules

1. **modern primitives** — Ed25519 / X25519 / AES-GCM / Argon2id を default に
2. **自前実装は避ける** — verified library 利用を推奨
3. **migration 計画** — weak alg は scheduled に置換
4. **post-quantum readiness** — 数年内に hybrid 移行を見据える

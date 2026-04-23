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

```bash
grep -rE 'AES|RSA|ECDSA|ECDH|HMAC|SHA|MD5|RC4|DES|3DES|ChaCha|Poly1305' src/
grep -rE 'random|Random|rand\(|/dev/urandom|/dev/random|secrets\.|os\.urandom|crypto\.randomBytes' src/
grep -rE 'pbkdf2|scrypt|bcrypt|argon2|hkdf' src/
grep -rE 'jwt|JWS|JWE|JOSE' src/
grep -rE 'TLS|SSL|HTTPS|certificate|x509' src/
```

native binary は ghidra / IDA で `findcrypt` / signsrch。

### Phase 2 — algorithm 評価

| 種別 | 推奨 | 廃止 / 弱 |
|---|---|---|
| symmetric | AES-256-GCM / ChaCha20-Poly1305 | DES / 3DES / RC4 / AES-ECB |
| asymmetric | RSA-2048+ / Ed25519 / X25519 / P-256 | RSA-1024 / 自前 ECC |
| hash | SHA-256 / SHA-3 / BLAKE2 | MD5 / SHA-1 |
| MAC | HMAC-SHA-256 / Poly1305 | CRC / 自作 keyed hash |
| KDF | Argon2id / scrypt / bcrypt / PBKDF2 (>= 600k iter) | 単純 SHA / 短 iter |
| signing | EdDSA / ECDSA P-256 / RSA-PSS | RSA-PKCS#1 v1.5 (limited cases) |

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

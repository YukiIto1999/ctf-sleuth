---
name: testing-jwt-token-security
description: JWT 実装を秘密鍵推測 / claim 改竄 / 期限・kid 検証漏れ・JWE 偽装まで含めて棚卸し試験する。CTF / bug bounty / pentest で JWT が出てきた時の総合評価入口。
category: web
tags:
  - jwt
  - jwe
  - jws
  - hmac
  - brute-force
  - token-security
---

# JWT Token Security Assessment

## When to Use

- 対象 API / SSO / OAuth フローで JWT が発行・検証される
- JWT の脆弱性類別をまとめて棚卸ししたい (single 観点 deep dive ではない)
- JWE / JWS / nested JWT の組合せが含まれる構成
- 短時間で複数の JWT 攻撃 vector を一度に投げたい

**使わない場面**: OAuth flow 全体の評価 (→ `testing-oauth2-implementation-flaws`)、JWT を含まない authentication (→ `authentication`)。

単一観点を深掘りするときは references/ を参照: alg confusion (RS256 → HS256 / kid / jku / x5u 経由) は `references/alg-confusion.md`、`alg=none` 系は `references/alg-none.md`。

## Approach / Workflow

### Phase 1 — 観察

```
1. JWT を取得 (login / refresh / OAuth 認可コード交換)
2. 3 part decode (header / payload / signature)
3. 取得経路 (Authorization Bearer / Cookie / form / URL fragment)
4. 失効 / 更新 (refresh token / re-issue tempo)
5. JWKS / public key の所在 (`/.well-known/jwks.json`, `/oauth/keys`)
```

### Phase 2 — 攻撃 vector の網羅試験

| 種別 | 攻撃 |
|---|---|
| 署名検証無し | `alg=none` 系 (`references/alg-none.md`) |
| 公開鍵流用 | RS256 → HS256 confusion (`references/alg-confusion.md`) |
| HMAC 鍵推測 | hashcat mode 16500 で wordlist 攻撃 (HS256 で公開鍵使わない場合) |
| kid 注入 | path traversal / SQLi / URL 経由の鍵置換 |
| jku / x5u 注入 | 攻撃者ホストの JWKS / X.509 を指す URL |
| claim 改竄 | sub / role / iss / aud の置換 |
| 有効期限無視 | exp / nbf を未来 / 過去に書換え |
| token replay | 過去 token の reuse、jti 検証なし |
| JWE 暗号攻撃 | RSA1_5 padding oracle / weak ECDH-ES / direct key encryption の typ confusion |

### Phase 3 — HMAC 鍵推測

HS256 / HS384 / HS512 で短い秘密鍵が使われていると brute force が成立する:

```
hashcat -m 16500 jwt.txt rockyou.txt
john --format=HMAC-SHA256 jwt.txt --wordlist=rockyou.txt
```

JWT 1 行を `<HEADER>.<PAYLOAD>.<SIGNATURE>` のまま入力。鍵が判明したら任意 token を再発行できる。

### Phase 4 — claim 改竄

判明した鍵 / 受け入れられる alg で claim を書換える:

```python
import jwt, time
fresh = jwt.encode({
  "sub": "admin",
  "role": "admin",
  "iss": original_iss,
  "aud": original_aud,
  "exp": int(time.time()) + 3600,
  "iat": int(time.time()),
  "jti": new_jti
}, key, algorithm="HS256")
```

issuer / audience の検証が抜けていれば、別 service の token を流用 (cross-tenant token replay)。

### Phase 5 — JWE 系

JWE は header `enc` と `alg` の組合せで暗号方式が決まる。

| 観点 | 試験 |
|---|---|
| RSA1_5 | Bleichenbacher padding oracle で AES key を 1 bit ずつ復元 |
| direct key (`alg=dir`) | content-encryption key を共有秘密として brute force |
| ECDH-ES | invalid curve attack (使われない曲線の点を入れて鍵交換破り) |
| typ confusion | `cty=JWT` で nested JWS の中身を信頼させる |

### Phase 6 — 自動化

```
jwt_tool $JWT -M at -t 'https://target/api/me' -rh 'Authorization: Bearer $JWT'
  # all-tests scan + automatic re-request
jwt_tool $JWT -X k -pk public.pem      # alg confusion
jwt_tool $JWT -X a                     # alg=none 系
jwt_tool $JWT -X i                     # claim 改竄一覧
jwt_tool $JWT -C -d wordlist.txt       # HMAC crack
```

burp の `JWT Editor` extension は GUI で同等。

### Phase 7 — レポート

```
- token 種別 / アルゴリズム / 期限ポリシ
- 検証された脆弱性 (alg confusion / brute / kid SQLi など)
- 各脆弱性の PoC (forged token は redact)
- 修正提案 (alg allowlist / kid sanitize / EdDSA / iat/jti enforcement)
```

## Tools

```
jwt_tool
burp + JWT Editor
hashcat (16500)
john (HMAC-SHA256)
python PyJWT / cryptography
WebFetch
Bash (sandbox)
```

## Related Skills

- `web-pentester`, `api-security`, `authentication`
- `testing-oauth2-implementation-flaws`, `detection-web`
- `performing-cryptographic-audit-of-application`
- `injection` (kid SQLi 系)

## Rules

1. **スコープ厳守** — token 試験は authorized scope のみ
2. **PoC 最小** — 1 user impersonation 確認 → 停止。一括 user 列挙はしない
3. **brute force 帯域** — オフライン crack は問題ないが、online API 投げ込みは低頻度
4. **forged token / cracked secret を report に貼らない** — secret は length のみ

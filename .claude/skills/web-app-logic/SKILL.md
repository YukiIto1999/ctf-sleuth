---
name: web-app-logic
description: スキャナでは検出できないビジネスロジック欠陥・レース・認可境界破り・キャッシュ汚染 / 欺瞞・情報開示を体系的に試験する。CTF web で workflow 制約を破る系問題、bug bounty で高額帯の logic 系で発火。
category: web
tags:
  - web
  - logic
  - business-logic
  - race
  - access-control
  - cache
---

# Web Application Logic

## When to Use

- 機能フローが複雑で、スキャナの汎用シグネチャでは捉えられない欠陥が疑われる
- 残高 / クーポン / 在庫 / 出金 / 招待 など状態を進める操作がある
- ロール / テナント / 個人別リソース境界が複数あり認可漏れが起こりうる
- CDN / reverse proxy が前段にあり、cache layer の挙動が独立している

**使わない場面**: 単純な汎用脆弱性（→ `injection`、`client-side`、`server-side` 個別）。

## Approach / Workflow

### Phase 1 — フローと不変条件の言語化

1〜2 本のユーザフロー（signup→primary action、特権 flow があれば 1 本）を辿って、**観察した具体オブジェクト**で不変条件を書き出す:

```
- order が submitted の状態でしか shipping は始まらない
- coupon は 1 ユーザ 1 回まで
- balance は negative にならない
- user A の note は user B に見えない
- approval は 2 名以上
```

各不変条件に対して、破る試験を 1 つ起案する。

### Phase 2 — ビジネスロジック濫用バックログ (10–15 件)

各項目はこのフォーム:

```
N. <名前> — 対象: <flow / object>
   前提: <role / tenant / state>
   濫用案: <破る不変条件 / tamper / replay / race / state skip>
   検証: <high-level steps>
   成功シグナル: <どの応答で成立とするか>
   影響: <1 文>
```

濫用パターンは概ね以下に分類:

| カテゴリ | 例 |
|---|---|
| state skip | step 3 を踏まずに step 5 を直接送る |
| price manipulation | `price=0`, `quantity=-1`, `currency=KRW` (本来 USD) |
| coupon / credit | 同 coupon 並列適用、適用後の cancel で残量増加 |
| approval bypass | self-approve、approval 不要分岐に乗せる |
| tenant boundary | 別 tenant の resource ID を自分の token で参照 |
| feature gate bypass | premium feature を free アカウントで呼ぶ |
| limit bypass | rate limit を IPv6 や header で回避 |
| invitation abuse | 招待リンクを使い回す / 期限破る |

### Phase 3 — レースコンディション

```
TOCTOU (Time of Check / Time of Use)
- 残高チェック → 出金 の間に別 thread の残高チェックが通る
- coupon 1 回制限を 50 並列で回避
- promotion code を同時 redeem
- friend invite reward を同 token で 100 並列
```

実装:

```
seq 50 | xargs -P 50 -I {} curl -s -X POST 'https://target/api/redeem' \
  -H 'Authorization: Bearer <T>' -d '{"code":"X"}'
```

burp の `Turbo Intruder` / `single-packet attack` がより信頼性が高い (1 パケットに HTTP/2 streams を詰めて TCP 順序依存を消す)。

### Phase 4 — 認可境界 (IDOR / 横 / 縦)

| 種別 | 試験 |
|---|---|
| 横 | user A の token で user B のリソース ID を参照 |
| 縦 | 一般ユーザの token で admin endpoint |
| 強制ブラウジング | `/admin/`, `/internal/`, `/.git/`, `/.svn/`, `/api/v1/admin/users` |
| pre-auth ルート | 認証必須を `?force=true` 等で回避 |
| pre-auth 削除 | DELETE が CSRF token なしで通る |

### Phase 5 — Cache Poisoning / Deception

cache poisoning:

```
1. unkeyed header (X-Forwarded-Host, X-Forwarded-Proto, User-Agent) を変えても
   同じ cache key にヒットするか観察
2. 該当 header に攻撃者制御 URL を入れる
3. 後続のユーザにその応答が配られるか確認 (低トラフィック endpoint で示す)
```

cache deception:

```
GET /account/me/profile.css → static として cache される
→ /account/me/profile.css の応答に動的データが残ると別ユーザに漏洩
バリエーション: ;.css, %0a.css, /static/../account/me, normalization 不一致
```

### Phase 6 — 情報開示

- error message の stack trace / DB schema 漏洩
- debug endpoint (`/debug`, `/_debug`, `/actuator/`, `/api/health/info`)
- `.git/`, `.svn/`, `.env`, `Dockerfile`, `docker-compose.yml`, `package.json`, `composer.lock` の露出
- cloud metadata 経由（→ SSRF 系）
- response の HTTP/2 push で隠した URL がブラウザに見えるパターン

### Phase 7 — PoC

logic 系 PoC は手順依存。以下フォーマット:

```
背景: <フロー説明>
不変条件: <破ろうとしているもの>
手順:
  1. ... (curl / burp request)
  2. ...
  3. ...
影響: <被害>
```

## Tools

```
curl
burp (Turbo Intruder, Repeater, Param Miner)
mitmproxy
ffuf
WebFetch
Bash (sandbox)
```

## Related Skills

- `web-pentester`, `api-security`, `authentication`, `client-side`, `server-side`
- `bug-bounter`, `web-bounty`
- `injection`, `server-side`
- `detection-web` (race / cache 異常を log で検知する視点)

## Rules

1. **スコープ厳守** — 試験は test account 同士で示す。一般ユーザ被害が出る濫用は試さない
2. **race の負荷** — 50 並列を上限にし、結果が出たら止める。サービス停止の予感が出たら即時撤退
3. **可逆性** — 状態変更系の試験は元に戻せる範囲で行う。不可逆 (出金 / 削除) は 1 回限定で示す
4. **取得情報の取扱** — 他ユーザのリソースが取れた場合、内容を見ずに ID と response の最小行のみ控える

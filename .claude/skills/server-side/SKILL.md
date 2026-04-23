---
name: server-side
description: SSRF / HTTP request smuggling / path traversal / 危険なファイルアップロード / 安全でないデシリアライズ / Host header injection など、サーバ側で発火する脆弱性の体系的試験。CTF web の RCE 系・HTB の web 入口で発火する。
category: web
tags:
  - web
  - server-side
  - ssrf
  - rce
  - smuggling
  - deserialization
  - traversal
---

# Server-Side Vulnerabilities

## When to Use

- サーバ側で外部リクエスト発行・ファイル取扱い・シリアル化解除を行う endpoint がある
- proxy / CDN を介する構成で HTTP request smuggling の余地を疑う
- `Host` ヘッダや multi-tenant 設計でルーティング詐称が成立しそう
- ファイルアップロード機能を持ち、検証ロジックが甘そう

**使わない場面**: 純粋なクライアント側脆弱性 (→ `client-side`)、クエリ系の DB 注入のみ (→ `injection`)。

SSRF の variant 深掘りは references/ を参照: 応答に fetch 結果が返る経路 = `references/ssrf-visible.md`、応答が見えない blind 経路 = `references/ssrf-blind.md`。

## Approach / Workflow

### Phase 1 — 表面の列挙

サーバ処理点を抽出:

```
- URL パラメータ / form / cookie / header から外部 fetch を起こす機能 (preview, OG, webhook, import URL, PDF generator)
- 任意 path を扱う機能 (zip 展開, file download, log fetch)
- アップロード受付け endpoint
- session / cache / queue 経由の deserialization
- proxy / CDN 構成 (X-Forwarded-* の扱い)
```

### Phase 2 — SSRF

| 観点 | 試験 |
|---|---|
| 内部サービス | `http://127.0.0.1:6379`, `http://localhost:9200`, kubelet `10250` 等を url パラメータに |
| cloud メタデータ | `http://169.254.169.254/latest/meta-data/` (AWS), `metadata.google.internal` (GCP), `169.254.169.254/metadata/v1/` (DO), `100.100.100.200` (Aliyun) |
| protocol smuggling | `gopher://` で SMTP / Redis / memcached を発火, `dict://`, `file://` |
| DNS rebinding | TTL 0 の DNS で初回検証通過 → 2 回目で内部 IP |
| URL parser 不一致 | `http://attacker.com#@127.0.0.1/`, `http://127.0.0.1.attacker.com/` |
| blind SSRF | `out-of-band` (DNS / HTTP) で発火確認 — 詳細は `references/ssrf-blind.md` |

### Phase 3 — HTTP Request Smuggling

frontend / backend で `Content-Length` (CL) と `Transfer-Encoding` (TE) の解釈が違うときに成立。

```
CL.TE  : front は CL を見る、back は TE を見る
TE.CL  : 逆
TE.TE  : 両方が TE を見るが obfuscation で片方が CL fallback
CL.0   : POST body を見ない back 側 (HTTP/2 downgrade)
H2.CL  : HTTP/2 の擬似ヘッダ + CL の不整合
h2c smuggling : Upgrade: h2c で HTTP/2 にアップグレード後の暗黙の枠送信
```

burp `HTTP Request Smuggler` を使うのが定番。connection pooling desync 検出にも有効。確認は `request smuggling tester` (smuggler.py / h2csmuggler) で出す。

### Phase 4 — Path Traversal

```
?file=../../../../etc/passwd
?file=..%2f..%2f..%2fetc%2fpasswd
?file=..%252fetc%252fpasswd     # 二重 URL encode
?file=....//....//etc/passwd    # 一部の正規化が ../ を 1 個削るだけ
?file=/etc/passwd%00.txt        # null byte (PHP < 5.3.4)
?file=php://filter/convert.base64-encode/resource=index.php
```

normalize → 開く前に realpath / chroot / allowlist が無いか観察。WAF の signature 回避には URL encode / overlong UTF-8 / case 変換を組合せる。

### Phase 5 — File Upload

- 拡張子 bypass: `.php`, `.phtml`, `.php5`, `.phar`, `.jsp`, `.jspx`, `.aspx`, `.cer`, `.jsx`
- MIME type / magic bytes 改竄: `.png` 先頭に PNG magic、後ろに `<?php ... ?>`
- polyglot: `phar+phpgif` の組合せ
- path injection: `filename="../../shell.php"`
- 上書きされた config / .htaccess / web.config 経由の動作変更

### Phase 6 — Insecure Deserialization

| 言語 | 入口 | gadget |
|---|---|---|
| Java | session / jsf state / RMI / remote API | ysoserial CommonsCollections / Spring / Hibernate / Click |
| PHP | session.serialize_handler / `unserialize` / cookie | phpggc Laravel / Yii / Symfony / Monolog |
| Python | `pickle.loads` (危険) / pyyaml (`!!python/object/apply`) | `__reduce__` で os.system |
| .NET | BinaryFormatter / SoapFormatter | ysoserial.net TypeConfuseDelegate |
| Ruby | Marshal.load / yaml.load | universal RCE chain |
| Node | node-serialize / serialize-javascript | function serialization |

検出は cookie / hidden field / API body の中に shape (`O:`, `\xac\xed`, `eyJ` の特定パターン) を探す。

### Phase 7 — Host Header Injection

- password reset link が `Host` を信用していないか
- 仮想ホスト routing が Host で多テナントを切替えていないか
- cache key に Host が含まれず poisoning 可能か

```
GET /reset?email=victim@example.com HTTP/1.1
Host: attacker.com
```

### Phase 8 — 確証と PoC

最小再現 + 影響:

```
SSRF       → cloud metadata 経由の credential 取得 → IAM 列挙
smuggling  → 別ユーザ session の hijack
traversal  → /etc/passwd / config / .env を読み出し
upload     → webshell 設置 → コマンド実行
deserial   → RCE で /etc/hostname など特定ファイル
host       → password reset を attacker domain に送る → アカウント乗取
```

## Tools

```
curl
ffuf
gopherus           (SSRF gopher payload 生成)
ysoserial / ysoserial.net / phpggc
http-request-smuggler / smuggler.py / h2csmuggler
WebFetch / WebSearch
Bash (sandbox)
mitmproxy / Burp
```

## Related Skills

- `web-pentester`, `client-side`, `api-security`, `web-app-logic`
- `injection`
- `authentication`, `testing-jwt-token-security`
- `detection-web` (防御視点)

## Rules

1. **スコープ厳守** — internal IP / metadata 経由の探索は明示許可下のみ
2. **RCE は最小実証** — `id` / `whoami` / DNS callback で済ませる。任意ファイル削除・再起動・persistence は禁止
3. **smuggling 試験は慎重** — 他ユーザ session の汚染が起きうるので低頻度・低帯域・観察主体
4. **upload された artefact** — 試験後は削除を要求 / 自前で削除する

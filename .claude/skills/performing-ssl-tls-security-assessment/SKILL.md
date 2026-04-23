---
name: performing-ssl-tls-security-assessment
description: SSL / TLS server 設定を sslyze / testssl.sh / nmap で評価し、cipher / protocol version / cert chain / 既知 CVE への耐性を判定する。CTF / pentest / 自社 audit で発火。
category: network
tags:
  - tls
  - ssl
  - sslyze
  - testssl
  - cert
  - cipher
---

# SSL/TLS Security Assessment

## When to Use

- web / API / mail server の TLS 構成を audit
- 既知脆弱性 (Heartbleed / POODLE / FREAK / Logjam / DROWN) の有無を確認
- cert chain / OCSP / SCT / HSTS / HPKP の設定確認

**使わない場面**: TLS pinning bypass のクライアント側試験 (→ `ios-security` 等)、network capture 上の暗号化通信の解析 (→ `network-analyzer`)。

## Approach / Workflow

### Phase 1 — 主要ツール

```
sslyze        Python ベース、scriptable
testssl.sh    Bash、CVE 判定が豊富
nmap --script ssl-*       軽量
sslscan       quick check
qualys SSL Labs (web)     external assess
```

### Phase 2 — sslyze

```bash
sslyze --regular target:443
sslyze --json_out report.json target:443
sslyze target:443 \
  --certinfo --robot --heartbleed --openssl_ccs --reneg \
  --tlsv1_2 --tlsv1_3 --resum --compression --fallback
```

### Phase 3 — 評価項目

| 観点 | desired | NG |
|---|---|---|
| protocol | TLS 1.2 + 1.3 のみ | TLS 1.0 / 1.1 / SSL 3.0 / 2.0 有効 |
| cipher (AEAD) | ECDHE + AES-GCM / ChaCha20-Poly1305 | RC4 / 3DES / DES / NULL / EXPORT / DH-1024 / RSA-key-exchange |
| cert | 2048+ RSA / 256+ ECDSA / SHA-256+ | 1024 RSA / SHA-1 / 自己署名 production |
| chain | complete chain | intermediate 不在 |
| HSTS | 有効 + preload | 無 |
| OCSP stapling | 有効 | 無 |
| SCT | embedded | 無 |
| renegotiation | secure renegotiation | client-initiated insecure |
| compression | OFF | TLS compression ON (CRIME) |
| TLS_FALLBACK_SCSV | 有効 | 無 (POODLE downgrade 余地) |
| Forward Secrecy | 全 cipher が PFS | RSA key exchange 残 |
| heartbleed | not vuln | OpenSSL 1.0.1 系で patch なし → vuln |
| ROBOT | not vuln | RSA-PKCS1 v1.5 で oracle |
| DROWN / FREAK / Logjam | not vuln | weak DH / RSA |

### Phase 4 — testssl.sh (CVE 判定豊富)

```bash
./testssl.sh --severity HIGH --jsonfile out.json target:443
```

CVE-2014-0224 (CCS Injection)、CVE-2016-0703 (DROWN)、CVE-2014-3566 (POODLE)、CVE-2018-0732 (LogJam) などを自動判定。

### Phase 5 — cert chain 詳細

```bash
openssl s_client -connect target:443 -servername target -showcerts < /dev/null
openssl x509 -in cert.pem -noout -text
openssl s_client -connect target:443 -CAfile rootca.pem
```

OCSP 確認:

```bash
openssl ocsp -issuer issuer.pem -cert cert.pem -text -url <ocsp_url>
```

SCT (Signed Certificate Timestamp) は CT log に登録されているか:

```
crt.sh 検索でくる cert がそれ
```

### Phase 6 — config に基づく remediation 例

```
nginx:
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_ciphers TLS_AES_256_GCM_SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:...
  ssl_prefer_server_ciphers off;
  ssl_session_tickets off;
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";
  ssl_stapling on;
  ssl_stapling_verify on;
```

```
apache:
  SSLProtocol -all +TLSv1.2 +TLSv1.3
  SSLCipherSuite ...
  SSLHonorCipherOrder off
  Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
```

### Phase 7 — レポート

```
- target / port / 取得 cert chain
- 検出 vulnerability (CVE 番号 / severity)
- protocol / cipher / 設定上の NG
- 推奨設定 snippet
```

## Tools

```
sslyze
testssl.sh
sslscan / nmap --script ssl-*
openssl s_client / x509 / ocsp
WebFetch (qualys SSL Labs)
Bash (sandbox)
```

## Related Skills

- `network-analyzer`
- `web-pentester`, `api-security`, `authentication`, `testing-jwt-token-security`
- `performing-cryptographic-audit-of-application`
- `reverse-engineering`, `network-hunter` (cert fingerprint)
- `dfir`, `blue-teamer`, `bug-bounter`

## Rules

1. **scope** — 認可済 host / port のみ
2. **rate** — 重い scan を本番に当てるときは throttle
3. **PII redaction** — cert SAN に internal name が出る場合 redact
4. **修正提案を含む報告**

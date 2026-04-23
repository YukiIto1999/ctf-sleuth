
# Cobalt Strike Malleable C2 Profile Analysis

`reverse-engineering` から呼ばれる variant 別 deep dive

## When to Use

- 公開 / 流出した Malleable C2 profile (`.profile`) を解析
- profile から observed traffic を予測 / 検知 rule を生成
- beacon config (→ `reverse-engineering`) と pair で actor 識別

**使わない場面**: live beacon の rev (→ `reverse-engineering`)。

## Approach / Workflow

### Phase 1 — profile 構造

`.profile` は team server 設定:

```
set sleeptime "60000";
set jitter "20";
set useragent "Mozilla/5.0 (...)";
http-get {
  set uri "/load";
  client {
    header "Accept" "*/*";
    metadata { base64; prepend "id="; header "Cookie"; }
  }
  server {
    header "Content-Type" "image/png";
    output { netbios; print; }
  }
}
http-post {
  set uri "/submit";
  client {
    parameter "id" { netbios; print; }
    output { print; }
  }
}
```

### Phase 2 — parse

```
- dissect.cobaltstrike (Fox-IT) python module
- parse_profile.py 系の OSS parser
```

```bash
pip install dissect.cobaltstrike
cs-parse-malleable beacon-default.profile
```

抽出される field:

```
sleep / jitter
user-agent
URI list (GET / POST)
header (静的 / 動的)
metadata transform (base64 / netbios / mask / prepend / append)
TLS profile (SNI / cert pin)
DNS profile
```

### Phase 3 — 観測パターンの推定

profile から実 traffic の見え方を予測:

```
- GET /load + Cookie: <encoded>      → metadata transform 適用後
- POST /submit + body: <encoded>     → response 暗号化された beacon output
- HTTP/1.1 + 特定 User-Agent 連続発生
```

### Phase 4 — fingerprint 化

```
- URI pattern 集合
- header 順序
- User-Agent 文字列
- response の Content-Type と長さ
- TLS cert (Self-signed の subject / SAN 不在 / not_before の閾値)
- JA3 / JA3S
```

### Phase 5 — Malleable profile の actor 紐付け

公開 profile (Github / Twitter で公開された template):

```
amazon.profile / jquery-c2.4.5.profile / cs-default.profile
amazon-cdn.profile / google-resourceless.profile
```

これらを default で使う actor は不慣れ／自前 modify してる actor は経験豊富。modify 跡の癖で actor identification。

### Phase 6 — Malleable PE config (post-ex stage)

profile には PE post-ex も含まれる:

```
post-ex {
    set spawnto_x86 "%windir%\\\\syswow64\\\\rundll32.exe";
    set spawnto_x64 "%windir%\\\\sysnative\\\\rundll32.exe";
    set obfuscate "true";
    set smartinject "true";
    set amsi_disable "true";
}
```

amsi_disable / smartinject / spawnto は EDR detection 評価に直結。

### Phase 7 — Suricata / Zeek rule の draft

```
alert http any any -> any any (
  msg:"Cobalt Strike Beacon GET /load default";
  http.uri; content:"/load";
  http.user_agent; content:"Mozilla/5.0";
  flow:to_server,established;
  classtype:trojan-activity; sid:1000001; rev:1;
)
```

URI / header / user-agent / TLS pattern の組合せで signature を作る。

### Phase 8 — レポート / IOC

```
- profile 出所 (公開 / 流出 / 改造度合)
- 観測予測 (URI / header / UA)
- 推定 actor / actor cluster
- detection rule (Suricata / Zeek / Sigma)
- TI feed 投入用 indicator
```

## Tools

```
dissect.cobaltstrike
1768.py
yara
zeek / suricata (rule 適用)
WebFetch
Bash (sandbox)
```

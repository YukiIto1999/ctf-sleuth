
# Outlook PST / OST Forensics

`disk-forensics` から呼ばれる variant 別 deep dive

## When to Use

- Outlook の PST / OST file が evidence に含まれる
- email 経由 phishing / BEC / 内部漏洩の調査
- 削除済 message や添付の復元
- email metadata からの timeline 構築

**使わない場面**: live Exchange / M365 への直接 query (→ Microsoft Graph API)、Gmail / mbox 形式 (→ 別ツール)。

## Approach / Workflow

### Phase 1 — file 確認

```
PST: archive / export 形式。完全 mailbox 持ち出し
OST: cached mode の同期データ。サーバ側と紐付く

%LOCALAPPDATA%\Microsoft\Outlook\*.ost
<UserDocs>\Outlook Files\*.pst
<NetworkShare>\<user>.pst (share の archive)
```

```bash
file mail.pst
sha256sum mail.pst                # チェーン保全
```

### Phase 2 — libpff (`pff-tools`)

```bash
pffinfo mail.pst                  # ファイル情報
pffexport -m all mail.pst          # 全 message export
pffexport -m all -t output mail.pst
```

`-m` の値:

```
all                 全 folder
recovered           削除済の復元
debug               構造 dump (forensic 用)
```

Output は folder 階層を再現:

```
output/
├── Inbox/
│   ├── Message00001/Message.txt
│   ├── Message00001/Attachments/
│   ├── ...
├── Sent Items/
├── Deleted Items/
├── Recoverable Items/  (Exchange のごみ箱)
```

### Phase 3 — message 解析

各 Message ファイルから:

```
- From / To / Cc / Bcc
- Subject
- Received / Sent timestamp
- Message-ID / In-Reply-To / References (chain 再構築)
- Authentication-Results (SPF / DKIM / DMARC)
- X-Mailer / X-Originating-IP / Received chain (`phishing-investigation`)
- Body (plain / HTML)
- 添付 (filename / size / hash)
```

### Phase 4 — 削除済 message 復元

```
Outlook の "ごみ箱" 相当: Deleted Items
Exchange の "Recoverable Items" (purges, versions, deletions)
PST 内の slack / unallocated 領域
```

`pffexport -m recovered` または `bulk_extractor` で raw scan。

### Phase 5 — 添付 triage

```bash
find output/ -path '*/Attachments/*' -type f | xargs sha256sum > attachments.sha256
clamscan -r output/                         # AV scan
yara -r rules/ output/                       # custom rule
exiftool output/Inbox/Message00001/Attachments/*.docx
oletools (oleid / olevba) output/.../macro.docm
```

phishing 調査では:

- 拡張子と magic byte の一致確認 (`.pdf` の中身が EXE)
- Office macro auto-exec
- HTML smuggling (添付 HTML の base64 blob)

### Phase 6 — timeline / actor 連鎖

```
- 受信 → 開封 → 添付実行 → 内部転送 / 外部送信
- 同一 thread の reply chain
- Bcc 経由の暗黙コピー
- forwarding rule (auto-forward の証跡)
```

forwarding rule は OST に inbox rules として埋まる:

```bash
pffinfo -m all mail.ost | grep -i 'rule\|forward'
```

### Phase 7 — search

大量 message の高速検索:

```bash
ripgrep -r 'phishing keyword' output/
grep -r 'http://attacker.com' output/
```

または ElasticSearch / OpenSearch にロードして対話 query。

### Phase 8 — レポート

```
- mailbox サイズ / 期間
- 重要 message (phishing / BEC / 内部漏洩) の hash / 件数
- 関与した actor (送信者 / 受信者 / 中継 IP)
- 添付 IOC
- 削除 / forwarding rule の証跡
- timeline
```

## Tools

```
libpff (pff-tools)
readpst (perl 系、補助)
oletools / oleid / olevba
exiftool
yara / clamav
ripgrep
WebFetch
Bash (sandbox)
```

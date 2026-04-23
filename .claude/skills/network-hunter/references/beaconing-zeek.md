
# Zeek Beacon Pattern Detection

`network-hunter` から呼ばれる variant 別 deep dive

## When to Use

- Zeek conn.log がある環境で beacon 検出を運用
- malware sandbox 出力 pcap から beacon 特定
- TI feed の補完用に beacon-style C2 を発見

**使わない場面**: 単発 pcap の hunt (→ `network-hunter` の generic 手順)、DNS 系 (→ `network-hunter`)。

## Approach / Workflow

### Phase 1 — conn.log の field

```
ts uid id.orig_h id.orig_p id.resp_h id.resp_p proto service duration orig_bytes resp_bytes conn_state
```

### Phase 2 — flow の集約

beacon の特徴: 同 (src, dst) pair が 一定間隔で連続発生。

```bash
zeek-cut ts id.orig_h id.resp_h id.resp_p < conn.log > flows.tsv
```

```python
import pandas as pd, numpy as np
df = pd.read_csv('flows.tsv', sep='\t', names=['ts','src','dst','dport'])
df['ts'] = pd.to_datetime(df['ts'].astype(float), unit='s')

g = df.groupby(['src','dst','dport'])
stats = g['ts'].agg(['count', lambda s: s.diff().dt.total_seconds().std(),
                     lambda s: s.diff().dt.total_seconds().mean()])
stats.columns = ['count','std','mean']
candidates = stats[(stats['count'] > 30) & (stats['mean'] > 10) & (stats['std'] < stats['mean']*0.3)]
print(candidates.sort_values('count', ascending=False).head(20))
```

`std / mean < 0.3` (CV) は周期性が高い候補。

### Phase 3 — payload size の一致

beacon は同 size response を返すことが多い。

```python
df2 = pd.read_csv('flows.tsv', sep='\t', names=['ts','src','dst','dport','o','r'])
g2 = df2.groupby(['src','dst','dport'])
sz = g2['r'].agg(['mean','std','count'])
sz['cv'] = sz['std'] / sz['mean']
sz_candidates = sz[(sz['cv'] < 0.05) & (sz['count'] > 30)]
```

### Phase 4 — RITA との連携

`activecountermeasures/rita` は Zeek log を import し beacon score / DGA / longhttp connection を出す:

```bash
rita import -i ~/zeek/logs/2024-01-15
rita show-beacons --human-readable mydataset
```

### Phase 5 — 既知 beacon family の同定

```
- Cobalt Strike: sleep + jitter, GET URI 固定, default 60s
- Sliver: 多 protocol、profile 依存
- Empire: PowerShell IEX
- Metasploit: HTTP/HTTPS payload stage
- Mythic: 多 profile
```

config 抽出 (→ `reverse-engineering`) と pair で family identify。

### Phase 6 — ノイズ除去

```
- monitoring agent (Datadog / NewRelic) の heartbeat
- antivirus update check
- NTP / time sync
- cloud SDK (AWS heartbeat, GCP metadata)
- corporate proxy / SaaS keepalive
```

これらを allowlist に登録。

### Phase 7 — レポート / IOC

```
- 検出 (src, dst, dport) と 周期 / jitter
- 推定 family / config
- 関連 host
- 推奨 (FW block / TI feed / process audit)
- detection rule (Sigma / Zeek script)
```

## Tools

```
zeek + zeek-cut
RITA
pandas / numpy / scipy.fft (周期検出)
WebFetch
Bash (sandbox)
```

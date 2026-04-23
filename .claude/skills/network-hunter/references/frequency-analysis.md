
# Beaconing Detection via Frequency Analysis

`network-hunter` から呼ばれる variant 別 deep dive

## When to Use

- 既存 SIEM / Zeek / Splunk に beacon 検出 rule を運用
- 一定周期 (jitter ありでも) の outbound を抽出
- 高 noise 環境での hunting (周波数 domain で抽出)

**使わない場面**: 単発 pcap で目視確認 (→ `network-analyzer`)、Zeek 直接利用 (→ `network-hunter`)。

## Approach / Workflow

### Phase 1 — flow 抽出

source 別:

```
zeek conn.log               1 行 = 1 connection
NetFlow / IPFIX             集約 flow
firewall log                allow / deny event
proxy log                   HTTP/HTTPS 1 行 = 1 request
SIEM (splunk index=*)
```

抽出 column: `timestamp / src / dst / dport / bytes`。`(src, dst, dport)` を 1 candidate と扱う。

### Phase 2 — inter-arrival distribution

```python
import pandas as pd, numpy as np
df = pd.read_csv('flows.tsv', sep='\t')
g = df.groupby(['src','dst','dport'])
def cv(s):
    d = s.diff().dt.total_seconds().dropna()
    if len(d) < 10 or d.mean() == 0: return np.nan
    return d.std() / d.mean()
stats = g['ts'].apply(cv).reset_index(name='cv')
candidates = stats[stats['cv'] < 0.3]
```

CV (coefficient of variation) < 0.3 で連続 30+ 回は beacon 候補。

### Phase 3 — Autocorrelation

連続 inter-arrival 列の autocorrelation:

```python
def autocorr(arr, lag=1):
    arr = np.array(arr)
    arr = arr - arr.mean()
    n = len(arr)
    return (arr[:-lag] * arr[lag:]).sum() / (arr * arr).sum()
```

lag=1 が高い → 周期性。

### Phase 4 — FFT

```python
import scipy.fft as fft
inter = df.groupby(['src','dst'])['ts'].apply(lambda s: s.diff().dt.total_seconds().dropna().values)
for key, arr in inter.items():
    if len(arr) < 50: continue
    spec = np.abs(fft.rfft(arr - arr.mean()))
    peak = np.argmax(spec[1:]) + 1
    freq = peak / len(arr)
    period_s = 1 / freq if freq > 0 else None
    if period_s and 30 < period_s < 3600:
        print(key, period_s, spec[peak])
```

dominant peak の周期が 30-3600 秒なら beacon 候補。

### Phase 5 — payload size の一貫性

```python
size_cv = df.groupby(['src','dst','dport'])['orig_bytes'].agg(lambda s: s.std() / s.mean() if s.mean() else np.nan)
size_candidates = size_cv[size_cv < 0.05]
```

### Phase 6 — false positive 除外

```
- monitoring (Datadog / NR / Splunk forwarder)
- AV / EDR heartbeat
- NTP
- cloud SDK metadata
- DNS resolver background
- mail server queue
```

allowlist DB を社内で管理。

### Phase 7 — クロス相関 (host 同期)

複数 host が同 dst に同 timing で接続 → 大規模 botnet / 共通 C2:

```python
g = df.groupby('dst')
for dst, sub in g:
    n_src = sub['src'].nunique()
    if n_src > 5:
        print(dst, n_src)
```

### Phase 8 — レポート / detection rule

```
- 検出 candidate (src / dst / dport / period / size)
- 既存 allowlist との照合
- 推定 C2 family (config が抽出できれば)
- 推奨対応
- detection rule (Sigma / Zeek script / Splunk SPL)
```

## Tools

```
pandas / numpy / scipy.fft / scipy.signal
RITA (補助)
zeek / netflow / Splunk / Elastic
WebFetch
Bash (sandbox)
```

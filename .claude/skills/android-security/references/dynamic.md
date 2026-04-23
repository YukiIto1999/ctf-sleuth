
# Android Dynamic Analysis

`android-security` から呼ばれる variant 別 deep dive

## When to Use

- runtime にしか見えない logic / 暗号 routine の hook
- TLS pinning / jailbreak detection の精密 bypass
- SAST で見えない obfuscation / 難読化 への対応
- network traffic の interception

**使わない場面**: 静的検査のみ (→ `android-security`、`android-security`)、攻撃する Intent IPC (→ `android-security`)。

## Approach / Workflow

### Phase 1 — 環境

```
- Android emulator (Android Studio AVD / Genymotion / Corellium / Bluestacks 系)
- 物理 device (rooted) を engagement で許可済の場合
- frida-server を device に push
- Burp / mitmproxy を host で起動 + cert を device に install
```

```bash
adb push frida-server /data/local/tmp/
adb shell "chmod 755 /data/local/tmp/frida-server && /data/local/tmp/frida-server &"
frida-ps -U
```

### Phase 2 — Objection

baseline observability:

```bash
objection -g <package> explore
> android keystore list
> android sslpinning disable
> android root disable
> android hooking list classes
> android hooking watch class <name>
> android hooking watch class_method '<class>:<method>'
> android intent launch_activity <activity>
> android intent launch_service <service>
> android shell_exec
> environment
> file ls /data/data/<package>/
> file download <path> <local>
```

### Phase 3 — Frida script で hook

```js
Java.perform(function() {
    var Login = Java.use('com.example.LoginActivity');
    Login.doLogin.implementation = function(user, pass) {
        console.log('login', user, pass);
        return this.doLogin(user, pass);
    };
});
```

method 引数 / return / instance state を log。`Java.choose` で 既存 instance を hook。

### Phase 4 — TLS pinning bypass

```bash
objection -g <package> explore
> android sslpinning disable
```

または手動 Frida script:

```js
// SSLContext / TrustManager を override で全 cert accept
```

`androidssl-bypass.js` 等 既存 script があるが、custom pinning (TrustKit / OkHttp CertificatePinner / NetworkSecurityConfig) は version 別に対処。

### Phase 5 — Burp / mitmproxy 経由 traffic

```
device proxy → host:8080
device に Burp CA を install (Settings → Security → Install from storage)
Android 7+ は network_security_config で user CA 不信任 → root 化 + system CA 配置
```

API endpoint / 認証 header / token 寿命を観察。`web-pentester` / `api-security` で深掘り。

### Phase 6 — drozer (IPC + injection)

```bash
drozer console connect
> run app.activity.start --component <package> <activity> --extra string foo bar
> run app.broadcast.send --action <action> --extra string foo bar
> run scanner.provider.injection -a <package>          # SQLi
> run scanner.provider.traversal -a <package>          # path traversal
> run app.provider.read content://<authority>/<path>
> run app.provider.update content://<authority>/<path> --selection ... --string col val
```

`android-security` の手順を併用。

### Phase 7 — native code

```
- JNI 経由の関数を Module.findExportByName で hook
- Stalker で instruction 単位 trace
- Process.findRangeByAddress で memory map
- libc / libssl の関数 (open / read / SSL_read) を hook
```

```js
Interceptor.attach(Module.findExportByName('libnative.so', 'do_decrypt'), {
    onEnter: function(args) { ... },
    onLeave: function(retval) { ... }
});
```

### Phase 8 — レポート

```
- 観察した sensitive call (login / payment / 暗号)
- 抽出した token / key / API URL (redact)
- bypass した防御 (pinning / root detection)
- runtime hook で見えた obfuscated 文字列
- 推奨 (RASP / 強い pinning / native protection)
```

## Tools

```
frida / frida-tools
objection
drozer
adb
Burp / mitmproxy
WebFetch
Bash (sandbox)
```


# iOS App Reversing with Frida

`ios-security` から呼ばれる variant 別 deep dive

## When to Use

- iOS アプリの method 呼出しを runtime hook して挙動を捕捉
- 暗号 key / TLS cert / API token の動的抽出
- jailbreak / TLS pinning bypass の精密制御
- objection の標準コマンドで足りない複雑 hook

**使わない場面**: Objection 標準コマンドで完結 (→ `ios-security`)、static Mach-O 解析のみ (→ `reverse-engineering`)。

## Approach / Workflow

### Phase 1 — 環境

```
- jailbroken device / Corellium emulator
- frida-server を device に install
- ホスト: pip install frida-tools
```

```bash
frida-ls-devices
frida-ps -U
frida-trace -U -i 'open' -i 'CCCryptorCreate' -n MyApp
```

### Phase 2 — クラス / method 列挙

```js
// Frida REPL
ObjC.classes.NSString
Object.keys(ObjC.classes).filter(n => n.includes('Login'))
ObjC.classes.AppLoginViewController.$ownMethods

// Swift / class-dump 系
Process.enumerateModules()
Module.enumerateExports('MyApp')
```

class-dump (`class-dump-z`) で 静的 Mach-O から ObjC class info を取得し、hook 対象を特定。

### Phase 3 — method hook

```js
var Login = ObjC.classes.AppLoginViewController;
Interceptor.attach(Login['- loginWithUser:password:'].implementation, {
    onEnter: function(args) {
        var user = ObjC.Object(args[2]).toString();
        var pass = ObjC.Object(args[3]).toString();
        console.log('login', user, pass);
    },
    onLeave: function(retval) {
        console.log('return', retval);
    }
});
```

Swift method は demangled name を使う:

```js
Module.findExportByName('MyApp', '$s5MyApp14LoginViewModelC5loginyyF')
```

Swift mangled symbol は `swift demangle` で読みやすく。

### Phase 4 — 暗号 key / token 抽出

```js
// CommonCrypto を hook
Interceptor.attach(Module.findExportByName(null, 'CCCrypt'), {
    onEnter: function(args) {
        // op, alg, options, key, keyLen, iv, dataIn, dataInLen, dataOut, dataOutAvail, dataOutMoved
        var key = Memory.readByteArray(args[3], parseInt(args[4]));
        console.log('CCCrypt key:', hexdump(key));
    }
});
```

特定 method の input/output から key / IV / plaintext を log。

### Phase 5 — jailbreak / pinning bypass

```js
// jailbreak detection: -[Foo isJailbroken] を false にする
var Foo = ObjC.classes.JailbreakDetector;
Foo['- isJailbroken'].implementation = ObjC.implement(Foo['- isJailbroken'], function() { return 0; });

// TLS pinning (NSURLSession): challenge を成功扱いにする
var URLSession = ObjC.classes.NSURLSession;
// 詳細は SecTrustEvaluate hook で trust = kSecTrustResultProceed
```

`frida-ios-jailbreak-bypass.js`、`frida-ios-ssl-bypass.js` 系の公開 script もあるが、自前で fingerprint を読み解いて hook を組むほうが detection が更新されたとき安定する。

### Phase 6 — file / network monitoring

```js
Interceptor.attach(Module.findExportByName(null, 'open'), {
    onEnter: function(args) {
        console.log('open', Memory.readUtf8String(args[0]));
    }
});

Interceptor.attach(Module.findExportByName(null, 'connect'), {
    onEnter: function(args) {
        // sockaddr 解析
    }
});
```

### Phase 7 — Stalker (instruction-level trace)

```js
Stalker.follow(Process.getCurrentThreadId(), {
    events: { call: true, ret: false },
    onCallSummary: function(summary) {
        console.log(JSON.stringify(summary));
    }
});
```

重要部のみ trace し log を絞る (全 instruction trace は重い)。

### Phase 8 — レポート / IOC

```
- bundle-id / version
- 抽出した暗号 key / IV / API token (redact)
- bypass した detection 関数
- 観察した sensitive 操作 (login, payment, credentials handling)
- 推奨 (key の secure enclave 活用 / runtime integrity check 強化)
```

## Tools

```
frida / frida-tools / frida-trace
class-dump-z
Hopper / Ghidra (補助 static)
mitmproxy / Burp (TLS pin 解除後)
WebFetch
Bash (sandbox)
```

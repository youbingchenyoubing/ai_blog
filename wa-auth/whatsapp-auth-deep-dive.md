# 深度解析 WhatsApp Web 授权机制：从协议分析到配对码服务实现

> 本文从逆向分析一个真实 WhatsApp 授权凭据入手，深入剖析 WhatsApp Web 多设备协议的认证机制，并基于 Baileys 开源库完整实现一个配对码授权服务。

---

## 一、从一个真实凭据说起

某网站 `aflo.top` 在用户完成 WhatsApp 授权后，服务端拿到了这样一份数据：

```json
{
  "Phone": "5927342668",
  "noiseKey": {
    "public": {"type":"Buffer","data":"s2WFvEWCC+oVAzniutlrswb4DSl2d6OwP4GhHJVdl0o="},
    "private": {"type":"Buffer","data":"+EAFoftQzemFbPvZKCK6q9hlgGYO3VQwSL56eUBJn3s="}
  },
  "signedIdentityKey": {
    "public": {"type":"Buffer","data":"Q+1U1cP723z05HfNhXU1y5xEcoFgnqI7snv2Qgcu20Y="},
    "private": {"type":"Buffer","data":"kAe9EMPcAgPHUvyV7XAjL33wLvWFJHIp/Pm6rggzzEU="}
  },
  "signedPreKey": {
    "keyId": 1,
    "signature": "EVvKwvCRrSwRvEps09DErxZRAdrLxf0cib6rgeuWG7kBqlbRxwzwDgVj0F8gaiykomXxUQuO1D0RoThrj4rGAg==",
    "keyPair": {
      "public": {"type":"Buffer","data":"O9XUvxvBKBYuXAa2VnrMGTYPdpRrLs1UPrBz1Nm9oFc="},
      "private": {"type":"Buffer","data":"aAvEMoXG373iINsG3BQz1BOpY3iP5Rr84IIfb1eBi2I="}
    }
  },
  "registrationId": 3537321937,
  "advSecretKey": "lD9HSmv7hdtAyyXq8svhtRWEJuF2FhEhhXJsB2tGFtc=",
  "me": {
    "id": "5927342668:4@s.whatsapp.net",
    "lid": "250504554774755:4@lid",
    "name": ""
  },
  "account": {
    "details": "CLu3msoBEMjFltEGGAEgACgA",
    "accountSignatureKey": "6QvzyA7/5aCuARwPHDGueqhOsa0NbCKxKn3UnTJpuQI=",
    "accountSignature": "TqrytN8KFFMTSj9ehjWf46KiYPN2qKNx77Xros84viBQKfPkRMrYTo9SstOOqYhVxeKoWOQDZ3/YMHs+ShScAA==",
    "deviceSignature": "wKcWi5neoswySXC8d9mQxGJiCmFSi8Zr8fe7gjSwz+rjzRwt+mSlYrNo87GnfdYvzxH8tT70PXnBmOaZiac1CA=="
  },
  "platform": "android",
  "registered": true,
  "signalIdentities": {
    "identifier": {"name":"5927342668:4@s.whatsapp.net","deviceId":4},
    "identifierKey": {"type":"Buffer","data":"BUPtVNXD+9t89OR3zYV1NcucRHKBYJ6iO7J79kIHLttG"}
  }
}
```

这份数据看起来密密麻麻，但它实际上就是 **@whiskeysockets/baileys** 库的 `AuthenticationCreds` 对象——WhatsApp Web 多设备协议的完整认证凭据。

接下来，我们逐字段拆解，然后从零实现一个完整的授权服务。

---

## 二、凭据字段深度解析

### 2.1 传输层：Noise Protocol 握手密钥

```
noiseKey.public  → Curve25519 公钥
noiseKey.private → Curve25519 私钥
```

WhatsApp Web 使用 **Noise_XX_25519_AESGCM_SHA256** 协议建立 WebSocket 加密通道。`noiseKey` 是客户端在握手阶段使用的临时密钥对：

- `Noise_XX` 模式意味着双方都要发送公钥（双向认证）
- 握手完成后，所有 WebSocket 通信都通过 AES-GCM 加密
- 这层加密位于 TLS 之上，形成双层加密

### 2.2 身份层：Signal 协议密钥

```
signedIdentityKey  → 长期身份密钥（Identity Key）
signedPreKey       → 签名预密钥（Signed Pre-Key），由 Identity Key 签名
```

WhatsApp 使用 Signal 协议进行端到端加密。当另一个设备要与此设备建立加密会话时，使用 **X3DH（Extended Triple Diffie-Hellman）** 密钥协商协议：

```
DH1 = DH(IK_A, SPK_B)     // 发送方身份密钥 × 接收方签名预密钥
DH2 = DH(EK_A, IK_B)     // 发送方临时密钥 × 接收方身份密钥
DH3 = DH(EK_A, SPK_B)    // 发送方临时密钥 × 接收方签名预密钥
DH4 = DH(EK_A, OPK_B)    // 发送方临时密钥 × 接收方一次性预密钥

共享密钥 = DH1 || DH2 || DH3 || DH4
```

`signedPreKey` 的 `signature` 字段就是用 `signedIdentityKey.private` 对 `signedPreKey.public` 的签名，防止中间人替换预密钥。

### 2.3 设备标识：JID 与设备ID

```
me.id  = "5927342668:4@s.whatsapp.net"
me.lid = "250504554774755:4@lid"
```

- **JID（Jabber ID）** 是 WhatsApp 的用户标识，格式为 `手机号:设备ID@域名`
- `:4` 表示这是第4个已链接设备（WhatsApp 允许手机 + 最多4个辅助设备）
- `@s.whatsapp.net` 是标准用户域，`@lid` 是链接设备的内部标识

### 2.4 签名链：三层签名验证

```
account.accountSignatureKey → 账户级公钥
account.accountSignature    → 用账户私钥签名（证明账户所有权）
account.deviceSignature     → 用设备私钥签名（证明设备所有权）
```

WhatsApp 服务器通过验证这条签名链来确认设备的合法性：

```
账户私钥 ──签名──→ accountSignature     （证明"我是这个账户"）
设备私钥 ──签名──→ deviceSignature      （证明"我是这个设备"）
账户公钥 ──验证──→ accountSignatureKey  （服务器可验证）
```

### 2.5 其他字段

| 字段 | 说明 |
|------|------|
| `registrationId` | 32位注册ID，标识设备在 WhatsApp 服务器上的注册 |
| `advSecretKey` | Authenticated Device Verification 密钥，用于设备间验证 |
| `pairingEphemeralKeyPair` | 配对码流程的一次性临时密钥对 |
| `routingInfo` | WhatsApp 服务器路由信息（protobuf 编码） |
| `signalIdentities` | Signal 协议身份绑定（JID + 身份公钥） |
| `platform` | 伪装平台标识 |

---

## 三、WhatsApp Web 授权流程

WhatsApp 多设备协议提供两种授权方式，本质上都是"链接辅助设备"：

### 3.1 二维码模式

```
用户浏览器          服务端 (Baileys)          WhatsApp 服务器
    │                     │                        │
    │  1.请求二维码        │                        │
    │────────────────────>│                        │
    │                     │  2.makeWASocket()      │
    │                     │  3.Noise握手           │
    │                     │───────────────────────>│
    │                     │  4.返回QR码数据         │
    │                     │<───────────────────────│
    │  5.返回QR码         │                        │
    │<────────────────────│                        │
    │                     │                        │
    │  6.用户用手机扫码    │                        │
    │══════════════════════════════════════════════>│
    │                     │  7.配对成功通知         │
    │                     │<───────────────────────│
    │                     │  8.creds.update 事件   │
    │                     │  9.saveCreds() 保存凭据 │
    │  10.查询状态=connected│                       │
    │<────────────────────│                        │
```

### 3.2 配对码模式

配对码模式是二维码的替代方案，适合无头（headless）环境：

```
用户浏览器          服务端 (Baileys)          WhatsApp 服务器
    │                     │                        │
    │  1.提交手机号        │                        │
    │────────────────────>│                        │
    │                     │  2.makeWASocket()      │
    │                     │  3.Noise握手           │
    │                     │───────────────────────>│
    │                     │  4.requestPairingCode()│
    │                     │───────────────────────>│
    │                     │  5.返回8位配对码        │
    │                     │<───────────────────────│
    │  6.显示配对码        │                        │
    │<────────────────────│                        │
    │                     │                        │
    │  7.用户在手机WhatsApp│                        │
    │    输入配对码        │                        │
    │══════════════════════════════════════════════>│
    │                     │  8.配对成功通知         │
    │                     │<───────────────────────│
    │                     │  9.creds.update 事件   │
    │                     │  10.saveCreds() 保存   │
    │  11.查询状态=connected│                       │
    │<────────────────────│                        │
```

**关键区别**：二维码模式中 QR 码包含 `noiseKey.public`，手机扫描后直接建立链接；配对码模式中，用户手动输入8位码，WhatsApp 服务器验证后完成链接。

---

## 四、从零实现配对码授权服务

### 4.1 项目结构

```
wa-auth/
├── server.js                  # Express REST API 服务
├── lib/
│   ├── wa-auth.js             # WhatsApp 授权核心模块
│   └── credential-store.js    # 凭据存储管理
├── sessions/                  # 会话凭据存储目录（自动创建）
└── package.json
```

### 4.2 核心依赖

```json
{
  "dependencies": {
    "@whiskeysockets/baileys": "^6.7.8",
    "express": "^4.21.0",
    "pino": "^9.5.0",
    "qrcode-terminal": "^0.12.0"
  }
}
```

- **@whiskeysockets/baileys** — WhatsApp Web 协议的 TypeScript 实现，无需浏览器即可直接通过 WebSocket 与 WhatsApp 服务器通信
- **express** — REST API 框架
- **pino** — Baileys 内部使用的日志库
- **qrcode-terminal** — 终端二维码显示

### 4.3 凭据存储模块

WhatsApp 的凭据中包含大量 `Buffer` 对象（密钥、签名等），无法直接 `JSON.stringify`。我们需要一个序列化层：

```javascript
// lib/credential-store.js

const fs = require('fs')
const path = require('path')

const CREDENTIALS_DIR = path.join(__dirname, '..', 'sessions')

/**
 * Buffer 序列化：递归遍历对象，将 Buffer 转为 base64 编码的 JSON 描述
 * { type: 'Buffer', data: 'base64string' }
 */
function serializeBuffers(obj) {
  if (obj === null || obj === undefined) return obj
  if (Buffer.isBuffer(obj)) {
    return { type: 'Buffer', data: obj.toString('base64') }
  }
  if (Array.isArray(obj)) {
    return obj.map(serializeBuffers)
  }
  if (typeof obj === 'object') {
    const result = {}
    for (const key of Object.keys(obj)) {
      result[key] = serializeBuffers(obj[key])
    }
    return result
  }
  return obj
}

/**
 * Buffer 反序列化：将 JSON 中的 Buffer 描述还原为 Buffer 实例
 */
function deserializeBuffers(obj) {
  if (obj === null || obj === undefined) return obj
  if (Array.isArray(obj)) {
    return obj.map(deserializeBuffers)
  }
  if (typeof obj === 'object') {
    if (obj.type === 'Buffer' && typeof obj.data === 'string') {
      return Buffer.from(obj.data, 'base64')
    }
    const result = {}
    for (const key of Object.keys(obj)) {
      result[key] = deserializeBuffers(obj[key])
    }
    return result
  }
  return obj
}

/**
 * 保存凭据到文件
 */
function saveCredentials(sessionId, creds) {
  const dir = getSessionDir(sessionId)
  const filePath = path.join(dir, 'creds.json')
  const serialized = serializeBuffers(creds)
  fs.writeFileSync(filePath, JSON.stringify(serialized, null, 2), 'utf-8')
  return filePath
}

/**
 * 读取凭据文件
 */
function loadCredentials(sessionId) {
  const filePath = path.join(getSessionDir(sessionId), 'creds.json')
  if (!fs.existsSync(filePath)) return null
  const raw = JSON.parse(fs.readFileSync(filePath, 'utf-8'))
  return deserializeBuffers(raw)
}
```

**设计要点**：

1. **递归序列化** — 凭据是深层嵌套对象，密钥可能出现在任意层级，必须递归处理
2. **base64 编码** — Buffer 的二进制数据用 base64 编码为字符串，保证 JSON 兼容
3. **双向转换** — 序列化和反序列化必须可逆，保证恢复会话时凭据完整还原

### 4.4 WhatsApp 授权核心模块

这是整个服务的核心，封装了 Baileys 的连接、配对码请求、状态管理等逻辑：

```javascript
// lib/wa-auth.js

const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
  Browsers
} = require('@whiskeysockets/baileys')
const P = require('pino')
const credentialStore = require('./credential-store')

const sessions = new Map()

async function createConnection(options) {
  const {
    sessionId,
    phoneNumber,
    usePairingCode = true,
    platform = 'android',
    onQrCode,
    onPairingCode,
    onConnected,
    onDisconnected
  } = options

  // 获取最新 WhatsApp Web 版本号
  const { version } = await fetchLatestBaileysVersion()

  // 使用多文件认证状态（Baileys 内置的凭据管理）
  const authDir = path.join(credentialStore.CREDENTIALS_DIR, sessionId)
  const { state, saveCreds } = await useMultiFileAuthState(authDir)

  // 创建 WhatsApp Socket
  const sock = makeWASocket({
    version,
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, P({ level: 'silent' }))
    },
    printQRInTerminal: false,
    browser: Browsers.ubuntu('Chrome'),  // 伪装为 Ubuntu Chrome
    logger: P({ level: 'silent' }),
    connectTimeoutMs: 60_000,
    keepAliveIntervalMs: 25_000,
    markOnlineOnConnect: false,
  })

  // 关键：凭据更新时自动保存
  sock.ev.on('creds.update', saveCreds)

  // 连接状态处理
  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update

    // 配对码模式：当 QR 数据到达时请求配对码
    if (qr && usePairingCode && !sock.authState.creds.registered) {
      const code = await sock.requestPairingCode(phoneNumber)
      // code 是8位配对码，如 "A1B2-C3D4"
      if (onPairingCode) onPairingCode(code)
    }

    // 连接成功
    if (connection === 'open') {
      credentialStore.saveCredentials(sessionId, sock.authState.creds)
      if (onConnected) {
        onConnected(credentialStore.serializeBuffers(sock.authState.creds))
      }
    }

    // 连接断开
    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut
      if (!shouldReconnect) {
        sessions.delete(sessionId)
        credentialStore.deleteCredentials(sessionId)
      }
    }
  })
}
```

**关键设计决策**：

1. **`fetchLatestBaileysVersion()`** — WhatsApp 会定期更新协议版本，必须获取最新版本号否则连接会被拒绝
2. **`makeCacheableSignalKeyStore()`** — Signal 协议密钥的缓存层，避免每次操作都读写磁盘
3. **`creds.update` 事件** — 这是凭据保存的触发点，Baileys 在密钥轮换、会话更新时都会触发此事件
4. **`requestPairingCode()` 的时机** — 必须在 QR 数据到达后、且 `creds.registered === false` 时调用，否则会报错

### 4.5 REST API 服务

将核心模块封装为 HTTP 接口，方便前端集成：

```javascript
// server.js

const express = require('express')
const waAuth = require('./lib/wa-auth')
const credentialStore = require('./lib/credential-store')

const app = express()
app.use(express.json())

// 配对码授权
app.post('/api/auth/pairing-code', async (req, res) => {
  const { phoneNumber, sessionId, platform } = req.body
  const cleanPhone = phoneNumber.replace(/[\+\-\(\)\s]/g, '')
  const sid = sessionId || `wa_${cleanPhone}_${Date.now()}`

  const result = await waAuth.createConnection({
    sessionId: sid,
    phoneNumber: cleanPhone,
    usePairingCode: true,
    platform: platform || 'android',
    onPairingCode: (code) => console.log(`配对码: ${code}`),
    onConnected: (creds) => console.log(`已连接: ${creds.me?.id}`),
    onDisconnected: (info) => console.log(`已断开: ${info.reason}`),
  })

  res.json({
    success: true,
    sessionId: sid,
    pairingCode: result.pairingCode,
    message: result.pairingCode
      ? `请在 WhatsApp 中输入配对码: ${result.pairingCode}`
      : '正在生成配对码，请稍后查询状态'
  })
})

// 查询授权状态
app.get('/api/auth/status/:sessionId', (req, res) => {
  const info = waAuth.getSessionInfo(req.params.sessionId)
  if (!info) return res.status(404).json({ error: '会话不存在' })
  res.json(info)
})

// 获取完整凭据
app.get('/api/auth/credentials/:sessionId', (req, res) => {
  const creds = waAuth.getSessionCredentials(req.params.sessionId)
  if (!creds) return res.status(404).json({ error: '凭据不存在' })
  res.json(creds)
})

app.listen(3000)
```

---

## 五、完整 API 接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/pairing-code` | 配对码授权，传入手机号获取8位配对码 |
| POST | `/api/auth/qr-code` | 二维码授权，返回 QR 码数据 |
| GET | `/api/auth/status/:id` | 查询授权状态（connecting/pairing_code_ready/connected 等） |
| GET | `/api/auth/credentials/:id` | 获取完整凭据 JSON |
| GET | `/api/auth/sessions` | 列出所有活跃和已保存的会话 |
| DELETE | `/api/auth/session/:id` | 断开并删除会话 |
| POST | `/api/auth/restore/:id` | 使用已保存凭据恢复连接 |
| POST | `/api/message/send/:id` | 授权成功后发送消息 |

---

## 六、前端集成

### 6.1 为什么不能纯前端？

Baileys 依赖 Node.js 原生模块，**无法直接在浏览器中运行**：

| 依赖 | 浏览器是否支持 |
|------|--------------|
| `net` 模块（自定义 WebSocket） | 不支持 |
| `fs` 模块（凭据文件读写） | 不支持 |
| `crypto` 原生加密 | 部分支持，但 API 不同 |
| 自定义 WebSocket Headers | 浏览器 WebSocket API 不支持 |

因此必须采用**前后端分离**架构：

```
┌──────────────────────┐       HTTP        ┌──────────────────────┐       WebSocket       ┌─────────────┐
│   前端 (浏览器)        │ ──────────────→  │  后端 (Node.js)       │ ──────────────────→  │  WhatsApp    │
│   展示配对码/二维码    │  ←────────────── │  Baileys 协议处理     │  ←──────────────────  │  服务器       │
│   轮询授权状态         │    JSON 响应      │  凭据存储管理         │    二进制消息          │             │
└──────────────────────┘                   └──────────────────────┘                       └─────────────┘
```

### 6.2 前端页面实现

项目已内置完整的前端页面（`public/index.html`），采用 WhatsApp 官方深色主题风格，包含三个标签页：

**配对码页面**：
- 输入手机号 → 获取8位配对码 → 显示操作步骤 → 自动轮询状态 → 授权成功

**二维码页面**：
- 点击生成 → 渲染 QR 码（使用 qrcode.js）→ 自动轮询 → 授权成功

**会话管理页面**：
- 列出所有活跃/已保存会话 → 恢复/断开/删除 → 查看完整凭据 JSON

前端核心逻辑：

```javascript
// 1. 请求配对码
async function requestPairingCode() {
  const data = await fetch('/api/auth/pairing-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phoneNumber: '5927342668', platform: 'android' })
  }).then(r => r.json())

  // 显示配对码，如 "A1B2-C3D4"
  showPairingCode(data.pairingCode)
  startPolling()
}

// 2. 每3秒轮询状态
function startPolling() {
  setInterval(async () => {
    const info = await fetch(`/api/auth/status/${sessionId}`).then(r => r.json())
    if (info.status === 'connected') {
      // 授权成功，显示凭据获取按钮
      showSuccess(info.me.id)
    }
  }, 3000)
}

// 3. 获取凭据
async function fetchCredentials() {
  const creds = await fetch(`/api/auth/credentials/${sessionId}`).then(r => r.json())
  // creds 就是完整的 AuthenticationCreds 对象
  displayCredentials(creds)
}
```

### 6.3 集成到现有前端项目

如果要在 React/Vue 项目中集成，只需调用后端 API：

```javascript
// React Hook 示例
function useWhatsAppAuth() {
  const [state, setState] = useState({ status: 'idle', pairingCode: null, credentials: null })
  const sessionIdRef = useRef(null)

  const requestCode = async (phoneNumber) => {
    const data = await fetch('/api/auth/pairing-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phoneNumber })
    }).then(r => r.json())

    sessionIdRef.current = data.sessionId
    setState({ status: 'waiting', pairingCode: data.pairingCode })
  }

  // 轮询状态
  useEffect(() => {
    if (state.status !== 'waiting') return
    const timer = setInterval(async () => {
      const info = await fetch(`/api/auth/status/${sessionIdRef.current}`).then(r => r.json())
      if (info.status === 'connected') {
        const creds = await fetch(`/api/auth/credentials/${sessionIdRef.current}`).then(r => r.json())
        setState({ status: 'connected', credentials: creds })
      }
    }, 3000)
    return () => clearInterval(timer)
  }, [state.status])

  return { ...state, requestCode }
}
```

### 6.4 跨域部署

如果前后端不在同一域名，需要配置 CORS（后端已内置）：

```javascript
// 后端已配置，无需额外操作
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*')
  res.header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
  if (req.method === 'OPTIONS') return res.sendStatus(200)
  next()
})
```

前端只需修改 `API_BASE`：

```javascript
const API_BASE = 'https://your-wa-auth-server.com'
```

---

## 七、会话状态机

授权过程中，会话经历以下状态流转：

```
                    ┌─────────────┐
                    │ connecting  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼                         ▼
    ┌──────────────────┐     ┌─────────────────────┐
    │ pairing_code_ready│     │     qr_ready        │
    └────────┬─────────┘     └──────────┬──────────┘
             │                          │
             │   用户输入配对码/扫码      │
             │                          │
             ▼                          ▼
         ┌──────────────────────────────┐
         │         connected            │
         └──────────────┬───────────────┘
                        │
              ┌─────────┼──────────┐
              ▼                    ▼
    ┌───────────────┐    ┌──────────────┐
    │ disconnected  │    │  logged_out  │
    │ (可自动重连)   │    │ (需重新授权)  │
    └───────────────┘    └──────────────┘
```

---

## 八、安全考量

### 8.1 凭据即身份

WhatsApp 的认证凭据包含所有私钥，**拥有凭据 = 拥有账号的完整控制权**。这意味着：

- 可以读取所有聊天消息
- 可以以用户身份发送消息
- 可以获取联系人列表
- 可以持续监控用户活动

### 8.2 生产环境建议

1. **加密存储** — 凭据文件应使用 AES-256 加密，密钥由环境变量管理
2. **API 认证** — 添加 JWT/API Key 中间件，防止未授权调用
3. **HTTPS 部署** — 凭据在传输过程中必须加密
4. **定期轮换** — `signedPreKey` 应定期更新（Baileys 自动处理）
5. **访问日志** — 记录所有凭据访问操作，便于审计

### 8.3 用户风险提示

将 WhatsApp 配对码提供给第三方网站，等同于将 WhatsApp 账号控制权交给对方。在实现此类服务时，必须：

- 明确告知用户授权范围
- 提供随时撤销授权的机制
- 不存储超出业务需要的凭据

---

## 九、总结

本文从一个真实凭据出发，完整剖析了 WhatsApp Web 多设备协议的认证机制：

1. **Noise Protocol** 负责传输层加密（WebSocket 通道）
2. **Signal Protocol** 负责端到端加密（消息加密）
3. **X3DH 密钥协商** 建立加密会话
4. **签名链** 验证设备合法性
5. **配对码/二维码** 是设备链接的两种验证方式

基于 Baileys 的实现将整个流程封装为简洁的 REST API，核心只需三个步骤：

```
请求配对码 → 用户输入 → 获取凭据
```

完整代码见项目 `wa-auth/` 目录，启动方式：

```bash
cd wa-auth && npm install && npm start
```

---

*本文仅供技术研究和学习交流，请遵守 WhatsApp 服务条款，不要将此技术用于骚扰、欺诈或其他违法行为。*

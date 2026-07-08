# WhatsApp 配对码授权服务 - 使用手册

## 概述

本服务基于 `@whiskeysockets/baileys` 实现 WhatsApp Web 多设备协议的授权流程，支持**配对码**和**二维码**两种授权方式，提供 REST API 接口，可轻松集成到任何 Web 应用中。

## 架构说明

```
wa-auth/
├── server.js                  # Express REST API 服务
├── lib/
│   ├── wa-auth.js             # WhatsApp 授权核心模块
│   └── credential-store.js    # 凭据存储管理
├── sessions/                  # 会话凭据存储目录（自动创建）
│   ├── wa_5927342668_xxxx/
│   │   ├── creds.json         # 认证凭据
│   │   └── app-state-sync-key-*.json
│   └── ...
└── package.json
```

## 快速开始

### 1. 安装

```bash
cd wa-auth
npm install
```

### 2. 启动服务

```bash
npm start
# 或开发模式（自动重启）
npm run dev
```

服务默认运行在 `http://localhost:3000`，可通过环境变量 `PORT` 修改。

### 3. 验证服务

```bash
curl http://localhost:3000/
```

---

## API 接口文档

### 1. 请求配对码

通过手机号获取 WhatsApp 配对码，用户在手机 WhatsApp 中输入该配对码完成授权。

**请求**

```
POST /api/auth/pairing-code
Content-Type: application/json
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phoneNumber | string | 是 | 手机号（含国家码，不含+号），如 `5927342668` |
| sessionId | string | 否 | 自定义会话ID，不传则自动生成 |
| platform | string | 否 | 伪装平台：`android`（默认）、`ios`、`web` |

**示例**

```bash
curl -X POST http://localhost:3000/api/auth/pairing-code \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber":"5927342668"}'
```

**响应**

```json
{
  "success": true,
  "sessionId": "wa_5927342668_1717912345678",
  "status": "pairing_code_ready",
  "pairingCode": "A1B2-C3D4",
  "message": "请在 WhatsApp 中输入配对码: A1B2-C3D4"
}
```

**用户操作**

1. 打开手机 WhatsApp
2. 进入 **设置 > 已链接设备 > 链接设备 > 改用手机号码链接**
3. 输入返回的8位配对码

---

### 2. 请求二维码

生成 WhatsApp 二维码，用户用手机扫码完成授权。

**请求**

```
POST /api/auth/qr-code
Content-Type: application/json
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sessionId | string | 否 | 自定义会话ID |
| platform | string | 否 | 伪装平台：`web`（默认）、`android`、`ios` |

**示例**

```bash
curl -X POST http://localhost:3000/api/auth/qr-code \
  -H "Content-Type: application/json" \
  -d '{}'
```

**响应**

```json
{
  "success": true,
  "sessionId": "wa_qr_1717912345678",
  "status": "qr_ready",
  "qrCode": "2@abc123...",
  "message": "请使用 WhatsApp 扫描二维码"
}
```

> `qrCode` 字段为 WhatsApp 原始二维码数据，前端需用 QR 库渲染为图片。

---

### 3. 查询授权状态

**请求**

```
GET /api/auth/status/:sessionId
```

**示例**

```bash
curl http://localhost:3000/api/auth/status/wa_5927342668_1717912345678
```

**响应**

```json
{
  "sessionId": "wa_5927342668_1717912345678",
  "status": "connected",
  "pairingCode": "A1B2-C3D4",
  "phoneNumber": "5927342668",
  "platform": "android",
  "registered": true,
  "me": {
    "id": "5927342668:4@s.whatsapp.net",
    "lid": "250504554774755:4@lid",
    "name": ""
  },
  "createdAt": 1717912345678,
  "connectedAt": 1717912350000
}
```

**状态值说明**

| 状态 | 说明 |
|------|------|
| `connecting` | 正在建立连接 |
| `qr_ready` | 二维码已生成，等待扫描 |
| `pairing_code_ready` | 配对码已生成，等待输入 |
| `pairing_code_error` | 配对码生成失败 |
| `connected` | 已成功连接 |
| `disconnected` | 连接断开（可重连） |
| `logged_out` | 已登出（需重新授权） |

---

### 4. 获取完整凭据

授权成功后获取完整的 WhatsApp 认证凭据，包含所有密钥信息。

**请求**

```
GET /api/auth/credentials/:sessionId
```

**示例**

```bash
curl http://localhost:3000/api/auth/credentials/wa_5927342668_1717912345678
```

**响应**

返回完整的 `AuthenticationCreds` 对象，结构如下：

```json
{
  "Phone": "5927342668",
  "noiseKey": {
    "public": { "type": "Buffer", "data": "s2WFvEWCC+oVAzniutlrswb4DSl2d6OwP4GhHJVdl0o=" },
    "private": { "type": "Buffer", "data": "+EAFoftQzemFbPvZKCK6q9hlgGYO3VQwSL56eUBJn3s=" }
  },
  "signedIdentityKey": {
    "public": { "type": "Buffer", "data": "Q+1U1cP723z05HfNhXU1y5xEcoFgnqI7snv2Qgcu20Y=" },
    "private": { "type": "Buffer", "data": "kAe9EMPcAgPHUvyV7XAjL33wLvWFJHIp/Pm6rggzzEU=" }
  },
  "signedPreKey": {
    "keyId": 1,
    "signature": "EVvKwvCRrSwRvEps09DErxZRAdrLxf0cib6rgeuWG7kBqlbRxwzwDgVj0F8gaiykomXxUQuO1D0RoThrj4rGAg==",
    "keyPair": {
      "public": { "type": "Buffer", "data": "O9XUvxvBKBYuXAa2VnrMGTYPdpRrLs1UPrBz1Nm9oFc=" },
      "private": { "type": "Buffer", "data": "aAvEMoXG373iINsG3BQz1BOpY3iP5Rr84IIfb1eBi2I=" }
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
    "identifier": {
      "name": "5927342668:4@s.whatsapp.net",
      "deviceId": 4
    },
    "identifierKey": {
      "type": "Buffer",
      "data": "BUPtVNXD+9t89OR3zYV1NcucRHKBYJ6iO7J79kIHLttG"
    }
  }
}
```

---

### 5. 列出所有会话

**请求**

```
GET /api/auth/sessions
```

**响应**

```json
{
  "active": [
    {
      "sessionId": "wa_5927342668_xxxx",
      "status": "connected",
      "registered": true,
      "me": { "id": "5927342668:4@s.whatsapp.net" }
    }
  ],
  "saved": ["wa_5927342668_xxxx", "wa_1234567890_yyyy"]
}
```

---

### 6. 断开并删除会话

**请求**

```
DELETE /api/auth/session/:sessionId?deleteCredentials=true
```

**参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| deleteCredentials | query | 是否同时删除保存的凭据文件，默认 `false` |

---

### 7. 恢复已保存的会话

使用之前保存的凭据重新建立连接，无需再次配对。

**请求**

```
POST /api/auth/restore/:sessionId
```

**示例**

```bash
curl -X POST http://localhost:3000/api/auth/restore/wa_5927342668_1717912345678
```

---

### 8. 发送消息

授权成功后，可代替用户发送消息。

**请求**

```
POST /api/message/send/:sessionId
Content-Type: application/json
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| jid | string | 是 | 接收者 JID，如 `5927342668@s.whatsapp.net` |
| text | string | 否 | 文本消息内容 |
| image | object | 否 | 图片消息 `{data: base64, caption: string}` |
| document | object | 否 | 文件消息 `{data: base64, fileName: string, mimetype: string}` |

**示例 - 发送文本**

```bash
curl -X POST http://localhost:3000/api/message/send/wa_5927342668_xxxx \
  -H "Content-Type: application/json" \
  -d '{"jid":"5927342668@s.whatsapp.net","text":"Hello from WA-Auth!"}'
```

---

## 凭据字段详解

| 字段 | 说明 |
|------|------|
| `noiseKey` | Noise Protocol 握手密钥对，用于 WebSocket 加密通道建立 |
| `signedIdentityKey` | Signal 协议身份密钥，代表设备长期身份 |
| `signedPreKey` | 签名预密钥，由身份密钥签名，用于 X3DH 密钥协商 |
| `registrationId` | WhatsApp 服务器上的注册标识 |
| `advSecretKey` | Authenticated Device Verification 密钥 |
| `me.id` | JID 格式 `手机号:设备ID@s.whatsapp.net`，设备ID 表示链接设备序号 |
| `me.lid` | Linked ID，WhatsApp 内部链接设备标识 |
| `account.details` | 账户详情 protobuf（Base64） |
| `account.accountSignatureKey` | 账户签名公钥 |
| `account.accountSignature` | 账户签名（证明账户所有权） |
| `account.deviceSignature` | 设备签名（证明设备所有权） |
| `pairingEphemeralKeyPair` | 配对码流程的临时密钥对 |
| `routingInfo` | WhatsApp 服务器路由信息 |
| `signalIdentities` | Signal 协议身份绑定（JID + 身份公钥） |

---

## 授权流程图

### 配对码模式

```
客户端                    服务端                    WhatsApp
  │                        │                        │
  │ POST /pairing-code     │                        │
  │ {phoneNumber}          │                        │
  │───────────────────────>│                        │
  │                        │  makeWASocket()        │
  │                        │  requestPairingCode()  │
  │                        │───────────────────────>│
  │                        │   返回8位配对码          │
  │                        │<───────────────────────│
  │  返回 pairingCode      │                        │
  │<───────────────────────│                        │
  │                        │                        │
  │  用户在手机输入配对码    │                        │
  │══════════════════════════════════════════════════>│
  │                        │   配对成功通知           │
  │                        │<───────────────────────│
  │                        │  保存凭据到文件          │
  │                        │                        │
  │ GET /credentials/:id   │                        │
  │───────────────────────>│                        │
  │  返回完整凭据JSON       │                        │
  │<───────────────────────│                        │
```

### 二维码模式

```
客户端                    服务端                    WhatsApp
  │                        │                        │
  │ POST /qr-code          │                        │
  │───────────────────────>│                        │
  │                        │  makeWASocket()        │
  │                        │  生成QR码               │
  │  返回 qrCode 数据      │                        │
  │<───────────────────────│                        │
  │                        │                        │
  │  用户扫码               │                        │
  │══════════════════════════════════════════════════>│
  │                        │   认证成功通知           │
  │                        │<───────────────────────│
  │                        │  保存凭据到文件          │
  │                        │                        │
  │ GET /credentials/:id   │                        │
  │───────────────────────>│                        │
  │  返回完整凭据JSON       │                        │
  │<───────────────────────│                        │
```

---

## 前端集成示例

### JavaScript (fetch)

```javascript
// 1. 请求配对码
async function requestPairingCode(phoneNumber) {
  const res = await fetch('http://localhost:3000/api/auth/pairing-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phoneNumber })
  })
  const data = await res.json()
  console.log(`配对码: ${data.pairingCode}`)
  return data
}

// 2. 轮询状态直到连接成功
async function waitForConnection(sessionId, interval = 3000) {
  while (true) {
    const res = await fetch(`http://localhost:3000/api/auth/status/${sessionId}`)
    const data = await res.json()

    if (data.status === 'connected') {
      console.log('授权成功！')
      return data
    }
    if (data.status === 'logged_out' || data.status === 'pairing_code_error') {
      throw new Error(`授权失败: ${data.status}`)
    }

    await new Promise(r => setTimeout(r, interval))
  }
}

// 3. 获取凭据
async function getCredentials(sessionId) {
  const res = await fetch(`http://localhost:3000/api/auth/credentials/${sessionId}`)
  return await res.json()
}

// 完整流程
async function main() {
  const { sessionId, pairingCode } = await requestPairingCode('5927342668')
  alert(`请在 WhatsApp 中输入配对码: ${pairingCode}`)
  await waitForConnection(sessionId)
  const creds = await getCredentials(sessionId)
  console.log('完整凭据:', creds)
}
```

---

## 常见问题

### Q: 配对码过期了怎么办？

配对码有效期约 60 秒。过期后重新调用 `POST /api/auth/pairing-code` 即可获取新配对码。

### Q: 设备ID `:4` 是什么意思？

JID 中的 `:4` 表示这是第4个链接设备。WhatsApp 允许最多链接 4 个设备（手机 + 3个辅助设备）。

### Q: 凭据可以跨服务器使用吗？

可以。凭据是自包含的，只要将 `sessions/` 目录下的凭据文件复制到新服务器，调用恢复接口即可重新连接。

### Q: 连接断开后会自动重连吗？

Baileys 内置了自动重连机制。对于临时断开（网络波动），会自动重连；对于 `loggedOut` 状态，需要重新授权。

### Q: 手机号格式要求？

- 必须包含国家码
- 不含 `+`、`-`、`()`、空格
- 示例：圭亚那 `5927342668`，中国 `8613800138000`

---

## 安全警告

- 凭据文件包含所有私钥，**必须妥善保管**，泄露等同于 WhatsApp 账号被盗
- 生产环境建议加密存储凭据
- API 服务应添加认证中间件，防止未授权访问
- 建议使用 HTTPS 部署

/**
 * WhatsApp 配对码授权 REST API 服务
 *
 * API 端点：
 *   POST   /api/auth/pairing-code   - 请求配对码
 *   POST   /api/auth/qr-code        - 请求二维码
 *   GET    /api/auth/status/:id     - 查询授权状态
 *   GET    /api/auth/credentials/:id - 获取完整凭据
 *   GET    /api/auth/sessions       - 列出所有会话
 *   DELETE /api/auth/session/:id    - 断开并删除会话
 *   POST   /api/auth/restore/:id    - 恢复已保存的会话
 *   POST   /api/message/send/:id    - 发送消息
 */

const express = require('express')
const path = require('path')
const QRCode = require('qrcode-terminal')
const waAuth = require('./lib/wa-auth')
const credentialStore = require('./lib/credential-store')

const app = express()
app.use(express.json())

// 静态文件服务（前端页面）
app.use(express.static(path.join(__dirname, 'public')))

// CORS
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*')
  res.header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
  if (req.method === 'OPTIONS') return res.sendStatus(200)
  next()
})

// ============================================================
// 配对码授权
// ============================================================
app.post('/api/auth/pairing-code', async (req, res) => {
  try {
    const { phoneNumber, sessionId, platform } = req.body

    if (!phoneNumber) {
      return res.status(400).json({ error: '缺少 phoneNumber 参数' })
    }

    // 清理手机号：移除 +, -, (), 空格
    const cleanPhone = phoneNumber.replace(/[\+\-\(\)\s]/g, '')
    const sid = sessionId || `wa_${cleanPhone}_${Date.now()}`

    const result = await waAuth.createConnection({
      sessionId: sid,
      phoneNumber: cleanPhone,
      usePairingCode: true,
      platform: platform || 'android',
      onPairingCode: (code) => {
        console.log(`[配对码] ${cleanPhone} => ${code}`)
      },
      onConnected: (creds) => {
        console.log(`[已连接] ${sid} - ${creds.me?.id || 'unknown'}`)
      },
      onDisconnected: (info) => {
        console.log(`[已断开] ${sid} - ${info.reason}`)
      }
    })

    res.json({
      success: true,
      sessionId: sid,
      status: result.status,
      pairingCode: result.pairingCode,
      message: result.pairingCode
        ? `请在 WhatsApp 中输入配对码: ${result.pairingCode}`
        : '正在生成配对码，请稍后查询状态'
    })
  } catch (err) {
    console.error('[配对码错误]', err)
    res.status(500).json({ error: err.message })
  }
})

// ============================================================
// 二维码授权
// ============================================================
app.post('/api/auth/qr-code', async (req, res) => {
  try {
    const { sessionId, platform } = req.body
    const sid = sessionId || `wa_qr_${Date.now()}`

    let qrCodeData = null

    const result = await waAuth.createConnection({
      sessionId: sid,
      usePairingCode: false,
      platform: platform || 'web',
      onQrCode: (qr) => {
        qrCodeData = qr
        console.log(`[二维码] ${sid} 已生成`)
        // 在终端也显示二维码
        QRCode.generate(qr, { small: true })
      },
      onConnected: (creds) => {
        console.log(`[已连接] ${sid} - ${creds.me?.id || 'unknown'}`)
      },
      onDisconnected: (info) => {
        console.log(`[已断开] ${sid} - ${info.reason}`)
      }
    })

    res.json({
      success: true,
      sessionId: sid,
      status: result.status,
      qrCode: result.qrCode || qrCodeData,
      message: '请使用 WhatsApp 扫描二维码'
    })
  } catch (err) {
    console.error('[二维码错误]', err)
    res.status(500).json({ error: err.message })
  }
})

// ============================================================
// 查询授权状态
// ============================================================
app.get('/api/auth/status/:sessionId', (req, res) => {
  const info = waAuth.getSessionInfo(req.params.sessionId)
  if (!info) {
    return res.status(404).json({ error: '会话不存在' })
  }
  res.json(info)
})

// ============================================================
// 获取完整凭据
// ============================================================
app.get('/api/auth/credentials/:sessionId', (req, res) => {
  const creds = waAuth.getSessionCredentials(req.params.sessionId)
  if (!creds) {
    // 尝试从文件加载
    const fileCreds = credentialStore.exportCredentials(req.params.sessionId)
    if (!fileCreds) {
      return res.status(404).json({ error: '凭据不存在' })
    }
    return res.json(fileCreds)
  }
  res.json(creds)
})

// ============================================================
// 列出所有会话
// ============================================================
app.get('/api/auth/sessions', (req, res) => {
  const activeSessions = waAuth.getAllSessions()
  const savedSessions = credentialStore.listSessions()

  res.json({
    active: activeSessions,
    saved: savedSessions
  })
})

// ============================================================
// 断开并删除会话
// ============================================================
app.delete('/api/auth/session/:sessionId', async (req, res) => {
  const { deleteCredentials } = req.query
  const sid = req.params.sessionId

  await waAuth.disconnectSession(sid)

  if (deleteCredentials === 'true') {
    credentialStore.deleteCredentials(sid)
  }

  res.json({ success: true, message: '会话已断开' })
})

// ============================================================
// 恢复已保存的会话
// ============================================================
app.post('/api/auth/restore/:sessionId', async (req, res) => {
  try {
    const result = await waAuth.restoreSession(req.params.sessionId)
    res.json({
      success: true,
      sessionId: req.params.sessionId,
      status: result.status
    })
  } catch (err) {
    res.status(400).json({ error: err.message })
  }
})

// ============================================================
// 发送消息
// ============================================================
app.post('/api/message/send/:sessionId', async (req, res) => {
  try {
    const { jid, text, image, document } = req.body

    if (!jid) {
      return res.status(400).json({ error: '缺少 jid 参数（如 5927342668@s.whatsapp.net）' })
    }

    let content
    if (text) {
      content = { text }
    } else if (image) {
      content = { image: Buffer.from(image.data, 'base64'), caption: image.caption || '' }
    } else if (document) {
      content = { document: Buffer.from(document.data, 'base64'), fileName: document.fileName, mimetype: document.mimetype }
    } else {
      return res.status(400).json({ error: '缺少消息内容（text/image/document）' })
    }

    const sent = await waAuth.sendMessage(req.params.sessionId, jid, content)
    res.json({ success: true, messageId: sent.key.id })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// ============================================================
// 首页 - 返回前端页面（由 express.static 处理）
// ============================================================
app.get('/api', (req, res) => {
  res.json({
    name: 'WhatsApp 配对码授权服务',
    version: '1.0.0',
    endpoints: {
      'POST /api/auth/pairing-code': '配对码授权',
      'POST /api/auth/qr-code': '二维码授权',
      'GET /api/auth/status/:id': '查询状态',
      'GET /api/auth/credentials/:id': '获取凭据',
      'GET /api/auth/sessions': '列出会话',
      'DELETE /api/auth/session/:id': '断开会话',
      'POST /api/auth/restore/:id': '恢复会话',
      'POST /api/message/send/:id': '发送消息',
    }
  })
})

// ============================================================
// 启动服务
// ============================================================
const PORT = process.env.PORT || 3000

app.listen(PORT, () => {
  console.log('========================================')
  console.log('  WhatsApp 配对码授权服务已启动')
  console.log(`  地址: http://localhost:${PORT}`)
  console.log('========================================')
  console.log('')
  console.log('API 使用示例:')
  console.log('')
  console.log('  # 请求配对码')
  console.log(`  curl -X POST http://localhost:${PORT}/api/auth/pairing-code \\`)
  console.log('    -H "Content-Type: application/json" \\')
  console.log('    -d \'{"phoneNumber":"5927342668"}\'')
  console.log('')
  console.log('  # 查询状态')
  console.log(`  curl http://localhost:${PORT}/api/auth/status/<sessionId>`)
  console.log('')
  console.log('  # 获取凭据')
  console.log(`  curl http://localhost:${PORT}/api/auth/credentials/<sessionId>`)
  console.log('')
})

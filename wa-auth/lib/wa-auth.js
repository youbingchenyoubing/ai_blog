/**
 * WhatsApp 配对码授权核心模块
 * 基于 @whiskeysockets/baileys 实现
 *
 * 支持两种授权方式：
 *   1. 配对码（Pairing Code）- 输入手机号获取8位配对码
 *   2. 二维码（QR Code）- 扫码登录
 */

const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
  Browsers
} = require('@whiskeysockets/baileys')
const P = require('pino')
const { Boom } = require('@hapi/boom')
const credentialStore = require('./credential-store')

// 会话管理器
const sessions = new Map()

/**
 * 创建 WhatsApp 连接
 * @param {Object} options
 * @param {string} options.sessionId - 会话ID
 * @param {string} options.phoneNumber - 手机号（配对码模式）
 * @param {boolean} options.usePairingCode - 是否使用配对码模式
 * @param {string} options.platform - 伪装平台: android | ios | web
 * @param {Function} options.onQrCode - 二维码回调 (qrCode) => void
 * @param {Function} options.onPairingCode - 配对码回调 (code) => void
 * @param {Function} options.onConnected - 连接成功回调 (creds) => void
 * @param {Function} options.onDisconnected - 断开连接回调 (reason) => void
 * @returns {Promise<Object>} 会话信息
 */
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

  // 如果已有同 ID 的活跃会话，先断开
  if (sessions.has(sessionId)) {
    const existing = sessions.get(sessionId)
    if (existing.sock) {
      existing.sock.end(undefined)
    }
    sessions.delete(sessionId)
  }

  // 获取最新 Baileys 版本
  const { version } = await fetchLatestBaileysVersion()

  // 使用多文件认证状态
  const authDir = credentialStore.getSessionDir
    ? credentialStore.getSessionDir(sessionId)
    : require('path').join(credentialStore.CREDENTIALS_DIR, sessionId)

  const { state, saveCreds } = await useMultiFileAuthState(authDir)

  // 选择浏览器伪装
  let browser
  switch (platform) {
    case 'android':
      browser = Browsers.ubuntu('Chrome')
      break
    case 'ios':
      browser = Browsers.macOS('Chrome')
      break
    case 'windows':
      browser = Browsers.windows('Chrome')
      break
    default:
      browser = Browsers.ubuntu('Chrome')
  }

  // 创建 Socket
  const sock = makeWASocket({
    version,
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, P({ level: 'silent' }))
    },
    printQRInTerminal: false,
    browser,
    logger: P({ level: 'silent' }),
    connectTimeoutMs: 60_000,
    defaultQueryTimeoutMs: 30_000,
    keepAliveIntervalMs: 25_000,
    markOnlineOnConnect: false,
  })

  // 保存凭据回调
  sock.ev.on('creds.update', saveCreds)

  // 会话状态
  const sessionState = {
    sessionId,
    sock,
    status: 'connecting',
    pairingCode: null,
    qrCode: null,
    credentials: null,
    phoneNumber: phoneNumber || null,
    platform,
    createdAt: Date.now(),
    connectedAt: null,
  }

  sessions.set(sessionId, sessionState)

  // 连接更新处理
  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update

    // 处理二维码
    if (qr) {
      sessionState.qrCode = qr
      sessionState.status = 'qr_ready'
      if (!usePairingCode && onQrCode) {
        onQrCode(qr)
      }
    }

    // 配对码模式：连接后请求配对码
    if (qr && usePairingCode && !sock.authState.creds.registered) {
      try {
        const code = await sock.requestPairingCode(phoneNumber)
        sessionState.pairingCode = code
        sessionState.status = 'pairing_code_ready'
        if (onPairingCode) {
          onPairingCode(code)
        }
      } catch (err) {
        sessionState.status = 'pairing_code_error'
        sessionState.error = err.message
      }
    }

    // 连接成功
    if (connection === 'open') {
      sessionState.status = 'connected'
      sessionState.connectedAt = Date.now()
      sessionState.credentials = sock.authState.creds

      // 保存完整凭据
      credentialStore.saveCredentials(sessionId, sock.authState.creds)

      if (onConnected) {
        onConnected(credentialStore.serializeBuffers(sock.authState.creds))
      }
    }

    // 连接断开
    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut

      sessionState.status = shouldReconnect ? 'disconnected' : 'logged_out'

      if (!shouldReconnect) {
        // 被踢下线，清理会话
        sessions.delete(sessionId)
        credentialStore.deleteCredentials(sessionId)
      }

      if (onDisconnected) {
        onDisconnected({
          statusCode,
          reason: getDisconnectReason(statusCode),
          shouldReconnect
        })
      }
    }
  })

  // 等待初始状态
  return new Promise((resolve) => {
    // 短暂等待让连接建立
    setTimeout(() => {
      resolve(getSessionInfo(sessionId))
    }, 2000)
  })
}

/**
 * 获取断开原因描述
 */
function getDisconnectReason(statusCode) {
  const reasons = {
    [DisconnectReason.badSession]: '会话无效，需要重新扫描',
    [DisconnectReason.connectionClosed]: '连接关闭，将自动重连',
    [DisconnectReason.connectionLost]: '连接丢失，将自动重连',
    [DisconnectReason.connectionReplaced]: '连接被其他设备替换',
    [DisconnectReason.loggedOut]: '已登出，需要重新认证',
    [DisconnectReason.restartRequired]: '需要重启',
    [DisconnectReason.timedOut]: '连接超时',
  }
  return reasons[statusCode] || `未知原因 (${statusCode})`
}

/**
 * 获取会话信息
 */
function getSessionInfo(sessionId) {
  const session = sessions.get(sessionId)
  if (!session) return null

  return {
    sessionId: session.sessionId,
    status: session.status,
    pairingCode: session.pairingCode,
    qrCode: session.qrCode,
    phoneNumber: session.phoneNumber,
    platform: session.platform,
    registered: session.sock?.authState?.creds?.registered || false,
    me: session.sock?.authState?.creds?.me || null,
    createdAt: session.createdAt,
    connectedAt: session.connectedAt,
  }
}

/**
 * 获取完整凭据（已序列化）
 */
function getSessionCredentials(sessionId) {
  const session = sessions.get(sessionId)
  if (!session) return null

  const creds = session.sock?.authState?.creds
  if (!creds) return null

  return credentialStore.serializeBuffers(creds)
}

/**
 * 断开会话
 */
async function disconnectSession(sessionId) {
  const session = sessions.get(sessionId)
  if (!session) return false

  try {
    await session.sock.end(undefined)
  } catch (e) {
    // 忽略关闭错误
  }
  sessions.delete(sessionId)
  return true
}

/**
 * 发送消息
 */
async function sendMessage(sessionId, jid, content) {
  const session = sessions.get(sessionId)
  if (!session || session.status !== 'connected') {
    throw new Error('会话未连接')
  }

  const sent = await session.sock.sendMessage(jid, content)
  return sent
}

/**
 * 获取所有活跃会话
 */
function getAllSessions() {
  const result = []
  for (const [id] of sessions) {
    result.push(getSessionInfo(id))
  }
  return result
}

/**
 * 使用已保存的凭据恢复连接
 */
async function restoreSession(sessionId) {
  const creds = credentialStore.loadCredentials(sessionId)
  if (!creds || !creds.registered) {
    throw new Error('没有有效的已注册凭据')
  }

  return createConnection({
    sessionId,
    usePairingCode: false,
    onConnected: (credentials) => {
      console.log(`[WA-Auth] 会话 ${sessionId} 已恢复连接`)
    },
    onDisconnected: (info) => {
      console.log(`[WA-Auth] 会话 ${sessionId} 断开: ${info.reason}`)
    }
  })
}

module.exports = {
  createConnection,
  getSessionInfo,
  getSessionCredentials,
  disconnectSession,
  sendMessage,
  getAllSessions,
  restoreSession,
  sessions,
}

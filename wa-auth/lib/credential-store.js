/**
 * 凭据存储模块
 * 管理 WhatsApp 认证凭据的读写、Buffer 序列化/反序列化
 */

const fs = require('fs')
const path = require('path')

const CREDENTIALS_DIR = path.join(__dirname, '..', 'sessions')

// 确保目录存在
if (!fs.existsSync(CREDENTIALS_DIR)) {
  fs.mkdirSync(CREDENTIALS_DIR, { recursive: true })
}

/**
 * Buffer 序列化：将包含 Buffer 的对象转为可 JSON 序列化的格式
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
    // 检查是否是 Buffer 描述对象
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
 * 获取会话目录路径
 */
function getSessionDir(sessionId) {
  const dir = path.join(CREDENTIALS_DIR, sessionId)
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true })
  }
  return dir
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
  if (!fs.existsSync(filePath)) {
    return null
  }
  const raw = JSON.parse(fs.readFileSync(filePath, 'utf-8'))
  return deserializeBuffers(raw)
}

/**
 * 删除会话凭据
 */
function deleteCredentials(sessionId) {
  const dir = getSessionDir(sessionId)
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true })
    return true
  }
  return false
}

/**
 * 列出所有已保存的会话
 */
function listSessions() {
  if (!fs.existsSync(CREDENTIALS_DIR)) {
    return []
  }
  return fs.readdirSync(CREDENTIALS_DIR).filter(name => {
    const credsPath = path.join(CREDENTIALS_DIR, name, 'creds.json')
    return fs.existsSync(credsPath)
  })
}

/**
 * 检查会话是否已注册
 */
function isRegistered(sessionId) {
  const creds = loadCredentials(sessionId)
  return creds !== null && creds.registered === true
}

/**
 * 导出凭据为可传输的 JSON 格式（Buffer 用 base64 编码）
 */
function exportCredentials(sessionId) {
  const creds = loadCredentials(sessionId)
  if (!creds) return null
  return serializeBuffers(creds)
}

module.exports = {
  serializeBuffers,
  deserializeBuffers,
  saveCredentials,
  loadCredentials,
  deleteCredentials,
  listSessions,
  isRegistered,
  exportCredentials,
  CREDENTIALS_DIR
}

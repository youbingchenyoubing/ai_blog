# iMessage 群控 Agent：自动群发 + 智能回复

> 基于前两篇文章的 iPhone 自动化和群控方案，本文实现一个完整的 iMessage 群控 Agent：自动群发消息、读取 iMessage 短信、AI 自动回复。项目代码在 `imessage-agent/` 目录下，可直接运行。

## 一、系统架构

```
┌─────────────────────────────────────────────────────┐
│                   main.py (入口)                     │
├─────────────────────────────────────────────────────┤
│               scheduler.py (调度引擎)                 │
│         轮询消息 · 分发任务 · 协调模块                  │
├──────────┬──────────┬──────────┬────────────────────┤
│ device.py│imessage.py│  ai.py   │                    │
│ 设备管理  │读取+发送  │AI回复    │                    │
├──────────┴──────────┴──────────┴────────────────────┤
│              config.yaml (配置中心)                   │
└─────────────────────────────────────────────────────┘
```

**两种工作模式：**

| 模式 | 读取方式 | 发送方式 | 多设备支持 | 适用场景 |
|------|----------|----------|------------|----------|
| **mac** | chat.db (SQLite) | AppleScript | ❌ 仅单 Apple ID | 1 台 iPhone + Mac iCloud 同步 |
| **wda** | WDA 无障碍树 | WDA UI 自动化 | ✅ 每台 iPhone 独立控制 | 多台 iPhone 群控 |

> ⚠️ **Mac 模式无法真正群控多台 iPhone**。Mac 的 Messages App 只能登录一个 Apple ID，所有消息共享同一个 chat.db。如果你有多台 iPhone 使用不同 Apple ID，必须使用 WDA 模式。

---

## 二、核心模块详解

### 2.1 iMessage 读取模块

**Mac 模式：读取 chat.db**

macOS 的 Messages 应用将所有 iMessage 存储在 `~/Library/Messages/chat.db`（SQLite 数据库）。开启 iCloud 消息同步后，iPhone 上的消息会自动同步到 Mac。

核心表结构：

```sql
-- 消息表
message (ROWID, text, is_from_me, date, handle_id, service)

-- 联系人表
handle (ROWID, id)  -- id 为手机号或 Apple ID

-- 聊天-消息关联表
chat_message_join (chat_id, message_id)
```

读取新消息的 SQL：

```sql
SELECT m.ROWID, m.text, m.is_from_me, m.date,
       h.id AS sender_id, cmj.chat_id
FROM message m
LEFT JOIN handle h ON m.handle_id = h.ROWID
LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
WHERE m.ROWID > ?    -- 上次读取的最大 ID
AND m.text IS NOT NULL
ORDER BY m.date DESC
LIMIT 50
```

> ⚠️ 需要在「系统设置 → 隐私与安全 → 完全磁盘访问权限」中添加终端应用，否则无法读取 chat.db。

**WDA 模式：读取 Messages App**

通过 WebDriverAgent 打开 Messages App，读取无障碍树（Accessibility Tree）中的消息内容。这种方式不需要 iCloud 同步，但解析精度有限。

### 2.2 消息发送模块

**Mac 模式：AppleScript 发送**

```applescript
tell application "Messages"
    set targetService to 1st account whose service type = iMessage
    set targetBuddy to participant "+8613800138000" of targetService
    send "Hello" to targetBuddy
end tell
```

Python 通过 `subprocess` 调用 `osascript` 执行 AppleScript。

**WDA 模式：UI 自动化发送**

通过 WDA 模拟用户操作：打开 Messages → 新建消息 → 输入收件人 → 输入内容 → 点击发送。

### 2.3 AI 自动回复模块

支持两种回复引擎：

**OpenAI 模式（默认）：**

```
收到消息 → 发送给 GPT → 获取回复 → 发送回去
```

支持任何 OpenAI 兼容 API（OpenAI、智谱、DeepSeek 等），只需修改 `base_url` 和 `api_key`。

**规则模式（备选）：**

基于关键词匹配的简单规则引擎，无需 API 调用，适合简单场景。

### 2.4 调度引擎

- **轮询模式**：定时检查每台设备的新消息
- **并发处理**：多设备同时轮询，互不阻塞
- **智能延迟**：AI 回复前随机等待 3~8 秒，模拟真人行为
- **关键词过滤**：验证码、快递等关键词跳过自动回复
- **黑名单**：指定发送者不自动回复

---

## 三、快速开始

### 3.1 环境准备

```bash
# 安装 Python 依赖
cd imessage-agent
pip install -r requirements.txt

# Mac 模式需要：开启 iCloud 消息同步
# iPhone: 设置 → [你的名字] → iCloud → 消息 → 开启
# Mac: 系统设置 → [你的名字] → iCloud → 消息 → 开启

# 授权终端访问 chat.db
# 系统设置 → 隐私与安全 → 完全磁盘访问权限 → 添加终端/Terminal
```

### 3.2 修改配置

编辑 `config.yaml`：

```yaml
# AI 配置（必改）
ai:
  base_url: "https://api.openai.com/v1"   # 或其他兼容 API
  api_key: "sk-your-api-key-here"          # 你的 API Key
  model: "gpt-4o-mini"

# 群发配置
broadcast:
  message: "你好，这是一条测试消息"
  recipients:
    - "+8613800138000"
  enabled: true

# 自动回复配置
auto_reply:
  enabled: true
  keyword_filters:
    - "验证码"
    - "快递"
```

### 3.3 启动

```bash
# 启动 Agent（群发 + 自动回复）
python main.py start

# 查看设备状态
python main.py status

# 手动发送消息
python main.py send --to "+8613800138000" --text "你好"

# 手动群发
python main.py broadcast --text "通知：明天休息"
```

### 3.4 运行效果

```
15:30:01 [INFO] ==================================================
15:30:01 [INFO]   iMessage 群控 Agent 启动
15:30:01 [INFO] ==================================================
15:30:01 [INFO] 在线设备: 2/2
15:30:01 [INFO]   ✅ iPhone-A (mac) - 端口 8100
15:30:01 [INFO]   ✅ iPhone-B (mac) - 端口 8200
15:30:02 [INFO] 📢 群发消息: 你好，这是一条测试消息
15:30:02 [INFO]    收件人: ['+8613800138000']
15:30:05 [INFO]   ✅ iPhone-A->+8613800138000
15:30:08 [INFO]   ✅ iPhone-B->+8613800138000
15:30:08 [INFO] 群发完成: 2/2 成功
15:30:08 [INFO] 🔄 自动回复已启用，轮询间隔: 5s
15:30:25 [INFO] [iPhone-A] 15:30:25 收到消息:
15:30:25 [INFO]   📨 +8613900139000: 今天天气怎么样？
15:30:25 [INFO]   ⏳ 等待 5.2s 后回复...
15:30:30 [INFO]   🤖 AI 回复: 今天阳光不错，适合出门走走～
15:30:31 [INFO]   ✅ 已回复 +8613900139000
```

---

## 四、配置详解

### 4.1 设备配置

```yaml
devices:
  - name: "iPhone-A"           # 设备名称（自定义）
    udid: "your_udid_here"     # 设备 UDID（WDA 模式需要）
    local_port: 8100           # 本地端口（WDA 模式需要）
    mode: "mac"                # 工作模式: mac 或 wda
```

### 4.2 AI 配置

```yaml
ai:
  provider: "openai"                          # openai 或 rule
  base_url: "https://api.openai.com/v1"       # API 地址
  api_key: "sk-xxx"                           # API Key
  model: "gpt-4o-mini"                        # 模型名称
  system_prompt: |                            # 系统提示词
    你是一个智能消息助手...
```

**兼容的 AI 服务：**

| 服务 | base_url | model |
|------|----------|-------|
| OpenAI | https://api.openai.com/v1 | gpt-4o-mini |
| 智谱 GLM | https://open.bigmodel.cn/api/paas/v4 | glm-4-flash |
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat |
| 月之暗面 | https://api.moonshot.cn/v1 | moonshot-v1-8k |

### 4.3 自动回复配置

```yaml
auto_reply:
  enabled: true               # 是否启用自动回复
  reply_delay_min: 3          # 最小回复延迟（秒）
  reply_delay_max: 8          # 最大回复延迟（秒）
  keyword_filters:            # 包含这些关键词的消息不回复
    - "验证码"
    - "快递"
  blocked_senders:            # 这些发送者不回复
    - "spam@icloud.com"
```

---

## 五、项目文件说明

```
imessage-agent/
├── config.yaml          # 配置文件（修改后使用）
├── requirements.txt     # Python 依赖
├── main.py             # 主入口
└── core/
    ├── __init__.py
    ├── device.py        # 设备管理（注册、健康检查、iproxy）
    ├── imessage.py      # iMessage 读取 + 发送（Mac/WDA 双模式）
    ├── ai.py            # AI 自动回复（OpenAI + 规则引擎）
    └── scheduler.py     # 群控调度（轮询、并发、群发）
```

---

## 六、常见问题

### Q: 读取 chat.db 报错 "unable to open database file"

需要在「系统设置 → 隐私与安全 → 完全磁盘访问权限」中添加你运行脚本的终端应用（Terminal / iTerm2 / VS Code 等）。

### Q: AppleScript 发送消息报错 "Not allowed to send messages"

首次运行 AppleScript 发送消息时，macOS 会弹出权限确认框，需要点击「允许」。如果错过了，在「系统设置 → 隐私与安全 → 自动化」中重新授权。

### Q: 免费开发者账号的 WDA 7 天过期怎么办？

免费 Apple ID 签名的 WDA 有效期 7 天，过期后需要重新部署。建议：
- 写一个定时脚本每周自动重新部署
- 或使用付费开发者账号（$99/年），签名有效期 1 年

### Q: 如何同时控制多台 iPhone 的 iMessage？

每台 iPhone 需要使用不同的 Apple ID。如果所有 iPhone 共享同一个 Apple ID：
- Mac 模式：chat.db 会包含所有设备的消息，通过 `service` 字段区分
- WDA 模式：每台设备独立读取，天然隔离

### Q: AI 回复不够自然怎么办？

调整 `system_prompt` 提示词，例如：

```yaml
system_prompt: |
  你是一个性格开朗的朋友，聊天风格随意幽默。
  回复要求：
  - 用口语化的表达，不要太正式
  - 可以适当用表情符号
  - 回复控制在20字以内
  - 如果对方发的是日常闲聊，用同样轻松的语气回应
```

---

## 七、安全与合规

1. **iMessage 使用条款**：Apple 不允许通过自动化方式大量发送 iMessage，滥发可能导致账号被封禁
2. **消息频率控制**：建议每分钟发送不超过 15 条消息，避免触发 Apple 的反垃圾机制
3. **隐私保护**：chat.db 包含所有消息记录，注意数据安全
4. **AI 回复风险**：AI 可能生成不恰当的回复，建议设置关键词过滤和人工审核
5. **合法用途**：本工具仅供个人学习和合法业务场景使用

---

## 参考资源

- [iPhone 自动化操作完全手册](./iphone-automation-guide.md)
- [iPhone 群控实战](./iphone-group-control-guide.md)
- [macOS chat.db 结构分析](https://spin.atomicobject.com/search-imessage-sql/)
- [AppleScript Messages 词典](https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide/reference/ASLR_apps.html)
- [OpenAI API 文档](https://platform.openai.com/docs/api-reference)

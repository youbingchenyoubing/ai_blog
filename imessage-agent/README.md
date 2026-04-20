# iMessage 群控 Agent — 项目文档

> 一台 Mac 通过 USB 连接多台 iPhone，实现 iMessage 消息群发、自动读取、AI 智能回复。

## 一、项目概述

### 1.1 功能清单

| 功能 | 说明 | 状态 |
|------|------|------|
| 消息群发 | 多台 iPhone 同时向多个收件人发送 iMessage | ✅ 已实现 |
| 消息读取 | 自动检测新收到的 iMessage | ✅ 已实现 |
| AI 自动回复 | 收到消息后由 AI 生成回复并自动发送 | ✅ 已实现 |
| 多设备群控 | 一台 Mac 同时控制多台 iPhone | ✅ 已实现 |
| 关键词过滤 | 验证码、快递等消息跳过自动回复 | ✅ 已实现 |
| 黑名单 | 指定发送者不自动回复 | ✅ 已实现 |
| 模拟真人延迟 | 回复前随机等待 3~8 秒 | ✅ 已实现 |
| 截图监控 | 定时截图检测屏幕变化 | ✅ 已实现 |

### 1.2 两种工作模式

| 模式 | 读取方式 | 发送方式 | 多设备 | 适用场景 |
|------|----------|----------|--------|----------|
| **wda** | WDA 无障碍树 | WDA UI 自动化 | ✅ 每台独立 | 多台 iPhone 群控 |
| **mac** | chat.db (SQLite) | AppleScript | ❌ 仅单 Apple ID | 1 台 iPhone + Mac |

> **群控场景必须使用 WDA 模式。** Mac 模式受限于一个 Apple ID 只能登录一台 Mac Messages App。

### 1.3 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                        main.py (CLI 入口)                     │
│  python main.py start | status | send | broadcast            │
├──────────────────────────────────────────────────────────────┤
│                    scheduler.py (调度引擎)                     │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │ 轮询消息     │  │ 分发任务      │  │ 并发控制             │ │
│  │ (定时器)     │  │ (ThreadPool) │  │ (设备级隔离)         │ │
│  └─────────────┘  └──────────────┘  └─────────────────────┘ │
├──────────┬───────────────┬───────────────┬──────────────────┤
│ device.py│  imessage.py  │    ai.py      │                  │
│ 设备管理  │ 读取 + 发送    │  AI 回复      │                  │
│ 注册/健康 │ Mac/WDA 双模式 │ OpenAI/规则   │                  │
├──────────┴───────────────┴───────────────┴──────────────────┤
│                    config.yaml (配置中心)                      │
├──────────────────────────────────────────────────────────────┤
│                    start_usb.sh (硬件启动)                     │
│            检测设备 → iproxy 映射 → 验证 WDA                   │
└──────────────────────────────────────────────────────────────┘
```

### 1.4 数据流

```
WDA 模式数据流：

  读取: iPhone Messages App → WDA(source) → Python 解析 → Message 对象
  发送: Python → WDA(UI 操作) → iPhone Messages App → iMessage 发出
  回复: Message → AI API → 回复文本 → WDA → iPhone Messages App

Mac 模式数据流：

  读取: iPhone → iCloud 同步 → Mac chat.db → SQLite 查询 → Message 对象
  发送: Python → osascript → Mac Messages App → iCloud → iPhone 发出
```

---

## 二、项目结构

```
imessage-agent/
├── config.yaml          # 配置文件
├── requirements.txt     # Python 依赖
├── main.py              # CLI 主入口
├── start_usb.sh         # USB 连接检查与端口映射脚本
└── core/
    ├── __init__.py
    ├── device.py         # Device / DeviceManager — 设备注册与状态管理
    ├── imessage.py       # IMessageReader / IMessageSender — 消息读取与发送
    ├── ai.py             # AIReplier / SimpleRuleReplier — AI 自动回复
    └── scheduler.py      # MessageScheduler — 群控调度引擎
```

---

## 三、模块详细设计

### 3.1 device.py — 设备管理

**核心类：**

| 类 | 职责 |
|----|------|
| `DeviceMode` | 枚举：MAC / WDA |
| `DeviceStatus` | 枚举：ONLINE / BUSY / OFFLINE |
| `Device` | 单台设备的数据模型 |
| `Message` | 单条消息的数据模型 |
| `DeviceManager` | 管理所有设备，从 config.yaml 加载 |

**Device 字段：**

```python
@dataclass
class Device:
    name: str                    # 设备名称（自定义，如 "iPhone-A"）
    udid: str                    # 设备 UDID（WDA 模式必需）
    local_port: int              # Mac 本地映射端口（8100, 8200, 8300...）
    mode: DeviceMode             # 工作模式：WDA 或 MAC
    apple_id: str                # 该设备绑定的 Apple ID
    status: DeviceStatus         # 当前状态
    current_task: Optional[str]  # 当前执行的任务 ID
    last_message_id: int         # 上次读取的最大消息 ID（增量读取）
    last_screenshot_hash: str    # 上次截图的 MD5（变化检测）
```

**Message 字段：**

```python
@dataclass
class Message:
    rowid: int                   # 消息唯一 ID
    text: str                    # 消息文本内容
    sender: str                  # 发送者（手机号 / Apple ID）
    is_from_me: bool             # 是否是我发送的
    date: float                  # 时间戳
    chat_id: Optional[int]       # 聊天会话 ID
    service: Optional[str]       # 服务类型（iMessage / SMS）
    device_name: str             # 来自哪台设备
```

**DeviceManager 方法：**

| 方法 | 说明 |
|------|------|
| `_init_devices()` | 从 config.yaml 加载设备列表 |
| `get_online_devices()` | 返回所有在线设备 |
| `health_check()` | 逐台检查设备在线状态 |
| `start_iproxy()` | 为 WDA 设备启动 iproxy 端口映射 |

### 3.2 imessage.py — 消息读取与发送

**IMessageReader：**

| 方法 | 模式 | 说明 |
|------|------|------|
| `read_new_messages(device)` | 通用 | 根据设备模式分发到具体实现 |
| `_read_from_chatdb(device)` | Mac | 读取 `~/Library/Messages/chat.db`，增量查询 |
| `_read_from_wda(device)` | WDA | 通过 WDA 打开 Messages App，解析无障碍树 |
| `_parse_messages_from_source()` | WDA | 正则提取 `XCUIElementTypeStaticText` 的 value |
| `take_screenshot(device)` | WDA | 截图并 MD5 去重，用于变化检测 |

**Mac 模式 chat.db 查询 SQL：**

```sql
SELECT m.ROWID, m.text, m.is_from_me, m.date, m.service,
       h.id AS sender_id, cmj.chat_id
FROM message m
LEFT JOIN handle h ON m.handle_id = h.ROWID
LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
WHERE m.ROWID > ?          -- 增量：只查上次之后的新消息
AND m.text IS NOT NULL
AND m.text != ''
ORDER BY m.date DESC
LIMIT 50
```

**IMessageSender：**

| 方法 | 模式 | 说明 |
|------|------|------|
| `send_message(device, recipient, text)` | 通用 | 根据设备模式分发 |
| `_send_via_applescript(recipient, text)` | Mac | 通过 `osascript` 调用 AppleScript |
| `_send_via_wda(device, recipient, text)` | WDA | 通过 WDA 模拟 UI 操作发送 |
| `broadcast(devices, recipients, text)` | 通用 | 多设备 × 多收件人矩阵式群发 |

**WDA 发送流程：**

```
打开 Messages App → 点击 New Message → 输入收件人 → 选择联系人
→ 点击消息输入框 → 输入文本 → 点击 Send 按钮
```

**AppleScript 发送：**

```applescript
tell application "Messages"
    set targetService to 1st account whose service type = iMessage
    set targetBuddy to participant "+8613800138000" of targetService
    send "Hello" to targetBuddy
end tell
```

### 3.3 ai.py — AI 自动回复

**AIReplier（OpenAI 模式）：**

| 方法 | 说明 |
|------|------|
| `should_reply(message)` | 判断是否应该回复（过滤自己的消息、黑名单、关键词） |
| `generate_reply(message)` | 调用 OpenAI API 生成回复文本 |
| `process_message(device, message, sender)` | 完整流程：判断 → 延迟 → 生成 → 返回 |

**回复流程：**

```
收到消息 → should_reply() 判断
  ├─ 是自己发的 → 跳过
  ├─ 在黑名单中 → 跳过
  ├─ 包含过滤关键词 → 跳过
  └─ 应该回复 → 随机延迟 3~8s → AI 生成回复 → 返回回复文本
```

**SimpleRuleReplier（规则模式）：**

无需 API 调用，基于关键词匹配的简单规则引擎：
- 自定义规则：配置 `rules` 字典，key 为触发词，value 为回复
- 内置规则：问候语、问句的默认回复
- 兜底回复：`"收到，我看到你的消息了！"`

**兼容的 AI 服务：**

| 服务 | base_url | model |
|------|----------|-------|
| OpenAI | `https://api.openai.com/v1` | gpt-4o-mini |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | glm-4-flash |
| DeepSeek | `https://api.deepseek.com/v1` | deepseek-chat |
| 月之暗面 | `https://api.moonshot.cn/v1` | moonshot-v1-8k |

### 3.4 scheduler.py — 群控调度引擎

**MessageScheduler：**

| 方法 | 说明 |
|------|------|
| `start()` | 主入口：健康检查 → 群发 → 进入自动回复循环 |
| `stop()` | 停止运行 |
| `_run_broadcast(cfg)` | 执行消息群发 |
| `_run_auto_reply_loop()` | 无限循环轮询所有设备 |
| `_poll_all_devices()` | ThreadPoolExecutor 并发轮询 |
| `_poll_device(device)` | 单设备：读取新消息 → AI 回复 → 发送 |
| `send_to_all(text, recipients)` | 手动发送消息 |
| `status()` | 显示所有设备状态 |

**并发模型：**

```
主线程
  │
  ├─ _run_auto_reply_loop()
  │    │
  │    ├─ _poll_all_devices()  ← 每轮
  │    │    ├─ ThreadPoolExecutor
  │    │    │    ├─ Thread-1: _poll_device(iPhone-A)
  │    │    │    ├─ Thread-2: _poll_device(iPhone-B)
  │    │    │    └─ Thread-3: _poll_device(iPhone-C)
  │    │    └─ 等待所有线程完成
  │    │
  │    └─ sleep(poll_interval)
  │
  └─ 循环
```

---

## 四、配置文件详解

```yaml
# ===== 设备列表 =====
devices:
  - name: "iPhone-A"              # 设备名称（自定义）
    udid: "your_device_udid_here" # 设备 UDID（idevice_id -l 获取）
    local_port: 8100              # Mac 本地映射端口
    mode: "wda"                   # 工作模式：wda 或 mac
    apple_id: "+8613800138000"    # 该设备绑定的 Apple ID

# ===== Mac 模式配置 =====
mac:
  chat_db_path: "~/Library/Messages/chat.db"  # chat.db 路径
  poll_interval: 5                              # 轮询间隔（秒）

# ===== WDA 模式配置 =====
wda:
  poll_interval: 10       # 轮询间隔（秒），WDA 操作较慢建议 ≥10
  screenshot_dir: "./screenshots"  # 截图保存目录

# ===== AI 配置 =====
ai:
  provider: "openai"      # openai 或 rule
  base_url: "https://api.openai.com/v1"
  api_key: "sk-xxx"
  model: "gpt-4o-mini"
  system_prompt: |         # AI 系统提示词，控制回复风格
    你是一个智能消息助手...

# ===== 群发配置 =====
broadcast:
  message: "群发内容"
  recipients:              # 收件人列表
    - "+8613800138000"
  interval: 60             # 群发间隔（秒）
  enabled: false           # 启动时是否自动群发

# ===== 自动回复配置 =====
auto_reply:
  enabled: true            # 是否启用自动回复
  reply_delay_min: 3       # 最小回复延迟（秒）
  reply_delay_max: 8       # 最大回复延迟（秒）
  keyword_filters:         # 包含这些关键词的消息不自动回复
    - "验证码"
    - "快递"
  blocked_senders: []      # 黑名单发送者

# ===== 日志配置 =====
logging:
  level: "INFO"
  file: "imessage_agent.log"
```

---

## 五、使用指南

### 5.1 环境准备

**硬件：**

| 物品 | 要求 |
|------|------|
| Mac | macOS 13+，至少 1 个 USB 口 |
| iPhone | iOS 16+，每台已激活 iMessage |
| USB Hub | 工业级，每口独立供电 ≥2.1A（3 台以上需要） |
| 数据线 | 支持 USB 数据传输（不是仅充电线） |

**软件：**

```bash
# 1. 安装 Homebrew 工具
brew install libimobiledevice

# 2. 安装 Python 依赖
cd imessage-agent
pip install -r requirements.txt

# 3. 克隆并配置 WebDriverAgent（WDA 模式需要）
git clone https://github.com/appium/WebDriverAgent.git
# 用 Xcode 打开，配置签名，部署到 iPhone
```

### 5.2 硬件连接

```bash
# 1. iPhone 通过 USB 连接到 Mac（直连或通过 Hub）
# 2. iPhone 弹出「信任此电脑？」→ 点击信任
# 3. 运行连接检查脚本
./start_usb.sh
```

`start_usb.sh` 会自动完成：
- 检测所有 USB 连接的 iPhone
- 显示设备名称、iOS 版本、UDID
- 为每台设备启动 iproxy 端口映射
- 验证 WDA 是否在线

### 5.3 部署 WebDriverAgent

对每台 iPhone 执行一次（首次或 WDA 过期后）：

```bash
# 查看设备 UDID
idevice_id -l

# 为每台设备编译部署 WDA（替换 UDID）
xcodebuild -project WebDriverAgent.xcodeproj \
  -scheme WebDriverAgentRunner \
  -destination 'id=<UDID>' \
  test
```

首次部署后需在 iPhone 上信任开发者证书：
`设置 → 通用 → VPN与设备管理 → 信任`

### 5.4 修改配置

编辑 `config.yaml`，至少修改：

1. **设备 UDID**：运行 `idevice_id -l` 获取
2. **AI API Key**：填入你的 OpenAI 或兼容 API Key
3. **收件人列表**：群发的目标手机号或 Apple ID

### 5.5 启动

```bash
# 启动 Agent（群发 + 自动回复）
python main.py start

# 查看设备状态
python main.py status

# 手动发送消息
python main.py send --to "+8613800138000" --text "你好"

# 手动群发
python main.py broadcast --text "通知：明天休息"

# 使用自定义配置
python main.py --config /path/to/config.yaml start
```

### 5.6 运行效果

```
15:30:01 [INFO] ==================================================
15:30:01 [INFO]   iMessage 群控 Agent 启动
15:30:01 [INFO] ==================================================
15:30:01 [INFO] 在线设备: 3/3
15:30:01 [INFO]   ✅ iPhone-A (wda) - 端口 8100
15:30:01 [INFO]   ✅ iPhone-B (wda) - 端口 8200
15:30:01 [INFO]   ✅ iPhone-C (wda) - 端口 8300
15:30:08 [INFO] 🔄 自动回复已启用，轮询间隔: 10s
15:30:18 [INFO] [iPhone-A] 15:30:18 收到消息:
15:30:18 [INFO]   📨 +8613900139000: 今天天气怎么样？
15:30:18 [INFO]   ⏳ 等待 5.2s 后回复...
15:30:23 [INFO]   🤖 AI 回复: 今天阳光不错，适合出门走走～
15:30:24 [INFO]   ✅ 已回复 +8613900139000
```

---

## 六、关键技术细节

### 6.1 多设备端口映射

每台 iPhone 上的 WDA 监听 8100 端口（设备内部端口相同），通过 `iproxy -u UDID` 映射到 Mac 的不同本地端口：

```
iproxy 8100 8100 -u UDID_A  →  iPhone-A
iproxy 8200 8100 -u UDID_B  →  iPhone-B
iproxy 8300 8100 -u UDID_C  →  iPhone-C
```

Python 通过 `http://localhost:8100`、`http://localhost:8200` 等分别连接不同设备。

### 6.2 增量消息读取

使用 `last_message_id` 实现增量读取，避免重复处理：

- Mac 模式：`WHERE m.ROWID > last_message_id`
- WDA 模式：`rowid = last_message_id + i + 1`

每次读取后更新 `last_message_id` 为最大值。

### 6.3 截图变化检测

WDA 模式下通过截图 MD5 哈希检测屏幕变化：

```python
file_hash = hashlib.md5(screenshot_bytes).hexdigest()
if file_hash == device.last_screenshot_hash:
    # 屏幕没变化，跳过
else:
    # 屏幕有变化，可能有新消息
    device.last_screenshot_hash = file_hash
```

### 6.4 并发与隔离

- 每台设备在独立线程中轮询，互不阻塞
- 设备状态（ONLINE/BUSY/OFFLINE）隔离，单台故障不影响其他
- 任务失败自动重试（AIReplier 内部）

---

## 七、已知限制与优化方向

### 7.1 当前限制

| 限制 | 原因 | 影响 |
|------|------|------|
| WDA 读取消息无法区分发送者 | 无障碍树中缺少发送者信息 | 无法针对特定人回复 |
| WDA 读取消息可能重复 | 正则匹配不够精确 | 可能重复回复 |
| Mac 模式仅支持单 Apple ID | Mac Messages App 限制 | 无法群控多账号 |
| 免费开发者证书 7 天过期 | Apple 限制 | WDA 每周需重新部署 |
| WDA 操作速度慢 | 每步需要 UI 渲染等待 | 轮询间隔 ≥10s |
| 不支持 SMS（仅 iMessage） | WDA/SMS 协议不同 | 非 iMessage 联系人无法使用 |

### 7.2 优化方向

#### 优先级 P0：替代 WDA 读取——Webhook 实时转发（已实现 ✅）

WDA 读取消息的核心问题：无障碍树解析不精确、无法区分发送者、轮询延迟大。
**最佳方案不是 OCR，而是让 iPhone 自己把消息推过来。**

**方案：iOS 快捷指令 + Webhook**

```
iPhone 收到 iMessage → 快捷指令自动触发 → POST 到 Mac Webhook 服务器 → AI 回复
```

优势：
- ✅ 实时推送，零延迟（不是轮询）
- ✅ 精确获取发送者和消息内容
- ✅ 不依赖 WDA 读取，WDA 仅用于发送
- ✅ iOS 17+ 支持息屏自动运行
- ✅ Apple 官方自动化框架，无需越狱

**iPhone 快捷指令配置步骤：**

1. 打开「快捷指令」→「自动化」→「创建个人自动化」
2. 触发条件：选择「信息」→「收到信息」
3. 添加操作：「获取 URL 内容」
4. 配置：
   - URL：`http://<Mac的IP>:9876/`
   - 方法：POST
   - 头部：`Content-Type: application/json`
   - 请求体（JSON）：
     ```json
     {
       "device_name": "iPhone-A",
       "text": "快捷指令输入：消息内容",
       "sender": "快捷指令输入：发件人"
     }
     ```
5. 关闭「运行前问询」→ 完成

> iOS 17+ 支持完全自动运行（息屏也可），iOS 16 需手动确认。

**Mac 端 Webhook 服务器（已内置）：**

```yaml
# config.yaml
webhook:
  enabled: true
  port: 9876
```

启动后 Mac 监听 9876 端口，iPhone 收到消息后自动 POST 过来。

#### 优先级 P0+：Mac 多用户 + 多 chat.db（已实现 ✅）

一台 Mac 可以创建多个用户账号，每个用户登录不同的 Apple ID，各自有独立的 chat.db：

```
Mac 用户 A (Apple ID-1) → /Users/user_a/Library/Messages/chat.db
Mac 用户 B (Apple ID-2) → /Users/user_b/Library/Messages/chat.db
Mac 用户 C (Apple ID-3) → /Users/user_c/Library/Messages/chat.db
```

配置方式：

```yaml
devices:
  - name: "iPhone-A"
    mode: "mac"
    chatdb_path: "/Users/user_a/Library/Messages/chat.db"
  - name: "iPhone-B"
    mode: "mac"
    chatdb_path: "/Users/user_b/Library/Messages/chat.db"
```

前提条件：
- 开启 Mac「快速用户切换」功能（系统设置 → 用户与群组）
- 所有用户同时保持登录状态
- 每个用户在 Messages App 中登录不同的 Apple ID
- 终端需要完全磁盘访问权限来读取其他用户的 chat.db

优势：
- ✅ chat.db 读取精确（完整的发送者、内容、时间）
- ✅ 不需要 WDA 读取，WDA 仅用于发送
- ✅ 一台 Mac 可以同时读取多个 Apple ID 的消息

#### 优先级 P1：消息推送实时监听（chat.db WAL）

当前使用轮询（polling）方式，有延迟。优化为事件驱动：

**方案 A：Mac 模式 — chat.db WAL 监听**

```python
# 监听 chat.db 的 WAL 日志变化
# 使用 fsevents 或 watchdog 库
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ChatDBHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if "chat.db" in event.src_path:
            read_new_messages()
```

**方案 B：WDA 模式 — 通知监听**

```python
# 通过 pymobiledevice3 监听 iOS 通知
# 当收到 iMessage 通知时触发读取
pymobiledevice3 notifications listen
```

#### 优先级 P2：Web 管理面板

```
┌─────────────────────────────────────────┐
│          iMessage Agent Dashboard        │
├─────────────────────────────────────────┤
│  设备状态  │  消息记录  │  任务管理       │
│  🟢 iPhone-A  │  📨 12条  │  ▶ 运行中   │
│  🟢 iPhone-B  │  📨 8条   │  ▶ 运行中   │
│  🔴 iPhone-C  │  📨 0条   │  ⏹ 已停止   │
├─────────────────────────────────────────┤
│  [群发消息]  [查看日志]  [修改配置]       │
└─────────────────────────────────────────┘
```

技术选型：Flask + WebSocket（参考群控文章第九节）

#### 优先级 P3：对话上下文

当前每次回复是独立的，没有上下文。优化：

```python
# 维护每个联系人的对话历史
conversation_history: dict[str, list[dict]] = {}

def generate_reply_with_context(message: Message) -> str:
    history = conversation_history.get(message.sender, [])
    history.append({"role": "user", "content": message.text})

    response = client.chat.completions.create(
        model=self.model,
        messages=[
            {"role": "system", "content": self.system_prompt},
            *history[-10:],  # 最近 10 轮对话
        ],
    )

    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})
    conversation_history[message.sender] = history
    return reply
```

#### 优先级 P4：WDA 自动部署与保活

```bash
# 自动检测 WDA 离线并重新部署
while true; do
    for UDID in $(idevice_id -l); do
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/status)
        if [ "$STATUS" != "200" ]; then
            echo "WDA 离线，重新部署: $UDID"
            xcodebuild -project WebDriverAgent.xcodeproj \
                -scheme WebDriverAgentRunner \
                -destination "id=$UDID" test &
        fi
    done
    sleep 30
done
```

#### 优先级 P5：分布式扩展

超过 30 台设备时，单 Mac 不够用，需要多 Mac 集群：

```
主控服务器 (Flask API + 任务队列)
    │
    ├── Mac Worker 1 (20 台 iPhone)
    ├── Mac Worker 2 (20 台 iPhone)
    └── Mac Worker 3 (20 台 iPhone)
```

Worker 通过 HTTP API 上报状态、领取任务。

---

## 八、常见问题

### Q1: 读取 chat.db 报错 "unable to open database file"

在「系统设置 → 隐私与安全 → 完全磁盘访问权限」中添加运行脚本的终端应用。

### Q2: AppleScript 发送消息报错 "Not allowed to send messages"

首次运行时 macOS 会弹出权限确认框，点击「允许」。或在「系统设置 → 隐私与安全 → 自动化」中重新授权。

### Q3: WDA 7 天过期怎么办？

- 短期：手动重新部署
- 中期：写定时脚本每周自动重新部署（见 P4 优化方向）
- 长期：使用付费开发者账号（$99/年），签名有效期 1 年

### Q4: 多台 iPhone 能否共用一个 Apple ID？

可以，但 Mac 模式下所有消息会混在一起。WDA 模式下每台设备独立读取，不受影响。建议群控场景每台 iPhone 使用不同 Apple ID。

### Q5: WDA 读取消息不准确怎么办？

这是当前最大的限制。建议优化为截图 + OCR 方案（见 P0 优化方向），或使用 Mac 模式 + iCloud 同步（仅限单 Apple ID）。

### Q6: 如何控制发送频率避免被封号？

- 每分钟发送不超过 15 条消息
- 群发间隔设置 ≥60 秒
- 自动回复延迟 3~8 秒模拟真人
- 避免短时间内向同一联系人发送大量消息

---

## 九、安全与合规

1. **Apple 开发者协议**：免费账号 7 天签名限制，大规模使用建议付费开发者账号
2. **iMessage 使用条款**：Apple 禁止通过自动化方式大量发送 iMessage，滥发可能被封号
3. **隐私保护**：chat.db 包含所有消息记录，注意数据安全
4. **AI 回复风险**：AI 可能生成不恰当回复，建议设置关键词过滤和人工审核
5. **合法用途**：本工具仅供个人学习和合法业务场景使用，禁止用于违法违规场景

---

## 十、依赖清单

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 运行环境 |
| openai | ≥1.0.0 | AI 回复生成 |
| pyyaml | ≥6.0 | 配置文件解析 |
| facebook-wda | ≥1.0.0 | WDA 模式设备控制 |
| libimobiledevice | - | iproxy 端口映射、idevice_id 设备检测 |
| WebDriverAgent | - | iOS 自动化服务端 |
| Xcode | 最新版 | 编译部署 WDA |

---

## 十一、参考资源

- [iPhone 自动化操作完全手册](./iphone-automation-guide.md)
- [iPhone 群控实战](./iphone-group-control-guide.md)
- [WebDriverAgent - GitHub](https://github.com/appium/WebDriverAgent)
- [facebook-wda - GitHub](https://github.com/openatx/facebook-wda)
- [OpenAI API 文档](https://platform.openai.com/docs/api-reference)
- [macOS chat.db 结构分析](https://spin.atomicobject.com/search-imessage-sql/)
- [AppleScript Messages 词典](https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide/reference/ASLR_apps.html)

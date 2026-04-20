# 一台 Mac 群控多台 iPhone：Mac 多用户方案详解

> 这是目前最优雅的 iPhone 群控方案：一台 Mac 创建多个用户账号，每个用户登录不同 Apple ID，通过各自的 chat.db 精确读取消息，通过 WDA 精确发送消息。不需要 OCR，不需要 Webhook，不需要多台 Mac。

## 一、方案原理

### 1.1 核心思路

```
一台 Mac
├── 用户 A (Apple ID-1) ← iCloud 同步 ← iPhone-A 的 iMessage
│   └── /Users/user_a/Library/Messages/chat.db
├── 用户 B (Apple ID-2) ← iCloud 同步 ← iPhone-B 的 iMessage
│   └── /Users/user_b/Library/Messages/chat.db
└── 用户 C (Apple ID-3) ← iCloud 同步 ← iPhone-C 的 iMessage
    └── /Users/user_c/Library/Messages/chat.db

主控程序（用户 A 运行）
├── 读取：同时读取 3 个 chat.db → 精确获取每台设备的消息
└── 发送：通过 WDA 在对应 iPhone 上发送 → 每台设备用自己的 Apple ID
```

### 1.2 为什么这是最优方案

| 对比项 | Mac 多用户方案 | Webhook 方案 | WDA 读取方案 | OCR 方案 |
|--------|---------------|-------------|-------------|---------|
| 消息精度 | ✅ 精确（chat.db） | ✅ 精确（快捷指令） | ❌ 不精确（无障碍树） | ❌ 不稳定 |
| 发送者识别 | ✅ 完整 | ✅ 完整 | ❌ 缺失 | ❌ 不可靠 |
| 实时性 | ⚠️ 轮询 5s | ✅ 实时推送 | ⚠️ 轮询 10s | ⚠️ 轮询 10s |
| 多设备支持 | ✅ 每用户一个 ID | ✅ 每台独立配置 | ✅ 每台独立 WDA | ✅ |
| 额外配置 | 创建 Mac 用户 | 每台 iPhone 配快捷指令 | 部署 WDA | 无 |
| 依赖 | 仅 Mac + iCloud | iPhone + Mac | Mac + WDA + USB | Mac + WDA + OCR |
| 发送方式 | WDA（各设备独立） | WDA | WDA | WDA |

**Mac 多用户方案的优势：**
- 读取最精确：chat.db 包含完整的发送者、内容、时间、服务类型
- 不需要每台 iPhone 配置快捷指令
- 不依赖 WDA 读取（WDA 仅用于发送，发送比读取简单得多）
- 一台 Mac 搞定一切

---

## 二、Mac 多用户配置

### 2.1 创建用户账号

为每台 iPhone 创建一个对应的 Mac 用户：

```
系统设置 → 用户与群组 → 添加用户

用户 A: user_a （对应 iPhone-A, Apple ID-1）
用户 B: user_b （对应 iPhone-B, Apple ID-2）
用户 C: user_c （对应 iPhone-C, Apple ID-3）
```

建议：
- 账号类型选「标准」即可
- 用户名用有意义的名称，如 `iphone_a`、`iphone_b`
- 设置密码（后续需要）

### 2.2 开启快速用户切换

```
系统设置 → 用户与群组 → 快速用户切换 → 开启
```

开启后，多个用户可以同时保持登录状态，不需要退出当前用户。

### 2.3 每个用户登录 Messages

逐个切换到每个用户，在 Messages App 中登录对应的 Apple ID：

```
切换到用户 A → 打开 Messages → 登录 Apple ID-1 → 开启 iCloud 消息同步
切换到用户 B → 打开 Messages → 登录 Apple ID-2 → 开启 iCloud 消息同步
切换到用户 C → 打开 Messages → 登录 Apple ID-3 → 开启 iCloud 消息同步
```

**iCloud 消息同步开启方式：**
```
iPhone: 设置 → [你的名字] → iCloud → 消息 → 开启
Mac: 系统设置 → [你的名字] → iCloud → 消息 → 开启
```

### 2.4 验证 chat.db

```bash
# 检查每个用户的 chat.db 是否存在
ls -la /Users/user_a/Library/Messages/chat.db
ls -la /Users/user_b/Library/Messages/chat.db
ls -la /Users/user_c/Library/Messages/chat.db
```

### 2.5 授权读取其他用户的 chat.db

在主控用户（运行程序的用户）的终端中，需要完全磁盘访问权限：

```
系统设置 → 隐私与安全 → 完全磁盘访问权限 → 添加终端 (Terminal / iTerm2)
```

---

## 三、iPhone 连接与 WDA 部署

### 3.1 USB 连接

所有 iPhone 通过 USB Hub 连接到 Mac：

```bash
# 验证连接
idevice_id -l

# 启动端口映射
./start_usb.sh
```

### 3.2 部署 WDA（仅用于发送）

每台 iPhone 需要部署 WebDriverAgent，但只需要它能发送消息即可，不需要精确读取：

```bash
# 为每台设备部署 WDA
xcodebuild -project WebDriverAgent.xcodeproj \
  -scheme WebDriverAgentRunner \
  -destination 'id=<UDID_A>' test &

xcodebuild -project WebDriverAgent.xcodeproj \
  -scheme WebDriverAgentRunner \
  -destination 'id=<UDID_B>' test &

xcodebuild -project WebDriverAgent.xcodeproj \
  -scheme WebDriverAgentRunner \
  -destination 'id=<UDID_C>' test &
```

---

## 四、项目配置

### 4.1 config.yaml

```yaml
devices:
  # iPhone-A：读取用 chat.db，发送用 WDA
  - name: "iPhone-A"
    udid: "a1b2c3d4e5f6..."
    local_port: 8100
    mode: "mac"
    apple_id: "+8613800138000"
    chatdb_path: "/Users/user_a/Library/Messages/chat.db"

  # iPhone-B：读取用 chat.db，发送用 WDA
  - name: "iPhone-B"
    udid: "f7e8d9c0b1a2..."
    local_port: 8200
    mode: "mac"
    apple_id: "+8613900139000"
    chatdb_path: "/Users/user_b/Library/Messages/chat.db"

  # iPhone-C：读取用 chat.db，发送用 WDA
  - name: "iPhone-C"
    udid: "1234567890ab..."
    local_port: 8300
    mode: "mac"
    apple_id: "user@icloud.com"
    chatdb_path: "/Users/user_c/Library/Messages/chat.db"

mac:
  poll_interval: 5

wda:
  poll_interval: 10
  screenshot_dir: "./screenshots"

webhook:
  enabled: false

ai:
  provider: "openai"
  base_url: "https://api.openai.com/v1"
  api_key: "sk-your-api-key-here"
  model: "gpt-4o-mini"
  system_prompt: |
    你是一个智能消息助手。请根据收到的消息内容，生成一条简短、自然、友好的回复。

broadcast:
  message: "你好，这是一条测试消息"
  recipients:
    - "+8613800138000"
  interval: 60
  enabled: false

auto_reply:
  enabled: true
  reply_delay_min: 3
  reply_delay_max: 8
  keyword_filters:
    - "验证码"
    - "快递"
  blocked_senders: []

logging:
  level: "INFO"
  file: "imessage_agent.log"
```

### 4.2 关键设计

```
┌─────────────────────────────────────────────────────────────┐
│                    Mac 多用户群控架构                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  读取层（chat.db）                                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ user_a       │ │ user_b       │ │ user_c       │        │
│  │ chat.db      │ │ chat.db      │ │ chat.db      │        │
│  │ Apple ID-1   │ │ Apple ID-2   │ │ Apple ID-3   │        │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘        │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          ▼                                  │
│              主控程序 (user_a 运行)                           │
│              ┌──────────────────┐                           │
│              │  scheduler.py    │                           │
│              │  并发读取 3 个 DB │                           │
│              │  AI 生成回复     │                           │
│              └────────┬─────────┘                           │
│                       │                                     │
│  发送层（WDA）        │                                     │
│         ┌─────────────┼─────────────┐                      │
│         ▼             ▼             ▼                      │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐             │
│  │ iPhone-A   │ │ iPhone-B   │ │ iPhone-C   │             │
│  │ WDA :8100  │ │ WDA :8200  │ │ WDA :8300  │             │
│  │ Apple ID-1 │ │ Apple ID-2 │ │ Apple ID-3 │             │
│  └────────────┘ └────────────┘ └────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**读取**：每个设备的 `chatdb_path` 指向对应用户的 chat.db，精确读取
**发送**：通过 WDA 在对应 iPhone 上操作，每台设备用自己的 Apple ID 发出

---

## 五、完整操作步骤

### 步骤 1：创建 Mac 用户

```bash
# 通过命令行创建用户（需要管理员权限）
sudo dscl . -create /Users/iphone_a
sudo dscl . -create /Users/iphone_a UserShell /bin/bash
sudo dscl . -create /Users/iphone_a RealName "iPhone A"
sudo dscl . -create /Users/iphone_a NFSHomeDirectory /Users/iphone_a
sudo dscl . -create /Users/iphone_a UniqueID 501
sudo dscl . -create /Users/iphone_a PrimaryGroupID 20
sudo dscl . -passwd /Users/iphone_a your_password
sudo createhomedir -c -u iphone_a
```

或通过 GUI：`系统设置 → 用户与群组 → 添加用户`

### 步骤 2：配置每个用户

逐个切换到每个用户：

1. 登录用户 → 打开 Messages → 登录 Apple ID → 开启 iCloud 消息同步
2. 等待消息同步完成（可能需要几分钟）
3. 切换回主控用户

### 步骤 3：连接 iPhone 并部署 WDA

```bash
# 连接所有 iPhone
./start_usb.sh

# 部署 WDA 到每台设备（见上文第三节）
```

### 步骤 4：修改配置

编辑 `config.yaml`，填入每台设备的 UDID、端口、chat.db 路径。

### 步骤 5：启动

```bash
python main.py start
```

### 步骤 6：验证

```bash
# 查看设备状态
python main.py status

# 手动发送测试消息
python main.py send --to "+8613800138000" --text "测试消息"
```

---

## 六、常见问题

### Q1: 读取其他用户的 chat.db 报权限错误

确保主控终端有「完全磁盘访问权限」：
```
系统设置 → 隐私与安全 → 完全磁盘访问权限 → 添加终端
```

### Q2: 某个用户的 chat.db 没有新消息

- 确认该用户已登录 Messages App
- 确认 iCloud 消息同步已开启
- 确认该用户没有退出登录（使用快速用户切换，不要退出）
- 检查 Mac 是否联网

### Q3: 多用户同时登录会占用很多资源吗？

不会。macOS 的快速用户切换设计就是让多个用户同时保持登录。后台用户的 Messages App 只占用少量内存（约 50~100MB/用户）。

### Q4: 最多支持多少个用户？

理论上没有限制，实际受 Mac 内存影响：
- 8GB Mac：建议 ≤5 个用户
- 16GB Mac：建议 ≤10 个用户
- 32GB Mac：可以 20+ 个用户

### Q5: 发送消息时如何确保从正确的 Apple ID 发出？

WDA 模式下，消息从 iPhone 本身发出，自然使用 iPhone 上登录的 Apple ID。不需要担心发送者身份问题。

### Q6: 可以混合使用 Mac 模式和 WDA 模式吗？

可以。配置文件中每个设备可以独立设置 mode：
- `mode: "mac"` + `chatdb_path`：通过 chat.db 读取，WDA 发送
- `mode: "wda"`：通过 WDA 读取和发送（精度较低）

---

## 七、方案对比总结

| 需求 | 推荐方案 |
|------|----------|
| 1 台 iPhone + 1 个 Apple ID | Mac 单用户 + chat.db + AppleScript |
| 多台 iPhone + 多个 Apple ID + 1 台 Mac | **Mac 多用户 + chat.db + WDA 发送**（本方案） |
| 多台 iPhone + 不想创建多用户 | Webhook + 快捷指令 + WDA 发送 |
| 超过 10 台 iPhone | 多 Mac 集群或 Mac 多用户 + Webhook 混合 |

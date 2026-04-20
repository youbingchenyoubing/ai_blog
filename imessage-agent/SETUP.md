# 多台 iPhone 关联一台 Mac 完整配置手册

> 本手册将手把手教你：如何让 3 台 iPhone（不同 Apple ID）的 iMessage 全部同步到一台 Mac 上，实现读取 + 自动回复 + 群发。

## 前置条件

| 项目 | 要求 |
|------|------|
| Mac | macOS 13+，至少 16GB 内存（推荐） |
| iPhone | iOS 16+，每台已激活 iMessage |
| Apple ID | 每台 iPhone 一个独立的 Apple ID |
| 网络 | Mac 和所有 iPhone 需联网 |
| 数据线 | 支持 USB 数据传输 |

---

## 第一步：在 Mac 上创建多个用户

每台 iPhone 需要对应一个 Mac 用户账号。Mac 的 Messages App 只能登录一个 Apple ID，所以必须创建多个用户。

### 1.1 通过系统设置创建（推荐）

1. 打开 **系统设置** → **用户与群组**
2. 点击 **添加用户**（需要输入管理员密码）
3. 填写信息：

| 字段 | iPhone-A 对应 | iPhone-B 对应 | iPhone-C 对应 |
|------|--------------|--------------|--------------|
| 全名 | iPhone A | iPhone B | iPhone C |
| 账户名称 | iphone_a | iphone_b | iphone_c |
| 密码 | 自定义 | 自定义 | 自定义 |
| 类型 | 标准 | 标准 | 标准 |

4. 重复操作，创建所有需要的用户

### 1.2 通过命令行创建

```bash
# 创建用户 iphone_a
sudo dscl . -create /Users/iphone_a
sudo dscl . -create /Users/iphone_a UserShell /bin/bash
sudo dscl . -create /Users/iphone_a RealName "iPhone A"
sudo dscl . -create /Users/iphone_a NFSHomeDirectory /Users/iphone_a
sudo dscl . -create /Users/iphone_a UniqueID 502
sudo dscl . -create /Users/iphone_a PrimaryGroupID 20
sudo dscl . -passwd /Users/iphone_a "你的密码"
sudo createhomedir -c -u iphone_a

# 创建用户 iphone_b
sudo dscl . -create /Users/iphone_b
sudo dscl . -create /Users/iphone_b UserShell /bin/bash
sudo dscl . -create /Users/iphone_b RealName "iPhone B"
sudo dscl . -create /Users/iphone_b NFSHomeDirectory /Users/iphone_b
sudo dscl . -create /Users/iphone_b UniqueID 503
sudo dscl . -create /Users/iphone_b PrimaryGroupID 20
sudo dscl . -passwd /Users/iphone_b "你的密码"
sudo createhomedir -c -u iphone_b

# 创建用户 iphone_c
sudo dscl . -create /Users/iphone_c
sudo dscl . -create /Users/iphone_c UserShell /bin/bash
sudo dscl . -create /Users/iphone_c RealName "iPhone C"
sudo dscl . -create /Users/iphone_c NFSHomeDirectory /Users/iphone_c
sudo dscl . -create /Users/iphone_c UniqueID 504
sudo dscl . -create /Users/iphone_c PrimaryGroupID 20
sudo dscl . -passwd /Users/iphone_c "你的密码"
sudo createhomedir -c -u iphone_c
```

### 1.3 验证用户创建成功

```bash
ls /Users/
# 应该看到: iphone_a  iphone_b  iphone_c  你的主用户
```

---

## 第二步：开启快速用户切换

快速用户切换允许所有用户同时保持登录状态，不需要退出。

1. 打开 **系统设置** → **用户与群组**
2. 找到 **快速用户切换** → 开启
3. 菜单栏会出现用户切换菜单

> ⚠️ **关键**：后续操作中，切换用户时选择「切换用户」而不是「退出登录」。退出登录会导致该用户的 Messages App 关闭，iCloud 同步中断。

---

## 第三步：逐个用户登录 Messages

这一步最关键，需要逐个切换到每个用户，在 Messages App 中登录对应的 Apple ID。

### 3.1 用户 A：登录 Apple ID-1

1. 点击菜单栏的用户名 → 切换到 **iPhone A**
2. 输入密码登录
3. 打开 **Messages**（信息）App
4. 如果是首次打开，按提示登录 Apple ID-1
5. 如果已登录其他 Apple ID：
   - `Messages → 设置 → iMessage 账户 → 退出登录`
   - 重新登录 Apple ID-1
6. 确认 **iCloud 消息同步** 已开启：
   - `系统设置 → [Apple ID-1] → iCloud → 消息` → 确保已开启
7. 等待消息同步完成（可能需要 1~5 分钟）
8. **不要退出登录**，切换回主用户

### 3.2 用户 B：登录 Apple ID-2

1. 点击菜单栏的用户名 → 切换到 **iPhone B**
2. 输入密码登录
3. 打开 **Messages** App
4. 登录 Apple ID-2
5. 确认 iCloud 消息同步已开启
6. 等待消息同步完成
7. 切换回主用户

### 3.3 用户 C：登录 Apple ID-3

重复上述步骤，登录 Apple ID-3。

### 3.4 验证同步

切换回你的主用户，检查每个用户的 chat.db 是否有数据：

```bash
# 检查 chat.db 文件是否存在
ls -la /Users/iphone_a/Library/Messages/chat.db
ls -la /Users/iphone_b/Library/Messages/chat.db
ls -la /Users/iphone_c/Library/Messages/chat.db

# 查看每个 chat.db 中的消息数量
for user in iphone_a iphone_b iphone_c; do
    echo "=== $user ==="
    sqlite3 "/Users/$user/Library/Messages/chat.db" \
        "SELECT COUNT(*) FROM message WHERE text IS NOT NULL;" 2>/dev/null || echo "无法读取"
done
```

如果输出类似：

```
=== iphone_a ===
142
=== iphone_b ===
87
=== iphone_c ===
203
```

说明同步成功。

---

## 第四步：iPhone 端配置 iCloud 消息同步

每台 iPhone 需要确保 iCloud 消息同步已开启，这样消息才会同步到 Mac。

### 在每台 iPhone 上操作：

1. 打开 **设置** → 点击顶部的 **[你的名字]**
2. 点击 **iCloud**
3. 找到 **消息** → 确保开关为 **开启**
4. 等待同步完成

### 验证同步：

在 iPhone 上发送一条测试消息，然后在 Mac 上检查对应用户的 chat.db：

```bash
# 查看最新消息
sqlite3 "/Users/iphone_a/Library/Messages/chat.db" \
    "SELECT text, date FROM message ORDER BY date DESC LIMIT 5;"
```

---

## 第五步：授权主用户读取其他用户的 chat.db

你的主控程序在主用户下运行，需要读取其他用户的 chat.db。

### 5.1 添加完全磁盘访问权限

1. 打开 **系统设置** → **隐私与安全** → **完全磁盘访问权限**
2. 点击 **+** 号，添加你运行脚本的终端应用：
   - 如果用 Terminal：添加 `/Applications/Utilities/Terminal.app`
   - 如果用 iTerm2：添加 `/Applications/iTerm.app`
   - 如果用 VS Code：添加 `/Applications/Visual Studio Code.app`
3. 添加后需要**重启终端**才能生效

### 5.2 验证读取权限

```bash
# 在主用户的终端中测试读取
sqlite3 "/Users/iphone_a/Library/Messages/chat.db" \
    "SELECT COUNT(*) FROM message;" 2>/dev/null && echo "✅ 可读取" || echo "❌ 无权限"
```

如果报权限错误，检查：
- 完全磁盘访问权限是否已添加
- 终端是否已重启
- 对应用户是否处于登录状态（快速用户切换，未退出）

---

## 第六步：USB 连接 iPhone 并部署 WDA

WDA 用于在 iPhone 上发送消息（读取已经通过 chat.db 解决了）。

### 6.1 连接 iPhone

1. 所有 iPhone 通过 USB 数据线连接到 Mac（3 台以内直连，3 台以上用 USB Hub）
2. 每台 iPhone 弹出「信任此电脑？」→ 点击 **信任**

### 6.2 验证连接

```bash
# 安装 libimobiledevice（如果还没有）
brew install libimobiledevice

# 查看已连接设备
idevice_id -l
```

应该显示 3 个 UDID。

### 6.3 获取每台设备的详细信息

```bash
for UDID in $(idevice_id -l); do
    NAME=$(ideviceinfo -u $UDID -k DeviceName 2>/dev/null)
    IOS=$(ideviceinfo -u $UDID -k ProductVersion 2>/dev/null)
    echo "$NAME (iOS $IOS) → UDID: $UDID"
done
```

记录每台设备的 UDID，后续配置需要用到。

### 6.4 部署 WebDriverAgent

**首次部署：**

1. 克隆 WebDriverAgent：
```bash
git clone https://github.com/appium/WebDriverAgent.git
cd WebDriverAgent
```

2. 用 Xcode 打开：
```bash
open WebDriverAgent.xcodeproj
```

3. 配置签名（对 3 个 Target 都要操作）：
   - 选择 `WebDriverAgentLib` → Signing & Capabilities
   - 勾选 `Automatically manage signing`
   - Team 选择你的 Apple ID
   - Bundle Identifier 改为 `com.yourname.WebDriverAgentLib`
   - 对 `WebDriverAgentRunner` 重复，Bundle ID 改为 `com.yourname.WebDriverAgentRunner`
   - 对 `IntegrationApp` 重复，Bundle ID 改为 `com.yourname.IntegrationApp`

4. 逐台部署：
   - 在 Xcode 顶部选择第一台 iPhone → 长按 Run 按钮 → 选择 **Test**
   - 等待编译部署完成
   - 在 iPhone 上信任开发者证书：`设置 → 通用 → VPN与设备管理 → 信任`
   - 重复以上步骤部署到其他 iPhone

**命令行批量部署：**

```bash
# 替换为实际的 UDID
xcodebuild -project WebDriverAgent.xcodeproj \
  -scheme WebDriverAgentRunner \
  -destination 'id=UDID_IPHONE_A' \
  -allowProvisioningUpdates \
  test &

xcodebuild -project WebDriverAgent.xcodeproj \
  -scheme WebDriverAgentRunner \
  -destination 'id=UDID_IPHONE_B' \
  -allowProvisioningUpdates \
  test &

xcodebuild -project WebDriverAgent.xcodeproj \
  -scheme WebDriverAgentRunner \
  -destination 'id=UDID_IPHONE_C' \
  -allowProvisioningUpdates \
  test &

wait
echo "所有设备 WDA 部署完成"
```

### 6.5 启动端口映射

```bash
# 为每台设备映射不同端口
iproxy 8100 8100 -u UDID_IPHONE_A &
iproxy 8200 8100 -u UDID_IPHONE_B &
iproxy 8300 8100 -u UDID_IPHONE_C &

# 验证
curl http://localhost:8100/status
curl http://localhost:8200/status
curl http://localhost:8300/status
```

或使用一键脚本：

```bash
cd imessage-agent
./start_usb.sh
```

---

## 第七步：配置项目

### 7.1 修改 config.yaml

```yaml
devices:
  - name: "iPhone-A"
    udid: "a1b2c3d4e5f6..."          # 第六步获取的 UDID
    local_port: 8100                   # iproxy 映射的端口
    mode: "mac"                        # mac 模式：chat.db 读取 + WDA 发送
    apple_id: "+8613800138000"         # iPhone-A 的 Apple ID / 手机号
    chatdb_path: "/Users/iphone_a/Library/Messages/chat.db"

  - name: "iPhone-B"
    udid: "f7e8d9c0b1a2..."
    local_port: 8200
    mode: "mac"
    apple_id: "+8613900139000"
    chatdb_path: "/Users/iphone_b/Library/Messages/chat.db"

  - name: "iPhone-C"
    udid: "1234567890ab..."
    local_port: 8300
    mode: "mac"
    apple_id: "user@icloud.com"
    chatdb_path: "/Users/iphone_c/Library/Messages/chat.db"

mac:
  poll_interval: 5

ai:
  provider: "openai"
  base_url: "https://api.openai.com/v1"
  api_key: "sk-your-api-key-here"     # 替换为你的 API Key
  model: "gpt-4o-mini"

auto_reply:
  enabled: true
  reply_delay_min: 3
  reply_delay_max: 8
  keyword_filters:
    - "验证码"
    - "快递"
  blocked_senders: []

broadcast:
  enabled: false
```

### 7.2 安装 Python 依赖

```bash
cd imessage-agent
pip install -r requirements.txt
```

---

## 第八步：启动与验证

### 8.1 启动 Agent

```bash
python main.py start
```

预期输出：

```
15:30:01 [INFO] ==================================================
15:30:01 [INFO]   iMessage 群控 Agent 启动
15:30:01 [INFO] ==================================================
15:30:01 [INFO] 在线设备: 3/3
15:30:01 [INFO]   ✅ iPhone-A (mac) - 端口 8100
15:30:01 [INFO]   ✅ iPhone-B (mac) - 端口 8200
15:30:01 [INFO]   ✅ iPhone-C (mac) - 端口 8300
15:30:02 [INFO] 🔄 自动回复已启用（轮询模式），间隔: 5s
```

### 8.2 测试发送

```bash
# 从 iPhone-A 发送一条测试消息
python main.py send --to "+8613900139000" --text "测试消息"
```

### 8.3 测试自动回复

用另一部手机给 iPhone-A 发一条 iMessage，观察 Agent 是否自动回复：

```
15:35:12 [INFO] [iPhone-A] 15:35:12 收到消息:
15:35:12 [INFO]   📨 +8613900139000: 你好，在吗？
15:35:12 [INFO]   ⏳ 等待 4.7s 后回复...
15:35:17 [INFO]   🤖 AI 回复: 在的，有什么事呀？
15:35:18 [INFO]   ✅ 已回复 +8613900139000
```

---

## 完整配置检查清单

启动前逐项确认：

### Mac 端

- [ ] 已创建 N 个 Mac 用户（每个 iPhone 一个）
- [ ] 已开启快速用户切换
- [ ] 每个用户已登录 Messages + 对应 Apple ID
- [ ] 每个用户的 iCloud 消息同步已开启
- [ ] 每个用户的 chat.db 可读取
- [ ] 主用户终端已添加完全磁盘访问权限
- [ ] 所有用户处于登录状态（未退出）

### iPhone 端

- [ ] 每台 iPhone 的 iCloud 消息同步已开启
- [ ] 每台 iPhone 通过 USB 连接到 Mac
- [ ] 每台 iPhone 已信任此电脑
- [ ] WebDriverAgent 已部署到每台 iPhone
- [ ] 每台 iPhone 已信任开发者证书
- [ ] iproxy 端口映射已启动

### 项目配置

- [ ] config.yaml 中每台设备的 UDID 已填写
- [ ] config.yaml 中每台设备的 chatdb_path 已填写
- [ ] config.yaml 中 AI API Key 已填写
- [ ] Python 依赖已安装

---

## 日常使用流程

每次使用时，按以下顺序操作：

```bash
# 1. 确保所有 Mac 用户已登录（快速用户切换，不要退出）
#    点击菜单栏用户名 → 确认所有用户都显示为"已登录"

# 2. 连接 iPhone + 启动端口映射
cd imessage-agent
./start_usb.sh

# 3. 启动 Agent
python main.py start
```

---

## 常见问题排查

### 问题：chat.db 读取不到新消息

**排查步骤：**

```bash
# 1. 检查用户是否登录
# 菜单栏 → 快速用户切换 → 确认用户未退出

# 2. 检查 iCloud 同步
# 切换到该用户 → Messages → 确认消息已同步

# 3. 检查文件权限
ls -la /Users/iphone_a/Library/Messages/chat.db

# 4. 手动查询
sqlite3 "/Users/iphone_a/Library/Messages/chat.db" \
    "SELECT text FROM message ORDER BY date DESC LIMIT 3;"
```

### 问题：WDA 发送消息失败

**排查步骤：**

```bash
# 1. 检查 WDA 是否在线
curl http://localhost:8100/status

# 2. 检查 iproxy 是否运行
ps aux | grep iproxy

# 3. 检查 iPhone 连接
idevice_id -l

# 4. 重新部署 WDA
# Xcode → 选择设备 → Test
```

### 问题：某个 Mac 用户的 Messages 退出登录

```bash
# 切换到该用户 → 重新打开 Messages → 确认 Apple ID 已登录
# 如果需要重新登录：
# Messages → 设置 → iMessage → 登录
```

### 问题：免费开发者证书过期（7天）

```bash
# 重新部署 WDA
xcodebuild -project WebDriverAgent.xcodeproj \
  -scheme WebDriverAgentRunner \
  -destination 'id=<UDID>' \
  test

# iPhone 上重新信任证书
# 设置 → 通用 → VPN与设备管理 → 信任
```

### 问题：Mac 内存不足

```bash
# 查看内存使用
activity_monitor  # 打开活动监视器

# 每个后台用户的 Messages App 约占 50~100MB
# 8GB Mac 建议 ≤5 个用户
# 16GB Mac 建议 ≤10 个用户
```

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        一台 Mac                                  │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 用户 iphone_a │  │ 用户 iphone_b │  │ 用户 iphone_c │          │
│  │ Apple ID-1   │  │ Apple ID-2   │  │ Apple ID-3   │          │
│  │ Messages ✓   │  │ Messages ✓   │  │ Messages ✓   │          │
│  │ chat.db ✓    │  │ chat.db ✓    │  │ chat.db ✓    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           ▼                                     │
│              ┌────────────────────────┐                         │
│              │   主控程序 (scheduler)  │                         │
│              │                        │                         │
│              │  读取: 3 个 chat.db    │                         │
│              │  AI: OpenAI 生成回复   │                         │
│              │  发送: WDA → iPhone    │                         │
│              └────────────┬───────────┘                         │
│                           │                                     │
│         ┌─────────────────┼─────────────────┐                   │
│         ▼                 ▼                 ▼                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │ iPhone-A   │  │ iPhone-B   │  │ iPhone-C   │               │
│  │ USB + WDA  │  │ USB + WDA  │  │ USB + WDA  │               │
│  │ Apple ID-1 │  │ Apple ID-2 │  │ Apple ID-3 │               │
│  │ :8100      │  │ :8200      │  │ :8300      │               │
│  └────────────┘  └────────────┘  └────────────┘               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

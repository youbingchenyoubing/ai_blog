# Telegram 多账户管理 Agent

> 基于 Telethon 实现的 Telegram 多账户管理与使用工具：消息群发、自动读取、AI 智能回复、在线改资料、防封保活、用户账户 + 机器人账户统一管理。

## 一、功能概览

| 功能 | 说明 | 状态 |
|------|------|------|
| 多账户管理 | 同时管理多个用户账户 + 机器人账户 | ✅ |
| 会话持久化 | .session 文件保存登录态，无需重复登录 | ✅ |
| 消息群发 | 多账户 × 多收件人矩阵式群发 | ✅ |
| 消息读取 | 增量轮询所有会话新消息 | ✅ |
| AI 自动回复 | OpenAI / 兼容 API 生成智能回复 | ✅ |
| 规则回复 | 关键词匹配的兜底规则引擎 | ✅ |
| 黑名单 / 关键词过滤 | 跳过指定发送者或含敏感词的消息 | ✅ |
| 私聊限制 | 仅回复私聊，不响应群组消息 | ✅ |
| 模拟真人延迟 | 回复前随机等待 3~8 秒 | ✅ |
| 对话上下文 | 维护每个联系人最近 10 轮对话 | ✅ |
| 代理支持 | SOCKS5/HTTP 代理（适用于受限网络） | ✅ |
| **在线改资料** | 用户名 / 姓名 / 简介 / 头像 / 两步验证 / 换绑手机号 | ✅ |
| **防封保活** | 行为模拟、频率限制、养号期、健康分、保活心跳 | ✅ |
| **设备指纹** | 随机主流设备型号，降低风控异常概率 | ✅ |
| **健康报告** | 实时查看账户健康分、FloodWait 次数、活动时间 | ✅ |

## 二、项目结构

```
telegram-agent/
├── config.yaml              # 配置文件（账户、AI、群发、自动回复、存活率、资料）
├── requirements.txt         # Python 依赖
├── main.py                  # CLI 主入口
├── sessions/                # 会话文件目录（自动创建）
├── avatars/                 # 头像目录（批量修改时按 <name>.jpg 匹配）
└── core/
    ├── __init__.py
    ├── account.py           # Account / AccountManager — 多账户管理
    ├── telegram_client.py   # TelegramReader / TelegramSender — 消息读写
    ├── ai.py                # AIReplier / SimpleRuleReplier — 智能回复
    ├── profile.py           # ProfileManager — 在线修改账户资料
    ├── survival.py          # SurvivalGuard / RateLimiter — 防封保活
    └── scheduler.py         # MessageScheduler — 异步调度引擎
```

## 三、快速开始

### 3.1 获取 API 凭证

1. 访问 https://my.telegram.org → 登录手机号
2. 「API development tools」→ 创建应用
3. 记下 `api_id` 和 `api_hash`

> Bot 账户额外需要 BotToken：在 Telegram 中找 [@BotFather](https://t.me/BotFather) 创建机器人获取。

### 3.2 安装依赖

```bash
cd telegram-agent
pip install -r requirements.txt
```

### 3.3 修改配置

编辑 `config.yaml`，至少修改：

1. **api_id / api_hash**：填入你的 Telegram API 凭证
2. **手机号 / bot_token**：用户账户填手机号，机器人填 BotToken
3. **AI API Key**：填入 OpenAI 或兼容 API Key
4. **收件人列表**：群发目标（@username 或 user_id）

### 3.4 首次登录

用户账户首次使用需要交互式输入验证码：

```bash
python main.py login
```

按提示输入收到的 Telegram 验证码（如开启了两步验证还需输入密码）。成功后会在 `sessions/` 目录生成 `.session` 文件，后续直接复用。

### 3.5 启动 Agent

```bash
# 启动（登录 + 群发 + 自动回复 + 保活）
python main.py start

# 查看账户状态（含健康分）
python main.py status

# 手动发送消息
python main.py send --to "@username" --text "你好"

# 手动群发
python main.py broadcast --text "通知：明天休息"

# 使用自定义配置
python main.py --config /path/to/config.yaml start
```

### 3.6 在线修改账户资料

```bash
# 查看所有账户当前资料
python main.py profile show

# 修改单个账户的姓名
python main.py profile set-name --account Account-A --first "小明" --last "李"

# 修改 @username（传空字符串删除）
python main.py profile set-username --account Account-A --username "xiaoming"

# 修改个人简介
python main.py profile set-about --account Account-A --about "热爱生活"

# 修改头像（单个）
python main.py profile set-photo --account Account-A --file /path/to/avatar.jpg

# 批量修改头像（从 avatars/ 目录取 <账户名>.jpg）
python main.py profile set-photo --all

# 设置两步验证（密码 + 恢复邮箱）
python main.py profile set-2fa --account Account-A \
    --password "MyStrongPass123" \
    --email "recovery@example.com" \
    --hint "我的密码提示"

# 修改两步验证（需提供当前密码）
python main.py profile set-2fa --account Account-A \
    --current "OldPass123" \
    --password "NewPass456" \
    --email "new@example.com"

# 换绑手机号（会发送验证码到新号码）
python main.py profile change-phone --account Account-A --phone "+8613900139000"

# 批量应用 config.yaml 中 profile.defaults 配置
python main.py profile apply-all
```

### 3.7 存活率与保活

```bash
# 立即执行一次保活（读取对话 + 标记已读 + 心跳）
python main.py keepalive

# 查看账户健康报告（健康分、FloodWait 次数、活动时间、警告）
python main.py health
```

启动 `start` 命令时会自动开启保活后台任务（间隔由 `survival.keepalive_interval` 控制，默认 30 分钟）。

## 四、配置详解

### 4.1 账户配置

```yaml
accounts:
  - name: "Account-A"             # 账户名称（自定义）
    type: "user"                  # user 或 bot
    session: "sessions/account_a" # .session 文件路径（不含扩展名）
    api_id: 123456                # Telegram API ID
    api_hash: "your_api_hash"     # Telegram API Hash
    phone: "+8613800138000"       # 用户账户需要
    proxy: null                   # 可选: ["socks5", "127.0.0.1", 1080]
    enabled: true                 # 是否启用
```

**账户类型对比：**

| 类型 | 登录方式 | 能力 | 适用场景 |
|------|----------|------|----------|
| user | 手机号 + 验证码 | 读写所有会话、私聊、群组 | 个人账号管理、私聊自动化 |
| bot | BotToken | 仅能接收@机器人的消息、主动发消息给已开启对话的用户 | 客服机器人、通知推送 |

### 4.2 代理配置

在受限网络环境下使用代理：

```yaml
accounts:
  - name: "Account-A"
    # ...
    proxy: ["socks5", "127.0.0.1", 1080]
    # 也可用 http: ["http", "127.0.0.1", 7890]
```

需要额外安装代理依赖：

```bash
pip install python-socks[asyncio]   # SOCKS5
# 或
pip install pysocks                  # SOCKS5（备选）
```

### 4.3 AI 配置

```yaml
ai:
  provider: "openai"           # openai 或 rule
  base_url: "https://api.openai.com/v1"
  api_key: "sk-xxx"
  model: "gpt-4o-mini"
  system_prompt: |              # 控制回复风格
    你是一个智能消息助手...
```

**兼容的 AI 服务：**

| 服务 | base_url | 推荐 model |
|------|----------|------------|
| OpenAI | `https://api.openai.com/v1` | gpt-4o-mini |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | glm-4-flash |
| DeepSeek | `https://api.deepseek.com/v1` | deepseek-chat |
| 月之暗面 | `https://api.moonshot.cn/v1` | moonshot-v1-8k |

### 4.4 自动回复配置

```yaml
auto_reply:
  enabled: true
  reply_delay_min: 3            # 最小回复延迟（秒）
  reply_delay_max: 8            # 最大回复延迟（秒）
  keyword_filters:              # 含这些关键词的消息不回复
    - "验证码"
    - "快递"
  blocked_senders: []           # 黑名单（user_id 或 username）
  private_only: true            # 仅回复私聊
```

## 五、运行效果

```
15:30:01 [INFO] ==================================================
15:30:01 [INFO]   Telegram 多账户 Agent 启动
15:30:01 [INFO] ==================================================
  ✅ Account-A (user)
  ✅ Bot-B (bot)
15:30:01 [INFO] 在线账户: 2/2
15:30:01 [INFO]   ✅ Account-A (user) @your_username
15:30:01 [INFO]   ✅ Bot-B (bot) id=123456789
15:30:01 [INFO] 🔄 自动回复已启用，轮询间隔: 5s
15:30:01 [INFO] 按 Ctrl+C 停止
15:30:18 [INFO] [Account-A] 15:30:18 收到消息:
15:30:18 [INFO]   📨 张三 (user): 今天天气怎么样？
15:30:23 [INFO]   ✅ 已回复
```

## 六、核心模块说明

### 6.1 account.py — 多账户管理

| 类 | 职责 |
|----|------|
| `AccountType` | 枚举：USER / BOT |
| `AccountStatus` | 枚举：ONLINE / OFFLINE / NEED_LOGIN / ERROR |
| `Account` | 单个账户数据模型，封装 TelegramClient |
| `AccountManager` | 管理所有账户，从 config.yaml 加载 |

**关键方法：**

| 方法 | 说明 |
|------|------|
| `login(account, interactive)` | 登录账户，支持验证码/两步验证 |
| `health_check()` | 检查所有账户连接状态 |
| `start_all()` | 启动所有账户 |
| `stop_all()` | 断开所有账户连接 |

### 6.2 telegram_client.py — 消息读写

**TelegramReader：**
- `read_new_messages(account)` — 增量读取所有会话新消息
- 使用 `account.last_message_id` 作为游标，避免重复处理

**TelegramSender：**
- `send_message(account, recipient, text)` — 发送消息
- `reply_message(account, chat_id, reply_to_id, text)` — 回复指定消息
- `broadcast(accounts, recipients, text)` — 矩阵式群发

**收件人解析支持：**
- `@username`
- `user_id`（数字字符串）
- `t.me/username` 链接

### 6.3 ai.py — 智能回复

- `AIReplier` — OpenAI 兼容 API，支持对话上下文（最近 10 轮）
- `SimpleRuleReplier` — 关键词规则引擎，无需 API 调用

**回复流程：**
```
收到消息 → should_reply() 判断
  ├─ 是自己发的 → 跳过
  ├─ 在黑名单中 → 跳过
  ├─ 包含过滤关键词 → 跳过
  ├─ 非私聊且 private_only=true → 跳过
  └─ 应该回复 → 随机延迟 3~8s → AI 生成 → 回复原消息
```

### 6.4 scheduler.py — 异步调度引擎

- 使用 `asyncio.gather` 并发轮询所有账户
- 主循环：`_poll_all_accounts → _poll_account → reader.read → guard.before_send → replier.process → guard.after_send`
- 启动时自动拉起保活后台任务 `keepalive_loop`

### 6.5 profile.py — 在线资料管理

| 方法 | 说明 | Telegram 限制 |
|------|------|---------------|
| `get_profile(account)` | 读取 id/姓名/用户名/手机号/简介/头像 | - |
| `update_username(account, username)` | 修改或删除 @username | 5-32 字符，字母开头 |
| `update_name(account, first, last)` | 修改 first_name / last_name | first_name 必填 |
| `update_about(account, about)` | 修改个人简介 | 普通 70 字符，Premium 140 |
| `update_photo(account, file_path)` | 上传新头像 | - |
| `delete_photo(account)` | 删除当前头像 | - |
| `update_2fa(...)` | 设置/更新两步验证密码与恢复邮箱 | 密码 ≥8 位 |
| `disable_2fa(account, current)` | 关闭两步验证 | 需当前密码 |
| `change_phone(account, new_phone)` | 换绑手机号 | 24h 内仅 1 次 |

**两步验证流程：**
```
未设置两步验证 → 直接设置 password + email
已设置两步验证 → 验证 current_password → 更新 password + email
```

**换绑手机号流程：**
```
SendChangePhoneCodeRequest（发送验证码到新号码）
  → 用户输入验证码
  → ChangePhoneRequest（完成换绑）
```

### 6.6 survival.py — 防封保活

**核心机制：**

| 机制 | 说明 |
|------|------|
| **频率限制** | 每账户独立 RateLimiter，默认 15 次/分钟、150 次/小时（低于 Telegram 阈值） |
| **养号期** | 新号 N 天内严格限制（5 次/分钟、30 次/小时），N 由 `warmup_days` 配置 |
| **活跃时段** | 非活跃时段仅 30% 概率执行操作，模拟真人作息 |
| **操作抖动** | 所有操作额外加 0-5 秒随机延迟 |
| **FloodWait 冷却** | 触发后 5 分钟内暂停该账户操作，并扣健康分 |
| **健康分** | 0-100 分，发送成功 +0.1，失败 -2，FloodWait -最多 20，保活 +0.5 |
| **保活心跳** | 定期读取对话 + 标记已读 + 获取自身资料，避免长时间无活动 |
| **设备指纹** | 创建客户端时随机使用 iPhone 14 Pro / Pixel 7 等主流设备参数 |

**保活流程：**
```
keepalive_loop (默认 30 分钟一次)
  └─ 对每个在线账户：
      ├─ iter_dialogs(limit=10)  拉取最近对话
      ├─ dialog.mark_read()      标记已读（模拟查看）
      ├─ human_delay(0.5, 1.5)   操作间隔
      └─ get_me()                心跳
```

**健康报告字段：**

| 字段 | 说明 |
|------|------|
| `health_score` | 0-100 健康分，低于 30 暂停操作 |
| `send_count_24h` | 24 小时内发送数 |
| `flood_wait_count` | FloodWait 总次数 |
| `last_active` | 最后活动时间 |
| `in_warmup` | 是否在养号期 |
| `warnings` | 警告列表（健康分过低/频繁 FloodWait/长时间无活动） |

## 七、防封号最佳实践

1. **新号养号**：注册后前 3 天不要群发，仅正常聊天、加入几个群、浏览频道
2. **渐进式活动**：发送量从少到多，避免突然爆发
3. **遵守频率限制**：保持每分钟 ≤15 次，每小时 ≤150 次
4. **设置两步验证**：开启后账户安全性大幅提升，被封概率降低
5. **绑定恢复邮箱**：万一被封可申诉找回
6. **保持活跃**：保活任务避免账户被判定为僵尸号
7. **避免敏感内容**：不发垃圾信息、诈骗、色情等违规内容
8. **IP 隔离**：不同账户使用不同代理 IP，避免同 IP 多账户被关联
9. **设备指纹**：保持与真实移动客户端一致的设备参数
10. **合理作息**：使用 `active_hours` 限制非活跃时段操作

## 八、常见问题

### Q1: 首次登录收不到验证码？

- 确认手机号格式正确（带国际区号，如 `+8613800138000`）
- 检查 Telegram 是否能正常收发消息
- 如使用代理，确认代理可用
- 同一手机号频繁请求会触发限流，等待 24 小时再试

### Q2: 提示 "API_ID_INVALID" / "API_HASH_INVALID"

- 检查 api_id 是否为整数（不要加引号）
- 确认 api_hash 来自同一应用
- 重新到 https://my.telegram.org 获取

### Q3: FloodWaitError 怎么处理？

Telegram 对发送频率有限制，触发后会返回需要等待的秒数。本工具会自动跳过本次请求并记录日志。建议：
- 每分钟发送不超过 20 条消息
- 群发间隔设置 ≥60 秒
- 自动回复延迟 3~8 秒模拟真人

### Q4: session 文件丢失怎么办？

需要重新登录（`python main.py login`）。建议定期备份 `sessions/` 目录。

### Q5: 如何同时管理 10+ 个账户？

- 每个账户使用独立的 api_id（同一应用可创建多个）
- 或共用同一 api_id（Telegram 允许，但有限流）
- 建议在 config.yaml 中按 enabled 分批启用
- 大规模场景考虑分布式部署（多台机器 + Redis 任务队列）

### Q6: 机器人账户能读取所有群消息吗？

不能。Bot 默认只能收到：
- @机器人 的消息
- 包含 `/` 命令的消息
- 已开启 inline privacy off 的群消息

如需读取所有群消息，需在 [@BotFather](https://t.me/BotFather) 中关闭 `Group Privacy`（`/setprivacy` → Disable）。

### Q7: 如何发送媒体文件（图片/视频）？

当前版本仅支持文本。扩展方式：

```python
await account.client.send_file(entity, '/path/to/file.jpg', caption='说明')
```

## 九、安全与合规

1. **api_id/api_hash 保密**：不要提交到公开仓库，建议加入 .gitignore
2. **session 文件保密**：等价于登录态，泄露后他人可冒充你
3. **Telegram 服务条款**：禁止滥用自动化大量发送消息，滥发可能被封号
4. **AI 回复风险**：AI 可能生成不恰当回复，建议设置关键词过滤和人工审核
5. **隐私保护**：读取的消息内容注意数据安全，遵守当地法律法规
6. **合法用途**：本工具仅供个人学习和合法业务场景使用，禁止用于违法违规场景

## 十、依赖清单

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 运行环境 |
| telethon | ≥1.34.0 | Telegram MTProto 客户端 |
| openai | ≥1.0.0 | AI 回复生成 |
| pyyaml | ≥6.0 | 配置文件解析 |
| cryptg | ≥0.4.0 | Telethon 加密加速（可选但推荐） |
| python-socks | - | SOCKS5 代理（可选） |

## 十一、参考资源

- [Telethon 官方文档](https://docs.telethon.dev)
- [Telegram API 官方文档](https://core.telegram.org/api)
- [BotFather](https://t.me/BotFather) — 创建和管理机器人
- [my.telegram.org](https://my.telegram.org) — 获取 api_id/api_hash
- [OpenAI API 文档](https://platform.openai.com/docs/api-reference)

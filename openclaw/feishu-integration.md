# OpenClaw 飞书对接指南(Docker 部署)

> 基于 OpenClaw 官方外部插件 `@openclaw/feishu`(社区维护:`@m1heng`)。
> 插件状态:生产可用(私聊 + 群聊)。
> 适用 OpenClaw 版本:`>= 2026.5.29`。

## 一、整体说明

### 1.1 传输模式

默认 **WebSocket 长连接**,无需公网回调地址,Docker 桌面机也能用。Webhook 模式可选,需要公网入口。

### 1.2 能力概览

| 能力 | 是否支持 |
|------|---------|
| 私聊 DM | ✅ |
| 群聊 | ✅(@提及默认必填) |
| 流式卡片回复 | ✅(默认 `partial`) |
| 图片 / 文件 / 音视频 | ✅ |
| 富文本 post | ⚠️ 出站不支持完整富文本 |
| 多账号 | ✅ |
| 飞书文档 / 多维表 / 云文档工具 | ✅ |
| VC 会议自动加入 | ✅(`vcAutoJoin`) |
| 动态按用户隔离 Agent | ✅(`dynamicAgentCreation`) |

### 1.3 DM 策略(`dmPolicy`)

| 值 | 行为 |
|----|------|
| `"pairing"` (默认) | 陌生人发消息收到配对码,CLI 审批 |
| `"allowlist"` | 仅白名单用户(`allowFrom` 里的 `ou_xxx`) |
| `"open"` | 任意人私聊(配置校验要求 `allowFrom` 含 `"*"`) |

### 1.4 群聊策略(`groupPolicy`)

| 值 | 行为 |
|----|------|
| `"open"` | 所有群都回 |
| `"allowlist"` (默认) | 仅 `groupAllowFrom` 或 `groups.<chat_id>` 显式列出的群 |
| `"disabled"` | 全部禁群,`groups.<chat_id>` 也不覆写 |

---

## 二、飞书开放平台侧准备

### 2.1 创建自建应用

1. 打开 https://open.feishu.cn 登录企业账号
2. 「开发者后台」→「创建企业自建应用」,填名称、描述、图标
3. 应用详情页拿到:
   - **App ID**(`cli_xxxxxxxxxxxxxxxx`)
   - **App Secret**
4. 「机器人」标签页 → 启用机器人
5. 「权限管理」最少开以下 scope:

   | Scope | 用途 |
   |-------|------|
   | `im:message` | 收发消息 |
   | `im:message.group_at_msg` | 群 @ 接收 |
   | `im:message.group_at_msg:readonly` | 群 @ 只读 |
   | `im:chat` | 群信息查询 |
   | `im:resource` | 上传下载图片/文件/音视频 |
   | `contact:user.base:readonly` | 解析用户名(可选,见 4.3) |
   | `docx:document` / `drive:drive` | 文档工具 |
   | `bitable:app` | 多维表工具 |
   | `vc:meeting.bot.join:write` | VC 会议自动加入 |

6. 「事件与回调」→「事件配置」:
   - **事件订阅方式** → 选 **长连接(WebSocket)**
   - 订阅事件:
     - `im.message.receive_v1`(消息接收,必选)
     - `drive.notice.comment_add_v1`(文档评论接收,可选)
     - `vc.bot.meeting_invited_v1`(会议邀请,可选)
7. 「版本管理」→ 创建版本 → 提交管理员审批 → 通过

### 2.2 国际版 Lark

通用 base URL 是 `https://open.larksuite.com`,插件里设 `domain: "lark"`。

---

## 三、容器内安装与配置

### 3.1 进入容器(本教程前提容器已启动)

```powershell
# Windows PowerShell
docker exec -it openclaw-gateway sh
```

进入容器后,后续命令在容器内 `/app` 路径下执行(提示符 `node@xxx:/app$`)。

### 3.2 安装插件(一次性)

```bash
# 插件属于官方外部包,ClawHub 或 npm 都可以
openclaw plugins install @openclaw/feishu
openclaw config set plugins.entries.feishu.enabled true
```

### 3.3 基础配置(非交互,推荐方式)

不用 `channels login` 交互向导,直接 `config set` 一行行写更稳:

```bash
# 基础凭证
openclaw config set channels.feishu.appId "cli_xxxxxxxxxxxxxxxx"
openclaw config set channels.feishu.appSecret "你的AppSecret"

# 域名:feishu (国内) / lark (国际)
openclaw config set channels.feishu.domain "feishu"

# 传输模式:websocket (推荐,无需公网地址) / webhook
openclaw config set channels.feishu.connectionMode "websocket"

# DM 策略
openclaw config set channels.feishu.dmPolicy "pairing"

# 群聊策略
openclaw config set channels.feishu.groupPolicy "allowlist"

# @提及:默认 true(群内需 @机器人 才回);groupPolicy=open 时默认 false
openclaw config set channels.feishu.requireMention true

# 流式回复(边生成边更新卡片)
openclaw config set channels.feishu.streaming.mode "partial"
```

### 3.4 重启网关

```bash
openclaw gateway restart
```

### 3.5 验证

```bash
# 状态
openclaw channels status

# 实时日志(看到 feishu websocket 连接成功即可)
openclaw logs --follow | grep -i feishu
```

---

## 四、私聊使用

### 4.1 第一次发消息

1. 在飞书 APP 里搜索你的机器人名称
2. 发一条消息("hi")
3. 由于 `dmPolicy: pairing`,你会收到一个配对码

把配对码在容器内批准:

```bash
openclaw pairing list feishu
openclaw pairing approve feishu <CODE>
```

### 4.2 用 allowlist 白名单模式

拿到你自己的 `ou_xxx` open_id(见 §6.1 取 ID 方法),然后:

```bash
openclaw config set channels.feishu.dmPolicy "allowlist"
openclaw config set channels.feishu.allowFrom '["ou_xxxxxxxxxxxxxxxx"]'
openclaw gateway restart
```

### 4.3 开放给公开用户

```bash
openclaw config set channels.feishu.dmPolicy "open"
openclaw config set channels.feishu.allowFrom '["*"]'
openclaw gateway restart
```

> ⚠️ 公开模式有滥用风险,建议同时开启 `dynamicAgentCreation`(见 §8)做用户隔离。

### 4.4 减少不必要的 API 调用量

```bash
openclaw config set channels.feishu.typingIndicator false
openclaw config set channels.feishu.resolveSenderNames false
openclaw gateway restart
```

(默认 `true`,会调用 typing reaction / 用户信息接口,免费额度吃紧时建议关)

---

## 五、群聊使用

### 5.1 开放所有群

```bash
openclaw config set channels.feishu.groupPolicy "open"
# 此时 requireMention 自动变为 false
openclaw gateway restart
```

### 5.2 白名单指定群

```bash
openclaw config set channels.feishu.groupPolicy "allowlist"
openclaw config set channels.feishu.groupAllowFrom '["oc_xxxx", "oc_yyyy"]'
openclaw gateway restart
```

### 5.3 在群里使用

- 把机器人加进群(飞书群设置 → 添加机器人)
- 默认需要 @机器人 才会回复
- @all 不会被识别为 @ 机器人

### 5.4 限定群内可见发言人

```json5
{
  channels: {
    feishu: {
      groupPolicy: "allowlist",
      groupAllowFrom: ["oc_xxx"],
      groups: {
        oc_xxx: {
          // 仅这些 ou_xxx 用户的消息会进 agent
          allowFrom: ["ou_user1", "ou_user2"],
          requireMention: false,
        },
      },
    },
  },
}
```

对应 CLI 写法:
```bash
openclaw config set channels.feishu.groups.oc_xxx.allowFrom '["ou_user1","ou_user2"]'
openclaw config set channels.feishu.groups.oc_xxx.requireMention false
openclaw gateway restart
```

### 5.5 群会话作用域(`groupSessionScope`)

| 值 | 会话粒度 |
|----|---------|
| `"group"` (默认) | 一个群 = 一个会话 |
| `"group_sender"` | 群+发送人 各一个会话 |
| `"group_topic"` | 话题线程 各一个会话(回退到群) |
| `"group_topic_sender"` | 话题+发送人(回退到群+发送人) |

**让回复落在话题线程里**:
```bash
openclaw config set channels.feishu.replyInThread "enabled"
openclaw gateway restart
```

---

## 六、获取 ID 速查

### 6.1 用户 `ou_xxx`

让机器人启动后,任意人 DM 机器人,然后:

```bash
openclaw logs --follow | grep -i open_id
# 或者看配对请求列表
openclaw pairing list feishu
```

### 6.2 群 `oc_xxx`

飞书 APP 打开群 → 右上角菜单 → 设置 → 群 ID(`chat_id`,格式 `oc_xxx`)。

---

## 七、机器人命令

飞书不支持原生斜杠菜单,直接把命令当文本发:

| 命令 | 作用 |
|------|------|
| `/status` | 查看 bot 状态 |
| `/reset` | 重置当前会话 |
| `/model` | 查看或切换模型 |

ACP 进阶(代码 agent):
```
/acp spawn codex --thread here
```

---

## 八、按用户隔离 Agent(公开 bot 必备)

让每个 DM 用户独享一个 agent 实例(独立 workspace、独立记忆):

```bash
# 私聊放开
openclaw config set channels.feishu.dmPolicy "open"
openclaw config set channels.feishu.allowFrom '["*"]'

# 开启动态 agent
openclaw config set channels.feishu.dynamicAgentCreation.enabled true
openclaw config set channels.feishu.dynamicAgentCreation.workspaceTemplate "~/.openclaw/workspace-{agentId}"
openclaw config set channels.feishu.dynamicAgentCreation.agentDirTemplate "~/.openclaw/agents/{agentId}/agent"

# 全局 DM 会话作用域(影响所有渠道,按需)
openclaw config set session.dmScope "main"

openclaw gateway restart
```

验证日志:
```
feishu: creating dynamic agent "feishu-ou_xxxxxx" for user ou_xxxxxx
  workspace: /home/user/.openclaw/workspace-feishu-ou_xxxxxx
  agentDir: /home/user/.openclaw/agents/feishu-ou_xxxxxx/agent
```

> ⚠️ 这是消息层的隔离,不是多租户安全边界。Agent 进程和宿主环境共享。

---

## 九、多账号配置

一台 OpenClaw 跑多个飞书机器人:

```json5
{
  channels: {
    feishu: {
      defaultAccount: "main",
      accounts: {
        main: {
          appId: "cli_AAA",
          appSecret: "secret_A",
          name: "主机器人",
        },
        backup: {
          appId: "cli_BBB",
          appSecret: "secret_B",
          name: "备用机器人",
          enabled: false,
        },
      },
    },
  },
}
```

`defaultAccount` 决定不指定账号时出站走哪个。每个账号可单独覆写 `tts`、`tools`、`domain` 等。

---

## 十、飞书工作区工具

插件内置一组 agent 可用的工具,通过 `channels.feishu.tools.*` 开关:

| 配置 key | 工具 | 默认 |
|---------|------|------|
| `tools.doc` | 飞书文档 | `true` |
| `tools.chat` | 群信息+成员 | `true` |
| `tools.wiki` | 知识库(依赖 doc) | `true` |
| `tools.drive` | 云盘 | `true` |
| `tools.perm` | 权限管理(敏感) | `false` |
| `tools.scopes` | 应用 scope 诊断 | `true` |
| `tools.bitable` | 多维表/Bitable | `true` |

关掉某些工具:
```bash
openclaw config set channels.feishu.tools.perm false
openclaw gateway restart
```

---

## 十一、Webhook 模式(可选,需要公网)

```bash
openclaw config set channels.feishu.connectionMode "webhook"
openclaw config set channels.feishu.webhookPath "/feishu/events"
openclaw config set channels.feishu.webhookHost "0.0.0.0"
openclaw config set channels.feishu.webhookPort 3000
openclaw config set channels.feishu.verificationToken "飞书开放平台给的Token"
openclaw config set channels.feishu.encryptKey "飞书开放平台给的EncryptKey"
openclaw gateway restart
```

Docker 下还需在 `docker run` 加 `-p 3000:3000`,并在飞书开放平台填回调 URL:
```
https://你的公网域名/feishu/events
```

---

## 十二、ACP 持久化绑定(代码 agent)

让某个飞书 DM/话题绑定到 codex/claude 等 ACP agent:

```json5
{
  agents: {
    list: [
      {
        id: "codex",
        runtime: {
          type: "acp",
          acp: {
            agent: "codex",
            backend: "acpx",
            mode: "persistent",
            cwd: "/workspace/openclaw",
          },
        },
      },
    ],
  },
  bindings: [
    {
      type: "acp",
      agentId: "codex",
      match: {
        channel: "feishu",
        accountId: "default",
        peer: { kind: "direct", id: "ou_1234567890" },
      },
    },
    {
      type: "acp",
      agentId: "codex",
      match: {
        channel: "feishu",
        peer: { kind: "group", id: "oc_group_chat:topic:om_topic_root" },
      },
      acp: { label: "codex-feishu-topic" },
    },
  ],
}
```

在对话里直接发:
```
/acp spawn codex --thread here
```

---

## 十三、常用排错

| 现象 | 排查 |
|------|------|
| 群里不回 | 1. 机器人已加入群 2. 默认要 @ 3. `groupPolicy` 不是 `disabled` 4. 看 `openclaw logs --follow` |
| 收不到消息 | 1. 应用已发布且通过审批 2. 事件订阅包含 `im.message.receive_v1` 3. 选择了 **长连接** 模式 4. 所需 scope 都给了 5. 网关运行中 |
| App Secret 泄露 | 1. 飞书开放平台重置 Secret 2. 更新配置 3. `openclaw gateway restart` |
| QR 配置在手机飞书 APP 不响应 | 改用人工配置:重跑 `openclaw channels login --channel feishu`,选手动模式,粘贴 App ID/Secret |
| 容器看不到二维码 | wizard 是给本机用,容器内用 `docker exec -it` 进容器跑配置命令,见 §3.3 直接 `config set` |
| 启动循环重启 | 看日志找 validation 错。`openclaw doctor --fix` 自动修 |

---

## 十四、Security 建议

### 14.1 App Secret 改用 SecretRef(不明文存配置)

```bash
openclaw secrets configure
# 按提示把 App Secret 存进 SecretRef,标识 feishu-app-secret

openclaw config set channels.feishu.appSecret '${secret:feishu-app-secret}'
openclaw gateway restart
```

### 14.2 凭证持久化(容器场景)

App Secret / OAuth token / 用户 pairing 数据存放在容器内 `~/.openclaw` / `/home/node/.openclaw`,对应宿主机你 bat 脚本挂载的目录(`D:\docker_env\openclaw`)。

**升级镜像不丢配置**,因为挂载目录是宿主机持久化的。

### 14.3 文件权限

容器内会校验 `~/.openclaw` 目录权限:
- 目录应 `chmod 700`
- `openclaw.json` 应 `chmod 600`

```bash
docker exec openclaw-gateway sh -c "chmod 700 /home/node/.openclaw && chmod 600 /home/node/.openclaw/openclaw.json"
```

Windows Docker Desktop 下一般无需手动改,WSL2 自动处理。

---

## 十五、配置速查表

| 配置项 | 说明 | 默认 |
|--------|------|------|
| `channels.feishu.enabled` | 启停渠道 | `true` |
| `channels.feishu.domain` | `feishu`/`lark`/`https://` | `feishu` |
| `channels.feishu.connectionMode` | `websocket` / `webhook` | `websocket` |
| `channels.feishu.appId` / `appSecret` | 凭证 | - |
| `channels.feishu.dmPolicy` | DM 策略 | `pairing` |
| `channels.feishu.allowFrom` | DM 白名单 (`ou_xxx`) | - |
| `channels.feishu.groupPolicy` | 群策略 | `allowlist` |
| `channels.feishu.groupAllowFrom` | 群白名单 (`oc_xxx`) | - |
| `channels.feishu.requireMention` | 群内必 @ | `true`(open 时 `false`) |
| `channels.feishu.allowBots` | 接受其他 bot @ | `false` |
| `channels.feishu.groupSessionScope` | 群会话粒度 | `group` |
| `channels.feishu.replyInThread` | 话题线程回复 | `disabled` |
| `channels.feishu.reactionNotifications` | 表情回应推送 | `own` |
| `channels.feishu.vcAutoJoin` | 会议自动加入 | `false` |
| `channels.feishu.streaming.mode` | 流式卡片 | `partial` |
| `channels.feishu.streaming.block.enabled` | 块级流式 | `false` |
| `channels.feishu.renderMode` | `auto` / `raw` / `card` | `auto` |
| `channels.feishu.textChunkLimit` | 文本切片大小 | `4000` |
| `channels.feishu.mediaMaxMb` | 媒体大小上限 | `30` |
| `channels.feishu.typingIndicator` | 输入中提示 | `true` |
| `channels.feishu.resolveSenderNames` | 解析发送者名 | `true` |
| `channels.feishu.dynamicAgentCreation.enabled` | 按用户隔离 agent | `false` |
| `channels.feishu.dynamicAgentCreation.maxAgents` | 最大动态 agent 数 | 不限 |

---

## 十六、参考

- 官方文档:https://docs.openclaw.ai/channels/feishu
- 插件包:`@openclaw/feishu`(npm / ClawHub)
- 维护者:`@m1heng`(社区维护)
- 最低 OpenClaw 版本:`2026.5.29`

# OpenClaw 工具/插件分析与推荐

> 基于 OpenClaw `2026.7.1` 容器内实际扫描结果(53/73 插件已 enabled)。
> 使用场景:飞书 + 百炼 + Docker 桌面机 + 国内使用。
> 生成日期:2026-07-21。

## 一、三个能力层次

OpenClaw 把 agent 能用的能力分三层,各自查找方式不同:

| 层次 | 是什么 | 加入方式 | 查找入口 |
|------|--------|---------|----------|
| **工具(Tools)** | agent 可调用的函数,如 `exec`、`web_search`、`browser` | 大部分内置,部分由插件提供 | https://docs.openclaw.ai/zh-CN/tools |
| **技能(Skills)** | `SKILL.md` 指令包,告诉 agent 按什么流程走 | 内置一批,工作区自定义,插件可携带 | https://docs.openclaw.ai/zh-CN/tools/skills |
| **插件(Plugins)** | 添加工具/Skills/provider/channel/钩子的可安装包 | 内置 + ClawHub + npm + git + 本地路径 | https://docs.openclaw.ai/plugins/plugin-inventory |

## 二、当前容器实际状态

### 2.1 已启用的关键插件(53 个 enabled 中的代表)

| 插件 | 作用 | 状态 |
|------|------|------|
| `feishu` | 飞书渠道(已配通) | ✅ enabled |
| `qwen` | 百炼/Qwen Token Plan provider | ✅ enabled |
| `deepseek` | DeepSeek provider | ✅ enabled |
| `moonshot` | Kimi/Moonshot provider | ✅ enabled |
| `browser` | 浏览器自动化 | ✅ enabled(但无 Chromium) |
| `memory-core` | 基础记忆 | ✅ enabled |
| `web-readability` | HTML 抽正文 | ✅ enabled |
| `document-extract` | 本地文档提取 | ✅ enabled |
| `nvidia` | NVIDIA NIM provider | ✅ enabled |
| `anthropic`、`openai`、`google`、`mistral` 等其他厂商 | 各厂 model provider | ✅ enabled(但无 key) |

### 2.2 已存在但未启用的内置插件

| 插件 ID | 作用 | 推荐度 |
|---------|------|--------|
| `duckduckgo` | 免费网络搜索(无 key) | ⭐⭐⭐⭐⭐ |
| `memory-wiki` | Obsidian 风格知识库,长期记忆 | ⭐⭐⭐⭐⭐ |
| `active-memory` | 对话时主动调记忆 | ⭐⭐⭐⭐ |
| `webhooks` | 接外部 webhook 触发 TaskFlow | ⭐⭐⭐⭐ |
| `llm-task` | JSON-only 子任务 LLM | ⭐⭐⭐ |
| `logbook` | 自动工作日志(需 paired node) | ⭐⭐ |
| `workboard` | Dashboard 看 agent 任务 | ⭐⭐ |
| `policy` | 多用户合规检查 | ⭐(单人不需要) |
| `open-prose` | `/prose` 写作 skill | ⭐⭐ |
| `telegram` | 也接 Telegram 时启 | ⭐⭐(已有飞书) |
| `migrate-claude` | 从 Claude Code 迁一次 | 🟡 一次性 |
| `bonjour` | 局域网广播发现 | ⭐(Docker 自动禁) |
| `imessage` | macOS 才用得了 | ❌ |
| `diagnostics-otel` | OTLP 排查 | 🟡 高级玩家 |
| `oc-path` | `oc://` 路径寻址 | 🟡 niche |

### 2.3 已安装但未启用的外部插件

| 插件 | 状态 | 备注 |
|------|------|------|
| `deepseek-provider`、`moonshot-provider`、`qwen-provider` | 已装+已启 | ok |
| `codex`、`codex-supervisor` | 已装未启 | OpenAI Codex 专用,用不到 |

## 三、按优先级的推荐清单

### 优先级 1:立刻启用(纯配置,无 key,无依赖)

```bash
# 1. 免费联网搜索(DuckDuckGo,无需 API key)
openclaw config set plugins.entries.duckduckgo.enabled true

# 2. 长期记忆 - Obsidian 风格知识库
openclaw config set plugins.entries.memory-wiki.enabled true

# 3. 对话时主动检索记忆注入
openclaw config set plugins.entries.active-memory.enabled true

# 4. 让外部服务(GitHub/CI/脚本)通过 webhook 触发 agent
openclaw config set plugins.entries.webhooks.enabled true

# 5. 让 agent 能调用一个 JSON-only LLM 做子任务
openclaw config set plugins.entries.llm-task.enabled true

# 重启生效
openclaw gateway restart
```

### 优先级 2:从 ClawHub/npm 装(免费/带 quota)

```bash
# 代码 diff 渲染(在飞书卡片里好看)
openclaw plugins install @openclaw/diffs

# AI 优化搜索,比 DuckDuckGo 准(免费 1000 次/月,需 key)
# 去https://tavily.com 注册免费 key,然后:
openclaw plugins install @openclaw/tavily-plugin
# openclaw config set secrets.entries.TAVILY_API_KEY 'xxx' 或者在 .env 加

# 整站抓取 + 网站爬取(研究场景)
openclaw plugins install @openclaw/firecrawl-plugin

# 向量记忆库(大量记忆时比 memory-wiki 强,需装依赖)
openclaw plugins install @openclaw/memory-lancedb

# 类型化工作流 + 可恢复审批(复杂任务流)
openclaw plugins install @openclaw/lobster

# 每个装完都要重启网关
openclaw gateway restart
```

### 优先级 3:可选

| 插件 | 何时开 |
|------|------|
| `telegram` | 也想接 Telegram 时 |
| `logbook` | 想让机器人自动记录你一天做了什么(需 paired node) |
| `workboard` | 想在 Dashboard 看 agent-owned issues |
| `policy` | 多人共享 gateway 时做合规检查 |
| `open-prose` | 写作助手 skill |

### 优先级 4:浏览器能力(需要时再上)

当前镜像是普通 `latest`(没 Chromium),要用 `browser` 工具实操网页需要:

**方案 A:换镜像(推荐,一键到位)**
修改 `run_openclaw.bat` 里:
```bat
set IMAGE=ghcr.io/openclaw/openclaw:latest-browser
```
重新拉镜像起容器即可,自带 Chromium + Xvfb。

**方案 B:在已启用的容器里手动装**
```bash
docker exec -it openclaw-gateway sh
node /app/node_modules/playwright-core/cli.js install chromium
exit
# 或者挂 OPENCLAW_HOME_VOLUME 持久化,避免升级丢失
```

## 四、对话级别常用工具(不用装,直接用)

这部分是 OpenClaw 内置,**直接发消息让 agent 调用**,不用专门启用:

| 工具 | 用法(在飞书 DM 里发) |
|------|------|
| `exec` | "跑一下 `ls -la /home/node`" |
| `read` / `write` / `edit` / `apply_patch` | "在工作区读/改 xxx 文件" |
| `web_search` | "搜一下 XXX 最新进展"(需装 duckduckgo/tavily) |
| `web_fetch` | "抓取这个 URL 的正文:https://xxx" |
| `browser` | "打开 xxx 网站帮我截图"(需 Chromium) |
| `image` | "识别一下这张图:..."(需支持视觉的模型,如 `qwen3.7-plus`) |
| `image_generate` | "画一张 ...(描述)"(需图像 provider,如 fal) |
| `video_generate` | "生成一段视频 ...(需 video provider) |
| `tts` | "把这段话转成语音"(需 TTS provider) |
| `message` | 让 agent 主动给某渠道发消息 |
| `cron` | "每天早上 9 点提醒我 ...(自动化) |
| `sessions_*` / `subagents` | 让 agent 派子任务给其他 agent |
| `tool_search` | OpenClaw 工具太多时,agent 自己查找用 |

## 五、Skill 查找与使用

### 5.1 看当前 agent 可用的 skills
```bash
docker exec openclaw-gateway openclaw skills list --agent main
```

### 5.2 看某个 skill 详情
```bash
docker exec openclaw-gateway openclaw skills info <name> --agent main
```

### 5.3 让 agent 用 skill
在飞书 DM 里直接说:
```
用 xxx skill 帮我做 ...
```

### 5.4 写自己的 skill
- 创建:https://docs.openclaw.ai/zh-CN/tools/creating-skills
- 半自动生成:https://docs.openclaw.ai/zh-CN/tools/skill-workshop
- 配置项:https://docs.openclaw.ai/zh-CN/tools/skills-config

### 5.5 Skill 来源
1. 工作区 `~/.openclaw/workspace/SKILL.md`
2. 共享 skill 目录
3. 插件包携带
4. 托管 OpenClaw Skill 根目录

## 六、自动化能力(进阶)

| 能力 | 文档 | 用途 |
|------|------|------|
| **Cron 定时** | https://docs.openclaw.ai/zh-CN/automation | 定时跑任务 / 提醒 |
| **Heartbeat** | https://docs.openclaw.ai/zh-CN/automation | 周期性主动汇报 |
| **Hooks** | https://docs.openclaw.ai/zh-CN/automation | 命令/消息生命周期钩子 |
| **TaskFlow** | https://docs.openclaw.ai/zh-CN/automation | 多步状态机工作流 |
| **Subagents** | https://docs.openclaw.ai/zh-CN/tools/subagents | 一个会话里派多个 agent 并行干 |
| **Agent send** | https://docs.openclaw.ai/zh-CN/tools/agent-send | agent 之间发消息 |
| **ACP Agents** | https://docs.openclaw.ai/zh-CN/tools/acp-agents | 接 Codex/Claude Code 等 ACP harness |

## 七、常用诊断命令

```bash
# 看所有插件
docker exec openclaw-gateway openclaw plugins list

# 看插件运行时实际注册的工具/钩子
docker exec openclaw-gateway openclaw plugins inspect <id> --runtime --json

# 看 agent 可用 skills
docker exec openclaw-gateway openclaw skills list --agent main

# 搜 ClawHub 公开插件
docker exec openclaw-gateway openclaw plugins search "<关键词>"

# 看当前 session 列表
docker exec openclaw-gateway openclaw sessions list --agent main

# 健康检查
docker exec openclaw-gateway openclaw doctor

# 配置校验
docker exec openclaw-gateway openclaw config validate
```

## 八、文档入口总览

| 主题 | URL |
|------|-----|
| 工具概览(从这里开始) | https://docs.openclaw.ai/zh-CN/tools |
| 工具策略配置 | https://docs.openclaw.ai/zh-CN/gateway/config-tools |
| Skills 总览 | https://docs.openclaw.ai/zh-CN/tools/skills |
| Skills 创建 | https://docs.openclaw.ai/zh-CN/tools/creating-skills |
| Skills 工作坊 | https://docs.openclaw.ai/zh-CN/tools/skill-workshop |
| Skills 配置 | https://docs.openclaw.ai/zh-CN/tools/skills-config |
| 插件入门 | https://docs.openclaw.ai/zh-CN/tools/plugin |
| 构建插件 | https://docs.openclaw.ai/zh-CN/plugins/building-plugins |
| 插件清单(全 141 个) | https://docs.openclaw.ai/plugins/plugin-inventory |
| 插件 SDK | https://docs.openclaw.ai/zh-CN/plugins/sdk-overview |
| 插件 manifest | https://docs.openclaw.ai/zh-CN/plugins/manifest |
| 自动化总览 | https://docs.openclaw.ai/zh-CN/automation |
| 子 agent | https://docs.openclaw.ai/zh-CN/tools/subagents |
| ACP agents | https://docs.openclaw.ai/zh-CN/tools/acp-agents |
| Agent send | https://docs.openclaw.ai/zh-CN/tools/agent-send |
| 工具搜索 | https://docs.openclaw.ai/zh-CN/tools/tool-search |
| 浏览器工具 | https://docs.openclaw.ai/zh-CN/tools/browser |
| Exec 工具 | https://docs.openclaw.ai/zh-CN/tools/exec |
| 代码执行 | https://docs.openclaw.ai/zh-CN/tools/code-execution |
| Web 工具 | https://docs.openclaw.ai/zh-CN/tools/web |
| Web 获取 | https://docs.openclaw.ai/zh-CN/tools/web-fetch |
| 媒体概览 | https://docs.openclaw.ai/zh-CN/tools/media-overview |

## 九、按场景的推荐组合

### 9.1 「飞书智能助手」最小有用集
- `duckduckgo`(联网)
- `memory-wiki`(长期记忆)
- `webhooks`(让自定义脚本触发 bot)
- `active-memory`(主动调记忆)

### 9.2 「研发助手」加分项
- `@openclaw/diffs`(代码 diff 渲染)
- `@openclaw/tavily-plugin`(更准的搜索)
- `@openclaw/firecrawl-plugin`(文档/网站抓取)
- 镜像换 `latest-browser`(浏览器自动化)

### 9.3 「记忆密集型」
- `memory-core`(已有)+ `memory-wiki`(知识库)+ `@openclaw/memory-lancedb`(向量检索)
- `active-memory`(主动调)

### 9.4 「自动化中枢」
- `webhooks`(外部触发)
- 内置 `cron`(定时)
- 内置 `heartbeat_respond`(周期互动)
- `@openclaw/lobster`(复杂工作流)

### 9.5 「公开多用户服务」
- 飞书 `dynamicAgentCreation.enabled: true`(按用户隔离 agent)
- `@openclaw/memory-lancedb`(向量记忆)
- `active-memory`(主动调)
- `policy`(合规检查)
- 飞书 `dmPolicy: "open"` + `allowFrom: ["*"]`

## 十、装新插件的通用流程

```bash
# 1. 容器内装(任选一种来源)
openclaw plugins install clawhub:@openclaw/<name>
openclaw plugins install npm:@openclaw/<name>
openclaw plugins install git:github.com/<owner>/<repo>@<ref>
openclaw plugins install ./my-plugin      # 本地开发
openclaw plugins install --link ./my-plugin

# 2. 大多数情况 setup.sh 会自动加到 plugins.allow 并启用
# 如果没自动启用:
openclaw config set plugins.entries.<id>.enabled true

# 3. 重启网关
openclaw gateway restart

# 4. 验证
openclaw plugins inspect <id> --runtime --json
```

## 十一、安全提示

1. **插件 = 代码,装前确认来源可信**。OpenClaw 在非交互模式下装新源需要 `--force`,即为了让你审一下
2. **API key 不要写明文在 `openclaw.json`**,用 SecretRef:
   ```bash
   openclaw secrets configure
   ```
3. **多用户场景必须开 `dynamicAgentCreation` + `dmScope: per-channel-peer`**,否则别人的对话别人能搜到
4. **公网暴露 gateway 前**看 https://docs.openclaw.ai/zh-CN/gateway/security

## 十二、参考

- OpenClaw 官方文档:https://docs.openclaw.ai
- ClawHub(社区插件发现):https://docs.openclaw.ai/clawhub
- 你当前容器镜像:`ghcr.io/openclaw/openclaw:latest`(2026.7.1)
- 本次扫描时已启用插件数:53/73
- 你已配置的渠道:飞书(`feishu`)
- 你已配置的 provider:`qwen`(百烈)、`nvidia`(NIM)

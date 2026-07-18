# OpenClaw 行政办公场景实战指南

> 面向行政人员的实战教程,从安装到上手,以表格、PPT、PDF、文档生成、即时通讯对接五大场景为主线,提供可复制的完整操作步骤
>
> 知识来源:本指南整合自 [01-Windows安装配置卸载指南](./01-Windows安装配置卸载指南.md) 与 [02-行政办公场景模型选择与配置](./02-行政办公场景模型选择与配置.md),将原本分散在两篇中的"安装+配置+场景"按实战步骤重新编排,便于一次性跟着做完整套行政办公落地。

---

## 目录

1. [实战目标与适用场景](#一实战目标与适用场景)
2. [第一步:环境准备与安装](#二第一步环境准备与安装)
3. [第二步:配置行政办公模型](#三第二步配置行政办公模型)
4. [第三步:安装办公技能](#四第三步安装办公技能)
5. [第四步:表格处理实战](#五第四步表格处理实战)
6. [第五步:PPT 制作实战](#六第五步ppt-制作实战)
7. [第六步:PDF 处理实战](#七第六步pdf-处理实战)
8. [第七步:文档转换与生成实战](#八第七步文档转换与生成实战)
9. [第八步:接入企业即时通讯](#九第八步接入企业即时通讯)
10. [第九步:成本与安全优化](#十第九步成本与安全优化)
11. [第十步:常见问题排查](#十一第十步常见问题排查)
12. [附录:速查表](#附录速查表)

---

## 一、实战目标与适用场景

### 1.1 目标

用 OpenClaw 搭建一个 7×24 小时在线的行政办公 AI 助手,实现:

- 表格自动生成、统计、图表、批量合并
- PPT 自动生成与排版
- PDF 转换、合并、拆分、OCR、加水印
- Word/PDF/Excel/PPT 格式互转
- 公文、通知、合同、会议纪要自动生成
- 接入企业微信/钉钉/飞书,在群里 @机器人 完成所有文档操作

### 1.2 适用场景

| 场景 | 具体需求 | 推荐技能 |
|------|----------|----------|
| 表格处理 | 数据统计、汇总报表、考勤表、费用报销表、图表生成 | excel、excel-magic |
| PPT 制作 | 工作汇报、方案展示、培训课件、会议纪要转 PPT | ppt-generator、doc-assistant |
| PDF 处理 | PDF 转 Word/Excel、合并拆分、加水印、OCR 识别、提取表格 | pdf-convert-edit、nutrient-openclaw |
| 文档转换 | Word ↔ PDF ↔ Excel ↔ PPT 格式互转 | file-converter、doc-assistant |
| 文档生成 | 自动生成周报、合同、通知、方案、会议纪要 | doc-assistant、document-pro |
| 批量操作 | 批量格式转换、批量提取内容、批量替换文字 | file-converter、doc-assistant |

### 1.3 前置准备清单

- Windows 10 1903+ 或 Windows 11(也支持 macOS / Linux)
- 至少一个 AI 服务商 API 密钥(推荐先备阿里云通义千问)
- 如需接入 IM:企业微信 / 钉钉 / 飞书 任一管理员账号
- 如用 Docker 部署:Docker Desktop 已安装

---

## 二、第一步:环境准备与安装

OpenClaw 在 Windows 上有三条安装路线,行政场景推荐 WSL2 或 Docker。

### 2.1 路线选型

| 路线 | 适用 | 优劣 |
|------|------|------|
| A:WSL2 安装(官方推荐) | 想要稳定完整体验 | 兼容性最好,需重启一次 |
| B:原生 Windows 安装 | 只跑本机 CLI,快速试用 | 步骤少,稳定性略逊 |
| C:Docker 安装 | 生产/长期使用、多机部署 | 环境隔离干净,可迁移 |

### 2.2 路线 A:WSL2 安装(推荐)

**第 1 步:以管理员身份打开 PowerShell,安装 WSL2**

```powershell
wsl --install
```

该命令会自动启用 WSL 与虚拟机平台功能,并安装 Ubuntu。完成后重启电脑,按提示设置 Ubuntu 用户名和密码。

**第 2 步:在 WSL2(Ubuntu 终端)中安装 OpenClaw**

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

脚本会自动检测 Node、安装 CLI 与依赖,并启动初始化向导。

如需无交互安装(自动化场景):

```bash
curl -fsSL https://openclaw.ai/install.sh | bash -s -- --no-onboard
```

### 2.3 路线 B:原生 Windows 安装

**第 1 步:以管理员身份打开 PowerShell**

开始菜单搜索 `PowerShell` → 右键 → "以管理员身份运行" → UAC 弹窗点"是"。

**第 2 步:解锁脚本执行权限**

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**第 3 步:执行安装命令**

```powershell
iwr -useb https://openclaw.ai/install.ps1 | iex
```

- `iwr` = `Invoke-WebRequest`,下载安装脚本
- `-useb` = 使用 TLS 加密
- `iex` = `Invoke-Expression`,执行脚本

安装脚本会自动检测 Node(缺失时安装 Node 24)、安装 CLI、启动初始化向导。

跳过自动引导(可选):

```powershell
& ([scriptblock]::Create((iwr -useb https://openclaw.ai/install.ps1))) -NoOnboard
```

### 2.4 路线 C:Docker 安装(生产推荐)

**第 1 步:安装 Docker Desktop**

下载 [Docker Desktop](https://www.docker.com/products/docker-desktop/),安装时勾选 "Use WSL 2 instead of Hyper-V",完成后重启。验证:

```powershell
docker --version
docker compose version
```

**第 2 步:在任意目录创建两个文件**

`docker-compose.yml`:

```yaml
services:
  openclaw-gateway:
    image: ghcr.io/openclaw/openclaw:latest
    container_name: openclaw-gateway
    restart: unless-stopped
    ports:
      - "18789:18789"
    volumes:
      - ./openclaw-data:/root/.openclaw
      - ./workspace:/workspace
    env_file:
      - .env
    environment:
      - TZ=Asia/Shanghai
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:18789/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
```

`.env`(同目录):

```env
# API 密钥(按需填写)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
ZHIPU_API_KEY=xxxxxxxxxxxxxxxx
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# 主目录(容器内路径,一般无需修改)
OPENCLAW_HOME=/root/.openclaw
```

**第 3 步:启动并初始化**

```powershell
docker compose up -d
# 首次使用:进入容器运行 onboard 初始化向导
docker exec -it openclaw-gateway openclaw onboard
# 验证
docker compose ps
curl http://localhost:18789/health
```

> 修改 `.env` 后必须 `docker compose up -d --force-recreate` 重建容器才能生效,数据保留在 `./openclaw-data` 不会丢失。

### 2.5 初始化向导(onboard)

无论选哪条路线,首次启动都要运行一次 onboard:

```powershell
openclaw onboard
```

向导会引导完成:
1. Gateway(网关)配置 — 监听地址、端口(默认 18789)
2. Provider(提供商)选择 — OpenAI / Qwen / GLM / DeepSeek / Ollama 等
3. Model(模型)选择 — 如 `qwen-max`、`glm-4-plus`
4. Workspace(工作区)设置
5. Channels(频道)连接
6. Skills(技能)安装

### 2.6 验证安装

```powershell
openclaw --version
openclaw doctor
openclaw gateway start
```

`openclaw doctor` 会检查环境配置是否正确,并给出修复建议。

### 2.7 配置文件位置

| 部署方式 | 配置目录 |
|----------|----------|
| 原生 / WSL2 | `~/.openclaw/`(Windows 下为 `C:\Users\<用户名>\.openclaw\`) |
| docker run | 宿主机 `C:\openclaw\` → 容器内 `/root/.openclaw/` |
| docker compose | 宿主机 `.\openclaw-data\` → 容器内 `/root/.openclaw/` |

关键文件:
- `.env` — API 密钥、提供商设置
- `config.yaml` 或 `openclaw.json` — 网关、技能、频道配置
- `skills/` — 已安装技能
- `workspaces/` — 工作区数据

> 密钥仅存储在本地,不会发送到除 AI 提供商以外的任何地方。

---

## 三、第二步:配置行政办公模型

### 3.1 模型选择原则

行政办公场景对模型的核心要求:
- **中文理解能力强** — 通知、公文、合同等中文语境
- **指令遵循精准** — 格式、模板、排版要求严格
- **长文本处理** — 合同、报告等长文档
- **成本可控** — 日常高频使用,需平衡效果与费用

### 3.2 推荐模型对比

| 模型 | 提供商 | 中文能力 | 长文本 | 成本 | 推荐场景 |
|------|--------|----------|--------|------|----------|
| `qwen-max` | 阿里云通义千问 | ★★★★★ | ★★★★ | 低 | **首选**,中文公文/通知/合同生成 |
| `qwen-plus` | 阿里云通义千问 | ★★★★☆ | ★★★ | 极低 | 日常表格处理、简单文档 |
| `deepseek-chat` | DeepSeek | ★★★★ | ★★★★ | 低 | 复杂推理、数据分析 |
| `deepseek-r1` | DeepSeek | ★★★★ | ★★★★★ | 中 | 复杂报表逻辑、多步推理 |
| `glm-4-plus` | 智谱 GLM | ★★★★★ | ★★★★ | 低 | 中文写作、公文润色 |
| `claude-sonnet-4-5` | Anthropic | ★★★★ | ★★★★★ | 高 | 复杂长文档、精细排版 |
| `gpt-5.2` | OpenAI | ★★★★ | ★★★★ | 高 | 综合能力强,通用场景 |
| `moonshot-v1-128k` | Kimi | ★★★★ | ★★★★★ | 低 | 超长文档处理(128K 上下文) |
| `minimax/MiniMax-M2.5` | MiniMax | ★★★★ | ★★★★ | 低 | 性价比高,日常办公 |

### 3.3 场景化模型方案

**方案 1:日常文档处理(首选性价比)**

```
主模型:qwen-max(中文最强,价格低)
回退模型:deepseek-chat
```
适合:通知撰写、表格生成、PDF 转换、简单 PPT

**方案 2:复杂报表与数据分析**

```
主模型:deepseek-r1(推理能力强)
回退模型:qwen-max
```
适合:多表联动统计、费用分析、考勤异常检测

**方案 3:长文档/合同处理**

```
主模型:moonshot-v1-128k(128K 上下文)
回退模型:claude-sonnet-4-5
```
适合:合同审查、长报告汇总、多文档对比

**方案 4:精细排版与高质量输出**

```
主模型:claude-sonnet-4-5(排版指令遵循最好)
回退模型:gpt-5.2
```
适合:重要汇报 PPT、正式公文、对外方案

### 3.4 编辑主配置文件

编辑 `~/.openclaw/openclaw.json`(JSON5 格式,支持注释):

```json5
{
  // 模型配置
  agents: {
    defaults: {
      model: {
        // 主模型:通义千问 Max,中文行政场景首选
        primary: "qwen-max",
        // 回退模型:主模型不可用时依次尝试
        fallbacks: ["deepseek-chat", "glm-4-plus"],
      },
      models: {
        "qwen-max": { alias: "千问Max" },
        "deepseek-chat": { alias: "DeepSeek" },
        "glm-4-plus": { alias: "智谱GLM" },
        "moonshot-v1-128k": { alias: "Kimi长文本" },
        "claude-sonnet-4-5": { alias: "Claude" },
      },
    },
  },

  // 模型提供商配置
  models: {
    providers: {
      qwen: {
        baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
        apiKey: "${DASHSCOPE_API_KEY}",
      },
      deepseek: {
        baseUrl: "https://api.deepseek.com/v1",
        apiKey: "${DEEPSEEK_API_KEY}",
      },
      zhipu: {
        baseUrl: "https://open.bigmodel.cn/api/paas/v4",
        apiKey: "${ZHIPU_API_KEY}",
      },
      moonshot: {
        baseUrl: "https://api.moonshot.cn/v1",
        apiKey: "${MOONSHOT_API_KEY}",
      },
    },
  },

  // 工作区
  agent: {
    workspace: "~/.openclaw/workspace",
  },
}
```

### 3.5 配置 API 密钥

编辑 `~/.openclaw/.env`:

```env
# === 国内模型 API 密钥 ===

# 阿里云通义千问(必配,主模型)
# 获取地址:https://dashscope.console.aliyun.com/
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx

# DeepSeek(推荐配置,回退模型)
# 获取地址:https://platform.deepseek.com/
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# 智谱 GLM(可选配置)
# 获取地址:https://open.bigmodel.cn/
ZHIPU_API_KEY=xxxxxxxxxxxxxxxx

# Moonshot / Kimi(长文档场景推荐)
# 获取地址:https://platform.moonshot.cn/
MOONSHOT_API_KEY=sk-xxxxxxxxxxxxxxxx

# === 海外模型 API 密钥(可选) ===
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### 3.6 CLI 快速切换模型

```powershell
# 查看可用模型列表
openclaw models list

# 设置主模型
openclaw models set qwen-max

# 切换到 DeepSeek
openclaw models set deepseek-chat

# 切换到长文本模型处理合同
openclaw models set moonshot-v1-128k

# 切换到精细排版模型做重要 PPT
openclaw models set claude-sonnet-4-5

# 查看当前模型状态
openclaw models status
```

### 3.7 按任务临时切换模型

无需修改配置文件,直接在对话中指定:

```
@qwen-max 帮我写一份关于端午节放假的通知
@deepseek-r1 分析这份考勤表中的异常数据
@moonshot-v1-128k 阅读这份50页的合同,提取关键条款
@claude-sonnet-4-5 制作一份季度工作汇报 PPT,要求排版精美
```

### 3.8 让配置生效

```powershell
openclaw gateway restart
openclaw models status
```

---

## 四、第三步:安装办公技能

### 4.1 必装技能(行政场景最小集)

```powershell
# 文档全能助手 — 格式互转、摘要、纠错
openclaw skill install doc-assistant

# Excel 魔法大师 — 数据清洗、图表、公式
openclaw skill install excel-magic

# PDF 处理神器 — 转换、合并、拆分、OCR、水印
openclaw skill install pdf-convert-edit

# 文件格式转换 — 50+ 格式互转
openclaw skill install file-converter

# PPT 生成器 — 自动生成演示文稿
openclaw skill install ppt-generator

# 文档专业版 — PDF/DOCX/PPTX/XLSX 深度处理
openclaw skill install document-pro
```

### 4.2 推荐补充技能

```powershell
# Excel 基础操作 — 读写编辑 xlsx 文件
openclaw skill install excel

# Excel 周报仪表盘 — 自动生成可刷新的 Excel 仪表盘
openclaw skill install excel-weekly-dashboard

# Nutrient PDF — 高级 PDF 处理(数字签名、PII 脱敏、OCR)
openclaw skill install nutrient-openclaw

# Office 综合技能 — Word/Excel/PPT 操作指导
openclaw skill install office
```

### 4.3 技能管理

```powershell
# 列出所有已安装技能
openclaw skill list

# 查看技能详情
openclaw skill info excel-magic

# 更新技能
openclaw skill update excel-magic

# 卸载不需要的技能
openclaw skill uninstall nutrient-openclaw
```

---

## 五、第四步:表格处理实战

适用模型:`qwen-max`(日常)或 `deepseek-r1`(复杂统计)
适用技能:`excel`、`excel-magic`、`excel-weekly-dashboard`

### 5.1 场景 1:从零生成费用报销统计表

**步骤:**

1. 切换到日常模型:

```powershell
openclaw models set qwen-max
```

2. 直接给指令:

```
帮我制作一份月度费用报销统计表,包含日期、部门、费用类型、金额、备注列,
并按部门汇总合计金额,生成柱状图
```

3. OpenClaw 会调用 `excel-magic` 技能生成 `.xlsx` 文件,保存到工作区 `~/.openclaw/workspace/`。

### 5.2 场景 2:考勤异常检测

**步骤:**

1. 切换到推理模型:

```powershell
openclaw models set deepseek-r1
```

2. 上传考勤表后给指令:

```
读取这份考勤表,统计每人迟到次数和缺勤天数,标记异常记录,
生成一份考勤异常汇总表
```

### 5.3 场景 3:多表合并汇总

```
把这三个 Excel 文件的数据合并到一张总表里,
按日期排序,去除重复项,添加小计和合计行
```

### 5.4 场景 4:周报仪表盘

```powershell
# 先安装周报仪表盘技能(若未安装)
openclaw skill install excel-weekly-dashboard
```

```
根据本周工作日志生成一份周报仪表盘,包含任务完成率柱状图、
工时占比饼图、本周亮点与问题清单
```

> 技巧:复杂表格明确指定"生成 xlsx 格式文件",避免 Markdown 表格输出。

---

## 六、第五步:PPT 制作实战

适用模型:`qwen-max`(日常)或 `claude-sonnet-4-5`(重要汇报)
适用技能:`ppt-generator`、`doc-assistant`

### 6.1 场景 1:季度工作汇报 PPT

**步骤:**

1. 重要汇报切换到精细排版模型:

```powershell
openclaw models set claude-sonnet-4-5
```

2. 给出详细结构指令:

```
制作一份2026年Q1行政工作汇报PPT,10页左右,
包含:封面、目录、工作概述、重点项目、费用分析、团队建设、下季度计划、结尾
风格简洁专业,使用蓝色主题
```

### 6.2 场景 2:会议纪要转 PPT

```
根据这份会议纪要文档,生成一份5页的汇报PPT,
重点突出决议事项和责任人
```

### 6.3 PPT 排版不理想的处理

1. 提供更详细的排版要求(主题色、字体、每页内容)
2. 用 `ppt-generator` 生成结构化大纲,再手动调整
3. 重要 PPT 用 `claude-sonnet-4-5`,排版指令遵循更好

---

## 七、第六步:PDF 处理实战

适用模型:`qwen-max` 或 `moonshot-v1-128k`(超长 PDF)
适用技能:`pdf-convert-edit`、`nutrient-openclaw`

### 7.1 场景 1:多份 PDF 合并

```
把这5份PDF合同合并成一个文件,并在每份合同之间插入分页标签
```

### 7.2 场景 2:扫描版 PDF OCR 转 Word

```
将这份扫描版PDF进行OCR识别,提取所有文字内容,
然后转换为可编辑的Word文档
```

> 中文 OCR 不准时,在指令中指定语言:"对这份中文PDF进行OCR识别"。`nutrient-openclaw` 支持多语言 OCR。

### 7.3 场景 3:PDF 加水印与密码

```
给这份PDF文件添加"内部文件"水印,并设置打开密码为123456
```

### 7.4 场景 4:从 PDF 年报提取财务数据

```
把这份PDF年报中的财务数据提取出来,生成一份Excel表格,
包含收入、支出、利润三列,并按季度汇总
```

---

## 八、第七步:文档转换与生成实战

适用模型:`qwen-max`、`glm-4-plus`(公文润色)
适用技能:`doc-assistant`、`file-converter`、`document-pro`

### 8.1 场景 1:Word 转 PDF 并发送

```
把这份Word通知转换为PDF格式,并发送到指定邮箱
```

### 8.2 场景 2:按要点生成标准合同

```
根据以下要点,生成一份标准格式的劳动合同:
1. 甲方:XX科技有限公司
2. 乙方:张三
3. 合同期限:2026年1月1日至2028年12月31日
4. 岗位:行政专员
5. 月薪:8000元
```

### 8.3 场景 3:放假通知撰写

```
@qwen-max 根据以下内容生成放假通知:端午节6月28日-30日放假3天
```

### 8.4 场景 4:格式批量互转

```
把这个文件夹下的所有 docx 文件批量转换为 PDF,
保持原文件名,输出到 output 子目录
```

---

## 九、第八步:接入企业即时通讯

将 OpenClaw 接入 IM,实现 24 小时在线 AI 助手,员工在群里 @机器人 即可完成文档处理。

### 9.1 平台选型

| 平台 | 插件名称 | 连接方式 | 适用场景 |
|------|----------|----------|----------|
| 企业微信 | `wecom` / `wecom-app` | Webhook 回调 | 企业内部办公首选 |
| 钉钉 | `dingtalk` | Stream 长连接 | 钉钉生态企业首选 |
| 飞书 / Lark | `feishu` | WebSocket 长连接 | 字节系企业首选 |
| QQ | `qqbot` / `napcat` | QQ 开放平台 / NapCat | 小团队/个人使用 |

### 9.2 企业微信对接(完整步骤)

**第 1 步:注册企业微信**

1. 访问 [企业微信官网](https://work.weixin.qq.com),用个人微信扫码注册
2. 填写企业名称、手机号,**无需营业执照**,几分钟即可完成
3. 登录 [企业微信管理后台](https://work.weixin.qq.com/wework_admin/)

**第 2 步:创建自建应用**

1. 左侧导航「应用管理 → 应用 → 自建 → 创建应用」
2. 填写应用名称(如"OpenClaw AI 助手"),上传 Logo
3. 可见范围选"全部员工",点击创建
4. 进入应用详情页,记录以下凭证:
   - **AgentId** — 应用 ID
   - **CorpSecret** — 应用密钥
   - **CorpId** — 在「我的企业」页面获取

**第 3 步:配置接收消息**

1. 在应用详情页,进入「接收消息」
2. 设置回调 URL:`https://你的域名/channels/wecom/webhook`
3. 随机生成 **Token** 和 **EncodingAESKey**,记录下来
4. 保存配置

**第 4 步:安装插件并配置**

```powershell
# 安装企业微信插件
openclaw plugins install @openclaw-china/channels

# 或安装独立企业微信插件
openclaw plugins install @m1heng-clawd/wework
```

编辑 `~/.openclaw/openclaw.json`,在 `channels` 中添加:

```json5
{
  channels: {
    wecom: {
      enabled: true,
      corpId: "ww你的企业ID",
      agentId: "你的应用AgentId",
      secret: "${WECOM_SECRET}",
      token: "${WECOM_TOKEN}",
      encodingAESKey: "${WECOM_ENCODING_AES_KEY}",
      webhookPath: "/wecom/webhook",
      // 消息策略:仅响应白名单用户
      dmPolicy: "allowlist",
      groupPolicy: "allowlist",
    },
  },
}
```

在 `~/.openclaw/.env` 中添加:

```env
WECOM_SECRET=你的应用Secret
WECOM_TOKEN=你设置的Token
WECOM_ENCODING_AES_KEY=你设置的EncodingAESKey
```

**第 5 步:重启网关并验证**

```powershell
openclaw gateway restart
openclaw channels status
```

在企业微信中找到自建应用,发送消息测试。

### 9.3 钉钉对接(完整步骤)

**第 1 步:创建钉钉企业内部应用**

1. 访问 [钉钉开放平台](https://open-dev.dingtalk.com/)
2. 创建企业内部应用,获取 **Client ID** 和 **Client Secret**
3. 添加「机器人」能力,消息接收选择 **Stream 模式**(无需公网 URL)
4. 发布应用版本,设置可见范围

**第 2 步:安装插件并配置**

```powershell
openclaw plugins install @openclaw-china/channels
# 或
openclaw plugins install dingtalk
```

编辑 `~/.openclaw/openclaw.json`:

```json5
{
  channels: {
    dingtalk: {
      enabled: true,
      clientId: "ding你的ClientID",
      clientSecret: "${DINGTALK_CLIENT_SECRET}",
      robotCode: "ding你的RobotCode",
      // Stream 模式,无需公网 IP
      streamMode: true,
      dmPolicy: "allowlist",
      groupPolicy: "mention",  // 群聊中仅响应 @机器人 的消息
    },
  },
}
```

在 `~/.openclaw/.env` 中添加:

```env
DINGTALK_CLIENT_SECRET=你的ClientSecret
```

**第 3 步:重启并验证**

```powershell
openclaw gateway restart
openclaw channels status
```

在钉钉中 @机器人 发送消息测试。

### 9.4 飞书 / Lark 对接(完整步骤)

**第 1 步:创建飞书应用**

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 创建企业自建应用,记录 **App ID** 和 **App Secret**
3. 添加「机器人」能力
4. 开启事件订阅,选择 **WebSocket 长连接模式**(无需公网 URL)
5. 添加事件:`im.message.receive_v1`(接收消息)
6. 发布应用版本

**第 2 步:安装插件并配置**

```powershell
openclaw plugins install @openclaw/feishu
```

编辑 `~/.openclaw/openclaw.json`:

```json5
{
  channels: {
    feishu: {
      enabled: true,
      appId: "你的AppID",
      appSecret: {
        source: "env",
        id: "FEISHU_APP_SECRET",
      },
      // WebSocket 长连接模式(推荐,无需公网 URL)
      connectionMode: "websocket",
      dmPolicy: "allowlist",
      groupPolicy: "mention",
      // 国际版 Lark 用户需设置域名
      // domain: "lark",
    },
  },
}
```

在 `~/.openclaw/.env` 中添加:

```env
FEISHU_APP_SECRET=你的AppSecret
```

**第 3 步:重启并验证**

```powershell
openclaw gateway restart
openclaw channels status
```

### 9.5 QQ 对接

**方式一:QQ 开放平台(官方)**

1. 访问 [QQ 开放平台](https://q.qq.com/),手机 QQ 扫码登录
2. 创建机器人,记录 **App ID** 和 **App Secret**
3. 配置:

```powershell
openclaw channels add --channel qqbot --token "AppID:AppSecret"
```

或手动编辑 `~/.openclaw/openclaw.json`:

```json5
{
  channels: {
    qqbot: {
      enabled: true,
      appId: "你的AppID",
      appSecret: "${QQ_APP_SECRET}",
    },
  },
}
```

**方式二:NapCat(个人 QQ 号接入,无需企业认证)**

1. 安装 [NapCat](https://github.com/NapNeko/NapCatQQ)
2. 启动 NapCat 并配置 HTTP API
3. 编辑 `~/.openclaw/openclaw.json`:

```json5
{
  channels: {
    napcat: {
      enabled: true,
      httpApi: "http://127.0.0.1:3000",
      accessToken: "你的NapCat Token",
      selfId: "你的QQ号",
    },
  },
}
```

### 9.6 多渠道同时启用

行政场景可同时启用多个渠道:

```json5
{
  channels: {
    // 企业微信 — 内部正式沟通
    wecom: {
      enabled: true,
      corpId: "ww你的企业ID",
      agentId: "你的AgentId",
      secret: "${WECOM_SECRET}",
      token: "${WECOM_TOKEN}",
      encodingAESKey: "${WECOM_ENCODING_AES_KEY}",
    },
    // 钉钉 — 项目组沟通
    dingtalk: {
      enabled: true,
      clientId: "ding你的ClientID",
      clientSecret: "${DINGTALK_CLIENT_SECRET}",
      robotCode: "ding你的RobotCode",
      streamMode: true,
    },
    // 飞书 — 跨部门协作
    feishu: {
      enabled: true,
      appId: "你的AppID",
      appSecret: {
        source: "env",
        id: "FEISHU_APP_SECRET",
      },
      connectionMode: "websocket",
    },
  },
}
```

对应 `.env`:

```env
WECOM_SECRET=xxx
WECOM_TOKEN=xxx
WECOM_ENCODING_AES_KEY=xxx
DINGTALK_CLIENT_SECRET=xxx
FEISHU_APP_SECRET=xxx
```

### 9.7 IM 中的行政实战

在企业微信/钉钉/飞书中 @机器人 即可使用:

```
@OpenClaw 帮我生成一份本周的会议纪要汇总
@OpenClaw 把这份PDF转为Word文档发给我
@OpenClaw 制作一份Q1费用分析表格
@OpenClaw 根据以下内容生成放假通知:端午节6月28日-30日放假3天
@OpenClaw 查询上个月的办公用品采购明细
```

**群聊使用技巧:**
- 钉钉/飞书默认仅响应 `@机器人` 的消息,避免干扰正常群聊
- 可配置 `groupPolicy: "all"` 让机器人响应群内所有消息(慎用)
- 可设置白名单,仅允许特定群组使用

### 9.8 渠道管理命令

```powershell
# 查看所有渠道状态
openclaw channels status

# 交互式添加渠道
openclaw channels add

# 添加指定渠道
openclaw channels add --channel wecom --corp-id "xxx" --agent-id "xxx" --corp-secret "xxx"

# 禁用某个渠道
openclaw channels disable wecom

# 启用某个渠道
openclaw channels enable wecom

# 重启网关使配置生效
openclaw gateway restart
```

---

## 十、第九步:成本与安全优化

### 10.1 成本优化策略

| 策略 | 说明 |
|------|------|
| 日常用国产模型 | `qwen-max`、`deepseek-chat` 价格远低于海外模型 |
| 简单任务用轻量模型 | `qwen-plus` 处理简单表格和文档,成本极低 |
| 仅重要场景用海外模型 | 正式汇报 PPT、对外方案才用 Claude/GPT |
| 利用回退机制 | 主模型失败时自动切换,避免重试浪费 |

### 10.2 效率优化:定时任务

在 `openclaw.json` 中添加自动化配置:

```json5
{
  automation: {
    // 定时任务:每周一 9 点自动生成上周工作汇总
    cron: [
      {
        schedule: "0 9 * * 1",
        prompt: "汇总上周所有工作文档,生成周报",
        model: "qwen-max",
      },
    ],
  },
}
```

### 10.3 安全注意事项

- API 密钥仅存储在本地 `~/.openclaw/.env`,不会外传
- 涉及敏感文件(合同、人事信息)时,建议使用本地模型(Ollama)
- PDF 添加水印和密码保护,防止内部文件外泄

**本地模型部署(完全离线,数据不出本机):**

```powershell
# 安装 Ollama:https://ollama.com/download
ollama pull qwen2.5:7b

# 在 OpenClaw 中切换到本地模型
openclaw models set ollama/qwen2.5:7b
```

### 10.4 升级与卸载

**升级:**

```powershell
npm install -g openclaw@latest
# 或
openclaw update
```

**卸载(重要:先停网关):**

```powershell
# 1. 停止网关服务
openclaw gateway stop

# 2. 卸载网关服务
openclaw gateway uninstall

# 3. 一键全自动卸载
openclaw uninstall --all --yes --non-interactive
```

Docker 部署的卸载:

```powershell
docker compose down
docker rmi openclaw:local
docker rmi ghcr.io/openclaw/openclaw:latest
```

---

## 十一、第十步:常见问题排查

### Q1:生成表格格式混乱怎么办?

明确指定输出格式,如"生成 xlsx 格式文件"或"使用 Markdown 表格格式"。复杂表格建议用 `excel-magic` 技能直接生成 Excel 文件。

### Q2:PPT 生成后排版不理想?

1. 提供更详细的排版要求(主题色、字体、每页内容)
2. 用 `ppt-generator` 生成结构化大纲,再手动调整
3. 重要 PPT 用 `claude-sonnet-4-5` 模型,排版指令遵循更好

### Q3:PDF OCR 识别中文不准?

在指令中指定语言,如"对这份中文PDF进行OCR识别"。`nutrient-openclaw` 支持多语言 OCR。

### Q4:国内模型 API 调用不稳定?

配置回退模型,主模型不可用时自动切换:

```json5
{
  agents: {
    defaults: {
      model: {
        primary: "qwen-max",
        fallbacks: ["deepseek-chat", "glm-4-plus"],
      },
    },
  },
}
```

### Q5:处理大文件时超时?

1. 用长上下文模型:`moonshot-v1-128k` 支持 128K 上下文
2. 拆分大文件后分批处理
3. 在配置中调整超时时间

### Q6:PowerShell 执行策略报错?

以管理员身份运行 PowerShell,执行:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q7:Node.js 版本不兼容?

确保 Node ≥ 22.16,推荐 Node 24:

```powershell
winget install OpenJS.NodeJS.LTS
```

### Q8:WSL2 安装后无法启动?

1. 确认 BIOS 中已启用虚拟化(VT-x / AMD-V)
2. 运行 `wsl --update` 更新 WSL
3. 运行 `wsl --status` 检查状态

### Q9:Docker 构建时 OOM(退出码 137)?

1. Docker Desktop → Settings → Resources 中将内存调至至少 2GB
2. 或使用预构建镜像跳过本地构建:`docker pull ghcr.io/openclaw/openclaw:latest`

### Q10:企业微信回调 URL 验证失败?

1. 确认网关已启动且公网可访问:`openclaw gateway status`
2. 检查回调 URL 是否正确填写在企微后台
3. 确认 Token 和 EncodingAESKey 与配置文件一致
4. 如无公网 IP,可使用 ngrok 等内网穿透工具

### Q11:钉钉机器人收不到消息?

1. 确认应用已发布并设置可见范围
2. 确认选择了 Stream 模式(无需公网 URL)
3. 检查 `clientSecret` 是否正确
4. 运行 `openclaw channels status` 查看渠道连接状态

### Q12:飞书机器人不响应群聊消息?

1. 确认已添加 `im.message.receive_v1` 事件订阅
2. 确认群聊中 @机器人 发送消息(`groupPolicy: "mention"`)
3. 检查机器人是否已加入目标群组
4. 确认应用版本已发布

---

## 附录:速查表

### A. 安装命令速查

| 路线 | 命令 |
|------|------|
| WSL2 安装 | `curl -fsSL https://openclaw.ai/install.sh \| bash` |
| 原生 Windows | `iwr -useb https://openclaw.ai/install.ps1 \| iex` |
| Docker 拉取镜像 | `docker pull ghcr.io/openclaw/openclaw:latest` |
| 初始化向导 | `openclaw onboard` |
| 验证安装 | `openclaw doctor` |

### B. 模型 CLI 速查

| 操作 | 命令 |
|------|------|
| 查看模型列表 | `openclaw models list` |
| 设置主模型 | `openclaw models set <model>` |
| 查看当前状态 | `openclaw models status` |
| 对话中临时切换 | `@<model> 你的指令` |

### C. 技能 CLI 速查

| 操作 | 命令 |
|------|------|
| 安装技能 | `openclaw skill install <name>` |
| 列出已装技能 | `openclaw skill list` |
| 查看技能详情 | `openclaw skill info <name>` |
| 更新技能 | `openclaw skill update <name>` |
| 卸载技能 | `openclaw skill uninstall <name>` |

### D. 渠道 CLI 速查

| 操作 | 命令 |
|------|------|
| 查看渠道状态 | `openclaw channels status` |
| 交互式添加 | `openclaw channels add` |
| 禁用渠道 | `openclaw channels disable <name>` |
| 启用渠道 | `openclaw channels enable <name>` |
| 重启网关 | `openclaw gateway restart` |

### E. 行政场景模型选择速查

| 场景 | 主模型 | 回退模型 |
|------|--------|----------|
| 日常文档/通知/表格 | qwen-max | deepseek-chat |
| 复杂报表/数据分析 | deepseek-r1 | qwen-max |
| 长文档/合同审查 | moonshot-v1-128k | claude-sonnet-4-5 |
| 精细排版/重要 PPT | claude-sonnet-4-5 | gpt-5.2 |
| 公文润色/中文写作 | glm-4-plus | qwen-max |

### F. 必装技能速查

| 技能 | 用途 |
|------|------|
| doc-assistant | 文档格式互转、摘要、纠错 |
| excel-magic | Excel 数据清洗、图表、公式 |
| pdf-convert-edit | PDF 转换、合并、拆分、OCR、水印 |
| file-converter | 50+ 格式互转 |
| ppt-generator | 自动生成 PPT |
| document-pro | PDF/DOCX/PPTX/XLSX 深度处理 |

### G. 参考链接

- 官方安装文档:https://docs.openclaw.ai/install/index
- 官方中文文档:https://openclaws.io/zh/docs/install
- 官方配置文档:https://docs.openclaw.ai/gateway/configuration
- GitHub 仓库:https://github.com/openclaw/openclaw
- 技能市场 ClawHub:https://clawhub.com
- 阿里云百炼平台:https://dashscope.console.aliyun.com/
- DeepSeek 开放平台:https://platform.deepseek.com/
- 智谱 AI 开放平台:https://open.bigmodel.cn/
- Moonshot 平台:https://platform.moonshot.cn/
- 企业微信管理后台:https://work.weixin.qq.com/wework_admin/
- 钉钉开放平台:https://open-dev.dingtalk.com/
- 飞书开放平台:https://open.feishu.cn/app
- QQ 开放平台:https://q.qq.com/
- NapCat 项目:https://github.com/NapNeko/NapCatQQ
- Ollama 下载:https://ollama.com/download

# OpenClaw Windows 安装、配置与卸载指南

> 基于官方文档整理，适用于 Windows 10（1903+）及 Windows 11

---

## 一、系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 1903+ 或 Windows 11 |
| Node.js | Node 24（推荐）；Node 22 LTS（22.16+）仍兼容支持 |
| 内存 | ≥ 4GB（推荐 8GB+） |
| 磁盘 | ~500 MB（安装及依赖） |
| 网络 | 需联网调用 AI API；本地模型（Ollama）可离线运行 |
| 可选 | Python 3.10+（部分技能需要）、Git（源码构建需要） |

> **官方建议**：Windows 上强烈推荐在 WSL2 下运行 OpenClaw，兼容性和稳定性更好。原生 Windows 也支持，但 WSL2 体验更完整。

---

## 二、安装方式

Windows 上有三条安装路线：

- **路线 A：WSL2 安装（官方推荐）** — 兼容性更完整，CLI、Gateway、工具链更稳定
- **路线 B：原生 Windows 安装** — 适合只想快速跑起来做本机 CLI 操作的用户
- **路线 C：Docker 安装** — 容器化部署，环境隔离干净，适合生产/长期使用

---

### 路线 A：WSL2 安装（推荐）

#### 1. 安装 WSL2

以管理员身份打开 PowerShell，执行：

```powershell
wsl --install
```

此命令会自动启用 WSL 和虚拟机平台功能，并安装 Ubuntu 作为默认发行版。安装完成后**重启电脑**。

重启后，按提示设置 Ubuntu 的用户名和密码。

#### 2. 在 WSL2 中安装 OpenClaw

打开 WSL 终端（Ubuntu），执行：

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

脚本会自动检测 Node、安装 CLI 和依赖，并启动初始化向导。

如需跳过自动引导（无交互安装）：

```bash
curl -fsSL https://openclaw.ai/install.sh | bash -s -- --no-onboard
```

---

### 路线 B：原生 Windows 安装

#### 1. 以管理员身份运行 PowerShell

- 点击"开始"菜单，搜索 `PowerShell`
- 右键点击"Windows PowerShell"，选择 **"以管理员身份运行"**
- 在 UAC 弹窗中点击"是"

#### 2. 解锁脚本执行权限

Windows 默认禁止运行远程脚本，需先授权：

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

或仅对当前会话生效：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

#### 3. 执行安装命令

```powershell
iwr -useb https://openclaw.ai/install.ps1 | iex
```

命令解释：
- `iwr` → `Invoke-WebRequest`，下载安装脚本
- `-useb` → 使用 TLS 加密
- `iex` → `Invoke-Expression`，执行脚本内容

安装脚本会自动：
- 检测 Node.js 环境（缺失时自动安装 Node 24）
- 安装 OpenClaw CLI
- 启动初始化向导（onboard）

#### 4. 跳过自动引导（可选）

```powershell
& ([scriptblock]::Create((iwr -useb https://openclaw.ai/install.ps1))) -NoOnboard
```

---

### 路线 C：Docker 安装

适合希望容器化部署、环境隔离的用户，也是生产环境和长期使用的推荐方式。

#### 1. 安装 Docker Desktop

1. 下载 [Docker Desktop](https://www.docker.com/products/docker-desktop/) 安装程序
2. 双击运行安装程序，**确保勾选 "Use WSL 2 instead of Hyper-V"**（推荐）
3. 安装完成后重启电脑
4. 启动 Docker Desktop，等待引擎就绪（托盘图标变为稳定状态）

验证安装：

```powershell
docker --version
docker compose version
```
自定义自己的OPENCLAW_GATEWAY_TOKEN
```shell
[BitConverter]::ToString([byte[]](1..32 | % {Get-Random -Maximum 256})).Replace("-","").ToLower()
```
#### 2. 方式一：使用预构建镜像（快速启动）

直接拉取官方预构建镜像并运行：

```powershell
# 拉取镜像
docker pull ghcr.io/openclaw/openclaw:latest

# 创建配置目录
mkdir C:\openclaw

# 运行容器
docker run -d ^
  --name openclaw-gateway ^
  -p 18789:18789 ^
  -v C:\openclaw:/root/.openclaw ^
  ghcr.io/openclaw/openclaw:latest
```

Gateway 默认运行在端口 **18789**，配置通过 bind mount 持久化到 `C:\openclaw` 目录。

#### 3. 方式二：Docker Compose 部署（推荐生产/长期使用）

适合长期部署，配置文件可固化，方便后续修改与迁移。

**步骤 a：克隆仓库**

```powershell
git clone https://github.com/openclaw/openclaw.git
cd openclaw
```

**步骤 b：使用官方 setup 脚本**

```bash
# 在 WSL 或 Git Bash 中运行
./scripts/docker/setup.sh
```

该脚本会自动完成三件事：
1. 检查并获取环境变量
2. 根据 Dockerfile 构建网关镜像
3. 根据 docker-compose.yml 启动网关容器

如需使用预构建镜像而非本地构建：

```bash
export OPENCLAW_IMAGE="ghcr.io/openclaw/openclaw:latest"
./scripts/docker/setup.sh
```

**步骤 c：手动流程（compose）**

如果不使用 setup 脚本，也可以手动操作：

```bash
# 构建镜像
docker build -t openclaw:local -f Dockerfile .

# 运行 onboard 初始化
docker compose run --rm openclaw-cli onboard

# 启动网关
docker compose up -d openclaw-gateway
```

> **注意**：从仓库根目录运行 `docker compose ...` 命令。

#### 4. Docker 环境变量

| 变量 | 说明 |
|------|------|
| `OPENCLAW_DOCKER_APT_PACKAGES` | 构建时安装额外的 apt 包 |
| `OPENCLAW_EXTRA_MOUNTS` | 添加额外的 Docker 挂载卷 |
| `OPENCLAW_IMAGE` | 指定使用的镜像（默认本地构建） |

#### 5. Docker 资源要求

| 项目 | 要求 |
|------|------|
| 内存 | 至少 2GB（1GB 主机构建时可能 OOM，退出码 137） |
| 磁盘 | 足够空间用于镜像 + 日志 |
| Docker | Docker Desktop + Docker Compose v2 |

#### 6. Docker 容器初始化（首次启动必须）

直接 `docker run` 启动容器时会报错 "Missing config"，因为容器内缺少配置文件。必须先执行初始化引导：

```powershell
# 创建配置目录（路径与 run_openclaw.bat 中 CONFIG_DIR 一致）
mkdir D:\docker_env\openclaw

# 第一步：运行初始化引导（交互式，按提示配置 API 密钥等）
docker run -it --rm -v D:\docker_env\openclaw:/root/.openclaw ghcr.io/openclaw/openclaw:latest openclaw onboard

# 第二步：启动 Gateway
docker run -d --name openclaw-gateway -p 18789:18789 -v D:\docker_env\openclaw:/root/.openclaw ghcr.io/openclaw/openclaw:latest
```

也可以使用项目中的启动脚本，自动完成检测和初始化：

```powershell
# 脚本会自动检测是否需要 onboard，首次运行自动引导
d:\work\ai_blog\openclaw\docker\run_openclaw.bat
```

#### 7. 验证 Docker 部署

```powershell
# 检查容器状态
docker ps

# 查看网关日志
docker logs openclaw-gateway

# 测试网关连通性
curl http://localhost:18789/health
```

#### 8. Docker 常用管理命令

```powershell
# 停止容器
docker compose down
# 或直接
docker stop openclaw-gateway

# 重启容器
docker compose restart
# 或直接
docker restart openclaw-gateway

# 查看日志
docker compose logs -f openclaw-gateway
# 或直接
docker logs -f openclaw-gateway

# 更新镜像并重启
docker pull ghcr.io/openclaw/openclaw:latest
docker stop openclaw-gateway
docker rm openclaw-gateway
docker run -d --name openclaw-gateway -p 18789:18789 -v D:\docker_env\openclaw:/root/.openclaw ghcr.io/openclaw/openclaw:latest
```

---

#### 9. Docker 容器内操作指南

Docker 部署后，配置和操作有三种方式，可混合使用：

方式一：Dashboard（浏览器控制界面）— 可视化操作，适合日常使用

```powershell
# Gateway 启动后，浏览器打开
http://localhost:18789/

# 或通过 CLI 命令打开
docker exec -it openclaw-gateway openclaw dashboard
```

Dashboard 功能：聊天对话、模型切换、渠道状态查看、执行审批。首次访问如提示认证，输入 `gateway.auth.token`（在 .env 中配置的 `OPENCLAW_GATEWAY_TOKEN`）。

方式二：CLI 命令（docker exec）— 适合安装插件、技能等需要校验的操作

```powershell
docker exec -it openclaw-gateway openclaw <子命令>
```

方式三：直接编辑配置文件 — 最快捷，适合批量修改

配置目录已通过 bind mount 映射到 `D:\docker_env\openclaw`，可直接在 Windows 上用编辑器修改 `openclaw.json` 和 `.env`，修改后重启容器生效。

> 下方统一用 `CONFIG_DIR` 指代 `D:\docker_env\openclaw`。

##### 9.1 模型配置

通过 Dashboard：打开 http://localhost:18789/ ，在设置中切换模型。

通过 CLI：

```powershell
# 查看可用模型
docker exec -it openclaw-gateway openclaw models list

# 设置主模型
docker exec -it openclaw-gateway openclaw models set qwen-max

# 切换模型
docker exec -it openclaw-gateway openclaw models set deepseek-chat

# 查看当前模型状态
docker exec -it openclaw-gateway openclaw models status
```

通过编辑配置文件：

编辑 `CONFIG_DIR\openclaw.json`，按 02-行政办公场景模型选择与配置.md 中的格式添加模型配置；编辑 `CONFIG_DIR\.env` 添加 API 密钥。修改后重启容器生效：

```powershell
docker restart openclaw-gateway
```

##### 9.2 模型提供商配置（含 NVIDIA NIM）

国内模型提供商（qwen、deepseek、zhipu 等）在 02-行政办公场景模型选择与配置.md 中有详细说明。此处补充 NVIDIA NIM 的配置方法。

NVIDIA NIM 通过 `https://integrate.api.nvidia.com/v1` 提供 OpenAI 兼容 API，当前免费使用（有 40 RPM 速率限制），适合作为回退模型。

**获取 API Key**：访问 https://build.nvidia.com/settings/api-keys 创建。

**.env 添加**：

```env
# NVIDIA NIM
NVIDIA_API_KEY=nvapi-你的密钥
```

**openclaw.json 在 models.providers 中添加**：

```json5
nvidia: {
  baseUrl: "https://integrate.api.nvidia.com/v1",
  api: "openai-completions",
  apiKey: "${NVIDIA_API_KEY}",
}
```

**NVIDIA 可用模型（均免费）**：

| 模型 ID | 说明 | 上下文长度 |
|---------|------|-----------|
| `nvidia/nvidia/nemotron-3-ultra-550b-a55b` | 推理能力最强，默认推荐 | 1M |
| `nvidia/nvidia/nemotron-3-super-120b-a12b` | 较轻量 | 1M |
| `nvidia/deepseek-ai/deepseek-v4-pro` | DeepSeek V4 Pro | 262K |
| `nvidia/qwen/qwen3.5-397b-a17b` | Qwen3.5 | 262K |
| `nvidia/z-ai/glm-5.2` | 智谱 GLM 5.2 | 202K |
| `nvidia/moonshotai/kimi-k2.6` | Kimi K2.6 | 262K |
| `nvidia/minimaxai/minimax-m3` | MiniMax M3 | 196K |

**设为主模型或回退模型**：

```json5
agents: {
  defaults: {
    model: {
      primary: "qwen-max",
      fallbacks: ["nvidia/nvidia/nemotron-3-ultra-550b-a55b", "deepseek-chat"],
    },
  },
},
```

> NVIDIA 免费层有 40 RPM 限制，建议作为回退模型使用，不推荐做高频调用的主模型。

##### 9.3 技能安装

```powershell
# 安装技能
docker exec -it openclaw-gateway openclaw skill install excel-magic

# 查看已安装技能
docker exec -it openclaw-gateway openclaw skill list

# 更新技能
docker exec -it openclaw-gateway openclaw skill update excel-magic

# 卸载技能
docker exec -it openclaw-gateway openclaw skill uninstall excel-magic
```

##### 9.4 渠道对接（钉钉、企业微信、飞书等）

渠道对接有三种配置方式，效果相同：

方式一：通过 Dashboard

打开 http://localhost:18789/ ，在设置中找到 Channels，按提示添加渠道凭证。

方式二：通过 CLI 交互式配置

```powershell
# 交互式添加渠道（按提示输入凭证）
docker exec -it openclaw-gateway openclaw channels add

# 添加指定渠道
docker exec -it openclaw-gateway openclaw channels add --channel dingtalk --client-id "xxx" --client-secret "xxx"

# 查看渠道状态
docker exec -it openclaw-gateway openclaw channels status

# 启用/禁用渠道
docker exec -it openclaw-gateway openclaw channels enable dingtalk
docker exec -it openclaw-gateway openclaw channels disable dingtalk

# 重启网关使配置生效
docker restart openclaw-gateway
```

方式三：直接编辑配置文件

1. 编辑 `CONFIG_DIR\openclaw.json`，添加 channels 配置（参考 02-行政办公场景模型选择与配置.md 第五章）
2. 编辑 `CONFIG_DIR\.env`，添加对应的 API 密钥
3. 安装渠道插件：

```powershell
# 安装国内渠道插件包（包含钉钉、企业微信、飞书）
docker exec -it openclaw-gateway openclaw plugins install @openclaw-china/channels
```

4. 重启容器：

```powershell
docker restart openclaw-gateway
```

5. 验证渠道连接：

```powershell
docker exec -it openclaw-gateway openclaw channels status
```

以钉钉为例的完整流程：

```powershell
# 1. 在钉钉开放平台 https://open-dev.dingtalk.com/ 创建企业内部应用
#    获取 Client ID 和 Client Secret
#    添加「机器人」能力，消息接收选 Stream 模式（无需公网 URL）
#    发布应用版本，设置可见范围
#    详细步骤参考 02-行政办公场景模型选择与配置.md 5.3 节

# 2. 编辑 CONFIG_DIR\.env，添加钉钉密钥
#    DINGTALK_CLIENT_SECRET=你的ClientSecret

# 3. 编辑 CONFIG_DIR\openclaw.json，添加钉钉渠道配置
#    channels: {
#      dingtalk: {
#        enabled: true,
#        clientId: "ding你的ClientID",
#        clientSecret: "${DINGTALK_CLIENT_SECRET}",
#        robotCode: "ding你的RobotCode",
#        streamMode: true,
#        dmPolicy: "allowlist",
#        groupPolicy: "mention",
#      },
#    }

# 4. 安装渠道插件
docker exec -it openclaw-gateway openclaw plugins install @openclaw-china/channels

# 5. 重启容器
docker restart openclaw-gateway

# 6. 验证
docker exec -it openclaw-gateway openclaw channels status

# 7. 在钉钉中 @机器人 发送消息测试
```

##### 9.5 插件管理

```powershell
# 安装插件
docker exec -it openclaw-gateway openclaw plugins install <插件名>

# 查看已安装插件
docker exec -it openclaw-gateway openclaw plugins list

# 更新插件
docker exec -it openclaw-gateway openclaw plugins update <插件名>

# 卸载插件
docker exec -it openclaw-gateway openclaw plugins uninstall <插件名>
```

##### 9.6 网关管理

```powershell
# 查看网关状态
docker exec -it openclaw-gateway openclaw gateway status

# 重启网关（等同于 docker restart）
docker exec -it openclaw-gateway openclaw gateway restart

# 查看网关日志
docker logs -f openclaw-gateway

# 健康检查
docker exec -it openclaw-gateway openclaw doctor

# 打开 Dashboard
docker exec -it openclaw-gateway openclaw dashboard
```

##### 9.7 容器重建注意事项

更新镜像或重建容器时，配置不会丢失（持久化在 D:\docker_env\openclaw），但已安装的插件和技能可能会丢失。建议：

1. 重建前备份配置目录：`xcopy D:\docker_env\openclaw D:\docker_env\openclaw_backup\ /E /I`
2. 重建后重新安装插件和技能
3. 或通过 Dockerfile 构建自定义镜像，预装所需插件

---

### 备选安装方式：npm / pnpm

如果你已经自行管理 Node.js 环境，可以直接用包管理器安装：

```powershell
# npm
npm install -g openclaw@latest

# pnpm
pnpm add -g openclaw@latest
```

安装完成后手动启动引导：

```powershell
openclaw onboard
```

---

## 三、基本配置

### 1. 初始化引导（onboard）

安装完成后，运行初始化向导：

```powershell
openclaw onboard
```

也可指定模型提供商直接引导：

```powershell
# 国内用户：阿里云百炼（DashScope 中国北京端点）
openclaw onboard --auth-choice modelstudio-api-key-cn

# 国际用户：阿里云百炼（新加坡端点）
openclaw onboard --auth-choice modelstudio-api-key

# NVIDIA NIM
openclaw onboard --auth-choice nvidia-api-key
```

向导会逐步引导你完成：
- Gateway（网关）配置
- Workspace（工作区）设置
- Channels（频道）连接
- Skills（技能）安装

> 注意：旧版 `qwen-portal` OAuth 集成已于 v2026.3.24 移除，必须使用百炼 API Key 方式接入。

### 2. 配置文件位置

所有配置存储在用户目录下：

```
C:\Users\<用户名>\.openclaw\
```

关键文件：
- `openclaw.json` — 主配置文件（JSON5 格式，支持注释），包含模型、渠道、网关设置
- `.env` — 环境变量文件，存储 API 密钥
- 配置文件中的密钥仅存储在本地，不会发送到除 AI 提供商以外的任何地方

### 3. 添加 API 密钥

编辑 `~/.openclaw/.env` 文件，添加你的 API 密钥：

```env
# === 阿里云百炼（DashScope）===
# 获取地址：https://bailian.console.aliyun.com/ → API Key 管理
# 中国大陆用户使用北京端点，Key 以 sk- 开头
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx

# === NVIDIA NIM（免费）===
# 获取地址：https://build.nvidia.com/settings/api-keys
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxx

# === 其他国内服务商 ===
# DeepSeek
# 获取地址：https://platform.deepseek.com/
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# 智谱 GLM
# 获取地址：https://open.bigmodel.cn/
ZHIPU_API_KEY=xxxxxxxxxxxxxxxx

# === 海外服务商（可选）===
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
```

国内用户推荐的 AI 服务商：
- 阿里云百炼：https://bailian.console.aliyun.com/ （推荐，千问系列模型首选）
- DeepSeek：https://platform.deepseek.com/
- 智谱 GLM：https://open.bigmodel.cn/
- NVIDIA NIM：https://build.nvidia.com/ （免费，适合回退模型）

### 4. 阿里云百炼端点说明

阿里云百炼已从旧版 DashScope 域名迁移至 WorkspaceId 专属域名，性能和稳定性更好。

| 地区 | Base URL | 适合人群 |
|------|----------|----------|
| 中国北京 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | 中国大陆用户（兼容旧域名） |
| 中国北京（推荐） | `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1` | 中国大陆用户（专属域名，性能更优） |
| 新加坡 | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | 国际用户、出海用户 |
| 美国弗吉尼亚 | `https://dashscope-us.aliyuncs.com/compatible-mode/v1` | 北美用户 |

> 注意：不同地区的 API Key 相互独立，不能跨地区使用。Base URL、API Key 和模型必须属于同一地区。
> WorkspaceId 在百炼控制台「业务空间详情」页面查看。

### 5. 环境变量

常用环境变量：

| 变量 | 说明 |
|------|------|
| `OPENCLAW_HOME` | 主目录路径 |
| `OPENCLAW_STATE_DIR` | 覆盖状态目录路径 |
| `OPENCLAW_CONFIG_PATH` | 覆盖配置文件路径 |
| `OPENCLAW_GATEWAY_TOKEN` | Dashboard 认证令牌 |

### 6. 启动网关

```powershell
openclaw gateway start
```

### 7. 验证安装

```powershell
openclaw --version
openclaw doctor
```

`openclaw doctor` 会检查环境配置是否正确，并给出修复建议。

---

## 四、升级 OpenClaw

```powershell
# 使用 npm 升级
npm install -g openclaw@latest

# 或使用内置命令
openclaw update
```

---

## 五、卸载 OpenClaw

> **重要前提**：不管用哪种方式卸载，**先停止并卸载网关服务**，否则会有后台进程残留！

### 第一步：停止网关服务

```powershell
openclaw gateway stop
```

### 第二步：卸载网关服务

```powershell
openclaw gateway uninstall
```

### 第三步：选择卸载方式

#### 方式一：一键全自动卸载（推荐）

以管理员身份运行 PowerShell：

```powershell
openclaw uninstall --all --yes --non-interactive
```

此命令会自动删除所有已安装的技能，并清理相关的配置数据。

#### 方式二：手动卸载

```powershell
# 卸载 CLI 工具
npm uninstall -g openclaw
```

如需彻底清理配置文件（谨慎操作）：

```powershell
# 删除配置目录
rmdir /s /q C:\Users\%USERNAME%\.openclaw
```

#### 多 profile / dev 环境场景

```powershell
openclaw uninstall --dev --profile foo
```

#### Docker 部署的卸载

```powershell
# 停止并删除容器
docker compose down

# 删除本地镜像
docker rmi openclaw:local
docker rmi ghcr.io/openclaw/openclaw:latest

# 清理配置目录（谨慎操作）
rmdir /s /q D:\docker_env\openclaw
```

如需彻底清理 Docker 资源（包括未使用的镜像、容器、网络）：

```powershell
docker system prune -a
```

```shell
# 绑定移动端
docker exec openclaw-gateway sh -c "openclaw qr --host 192.168.137.1"

docker exec openclaw-gateway openclaw devices approve f081ca3d-a529-4f6e-87c3-eb34306574a3

docker exec openclaw-gateway openclaw nodes pending 
```
---

## 六、常见问题

### Q1：PowerShell 执行策略报错

```
无法加载文件，因为在此系统上禁止运行脚本
```

**解决**：以管理员身份运行 PowerShell，执行：

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q2：Node.js 版本不兼容

**解决**：安装脚本会自动处理。如手动安装，确保 Node ≥ 22.16，推荐 Node 24。

```powershell
# 使用 winget 安装 Node
winget install OpenJS.NodeJS.LTS
```

### Q3：WSL2 安装后无法启动

**解决**：
1. 确认 BIOS 中已启用虚拟化（VT-x / AMD-V）
2. 运行 `wsl --update` 更新 WSL
3. 运行 `wsl --status` 检查状态

### Q4：网络连接问题（国内用户）

**解决**：配置镜像源或代理，编辑 `~/.openclaw/.env` 添加代理设置。

### Q5：Docker 构建时 OOM（内存不足，退出码 137）

**解决**：
1. 在 Docker Desktop → Settings → Resources 中将内存调至至少 2GB
2. 或使用预构建镜像跳过本地构建：`docker pull ghcr.io/openclaw/openclaw:latest`

### Q6：Docker 容器无法访问宿主机网络

**解决**：
1. 确认 Docker Desktop 的网络设置为默认的 NAT 模式
2. 在容器内使用 `host.docker.internal` 访问宿主机服务
3. 检查 Windows 防火墙是否放行了 Docker 相关端口

---

## 参考链接

- 官方安装文档：https://docs.openclaw.ai/install/index
- 官方中文文档：https://openclaws.io/zh/docs/install
- GitHub 仓库：https://github.com/openclaw/openclaw

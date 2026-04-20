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

#### 6. 验证 Docker 部署

```powershell
# 检查容器状态
docker ps

# 查看网关日志
docker logs openclaw-gateway

# 测试网关连通性
curl http://localhost:18789/health
```

#### 7. Docker 常用管理命令

```powershell
# 停止容器
docker compose down

# 重启容器
docker compose restart

# 查看日志
docker compose logs -f openclaw-gateway

# 更新镜像并重启
docker pull ghcr.io/openclaw/openclaw:latest
docker compose up -d openclaw-gateway
```

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

向导会逐步引导你完成：
- Gateway（网关）配置
- Workspace（工作区）设置
- Channels（频道）连接
- Skills（技能）安装

### 2. 配置文件位置

所有配置存储在用户目录下：

```
C:\Users\<用户名>\.openclaw\
```

关键文件：
- `.env` — 主配置文件，包含 API 密钥、提供商设置等
- 配置文件中的密钥仅存储在本地，不会发送到除 AI 提供商以外的任何地方

### 3. 添加 API 密钥

编辑 `~/.openclaw/.env` 文件，添加你的 API 密钥：

```env
# 示例：使用 OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

# 示例：使用国内服务商
# 阿里云 Qwen（DashScope）
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx

# 智谱 GLM
ZHIPU_API_KEY=xxxxxxxxxxxxxxxx
```

国内用户推荐的 AI 服务商：
- **阿里云 Qwen**：通过 [DashScope 百炼平台](https://dashscope.console.aliyun.com/) 创建 API-KEY
- **智谱 GLM**：在 [智谱 AI 开放平台](https://open.bigmodel.cn/) 注册并获取密钥

### 4. 环境变量

常用环境变量：

| 变量 | 说明 |
|------|------|
| `OPENCLAW_HOME` | 主目录路径 |
| `OPENCLAW_STATE_DIR` | 覆盖状态目录路径 |
| `OPENCLAW_CONFIG_PATH` | 覆盖配置文件路径 |

### 5. 启动网关

```powershell
openclaw gateway start
```

### 6. 验证安装

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
rmdir /s /q C:\openclaw
```

如需彻底清理 Docker 资源（包括未使用的镜像、容器、网络）：

```powershell
docker system prune -a
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

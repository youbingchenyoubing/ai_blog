# Wireshark 实战使用指南

> 网络流量分析的瑞士军刀——从抓包配置到协议解析、从过滤器语法到文件还原，每个功能都有可复现的步骤。CTF Misc 方向流量题、应急响应中的流量取证，都靠它。

---

## 目录

- [一、Wireshark 是什么](#一wireshark-是什么)
- [二、安装与环境配置](#二安装与环境配置)
- [三、两类过滤器：捕获 vs 显示](#三两类过滤器捕获-vs-显示)
- [四、显示过滤器语法详解](#四显示过滤器语法详解)
- [五、协议分析实战](#五协议分析实战)
- [六、流追踪与文件还原](#六流追踪与文件还原)
- [七、USB 流量分析（键鼠取证）](#七usb-流量分析键鼠取证)
- [八、tshark 命令行批量处理](#八tshark-命令行批量处理)
- [九、实战技巧与注意事项](#九实战技巧与注意事项)
- [十、速查表](#十速查表)

---

## 一、Wireshark 是什么

Wireshark 是一款开源的网络协议分析器，能实时抓取网络流量并逐包解码展示。它的核心能力：**把网卡上流过的字节流，按协议栈分层解析成人能读懂的请求、响应、字段值**。

在 CTF 与安全工作中的典型场景：

- Misc 流量题：从 pcap 包里还原被传输的文件、提取 flag、分析木马通信
- 应急响应：排查入侵流量、定位 C2 通信、还原攻击链
- 协议调试：分析自己开发的程序的网络行为

### Wireshark vs tshark vs Fiddler

| 工具 | 形态 | 强项 | 何时用 |
|------|------|------|--------|
| Wireshark | GUI | 全协议栈深度解析、可视化 | 单个 pcap 深度分析、人工看包 |
| tshark | 命令行 | 脚本化批处理、CI 集成 | 批量提取字段、自动化统计 |
| Fiddler | GUI | HTTPS 中间人、Web 调试 | 只看 HTTP/HTTPS、前端调试 |

> 💡 **新手建议**：GUI 看 pcap 用 Wireshark，批量提取字段用 tshark，两者同源、过滤器语法通用。

---

## 二、安装与环境配置

### 1. 各平台安装

```bash
# Kali Linux — 已预装
wireshark

# Debian/Ubuntu
sudo apt install -y wireshark
# 安装时弹窗询问非 root 用户是否可抓包，选 Yes
sudo usermod -aG wireshark $USER  # 把自己加入 wireshark 组
# 重新登录后生效，避免每次 sudo

# macOS
brew install --cask wireshark

# Windows
# 官网下载：https://www.wireshark.org/download.html
# 安装时务必勾选 Npcap（Win10/11 抓包驱动）
```

### 2. 启动与选网卡

1. 启动 Wireshark，首页会列出所有网卡及其上的实时流量小条
2. 双击要抓包的网卡即开始抓包（常见：`eth0` 有线、`wlan0` 无线、`lo` 本地回环）
3. 抓包中点击工具栏红色方块停止，绿色鲨鱼鳍继续

### 3. 抓取 HTTPS 流量（配置 SSLKEYLOGFILE）

CTF 中遇到 TLS 加密流量，若能拿到浏览器的密钥日志，可解密：

```bash
# 设置环境变量（浏览器会写入对称密钥到该文件）
# Linux/macOS
export SSLKEYLOGFILE=~/.sslkeylog.log

# Windows（系统属性 → 环境变量）
SSLKEYLOGFILE = C:\Users\you\.sslkeylog.log

# 启动浏览器后，Wireshark 中：
# 编辑 → 首选项 → Protocols → TLS → (Pre)-Master-Secret log filename
# 填入上面的文件路径
```

配置后，TLS 流量会自动解密为明文 HTTP 显示。

---

## 三、两类过滤器：捕获 vs 显示

Wireshark 有两套过滤器，语法不同，新手最容易踩坑。

| 类型 | 作用时机 | 语法 | 位置 |
|------|----------|------|------|
| 捕获过滤器（BPF） | 抓包前，决定哪些包进网卡缓冲 | tcpdump/BPF 语法 | 主界面上方捕获栏 |
| 显示过滤器 | 抓包后，决定哪些包在界面显示 | Wireshark 专用语法 | 主界面上方显示栏 |

### 1. 捕获过滤器（BPF 语法）

抓包时直接过滤，省内存、省磁盘。语法基于协议 + 方向 + 内容：

```bash
# 只抓 80 端口的包
tcp port 80

# 只抓某个 IP 的双向流量
host 192.168.1.100

# 只抓某个 IP 的入或出
src host 192.168.1.100    # 源 IP
dst host 192.168.1.100    # 目的 IP

# 组合：抓 80 或 443
tcp port 80 or tcp port 443

# 排除 SSH 自身流量（远程抓包时常用）
not port 22

# 只抓某个网段
net 192.168.1.0/24

# 抓 ICMP（ping）
icmp
```

> ⚠️ BPF 语法**不能**写 `http.request.method == "POST"`，那是显示过滤器语法。BPF 只认协议名、端口、IP、方向。

### 2. 显示过滤器（Wireshark 语法）

抓完包后筛选，灵活强大，支持字段级比较：

```
http                          # 仅 HTTP 流量
http.request.method == "POST" # POST 请求
ip.addr == 10.0.0.1           # 涉及该 IP（源或目的）
tcp.port == 4444              # 指定端口
http contains "flag"          # HTTP 包含 flag 字符串
tcp contains "flag"           # TCP 负载含 flag
```

---

## 四、显示过滤器语法详解

### 1. 比较运算符

| 运算符 | 含义 | 等价 |
|--------|------|------|
| `==` | 等于 | `eq` |
| `!=` | 不等于 | `ne` |
| `>` `<` `>=` `<=` | 大小比较 | `gt` `lt` `ge` `le` |
| `contains` | 包含字符串 | — |
| `matches` | 正则匹配 | `~` |
| `in` | 属于集合 | `{1, 2, 3}` |

### 2. 逻辑组合

```
and   / &&
or    / ||
not   / !
```

### 3. 常用协议字段

```
# IP 层
ip.addr == 10.0.0.1            # 源或目的 IP
ip.src == 10.0.0.1             # 源 IP
ip.dst == 10.0.0.1             # 目的 IP
ip.ttl < 64                    # TTL 值

# TCP/UDP
tcp.port == 8080               # 源或目的端口
tcp.srcport == 12345           # 源端口
tcp.dstport == 80              # 目的端口
tcp.flags.syn == 1             # SYN 包
tcp.flags.reset == 1           # RST 包
udp.port == 53                 # DNS 查询

# HTTP
http                           # 所有 HTTP
http.request.method == "POST"  # POST 请求
http.request.uri contains "login"  # URI 含 login
http.response.code == 200      # 200 响应
http.host == "example.com"     # Host 头
http.user_agent contains "curl"  # UA 含 curl
http.cookie contains "session" # Cookie 含 session

# DNS
dns                            # 所有 DNS
dns.qry.name == "example.com"  # 查询域名
dns.qry.type == 1              # A 记录查询

# TLS
tls.handshake.type == 1        # Client Hello
tls.handshake.extensions_server_name == "example.com"  # SNI

# 数据内容
data contains "flag{"          # 原始数据含 flag{
tcp.payload contains "flag"    # TCP 负载含 flag
```

### 4. 实用过滤技巧

```
# 排除背景噪声（浏览器、系统流量）
not (tcp.port == 443 or dns or arp or icmp)

# 只看客户端到服务器的请求
http.request

# 只看非 200 响应（找异常）
http.response.code != 200

# 找大包（可能传文件）
tcp.len > 1000

# 找特定时间段（右键包 → Time Shift）
frame.time >= "2024-01-01 10:00:00"
```

> 💡 **快捷构造过滤器**：在包详情栏右键某个字段 → Apply as Filter / Prepare as Filter，自动生成语法，避免手敲错字段名。

---

## 五、协议分析实战

### 1. HTTP 分析

最常见的 CTF 流量题载体。

```
# 找所有请求
http.request

# 找登录类请求（POST + login）
http.request.method == "POST" and http.request.uri contains "login"

# 找上传文件
http.request.method == "POST" and http.content_type contains "multipart"

# 找可疑响应（命令执行结果）
http.response and http contains "root:"
```

### 2. DNS 隧道检测

木马用 DNS 隧道外传数据时，查询域名会异常长或高频：

```
# 看所有 DNS 查询
dns.qry.name

# 找超长子域（可能藏数据）
dns.qry.name matches "^[a-zA-Z0-9]{30,}"

# 统计 DNS 查询目标（菜单：Statistics → DNS）
```

### 3. TCP 异常

```
# 找 RST 重置（端口扫描特征）
tcp.flags.reset == 1

# 找 SYN 扫描（半开扫描）
tcp.flags.syn == 1 and tcp.flags.ack == 0

# 找空包（心跳/保活）
tcp.len == 0

# 找重传
tcp.analysis.retransmission
```

### 4. ICMP 隧道

ping 包里藏数据时，ICMP 负载会异常：

```
# 看 ICMP 负载
icmp and data

# 正常 ping 负载是固定模式，异常内容可疑
```

---

## 六、流追踪与文件还原

### 1. TCP 流追踪

把一个 TCP 连接的双向数据按顺序拼成可读文本：

1. 选中某个 TCP 包
2. 右键 → Follow → TCP Stream
3. 弹出窗口显示完整会话，客户端流量红色、服务端蓝色
4. 底部可切换"显示方向"（仅客户端 / 仅服务端）
5. 保存为文件：Save as

```
# 也可用过滤器直接追踪某流
tcp.stream eq 5
```

### 2. HTTP 文件还原（导出对象）

CTF 中"流量里传了个图片/压缩包"的标准解法：

1. 菜单 File → Export Objects → HTTP
2. 弹出列表显示所有 HTTP 传输的文件（含 URL、MIME、大小）
3. 选中目标 → Save 保存到本地
4. 也可 Save All 全部导出

```
# tshark 等价命令
tshark -r file.pcap --export-objects http,./output/
```

### 3. SMB 文件还原

内网流量中 SMB 传文件：

1. File → Export Objects → SMB
2. 同样列出传输的文件，直接导出

### 4. 手动重组分片数据

有时文件被分到多个包里，Export Objects 取不到：

1. 用 `tcp.stream eq N` 过滤出该流
2. Follow TCP Stream
3. 选"仅服务端方向"
4. 数据格式选 Raw，Save as 保存为二进制文件

---

## 七、USB 流量分析（键鼠取证）

CTF Misc 常见题型：从 USB 抓包还原键盘输入或鼠标轨迹。

### 1. 提取 USB 数据

USB 键鼠走 HID 中断传输，数据在 `usb.capdata` 字段：

```bash
# tshark 提取所有 USB 数据
tshark -r usb.pcap -Y "usb.capdata" -T fields -e usb.capdata

# 提取并去掉冒号（输出纯 hex）
tshark -r usb.pcap -Y "usb.capdata" -T fields -e usb.capdata | tr -d ':'
```

### 2. 键盘数据还原

USB 键盘每个数据包 8 字节，第 3 字节（偏移 2）是按键扫描码：

```python
#!/usr/bin/env python3
"""USB 键盘流量还原"""
# 标准 HID 键盘扫描码到字符映射（部分）
KEY_MAP = {
    0x04: ('a', 'A'), 0x05: ('b', 'B'), 0x06: ('c', 'C'), 0x07: ('d', 'D'),
    0x08: ('e', 'E'), 0x09: ('f', 'F'), 0x0a: ('g', 'G'), 0x0b: ('h', 'H'),
    0x0c: ('i', 'I'), 0x0d: ('j', 'J'), 0x0e: ('k', 'K'), 0x0f: ('l', 'L'),
    0x10: ('m', 'M'), 0x11: ('n', 'N'), 0x12: ('o', 'O'), 0x13: ('p', 'P'),
    0x14: ('q', 'Q'), 0x15: ('r', 'R'), 0x16: ('s', 'S'), 0x17: ('t', 'T'),
    0x18: ('u', 'U'), 0x19: ('v', 'V'), 0x1a: ('w', 'W'), 0x1b: ('x', 'X'),
    0x1c: ('y', 'Y'), 0x1d: ('z', 'Z'),
    0x1e: ('1', '!'), 0x1f: ('2', '@'), 0x20: ('3', '#'), 0x21: ('4', '$'),
    0x22: ('5', '%'), 0x23: ('6', '^'), 0x24: ('7', '&'), 0x25: ('8', '*'),
    0x26: ('9', '('), 0x27: ('0', ')'),
    0x28: ('\n', '\n'), 0x29: ('ESC', 'ESC'), 0x2a: ('BKSP', 'BKSP'),
    0x2b: ('\t', '\t'), 0x2c: (' ', ' '),
    0x2d: ('-', '_'), 0x2e: ('=', '+'), 0x2f: ('[', '{'), 0x30: (']', '}'),
    0x33: (';', ':'), 0x34: ("'", '"'), 0x36: (',', '<'), 0x37: ('.', '>'),
    0x38: ('/', '?'),
}

def decode_keyboard(hex_lines):
    """hex_lines: 每行一个 8 字节 USB 数据的 hex 字符串"""
    result = ""
    for line in hex_lines:
        line = line.strip().replace(':', '')
        if len(line) < 16:
            continue
        # 第 0 字节 bit5 是 Left Shift
        shift = int(line[0:2], 16) & 0x20
        # 第 3、4 字节是同时按下的键（第 3 字节优先）
        for i in (4, 6):  # 偏移 2 和 3（hex 字符位置）
            code = int(line[i*2:i*2+2], 16)
            if code == 0:
                continue
            if code in KEY_MAP:
                result += KEY_MAP[code][1 if shift else 0]
            break  # 一个包只取一个有效键
    return result

# 用法：tshark -r usb.pcap -Y "usb.capdata" -T fields -e usb.capdata > data.txt
# 然后：
# with open('data.txt') as f: print(decode_keyboard(f))
```

### 3. 鼠标轨迹还原

USB 鼠标数据通常 4 字节：`[按键, X位移, Y位移低位, Y位移高位]`：

```python
#!/usr/bin/env python3
"""USB 鼠标轨迹还原 - 画图查看"""
import struct

def parse_mouse(hex_lines):
    points = []
    x, y = 0, 0
    for line in hex_lines:
        line = line.strip().replace(':', '')
        if len(line) < 8:
            continue
        btn = int(line[0:2], 16)
        # X、Y 是有符号 8 位整数（小端序拼成 16 位）
        dx = struct.unpack('b', bytes.fromhex(line[2:4]))[0]
        dy = struct.unpack('b', bytes.fromhex(line[4:6]))[0]
        x += dx
        y += dy
        if btn & 0x01:  # 左键按下时记录点
            points.append((x, y))
    return points

# 画图：pip install matplotlib
# import matplotlib.pyplot as plt
# pts = parse_mouse(open('data.txt'))
# xs, ys = zip(*pts)
# plt.scatter(xs, ys); plt.gca().invert_yaxis(); plt.show()
```

---

## 八、tshark 命令行批量处理

GUI 看包方便，但批量提取、脚本化分析必须用 tshark。

### 1. 基础读取

```bash
# 读取 pcap 概要
tshark -r file.pcap

# 只读前 10 个包
tshark -r file.pcap -c 10

# 用显示过滤器
tshark -r file.pcap -Y "http.request.method == POST"

# 用捕获过滤器（BPF）
tshark -r file.pcap -f "tcp port 80"
```

### 2. 提取字段（-T fields）

```bash
# 提取 HTTP 请求的 Host 和 URI
tshark -r file.pcap -Y "http.request" -T fields -e http.host -e http.request.uri

# 提取所有源目的 IP
tshark -r file.pcap -T fields -e ip.src -e ip.dst

# 提取 HTTP 响应体（文件内容）
tshark -r file.pcap -Y "http" -T fields -e http.file_data

# 提取 TCP 负载
tshark -r file.pcap -Y "tcp.port==4444" -T fields -e tcp.payload

# 提取并拼接 hex 流量，转成二进制文件
tshark -r file.pcap -Y "tcp.port==4444" -T fields -e data | tr -d '\n' | xxd -r -p > out.bin
```

### 3. 统计分析

```bash
# 协议层级统计
tshark -r file.pcap -q -z io,phs

# 会话统计（谁和谁通信最多）
tshark -r file.pcap -q -z conv,tcp

# HTTP 请求统计
tshark -r file.pcap -q -z http,tree

# DNS 查询统计
tshark -r file.pcap -q -z dns,tree

# 端点统计
tshark -r file.pcap -q -z endpoints,ip
```

### 4. 导出对象

```bash
# 导出 HTTP 传输的文件
tshark -r file.pcap --export-objects http,./output/

# 导出 SMB 文件
tshark -r file.pcap --export-objects smb,./output/
```

### 5. 实时抓包（替代 GUI）

```bash
# 实时抓 80 端口，输出到终端
tshark -i eth0 -f "tcp port 80"

# 抓 100 个包存文件
tshark -i eth0 -c 100 -w capture.pcap
```

---

## 九、实战技巧与注意事项

### 1. 找 flag 的标准套路

拿到一个流量包，按此顺序排查：

1. `http contains "flag"` 或 `tcp contains "flag"` —— 直接搜字符串
2. `http.request.method == "POST"` —— 看上传了什么
3. File → Export Objects → HTTP —— 看传了哪些文件
4. 统计 → DNS —— 看有没有 DNS 隧道
5. 找大包 `tcp.len > 500` —— 看有没有传文件
6. Follow TCP Stream —— 逐个流看会话内容

### 2. 时间戳分析

CTF 题有时按时间序列出题：

- 菜单 View → Time Display Format → 选秒数/日期时间
- 找异常间隔：某段时间密集通信 = 攻击发生

### 3. 解码乱码

- 右键包 → Decode As → 强制按某协议解析
- 例：把 8080 端口流量当 HTTP 解析

### 4. 性能优化

大 pcap（几百 MB）卡顿时：

- 先用捕获过滤器抓子集到新文件
- 关闭不必要的协议解析（Analyze → Enabled Protocols）
- 用 tshark 命令行替代 GUI

### 5. 常见踩坑

- 抓不到包：网卡选错、权限不够（非 root 未加 wireshark 组）
- 看不到 HTTP 只看 TCP：HTTPS 加密了，配 SSLKEYLOGFILE
- 过滤器报错：BPF 和显示过滤器语法混用（捕获栏用 BPF，显示栏用 Wireshark 语法）
- 时间显示不对：默认相对时间，改成绝对时间更直观

---

## 十、速查表

### 显示过滤器速查（最常用）

```
# 协议
http / https / dns / tcp / udp / icmp / tls / smb / ftp / smtp

# HTTP
http.request                              # 所有请求
http.request.method == "POST"             # POST 请求
http.request.uri contains "login"         # URI 含 login
http.response.code == 200                 # 200 响应
http.host == "example.com"                # Host 头
http.user_agent contains "curl"           # UA
http.cookie contains "session"            # Cookie
http contains "flag"                      # 任意字段含 flag

# IP / 端口
ip.addr == 10.0.0.1                       # 涉及该 IP
ip.src == 10.0.0.1 / ip.dst == 10.0.0.1
tcp.port == 8080                          # 端口
tcp.srcport == 12345 / tcp.dstport == 80

# 内容
tcp contains "flag"                       # TCP 负载含 flag
data contains "flag{"                     # 原始数据
tcp.len > 1000                            # 大包

# TCP 标志
tcp.flags.syn == 1                        # SYN
tcp.flags.reset == 1                      # RST
tcp.analysis.retransmission               # 重传

# 组合
http.request.method == "POST" and http contains "flag"
not (arp or dns or icmp)                  # 排除噪声
```

### tshark 命令速查

```bash
# 读取
tshark -r file.pcap                       # 读 pcap
tshark -r file.pcap -c 10                 # 前 10 包
tshark -r file.pcap -Y "http.request"     # 显示过滤

# 提取字段
tshark -r file.pcap -T fields -e ip.src -e ip.dst
tshark -r file.pcap -Y "http.request" -T fields -e http.host -e http.request.uri
tshark -r file.pcap -Y "tcp.port==4444" -T fields -e data | tr -d '\n' | xxd -r -p > out.bin

# 导出对象
tshark -r file.pcap --export-objects http,./output/

# 统计
tshark -r file.pcap -q -z conv,tcp        # 会话统计
tshark -r file.pcap -q -z io,phs          # 协议层级

# 抓包
tshark -i eth0 -f "tcp port 80"           # 实时抓
tshark -i eth0 -c 100 -w cap.pcap         # 抓 100 包存文件
```

### 捕获过滤器（BPF）速查

```
tcp port 80 / udp port 53                 # 端口
host 192.168.1.1                          # IP
src host 192.168.1.1 / dst host ...
net 192.168.1.0/24                        # 网段
tcp port 80 or tcp port 443               # 组合
not port 22                               # 排除 SSH
icmp / arp / tcp / udp                    # 协议
```

### 快捷键速查

| 快捷键 | 功能 |
|--------|------|
| Ctrl+E | 开始/停止抓包 |
| Ctrl+R | 重新加载文件 |
| Ctrl+F | 查找包 |
| Ctrl+N / Ctrl+P | 下一个/上一个匹配 |
| 右键 → Follow → TCP Stream | 追踪 TCP 流 |
| 右键字段 → Apply as Filter | 快速过滤 |

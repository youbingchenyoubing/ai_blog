# Wireshark 深度使用手册

> 从基础抓包走向专业流量分析——高级抓包技术、深度协议解析、网络取证工作流、Lua 自定义解析器、tshark 自动化流水线，面向 CTF 高阶流量题与实战应急响应场景。

***

## 目录

- [一、本手册定位](#一本手册定位)
- [二、高级抓包技术](#二高级抓包技术)
- [三、高级显示过滤器](#三高级显示过滤器)
- [四、专家信息系统](#四专家信息系统)
- [五、统计与可视化分析](#五统计与可视化分析)
- [六、着色规则与自定义列](#六着色规则与自定义列)
- [七、深度协议解析](#七深度协议解析)
- [八、网络取证工作流](#八网络取证工作流)
- [九、性能分析](#九性能分析)
- [十、高级文件雕刻与数据重组](#十高级文件雕刻与数据重组)
- [十一、自定义协议解析器（Lua 插件）](#十一自定义协议解析器lua-插件)
- [十二、pcap 处理工具链](#十二pcap-处理工具链)
- [十三、tshark 高级用法](#十三tshark-高级用法)
- [十四、自动化分析流水线](#十四自动化分析流水线)
- [十五、速查表](#十五速查表)

***

## 一、本手册定位

本手册是 [Wireshark实战使用指南](Wireshark实战使用指南.md) 的进阶篇。实战指南覆盖安装、基础过滤器、协议分析、流追踪、USB取证、tshark基础，本手册在此基础上深入以下方向：

| 实战指南已覆盖 | 本手册深入展开 |
|------------|----------|
| 捕获过滤器（BPF）基础 | 环缓冲、多网卡、远程抓包、dumpcap |
| 显示过滤器比较运算与逻辑组合 | 函数调用、切片、宏、时间函数、协议层级引用 |
| HTTP/DNS/TCP/ICMP 基础分析 | TLS 握手解析、802.11 无线、蓝牙 BLE、SMB 深度分析 |
| TCP 流追踪与 HTTP 文件导出 | 手动分片重组、特殊编码数据还原、隐蔽通道检测 |
| tshark 读取/提取/统计 | 管道流、JSON/PDML 输出、脚本化集成 |
| USB 键鼠取证 | 专家信息系统、网络取证工作流、性能分析、Lua 解析器 |

> 建议先掌握实战指南内容再阅读本手册。两份文档互补，无重复内容。

***

## 二、高级抓包技术

### 1. 环缓冲抓包（Ring Buffer）

长时间抓包时，pcap 文件会持续膨胀。环缓冲按时间或大小自动轮转，始终保留最新数据：

```
# Wireshark GUI 配置
# 捕获 → 选项 → 输出标签页
# 勾选 "Create a new file automatically"
#   每 100 MB 创建新文件（或 每 60 秒）
# 勾选 "Use a ring buffer"
#   保留文件数：10（超过后自动覆盖最旧的）

# tshark 等价
tshark -i eth0 -w capture.pcap \
  -b filesize:102400 \   # 每文件 100 MB
  -b files:10            # 保留 10 个文件轮转
```

> 场景：7x24 监控内网出口流量、应急响应期间持续抓包取证。环缓冲确保磁盘不会撑爆，同时保留最近的流量窗口。

### 2. 多网卡同时抓包

同时监听多个网口的流量，存入同一 pcap：

```bash
# tshark 多网卡
tshark -i eth0 -i eth1 -w dual_capture.pcap

# Wireshark GUI
# 捕获 → 选项 → 勾选多个接口 → 开始
```

> 场景：网关设备有内外两块网卡，同时抓进出口流量对比分析。

### 3. 远程抓包（rpcapd）

目标机器上运行 rpcapd 守护进程，本地 Wireshark 远程连接抓包：

```bash
# 目标机器（被监控主机）— 安装并启动 rpcapd
# Windows：Wireshark 安装目录下自带 rpcapd.exe
rpcapd.exe -n -p 2002    # -n 允许空密码（仅内网用），-p 指定端口

# Linux
sudo apt install rpcapd
sudo rpcapd -n -p 2002

# 本地 Wireshark 连接
# 捕获 → 选项 → Manage Interfaces → Remote Interfaces
# 添加：主机 IP，端口 2002
# 或 tshark：
tshark -i rpcap://192.168.1.50:2002/eth0 -w remote.pcap
```

> ⚠️ rpcapd 默认无加密，仅在可信内网使用。跨公网场景应走 SSH 隧道或 VPN。

### 4. dumpcap——最底层的抓包引擎

Wireshark 和 tshark 底层都调用 dumpcap 抓包。直接使用 dumpcap 更轻量，适合资源受限环境：

```bash
# 基本抓包
dumpcap -i eth0 -w capture.pcap

# 带环缓冲
dumpcap -i eth0 -w capture.pcap -b filesize:102400 -b files:10

# 限速抓包（每秒最多抓 1000 包）
dumpcap -i eth0 -w capture.pcap -c 100000 -b packets:1000

# 查看网卡列表
dumpcap -D
```

dumpcap 的优势：
- 内存占用极低（不解析协议，只写盘）
- 适合长期无人值守抓包
- 可用 systemd/supervisor 托管为服务

### 5. SSH 隧道远程抓包

通过 SSH 管道把远程流量实时传到本地 Wireshark：

```bash
# 方法1：SSH + 远程 tcpdump，管道输出给本地 Wireshark
ssh root@remote-host "tcpdump -i eth0 -U -w - not port 22" | wireshark -k -i -

# 方法2：SSH + 远程 tshark
ssh root@remote-host "tshark -i eth0 -w - not port 22" | wireshark -k -i -

# -U 让 tcpdump 不缓冲，实时输出
# -w - 输出到 stdout
# -k 让 Wireshark 立即开始抓包
# -i - 从 stdin 读取
```

> 场景：远程 Linux 服务器没有 GUI，在本地 Windows/macOS 的 Wireshark 中实时查看远端流量。

### 6. 捕获条件组合实战

```bash
# 只抓某个子网的 HTTP/HTTPS 流量
tshark -i eth0 -f "tcp port 80 or tcp port 443" and -f "net 192.168.1.0/24"

# 排除自身 SSH 和 DNS 噪声
tshark -i eth0 -f "not port 22 and not port 53"

# 抓特定 MAC 地址的流量
tshark -i eth0 -f "ether host aa:bb:cc:dd:ee:ff"

# 抓 VLAN 标签流量
tshark -i eth0 -f "vlan"
```

***

## 三、高级显示过滤器

实战指南介绍了比较运算符和逻辑组合，本节展开函数调用、切片、宏等高级语法。

### 1. 函数调用

Wireshark 显示过滤器支持内置函数，处理复杂匹配：

```
# upper()/lower() — 大小写不敏感匹配
upper(http.user_agent) contains "CURL"
lower(http.host) == "example.com"

# string() — 数值转字符串匹配
string(tcp.port) == "443"

# len() — 字段长度
len(http.request.uri) > 100           # URI 超过 100 字符（可能注入）
len(tcp.payload) > 0                   # 有负载的包

# exists — 字段是否存在
exists http.cookie                     # 有 Cookie 的请求
exists tls.handshake.extensions_server_name   # 有 SNI 的 Client Hello

# in 集合匹配
tcp.port in {80 443 8080 8443}         # 常见 Web 端口
http.response.code in {200 301 302}    # 正常响应码
```

### 2. 切片操作

切片（slice）用于匹配字段中的特定字节位置：

```
# 语法：字段名[起始偏移:长度]

# 匹配 IP 头的 TTL 字段（偏移 8，1 字节）
ip.ttl[0] == 64                        # TTL 等于 64

# 匹配 TCP 头标志位（偏移 13，1 字节）
tcp.flags[0] & 0x02 == 0x02            # SYN 标志位

# 匹配以太网帧的以太类型（偏移 12-13）
eth.type[0:2] == 0x0800                # IPv4

# 提取 TCP 序列号的前 2 字节
tcp.seq[0:2]

# 匹配 UDP 负载前 4 字节（魔数识别）
udp.payload[0:4] == 00:00:00:01
```

### 3. 宏（Display Filter Macros）

重复使用同一过滤器时，可定义为宏：

```
# 编辑 → 首选项 → Filter Macros → 添加
# 名称：web_ports
#表达式：tcp.port in {80 443 8080 8443}

# 使用时
${web_ports} and http.request
```

### 4. 协议层级引用

当一个包被多层协议封装时，用 `@` 指定引用哪一层的字段：

```
# 场景：IP-in-IP 隧道，内外层都有 IP 头
ip.src#1 == 10.0.0.1     # 外层 IP 源地址
ip.src#2 == 192.168.1.1  # 内层 IP 源地址

# 场景：GRE 隧道内的 ICMP
icmp.type @2 == 8        # 第二层（GRE 内）的 ICMP 类型
```

### 5. 时间函数与范围过滤

```
# 按绝对时间过滤
frame.time >= "2026-07-10 08:00:00" and frame.time <= "2026-07-10 09:00:00"

# 按相对时间（从第一个包起）
frame.time_relative > 60 and frame.time_relative < 120    # 第 60-120 秒

# 按时间间隔
frame.time_delta > 5       # 与上一包间隔超过 5 秒（异常静默期）
frame.time_delta_displayed > 10  # 显示列表中两包间隔超 10 秒
```

### 6. 复杂组合实战

```
# 找可疑的 HTTP POST 请求（大体积 + 非 200 响应）
http.request.method == "POST" and tcp.len > 5000

# 找 TLS Client Hello 中的特定 SNI
tls.handshake.type == 1 and tls.handshake.extensions_server_name contains "evil"

# 找非标准端口的 HTTP 流量
http and not tcp.port in {80 443 8080}

# 找可能的 SQL 注入尝试
http.request.uri matches "(?i)(union|select|insert|drop|--;|--\s)"

# 找 DNS 隧道（超长子域 + 高频查询）
dns.qry.name matches "^[a-zA-Z0-9]{40,}" and dns.flags.response == 0

# 找心跳/保活流量（周期性空包）
tcp.len == 0 and tcp.flags.ack == 1 and frame.time_delta < 1

# 找可能的命令执行结果回传
http.response and (http.content_type contains "text/plain") and tcp.len > 100

# 检测可能的端口扫描
tcp.flags.syn == 1 and tcp.flags.ack == 0 and tcp.analysis.count == 1
```

***

## 四、专家信息系统

Expert Info 是 Wireshark 内置的协议异常自动检测系统，能发现人眼容易忽略的问题。

### 1. 打开方式

```
# 菜单：Analyze → Expert Information
# 或点击底部状态栏的专家信息图标（彩色圆点）
```

Expert Info 窗口按严重程度分组显示所有自动检测到的异常。

### 2. 严重等级

| 等级 | 颜色 | 含义 | 典型发现 |
|------|------|------|----------|
| Error | 红色 | 协议违规/解析错误 | 格式错误的包、校验和错误 |
| Warning | 黄色 | 可能的问题 | 重传、乱序、零窗口 |
| Note | 青色 | 值得注意 | 窗口更新、保活、快速重传 |
| Chat | 蓝色 | 正常但有用的信息 | 连接建立/关闭、TCP 参数 |

### 3. 常见专家信息解读

**TCP 重传（Retransmission）**

```
# 过滤器
tcp.analysis.retransmission

# 含义：发送方认为包丢了，重新发送
# 原因可能是：网络拥塞、接收方处理慢、包确实丢了
# 应急场景：大量重传可能暗示中间人攻击（注入 RST 导致重传）
```

**TCP 乱序（Out-of-Order）**

```
# 过滤器
tcp.analysis.out_of_order

# 含义：包到达顺序与发送顺序不同
# 原因：网络路径变化、负载均衡多路径
# 正常网络中有少量乱序是允许的，大量出现则异常
```

**TCP 重复 ACK（Duplicate ACK）**

```
# 过滤器
tcp.analysis.duplicate_ack

# 含义：接收方反复确认同一序列号，暗示某段数据丢失
# 3 个重复 ACK 触发快速重传（TCP 拥塞控制）
```

**零窗口（Zero Window）**

```
# 过滤器
tcp.analysis.zero_window

# 含义：接收方缓冲区满了，通知发送方暂停
# 如果持续出现 → 接收方处理不过来，可能是性能瓶颈或被攻击
```

**窗口更新（Window Update）**

```
# 过滤器
tcp.analysis.window_update

# 含义：零窗口后恢复正常，接收方有了新空间
# 正常现象，但频繁更新说明缓冲区紧张
```

**校验和错误**

```
# 过滤器
tcp.checksum_bad == 1 or ip.checksum_bad == 1

# 常见误报：网卡做了 TCP 卸载（offload），操作系统层看到的是
# 未计算校验和的包，抓到的就是"错误"
# 排除方法：编辑 → 首选项 → Protocols → TCP/IPv4 → 取消勾选 Validate checksum
```

### 4. 实战：用 Expert Info 快速定位问题

```bash
# tshark 提取所有专家信息
tshark -r file.pcap -Y "tcp.analysis.flags" -T fields \
  -e frame.number -e ip.src -e ip.dst -e tcp.analysis.flags

# 统计各类异常的数量
tshark -r file.pcap -Y "tcp.analysis.flags" -T fields \
  -e tcp.analysis.flags | sort | uniq -c | sort -rn

# 只看重传（可能是攻击的痕迹）
tshark -r file.pcap -Y "tcp.analysis.retransmission" \
  -T fields -e frame.number -e ip.src -e ip.dst -e tcp.seq
```

***

## 五、统计与可视化分析

Wireshark 的 Statistics 菜单提供大量分析视图，是"从海量包里找规律"的关键。

### 1. 协议层级统计（Protocol Hierarchy）

```
# 菜单：Statistics → Protocol Hierarchy
# 或 tshark：
tshark -r file.pcap -q -z io,phs
```

输出示例：

```
Protocol Hierarchy Statistics
eth          100.00%  (总包数)
  ip          95.00%
    tcp        80.00%
      http       45.00%
      tls        30.00%
      ssh        5.00%
    udp        15.00%
      dns        10.00%
      quic       5.00%
    icmp       0.00%
  arp         5.00%
```

> 用途：快速判断流量构成。如果非标准协议占比异常高，值得深入看。

### 2. 会话统计（Conversations）

```
# 菜单：Statistics → Conversations
# 或 tshark：
tshark -r file.pcap -q -z conv,tcp    # TCP 会话
tshark -r file.pcap -q -z conv,udp    # UDP 会话
tshark -r file.pcap -q -z conv,ip     # IP 会话
tshark -r file.pcap -q -z conv,eth    # 以太网会话
```

GUI 中 Conversations 窗口的操作：
- 点击列标题排序（按字节量、包数、持续时间等）
- 右键某行 → Apply as Filter → 只看该会话
- 底部切换 TCP/UDP/IPv4/Ethernet 标签页

> 用途：找通信量最大的主机对，定位异常流量源。

### 3. 端点统计（Endpoints）

```
# 菜单：Statistics → Endpoints
# 或 tshark：
tshark -r file.pcap -q -z endpoints,ip
tshark -r file.pcap -q -z endpoints,tcp
```

> 用途：发现流量中的"明星节点"——某个 IP/端口出现频率异常高，可能是 C2 服务器或被攻击目标。

### 4. IO 图表（IO Graphs）

最直观的流量可视化工具，显示流量随时间的变化趋势：

```
# 菜单：Statistics → I/O Graph
```

配置方法：
1. 横轴为时间，纵轴为包数/字节数
2. 可添加多条曲线，每条配置不同过滤器
3. 点击 + 添加新系列，设置过滤器和颜色
4. 鼠标悬停查看具体数值

常用分析组合：

| 分析目标 | 过滤器 | 图表类型 |
|----------|--------|----------|
| 总流量趋势 | （空） | Line |
| HTTP 请求频率 | http.request | Line |
| DNS 查询频率 | dns.qry.name | Line |
| 数据外传检测 | tcp.srcport == 4444 | Line |
| 异常大包 | tcp.len > 1000 | Bar/FIO |
| 加密 vs 明文 | tls vs http | 两条线对比 |

> 用途：找流量突增时刻（攻击发生点）、周期性通信（C2 心跳）、数据外传（持续高吞吐）。

### 5. 流图（Flow Graph）

将 TCP 流按时间线可视化展示，直观看到请求/响应序列：

```
# 菜单：Statistics → Flow Graph
# 可选：显示所有流 / 仅显示被过滤的流
# 可选：显示 ARP / ICMP / TCP 标志
```

> 用途：还原 TCP 三次握手/四次挥手过程、理解请求-响应时序、发现异常中断。

### 6. TCP 流图（TCP Stream Graphs）

```
# 菜单：Statistics → TCP Stream Graphs

# Time-Sequence (Stevens)：序列号随时间变化
#   - 平稳上升 = 正常数据传输
#   - 跳跃/回退 = 重传/乱序
#   - 停滞 = 零窗口/拥塞

# Round Trip Time：RTT 分布
#   - 突然增大 = 网络拥塞或路由变化
#   - 持续高 RTT = 远程服务器或网络质量差

# Throughput：吞吐量随时间变化
#   - 下降 = 窗口收缩/丢包
#   - 波动 = 网络不稳定
#   - 长期低吞吐 = 瓶颈

# Window Scaling：接收窗口变化
#   - 频繁零窗口 = 接收方过载
```

### 7. DNS 统计

```
# 菜单：Statistics → DNS
# 或 tshark：
tshark -r file.pcap -q -z dns,tree
```

输出包含：
- 查询类型分布（A/AAAA/CNAME/MX/TXT...）
- 响应码统计（NoError/NXDomain/ServFail...）
- 高频查询域名排行

> 用途：DNS 隧道检测——TXT/NULL 类型查询占比异常、超长域名、NXDomain 泛洪。

### 8. HTTP 统计

```
# 菜单：Statistics → HTTP
#   → Packet Counter：请求/响应计数
#   → Requests：请求方法/Host/URI 分布
#   → Load Distribution：各服务器请求分布

# tshark：
tshark -r file.pcap -q -z http,tree
tshark -r file.pcap -q -z http_req,tree
```

***

## 六、着色规则与自定义列

### 1. 着色规则（Coloring Rules）

Wireshark 默认给不同协议的包着不同颜色，但你可以自定义规则突出关注的流量：

```
# 菜单：View → Coloring Rules
```

**默认着色规则解读：**

| 颜色 | 默认匹配 | 含义 |
|------|----------|------|
| 浅紫 | tcp.errors | TCP 错误（RST等） |
| 深蓝 | tcp | 普通 TCP |
| 深绿 | http | HTTP 流量 |
| 深红 | dns | DNS 查询 |
| 黑色 | tcp.syn | TCP 握手 |
| 灰色 | tcp.ack | 纯 ACK |

**添加自定义规则（按优先级从上到下匹配）：**

```
# 高亮可疑 POST 请求（红色背景）
名称：Suspicious POST
过滤器：http.request.method == "POST"
前景色：白色  背景色：红色

# 高亮大包（可能是文件传输，橙色背景）
名称：Large Packet
过滤器：tcp.len > 1000
前景色：黑色  背景色：橙色

# 高亮非标准端口 HTTP（黄色背景）
名称：HTTP on non-standard port
过滤器：http and not tcp.port in {80 443 8080}
前景色：黑色  背景色：黄色

# 高亮 DNS 隧道特征（品红色背景）
名称：DNS Tunnel
过滤器：dns.qry.name matches "^[a-zA-Z0-9]{30,}"
前景色：白色  背景色：品红色
```

> 规则从上到下匹配，第一个匹配的生效。把高优先级规则放在上面。

**导出/导入着色规则：**

```
# Coloring Rules 窗口 → Export / Import
# 配置文件存储位置：
# Linux: ~/.config/wireshark/colorfilters
# macOS: ~/.config/wireshark/colorfilters
# Windows: %APPDATA%\Wireshark\colorfilters
```

### 2. 自定义列（Custom Columns）

默认列只显示 No./Time/Source/Destination/Protocol/Length/Info，但可以添加任何协议字段作为列：

```
# 操作：包列表区右键列标题 → Column Preferences → + 添加
```

**高频自定义列：**

| 列名 | 字段名 | 用途 |
|------|--------|------|
| Src Port | tcp.srcport | 源端口 |
| Dst Port | tcp.dstport | 目的端口 |
| HTTP Host | http.host | HTTP 主机名 |
| HTTP URI | http.request.uri | HTTP 请求路径 |
| HTTP Method | http.request.method | HTTP 方法 |
| HTTP Status | http.response.code | HTTP 状态码 |
| DNS Query | dns.qry.name | DNS 查询域名 |
| TCP Stream | tcp.stream | TCP 流编号 |
| TTL | ip.ttl | 生存时间 |
| TCP Len | tcp.len | TCP 负载长度 |
| User-Agent | http.user_agent | 浏览器标识 |
| SNI | tls.handshake.extensions_server_name | TLS SNI |
| Delta Time | frame.time_delta | 与上一包间隔 |

> 快捷方式：在包详情栏右键某个字段 → Apply as Column，一键添加为列。

### 3. 配置文件（Profiles）

不同场景可以保存不同的列配置、着色规则、过滤器：

```
# 菜单：编辑 → 配置文件 → 新建
# 常用配置文件：
#   Default — 默认通用配置
#   HTTP Analysis — 侧重 HTTP 字段列、HTTP 着色
#   DNS Analysis — 侧重 DNS 字段列、DNS 着色
#   Forensics — 侧重时间戳、流编号、专家信息
#   Performance — 侧重 TCP 参数、窗口、RTT
```

配置文件存储位置：
```
# Linux: ~/.config/wireshark/profiles/
# Windows: %APPDATA%\Wireshark\profiles\
```

***

## 七、深度协议解析

### 1. TLS/SSL 深度解析

实战指南介绍了 SSLKEYLOGFILE 配置，本节深入 TLS 握手细节和常见分析场景。

**TLS 握手流程过滤器：**

```
# Client Hello
tls.handshake.type == 1

# Server Hello
tls.handshake.type == 2

# Certificate
tls.handshake.type == 11

# Server Key Exchange
tls.handshake.type == 12

# Client Key Exchange
tls.handshake.type == 16

# Change Cipher Spec
tls.record.content_type == 20

# Application Data（加密通信）
tls.record.content_type == 23
```

**提取 TLS 指纹信息：**

```bash
# 提取所有 SNI
tshark -r file.pcap -Y "tls.handshake.type == 1" \
  -T fields -e ip.src -e tls.handshake.extensions_server_name

# 提取支持的密码套件（JA3 指纹）
tshark -r file.pcap -Y "tls.handshake.type == 1" \
  -T fields -e ip.src -e tls.handshake.ciphersuite

# 提取服务器证书信息
tshark -r file.pcap -Y "tls.handshake.type == 11" \
  -T fields -e ip.src -e x509ce.dNSName

# 提取 TLS 版本
tshark -r file.pcap -Y "tls.handshake.type == 1" \
  -T fields -e ip.src -e tls.record.version
```

**JA3/JA3S 指纹分析：**

JA3 是基于 Client Hello 参数的客户端指纹，JA3S 是服务端指纹。Wireshark 4.x+ 原生支持：

```
# 显示 JA3 哈希
tls.handshake.ja3_hash

# 显示 JA3S 哈希
tls.handshake.ja3s_hash

# 过滤特定 JA3 指纹（已知恶意客户端）
tls.handshake.ja3_hash == "e7d705a3286e19ea42f587b344ee6865"
```

> 用途：识别恶意客户端（已知 JA3 指纹库）、检测 C2 工具（Cobalt Strike 有特征 JA3）、区分真实浏览器 vs 脚本。

**TLS 解密高级配置：**

```
# 除 SSLKEYLOGFILE 外，还支持：
# 1. RSA 私钥解密（仅 RSA 密钥交换，不支持 DHE/ECDHE）
#    编辑 → 首选项 → Protocols → TLS → RSA keys list
#    格式：IP,port,protocol,private_key_file

# 2. 多个 keylog 文件
#    可以合并多个浏览器的 keylog：
#    cat browser1.keylog browser2.keylog > combined.keylog

# 3. tshark 解密
tshark -r encrypted.pcap -o "tls.keylog_file:./keylog.txt" \
  -Y "http.request" -T fields -e http.host -e http.request.uri
```

### 2. 802.11 无线分析

Wireshark 可以分析 802.11（WiFi）帧，需要网卡支持监听模式：

```bash
# Linux 设置监听模式
sudo airmon-ng check kill    # 关闭干扰进程
sudo airmon-ng start wlan0   # 开启监听模式，产生 wlan0mon 接口

# 用 Wireshark 抓 wlan0mon
wireshark -i wlan0mon -k
```

**802.11 常用过滤器：**

```
# 管理帧
wlan.fc.type == 0                    # 所有管理帧
wlan.fc.type_subtype == 0            # Association Request
wlan.fc.type_subtype == 1            # Association Response
wlan.fc.type_subtype == 4            # Probe Request
wlan.fc.type_subtype == 5            # Probe Response
wlan.fc.type_subtype == 8            # Beacon
wlan.fc.type_subtype == 10           # Disassociation
wlan.fc.type_subtype == 11           # Authentication

# 控制帧
wlan.fc.type == 1                    # 所有控制帧

# 数据帧
wlan.fc.type == 2                    # 所有数据帧

# 特定 AP 的流量
wlan.bssid == "aa:bb:cc:dd:ee:ff"

# 特定客户端
wlan.sa == "11:22:33:44:55:66"       # 源地址
wlan.da == "77:88:99:aa:bb:cc"       # 目的地址

# EAPOL 握手（WPA/WPA2 认证过程）
eapol

# 特定 SSID
wlan.ssid == "TargetNetwork"
```

**WPA2 握手抓取与解密：**

```
# 1. 抓取 EAPOL 4-way 握手
#    过滤：eapol or wlan.bssid == "目标AP的BSSID"
# 2. 当看到 4 个 EAPOL 帧时，握手完成

# 3. 用 airdecap-ng 解密（需要密码）
airdecap-ng -e "SSID" -p "password" capture.pcap

# 4. 或在 Wireshark 中配置解密：
#    编辑 → 首选项 → Protocols → IEEE 802.11 → Decryption Keys
#    添加密钥类型：wpa-pwd
#    值：SSID:password
```

### 3. 蓝牙/BLE 分析

Wireshark 4.x+ 支持蓝牙 HCI 和 BLE 分析：

```bash
# Linux 蓝牙抓包
sudo btmon -i hci0 -w ble_capture.pcap

# 或用 hcidump
sudo hcidump -i hci0 -w ble_capture.pcap
```

**BLE 常用过滤器：**

```
# BLE 广播
btle.advertising_address

# BLE 连接
btle.link_layer_type == 2            # LL_DATA
btle.link_layer_type == 3            # LL_DATA_CTRL

# GATT 操作
btatt.opcode == 0x02                 # Read Request
btatt.opcode == 0x03                 # Read Response
btatt.opcode == 0x0A                 # Write Request
btatt.opcode == 0x1B                 # Handle Value Notification

# 特定 UUID 的服务
btgatt.uuid16 == 0x180F              # Battery Service
btgatt.uuid16 == 0x180A              # Device Information
```

### 4. SMB/CIFS 深度分析

内网渗透中分析文件共享和横向移动流量：

```
# SMB1 命令
smb.cmd == 0x72                       # Negotiate Protocol
smb.cmd == 0x73                       # Session Setup AndX
smb.cmd == 0x25                       # Tree Connect AndX
smb.cmd == 0x2D                       # Create/Read/Write

# SMB2 命令
smb2.cmd == 1                         # Negotiate
smb2.cmd == 2                         # Session Setup
smb2.cmd == 3                         # Tree Connect
smb2.cmd == 5                         # Create
smb2.cmd == 8                         # Read
smb2.cmd == 9                         # Write
smb2.cmd == 12                        # Close

# 找文件访问
smb2.filename contains "secret"

# 找认证尝试
smb2.cmd == 2 and not smb2.flags.session_setup

# NTLM 认证
ntlmssp.messagetype == 1              # Negotiate
ntlmssp.messagetype == 2              # Challenge
ntlmssp.messagetype == 3              # Auth
```

**提取 SMB 传输的文件名：**

```bash
tshark -r file.pcap -Y "smb2.filename" \
  -T fields -e ip.src -e ip.dst -e smb2.filename
```

### 5. 自定义解码（Decode As）

当流量跑在非标准端口上时，强制按某协议解析：

```
# 操作：右键某个包 → Decode As
# 或：Analyze → Decode As → 添加规则

# 常见场景：
# 1. HTTP 跑在 8080 → Decode As → TCP Port 8080 → HTTP
# 2. SSH 跑在 2222 → 不会自动识别，需手动指定
# 3. 自定义协议跑在 TCP 上 → 可按 DATA 看

# tshark 等价
tshark -r file.pcap -d "tcp.port==8080,http"
tshark -r file.pcap -d "udp.port==5060,sip"
```

***

## 八、网络取证工作流

### 1. 流量取证整体思路

拿到一个 pcap 样本，按此流程系统性分析：

```
第 1 步：概览
  ├─ Protocol Hierarchy（协议分布是否正常？）
  ├─ Conversations（谁和谁通信最多？）
  └─ Endpoints（有没有异常 IP/端口？）

第 2 步：时间线分析
  ├─ IO Graph（流量有无突增/突降？）
  ├─ 按时间段过滤（定位异常时段）
  └─ Flow Graph（关键会话的交互序列）

第 3 步：协议深入
  ├─ HTTP（请求/响应/文件/UA）
  ├─ DNS（域名/类型/频率）
  ├─ TLS（SNI/JA3/证书）
  └─ 其他（SMB/FTP/SMTP/SSH）

第 4 步：数据提取
  ├─ Export Objects（文件还原）
  ├─ TCP Stream（会话内容）
  ├─ tshark 字段提取（批量导出）
  └─ 手动重组（分片/编码数据）

第 5 步：报告
  ├─ 时间线还原
  ├─ IoC 提取
  └─ 攻击链描述
```

### 2. 攻击还原——Web 攻击

**SQL 注入攻击还原：**

```
# 1. 找到攻击请求
http.request.method == "POST" and http.request.uri contains "login"
http contains "union select"
http contains "' or 1=1"

# 2. 提取完整攻击序列
tcp.stream eq <攻击流编号>

# 3. 分析注入点与响应
# Follow TCP Stream 看请求和响应的完整对话

# 4. tshark 提取所有含 SQL 特征的请求
tshark -r file.pcap -Y "http.request" \
  -T fields -e frame.time -e ip.src -e http.request.uri \
  | grep -iE "(union|select|insert|drop|--;|1=1)"
```

**命令注入攻击还原：**

```
# 找命令执行特征
http contains "cmd="
http contains "/bin/sh"
http contains "bash -i"
http.response and http contains "root:"

# 反弹 shell 特征
tcp.port == 4444 and tcp.flags.syn == 1

# tshark 提取命令执行结果
tshark -r file.pcap -Y "http.response and http.content_type contains \"text\"" \
  -T fields -e frame.number -e http.response.code -e http.file_data
```

**Webshell 通信检测：**

```
# 特征：周期性 POST + 小请求体 + 可变参数名
http.request.method == "POST" and tcp.len < 500 and http.content_type contains "x-www-form-urlencoded"

# 找高频 POST 到同一 URL（心跳/命令轮询）
# Statistics → HTTP → Requests → 按 Host/URI 统计
```

### 3. 数据外传检测

```
# DNS 隧道
dns.qry.name matches "^[a-zA-Z0-9]{30,}"     # 超长子域
dns.qry.type == 16                             # TXT 记录查询（可携带数据）
dns.qry.type == 10                             # NULL 记录（iodine 工具特征）

# HTTP 隧道
http.request.method == "POST" and tcp.len > 5000 and not http.content_type in {"multipart/form-data" "application/x-www-form-urlencoded"}

# ICMP 隧道
icmp and data and len(data.data) > 64          # ICMP 负载异常大

# 大量出站流量到非常见端口
tcp.flags.syn == 1 and tcp.flags.ack == 0 and not tcp.dstport in {80 443 22 53 25}

# 基线对比法
# 1. 统计正常时段的流量特征（Conversations/Endpoints）
# 2. 对比异常时段的流量特征
# 3. 找出新增的通信对/端口/协议
```

### 4. C2 通信特征识别

```
# Beacon 心跳特征
# 周期性固定大小的通信，间隔均匀
# 过滤某 IP 对的所有流量，IO Graph 看是否呈周期性尖峰
ip.addr == "C2_IP" and tcp.flags.ack == 1

# Cobalt Strike 特征
http.user_agent contains "Mozilla/5.0" and http.request.uri matches "^[A-Za-z0-9]{4,}" and http.request.uri matches "/$"
# CS 默认 UA + 随机 URI + 结尾 /

# Metasploit 特征
http.user_agent contains "Mozilla/4.0" and http.request.uri matches "^/[A-Z]{4}"

# JA3 指纹匹配
tls.handshake.ja3_hash in {"e7d705a3286e19ea42f587b344ee6865" "6734f37431670b3ab4292b8f60f29984"}

# 长连接检测
# Statistics → Conversations → 按持续时间排序，找异常长的连接
```

### 5. 横向移动检测

```
# SMB 横向
smb2.cmd == 2                                   # 大量 Session Setup = 爆破/横向
smb2.filename contains "ADMIN$"                  # 访问管理共享
smb2.filename contains "C$"                      # 访问 C 盘共享
smb2.filename contains "ipc$"                    # IPC 共享

# WMI 横向
tcp.dstport == 135 and dcerpc                    # WMI 走 DCE/RPC

# PSExec 横向
smb2.filename contains "PSEXESVC"                # PSExec 服务名

# RDP 暴力
tcp.dstport == 3389 and tcp.flags.syn == 1 and tcp.flags.ack == 0
# 大量 SYN 到 3389 = 爆破

# 提取横向移动目标
tshark -r file.pcap -Y "smb2.cmd == 2" \
  -T fields -e ip.src -e ip.dst | sort -u
```

### 6. tshark 取证脚本集

```bash
#!/bin/bash
# forensic_quick.sh — 快速取证脚本

PCAP=$1

echo "=== 协议分布 ==="
tshark -r $PCAP -q -z io,phs

echo -e "\n=== Top 10 通信 IP 对 ==="
tshark -r $PCAP -q -z conv,ip | head -20

echo -e "\n=== DNS 查询域名 Top 20 ==="
tshark -r $PCAP -Y "dns.qry.name and dns.flags.response == 0" \
  -T fields -e dns.qry.name | sort | uniq -c | sort -rn | head -20

echo -e "\n=== HTTP 请求 Top 20 ==="
tshark -r $PCAP -Y "http.request" \
  -T fields -e http.host -e http.request.uri | sort | uniq -c | sort -rn | head -20

echo -e "\n=== TLS SNI Top 20 ==="
tshark -r $PCAP -Y "tls.handshake.extensions_server_name" \
  -T fields -e tls.handshake.extensions_server_name | sort | uniq -c | sort -rn | head -20

echo -e "\n=== Expert Info 统计 ==="
tshark -r $PCAP -Y "tcp.analysis.flags" \
  -T fields -e tcp.analysis.flags | sort | uniq -c | sort -rn

echo -e "\n=== 大包 Top 20（可能传文件） ==="
tshark -r $PCAP -Y "tcp.len > 1000" \
  -T fields -e frame.number -e ip.src -e ip.dst -e tcp.len | sort -t$'\t' -k4 -rn | head -20

echo -e "\n=== 可疑端口连接 ==="
tshark -r $PCAP -Y "tcp.flags.syn==1 and tcp.flags.ack==0 and not tcp.dstport in {80 443 22 53}" \
  -T fields -e ip.src -e ip.dst -e tcp.dstport | sort -u
```

***

## 九、性能分析

Wireshark 不仅是安全工具，也是网络性能分析利器。

### 1. TCP 吞吐量分析

```
# Statistics → TCP Stream Graphs → Throughput
# 选择要分析的流编号

# tshark 计算吞吐量
tshark -r file.pcap -q -z conv,tcp | grep <流编号>

# 计算某段时间的平均吞吐量
tshark -r file.pcap -Y "tcp.stream eq 5 and frame.time_relative >= 10 and frame.time_relative <= 20" \
  -T fields -e frame.len | awk '{sum+=$1} END {print sum/10/1024 " KB/s"}'
```

### 2. 延迟分析

```
# RTT 分析
# Statistics → TCP Stream Graphs → Round Trip Time

# 找高延迟包
frame.time_delta > 1 and tcp.flags.ack == 1

# DNS 查询延迟
dns and frame.time_delta_displayed > 0.5

# tshark 提取 TCP RTT
tshark -r file.pcap -Y "tcp.analysis.ack_rtt" \
  -T fields -e ip.src -e ip.dst -e tcp.analysis.ack_rtt
```

### 3. 丢包与重传分析

```
# 丢包指标
tcp.analysis.retransmission       # 重传
tcp.analysis.fast_retransmission  # 快速重传
tcp.analysis.out_of_order         # 乱序
tcp.analysis.duplicate_ack        # 重复 ACK
tcp.analysis.lost_segment         # 丢失段

# 计算重传率
total=$(tshark -r file.pcap -Y "tcp" -T fields -e frame.number | wc -l)
retrans=$(tshark -r file.pcap -Y "tcp.analysis.retransmission" -T fields -e frame.number | wc -l)
echo "重传率: $(echo "scale=2; $retrans*100/$total" | bc)%"

# 找丢包热点（哪个 IP 对丢包最多）
tshark -r file.pcap -Y "tcp.analysis.retransmission" \
  -T fields -e ip.src -e ip.dst | sort | uniq -c | sort -rn | head -10
```

### 4. TCP 窗口分析

```
# 零窗口（接收方过载）
tcp.analysis.zero_window

# 窗口缩放因子
tcp.window_size_scalefactor

# 窗口大小趋势
# Statistics → TCP Stream Graphs → Window Scaling

# 找窗口瓶颈
tcp.window_size < 1024 and tcp.len > 0
```

### 5. 连接建立时间分析

```
# TCP 三次握手耗时
# 测量 SYN → SYN-ACK → ACK 的时间间隔

# 找慢握手（SYN 到 SYN-ACK 间隔大）
tcp.flags.syn == 1 and tcp.flags.ack == 0

# tshark 提取握手时间
tshark -r file.pcap -Y "tcp.flags.syn==1" \
  -T fields -e frame.time -e ip.src -e ip.dst -e tcp.flags.syn -e tcp.flags.ack
```

***

## 十、高级文件雕刻与数据重组

实战指南介绍了 Export Objects 和 Follow TCP Stream，本节覆盖更复杂的场景。

### 1. 从分片 TCP 流中重组文件

当文件跨多个 TCP 段传输且 Export Objects 无法识别时：

```bash
# 第 1 步：定位目标流
tcp.stream eq 5

# 第 2 步：提取单方向数据
tshark -r file.pcap -Y "tcp.stream eq 5 and tcp.srcport == 80" \
  -T fields -e tcp.payload | tr -d '\n:' | xxd -r -p > reassembled.bin

# 第 3 步：验证文件头
xxd reassembled.bin | head -5
file reassembled.bin

# 第 4 步：如果文件头被截断，手动补上
# 例如补 PNG 文件头
printf '\x89PNG\r\n\x1a\n' | cat - reassembled.bin > fixed.png
```

### 2. 从多个流中拼合文件

某些场景下文件被拆分到多个 TCP 流中传输：

```bash
# 提取多个流的数据并拼合
for stream in 3 5 8 12; do
  tshark -r file.pcap -Y "tcp.stream eq $stream and tcp.srcport == 80" \
    -T fields -e tcp.payload | tr -d '\n:' | xxd -r -p
done > combined.bin

# 或按时间顺序排列
tshark -r file.pcap -Y "tcp.port == 80 and tcp.len > 0" \
  -T fields -e frame.time_relative -e tcp.stream -e tcp.payload \
  | sort -n | awk -F'\t' '{print $3}' | tr -d '\n:' | xxd -r -p > combined.bin
```

### 3. 从 HTTP Chunked 编码中还原数据

```bash
# 提取 chunked 响应体
tshark -r file.pcap -Y "http.response and http.content_length == 0" \
  -T fields -e tcp.stream

# 对目标流 Follow TCP Stream，选 Raw 格式保存
# 然后手动去除 chunked 分隔符，或用 Python：
python3 -c "
import sys
data = open(sys.argv[1], 'rb').read()
# 简化处理：按 \\r\\n 分割，跳过 chunk size 行
parts = data.split(b'\r\n')
result = b''
skip = False
for p in parts:
    if skip:
        skip = False
        continue
    try:
        int(p, 16)
        skip = True
    except ValueError:
        result += p
sys.stdout.buffer.write(result)
" raw_stream.bin > decoded.bin
```

### 4. 从 ICMP/DNS 中提取隐蔽数据

```bash
# ICMP 隧道数据提取
tshark -r file.pcap -Y "icmp.type == 8" \
  -T fields -e data.data | tr -d '\n:' | xxd -r -p > icmp_data.bin

# DNS TXT 记录数据提取
tshark -r file.pcap -Y "dns.qry.type == 16 and dns.flags.response == 1" \
  -T fields -e dns.txt | tr -d '\n' > dns_data.txt

# DNS 子域编码数据提取（dnscat2 等）
tshark -r file.pcap -Y "dns.qry.name and dns.flags.response == 0" \
  -T fields -e dns.qry.name | while read line; do
    # 提取子域部分（去掉末尾域名）
    echo "$line" | awk -F. '{print $1}'
  done > dns_subdomains.txt
```

### 5. VoIP 通话还原

Wireshark 可以从 SIP/RTP 流量中还原语音通话：

```
# 菜单：Telephony → VoIP Calls
# 列出所有通话，选中后可：
#   - Play：直接播放
#   - Save：保存为音频文件（au/wav/raw）
#   - Graph：查看通话信令流程图

# 过滤 SIP
sip

# 过滤 RTP
rtp

# 提取 RTP 流统计
tshark -r file.pcap -q -z rtp,streams
```

***

## 十一、自定义协议解析器（Lua 插件）

Wireshark 支持 Lua 脚本编写自定义协议解析器，用于解析私有协议或特殊封装。

### 1. Lua 插件基础结构

```lua
-- my_proto.lua — 最小协议解析器模板

-- 声明协议
local my_proto = Proto("myproto", "My Custom Protocol")

-- 声明字段
local f_version = ProtoField.uint8("myproto.version", "Version", base.DEC)
local f_type    = ProtoField.uint8("myproto.type", "Type", base.HEX)
local f_length  = ProtoField.uint16("myproto.length", "Length", base.DEC)
local f_payload = ProtoField.bytes("myproto.payload", "Payload")

my_proto.fields = { f_version, f_type, f_length, f_payload }

-- 类型名称映射
local type_names = {
    [0x01] = "HELLO",
    [0x02] = "DATA",
    [0x03] = "BYE",
}

-- 解析函数
function my_proto.dissector(buffer, pinfo, tree)
    local buf_len = buffer:len()
    if buf_len < 4 then return end  -- 最小头部 4 字节

    pinfo.cols.protocol = "MYPROTO"

    local subtree = tree:add(my_proto, buffer(), "My Protocol Data")
    local offset = 0

    -- Version (1 byte)
    subtree:add(f_version, buffer(offset, 1))
    offset = offset + 1

    -- Type (1 byte)
    local type_val = buffer(offset, 1):uint()
    local type_item = subtree:add(f_type, buffer(offset, 1))
    type_item:append_text(" (" .. (type_names[type_val] or "Unknown") .. ")")
    offset = offset + 1

    -- Length (2 bytes, big-endian)
    local length_val = buffer(offset, 2):uint()
    subtree:add(f_length, buffer(offset, 2))
    offset = offset + 2

    -- Payload
    if buf_len > offset then
        subtree:add(f_payload, buffer(offset, buf_len - offset))
    end
end

-- 注册到 TCP 端口 9999
local tcp_dissector_table = DissectorTable.get("tcp.port")
tcp_dissector_table:add(9999, my_proto)
```

### 2. 安装 Lua 插件

```bash
# 个人插件目录（推荐）
# Linux:   ~/.local/lib/wireshark/plugins/
# macOS:   ~/.local/lib/wireshark/plugins/
# Windows: %APPDATA%\Wireshark\plugins\

# 全局插件目录
# Linux:   /usr/lib/x86_64-linux-gnu/wireshark/plugins/
# macOS:   /Applications/Wireshark.app/Contents/PlugIns/wireshark/
# Windows: C:\Program Files\Wireshark\plugins\

# 复制插件后重新加载
# 菜单：Help → About Wireshark → Plugins → 点击 Reload
# 或重启 Wireshark

# 验证插件加载
# 菜单：Help → About Wireshark → Plugins 标签页
# 应该能看到 my_proto.lua
```

### 3. 进阶：带状态跟踪的解析器

```lua
-- stateful_proto.lua — 维护会话状态的解析器

local sf_proto = Proto("sfproto", "Stateful Protocol")

-- 字段
local f_seq     = ProtoField.uint32("sfproto.seq", "Sequence", base.DEC)
local f_cmd     = ProtoField.uint8("sfproto.cmd", "Command", base.HEX)
local f_data    = ProtoField.string("sfproto.data", "Data", base.ASCII)

sf_proto.fields = { f_seq, f_cmd, f_data }

-- 会话状态表
local sessions = {}

function sf_proto.dissector(buffer, pinfo, tree)
    local buf_len = buffer:len()
    if buf_len < 5 then return end

    pinfo.cols.protocol = "SFPROTO"

    -- 用 TCP 流编号作为会话 ID
    local stream_id = pinfo.src_port .. "-" .. pinfo.dst_port

    -- 初始化会话状态
    if not sessions[stream_id] then
        sessions[stream_id] = {
            last_seq = 0,
            pkt_count = 0,
        }
    end

    local sess = sessions[stream_id]
    sess.pkt_count = sess.pkt_count + 1

    local subtree = tree:add(sf_proto, buffer(), "Stateful Protocol (Pkt #" .. sess.pkt_count .. ")")
    local offset = 0

    -- Sequence
    local seq = buffer(offset, 4):uint()
    subtree:add(f_seq, buffer(offset, 4))
    offset = offset + 4

    -- 检测序列号跳跃（异常检测）
    if sess.last_seq > 0 and seq ~= sess.last_seq + 1 then
        subtree:add_expert_info(PI_SEQUENCE, PI_WARN,
            "Sequence gap: expected " .. (sess.last_seq + 1) .. " got " .. seq)
    end
    sess.last_seq = seq

    -- Command
    local cmd = buffer(offset, 1):uint()
    subtree:add(f_cmd, buffer(offset, 1))
    offset = offset + 1

    -- Data
    if buf_len > offset then
        subtree:add(f_data, buffer(offset, buf_len - offset))
    end
end

DissectorTable.get("tcp.port"):add(8888, sf_proto)
```

### 4. 调试 Lua 插件

```lua
-- 在脚本中使用 print 输出到控制台
-- 必须从命令行启动 Wireshark 才能看到输出：
-- Linux: wireshark（从终端启动）
-- Windows: wireshark.exe（从 cmd 启动）

function my_proto.dissector(buffer, pinfo, tree)
    print("Dissecting packet: " .. pinfo.number)
    print("  Buffer length: " .. buffer:len())
    print("  Source: " .. tostring(pinfo.src) .. ":" .. pinfo.src_port)
    -- ...
end

-- 也可以用 wireshark 的日志
-- 编辑 → 首选项 → Logging → 勾选 console log level
```

### 5. 实战：CTF 私有协议解析

CTF 流量题经常出现私有协议，编写 Lua 解析器可以极大提高分析效率：

```lua
-- ctf_proto.lua — CTF 常见私有协议解析模板

local ctf_proto = Proto("ctfproto", "CTF Custom Protocol")

local f_magic   = ProtoField.uint16("ctfproto.magic", "Magic", base.HEX)
local f_opcode  = ProtoField.uint8("ctfproto.opcode", "Opcode", base.DEC)
local f_flag    = ProtoField.string("ctfproto.flag", "Flag", base.ASCII)
local f_body    = ProtoField.bytes("ctfproto.body", "Body")

ctf_proto.fields = { f_magic, f_opcode, f_flag, f_body }

local opcodes = {
    [0x01] = "LOGIN",
    [0x02] = "SEND",
    [0x03] = "RECV",
    [0xFF] = "FLAG",
}

function ctf_proto.dissector(buffer, pinfo, tree)
    if buffer:len() < 3 then return end

    -- 检查 Magic Number
    local magic = buffer(0, 2):uint()
    if magic ~= 0xC7F1 then return end  -- 不是本协议，跳过

    pinfo.cols.protocol = "CTFPROTO"
    local subtree = tree:add(ctf_proto, buffer(), "CTF Protocol")
    local offset = 0

    -- Magic
    subtree:add(f_magic, buffer(offset, 2))
    offset = offset + 2

    -- Opcode
    local op = buffer(offset, 1):uint()
    local op_item = subtree:add(f_opcode, buffer(offset, 1))
    op_item:append_text(" (" .. (opcodes[op] or "Unknown") .. ")")
    pinfo.cols.info = opcodes[op] or ("Unknown(0x" .. string.format("%02X", op) .. ")")
    offset = offset + 1

    -- Body
    if buffer:len() > offset then
        local body_len = buffer:len() - offset

        -- 如果是 FLAG 操作码，尝试提取 flag
        if op == 0xFF then
            local flag_str = buffer(offset, body_len):string()
            subtree:add(f_flag, buffer(offset, body_len))
            pinfo.cols.info = pinfo.cols.info .. " " .. flag_str
        else
            subtree:add(f_body, buffer(offset, body_len))
        end
    end
end

-- 尝试注册到常见端口
DissectorTable.get("tcp.port"):add(12345, ctf_proto)
DissectorTable.get("udp.port"):add(12345, ctf_proto)
-- 也可以注册为"heuristic"解析器（自动检测）
```

***

## 十二、pcap 处理工具链

Wireshark 自带一组命令行工具，用于 pcap 文件的拆分、合并、修改、分析。

### 1. capinfos——pcap 文件信息

```bash
# 基本信息摘要
capinfos file.pcap

# 详细信息
capinfos -v file.pcap          # 详细模式

# 只看特定信息
capinfos -c file.pcap          # 包数量
capinfos -s file.pcap          # 文件大小
capinfos -e file.pcap          # 结束时间
capinfos -S file.pcap          # 开始时间
capinfos -d file.pcap          # 持续时间
capinfos -u file.pcap          # 捕获硬件/OS
capinfos -E file.pcap          # 封装类型
capinfos -T file.pcap          # 时间精度

# 批量统计
for f in *.pcap; do echo "$f: $(capinfos -c $f 2>/dev/null | grep packets | awk '{print $NF}')"; done
```

### 2. mergecap——合并 pcap 文件

```bash
# 合并多个 pcap（按时间戳排序）
mergecap -w merged.pcap file1.pcap file2.pcap file3.pcap

# 追加模式（不按时间排序，直接拼接）
mergecap -a -w appended.pcap file1.pcap file2.pcap

# 指定封装格式
mergecap -T pcapng -w merged.pcapng file1.pcap file2.pcap

# 合并环缓冲的轮转文件
mergecap -w full_capture.pcap capture_*.pcap
```

### 3. editcap——编辑 pcap 文件

```bash
# 按时间范围截取
editcap -A "2026-07-10 08:00:00" -B "2026-07-10 09:00:00" input.pcap output.pcap

# 按包数量分割
editcap -c 10000 input.pcap split_    # 每 10000 包一个文件，生成 split_00001.pcap 等

# 按文件大小分割
editcap -C 100 input.pcap split_      # 每文件约 100 KB

# 按时间间隔分割
editcap -i 60 input.pcap split_       # 每 60 秒一个文件

# 去重（删除重复包）
editcap -d input.pcap deduped.pcap

# 删除特定包（配合 tshark）
# 先用 tshark 找到要删除的包号，再用 editcap 删除
editcap -r input.pcap output.pcap 1-50 100-200   # 只保留这些包号

# 修改时间戳（时间偏移）
editcap -t 3600 input.pcap shifted.pcap   # 所有时戳加 3600 秒

# 修改封装类型
editcap -T pcap input_pcapng.pcapng output.pcap   # pcapng 转 pcap

# 剥离冗余信息（减小文件大小）
editcap -s input.pcap stripped.pcap     # 去掉每个包的尾部填充
```

### 4. text2pcap——从文本生成 pcap

```bash
# 从十六进制文本生成 pcap
# hex_data.txt 内容示例：
# 000000 00 0c 29 12 34 56 00 50 56 c0 00 01 08 00 45 00
# 000010 00 3c 1c 42 00 00 40 06 3f 2e c0 a8 01 64 c0 a8

text2pcap hex_data.txt output.pcap

# 指定封装类型
text2pcap -l 228 hex_data.txt output.pcap    # 228 = RAW (无链路层头)
text2pcap -l 101 hex_data.txt output.pcap    # 101 = Raw IP

# 追加到已有 pcap
text2pcap -a hex_data.txt existing.pcap

# 从 ASCII 文本生成
text2pcap -a ascii_data.txt output.pcap
```

> 用途：CTF 中题目给出原始 hex 数据而非 pcap 文件，用 text2pcap 转换后即可用 Wireshark 分析。

### 5. randpkt——随机包生成器（测试用）

```bash
# 生成随机包
randpkt -t dns output.pcap 1000      # 生成 1000 个 DNS 包
randpkt -t http output.pcap 500      # 生成 500 个 HTTP 包
```

### 6. reordercap——按时间戳重排

```bash
# 按 时间戳 重新排序 包
reordercap input.pcap reordered.pcap

# 检查是否已排序
capinfos -v input.pcap | grep "sorted"
```

### 7. dftool——显示过滤器基准测试

```bash
# 测试过滤器性能
dftest -r file.pcap "http.request.method == POST"

# 输出：匹配包数、执行时间（评估复杂过滤器的效率）
```

***

## 十三、tshark 高级用法

实战指南介绍了 tshark 基础读取和字段提取，本节深入管道、输出格式、脚本集成。

### 1. 输出格式

```bash
# 默认文本（类似 Wireshark 包列表）
tshark -r file.pcap

# 字段提取（最常用）
tshark -r file.pcap -T fields -e ip.src -e ip.dst -e tcp.port

# JSON 输出（适合程序处理）
tshark -r file.pcap -T json > output.json

# JSON 流式输出（大数据量）
tshark -r file.pcap -T jsonraw > output.json

# PDML 输出（XML 格式，包含所有协议字段）
tshark -r file.pcap -T pdml > output.xml

# PSML 输出（包摘要 XML）
tshark -r file.pcap -T psml > summary.xml

# EK 输出（Elasticsearch JSON 格式）
tshark -r file.pcap -T ek > output_ek.json

# 自定义格式
tshark -r file.pcap -T fields \
  -E header=y \              # 输出列标题
  -E separator=, \           # CSV 格式
  -E quote=d \               # 双引号包裹
  -e frame.number -e ip.src -e ip.dst -e frame.len
```

### 2. 管道与流式处理

```bash
# 从 stdin 读取（配合 tcpdump/ssh）
tcpdump -i eth0 -w - | tshark -i - -Y "http.request"

# SSH 远程抓包到本地分析
ssh remote "tcpdump -i eth0 -U -w - not port 22" | tshark -i - -Y "dns"

# tshark 输出管道到其他工具
tshark -r file.pcap -Y "http.request" -T fields -e http.host | sort | uniq -c | sort -rn

# 实时监控 HTTP 请求
tshark -i eth0 -Y "http.request" -T fields -e ip.src -e http.host -e http.request.uri

# 实时监控 DNS 查询
tshark -i eth0 -Y "dns.qry.name" -T fields -e ip.src -e dns.qry.name

# 管道到 Python 脚本
tshark -r file.pcap -Y "http.request" -T fields \
  -e frame.number -e ip.src -e http.host -e http.request.uri \
  | python3 analyze.py
```

### 3. 双通道分析（-2 两次遍历）

某些分析需要两次遍历（如 TCP 分析需要看到完整连接）：

```bash
# -2 开启两次遍历模式（性能换准确性）
tshark -r file.pcap -2 -Y "tcp.analysis.retransmission" \
  -T fields -e frame.number -e ip.src -e ip.dst

# -R 在两次遍历中使用显示过滤器（更精确）
tshark -r file.pcap -2 -R "tcp.analysis.retransmission"
```

### 4. 多文件读取与合并分析

```bash
# 读取多个文件
tshark -r file1.pcap -r file2.pcap -r file3.pcap

# 用通配符（shell 展开）
tshark -r capture_0000*.pcap -Y "http.request"

# 配合 mergecap 先合并再分析
mergecap -w merged.pcap part_*.pcap
tshark -r merged.pcap -q -z conv,tcp
```

### 5. 高级统计输出

```bash
# 自定义统计脚本
tshark -r file.pcap -q -z "conv,tcp,tcp.stream,tcp.srcport,tcp.dstport"

# 按字段值分组统计
tshark -r file.pcap -Y "http.request" -T fields -e http.host | sort | uniq -c | sort -rn

# 按时间窗口统计（每 10 秒的包数）
tshark -r file.pcap -T fields -e frame.time_relative | \
  awk '{bucket=int($1/10); count[bucket]++} END {for(b in count) print b*10, count[b]}' | sort -n

# 按 IP 对统计流量
tshark -r file.pcap -T fields -e ip.src -e ip.dst -e frame.len | \
  awk -F'\t' '{key=$1" <-> "$2; sum[key]+=$3} END {for(k in sum) print sum[k], k}' | sort -rn

# TCP 流大小排行
tshark -r file.pcap -Y "tcp.stream" -T fields -e tcp.stream -e frame.len | \
  awk -F'\t' '{sum[$1]+=$2} END {for(s in sum) print sum[s], s}' | sort -rn | head -20
```

### 6. 解密与分析一体化

```bash
# TLS 解密后提取 HTTP 内容
tshark -r encrypted.pcap \
  -o "tls.keylog_file:./keylog.txt" \
  -Y "http.request" \
  -T fields -e http.host -e http.request.uri -e http.user_agent

# TLS 解密后导出 HTTP 对象
tshark -r encrypted.pcap \
  -o "tls.keylog_file:./keylog.txt" \
  --export-objects http,./decrypted_http/

# WPA2 解密后分析 WiFi 流量
tshark -r wifi.pcap \
  -o "wlan.enable_decryption:TRUE" \
  -o "uat:80211_keys:\"wpa-pwd\",\"MySSID:MyPassword\"" \
  -Y "http.request" -T fields -e http.host
```

***

## 十四、自动化分析流水线

### 1. Python + tshark 批量分析

```python
#!/usr/bin/env python3
"""pcap_auto_analyze.py — 自动化流量分析脚本"""

import subprocess
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def tshark(pcap, args):
    """运行 tshark 命令并返回输出"""
    cmd = ["tshark", "-r", str(pcap)] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result.stdout


def protocol_hierarchy(pcap):
    """协议分布"""
    output = tshark(pcap, ["-q", "-z", "io,phs"])
    return output


def top_conversations(pcap, n=10):
    """Top N 通信对"""
    output = tshark(pcap, [
        "-q", "-z", "conv,ip",
        "-T", "fields",
        "-e", "ip.src", "-e", "ip.dst", "-e", "frame.len",
    ])
    conv = defaultdict(int)
    for line in output.strip().split("\n"):
        parts = line.split("\t")
        if len(parts) >= 3:
            try:
                key = f"{parts[0]} <-> {parts[1]}"
                conv[key] += int(parts[2])
            except ValueError:
                continue
    return sorted(conv.items(), key=lambda x: x[1], reverse=True)[:n]


def dns_queries(pcap):
    """DNS 查询域名统计"""
    output = tshark(pcap, [
        "-Y", "dns.qry.name and dns.flags.response == 0",
        "-T", "fields", "-e", "dns.qry.name",
    ])
    domains = [line.strip() for line in output.strip().split("\n") if line.strip()]
    return Counter(domains).most_common(20)


def http_requests(pcap):
    """HTTP 请求统计"""
    output = tshark(pcap, [
        "-Y", "http.request",
        "-T", "fields",
        "-e", "http.host", "-e", "http.request.method",
        "-e", "http.request.uri",
    ])
    reqs = []
    for line in output.strip().split("\n"):
        parts = line.split("\t")
        if len(parts) >= 3:
            reqs.append({
                "host": parts[0],
                "method": parts[1],
                "uri": parts[2],
            })
    return reqs


def suspicious_indicators(pcap):
    """可疑指标检测"""
    indicators = []

    # 超长 DNS 子域
    output = tshark(pcap, [
        "-Y", 'dns.qry.name matches "^[a-zA-Z0-9]{30,}"',
        "-T", "fields", "-e", "dns.qry.name",
    ])
    if output.strip():
        indicators.append({
            "type": "DNS Tunnel (long subdomain)",
            "details": output.strip().split("\n")[:5],
        })

    # 非 200 HTTP 响应
    output = tshark(pcap, [
        "-Y", "http.response.code != 200",
        "-T", "fields",
        "-e", "http.response.code", "-e", "http.request.uri",
    ])
    if output.strip():
        indicators.append({
            "type": "Non-200 HTTP responses",
            "count": len(output.strip().split("\n")),
        })

    # TCP 重传
    output = tshark(pcap, [
        "-Y", "tcp.analysis.retransmission",
        "-T", "fields", "-e", "ip.src", "-e", "ip.dst",
    ])
    if output.strip():
        indicators.append({
            "type": "TCP Retransmissions",
            "count": len(output.strip().split("\n")),
        })

    # 大包
    output = tshark(pcap, [
        "-Y", "tcp.len > 10000",
        "-T", "fields", "-e", "ip.src", "-e", "ip.dst", "-e", "tcp.len",
    ])
    if output.strip():
        indicators.append({
            "type": "Large packets (possible file transfer)",
            "count": len(output.strip().split("\n")),
        })

    return indicators


def analyze(pcap_path):
    """主分析函数"""
    pcap = Path(pcap_path)
    if not pcap.exists():
        print(f"File not found: {pcap}", file=sys.stderr)
        sys.exit(1)

    print(f"=== Analyzing: {pcap.name} ===\n")

    print("--- Protocol Hierarchy ---")
    print(protocol_hierarchy(pcap))

    print("\n--- Top Conversations ---")
    for conv, size in top_conversations(pcap):
        print(f"  {conv}: {size} bytes")

    print("\n--- DNS Queries (Top 20) ---")
    for domain, count in dns_queries(pcap):
        print(f"  {domain}: {count}")

    print("\n--- HTTP Requests ---")
    for req in http_requests(pcap)[:20]:
        print(f"  {req['method']} {req['host']}{req['uri']}")

    print("\n--- Suspicious Indicators ---")
    for ind in suspicious_indicators(pcap):
        print(f"  [{ind['type']}]")
        if "details" in ind:
            for d in ind["details"]:
                print(f"    {d}")
        elif "count" in ind:
            print(f"    Count: {ind['count']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <pcap_file>", file=sys.stderr)
        sys.exit(1)
    analyze(sys.argv[1])
```

### 2. 批量 pcap 处理

```bash
#!/bin/bash
# batch_analyze.sh — 批量分析目录下所有 pcap 文件

DIR=${1:-.}

for pcap in "$DIR"/*.pcap "$DIR"/*.pcapng; do
    [ -f "$pcap" ] || continue
    echo "========================================"
    echo "File: $pcap"
    echo "Size: $(du -h "$pcap" | cut -f1)"
    echo "Packets: $(capinfos -c "$pcap" 2>/dev/null | grep 'Number of packets' | awk '{print $NF}')"
    echo "Duration: $(capinfos -d "$pcap" 2>/dev/null | grep 'Capture duration' | awk '{print $NF}')"
    echo "---"
    tshark -r "$pcap" -q -z io,phs 2>/dev/null | head -20
    echo ""
done
```

### 3. 实时监控脚本

```bash
#!/bin/bash
# live_monitor.sh — 实时流量监控

INTERFACE=${1:-eth0}
ALERT_THRESHOLD=100  # 每秒包数告警阈值

echo "Monitoring interface: $INTERFACE"
echo "Alert threshold: $ALERT_THRESHOLD pkts/sec"
echo "Press Ctrl+C to stop"
echo ""

tshark -i $INTERFACE -q -z io,stat,1 2>/dev/null | while read line; do
    # 解析每秒统计
    pps=$(echo "$line" | awk '{print $2}')
    if [ -n "$pps" ] && [ "$pps" -gt "$ALERT_THRESHOLD" ] 2>/dev/null; then
        echo "[ALERT] $(date '+%H:%M:%S') High traffic: $pps pkts/sec"
    fi
done
```

### 4. 与其他工具联动

```bash
# tshark → Zeek (Bro) 联动
# 导出 PCAP 给 Zeek 分析
zeek -r file.pcap

# tshark → ELK 联动
# 输出 JSON 格式供 Elasticsearch 索引
tshark -r file.pcap -T json > for_elk.json

# tshark → NetworkMiner
# 直接用 NetworkMiner 打开 pcap
networkminer file.pcap

# tshark → Arkime (moloch)
# Arkime 自带抓包和索引功能
# 也可导入已有 pcap

# 从 tshark 提取 IoC 供威胁情报平台查询
tshark -r file.pcap -Y "dns.qry.name" -T fields -e dns.qry.name | \
  sort -u | while read domain; do
    # 查询 VirusTotal 等
    curl -s "https://www.virustotal.com/api/v3/domains/$domain" \
      -H "x-apikey: YOUR_KEY" | jq '.data.attributes.last_analysis_stats'
  done
```

***

## 十五、速查表

### 高级显示过滤器速查

```
# 函数
upper(http.user_agent) contains "CURL"        # 大小写不敏感
len(http.request.uri) > 100                   # 字段长度
string(tcp.port) == "443"                     # 数值转字符串
exists http.cookie                            # 字段存在性
tcp.port in {80 443 8080}                     # 集合匹配

# 切片
ip.ttl[0] == 64                               # IP TTL
tcp.flags[0] & 0x02 == 0x02                   # SYN 标志
eth.type[0:2] == 0x0800                       # 以太类型 IPv4

# 时间
frame.time >= "2026-07-10 08:00:00"           # 绝对时间
frame.time_relative > 60                      # 相对时间
frame.time_delta > 5                          # 包间隔

# 协议层级
ip.src#1 == 10.0.0.1                          # 外层 IP
ip.src#2 == 192.168.1.1                       # 内层 IP

# 复杂组合
http.request.uri matches "(?i)(union|select)" # 正则
dns.qry.name matches "^[a-zA-Z0-9]{30,}"      # DNS 隧道
tls.handshake.type == 1 and tls.handshake.extensions_server_name contains "evil"
```

### Expert Info 过滤器速查

```
tcp.analysis.retransmission                   # 重传
tcp.analysis.fast_retransmission              # 快速重传
tcp.analysis.out_of_order                     # 乱序
tcp.analysis.duplicate_ack                    # 重复 ACK
tcp.analysis.lost_segment                     # 丢失段
tcp.analysis.zero_window                      # 零窗口
tcp.analysis.window_update                    # 窗口更新
tcp.checksum_bad == 1                         # 校验和错误
ip.checksum_bad == 1                          # IP 校验和错误
```

### tshark 高级命令速查

```bash
# 输出格式
tshark -r f.pcap -T json                      # JSON
tshark -r f.pcap -T pdml                      # XML (全字段)
tshark -r f.pcap -T fields -E header=y -E separator=,  # CSV

# 管道
tcpdump -i eth0 -w - | tshark -i -            # 实时管道
ssh h "tcpdump -U -w -" | tshark -i -         # 远程管道

# 解密
tshark -r f.pcap -o "tls.keylog_file:keylog.txt" -Y "http.request"
tshark -r f.pcap -o "uat:80211_keys:\"wpa-pwd\",\"SSID:PASS\"" -Y "http"

# 两次遍历
tshark -r f.pcap -2 -Y "tcp.analysis.retransmission"

# 字段提取组合
tshark -r f.pcap -Y "http.request" -T fields -e ip.src -e http.host -e http.request.uri
tshark -r f.pcap -Y "tls.handshake.type==1" -T fields -e ip.src -e tls.handshake.extensions_server_name
```

### pcap 工具链速查

```bash
capinfos file.pcap                            # 文件信息
mergecap -w out.pcap a.pcap b.pcap            # 合并
editcap -A "08:00:00" -B "09:00:00" in.pcap out.pcap  # 按时间截取
editcap -c 10000 in.pcap prefix_              # 按包数分割
editcap -d in.pcap out.pcap                   # 去重
text2pcap hex.txt out.pcap                    # hex 转 pcap
reordercap in.pcap out.pcap                   # 时间戳重排
```

### Lua 解析器模板速查

```lua
-- 最小模板
local p = Proto("name", "Description")
local f1 = ProtoField.uint8("name.f1", "Field1")
p.fields = {f1}

function p.dissector(buf, pinfo, tree)
    pinfo.cols.protocol = "NAME"
    local sub = tree:add(p, buf())
    sub:add(f1, buf(0, 1))
end

DissectorTable.get("tcp.port"):add(9999, p)
```

### 取证分析流程速查

```
1. capinfos / Protocol Hierarchy          → 概览
2. Conversations / Endpoints              → 通信对
3. IO Graph                               → 时间线
4. Expert Info                            → 异常
5. HTTP/DNS/TLS 过滤                      → 协议深入
6. Export Objects / Follow Stream         → 数据提取
7. tshark 批量导出                        → 脚本化
8. Lua 解析器（私有协议）                  → 自定义
```

### 常用端口-协议映射速查

| 端口 | 协议 | 过滤器 |
|------|------|--------|
| 20/21 | FTP | ftp |
| 22 | SSH | ssh |
| 23 | Telnet | telnet |
| 25 | SMTP | smtp |
| 53 | DNS | dns |
| 80 | HTTP | http |
| 110 | POP3 | pop |
| 143 | IMAP | imap |
| 161/162 | SNMP | snmp |
| 389 | LDAP | ldap |
| 443 | HTTPS | tls |
| 445 | SMB | smb or smb2 |
| 993 | IMAPS | imap and tls |
| 1433 | MSSQL | tds |
| 3306 | MySQL | mysql |
| 3389 | RDP | rdp |
| 5432 | PostgreSQL | pgsql |
| 5900 | VNC | vnc |
| 6379 | Redis | redis |
| 8080 | HTTP Alt | http (需 Decode As) |
| 8443 | HTTPS Alt | tls |
| 9200 | Elasticsearch | http (需 Decode As) |
| 27017 | MongoDB | mongo |

# tshark 实战使用指南

> Wireshark 的命令行引擎——从抓包过滤到字段提取，从协议统计到文件还原，从管道流式处理到脚本化自动化，每个场景都有可复制的命令。GUI 看包用 Wireshark，批量分析和脚本化取证靠 tshark。

---

## 目录

- [一、tshark 是什么](#一tshark-是什么)
- [二、安装与环境配置](#二安装与环境配置)
- [三、核心概念与命令结构](#三核心概念与命令结构)
- [四、抓包：从网卡到文件](#四抓包从网卡到文件)
- [五、读包与过滤](#五读包与过滤)
- [六、字段提取（-T fields）](#六字段提取-t-fields)
- [七、输出格式与定制](#七输出格式与定制)
- [八、统计分析](#八统计分析)
- [九、协议分析实战](#九协议分析实战)
- [十、文件还原与对象导出](#十文件还原与对象导出)
- [十一、TLS 解密](#十一tls-解密)
- [十二、管道与流式处理](#十二管道与流式处理)
- [十三、脚本化自动化](#十三脚本化自动化)
- [十四、实战技巧与踩坑](#十四实战技巧与踩坑)
- [十五、速查表](#十五速查表)

---

## 一、tshark 是什么

tshark 是 Wireshark 发行包中的命令行网络协议分析器。它与 Wireshark 共享同一套协议解析引擎（libwireshark），但以终端方式运行，不依赖 GUI。这意味着 Wireshark 能解析的协议，tshark 全部支持；Wireshark 的显示过滤器语法，tshark 原样可用。

### tshark vs Wireshark vs tcpdump

| 维度 | tshark | Wireshark | tcpdump |
|------|--------|-----------|---------|
| 界面 | 命令行 | GUI | 命令行 |
| 协议解析深度 | 全协议栈深度解析 | 全协议栈深度解析 | 仅基础协议头 |
| 过滤器 | 显示过滤器 + BPF | 显示过滤器 + BPF | 仅 BPF |
| 字段提取 | 精确到协议字段 | 点击查看 | 仅原始包内容 |
| 脚本集成 | 天然支持管道和格式化输出 | 不支持 | 基础支持 |
| 大文件处理 | 可无界面高效运行 | 大文件卡顿 | 轻量快速 |
| 适用场景 | 批量分析、自动化、CI/CD、远程服务器 | 单文件深度分析、人工排查 | 快速抓包、轻量过滤 |

> 核心判断：需要逐包人眼审视用 Wireshark，需要批量提取/统计/自动化用 tshark，需要轻量快速抓包用 tcpdump。

### 与已有文档的关系

本文档是 tshark 的独立实战指南，全面覆盖从基础到高级的用法。[Wireshark实战使用指南](Wireshark实战使用指南.md) 中的 tshark 小节覆盖了最基础的读取和提取命令，[Wireshark深度使用手册](Wireshark深度使用手册.md) 中的 tshark 小节覆盖了管道和 JSON 输出。本文档在基础部分简要回顾后，重点展开实战场景和脚本化用法。

---

## 二、安装与环境配置

### 1. 安装

tshark 随 Wireshark 一起安装，无需单独安装。

```bash
# Kali Linux — 已预装
tshark --version

# Debian/Ubuntu
sudo apt install -y tshark
# 或安装完整 Wireshark（包含 tshark）
sudo apt install -y wireshark

# macOS
brew install wireshark
# 或仅安装 tshark（无 GUI）
brew install --cask wireshark-chmodbpf

# Windows
# 安装 Wireshark 后 tshark.exe 在安装目录下
# 建议加入 PATH：C:\Program Files\Wireshark
```

### 2. 权限配置

tshark 抓包需要 root 权限或加入 wireshark 组：

```bash
# 允许非 root 用户抓包
sudo usermod -aG wireshark $USER
# 重新登录后生效

# 验证权限
tshark -i eth0 -c 1
# 若报 "Permission denied" 则权限未生效
```

### 3. 确认安装

```bash
tshark --version
# 输出 Wireshark 版本和编译信息

# 查看可用网卡
tshark -D
# 输出编号和网卡名，如：
# 1. eth0
# 2. wlan0
# 3. lo
# 4. bluetooth0
```

---

## 三、核心概念与命令结构

### 1. 命令结构

tshark 命令由三部分组成：输入源、过滤条件、输出控制。

```
tshark [输入源] [过滤条件] [输出控制]
```

- 输入源：`-r file.pcap` 读文件，`-i eth0` 抓网卡
- 过滤条件：`-Y "display filter"` 显示过滤，`-f "bpf"` 捕获过滤
- 输出控制：`-T fields -e field_name` 提取字段，`-w output.pcap` 写文件

### 2. 两类过滤器

与 Wireshark 一致，tshark 也有两套过滤器：

| 过滤器 | 参数 | 语法 | 作用时机 |
|--------|------|------|----------|
| 捕获过滤器 | -f | BPF 语法 | 抓包时，决定哪些包进入 |
| 显示过滤器 | -Y | Wireshark 显示过滤器语法 | 解析后，决定哪些包输出 |

```bash
# 捕获过滤器（BPF）：只抓 80 端口
tshark -i eth0 -f "tcp port 80"

# 显示过滤器：只显示 HTTP POST
tshark -r file.pcap -Y "http.request.method == POST"

# 两者可以同时使用
tshark -i eth0 -f "tcp port 80" -Y "http.request.method == POST"
```

> BPF 语法仅支持协议名、端口、IP、方向等基础条件。需要按协议字段过滤时必须用显示过滤器。

### 3. 常用参数一览

```
输入源
  -r <file>           读取 pcap 文件
  -i <interface>      指定网卡抓包
  -c <count>          只抓/读前 N 个包

过滤
  -f <bpf>            捕获过滤器（BPF 语法）
  -Y <filter>         显示过滤器（Wireshark 语法）
  -2                  两次遍历模式（提高准确性，降低性能）
  -R <filter>         在两次遍历中使用显示过滤器（需配合 -2）

输出格式
  -T fields           字段提取模式
  -T json             JSON 格式
  -T pdml             XML 格式（含所有协议字段）
  -T psml             包摘要 XML
  -T ek               Elasticsearch JSON 格式
  -e <field>          指定提取的字段（配合 -T fields）

输出控制
  -E header=y         输出列标题（配合 -T fields）
  -E separator=<char> 设置分隔符（配合 -T fields）
  -E quote=d          双引号包裹（配合 -T fields）
  -w <file>           写入 pcap 文件
  -V                  详细输出（类似 Wireshark 包详情）

统计
  -q                  安静模式（统计时不输出逐包信息）
  -z <stat>           统计选项

其他
  --export-objects <proto>,<dir>  导出协议传输的文件
  -o <preference>                设置首选项
  -b <ringbuffer>                环缓冲参数
  -a <autostop>                  自动停止条件
```

---

## 四、抓包：从网卡到文件

### 1. 基础抓包

```bash
# 抓包并实时输出到终端
tshark -i eth0

# 只抓 100 个包
tshark -i eth0 -c 100

# 抓包并存入文件
tshark -i eth0 -w capture.pcap

# 抓 80 端口并存入文件
tshark -i eth0 -f "tcp port 80" -w http.pcap
```

### 2. 自动停止条件

```bash
# 抓满 1000 个包停止
tshark -i eth0 -a count:1000 -w capture.pcap

# 抓 60 秒后停止
tshark -i eth0 -a duration:60 -w capture.pcap

# 文件达到 100 MB 后停止
tshark -i eth0 -a filesize:102400 -w capture.pcap
```

### 3. 环缓冲抓包

长时间监控时，pcap 文件会持续增长。环缓冲按大小或时间轮转，始终保留最新数据：

```bash
# 每个文件 100 MB，保留 10 个文件轮转
tshark -i eth0 -w capture.pcap \
  -b filesize:102400 \
  -b files:10

# 每 300 秒创建新文件，保留 5 个
tshark -i eth0 -w capture.pcap \
  -b interval:300 \
  -b files:5
```

> 场景：7x24 监控内网出口流量、应急响应期间持续取证。环缓冲确保磁盘不会撑爆，同时保留最近的流量窗口。

### 4. 多网卡抓包

```bash
# 同时监听多个网卡
tshark -i eth0 -i eth1 -w dual_capture.pcap
```

### 5. 远程抓包

在无 GUI 的远程服务器上抓包，传输到本地分析：

```bash
# 方式一：远程 tcpdump 抓包，管道传输到本地 tshark 分析
ssh user@remote "tcpdump -i eth0 -U -w - not port 22" | tshark -i - -Y "http.request"

# 方式二：远程抓包存文件，scp 取回
ssh user@remote "tshark -i eth0 -c 10000 -w /tmp/remote.pcap"
scp user@remote:/tmp/remote.pcap ./

# 方式三：rpcapd 远程抓包守护进程
# 远程服务器启动：
rpcapd -n -p 2002
# 本地连接：
tshark -i rpcap://remote:2002/eth0 -w remote.pcap
```

---

## 五、读包与过滤

### 1. 基础读取

```bash
# 读取 pcap（输出概要，类似 Wireshark 包列表）
tshark -r file.pcap

# 只读前 10 个包
tshark -r file.pcap -c 10

# 详细输出（类似 Wireshark 点击包后的详情面板）
tshark -r file.pcap -V

# 读取多个文件
tshark -r part1.pcap -r part2.pcap -r part3.pcap

# 配合 mergecap 先合并再分析
mergecap -w merged.pcap part_*.pcap
tshark -r merged.pcap -q -z conv,tcp
```

### 2. 显示过滤器

显示过滤器是 tshark 最核心的过滤手段，语法与 Wireshark 完全一致：

```bash
# 只看 HTTP 请求
tshark -r file.pcap -Y "http.request"

# POST 请求
tshark -r file.pcap -Y "http.request.method == POST"

# 指定 IP
tshark -r file.pcap -Y "ip.addr == 192.168.1.100"

# 指定端口
tshark -r file.pcap -Y "tcp.port == 4444"

# 组合条件
tshark -r file.pcap -Y "http.request.method == POST and http contains \"password\""

# 排除噪声
tshark -r file.pcap -Y "not (arp or dns or icmp or tcp.port == 443)"
```

### 3. 捕获过滤器（读文件时过滤）

读 pcap 文件时，-f 参数也可以用于预过滤，减少 tshark 处理的包数量：

```bash
# 从大 pcap 中只读 TCP 80 端口的包
tshark -r file.pcap -f "tcp port 80"

# 只读特定 IP 的包
tshark -r file.pcap -f "host 10.0.0.1"
```

> 读文件时 -f 和 -Y 的区别：-f 在读取阶段过滤（减少解析量，更快），-Y 在解析后过滤（更精确）。两者可组合使用。

### 4. 两次遍历模式

某些分析需要看到完整连接信息（如 TCP 流重组、重传分析），单次遍历可能不完整。加 -2 启用两次遍历：

```bash
# 精确检测 TCP 重传
tshark -r file.pcap -2 -R "tcp.analysis.retransmission"

# 精确的 TCP 流分析
tshark -r file.pcap -2 -Y "tcp.stream eq 5"
```

> 两次遍历需要把整个文件读两遍，大文件会明显变慢。仅在需要精确 TCP 分析时使用。

### 5. 常用显示过滤器速查

```
# 协议
http / dns / tcp / udp / icmp / tls / smb / ftp / smtp / arp

# HTTP
http.request                                    # 所有请求
http.request.method == "POST"                   # POST 请求
http.request.uri contains "login"               # URI 含 login
http.response.code == 200                       # 200 响应
http.host == "example.com"                      # Host 头
http.user_agent contains "curl"                 # UA
http.cookie contains "session"                  # Cookie
http.contains "flag"                            # 任意字段含 flag

# IP / 端口
ip.addr == 10.0.0.1                             # 涉及该 IP
ip.src == 10.0.0.1 / ip.dst == 10.0.0.1
tcp.port == 8080                                # 端口
tcp.srcport == 12345 / tcp.dstport == 80

# DNS
dns.qry.name == "example.com"                  # 查询域名
dns.qry.type == 1                               # A 记录
dns.flags.response == 1                         # DNS 响应

# TLS
tls.handshake.type == 1                         # Client Hello
tls.handshake.extensions_server_name contains "evil"

# 内容搜索
tcp contains "flag"                             # TCP 负载含 flag
data contains "flag{"                           # 原始数据
tcp.payload contains "admin"                    # TCP 负载 hex 搜索

# TCP 标志
tcp.flags.syn == 1 and tcp.flags.ack == 0       # SYN 扫描
tcp.flags.reset == 1                            # RST
tcp.analysis.retransmission                     # 重传

# 大包（可能传文件）
tcp.len > 1000

# 时间范围
frame.time >= "2024-01-01 10:00:00"
```

---

## 六、字段提取（-T fields）

字段提取是 tshark 最强大的能力，也是区别于 tcpdump 的核心功能。可以精确提取任意协议的任意字段。

### 1. 基础提取

```bash
# 提取源 IP 和目的 IP
tshark -r file.pcap -T fields -e ip.src -e ip.dst

# 提取 HTTP 请求的 Host 和 URI
tshark -r file.pcap -Y "http.request" -T fields -e http.host -e http.request.uri

# 提取 DNS 查询域名
tshark -r file.pcap -Y "dns.qry.name" -T fields -e dns.qry.name
```

### 2. 多字段提取

多个 -e 参数，输出以制表符分隔：

```bash
# 提取 HTTP 请求的完整信息
tshark -r file.pcap -Y "http.request" -T fields \
  -e frame.number \
  -e ip.src \
  -e ip.dst \
  -e http.request.method \
  -e http.host \
  -e http.request.uri

# 输出示例：
# 1       10.0.0.5        10.0.0.1        GET     example.com     /
# 2       10.0.0.5        10.0.0.1        POST    example.com     /login
```

### 3. 格式化输出

```bash
# CSV 格式（带列标题）
tshark -r file.pcap -Y "http.request" -T fields \
  -E header=y \
  -E separator=, \
  -E quote=d \
  -e frame.number -e ip.src -e http.host -e http.request.uri

# 输出示例：
# "frame.number","ip.src","http.host","http.request.uri"
# "1","10.0.0.5","example.com","/"

# 用 | 分隔
tshark -r file.pcap -T fields -E separator='|' -e ip.src -e ip.dst
```

### 4. 提取数据内容

```bash
# 提取 HTTP 响应体
tshark -r file.pcap -Y "http.response" -T fields -e http.file_data

# 提取 TCP 负载（hex 格式）
tshark -r file.pcap -Y "tcp.port==4444" -T fields -e tcp.payload

# 提取原始数据
tshark -r file.pcap -Y "tcp.port==4444" -T fields -e data

# 提取 hex 流量并转为二进制文件
tshark -r file.pcap -Y "tcp.port==4444" -T fields -e data | \
  tr -d '\n:' | xxd -r -p > out.bin

# 提取 TCP 负载拼接为二进制
tshark -r file.pcap -Y "tcp.port==4444" -T fields -e tcp.payload | \
  tr -d '\n:' | xxd -r -p > payload.bin

# 提取 HTTP POST 表单数据
tshark -r file.pcap -Y 'http.request.method == "POST"' -T fields \
  -e http.file_data
```

### 5. 提取协议特定字段

```bash
# HTTP
tshark -r file.pcap -Y "http" -T fields \
  -e http.request.method \
  -e http.request.uri \
  -e http.response.code \
  -e http.content_type \
  -e http.user_agent \
  -e http.cookie \
  -e http.authorization

# DNS
tshark -r file.pcap -Y "dns" -T fields \
  -e dns.qry.name \
  -e dns.qry.type \
  -e dns.a \
  -e dns.flags.response

# TLS/SSL
tshark -r file.pcap -Y "tls.handshake" -T fields \
  -e ip.dst \
  -e tls.handshake.type \
  -e tls.handshake.extensions_server_name \
  -e tls.handshake.ciphersuite

# ICMP
tshark -r file.pcap -Y "icmp" -T fields \
  -e ip.src -e ip.dst -e icmp.type -e data

# USB（键鼠取证）
tshark -r usb.pcap -Y "usb.capdata" -T fields -e usb.capdata
```

### 6. 查找可用字段名

不确定字段名时，用 -V 查看详细输出找到字段名：

```bash
# 查看某个包的所有字段
tshark -r file.pcap -c 1 -V

# 在详细输出中搜索字段名
# 如看到 "Hypertext Transfer Protocol" 下有 "User-Agent: xxx"
# 则字段名为 http.user_agent

# 也可以用 Wireshark：右键字段 → Copy → Field Name
```

---

## 七、输出格式与定制

### 1. 文本输出（默认）

```bash
# 默认输出：一行一个包的摘要
tshark -r file.pcap

# 输出示例：
# 1 0.000000 10.0.0.5 → 10.0.0.1 TCP 74 54321 → 80 [SYN]
# 2 0.000123 10.0.0.1 → 10.0.0.5 TCP 74 80 → 54321 [SYN, ACK]
```

### 2. 字段提取（-T fields）

最常用的输出模式，精确控制输出内容。详见第六章。

### 3. JSON 输出

```bash
# 完整 JSON（包含所有协议字段）
tshark -r file.pcap -T json > output.json

# 流式 JSON（适合大文件，逐包输出）
tshark -r file.pcap -T jsonraw > output.json

# Elasticsearch 格式
tshark -r file.pcap -T ek > output_ek.json

# 仅提取特定字段的 JSON
tshark -r file.pcap -Y "http.request" -T json \
  -e http.host -e http.request.uri
```

JSON 输出结构示例：

```json
{
  "_index": "packets-2024-01-01",
  "_type": "doc",
  "_source": {
    "layers": {
      "frame": { "frame.number": ["1"] },
      "ip": { "ip.src": ["10.0.0.5"], "ip.dst": ["10.0.0.1"] },
      "http": { "http.request.method": ["GET"] }
    }
  }
}
```

### 4. XML 输出

```bash
# PDML：包含所有协议字段的详细 XML
tshark -r file.pcap -T pdml > output.xml

# PSML：包摘要 XML
tshark -r file.pcap -T psml > summary.xml
```

PDML 输出结构示例：

```xml
<packet>
  <proto name="ip">
    <field name="ip.src" show="10.0.0.5" value="0a000005"/>
    <field name="ip.dst" show="10.0.0.1" value="0a000001"/>
  </proto>
  <proto name="http">
    <field name="http.request.method" show="GET" value="474554"/>
  </proto>
</packet>
```

### 5. CSV 输出

```bash
# 标准 CSV
tshark -r file.pcap -Y "http.request" -T fields \
  -E header=y \
  -E separator=, \
  -E quote=d \
  -e frame.number -e ip.src -e ip.dst \
  -e http.request.method -e http.host -e http.request.uri \
  > http_requests.csv
```

### 6. 自定义列输出

```bash
# 用 -o 配置自定义列格式
tshark -r file.pcap \
  -o "gui.column.format:%m,%t,%s,%d,%p" \
  -c 5
# %m = 帧号, %t = 时间, %s = 源, %d = 目的, %p = 协议
```

---

## 八、统计分析

tshark 的 -z 参数提供丰富的内置统计功能，无需外部脚本即可完成常见统计。

### 1. 协议层级统计

```bash
# 查看流量中各协议占比
tshark -r file.pcap -q -z io,phs

# 输出示例：
# ===================================================================
# Protocol Hierarchy Statistics
# ===================================================================
# Eth        frames:1000  bytes:75000
#   IP       frames:980   bytes:73000
#     TCP    frames:800   bytes:62000
#       HTTP frames:300   bytes:35000
#     UDP    frames:180   bytes:11000
#       DNS  frames:120   bytes:6000
#   ARP     frames:20    bytes:2000
```

> 第一步分析新 pcap 的必做操作，快速了解流量组成。

### 2. 会话统计

```bash
# TCP 会话统计（谁和谁通信最多）
tshark -r file.pcap -q -z conv,tcp

# UDP 会话统计
tshark -r file.pcap -q -z conv,udp

# IP 会话统计
tshark -r file.pcap -q -z conv,ip

# 以太网会话统计
tshark -r file.pcap -q -z conv,eth
```

输出包含：地址对、帧数、字节数、持续时间。按字节数排序即可找到通信量最大的连接。

### 3. 端点统计

```bash
# IP 端点统计（哪些 IP 最活跃）
tshark -r file.pcap -q -z endpoints,ip

# TCP 端点统计
tshark -r file.pcap -q -z endpoints,tcp

# UDP 端点统计
tshark -r file.pcap -q -z endpoints,udp
```

### 4. HTTP 统计

```bash
# HTTP 请求分布
tshark -r file.pcap -q -z http,tree

# 输出包含：请求方法分布、响应码分布、Host 统计、URI 统计
```

### 5. DNS 统计

```bash
# DNS 查询统计
tshark -r file.pcap -q -z dns,tree

# 输出包含：查询类型分布、响应码分布、查询域名统计
```

### 6. IO 吞吐量统计

```bash
# 整体吞吐量
tshark -r file.pcap -q -z io,stat

# 按时间段统计（每 1 秒的吞吐量）
tshark -r file.pcap -q -z "io,stat,1"

# 按特定过滤条件统计
tshark -r file.pcap -q -z "io,stat,1,http,tcp"
```

### 7. 专家信息

```bash
# 查看 Wireshark 专家系统标记的异常
tshark -r file.pcap -q -z expert

# 按严重级别过滤
tshark -r file.pcap -q -z expert | grep -i "error\|warning"
```

---

## 九、协议分析实战

### 1. HTTP 流量分析

CTF 和应急响应中最常见的流量类型。

```bash
# 列出所有 HTTP 请求
tshark -r file.pcap -Y "http.request" -T fields \
  -e frame.number -e ip.src -e http.request.method \
  -e http.host -e http.request.uri

# 找 POST 请求（可能上传了文件或提交了密码）
tshark -r file.pcap -Y "http.request.method == POST" -T fields \
  -e frame.number -e ip.src -e http.request.uri -e http.content_type

# 找带密码/凭据的请求
tshark -r file.pcap -Y 'http.request.method == "POST" and http contains "password"' -T fields \
  -e frame.number -e ip.src -e http.request.uri -e http.file_data

# 找命令执行结果
tshark -r file.pcap -Y 'http.response and (http contains "root:" or http contains "uid=")' -T fields \
  -e frame.number -e http.response.code -e http.file_data

# 统计 HTTP 状态码分布
tshark -r file.pcap -Y "http.response" -T fields -e http.response.code | sort | uniq -c | sort -rn

# 统计访问最多的 URL
tshark -r file.pcap -Y "http.request" -T fields -e http.request.uri | sort | uniq -c | sort -rn | head -20

# 统计 User-Agent
tshark -r file.pcap -Y "http.request" -T fields -e http.user_agent | sort | uniq -c | sort -rn

# 搜索 HTTP 中的关键字
tshark -r file.pcap -Y "http contains \"flag\"" -T fields \
  -e frame.number -e http.file_data

# 提取 HTTP Basic Auth 凭据
tshark -r file.pcap -Y "http.authorization" -T fields \
  -e ip.src -e http.authorization
```

### 2. DNS 流量分析

```bash
# 列出所有 DNS 查询
tshark -r file.pcap -Y "dns.qry.name and dns.flags.response == 0" -T fields \
  -e frame.number -e ip.src -e dns.qry.name

# 列出所有 DNS 响应
tshark -r file.pcap -Y "dns.flags.response == 1" -T fields \
  -e frame.number -e dns.qry.name -e dns.a

# 找可疑长子域（DNS 隧道特征）
tshark -r file.pcap -Y "dns.qry.name" -T fields -e dns.qry.name | \
  awk -F. '{if(length($1)>30) print}'

# 统计查询频率最高的域名
tshark -r file.pcap -Y "dns.qry.name and dns.flags.response == 0" -T fields -e dns.qry.name | \
  sort | uniq -c | sort -rn | head -20

# 找非标准 TLD（可能 C2 通信）
tshark -r file.pcap -Y "dns.qry.name" -T fields -e dns.qry.name | \
  awk -F. '{print $NF}' | sort | uniq -c | sort -rn

# 检测 DNS 隧道：统计每秒查询数
tshark -r file.pcap -Y "dns.qry.name and dns.flags.response == 0" -T fields -e frame.time_relative | \
  awk '{bucket=int($1); count[bucket]++} END {for(b in count) print b, count[b]}' | sort -n

# 提取 TXT 记录内容（可能藏数据）
tshark -r file.pcap -Y "dns.txt" -T fields -e dns.txt
```

### 3. TCP 流量分析

```bash
# 找特定端口的通信
tshark -r file.pcap -Y "tcp.port == 4444" -T fields \
  -e frame.number -e ip.src -e ip.dst -e tcp.payload

# 找反向 Shell 特征
tshark -r file.pcap -Y "tcp.port == 4444" -T fields -e data | tr -d '\n:' | xxd -r -p

# 找 SYN 扫描
tshark -r file.pcap -Y "tcp.flags.syn == 1 and tcp.flags.ack == 0" -T fields \
  -e ip.src -e ip.dst -e tcp.dstport

# 找 RST 包
tshark -r file.pcap -Y "tcp.flags.reset == 1" -T fields \
  -e ip.src -e ip.dst -e tcp.dstport

# 提取完整 TCP 流数据
tshark -r file.pcap -Y "tcp.stream eq 5" -T fields -e tcp.payload | \
  tr -d '\n:' | xxd -r -p > stream5.bin

# TCP 重传统计
tshark -r file.pcap -2 -Y "tcp.analysis.retransmission" -T fields \
  -e frame.number -e ip.src -e ip.dst
```

### 4. ICMP 流量分析

```bash
# 查看 ICMP 流量
tshark -r file.pcap -Y "icmp" -T fields \
  -e frame.number -e ip.src -e ip.dst -e icmp.type -e data

# 检测 ICMP 隧道（异常大的 ICMP 负载）
tshark -r file.pcap -Y "icmp and data" -T fields -e frame.len -e data | \
  awk '$1 > 100 {print}'

# 提取 ICMP 数据负载
tshark -r file.pcap -Y "icmp and data" -T fields -e data | \
  tr -d '\n:' | xxd -r -p > icmp_data.bin
```

### 5. USB 流量分析

CTF Misc 常见题型：从 USB 抓包还原键盘输入或鼠标轨迹。

```bash
# 提取 USB HID 数据
tshark -r usb.pcap -Y "usb.capdata" -T fields -e usb.capdata

# 去掉冒号输出纯 hex
tshark -r usb.pcap -Y "usb.capdata" -T fields -e usb.capdata | tr -d ':'

# 提取 USB 设备描述符
tshark -r usb.pcap -Y "usb.device_descriptor" -T fields -e usb.device_descriptor

# 提取特定长度数据（键盘通常是 8 字节，鼠标 4 字节）
tshark -r usb.pcap -Y "usb.capdata and usb.data_len == 8" -T fields -e usb.capdata
```

键盘数据还原脚本：

```python
#!/usr/bin/env python3
"""USB 键盘流量还原"""
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
    result = ""
    for line in hex_lines:
        line = line.strip().replace(':', '')
        if len(line) < 16:
            continue
        shift = int(line[0:2], 16) & 0x20
        for i in (4, 6):
            code = int(line[i*2:i*2+2], 16)
            if code == 0:
                continue
            if code in KEY_MAP:
                result += KEY_MAP[code][1 if shift else 0]
            break
    return result

# 用法：
# tshark -r usb.pcap -Y "usb.capdata" -T fields -e usb.capdata > data.txt
# with open('data.txt') as f: print(decode_keyboard(f))
```

### 6. SMB/FTP 文件传输分析

```bash
# 列出 SMB 操作
tshark -r file.pcap -Y "smb" -T fields \
  -e frame.number -e ip.src -e ip.dst -e smb.cmd -e smb.file

# 列出 FTP 命令
tshark -r file.pcap -Y "ftp" -T fields \
  -e frame.number -e ip.src -e ftp.request.command -e ftp.request.arg

# 导出 SMB 传输的文件
tshark -r file.pcap --export-objects smb,./smb_files/

# 导出 FTP 传输的文件
tshark -r file.pcap --export-objects ftp,./ftp_files/
```

### 7. TLS 握手分析

即使不解密，TLS 握手信息也能暴露很多（SNI、证书、密码套件）：

```bash
# 提取所有 SNI（Server Name Indication）
tshark -r file.pcap -Y "tls.handshake.extensions_server_name" -T fields \
  -e ip.dst -e tls.handshake.extensions_server_name

# 提取 TLS 版本和密码套件
tshark -r file.pcap -Y "tls.handshake.type == 1" -T fields \
  -e ip.src -e ip.dst -e tls.handshake.version -e tls.handshake.ciphersuite

# 提取服务器证书信息
tshark -r file.pcap -Y "tls.handshake.type == 11" -T fields \
  -e ip.src -e x509ce.dNSName

# 统计 TLS 连接的目标
tshark -r file.pcap -Y "tls.handshake.extensions_server_name" -T fields \
  -e tls.handshake.extensions_server_name | sort | uniq -c | sort -rn
```

---

## 十、文件还原与对象导出

### 1. HTTP 对象导出

```bash
# 导出所有 HTTP 传输的文件（图片、脚本、压缩包等）
tshark -r file.pcap --export-objects http,./http_objects/

# 导出后用 file 命令识别文件类型
file ./http_objects/*

# 也可先列出对象再选择性导出
# 注意：tshark 不支持交互式选择，需要全部导出后手动筛选
```

### 2. SMB 对象导出

```bash
tshark -r file.pcap --export-objects smb,./smb_objects/
```

### 3. FTP 对象导出

```bash
tshark -r file.pcap --export-objects ftp,./ftp_objects/
```

### 4. 手动重组 TCP 流数据

Export Objects 无法导出时，需要手动提取和拼接：

```bash
# 找到目标 TCP 流编号
tshark -r file.pcap -Y "tcp.stream" -T fields -e tcp.stream | sort -n | uniq

# 提取特定流的数据（仅服务端方向）
tshark -r file.pcap -Y "tcp.stream eq 5 and ip.src == 10.0.0.1" -T fields -e tcp.payload | \
  tr -d '\n:' | xxd -r -p > stream5_server.bin

# 提取特定流的数据（仅客户端方向）
tshark -r file.pcap -Y "tcp.stream eq 5 and ip.src == 10.0.0.5" -T fields -e tcp.payload | \
  tr -d '\n:' | xxd -r -p > stream5_client.bin

# 从 data 字段提取（某些场景 tcp.payload 为空但 data 有内容）
tshark -r file.pcap -Y "tcp.stream eq 5" -T fields -e data | \
  tr -d '\n:' | xxd -r -p > stream5_data.bin
```

### 5. 从 HTTP 响应中提取特定文件

```bash
# 提取 Content-Type 为 image/png 的响应体
tshark -r file.pcap -Y 'http.content_type contains "image/png"' -T fields -e http.file_data | \
  tr -d '\n' | base64 -d > image.png

# 提取 application/octet-stream 类型的响应体
tshark -r file.pcap -Y 'http.content_type contains "octet-stream"' -T fields \
  -e http.file_data > binary_data.bin
```

### 6. 重组分片数据

某些协议（如 TFTP、分片 ICMP）的数据分散在多个包中：

```bash
# ICMP 分片数据重组
tshark -r file.pcap -Y "icmp and data" -T fields -e data | \
  tr -d '\n:' | xxd -r -p > icmp_reassembled.bin

# DNS TXT 记录拼接
tshark -r file.pcap -Y "dns.txt" -T fields -e dns.txt | \
  tr -d '\n' | base64 -d > dns_decoded.bin
```

---

## 十一、TLS 解密

### 1. 使用 SSLKEYLOGFILE 解密

```bash
# 使用浏览器密钥日志解密 TLS 流量
tshark -r encrypted.pcap \
  -o "tls.keylog_file:./keylog.txt" \
  -Y "http.request" \
  -T fields -e http.host -e http.request.uri

# 解密后导出 HTTP 对象
tshark -r encrypted.pcap \
  -o "tls.keylog_file:./keylog.txt" \
  --export-objects http,./decrypted_http/

# 解密后提取 HTTP POST 数据
tshark -r encrypted.pcap \
  -o "tls.keylog_file:./keylog.txt" \
  -Y 'http.request.method == "POST"' \
  -T fields -e http.request.uri -e http.file_data
```

### 2. 使用 RSA 私钥解密

```bash
# 使用服务器 RSA 私钥解密（仅限 RSA 密钥交换）
tshark -r encrypted.pcap \
  -o "tls.keys_file:./server.key,,," \
  -Y "http.request" \
  -T fields -e http.host -e http.request.uri
```

### 3. WPA2 WiFi 解密

```bash
# 使用 WiFi 密码解密无线流量
tshark -r wifi.pcap \
  -o "wlan.enable_decryption:TRUE" \
  -o "uat:80211_keys:\"wpa-pwd\",\"MySSID:MyPassword\"" \
  -Y "http.request" \
  -T fields -e http.host
```

> 注意：RSA 私钥解密仅适用于使用 RSA 密钥交换的 TLS 连接。TLS 1.3 和使用 DHE/ECDHE 的连接无法用私钥解密，必须使用 SSLKEYLOGFILE。

---

## 十二、管道与流式处理

### 1. 从 stdin 读取

```bash
# tcpdump 抓包管道到 tshark
tcpdump -i eth0 -w - | tshark -i - -Y "http.request"

# SSH 远程抓包到本地分析
ssh user@remote "tcpdump -i eth0 -U -w - not port 22" | tshark -i - -Y "dns"
```

> -U 参数让 tcpdump 无缓冲输出，实现实时流式传输。

### 2. tshark 输出管道到其他工具

```bash
# HTTP Host 统计
tshark -r file.pcap -Y "http.request" -T fields -e http.host | sort | uniq -c | sort -rn

# DNS 查询域名去重
tshark -r file.pcap -Y "dns.qry.name" -T fields -e dns.qry.name | sort -u

# 提取 IP 列表
tshark -r file.pcap -T fields -e ip.dst | sort -u | wc -l

# 找访问最多的 URI
tshark -r file.pcap -Y "http.request" -T fields -e http.request.uri | sort | uniq -c | sort -rn | head -20

# 统计每个 IP 的连接数
tshark -r file.pcap -Y "tcp.flags.syn == 1 and tcp.flags.ack == 0" -T fields -e ip.src | \
  sort | uniq -c | sort -rn
```

### 3. 实时监控

```bash
# 实时监控 HTTP 请求
tshark -i eth0 -Y "http.request" -T fields \
  -e ip.src -e http.host -e http.request.uri

# 实时监控 DNS 查询
tshark -i eth0 -Y "dns.qry.name" -T fields -e ip.src -e dns.qry.name

# 实时监控新 TLS 连接
tshark -i eth0 -Y "tls.handshake.type == 1" -T fields \
  -e ip.src -e ip.dst -e tls.handshake.extensions_server_name

# 实时监控 ICMP
tshark -i eth0 -Y "icmp" -T fields -e ip.src -e ip.dst -e icmp.type

# 实时监控特定端口
tshark -i eth0 -Y "tcp.port == 4444" -T fields \
  -e ip.src -e ip.dst -e tcp.payload
```

### 4. 管道到 Python 脚本

```bash
# tshark 输出管道到 Python
tshark -r file.pcap -Y "http.request" -T fields \
  -e frame.number -e ip.src -e http.host -e http.request.uri \
  | python3 analyze.py
```

```python
#!/usr/bin/env python3
"""analyze.py - 从 stdin 读取 tshark 输出进行分析"""
import sys

for line in sys.stdin:
    parts = line.strip().split('\t')
    if len(parts) >= 4:
        frame, src, host, uri = parts
        # 自定义分析逻辑
        if 'login' in uri.lower() or 'admin' in uri.lower():
            print(f"[!] Suspicious: {src} -> {host}{uri}")
```

---

## 十三、脚本化自动化

### 1. Python 调用 tshark 批量分析

```python
#!/usr/bin/env python3
"""pcap_auto_analyze.py - 自动化流量分析脚本"""

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
    return tshark(pcap, ["-q", "-z", "io,phs"])


def top_conversations(pcap, n=10):
    """Top N 通信对"""
    output = tshark(pcap, [
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
            reqs.append({"host": parts[0], "method": parts[1], "uri": parts[2]})
    return reqs


def search_keyword(pcap, keyword):
    """在流量中搜索关键字"""
    output = tshark(pcap, [
        "-Y", f'tcp contains "{keyword}"',
        "-T", "fields",
        "-e", "frame.number", "-e", "ip.src", "-e", "ip.dst",
    ])
    return output


def main(pcap_path):
    pcap = Path(pcap_path)
    if not pcap.exists():
        print(f"文件不存在: {pcap}")
        sys.exit(1)

    print("=" * 60)
    print(f"自动分析: {pcap.name}")
    print("=" * 60)

    print("\n[1] 协议分布:")
    print(protocol_hierarchy(pcap))

    print("\n[2] Top 10 通信对:")
    for conv, size in top_conversations(pcap):
        print(f"  {conv}: {size} bytes")

    print("\n[3] DNS 查询 Top 20:")
    for domain, count in dns_queries(pcap):
        print(f"  {domain}: {count}")

    print("\n[4] HTTP 请求:")
    for req in http_requests(pcap)[:30]:
        print(f"  {req['method']} {req['host']}{req['uri']}")

    print("\n[5] 搜索 'flag':")
    print(search_keyword(pcap, "flag"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"用法: python3 {sys.argv[0]} <pcap_file>")
        sys.exit(1)
    main(sys.argv[1])
```

### 2. Bash 一行流自动化

```bash
# 快速扫描 pcap 中的可疑特征

# 找所有 POST 请求的 URI 和源 IP
tshark -r file.pcap -Y "http.request.method == POST" -T fields \
  -e ip.src -e http.request.uri

# 找所有非标准端口的 TCP 连接
tshark -r file.pcap -Y "tcp.flags.syn == 1 and tcp.flags.ack == 0 and \
  not (tcp.dstport == 80 or tcp.dstport == 443 or tcp.dstport == 53 \
  or tcp.dstport == 22)" -T fields -e ip.src -e ip.dst -e tcp.dstport

# 统计每个 IP 发起的连接数（端口扫描检测）
tshark -r file.pcap -Y "tcp.flags.syn == 1 and tcp.flags.ack == 0" -T fields \
  -e ip.src -e tcp.dstport | sort -u | awk '{print $1}' | sort | uniq -c | sort -rn

# 找 DNS 查询中域名最长的（隧道检测）
tshark -r file.pcap -Y "dns.qry.name" -T fields -e dns.qry.name | \
  awk '{print length, $0}' | sort -rn | head -20

# 提取所有 HTTP Cookie
tshark -r file.pcap -Y "http.cookie" -T fields -e ip.src -e http.cookie

# 检测数据外泄：找大量出站流量
tshark -r file.pcap -T fields -e ip.src -e ip.dst -e frame.len | \
  awk -F'\t' '{key=$1" -> "$2; sum[key]+=$3} END {for(k in sum) print sum[k], k}' | \
  sort -rn | head -20
```

### 3. JSON 输出 + Python 处理

```bash
# 导出 JSON 供 Python 深度分析
tshark -r file.pcap -T json > output.json
```

```python
#!/usr/bin/env python3
"""json_analyze.py - 分析 tshark JSON 输出"""
import json
from collections import Counter

with open('output.json') as f:
    packets = json.load(f)

hosts = []
for pkt in packets:
    layers = pkt.get('_source', {}).get('layers', {})
    http = layers.get('http', {})
    host = http.get('http.host', [None])[0] if http else None
    if host:
        hosts.append(host)

print("HTTP Host 分布:")
for host, count in Counter(hosts).most_common(20):
    print(f"  {host}: {count}")
```

### 4. 批量 pcap 文件处理

```bash
#!/bin/bash
# batch_analyze.sh - 批量分析目录下所有 pcap 文件

for pcap in /path/to/pcaps/*.pcap; do
    echo "========== $(basename $pcap) =========="

    echo "[协议分布]"
    tshark -r "$pcap" -q -z io,phs 2>/dev/null | head -20

    echo "[HTTP 请求]"
    tshark -r "$pcap" -Y "http.request" -T fields \
      -e ip.src -e http.request.method -e http.host -e http.request.uri 2>/dev/null | head -10

    echo "[DNS 查询]"
    tshark -r "$pcap" -Y "dns.qry.name and dns.flags.response == 0" -T fields \
      -e dns.qry.name 2>/dev/null | sort -u | head -10

    echo ""
done
```

---

## 十四、实战技巧与踩坑

### 1. CTF 找 flag 的标准套路

拿到一个流量包，按此顺序用 tshark 排查：

```bash
# 第一步：协议概览
tshark -r file.pcap -q -z io,phs

# 第二步：直接搜 flag
tshark -r file.pcap -Y 'http contains "flag"' -T fields -e http.file_data
tshark -r file.pcap -Y 'tcp contains "flag"' -T fields -e data
tshark -r file.pcap -Y 'data contains "flag{"' -T fields -e data

# 第三步：看 POST 请求（可能上传了什么）
tshark -r file.pcap -Y "http.request.method == POST" -T fields \
  -e ip.src -e http.request.uri -e http.file_data

# 第四步：导出 HTTP 对象（可能传了文件）
tshark -r file.pcap --export-objects http,./http_objects/

# 第五步：检查 DNS 隧道
tshark -r file.pcap -Y "dns.qry.name" -T fields -e dns.qry.name | \
  awk -F. '{if(length($1)>20) print}'

# 第六步：检查非标准端口
tshark -r file.pcap -Y "tcp.flags.syn == 1 and tcp.flags.ack == 0" -T fields \
  -e ip.dst -e tcp.dstport | sort -u | grep -v -E ':(80|443|53|22|21|25)$'

# 第七步：逐流排查
tshark -r file.pcap -Y "tcp.stream" -T fields -e tcp.stream | sort -n | uniq
# 对每个流编号提取数据
for i in $(seq 0 20); do
    tshark -r file.pcap -Y "tcp.stream eq $i" -T fields -e tcp.payload 2>/dev/null | \
      tr -d '\n:' | xxd -r -p > "stream_${i}.bin" 2>/dev/null
    if [ -s "stream_${i}.bin" ]; then
        echo "Stream $i: $(file stream_${i}.bin)"
    fi
done
```

### 2. 应急响应流量取证流程

```bash
# 1. 快速概览
tshark -r incident.pcap -q -z io,phs
tshark -r incident.pcap -q -z conv,tcp
tshark -r incident.pcap -q -z endpoints,ip

# 2. 定位可疑 IP
# 找通信量最大的外部 IP
tshark -r incident.pcap -T fields -e ip.dst | sort | uniq -c | sort -rn | head -20

# 3. 分析可疑 IP 的通信
tshark -r incident.pcap -Y "ip.addr == <suspicious_ip>" -T fields \
  -e frame.number -e ip.src -e ip.dst -e tcp.dstport

# 4. 提取可疑 IP 的数据
tshark -r incident.pcap -Y "ip.addr == <suspicious_ip>" -T fields -e data | \
  tr -d '\n:' | xxd -r -p > c2_traffic.bin

# 5. 检查 DNS 通信
tshark -r incident.pcap -Y "dns.qry.name" -T fields -e ip.src -e dns.qry.name | \
  grep <suspicious_ip>

# 6. TLS SNI 分析
tshark -r incident.pcap -Y "tls.handshake.extensions_server_name" -T fields \
  -e ip.dst -e tls.handshake.extensions_server_name
```

### 3. 常见踩坑

1. 权限不足

```bash
# 报错：Permission denied
# 原因：非 root 且未加入 wireshark 组
sudo usermod -aG wireshark $USER
# 重新登录后生效
```

2. 字段名错误

```bash
# 报错：tshark: Some fields aren't valid
# 原因：字段名拼写错误
# 解决：用 tshark -r file.pcap -c 1 -V 查看正确字段名
# 或在 Wireshark 中右键字段 → Copy → Field Name
```

3. 显示过滤器与 BPF 混用

```bash
# 错误：在 -f 中使用了显示过滤器语法
tshark -r file.pcap -f "http.request.method == POST"  # 报错！

# 正确：
tshark -r file.pcap -Y "http.request.method == POST"  # 显示过滤器
tshark -r file.pcap -f "tcp port 80"                  # BPF 语法
```

4. 大文件处理慢

```bash
# 大 pcap 直接分析很慢
# 方法一：先用 -f 预过滤
tshark -r huge.pcap -f "tcp port 80" -Y "http.request" -T fields -e http.host

# 方法二：先用 editcap 裁剪时间范围
editcap -A "2024-01-01 10:00:00" -B "2024-01-01 11:00:00" huge.pcap slice.pcap
tshark -r slice.pcap -Y "http.request" -T fields -e http.host

# 方法三：先用 dumpcap 分段
editcap -c 10000 huge.pcap part_  # 每 10000 包一个文件
```

5. hex 提取后拼接出错

```bash
# 错误：直接拼接 hex 字符串有换行符干扰
tshark -r file.pcap -T fields -e tcp.payload > data.txt
cat data.txt | xxd -r -p > out.bin  # 可能包含空行或冒号

# 正确：去掉换行和冒号
tshark -r file.pcap -T fields -e tcp.payload | tr -d '\n:' | xxd -r -p > out.bin

# 更安全：用 data 字段替代 tcp.payload（某些场景更可靠）
tshark -r file.pcap -T fields -e data | tr -d '\n:' | xxd -r -p > out.bin
```

6. Windows 下 tshark 路径问题

```powershell
# Windows 下 tshark 可能不在 PATH 中
# 手动加入或使用完整路径
& "C:\Program Files\Wireshark\tshark.exe" -r file.pcap -Y "http.request"
```

7. 中文内容搜索

```bash
# 搜索包含中文的 HTTP 内容
# 方法一：直接搜索 UTF-8 hex
tshark -r file.pcap -Y "http contains e4b8ade69687"  # "中文" 的 UTF-8 编码

# 方法二：先导出再搜索
tshark -r file.pcap -Y "http" -T fields -e http.file_data > http_data.txt
grep "中文" http_data.txt
```

### 4. 性能优化技巧

```bash
# 只读必要字段，减少解析开销
# 慢：解析所有字段
tshark -r file.pcap -Y "http.request"
# 快：只提取需要的字段
tshark -r file.pcap -Y "http.request" -T fields -e http.host -e http.request.uri

# 使用 -f 预过滤减少包量
tshark -r file.pcap -f "tcp port 80" -Y "http.request.method == POST"

# 禁用不需要的协议解析（大幅提速）
tshark -r file.pcap -o "http.desegment_body:FALSE" -Y "http.request"

# 用 -c 限制包数（快速预览）
tshark -r file.pcap -c 1000 -q -z io,phs
```

---

## 十五、速查表

### 输入源

```bash
tshark -r file.pcap              # 读 pcap 文件
tshark -i eth0                   # 抓网卡
tshark -i eth0 -c 100            # 抓 100 个包
tshark -i eth0 -w out.pcap       # 抓包存文件
```

### 过滤

```bash
tshark -r f.pcap -Y "http.request"           # 显示过滤
tshark -r f.pcap -f "tcp port 80"            # BPF 捕获过滤
tshark -r f.pcap -2 -R "tcp.analysis.retransmission"  # 两次遍历
```

### 字段提取

```bash
tshark -r f.pcap -T fields -e ip.src -e ip.dst
tshark -r f.pcap -Y "http.request" -T fields -e http.host -e http.request.uri
tshark -r f.pcap -Y "tcp.port==4444" -T fields -e data | tr -d '\n:' | xxd -r -p > out.bin
```

### CSV 输出

```bash
tshark -r f.pcap -Y "http.request" -T fields \
  -E header=y -E separator=, -E quote=d \
  -e frame.number -e ip.src -e http.host -e http.request.uri
```

### 统计

```bash
tshark -r f.pcap -q -z io,phs               # 协议层级
tshark -r f.pcap -q -z conv,tcp             # TCP 会话
tshark -r f.pcap -q -z conv,ip              # IP 会话
tshark -r f.pcap -q -z endpoints,ip         # IP 端点
tshark -r f.pcap -q -z http,tree            # HTTP 统计
tshark -r f.pcap -q -z dns,tree             # DNS 统计
tshark -r f.pcap -q -z expert               # 专家信息
tshark -r f.pcap -q -z "io,stat,1"          # 每秒吞吐量
```

### 对象导出

```bash
tshark -r f.pcap --export-objects http,./out/    # HTTP 对象
tshark -r f.pcap --export-objects smb,./out/     # SMB 对象
tshark -r f.pcap --export-objects ftp,./out/     # FTP 对象
```

### TLS 解密

```bash
tshark -r f.pcap -o "tls.keylog_file:./keylog.txt" -Y "http.request"
tshark -r f.pcap -o "tls.keylog_file:./keylog.txt" --export-objects http,./out/
```

### 环缓冲抓包

```bash
tshark -i eth0 -w cap.pcap -b filesize:102400 -b files:10
```

### 管道

```bash
tcpdump -i eth0 -w - | tshark -i - -Y "dns"
ssh remote "tcpdump -i eth0 -U -w -" | tshark -i -
tshark -r f.pcap -T fields -e http.host | sort | uniq -c | sort -rn
```

### 实时监控

```bash
tshark -i eth0 -Y "http.request" -T fields -e ip.src -e http.host -e http.request.uri
tshark -i eth0 -Y "dns.qry.name" -T fields -e ip.src -e dns.qry.name
```

### 常用显示过滤器

```
http.request                                    # HTTP 请求
http.request.method == "POST"                   # POST
ip.addr == 10.0.0.1                             # 指定 IP
tcp.port == 4444                                # 指定端口
tcp contains "flag"                             # 内容搜索
dns.qry.name                                    # DNS 查询
tls.handshake.extensions_server_name            # TLS SNI
tcp.flags.syn == 1 and tcp.flags.ack == 0       # SYN 扫描
tcp.len > 1000                                  # 大包
```

### 辅助工具

```bash
mergecap -w merged.pcap part_*.pcap     # 合并 pcap
editcap -A "10:00:00" -B "11:00:00" in.pcap out.pcap  # 按时间裁剪
editcap -c 10000 in.pcap part_          # 按包数拆分
capinfos file.pcap                      # 查看 pcap 信息
dumpcap -i eth0 -w out.pcap             # 轻量抓包（仅写文件不解析）
reordercap in.pcap out.pcap             # 按时间排序
text2pcap input.txt output.pcap         # 文本转 pcap
```

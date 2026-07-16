# pyshark 实战使用指南

> Python 化的 Wireshark 解析引擎——用 Python 对象操作网络数据包，从 pcap 读取到实时抓包，从字段提取到协议分析，从 TLS 解密到自动化取证，每个场景都有可运行的脚本。需要 tshark 的能力但想用 Python 写逻辑，选 pyshark。

---

## 目录

- [一、pyshark 是什么](#一pyshark-是什么)
- [二、安装与环境配置](#二安装与环境配置)
- [三、核心概念：捕获对象与数据包模型](#三核心概念捕获对象与数据包模型)
- [四、FileCapture：读取 pcap 文件](#四filecapture读取-pcap-文件)
- [五、LiveCapture：实时抓包](#五livecapture实时抓包)
- [六、其他捕获模式](#六其他捕获模式)
- [七、数据包访问与字段提取](#七数据包访问与字段提取)
- [八、过滤器](#八过滤器)
- [九、协议分析实战](#九协议分析实战)
- [十、TLS 解密](#十tls-解密)
- [十一、高级技巧](#十一高级技巧)
- [十二、自动化分析脚本](#十二自动化分析脚本)
- [十三、实战技巧与踩坑](#十三实战技巧与踩坑)
- [十四、速查表](#十四速查表)

---

## 一、pyshark 是什么

pyshark 是 tshark 的 Python 封装库。它不在 Python 中重新实现协议解析，而是启动 tshark 子进程，利用 tshark 的 XML/JSON 输出将数据包转换为 Python 对象。这意味着 Wireshark 能解析的几百种协议，pyshark 全部支持——零额外成本。

### pyshark vs tshark vs Scapy vs dpkt

| 维度 | pyshark | tshark (命令行) | Scapy | dpkt |
|------|---------|----------------|-------|------|
| 协议解析深度 | 全协议栈（Wireshark 引擎） | 全协议栈 | 较广但不完整 | 仅基础 TCP/IP |
| 使用方式 | Python API | 命令行 | Python API | Python API |
| 构造/发送数据包 | 不支持 | 不支持 | 支持 | 基础支持 |
| 抓包能力 | 支持（调用 tshark） | 原生支持 | 支持 | 不支持 |
| 字段访问 | 对象属性（pkt.ip.src） | 命令行参数（-e ip.src） | 对象属性 | 手动偏移 |
| 性能 | 较慢（子进程+解析开销） | 快 | 中等 | 快 |
| 适用场景 | 需 Python 逻辑 + 全协议解析 | 批量提取/统计/管道 | 构造包/主动测试 | 轻量快速解析 |

> 核心判断：需要 Wireshark 级别的全协议深度解析 + Python 灵活逻辑用 pyshark，需要构造/发送包用 Scapy，需要极致性能用 dpkt/tshark 命令行。

### 与 tshark 实战指南的关系

[tshark实战使用指南](tshark实战使用指南.md) 覆盖了 tshark 命令行的全部用法。本文档专注于 Python API 层面，解决"用 tshark 提取数据后还需要写 Python 处理逻辑"的场景。pyshark 将提取和处理合为一步，直接在 Python 中完成条件判断、统计聚合、数据重组等复杂操作。

---

## 二、安装与环境配置

### 1. 前置依赖：tshark

pyshark 必须依赖 tshark，先确认 tshark 可用：

```bash
# 确认 tshark 已安装
tshark --version

# 若未安装，参见 tshark实战使用指南 第二章
```

### 2. 安装 pyshark

```bash
# pip 安装
pip install pyshark

# 或指定源
pip install pyshark -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 指定 tshark 路径

若 tshark 不在系统 PATH 中，需手动指定：

```python
import pyshark

# 方式一：初始化时指定
cap = pyshark.FileCapture(
    input_file='test.pcap',
    tshark_path='C:/Program Files/Wireshark/tshark.exe'
)

# 方式二：全局设置（修改 pyshark 配置）
# pyshark 不提供全局配置接口，每个 Capture 对象都需要传 tshark_path
# 建议封装一个工厂函数：
def make_capture(capture_type='file', tshark_path=None, **kwargs):
    tshark_path = tshark_path or 'C:/Program Files/Wireshark/tshark.exe'
    if capture_type == 'file':
        return pyshark.FileCapture(tshark_path=tshark_path, **kwargs)
    elif capture_type == 'live':
        return pyshark.LiveCapture(tshark_path=tshark_path, **kwargs)
```

### 4. 验证安装

```python
import pyshark

# 读取一个 pcap 测试
cap = pyshark.FileCapture(input_file='test.pcap')
for pkt in cap:
    print(pkt)
    break  # 只看第一个包
cap.close()
```

### 5. 权限说明

- 读取 pcap 文件：无需特殊权限
- 实时抓包（LiveCapture）：需要 root/管理员权限或加入 wireshark 组（同 tshark）

---

## 三、核心概念：捕获对象与数据包模型

### 1. 捕获对象体系

pyshark 提供多种捕获对象，对应不同的数据来源：

| 捕获对象 | 数据来源 | 典型场景 |
|----------|----------|----------|
| FileCapture | pcap/pcapng 文件 | 离线分析、CTF 流量题 |
| LiveCapture | 本地网卡 | 实时监控、流量取证 |
| LiveRingCapture | 本地网卡（环缓冲） | 长时间持续监控 |
| RemoteCapture | 远程 rpcapd 服务 | 远程服务器抓包 |
| InMemCapture | 内存 | 快速测试、管道输入 |
| PipeCapture | 命名管道 | 与其他工具联动 |

### 2. 数据包模型

每个数据包由多个 Layer 组成，Layer 按协议栈从低到高排列：

```
Packet
  ├── Layer ETH    (以太网)
  ├── Layer IP     (网络层)
  ├── Layer TCP    (传输层)
  └── Layer HTTP   (应用层)
```

访问方式：

```python
# 按协议名访问
pkt.ip.src          # '10.0.0.5'
pkt.tcp.dstport     # '80'
pkt.http.host       # 'example.com'

# 按索引访问
pkt[0]              # ETH Layer
pkt[1]              # IP Layer
pkt[2]              # TCP Layer

# 按字符串访问
pkt['ip'].src       # 同 pkt.ip.src

# 检查是否存在某层
if hasattr(pkt, 'http'):
    print(pkt.http.request_method)
```

### 3. 字段访问特点

pyshark 的字段值全部返回字符串：

```python
pkt.ip.ttl          # 返回 '64'，不是整数 64
pkt.tcp.dstport     # 返回 '80'，不是整数 80

# 需要数值时手动转换
ttl = int(pkt.ip.ttl)
port = int(pkt.tcp.dstport)
```

> 这是 pyshark 设计决定的：tshark 的 XML/JSON 输出所有字段都是字符串格式，pyshark 不做类型推断，原样传递。

---

## 四、FileCapture：读取 pcap 文件

### 1. 基础读取

```python
import pyshark

# 读取 pcap 文件
cap = pyshark.FileCapture(input_file='capture.pcap')

# 遍历所有包
for pkt in cap:
    print(pkt)

# 按索引访问
first_pkt = cap[0]
print(first_pkt)

# 获取包数量
print(f"总包数: {len(cap)}")

# 用完必须关闭，释放 tshark 子进程
cap.close()
```

### 2. 带过滤器读取

```python
# 显示过滤器
cap = pyshark.FileCapture(
    input_file='capture.pcap',
    display_filter='http.request.method == "POST"'
)

# BPF 过滤器（FileCapture 下不建议使用，存在已知 bug）
# 推荐用 display_filter 替代
cap = pyshark.FileCapture(
    input_file='capture.pcap',
    display_filter='tcp.port == 80'
)

for pkt in cap:
    print(pkt.ip.src, pkt.http.request_uri)
cap.close()
```

### 3. 内存优化：大文件处理

读取大 pcap 时，默认 keep_packets=True 会把所有包保存在内存中。设为 False 则只保留当前遍历的包：

```python
# 大文件：不保留已读包，节省内存
cap = pyshark.FileCapture(
    input_file='huge.pcap',
    keep_packets=False,
    display_filter='http.request'
)

for pkt in cap:
    # 逐包处理，处理完即释放
    process(pkt)

cap.close()
```

> keep_packets=False 时不能用 cap[0]、len(cap) 等随机访问，只能遍历一次。

### 4. 仅读取摘要

只需要快速浏览包信息时，only_summaries=True 大幅提速：

```python
cap = pyshark.FileCapture(
    input_file='capture.pcap',
    only_summaries=True
)

for pkt in cap:
    # 摘要信息：仅包含基本信息，无协议字段
    print(pkt)
cap.close()
```

### 5. 使用 EK JSON 模式

use_ek=True 使用 tshark 的 EK JSON 输出格式，比默认 XML 更快：

```python
cap = pyshark.FileCapture(
    input_file='capture.pcap',
    use_ek=True,
    display_filter='http.request'
)

for pkt in cap:
    if hasattr(pkt, 'http'):
        print(pkt.http.host)
cap.close()
```

> EK 模式比 XML 模式快，但某些字段的访问方式略有不同，建议先测试兼容性。

### 6. 完整参数一览

```python
cap = pyshark.FileCapture(
    input_file=None,           # pcap 文件路径
    keep_packets=True,         # 是否保留已读包（False 省内存但无法随机访问）
    display_filter=None,       # Wireshark 显示过滤器
    only_summaries=False,      # 仅读取摘要（更快但信息少）
    decryption_key=None,       # TLS/WiFi 解密密钥
    encryption_type='wpa-pwk', # 加密类型：'wep', 'wpa-pwd', 'wpa-pwk'
    decode_as=None,            # 强制协议解码：{'tcp.port==8888': 'http'}
    disable_protocol=None,     # 禁用某协议解析器
    tshark_path=None,          # tshark 路径
    override_prefs=None,       # 覆盖 tshark 首选项：{'tls.keylog_file': './keylog.txt'}
    use_json=False,            # 已废弃，用 use_ek
    use_ek=False,              # 使用 EK JSON 模式（更快）
    output_file=None,          # 输出到 pcap 文件
    include_raw=False,         # 包含原始包数据
    eventloop=None,            # 异步事件循环
    custom_parameters=None,    # 传给 tshark 的自定义参数
    debug=False                # 调试模式
)
```

---

## 五、LiveCapture：实时抓包

### 1. 基础实时抓包

```python
import pyshark

# 指定网卡抓包
cap = pyshark.LiveCapture(interface='eth0')

# 方式一：sniff() 抓指定数量/时间后停止
cap.sniff(packet_count=10, timeout=30)
for pkt in cap:
    print(pkt)
cap.close()

# 方式二：sniff_continuously() 生成器模式（推荐）
cap = pyshark.LiveCapture(interface='eth0')
for pkt in cap.sniff_continuously(packet_count=50):
    print(f"捕获: {pkt.highest_layer} {pkt.sniff_time}")
cap.close()
```

### 2. 回调模式

```python
import pyshark

def process_packet(pkt):
    """每捕获一个包就调用"""
    if hasattr(pkt, 'http'):
        print(f"HTTP: {pkt.ip.src} -> {pkt.http.host}{pkt.http.request_uri}")

cap = pyshark.LiveCapture(interface='eth0', display_filter='http.request')
cap.apply_on_packets(process_packet, timeout=60)
cap.close()
```

### 3. 带过滤器抓包

```python
# BPF 过滤器（捕获阶段过滤，更高效）
cap = pyshark.LiveCapture(
    interface='eth0',
    bpf_filter='tcp port 80'
)

# 显示过滤器（解析阶段过滤，更灵活）
cap = pyshark.LiveCapture(
    interface='eth0',
    display_filter='http.request.method == "POST"'
)

# 两者可组合使用
cap = pyshark.LiveCapture(
    interface='eth0',
    bpf_filter='tcp port 80 or tcp port 443',
    display_filter='http.request'
)
```

### 4. 抓包存文件

```python
cap = pyshark.LiveCapture(
    interface='eth0',
    output_file='capture.pcap'
)
cap.sniff(packet_count=1000)
cap.close()
# capture.pcap 可用 Wireshark 或 tshark 进一步分析
```

### 5. 异步抓包

```python
import asyncio
import pyshark

async def process_packet(pkt):
    if hasattr(pkt, 'ip'):
        print(f"{pkt.ip.src} -> {pkt.ip.dst}")

async def main():
    cap = pyshark.LiveCapture(interface='eth0', display_filter='ip')
    await cap.packets_from_tshark(process_packet, packet_count=50)
    cap.close()

asyncio.run(main())
```

### 6. LiveCapture 完整参数

```python
cap = pyshark.LiveCapture(
    interface=None,            # 网卡名（如 'eth0'）；None 则抓所有网卡
    bpf_filter=None,           # BPF 捕获过滤器
    display_filter=None,       # Wireshark 显示过滤器
    output_file=None,          # 输出到 pcap 文件
    decode_as=None,            # 强制协议解码
    disable_protocol=None,     # 禁用协议解析器
    tshark_path=None,          # tshark 路径
    override_prefs=None,       # 覆盖 tshark 首选项
    use_json=False,            # 已废弃
    use_ek=False,              # EK JSON 模式
    only_summaries=False,      # 仅摘要
    decryption_key=None,       # 解密密钥
    encryption_type='wpa-pwk', # 加密类型
    include_raw=False,         # 包含原始数据
    custom_parameters=None,    # 自定义 tshark 参数
    debug=False,               # 调试模式
    monitor_mode=False,        # 无线监控模式
    ring_file_size=None,       # 环缓冲文件大小（KB）
    ring_file_name=None,       # 环缓冲文件名
    num_ring_files=None,       # 环缓冲文件数
    ring_file_timeout=None,    # 环缓冲超时秒数
)
```

---

## 六、其他捕获模式

### 1. LiveRingCapture：环缓冲抓包

长时间监控时防止 pcap 文件无限增长：

```python
import pyshark

cap = pyshark.LiveRingCapture(
    interface='eth0',
    ring_file_size=102400,    # 每个文件 100 MB
    num_ring_files=5,         # 保留 5 个文件轮转
    ring_file_name='monitor'  # 文件名前缀
)
cap.sniff(timeout=3600)  # 抓 1 小时
cap.close()
```

### 2. RemoteCapture：远程抓包

从运行了 rpcapd 的远程机器抓包：

```python
import pyshark

# 远程服务器需先启动 rpcapd
# rpcapd -n -p 2002

cap = pyshark.RemoteCapture(
    remote_host='192.168.1.100',
    remote_interface='eth0',
    remote_port=2002,
    display_filter='http.request'
)

for pkt in cap.sniff_continuously(packet_count=20):
    if hasattr(pkt, 'http'):
        print(pkt.http.host)
cap.close()
```

### 3. InMemCapture：内存捕获

直接在内存中处理包数据，适合管道输入或测试：

```python
import pyshark

cap = pyshark.InMemCapture()
# 从管道或其他来源获取包数据后解析
# 具体用法取决于数据来源
```

### 4. PipeCapture：管道捕获

从命名管道读取数据：

```python
import pyshark

cap = pyshark.PipeCapture(pipe='/tmp/mypipe')
for pkt in cap.sniff_continuously():
    print(pkt)
cap.close()
```

---

## 七、数据包访问与字段提取

### 1. 包的基本信息

```python
pkt.number          # 帧号（字符串）
pkt.sniff_time      # 捕获时间（datetime 对象）
pkt.sniff_timestamp # 捕获时间戳（字符串）
pkt.length          # 包长度（字符串）
pkt.highest_layer   # 最高层协议名（如 'HTTP'）
pkt.layers          # 所有层对象列表 [<ETH Layer>, <IP Layer>, ...]
```

### 2. 层级访问

```python
# 方式一：属性访问（最常用）
pkt.eth.src         # 源 MAC
pkt.ip.src          # 源 IP
pkt.tcp.dstport     # 目的端口

# 方式二：字典访问
pkt['ip'].src       # 同上

# 方式三：索引访问
pkt[1].src          # 第 2 层（通常是 IP）

# 方式四：hasattr 安全检查
if hasattr(pkt, 'tcp'):
    print(pkt.tcp.srcport)
```

### 3. 层的字段查看

```python
# 查看某层所有字段名
layer = pkt.ip
print(dir(layer))           # 所有属性和方法
print(layer.field_names)    # 仅字段名列表

# 打印层的详细信息
pkt.ip.pretty_print()       # 格式化打印
pkt.pretty_print()          # 打印整个包
```

### 4. 常用协议字段速查

```python
# ETH
pkt.eth.src         # 源 MAC
pkt.eth.dst         # 目的 MAC

# IP
pkt.ip.src          # 源 IP
pkt.ip.dst          # 目的 IP
pkt.ip.ttl          # TTL
pkt.ip.proto        # 协议号
pkt.ip.len          # 总长度
pkt.ip.flags        # 标志

# TCP
pkt.tcp.srcport     # 源端口
pkt.tcp.dstport     # 目的端口
pkt.tcp.flags       # 标志（十六进制字符串）
pkt.tcp.seq         # 序列号
pkt.tcp.ack         # 确认号
pkt.tcp.window_size # 窗口大小
pkt.tcp.payload     # 负载（hex）

# UDP
pkt.udp.srcport     # 源端口
pkt.udp.dstport     # 目的端口
pkt.udp.length      # 长度

# HTTP
pkt.http.request_method     # 请求方法（GET/POST/...）
pkt.http.request_uri        # 请求 URI
pkt.http.host               # Host 头
pkt.http.user_agent         # User-Agent
pkt.http.cookie             # Cookie
pkt.http.authorization      # 认证头
pkt.http.response_code      # 响应码（200/404/...）
pkt.http.content_type       # Content-Type
pkt.http.file_data          # 文件数据

# DNS
pkt.dns.qry.name    # 查询域名
pkt.dns.qry.type    # 查询类型
pkt.dns.a           # A 记录
pkt.dns.flags       # 标志

# TLS
pkt.tls.record.content_type       # 记录类型
pkt.tls.handshake.type            # 握手类型（1=Client Hello）
pkt.tls.handshake.extensions_server_name  # SNI
```

### 5. 提取原始数据

```python
# include_raw=True 开启原始数据
cap = pyshark.FileCapture(
    input_file='capture.pcap',
    include_raw=True
)

for pkt in cap:
    # 获取原始 hex 数据
    if hasattr(pkt, 'tcp') and hasattr(pkt.tcp, 'payload'):
        payload_hex = pkt.tcp.payload
        # 转为二进制
        payload_bytes = bytes.fromhex(payload_hex.replace(':', ''))
```

---

## 八、过滤器

### 1. 两类过滤器

| 类型 | 参数 | 适用对象 | 语法 | 性能 |
|------|------|----------|------|------|
| BPF 过滤器 | bpf_filter | LiveCapture | BPF 语法 | 快（捕获阶段过滤） |
| 显示过滤器 | display_filter | 所有 Capture | Wireshark 语法 | 较慢（解析后过滤） |

> FileCapture 的 bpf_filter 存在已知 bug，建议只用 display_filter。

### 2. BPF 过滤器示例

```python
# 仅抓 TCP 80 端口
cap = pyshark.LiveCapture(interface='eth0', bpf_filter='tcp port 80')

# 仅抓某个 IP
cap = pyshark.LiveCapture(interface='eth0', bpf_filter='host 192.168.1.100')

# 排除 SSH
cap = pyshark.LiveCapture(interface='eth0', bpf_filter='not port 22')

# 组合
cap = pyshark.LiveCapture(
    interface='eth0',
    bpf_filter='tcp port 80 or tcp port 443'
)
```

### 3. 显示过滤器示例

```python
# HTTP POST 请求
cap = pyshark.FileCapture(
    input_file='file.pcap',
    display_filter='http.request.method == "POST"'
)

# 指定 IP
cap = pyshark.FileCapture(
    input_file='file.pcap',
    display_filter='ip.addr == 10.0.0.1'
)

# 组合条件
cap = pyshark.FileCapture(
    input_file='file.pcap',
    display_filter='http.request and ip.src == 10.0.0.5'
)

# TCP 特定端口
cap = pyshark.FileCapture(
    input_file='file.pcap',
    display_filter='tcp.port == 4444'
)

# DNS 隧道检测
cap = pyshark.FileCapture(
    input_file='file.pcap',
    display_filter='dns.qry.name and dns.flags.response == 0'
)

# TLS Client Hello
cap = pyshark.FileCapture(
    input_file='file.pcap',
    display_filter='tls.handshake.type == 1'
)

# 内容搜索
cap = pyshark.FileCapture(
    input_file='file.pcap',
    display_filter='tcp contains "flag"'
)
```

### 4. 显示过滤器语法速查

与 tshark/Wireshark 完全一致，详见 [tshark实战使用指南](tshark实战使用指南.md) 第五章的过滤器速查。

---

## 九、协议分析实战

### 1. HTTP 流量分析

```python
import pyshark

def analyze_http(pcap_path):
    """提取所有 HTTP 请求信息"""
    cap = pyshark.FileCapture(
        input_file=pcap_path,
        display_filter='http.request',
        keep_packets=False
    )

    for pkt in cap:
        method = pkt.http.request_method
        host = pkt.http.host if hasattr(pkt.http, 'host') else '-'
        uri = pkt.http.request_uri
        src = pkt.ip.src
        print(f"[{src}] {method} {host}{uri}")

    cap.close()


def find_post_data(pcap_path):
    """提取 HTTP POST 请求的表单数据"""
    cap = pyshark.FileCapture(
        input_file=pcap_path,
        display_filter='http.request.method == "POST"',
        keep_packets=False
    )

    for pkt in cap:
        src = pkt.ip.src
        uri = pkt.http.request_uri
        data = pkt.http.file_data if hasattr(pkt.http, 'file_data') else '(无数据)'
        print(f"[{src}] POST {uri}")
        print(f"  数据: {data}")

    cap.close()


def extract_credentials(pcap_path):
    """搜索 HTTP 中的凭据"""
    cap = pyshark.FileCapture(
        input_file=pcap_path,
        display_filter='http.authorization or (http.request.method == "POST" and http contains "password")',
        keep_packets=False
    )

    for pkt in cap:
        if hasattr(pkt.http, 'authorization'):
            print(f"Basic Auth: {pkt.ip.src} -> {pkt.http.authorization}")
        if hasattr(pkt.http, 'file_data') and 'password' in pkt.http.file_data.lower():
            print(f"POST 凭据: {pkt.ip.src} -> {pkt.http.file_data}")

    cap.close()
```

### 2. DNS 流量分析

```python
import pyshark
from collections import Counter

def analyze_dns(pcap_path):
    """DNS 查询统计与隧道检测"""
    cap = pyshark.FileCapture(
        input_file=pcap_path,
        display_filter='dns.qry.name',
        keep_packets=False
    )

    domains = Counter()
    long_subdomains = []

    for pkt in cap:
        if hasattr(pkt.dns, 'qry_name'):
            name = pkt.dns.qry_name
            domains[name] += 1

            # 检测 DNS 隧道：子域超长
            parts = name.split('.')
            if len(parts) > 2 and len(parts[0]) > 30:
                long_subdomains.append(name)

    cap.close()

    print("Top 20 查询域名:")
    for domain, count in domains.most_common(20):
        print(f"  {count:4d}  {domain}")

    if long_subdomains:
        print(f"\n[!] 可疑长子域（可能 DNS 隧道）:")
        for name in long_subdomains[:10]:
            print(f"  {name}")


def extract_dns_responses(pcap_path):
    """提取 DNS A 记录响应"""
    cap = pyshark.FileCapture(
        input_file=pcap_path,
        display_filter='dns.flags.response == 1 and dns.a',
        keep_packets=False
    )

    for pkt in cap:
        name = pkt.dns.qry_name if hasattr(pkt.dns, 'qry_name') else '?'
        addr = pkt.dns.a
        print(f"{name} -> {addr}")

    cap.close()
```

### 3. TCP 流量分析

```python
import pyshark

def extract_tcp_stream(pcap_path, stream_index):
    """提取指定 TCP 流的数据"""
    cap = pyshark.FileCapture(
        input_file=pcap_path,
        display_filter=f'tcp.stream eq {stream_index}',
        keep_packets=False,
        include_raw=True
    )

    client_data = []
    server_data = []

    # 假设第一个包的源 IP 为客户端
    client_ip = None

    for pkt in cap:
        if not hasattr(pkt, 'tcp'):
            continue
        if not hasattr(pkt.tcp, 'payload'):
            continue

        if client_ip is None:
            client_ip = pkt.ip.src

        payload_hex = pkt.tcp.payload.replace(':', '')
        payload_bytes = bytes.fromhex(payload_hex)

        if pkt.ip.src == client_ip:
            client_data.append(payload_bytes)
        else:
            server_data.append(payload_bytes)

    cap.close()

    client_bin = b''.join(client_data)
    server_bin = b''.join(server_data)

    return client_bin, server_bin


def list_tcp_streams(pcap_path):
    """列出所有 TCP 流编号"""
    cap = pyshark.FileCapture(
        input_file=pcap_path,
        display_filter='tcp.stream',
        keep_packets=False
    )

    streams = set()
    for pkt in cap:
        streams.add(pkt.tcp.stream)

    cap.close()
    return sorted(streams, key=lambda x: int(x))
```

### 4. ICMP 隧道检测

```python
import pyshark

def detect_icmp_tunnel(pcap_path):
    """检测 ICMP 隧道：异常大的负载"""
    cap = pyshark.FileCapture(
        input_file=pcap_path,
        display_filter='icmp and data',
        keep_packets=False
    )

    for pkt in cap:
        data_field = pkt.data if hasattr(pkt, 'data') else None
        frame_len = int(pkt.length)
        if frame_len > 100:  # 正常 ping 通常 < 100 字节
            print(f"[!] 异常 ICMP: 长度={frame_len} 源={pkt.ip.src} 目的={pkt.ip.dst}")

    cap.close()
```

### 5. USB 键盘取证

```python
import pyshark

# USB HID 键盘扫描码映射
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


def decode_usb_keyboard(pcap_path):
    """从 USB 抓包还原键盘输入"""
    cap = pyshark.FileCapture(
        input_file=pcap_path,
        display_filter='usb.capdata',
        keep_packets=False
    )

    result = ""
    for pkt in cap:
        if not hasattr(pkt, 'usb'):
            continue
        capdata = pkt.usb.capdata
        if not capdata:
            continue

        hex_str = capdata.replace(':', '')
        if len(hex_str) < 16:
            continue

        # 第 0 字节 bit5 是 Left Shift
        shift = int(hex_str[0:2], 16) & 0x20
        # 第 3 字节（偏移 2）是按键扫描码
        for i in (4, 6):
            code = int(hex_str[i*2:i*2+2], 16)
            if code == 0:
                continue
            if code in KEY_MAP:
                result += KEY_MAP[code][1 if shift else 0]
            break

    cap.close()
    return result
```

### 6. TLS SNI 提取

```python
import pyshark
from collections import Counter

def extract_sni(pcap_path):
    """提取所有 TLS SNI"""
    cap = pyshark.FileCapture(
        input_file=pcap_path,
        display_filter='tls.handshake.extensions_server_name',
        keep_packets=False
    )

    sni_count = Counter()
    for pkt in cap:
        if hasattr(pkt.tls, 'handshake_extensions_server_name'):
            sni = pkt.tls.handshake_extensions_server_name
            dst = pkt.ip.dst
            sni_count[sni] += 1
            print(f"  {dst} -> {sni}")

    cap.close()

    print("\nSNI 统计:")
    for sni, count in sni_count.most_common(20):
        print(f"  {count:3d}  {sni}")
```

---

## 十、TLS 解密

### 1. 使用 SSLKEYLOGFILE 解密

```python
import pyshark

# 方法一：通过 override_prefs 传递 keylog 文件
cap = pyshark.FileCapture(
    input_file='encrypted.pcap',
    override_prefs={'tls.keylog_file': './keylog.txt'},
    display_filter='http.request'
)

for pkt in cap:
    if hasattr(pkt, 'http'):
        host = pkt.http.host if hasattr(pkt.http, 'host') else '-'
        uri = pkt.http.request_uri
        print(f"{host}{uri}")

cap.close()
```

### 2. 使用 RSA 私钥解密

```python
import pyshark

cap = pyshark.FileCapture(
    input_file='encrypted.pcap',
    override_prefs={'tls.keys_file': './server.key,,,'},
    display_filter='http.request'
)

for pkt in cap:
    if hasattr(pkt, 'http'):
        print(pkt.http.host, pkt.http.request_uri)

cap.close()
```

### 3. WPA2 WiFi 解密

```python
import pyshark

cap = pyshark.FileCapture(
    input_file='wifi.pcap',
    decryption_key='MySSID:MyPassword',
    encryption_type='wpa-pwd',
    display_filter='http.request'
)

for pkt in cap:
    if hasattr(pkt, 'http'):
        print(pkt.http.host)

cap.close()
```

---

## 十一、高级技巧

### 1. decode_as：强制协议解码

让 tshark 将特定端口的流量按指定协议解析：

```python
# 将 8080 端口流量当 HTTP 解析
cap = pyshark.FileCapture(
    input_file='capture.pcap',
    decode_as={'tcp.port==8080': 'http'}
)

for pkt in cap:
    if hasattr(pkt, 'http'):
        print(pkt.http.request_uri)

cap.close()
```

### 2. disable_protocol：禁用协议解析

大文件分析时，禁用不需要的协议可以加速：

```python
# 禁用 DNS 解析（加速 HTTP 分析）
cap = pyshark.FileCapture(
    input_file='capture.pcap',
    disable_protocol='dns',
    display_filter='http.request'
)
```

### 3. custom_parameters：传递任意 tshark 参数

```python
# 传递自定义 tshark 参数
cap = pyshark.FileCapture(
    input_file='capture.pcap',
    custom_parameters=[
        '-o', 'tcp.desegment_tcp_streams:TRUE',
        '-o', 'http.desegment_body:TRUE',
    ]
)

# 也可以用字典形式
cap = pyshark.FileCapture(
    input_file='capture.pcap',
    custom_parameters={
        '-c': '1000',  # 只读 1000 个包
    }
)
```

### 4. 实时监控 + 告警

```python
import pyshark

def alert_callback(pkt):
    """实时检测可疑流量并告警"""
    if hasattr(pkt, 'http'):
        uri = pkt.http.request_uri if hasattr(pkt.http, 'request_uri') else ''
        if '/admin' in uri or '/shell' in uri:
            print(f"[!] 可疑请求: {pkt.ip.src} -> {uri}")

    if hasattr(pkt, 'tcp'):
        dstport = int(pkt.tcp.dstport)
        if dstport == 4444:
            print(f"[!] 反弹 Shell: {pkt.ip.src} -> {pkt.ip.dst}:{dstport}")


cap = pyshark.LiveCapture(interface='eth0')
cap.apply_on_packets(alert_callback, timeout=300)
cap.close()
```

### 5. 多网卡抓包

```python
# LiveCapture 不直接支持多网卡
# 替代方案：多线程各抓一个网卡
import threading
import pyshark

def capture_interface(interface, output_file):
    cap = pyshark.LiveCapture(
        interface=interface,
        output_file=output_file
    )
    cap.sniff(timeout=60)
    cap.close()
    print(f"{interface} 抓包完成 -> {output_file}")


threads = []
for iface, outfile in [('eth0', 'eth0.pcap'), ('eth1', 'eth1.pcap')]:
    t = threading.Thread(target=capture_interface, args=(iface, outfile))
    t.start()
    threads.append(t)

for t in threads:
    t.join()
```

---

## 十二、自动化分析脚本

### 1. 一键 pcap 分析报告

```python
#!/usr/bin/env python3
"""pcap_auto_report.py - 一键生成 pcap 分析报告"""

import pyshark
from collections import Counter, defaultdict


def analyze_pcap(pcap_path):
    cap = pyshark.FileCapture(
        input_file=pcap_path,
        keep_packets=False
    )

    proto_count = Counter()
    ip_src_count = Counter()
    ip_dst_count = Counter()
    http_hosts = Counter()
    http_uris = Counter()
    dns_names = Counter()
    conversations = defaultdict(int)

    for pkt in cap:
        # 协议统计
        proto_count[pkt.highest_layer] += 1

        # IP 统计
        if hasattr(pkt, 'ip'):
            ip_src_count[pkt.ip.src] += 1
            ip_dst_count[pkt.ip.dst] += 1
            conversations[f"{pkt.ip.src} <-> {pkt.ip.dst}"] += 1

        # HTTP 统计
        if hasattr(pkt, 'http'):
            if hasattr(pkt.http, 'host'):
                http_hosts[pkt.http.host] += 1
            if hasattr(pkt.http, 'request_uri'):
                http_uris[pkt.http.request_uri] += 1

        # DNS 统计
        if hasattr(pkt, 'dns') and hasattr(pkt.dns, 'qry_name'):
            dns_names[pkt.dns.qry_name] += 1

    cap.close()

    # 输出报告
    print("=" * 60)
    print(f"PCAP 分析报告: {pcap_path}")
    print("=" * 60)

    print("\n[1] 协议分布:")
    for proto, count in proto_count.most_common(15):
        print(f"  {count:6d}  {proto}")

    print("\n[2] Top 10 源 IP:")
    for ip, count in ip_src_count.most_common(10):
        print(f"  {count:6d}  {ip}")

    print("\n[3] Top 10 目的 IP:")
    for ip, count in ip_dst_count.most_common(10):
        print(f"  {count:6d}  {ip}")

    print("\n[4] Top 10 通信对:")
    for conv, count in sorted(conversations.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {count:6d}  {conv}")

    if http_hosts:
        print("\n[5] HTTP Host Top 10:")
        for host, count in http_hosts.most_common(10):
            print(f"  {count:6d}  {host}")

    if dns_names:
        print("\n[6] DNS 查询 Top 10:")
        for name, count in dns_names.most_common(10):
            print(f"  {count:6d}  {name}")


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print(f"用法: python3 {sys.argv[0]} <pcap_file>")
        sys.exit(1)
    analyze_pcap(sys.argv[1])
```

### 2. CTF 流量题自动化解题框架

```python
#!/usr/bin/env python3
"""ctf_pcap_solver.py - CTF 流量题自动化解题框架"""

import pyshark
import re


class CtfPcapSolver:
    def __init__(self, pcap_path):
        self.pcap_path = pcap_path

    def search_flag(self, patterns=None):
        """在流量中搜索 flag"""
        if patterns is None:
            patterns = [r'flag\{[^}]+\}', r'FLAG\{[^}]+\}', r'ctf\{[^}]+\}']

        flags_found = set()
        cap = pyshark.FileCapture(
            input_file=self.pcap_path,
            keep_packets=False
        )

        for pkt in cap:
            pkt_str = str(pkt)
            for pattern in patterns:
                matches = re.findall(pattern, pkt_str)
                flags_found.update(matches)

        cap.close()
        return flags_found

    def export_http_objects_info(self):
        """列出 HTTP 传输的文件信息"""
        cap = pyshark.FileCapture(
            input_file=self.pcap_path,
            display_filter='http',
            keep_packets=False
        )

        for pkt in cap:
            if hasattr(pkt, 'http'):
                if hasattr(pkt.http, 'content_type'):
                    src = pkt.ip.src if hasattr(pkt, 'ip') else '?'
                    print(f"  {src} -> {pkt.http.content_type}")

        cap.close()

    def check_dns_tunnel(self, threshold=30):
        """检测 DNS 隧道"""
        cap = pyshark.FileCapture(
            input_file=self.pcap_path,
            display_filter='dns.qry.name',
            keep_packets=False
        )

        suspicious = []
        for pkt in cap:
            if hasattr(pkt.dns, 'qry_name'):
                name = pkt.dns.qry_name
                parts = name.split('.')
                if parts and len(parts[0]) > threshold:
                    suspicious.append(name)

        cap.close()
        return suspicious

    def check_reverse_shell(self, suspicious_ports=None):
        """检测反弹 Shell 特征端口"""
        if suspicious_ports is None:
            suspicious_ports = [4444, 5555, 6666, 7777, 8888, 9999, 1234, 31337]

        cap = pyshark.FileCapture(
            input_file=self.pcap_path,
            display_filter='tcp.flags.syn == 1 and tcp.flags.ack == 0',
            keep_packets=False
        )

        for pkt in cap:
            dstport = int(pkt.tcp.dstport)
            if dstport in suspicious_ports:
                print(f"[!] 可疑端口: {pkt.ip.src} -> {pkt.ip.dst}:{dstport}")

        cap.close()

    def full_scan(self):
        """全量扫描"""
        print("=" * 60)
        print(f"CTF 流量分析: {self.pcap_path}")
        print("=" * 60)

        # 1. 搜索 flag
        print("\n[1] 搜索 flag:")
        flags = self.search_flag()
        if flags:
            for f in flags:
                print(f"  [FOUND] {f}")
        else:
            print("  未直接找到明文 flag")

        # 2. 检查 DNS 隧道
        print("\n[2] DNS 隧道检测:")
        dns_suspicious = self.check_dns_tunnel()
        if dns_suspicious:
            print(f"  发现 {len(dns_suspicious)} 个可疑长子域:")
            for name in dns_suspicious[:5]:
                print(f"    {name}")
        else:
            print("  未发现 DNS 隧道特征")

        # 3. 检查反弹 Shell
        print("\n[3] 反弹 Shell 检测:")
        self.check_reverse_shell()

        # 4. HTTP 对象
        print("\n[4] HTTP 传输文件:")
        self.export_http_objects_info()


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print(f"用法: python3 {sys.argv[0]} <pcap_file>")
        sys.exit(1)
    solver = CtfPcapSolver(sys.argv[1])
    solver.full_scan()
```

### 3. 实时流量监控脚本

```python
#!/usr/bin/env python3
"""realtime_monitor.py - 实时流量监控"""

import pyshark
from collections import Counter
from datetime import datetime


class TrafficMonitor:
    def __init__(self, interface='eth0'):
        self.interface = interface
        self.ip_counter = Counter()
        self.dns_counter = Counter()
        self.http_counter = Counter()

    def on_packet(self, pkt):
        """每个包的处理回调"""
        timestamp = datetime.now().strftime('%H:%M:%S')

        # IP 统计
        if hasattr(pkt, 'ip'):
            src = pkt.ip.src
            dst = pkt.ip.dst
            self.ip_counter[src] += 1

        # DNS 监控
        if hasattr(pkt, 'dns') and hasattr(pkt.dns, 'qry_name'):
            name = pkt.dns.qry_name
            self.dns_counter[name] += 1
            print(f"[{timestamp}] DNS: {name}")

        # HTTP 监控
        if hasattr(pkt, 'http'):
            if hasattr(pkt.http, 'request_method'):
                method = pkt.http.request_method
                uri = pkt.http.request_uri if hasattr(pkt.http, 'request_uri') else '/'
                host = pkt.http.host if hasattr(pkt.http, 'host') else '?'
                print(f"[{timestamp}] HTTP: {method} {host}{uri}")

    def start(self, timeout=60):
        print(f"开始监控 {self.interface}，持续 {timeout} 秒...")
        cap = pyshark.LiveCapture(interface=self.interface)
        cap.apply_on_packets(self.on_packet, timeout=timeout)
        cap.close()

        # 输出统计
        print("\n=== 监控统计 ===")
        print(f"\nTop 10 源 IP:")
        for ip, count in self.ip_counter.most_common(10):
            print(f"  {count:4d}  {ip}")

        if self.dns_counter:
            print(f"\nTop 10 DNS 查询:")
            for name, count in self.dns_counter.most_common(10):
                print(f"  {count:4d}  {name}")


if __name__ == '__main__':
    import sys
    iface = sys.argv[1] if len(sys.argv) > 1 else 'eth0'
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    monitor = TrafficMonitor(interface=iface)
    monitor.start(timeout=timeout)
```

---

## 十三、实战技巧与踩坑

### 1. 性能优化

pyshark 的性能瓶颈在于 tshark 子进程启动和 XML/JSON 解析开销。以下技巧可显著提速：

```python
# 1. 用 display_filter 在 tshark 侧过滤，减少传输和解析量
cap = pyshark.FileCapture(
    input_file='huge.pcap',
    display_filter='http.request',  # 只读 HTTP 请求
    keep_packets=False              # 不保留已读包
)

# 2. use_ek=True 使用 EK JSON 模式，比 XML 快
cap = pyshark.FileCapture(
    input_file='huge.pcap',
    use_ek=True,
    keep_packets=False
)

# 3. only_summaries=True 仅读摘要（速度最快但信息少）
cap = pyshark.FileCapture(
    input_file='huge.pcap',
    only_summaries=True
)

# 4. disable_protocol 禁用不需要的协议
cap = pyshark.FileCapture(
    input_file='huge.pcap',
    disable_protocol='dns',
    keep_packets=False
)

# 5. 大文件避免 len(cap) 和随机访问
# 错误：这会把整个文件读入内存
# total = len(cap)
# 正确：遍历时计数
count = 0
for pkt in cap:
    count += 1
```

### 2. 常见踩坑

1. tshark 找不到

```python
# 报错：tshark not found
# 原因：tshark 不在 PATH 中
# 解决：指定 tshark_path
cap = pyshark.FileCapture(
    input_file='test.pcap',
    tshark_path='C:/Program Files/Wireshark/tshark.exe'
)
```

2. 属性不存在报错

```python
# 报错：AttributeError: No attribute 'http'
# 原因：不是所有包都有 HTTP 层
# 解决：用 hasattr 检查
if hasattr(pkt, 'http'):
    print(pkt.http.host)

# 或 try-except
try:
    print(pkt.http.host)
except AttributeError:
    pass
```

3. 字段值是字符串

```python
# 错误：直接比较
if pkt.tcp.dstport == 80:  # 永远 False，dstport 是字符串 '80'
    pass

# 正确：转整数或字符串比较
if int(pkt.tcp.dstport) == 80:
    pass
if pkt.tcp.dstport == '80':
    pass
```

4. 内存暴涨

```python
# 原因：默认 keep_packets=True 保留所有包
# 解决：大文件用 keep_packets=False
cap = pyshark.FileCapture(
    input_file='huge.pcap',
    keep_packets=False
)
```

5. FileCapture 的 bpf_filter 不生效

```python
# FileCapture 的 bpf_filter 存在已知 bug
# 解决：改用 display_filter
# 不推荐：
# cap = pyshark.FileCapture(input_file='f.pcap', bpf_filter='tcp port 80')
# 推荐：
cap = pyshark.FileCapture(input_file='f.pcap', display_filter='tcp.port == 80')
```

6. 子进程残留

```python
# pyshark 启动 tshark 子进程，用完必须 close()
# 否则子进程不会自动退出
cap = pyshark.FileCapture(input_file='test.pcap')
for pkt in cap:
    process(pkt)
cap.close()  # 必须！

# 推荐用 with 语句（部分版本支持）
# 或 try-finally 确保关闭
cap = pyshark.FileCapture(input_file='test.pcap')
try:
    for pkt in cap:
        process(pkt)
finally:
    cap.close()
```

7. 循环中重复创建 Capture 对象

```python
# 错误：每次循环都启动新的 tshark 子进程
while True:
    cap = pyshark.LiveCapture(interface='eth0')
    for pkt in cap.sniff_continuously(packet_count=10):
        process(pkt)
    # cap.close() 忘了关，子进程堆积！

# 正确：创建一次，持续使用
cap = pyshark.LiveCapture(interface='eth0')
try:
    for pkt in cap.sniff_continuously():
        process(pkt)
finally:
    cap.close()
```

8. use_ek 模式下字段访问差异

```python
# EK JSON 模式下，某些嵌套字段的名称可能不同
# 如 tls.handshake.extensions_server_name 在 EK 模式下可能需要：
if hasattr(pkt, 'tls'):
    # 尝试不同写法
    sni = None
    if hasattr(pkt.tls, 'handshake_extensions_server_name'):
        sni = pkt.tls.handshake_extensions_server_name
    elif hasattr(pkt.tls, 'handshake'):
        # 可能需要更深层的访问
        pass
```

### 3. 何时用 pyshark vs 直接用 tshark

| 场景 | 推荐工具 | 原因 |
|------|----------|------|
| 批量提取几个字段到 CSV | tshark 命令行 | 更快更简单 |
| 逐包做复杂条件判断 | pyshark | Python 逻辑灵活 |
| 提取后需要复杂统计/聚合 | pyshark | 直接用 Python 生态 |
| 需要跨包关联分析 | pyshark | 状态保存在 Python 变量中 |
| CI/CD 管道处理 | tshark 命令行 | 更轻量 |
| 实时监控 + 告警 | pyshark | 回调模式天然适合 |
| CTF 流量题解题脚本 | pyshark | 快速原型 + 灵活处理 |
| 处理超大 pcap (>1GB) | tshark + awk | pyshark 内存开销大 |

---

## 十四、速查表

### 捕获对象

```python
# 文件
cap = pyshark.FileCapture(input_file='file.pcap')
cap = pyshark.FileCapture(input_file='file.pcap', display_filter='http.request')
cap = pyshark.FileCapture(input_file='file.pcap', keep_packets=False)

# 实时
cap = pyshark.LiveCapture(interface='eth0')
cap = pyshark.LiveCapture(interface='eth0', bpf_filter='tcp port 80')
cap = pyshark.LiveCapture(interface='eth0', display_filter='http.request')

# 远程
cap = pyshark.RemoteCapture(remote_host='192.168.1.1', remote_interface='eth0')

# 环缓冲
cap = pyshark.LiveRingCapture(interface='eth0', ring_file_size=102400, num_ring_files=10)
```

### 遍历方式

```python
# 方式一：for 遍历
for pkt in cap:
    process(pkt)

# 方式二：生成器（实时推荐）
for pkt in cap.sniff_continuously(packet_count=50):
    process(pkt)

# 方式三：回调
cap.apply_on_packets(callback, timeout=60)

# 方式四：异步
await cap.packets_from_tshark(async_callback, packet_count=50)
```

### 字段访问

```python
pkt.ip.src                        # 源 IP
pkt.ip.dst                        # 目的 IP
pkt.tcp.srcport                   # 源端口
pkt.tcp.dstport                   # 目的端口
pkt.http.host                     # HTTP Host
pkt.http.request_uri              # HTTP URI
pkt.dns.qry_name                  # DNS 域名
pkt.tls.handshake_extensions_server_name  # TLS SNI
pkt.layers                        # 所有层
pkt.highest_layer                 # 最高层协议
pkt.number                        # 帧号
pkt.sniff_time                    # 捕获时间
hasattr(pkt, 'http')              # 安全检查
```

### 过滤器

```python
# BPF（仅 LiveCapture）
bpf_filter='tcp port 80'
bpf_filter='host 192.168.1.1'
bpf_filter='not port 22'

# 显示过滤器（所有 Capture）
display_filter='http.request'
display_filter='tcp.port == 4444'
display_filter='ip.addr == 10.0.0.1'
display_filter='dns.qry.name'
display_filter='tls.handshake.type == 1'
```

### TLS 解密

```python
# SSLKEYLOGFILE
override_prefs={'tls.keylog_file': './keylog.txt'}

# RSA 私钥
override_prefs={'tls.keys_file': './server.key,,,'}

# WPA2
decryption_key='SSID:Password'
encryption_type='wpa-pwd'
```

### 性能优化

```python
keep_packets=False        # 不保留已读包
use_ek=True              # EK JSON 模式（更快）
only_summaries=True      # 仅摘要（最快）
display_filter='http'    # 侧过滤
disable_protocol='dns'   # 禁用不需要的协议
```

### 子进程管理

```python
cap.close()               # 用完必须关闭！
# 推荐用 try-finally
try:
    for pkt in cap:
        process(pkt)
finally:
    cap.close()
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
tcp.stream eq 5                                 # 指定 TCP 流
icmp and data                                   # ICMP 有数据
usb.capdata                                     # USB HID 数据
```

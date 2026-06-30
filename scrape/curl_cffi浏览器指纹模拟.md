# curl_cffi：浏览器指纹模拟 HTTP 客户端实战

> 现代反爬虫的核心不再是看你的 `User-Agent` 写得像不像浏览器，而是看你的 **TLS 握手** 像不像浏览器。`curl_cffi` 通过模拟真实浏览器的 TLS/JA3/HTTP2 指纹，让 Python 爬虫在网络层面"变成"Chrome、Safari、Edge 甚至 Firefox。本文系统介绍其原理、安装、不同浏览器的模拟方法及实战用法。

---

## 一、为什么需要 curl_cffi

### 1.1 TLS 指纹检测的原理

当客户端与 HTTPS 服务器建立连接时，会进行 TLS 握手。握手过程中客户端发送的 `ClientHello` 报文包含一组独特的参数：

```
TLS 握手关键参数：
  - 支持的密码套件（Cipher Suites）及其顺序
  - 支持的 TLS 扩展（Extensions）及其顺序
  - 支持的椭圆曲线（Elliptic Curves）
  - 支持的签名算法（Signature Algorithms）
  - ALPN 协议列表（如 h2, http/1.1）

这些参数组合后经哈希计算 → JA3 指纹
HTTP/2 的 SETTINGS 帧参数组合 → JA4 / Akamai 指纹
```

**关键问题**：不同 HTTP 客户端的 TLS 库（OpenSSL、GnuTLS、BoringSSL）产生的指纹各不相同：

| 客户端 | TLS 库 | JA3 特征 |
|--------|--------|----------|
| Chrome | BoringSSL | 特定的密码套件顺序和扩展 |
| Firefox | NSS | 不同于 Chrome 的扩展组合 |
| Python requests | OpenSSL | 与任何浏览器都不匹配 |
| curl | OpenSSL | 与任何浏览器都不匹配 |
| Safari | Secure Transport | 苹果系统特有指纹 |

Cloudflare、Akamai、Imperva 等 WAF/反爬服务商维护着庞大的指纹库，能精准识别非浏览器流量。**即使你把 `User-Agent` 设成 `Mozilla/5.0 ...`，TLS 指纹依然会暴露你是 Python 脚本。**

### 1.2 curl_cffi 的解决方案

`curl_cffi` 是 [curl-impersonate](https://github.com/lwthiker/curl-impersonate) 的 Python 绑定（通过 CFFI）。curl-impersonate 对 curl 进行了底层修改：

```
1. TLS 库替换：使用浏览器所用的 BoringSSL/NSS 而非 OpenSSL
2. 扩展顺序调整：精确匹配浏览器的 TLS 扩展排列
3. HTTP/2 定制：匹配浏览器的 SETTINGS 帧和窗口大小
4. 密码套件配置：使用 --ciphers、--curves 精确模拟
```

最终效果：从网络数据包层面看，`curl_cffi` 发出的请求与真实浏览器**几乎无法区分**。

---

## 二、安装与快速上手

### 2.1 安装

```bash
pip install curl_cffi --upgrade
```

要求 Python 3.10+。安装时会自动下载对应平台的预编译二进制（包含修改过的 libcurl），无需手动编译。

安装 beta 版本：

```bash
pip install curl_cffi --upgrade --pre
```

### 2.2 最简示例

```python
from curl_cffi import requests

# impersonate="chrome" 自动使用最新 Chrome 指纹
response = requests.get("https://tls.browserleaks.com/json", impersonate="chrome")
print(response.json())
# 输出中 ja3n_hash 应与真实 Chrome 一致
```

对比不加 `impersonate` 参数：

```python
# 不模拟浏览器，使用 curl 默认指纹
response = requests.get("https://tls.browserleaks.com/json")
# ja3n_hash 会暴露为 curl/OpenSSL 指纹
```

### 2.3 验证指纹效果

以 Walmart 反爬页面为例：

```python
from curl_cffi import requests

# 不模拟浏览器 → 返回 CAPTCHA 反爬页面
r1 = requests.get("https://www.walmart.com/search?q=keyboard")
print(r1.text[:200])  # "Robot or human?"

# 模拟 Chrome → 返回正常商品页
r2 = requests.get("https://www.walmart.com/search?q=keyboard", impersonate="chrome")
print(r2.text[:200])  # "<!DOCTYPE html>..." 正常 HTML
```

---

## 三、针对不同浏览器的模拟

这是 `curl_cffi` 的核心能力。通过 `impersonate` 参数指定目标浏览器及其版本。

### 3.1 支持的浏览器类型

```
Chrome 系列（基于 BoringSSL）
  ├── chrome99 ~ chrome146（桌面版）
  ├── chrome99_android, chrome131_android（安卓版）
  └── chrome133a（A/B 测试变体）

Edge 系列（基于 BoringSSL）
  ├── edge99
  └── edge101

Safari 系列（基于 Secure Transport/BoringSSL）
  ├── safari153, safari155, safari170
  ├── safari180, safari184
  ├── safari172_ios, safari180_ios, safari184_ios
  └── safari260, safari260_ios, safari2601

Firefox 系列（基于 NSS，v0.9.0+ 支持）
  ├── firefox133, firefox135
  ├── firefox144, firefox147
  └── tor145（Tor Browser）

通用别名（始终指向最新版本）
  ├── chrome        → 最新 Chrome 桌面版
  ├── firefox       → 最新 Firefox
  ├── safari        → 最新 Safari 桌面版
  ├── safari_ios    → 最新 Safari iOS 版
  └── chrome_android → 最新 Chrome 安卓版
```

### 3.2 选择浏览器的策略

```python
from curl_cffi import requests

# 策略 1：使用通用别名，始终跟随库更新到最新版本（推荐）
r = requests.get(url, impersonate="chrome")

# 策略 2：指定具体版本，锁定指纹（适合需要稳定复现的场景）
r = requests.get(url, impersonate="chrome131")

# 策略 3：模拟移动端（部分站点移动端反爬较弱）
r = requests.get(url, impersonate="safari_ios")
r = requests.get(url, impersonate="chrome_android")

# 策略 4：模拟 Firefox（v0.9.0+ 支持，适合目标站点对 Chrome 有额外检测时）
r = requests.get(url, impersonate="firefox")
```

**版本选择建议**：

1. **默认用 `chrome`**：覆盖面最广，绝大多数站点不会拦截真实 Chrome。
2. **被拦截时换 `safari` 或 `firefox`**：部分站点对 Chrome 流量做额外行为检测，换浏览器类型可能绕过。
3. **移动端站点用 `safari_ios`**：iOS 对 WebView 和 TLS 库有限制，很多 App 的指纹与 Safari iOS 接近。
4. **跳过的版本用上一版**：如 `chrome122` 未收录，用 `chrome120` 即可（指纹未变才会新增版本）。

### 3.3 指纹轮换的最佳实践

> **核心原则：模拟"一个稳定的真实用户"，而不是"一个会变形的爬虫"。** 频繁轮换不同浏览器版本并非最佳实践，反而可能暴露自动化特征。

#### 分场景策略

**场景一：常规抓取（推荐固定单一最新版本）**

```python
# 推荐：整个项目固定用一个最新版本
with requests.Session(impersonate="chrome") as s:
    r = s.get(url)
```

理由：
1. **真实用户行为模型**：一个真实用户在一次会话中不会每秒切换浏览器版本，频繁切换指纹反而暴露自动化特征。
2. **Cookie 与指纹一致性**：Session 中的 Cookie 是在某个浏览器指纹下获取的（如 `cf_clearance`），切换浏览器类型后 Cookie 可能失效，触发新一轮验证。
3. **HTTP/2 连接复用**：同一 Session 内切换指纹会破坏连接复用，降低性能。
4. **日志可追溯**：固定指纹便于调试和复现问题。

**场景二：被拦截时的降级策略（按"类型"切换，而非"版本"切换）**

```python
# 降级链：chrome → safari → firefox
FINGERPRINT_CHAIN = ["chrome", "safari", "firefox"]

def fetch_with_fallback(url):
    with requests.Session() as s:
        for fp in FINGERPRINT_CHAIN:
            try:
                r = s.get(url, impersonate=fp, timeout=15)
                if r.status_code == 200 and not is_blocked(r.text):
                    return r
            except Exception:
                continue
    return None
```

**切换的是浏览器"类型"（Chrome/Safari/Firefox），而不是同类型的"版本"（chrome120/chrome131/chrome146）**。因为：
- 同类型不同版本的 JA3 指纹差异很小，反爬系统通常按"指纹族"识别，换版本意义不大
- 不同类型（BoringSSL vs NSS vs Secure Transport）的指纹差异显著，才有绕过价值

**场景三：大规模分布式爬虫（按 IP 分配固定指纹，而非每次请求轮换）**

```python
# 每个代理 IP 绑定一个固定指纹，模拟"不同真实用户"
PROXY_FP_PAIRS = [
    ("http://proxy1:8080", "chrome"),
    ("http://proxy2:8080", "safari"),
    ("http://proxy3:8080", "firefox"),
    ("http://proxy4:8080", "chrome131"),  # 锁定版本
]

def fetch(url, pair):
    proxy, fp = pair
    with requests.Session(impersonate=fp, proxies={"https": proxy}) as s:
        return s.get(url)
```

**关键原则：一个 IP + 指纹组合应保持稳定，模拟一个"持续存在的真实用户"，而不是"会变形的机器人"**。

#### 不推荐的错误做法

```python
# ❌ 错误 1：每次请求随机轮换版本
browsers = ["chrome120", "chrome131", "chrome146", "safari17_0", "firefox135"]
r = requests.get(url, impersonate=random.choice(browsers))
# 问题：同一 Session/IP 下指纹频繁变化，比固定指纹更可疑

# ❌ 错误 2：同类型版本轮换
r = requests.get(url, impersonate="chrome120")
r = requests.get(url, impersonate="chrome131")  # 同族换版本无意义
r = requests.get(url, impersonate="chrome146")

# ❌ 错误 3：在已建立 Cookie 的会话中切换指纹
with requests.Session(impersonate="chrome") as s:
    s.get("https://site.com/login")  # 获取 Cookie
    s.get("https://site.com/data", impersonate="safari")  # Cookie 可能失效
```

#### 策略速查表

| 场景 | 推荐策略 |
|------|----------|
| 单机常规抓取 | 固定 `impersonate="chrome"` |
| 被反爬拦截 | 按**类型**降级：chrome → safari → firefox |
| 大规模分布式 | 每个 IP 绑定固定指纹，长期不变 |
| 需要稳定复现 | 锁定具体版本如 `chrome131` |
| 移动端站点 | 用 `safari_ios` 或 `chrome_android` |

**总结**：指纹轮换是最后的兜底手段，不应作为常规策略。优先固定指纹 + 代理 IP 轮换 + 请求频率控制。

### 3.4 验证不同浏览器指纹

```python
from curl_cffi import requests

browsers = ["chrome", "safari", "firefox", "edge101", "safari_ios"]

for browser in browsers:
    try:
        r = requests.get("https://tls.browserleaks.com/json", impersonate=browser)
        data = r.json()
        print(f"[{browser:>12}] ja3n_hash: {data.get('ja3n_hash', 'N/A')[:16]}...")
        print(f"{'':>14} user-agent: {data.get('user_agent', 'N/A')[:60]}")
    except Exception as e:
        print(f"[{browser:>12}] 错误: {e}")
```

输出示例：

```
[      chrome] ja3n_hash: 5d1b58f1e1f3a2c4...
                user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...Chrome/136...
[      safari] ja3n_hash: 8a2c4e6f7b3d1a5c...
                user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...Safari/605.1.15
[     firefox] ja3n_hash: 3f7e2d1c9b8a6f4e...
                user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101
[     edge101] ja3n_hash: 1a2b3c4d5e6f7a8b...
                user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...Edg/101.0.1210.53
[  safari_ios] ja3n_hash: 7e8f9a0b1c2d3e4f...
                user-agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) ...
```

每个浏览器的 JA3 指纹都不同，且与真实浏览器一致。

### 3.4 自定义指纹（非浏览器目标）

对于需要模拟非浏览器客户端（如 okhttp、Python urllib3）的场景，可使用 `ja3`、`akamai`、`extra_fp` 参数：

```python
from curl_cffi import requests

# 使用自定义 JA3 指纹
r = requests.get(
    url,
    ja3="771,4865-4866-4867-49195-49199-52393-52392-49196-49200-49162-49161-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513,29-23-24,0",
    extra_fp={
        "tls_signature_algorithms": [
            "ECDSAWithSHA256", "SSLV3_RSA_SHA256",
            "ECDSAWithSHA384", "SSLV3_RSA_SHA384",
            "ECDSAWithSHA512", "SSLV3_RSA_SHA512",
            "RSA_PSS_SHA256", "RSA_PSS_SHA384", "RSA_PSS_SHA512",
            "Ed25519",
        ],
    },
)
```

### 3.5 完全可编辑的指纹对象

从 v0.11+ 开始，可通过 `get_fingerprint` 获取指纹对象并自定义：

```python
import curl_cffi

# 获取指纹对象
fingerprint = curl_cffi.get_fingerprint("chrome")

# 修改 User-Agent（默认会自动设置匹配的 UA）
fingerprint.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Custom/1.0"

# 用自定义指纹发请求
r = curl_cffi.get("https://httpbin.org/headers", impersonate=fingerprint)
```

---

## 四、核心 API 用法

`curl_cffi` 的 API 设计模仿 `requests`，迁移成本极低。

### 4.1 请求方法

```python
from curl_cffi import requests

# GET
r = requests.get(url, params={"q": "keyword"}, impersonate="chrome")

# POST 表单
r = requests.post(url, data={"username": "admin", "password": "123456"}, impersonate="chrome")

# POST JSON
r = requests.post(url, json={"key": "value"}, impersonate="chrome")

# POST 二进制
r = requests.post(url, data=b"\x00\x01\x02", impersonate="chrome")

# PUT / DELETE / PATCH
r = requests.put(url, json=data, impersonate="chrome")
r = requests.delete(url, impersonate="chrome")
```

### 4.2 请求头处理

```python
from curl_cffi import requests

# 默认情况下，impersonate 会自动设置匹配的浏览器请求头
r = requests.get("https://httpbin.org/headers", impersonate="chrome")
# 自动包含: sec-ch-ua, sec-fetch-*, user-agent 等

# 覆盖部分请求头
r = requests.get(
    url,
    impersonate="chrome",
    headers={"Accept-Language": "zh-CN,zh;q=0.9", "X-Custom": "value"}
)

# 完全关闭默认请求头（只发送你指定的）
r = requests.get(url, impersonate="chrome", default_headers=False, headers={"User-Agent": "custom"})
```

### 4.3 文件上传

`curl_cffi` 不支持 `requests` 的 `files=` 参数，使用 `multipart=` 替代：

```python
import curl_cffi

mp = curl_cffi.CurlMime()
mp.addpart(
    name="attachment",          # 表单字段名
    content_type="image/png",   # MIME 类型
    filename="image.png",       # 服务器看到的文件名
    local_path="./image.png",   # 本地文件路径
    # data=file.read(),         # 或直接传二进制数据
)

r = curl_cffi.post(url, data={"foo": "bar"}, multipart=mp, impersonate="chrome")
```

### 4.4 响应处理

```python
r = requests.get(url, impersonate="chrome")

r.status_code      # 状态码
r.text             # 解码后的字符串
r.content          # 原始字节
r.json()           # JSON 解析
r.headers          # 响应头（大小写不敏感）
r.url              # 最终 URL（重定向后）
r.encoding         # 编码
r.encoding = "gbk" # 强制指定编码

# 流式读取
r = requests.get(url, stream=True, impersonate="chrome")
for chunk in r.iter_content():
    process(chunk)

# 原生回调式流式（性能更好）
def callback(chunk):
    process(chunk)

r = requests.get(url, content_callback=callback, impersonate="chrome")
```

---

## 五、Session 与高级特性

### 5.1 Session 会话管理

**强烈建议始终使用 Session**，可以复用连接、持久化 Cookie：

```python
from curl_cffi import requests

# 推荐用上下文管理器
with requests.Session(impersonate="chrome") as s:
    # 第一次请求设置的 Cookie 会自动保留
    s.get("https://httpbin.org/cookies/set/foo/bar")
    
    # 第二次请求自动携带 Cookie
    r = s.get("https://httpbin.org/cookies")
    print(r.json())  # {'cookies': {'foo': 'bar'}}

# Session 级别设置默认参数
with requests.Session(
    impersonate="chrome",
    headers={"Accept-Language": "zh-CN,zh;q=0.9"},
    timeout=30,
) as s:
    r = s.get("https://example.com")
```

### 5.2 代理集成

```python
from curl_cffi import requests

# HTTP/HTTPS/SOCKS 代理均支持
proxies = {
    "http": "http://user:pass@proxy:8080",
    "https": "http://user:pass@proxy:8080",
    # "https": "socks5://user:pass@proxy:1080",
}

with requests.Session(impersonate="chrome", proxies=proxies) as s:
    r = s.get("https://api.ipify.org?format=json")
    print(r.json())  # 代理 IP

# 每次请求轮换代理（反爬关键技巧）
proxy_pool = ["http://proxy1:8080", "http://proxy2:8080", "http://proxy3:8080"]
with requests.Session(impersonate="chrome") as s:
    for url in urls:
        proxy = {"https": proxy_pool[i % len(proxy_pool)]}
        r = s.get(url, proxies=proxy)
```

### 5.3 重试机制

```python
from curl_cffi import requests, RetryStrategy

# 简单重试次数
with requests.Session(impersonate="chrome", retry=3) as s:
    r = s.get(url)

# 自定义重试策略
strategy = RetryStrategy(
    count=3,                # 重试次数
    delay=0.2,              # 初始延迟
    jitter=0.1,             # 随机抖动
    backoff="exponential",  # 退避策略
)
with requests.Session(impersonate="chrome", retry=strategy) as s:
    r = s.get(url)
```

### 5.4 响应缓存

适合测试场景或需要稳定上游响应的场景：

```python
from datetime import timedelta
from curl_cffi import requests

with requests.Session(impersonate="chrome", cache=timedelta(minutes=5)) as s:
    # 第一次请求走网络
    r1 = s.get("https://example.com/api")
    # 5 分钟内第二次请求走缓存
    r2 = s.get("https://example.com/api")
```

### 5.5 认证

```python
from curl_cffi import requests

# Basic Auth
r = requests.get(url, auth=("user", "password"), impersonate="chrome")

# URL 内嵌认证
r = requests.get("https://user:password@example.com", impersonate="chrome")
```

---

## 六、异步并发

`curl_cffi` 提供完整的 `asyncio` 支持，是高并发爬虫的首选。

### 6.1 基础异步用法

```python
import asyncio
from curl_cffi import AsyncSession

async def fetch(url):
    async with AsyncSession(impersonate="chrome") as s:
        r = await s.get(url)
        return r.text

asyncio.run(fetch("https://example.com"))
```

### 6.2 并发抓取

```python
import asyncio
from curl_cffi import AsyncSession

urls = [
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
]

async def main():
    async with AsyncSession(impersonate="chrome") as s:
        tasks = [s.get(url) for url in urls]
        # 并发执行，总耗时约 1 秒而非 5 秒
        results = await asyncio.gather(*tasks)
        for r in results:
            print(r.status_code, r.url)

asyncio.run(main())
```

### 6.3 信号量控制并发数

```python
import asyncio
from curl_cffi import AsyncSession

async def bounded_fetch(s, url, semaphore):
    async with semaphore:
        r = await s.get(url, impersonate="chrome")
        return r

async def main():
    semaphore = asyncio.Semaphore(10)  # 最多 10 个并发
    async with AsyncSession(impersonate="chrome") as s:
        tasks = [bounded_fetch(s, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)

asyncio.run(main())
```

---

## 七、WebSocket 支持

`curl_cffi` 原生支持 WebSocket，适合抓取实时数据（行情、聊天、推送）。

### 7.1 同步 WebSocket

```python
from curl_cffi import requests, WebSocket

def on_message(ws: WebSocket, message):
    print("收到:", message)

def on_error(ws: WebSocket, error):
    print("错误:", error)

with requests.Session(impersonate="chrome") as session:
    ws = session.ws_connect(
        "wss://api.gemini.com/v1/marketdata/BTCUSD",
        on_message=on_message,
        on_error=on_error,
    )
    ws.run_forever()
```

### 7.2 异步 WebSocket

```python
import asyncio
from curl_cffi import AsyncSession

async def main():
    async with AsyncSession(impersonate="chrome") as session:
        async with session.ws_connect("wss://echo.websocket.org") as ws:
            # 发送消息
            await ws.send_str("Hello, World!")
            
            # 接收消息
            async for message in ws:
                print("收到:", message)
                if "Hello" in str(message):
                    break

asyncio.run(main())
```

---

## 八、HTTP/2 与 HTTP/3

`curl_cffi` 支持 HTTP/2 和 HTTP/3（v0.12.0+ 完整支持），这是 `requests` 所不具备的。

```python
from curl_cffi import requests

# HTTP/2（默认在 impersonate 时启用）
r = requests.get(url, impersonate="chrome")
print(r.http_version)  # "HTTP/2"

# 指定 HTTP 版本
from curl_cffi import CurlHttpVersion
r = requests.get(url, impersonate="chrome", http_version=CurlHttpVersion.V2_0)

# HTTP/3（需要目标站点支持，且使用支持 http3 的指纹如 chrome146）
r = requests.get(url, impersonate="chrome146")
```

---

## 九、实战案例

### 9.1 绕过 Cloudflare 反爬

```python
from curl_cffi import requests
from bs4 import BeautifulSoup

def scrape_cloudflare_protected_site(url):
    with requests.Session(impersonate="chrome") as s:
        # 第一次请求获取 cf_clearance Cookie
        r = s.get(url, timeout=30)
        
        if "cf-browser-verification" in r.text or "challenge" in r.text.lower():
            # 部分场景需要等待或换指纹
            r = s.get(url, impersonate="safari", timeout=30)
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            title = soup.find("title")
            return title.text if title else None
    return None

print(scrape_cloudflare_protected_site("https://example.com"))
```

### 9.2 多浏览器指纹轮换

```python
import random
from curl_cffi import requests

BROWSER_POOL = [
    "chrome", "chrome131", "chrome124",
    "safari", "safari17_0",
    "firefox", "firefox135",
    "edge101",
]

def fetch_with_rotation(url, max_retries=3):
    """指纹轮换抓取，被拦截时换浏览器"""
    with requests.Session() as s:
        for attempt in range(max_retries):
            browser = random.choice(BROWSER_POOL)
            try:
                r = s.get(url, impersonate=browser, timeout=15)
                if r.status_code == 200 and "captcha" not in r.text.lower():
                    return r
                print(f"[尝试 {attempt+1}] {browser} 被拦截")
            except Exception as e:
                print(f"[尝试 {attempt+1}] {browser} 错误: {e}")
    return None
```

### 9.3 完整爬虫示例

```python
import asyncio
from curl_cffi import AsyncSession
from bs4 import BeautifulSoup

async def scrape_product(session, url):
    r = await session.get(url, impersonate="chrome")
    if r.status_code != 200:
        return None
    
    soup = BeautifulSoup(r.text, "html.parser")
    return {
        "url": url,
        "title": soup.find("title").text if soup.find("title") else "",
        # 更多字段提取...
    }

async def main():
    urls = [
        "https://example.com/product/1",
        "https://example.com/product/2",
        "https://example.com/product/3",
    ]
    
    semaphore = asyncio.Semaphore(5)  # 限制并发
    
    async def bounded_scrape(session, url):
        async with semaphore:
            return await scrape_product(session, url)
    
    async with AsyncSession(impersonate="chrome") as session:
        tasks = [bounded_scrape(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
    
    for item in results:
        if item:
            print(item)

asyncio.run(main())
```

---

## 十、与其他 HTTP 客户端对比

| 特性 | curl_cffi | requests | aiohttp | httpx | pycurl |
|------|-----------|----------|---------|-------|--------|
| 同步 API | ✅ | ✅ | ❌ | ✅ | ✅ |
| 异步 API | ✅ | ❌ | ✅ | ✅ | ❌ |
| HTTP/2 | ✅ | ❌ | ❌ | ✅ | ✅ |
| HTTP/3 | ✅ | ❌ | ❌ | ❌ | ✅ |
| WebSocket | ✅ | ❌ | ✅ | ❌ | ❌ |
| TLS 指纹模拟 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 原生重试 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 速度 | 🐇🐇 | 🐇 | 🐇🐇 | 🐇 | 🐇🐇 |
| 代理支持 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cookie 处理 | ✅ | ✅ | ✅ | ✅ | ✅ |

**选型建议**：

- **需要绕过 TLS 指纹检测** → `curl_cffi`（唯一选择）
- **需要 HTTP/2 或 HTTP/3** → `curl_cffi`、`httpx`、`pycurl`
- **纯异步高并发且无反爬** → `aiohttp`（生态成熟）
- **简单场景且无反爬** → `requests`（最简单）
- **需要同时支持同步/异步且无反爬** → `httpx`

---

## 十一、生态集成

`curl_cffi` 可作为其他库的底层传输层：

### 11.1 作为 requests 适配器

```python
import requests
from curl_cffi.requests import Session

# 让 requests 库使用 curl_cffi 的指纹能力
session = requests.Session()
# 通过 urllib3 适配器集成（详见官方文档 Community 章节）
```

### 11.2 作为 httpx 传输层

```python
import httpx
# 详见 https://curl-cffi.readthedocs.io/en/latest/community.html#as-a-httpx-transport
```

### 11.3 Scrapy 集成

```python
# 通过 scrapy-curl-cffi 中间件集成
# 详见 https://curl-cffi.readthedocs.io/en/latest/community.html#scrapy-integrations
```

---

## 十二、常见问题与技巧

### 12.1 指纹更新

从 v0.15.1 开始，可以不更新 `curl_cffi` 本体而单独更新指纹库：

```bash
# 使用 CLI 工具更新指纹
python -m curl_cffi update-fingerprints
```

指纹存储路径详见[官方文档](https://curl-cffi.readthedocs.io/en/latest/fingerprints.html#storage-paths)。

### 12.2 请求头顺序

部分高级反爬会检测请求头顺序。`curl_cffi` 在 `impersonate` 模式下会自动按浏览器顺序排列请求头。如需自定义顺序，使用 `get_fingerprint` 获取可编辑对象。

### 12.3 证书错误

```python
# 遇到证书验证问题时（不推荐在生产环境关闭验证）
r = requests.get(url, impersonate="chrome", verify=False)
```

### 12.4 与抓包工具配合

```python
# 配合 Fiddler/Charles 抓包调试
r = requests.get(
    url,
    impersonate="chrome",
    verify=False,                              # 关闭证书验证
    proxies={"https": "http://127.0.0.1:8888"} # 抓包工具端口
)
```

### 12.5 PyInstaller 打包

打包时需包含 `curl_cffi` 的动态库，详见[官方 FAQ](https://curl-cffi.readthedocs.io/en/latest/faq.html#packaging-with-pyinstaller)。

---

## 十三、注意事项与合规

1. **指纹模拟不是万能的**：高级反爬还会检测行为特征（鼠标轨迹、请求频率、JS 执行），单纯模拟 TLS 指纹可能仍被拦截。
2. **遵守 robots.txt 和目标站点 ToS**：爬虫应在合规前提下进行。
3. **控制请求频率**：即使指纹完美，高频请求仍会触发 IP 封禁，建议配合代理和延迟。
4. **Firefox 支持较新**：v0.9.0+ 才支持 Firefox，早期版本仅支持基于 WebKit/Blink 的浏览器。
5. **商业版**：[impersonate.pro](https://impersonate.pro/) 提供每周更新的指纹库和更多浏览器类型，适合商业级爬虫。

---

## 参考资源

- 官方文档：https://curl-cffi.readthedocs.io/
- GitHub 仓库：https://github.com/lexiforest/curl_cffi
- curl-impersonate 项目：https://github.com/lwthiker/curl-impersonate
- 支持的浏览器目标列表：https://curl-cffi.readthedocs.io/en/latest/impersonate/targets.html
- Bright Data 教程：https://www.bright.cn/blog/web-data/web-scraping-with-curl-cffi
- 商业版指纹库：https://impersonate.pro/

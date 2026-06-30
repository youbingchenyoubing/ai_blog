# CloakBrowser：源码级反检测 Chromium 的理论与实践

> 现代反爬虫的终极战场在 **C++ 源码层**。`playwright-stealth` 之类的 JS 注入方案每次 Chrome 升级都会失效，`undetected-chromedriver` 的配置级补丁无法改变底层渲染行为。CloakBrowser 直接修改 Chromium 源码、重新编译二进制，把指纹伪装做在编译期——反爬系统看到的是一个真正的浏览器，因为它**就是**一个真正的浏览器。本文系统介绍其原理、API、实战用法，以及基于它构建的 cf-killer 自动解盾工具。

---

## 一、为什么需要源码级反检测

### 1.1 反爬检测的三层战场

现代反爬系统（Cloudflare、Akamai、DataDome、PerimeterX）采用分层检测，任何一层失败都会触发拦截：

```
┌─────────────────────────────────────────────────┐
│ 第一层：JavaScript API 检测                      │
│   navigator.webdriver / plugins / window.chrome │
│   → 传统方案：JS 注入覆写（playwright-stealth）  │
├─────────────────────────────────────────────────┤
│ 第二层：渲染指纹检测                              │
│   Canvas / WebGL / Audio / 字体 / GPU           │
│   → 传统方案：无法有效伪造（依赖底层渲染）        │
├─────────────────────────────────────────────────┤
│ 第三层：协议级检测                                │
│   TLS 指纹（JA3/JA4）/ HTTP/2 帧 / TCP 窗口     │
│   → 传统方案：完全够不着（发生在 OS 网络栈）      │
└─────────────────────────────────────────────────┘
```

### 1.2 传统方案的致命缺陷

**方案一：JavaScript 注入（playwright-stealth、puppeteer-extra-stealth）**

```javascript
// playwright-stealth 的做法：注入 JS 覆写属性
Object.defineProperty(navigator, 'webdriver', {
    get: () => false
});
```

问题：
1. **Chrome 升级即失效**：属性路径或函数签名变化导致补丁崩溃
2. **覆写痕迹可被检测**：反爬系统能识别 `Object.getOwnPropertyDescriptor` 被修改
3. **底层渲染无法伪造**：Canvas/WebGL 像素输出由 GPU 驱动决定，JS 够不着

**方案二：配置级补丁（undetected-chromedriver）**

```bash
chrome --disable-blink-features=AutomationControlled
```

问题：只能改启动参数，对运行时产生的指纹信号（Canvas 哈希、WebGL 渲染器、AudioContext 指纹）完全无能为力。

**方案三：Firefox 替代（Camoufox）**

问题：很多站点针对 Chromium 优化，Firefox 兼容性差；API 差异大，跨平台维护成本高。

### 1.3 核心矛盾

```
反爬系统检测的是浏览器的"底层行为特征"
传统方案修改的是浏览器的"表面属性"

→ 表面可以伪装，底层无法伪装
→ 唯一解：修改浏览器源码，让底层本身就是"真实浏览器"
```

---

## 二、CloakBrowser 的核心架构

### 2.1 设计哲学

CloakBrowser 的思路与所有现有方案都不同——**直接修改 Chromium 的 C++ 源码，重新编译二进制文件**。

```
┌─────────────────────────────────────────────┐
│  Python/JS Wrapper（极薄 API 层）            │
│  pip install cloakbrowser                   │
├─────────────────────────────────────────────┤
│  Playwright/Puppeteer API（标准 API）        │
│  无需学习新 API，换个 import 即可             │
├─────────────────────────────────────────────┤
│  Custom Chromium Binary（核心）              │
│  58 个 C++ 源码级补丁，编译进二进制           │
│  Canvas / WebGL / Audio / GPU / WebRTC ...  │
└─────────────────────────────────────────────┘
```

**关键区别**：

| 方案 | 修改层级 | 检测系统看到的是 |
|------|----------|------------------|
| playwright-stealth | JS 运行时注入 | 被打补丁的浏览器 |
| undetected-chromedriver | 启动配置参数 | 配置异常的浏览器 |
| Camoufox | Firefox 源码 | 真实 Firefox |
| **CloakBrowser** | **Chromium C++ 源码** | **真实 Chrome** |

### 2.2 58 个源码级补丁覆盖的维度

v0.3.31 版本的 58 个 C++ 补丁覆盖以下指纹维度（编译进二进制，非 JS 注入）：

```
渲染类指纹：
  ├── Canvas 行为（2D 绘制像素一致性）
  ├── WebGL 渲染器（GPU 型号/驱动版本）
  ├── Audio 行为（AudioContext 哈希）
  ├── 字体枚举（已安装字体列表）
  └── WebGPU 适配器

硬件类指纹：
  ├── GPU 厂商/渲染器
  ├── 硬件并发数（CPU 核心数）
  ├── 设备内存
  ├── 屏幕属性（分辨率/色深）
  └── 客户端矩形（ClientRects）

自动化信号：
  ├── navigator.webdriver = false（源码级移除）
  ├── navigator.plugins（真实插件列表，非空数组）
  ├── window.chrome（完整对象，非 undefined）
  ├── CDP（Chrome DevTools Protocol）行为
  └── 驱动输入行为（输入事件一致性）

网络类指纹：
  ├── TLS 指纹（JA3/JA4/Akamai 与真实 Chrome 一致）
  ├── WebRTC ICE 候选者 IP（防泄漏真实 IP）
  ├── 网络时序（DNS/连接/SSL 时间归零）
  └── 代理信号移除（Proxy-Connection 头泄漏）

环境一致性：
  ├── 时区（与代理 IP 匹配）
  ├── 语言环境（Locale）
  └── 跨平台一致性（本地/Docker/VPS 行为相同）
```

### 2.3 为什么源码级补丁有效

以 `navigator.webdriver` 为例：

```cpp
// 原生 Chromium 源码（自动化特征明显）
bool ChromeClient::isAutomated() {
    return webdriver_client_id_.has_value();  // 返回 true → 被检测
}

// CloakBrowser 修改后的源码
bool ChromeClient::isAutomated() {
    return false;  // 源码级移除自动化标记
}
```

**这不是"隐藏"自动化特征，而是从根本上不存在该特征**。反爬系统检测 `navigator.webdriver` 时，拿到的是 `false`，与真实浏览器完全一致。

同理，Canvas 指纹的修改发生在 Chromium 的 Skia 渲染引擎层，输出的像素数据与真实 Chrome 在统计意义上无法区分。

---

## 三、安装与快速上手

### 3.1 安装

```bash
# Python
pip install cloakbrowser

# Node.js（Playwright 方案）
npm install cloakbrowser playwright-core

# Node.js（Puppeteer 方案）
npm install cloakbrowser puppeteer-core

# 可选：自动从代理 IP 检测时区/语言
pip install cloakbrowser[geoip]
```

首次运行时自动下载 stealth Chromium 二进制（约 200MB，本地缓存）。二进制下载使用 SHA-256 校验确保完整性。

**Docker 体验（无需安装）**：

```bash
docker run --rm cloakhq/cloakbrowser cloaktest
```

### 3.2 最简示例

```python
from cloakbrowser import launch

browser = launch()
page = browser.new_page()
page.goto("https://example.com")
print(page.title())
browser.close()
```

**从 Playwright 迁移只需改一行**：

```diff
- from playwright.sync_api import sync_playwright
- pw = sync_playwright().start()
- browser = pw.chromium.launch()
+ from cloakbrowser import launch
+ browser = launch()
  page = browser.new_page()
  page.goto("https://example.com")
  # ... 其余代码完全不变
```

### 3.3 JavaScript 示例

```javascript
// Playwright 方案
import { launch } from 'cloakbrowser';

const browser = await launch();
const page = await browser.newPage();
await page.goto('https://example.com');
await browser.close();

// Puppeteer 方案
import { launch } from 'cloakbrowser/puppeteer';

const browser = await launch({ headless: true });
const page = await browser.newPage();
await page.goto('https://example.com');
await browser.close();
```

---

## 四、核心 API 详解

### 4.1 `launch()` —— 启动浏览器

```python
from cloakbrowser import launch

# 基础启动（无头模式，默认隐身配置）
browser = launch()

# 有头模式（部分站点检测无头，建议有头）
browser = launch(headless=False)

# 带代理（HTTP 或 SOCKS5）
browser = launch(proxy="http://user:pass@proxy:8080")
browser = launch(proxy="socks5://user:pass@proxy:1080")

# 代理字典（支持 bypass 和分离的认证字段）
browser = launch(proxy={
    "server": "http://proxy:8080",
    "bypass": ".google.com",
    "username": "user",
    "password": "pass"
})

# 额外 Chrome 参数
browser = launch(args=["--disable-gpu"])

# 时区和语言（通过二进制 flag 设置，非可检测的 CDP 模拟）
browser = launch(timezone="America/New_York", locale="en-US")

# 自动从代理 IP 检测时区/语言（需 pip install cloakbrowser[geoip]）
# 同时自动注入 --fingerprint-webrtc-ip 防止 WebRTC IP 泄漏
browser = launch(proxy="http://proxy:8080", geoip=True)

# 显式时区优先于自动检测
browser = launch(proxy="http://proxy:8080", geoip=True, timezone="Europe/London")

# 仅 WebRTC IP 伪装（无需 geoip 依赖，通过代理解析出口 IP）
browser = launch(proxy="http://proxy:8080", args=["--fingerprint-webrtc-ip=auto"])

# 显式 WebRTC IP（无网络调用）
browser = launch(proxy="http://proxy:8080", args=["--fingerprint-webrtc-ip=1.2.3.4"])

# 人类化行为（鼠标贝塞尔曲线、键盘逐字符输入、真实滚动）
browser = launch(humanize=True)

# 更慢更谨慎的移动
browser = launch(humanize=True, human_preset="careful")

# 关闭默认隐身参数（自带指纹 flag）
browser = launch(stealth_args=False, args=["--fingerprint=12345"])
```

返回标准 Playwright `Browser` 对象，所有 Playwright 方法都可用：`new_page()`、`new_context()`、`close()` 等。

### 4.2 `launch_async()` —— 异步启动

```python
import asyncio
from cloakbrowser import launch_async

async def main():
    browser = await launch_async()
    page = await browser.new_page()
    await page.goto("https://example.com")
    print(await page.title())
    await browser.close()

asyncio.run(main())
```

### 4.3 `launch_context()` —— 一次性创建浏览器+上下文

```python
from cloakbrowser import launch_context

context = launch_context(
    user_agent="Custom UA",
    viewport={"width": 1920, "height": 1080},
    locale="en-US",
    timezone="America/New_York",
)
page = context.new_page()
page.goto("https://protected-site.com")
context.close()
```

支持 `storage_state` 恢复会话：

```python
from cloakbrowser import launch_context

# 从 JSON 文件恢复会话（cookies、localStorage）
context = launch_context(storage_state="state.json")
page = context.new_page()
page.goto("https://example.com")

# 保存会话供下次使用
context.storage_state(path="state.json")
context.close()
```

### 4.4 `launch_persistent_context()` —— 持久化上下文

```python
from cloakbrowser import launch_persistent_context

# 跨会话保持 cookies 和 localStorage，绕过隐身模式检测
context = launch_persistent_context(
    user_data_dir="/path/to/profile",
    # 其他参数同 launch()
)
```

---

## 五、反检测能力实测

### 5.1 官方测试结果

v0.3.31（Chromium 146）经 30+ 检测站点实测：

| 检测服务 | 原生 Playwright | CloakBrowser | 说明 |
|----------|-----------------|--------------|------|
| **reCAPTCHA v3** | 0.1（机器人） | **0.9（人类）** | 服务端验证 |
| **Cloudflare Turnstile**（非交互） | 失败 | **通过** | 自动解决 |
| **Cloudflare Turnstile**（managed） | 失败 | **通过** | 单击通过 |
| **ShieldSquare** | 拦截 | **通过** | 生产站点 |
| **FingerprintJS** 机器人检测 | 检出 | **通过** | demo.fingerprint.com |
| **BrowserScan** 机器人检测 | 检出 | **正常（4/4）** | browserscan.net |
| **bot.incolumitas.com** | 13 项失败 | **1 项失败** | 仅 WEBDRIVER 规范 |
| **deviceandbrowserinfo.com** | 6 个 true 标志 | **0 个 true 标志** | `isBot: false` |
| `navigator.webdriver` | `true` | **`false`** | 源码级补丁 |
| `navigator.plugins.length` | 0 | **5** | 真实插件列表 |
| `window.chrome` | `undefined` | **`object`** | 与真实 Chrome 一致 |
| UA 字符串 | `HeadlessChrome` | **`Chrome/146.0.0.0`** | 无无头泄漏 |
| CDP 检测 | 检出 | **未检出** | `isAutomatedWithCDP: false` |
| TLS 指纹 | 不匹配 | **与 Chrome 一致** | JA3/JA4/Akamai 匹配 |

### 5.2 与同类工具对比

| 特性 | Playwright | playwright-stealth | undetected-chromedriver | Camoufox | **CloakBrowser** |
|------|------------|---------------------|-------------------------|----------|------------------|
| reCAPTCHA v3 评分 | 0.1 | 0.3-0.5 | 0.3-0.7 | 0.7-0.9 | **0.9** |
| Cloudflare Turnstile | 失败 | 偶尔 | 偶尔 | 通过 | **通过** |
| 补丁层级 | 无 | JS 注入 | 配置补丁 | C++（Firefox） | **C++（Chromium）** |
| 抗 Chrome 升级 | N/A | 经常失效 | 经常失效 | 是 | **是** |
| 维护状态 | 活跃 | 停滞 | 停滞 | 不稳定 | **活跃** |
| 浏览器引擎 | Chromium | Chromium | Chrome | Firefox | **Chromium** |
| Playwright API | 原生 | 原生 | 否（Selenium） | 否 | **原生** |

### 5.3 自行验证

```python
from cloakbrowser import launch

browser = launch(humanize=True)
page = browser.new_page()

# 1. 检测 navigator.webdriver
print("webdriver:", page.evaluate("navigator.webdriver"))  # False

# 2. 检测 plugins
print("plugins length:", page.evaluate("navigator.plugins.length"))  # 5

# 3. 检测 window.chrome
print("window.chrome:", page.evaluate("typeof window.chrome"))  # object

# 4. 检测 UA
print("UA:", page.evaluate("navigator.userAgent"))  # 不含 HeadlessChrome

# 5. 跑检测站点
page.goto("https://bot.sannysoft.com/")
page.screenshot(path="stealth_test.png")
browser.close()
```

---

## 六、humanize 拟人化行为

行为检测是反爬的最后一道防线。`humanize=True` 让所有鼠标、键盘、滚动行为模拟真实用户。

### 6.1 启用拟人化

```python
from cloakbrowser import launch

browser = launch(humanize=True)
page = browser.new_page()
page.goto("https://protected-site.com")

# 所有交互自动拟人化
page.click("#button")          # 贝塞尔曲线鼠标移动
page.fill("#input", "text")    # 逐字符输入，带随机延迟
page.mouse.wheel(0, 500)       # 真实滚动模式
```

### 6.2 拟人化细节

```
鼠标移动：
  - 贝塞尔曲线轨迹（非直线）
  - 随机抖动和过冲
  - 接近目标时减速

键盘输入：
  - 逐字符输入（非一次性填充）
  - 每个字符间随机延迟（50-200ms）
  - 偶尔的打字错误和修正

滚动：
  - 加速/减速曲线
  - 偶尔的反向滚动
  - 滚动停顿
```

### 6.3 预设模式

```python
# 默认模式
browser = launch(humanize=True, human_preset="default")

# 谨慎模式（更慢、更刻意）
browser = launch(humanize=True, human_preset="careful")
```

### 6.4 单次调用覆盖

```python
# 在特定调用上覆盖 humanize 设置
page.click("#button", human_config={"preset": "careful"})
```

---

## 七、代理与网络层隐身

CloakBrowser 处理浏览器层隐身，但**不处理 IP 层**。完整隐身需要配合代理。

### 7.1 代理配置

```python
from cloakbrowser import launch

# HTTP 代理
browser = launch(proxy="http://user:pass@residential-proxy:port")

# SOCKS5 代理（原生支持，QUIC/HTTP3 通过 UDP ASSOCIATE 隧道）
browser = launch(proxy="socks5://user:pass@host:port")

# 代理 + 自动时区/语言检测
browser = launch(
    proxy="http://user:pass@residential-proxy:port",
    geoip=True,          # 时区/语言匹配代理 IP
    headless=False,      # 部分站点检测无头
    humanize=True,       # 拟人化行为
)
```

### 7.2 WebRTC IP 泄漏防护

WebRTC 可能泄漏真实 IP，即使使用了代理：

```python
# 自动从代理出口 IP 生成 ICE 候选者
browser = launch(
    proxy="http://proxy:8080",
    args=["--fingerprint-webrtc-ip=auto"]  # 通过代理解析出口 IP
)

# 或显式指定 WebRTC IP（无网络调用）
browser = launch(
    proxy="http://proxy:8080",
    args=["--fingerprint-webrtc-ip=1.2.3.4"]
)
```

### 7.3 反爬完整栈

```
反爬检测的七层战场与对应方案：

┌────────────────────────────────────────────────────┐
│ 1. 浏览器指纹（Canvas/WebGL/Audio）  → CloakBrowser │
│ 2. TLS 指纹（JA3/JA4）                → CloakBrowser │
│ 3. 自动化标记（CDP/webdriver）        → CloakBrowser │
│ 4. 行为模式（鼠标/键盘）              → humanize=True │
├────────────────────────────────────────────────────┤
│ 5. IP 信誉（ASN 分类）                → 住宅/移动代理 │
│ 6. TCP/IP 指纹（p0f）                 → 移动代理      │
│ 7. DNS 一致性                         → 移动代理      │
└────────────────────────────────────────────────────┘

CloakBrowser 覆盖 1-4 层，代理覆盖 5-7 层。
两者结合才是完整的反检测方案。
```

---

## 八、实战：绕过 Cloudflare 保护站点

### 8.1 基础绕过

```python
from cloakbrowser import launch

browser = launch(
    headless=False,      # 部分站点检测无头
    humanize=True,       # 拟人化行为
    proxy="http://user:pass@residential-proxy:port",  # 住宅代理
    geoip=True,          # 时区/语言匹配代理 IP
)

page = browser.new_page()
page.goto("https://protected-site.com", timeout=60000)

# 等待 Cloudflare Turnstile 自动通过
page.wait_for_selector("#content", timeout=30000)

# 提取数据
title = page.title()
content = page.content()

print(f"标题: {title}")
browser.close()
```

### 8.2 处理 Turnstile 挑战

```python
from cloakbrowser import launch
import time

browser = launch(humanize=True, headless=False)
page = browser.new_page()
page.goto("https://site-with-turnstile.com")

# 等待 Turnstile iframe 出现
try:
    turnstile = page.wait_for_selector(
        'iframe[src*="challenges.cloudflare.com"]',
        timeout=10000
    )
    
    # 点击 Turnstile checkbox（humanize 会自动拟人化移动）
    if turnstile:
        turnstile.click()
        # 等待挑战通过
        page.wait_for_selector(".success-indicator", timeout=15000)
except:
    pass  # 非交互式挑战会自动通过

# 继续操作
page.screenshot(path="after_cf.png")
browser.close()
```

### 8.3 持久化会话（复用 cf_clearance Cookie）

```python
from cloakbrowser import launch_persistent_context

# 首次：通过 CF 验证，保存会话
context = launch_persistent_context(
    user_data_dir="/path/to/profile",
    humanize=True,
    proxy="http://residential-proxy:port",
)
page = context.new_page()
page.goto("https://protected-site.com")
# 等待 CF 通过...
context.close()

# 后续：复用会话，无需再次验证
context = launch_persistent_context(
    user_data_dir="/path/to/profile",
    proxy="http://residential-proxy:port",
)
page = context.new_page()
page.goto("https://protected-site.com/data")  # 直接访问
```

---

## 九、cf-killer：基于 CloakBrowser 的 CF 自动解盾工具

[cf-killer](https://github.com/qihe-no-study/cf-killer) 是基于 CloakBrowser 构建的 **Cloudflare 5 秒盾自动求解 + 页面批量抓取** 工具，封装了完整的 CF 解盾流程。

### 9.1 安装

```bash
pip install cf-killer

# 首次使用需下载 CloakBrowser 的 Chromium 二进制（约 200MB，仅一次）
python -c "import cloakbrowser; cloakbrowser.ensure_binary()"
```

依赖链：

```
cf-killer
  ├── cloakbrowser >= 0.3.0    # C++ 源码级反检测 Chromium
  │     ├── playwright >= 1.40  # 浏览器自动化
  │     ├── httpx >= 0.24       # HTTP 客户端
  │     └── greenlet >= 3.1     # 协程支持
  └── playwright >= 1.40
```

### 9.2 核心功能

| 功能 | 类/函数 | 说明 |
|------|---------|------|
| CF 自动解盾 | `CFSolver` | 检测并求解 Cloudflare Turnstile |
| 页面批量抓取 | `CFPageFetcher` | 持久化上下文，复用指纹和 cookie |
| 文件下载 | `download_file()` | 页内 fetch() 下载，复用 TLS 指纹 |
| 多实例并行 | `fetch_all()` | 多浏览器实例 + 独立代理并行 |

### 9.3 CF 解盾策略

支持四种 Turnstile 挑战类型：

| 类型 | 策略 |
|------|------|
| `non-interactive` | 纯轮询等待 CF 自动放行 |
| `managed` | 等待 iframe → 点击 checkbox → 轮询消失 |
| `interactive` | 同上，带更复杂的点击路径 |
| `embedded` | 嵌入式 Turnstile 求解 |

点击采用**四路径递进策略**：

```
1. iframe 内精确选择器点击
       ↓ 失败
2. iframe 坐标点击
       ↓ 失败
3. 主页面容器坐标点击
       ↓ 失败
4. Tab + Space 键盘兜底
```

### 9.4 批量抓取示例

```python
from cf_killer import fetch_all

URLS = [
    "https://gut.bmj.com/content/75/6/1085",
    "https://gut.bmj.com/content/75/6/1087",
    "https://www.sciencedirect.com/science/article/pii/S0039606025002491",
    # ... 更多 URL
]

results = fetch_all(
    URLS,
    instances=2,                  # 并行浏览器实例数
    concurrency=3,                # 每实例并发 tab 数
    max_pages_per_context=10,     # 每 10 页回收上下文
    headless=True,
    solve_cf=True,                # 自动解 CF
    proxy=None,                   # 或 "http://proxy:port"
    return_cookies=False,
    verbose=False,
)

ok = sum(1 for r in results if r["success"])
print(f"结果: {ok}/{len(results)} 成功")
for r in results:
    status = "✓" if r["success"] else "✗"
    print(f"  {status}  {(r['title'] or 'FAILED')[:60]}")
```

### 9.5 PDF 文件下载

过 CF 后，通过页内 `fetch()` 下载文件，复用浏览器的 cookie 和 TLS 指纹：

```python
import asyncio
from cf_killer import CFPageFetcher

PDF_URL = "https://protected-site.com/document.pdf"
OUTPUT = "./document.pdf"

async def main():
    async with CFPageFetcher(
        headless=True,
        solve_cf=True,
    ) as fetcher:
        ok = await fetcher.download_file(PDF_URL, OUTPUT)
        if ok:
            import os
            size_kb = os.path.getsize(OUTPUT) / 1024
            print(f"✅ 下载成功! ({size_kb:.0f} KB)")
        else:
            print("❌ 下载失败")

asyncio.run(main())
```

### 9.6 主要 API 参数

**`CFPageFetcher`**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `headless` | bool | True | 无头模式 |
| `humanize` | bool | False | 人类化鼠标轨迹/键盘时序 |
| `solve_cf` | bool | True | 自动求解 CF 挑战 |
| `cf_max_retries` | int | 5 | CF 求解最大重试次数 |
| `timeout` | int | 90000 | 页面导航超时 (ms) |
| `proxy` | str | None | 代理 URL |
| `max_pages_per_context` | int | 20 | 每 N 页回收浏览器上下文 |
| `return_cookies` | bool | False | 结果中是否包含 cookies |

**`fetch_all`**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `urls` | list | - | URL 列表 |
| `instances` | int | 1 | 并行浏览器实例数 |
| `concurrency` | int | 3 | 每实例并发 tab 数 |
| `max_pages_per_context` | int | 20 | 每 N 页自动回收 |
| `proxy` | str/list/callable | None | 单代理/代理列表/代理工厂函数 |

### 9.7 内存管理与并发设计

cf-killer 的工程亮点：

```
1. 自动 context 回收
   - 处理 N 页后重建浏览器上下文，防止内存泄漏
   - 避免长期运行导致的 OOM

2. 延迟回收机制
   - 并发场景下等活跃页面全部完成后再回收
   - 避免竞态条件导致的崩溃

3. 多实例并行
   - URL 均匀分配到多个浏览器实例
   - 每个实例独立 event loop + 独立代理
   - ThreadPoolExecutor 并行执行，最大化吞吐量

4. 代理三种模式
   - 单代理：所有实例共享一个代理
   - 代理列表：按实例分配不同代理
   - callable：代理工厂函数，动态生成
```

---

## 十、高级用法

### 10.1 浏览器配置管理器

CloakBrowser 提供自托管的浏览器配置管理器（Multilogin/GoLogin/AdsPower 的开源替代）：

```bash
# 启动配置管理器
docker run -p 8080:8080 -v cloakprofiles:/data cloakhq/cloakbrowser-manager
```

打开 http://localhost:8080，创建配置文件（唯一指纹 + 代理 + 持久会话），点击 Launch 通过 noVNC 在浏览器中交互。

### 10.2 加载 Chrome 扩展

```python
browser = launch(extension_paths=["/path/to/extension"])
```

### 10.3 与 AI Agent 框架集成

CloakBrowser 可作为以下框架的隐身底层：

- **browser-use**：AI 浏览器代理
- **Crawl4AI**：AI 爬虫
- **Scrapling**：智能爬虫
- **Stagehand**：AI 自动化
- **LangChain**：LLM 应用框架
- **Selenium**：传统自动化

### 10.4 二进制管理 CLI

```bash
# 检查更新
cloakbrowser update

# 指定版本
cloakbrowser use 0.3.31

# 清理缓存
cloakbrowser clean
```

---

## 十一、最佳实践

### 11.1 反爬完整方案

```python
from cloakbrowser import launch

# 完整反检测配置
browser = launch(
    headless=False,                                    # 部分站点检测无头
    humanize=True,                                     # 拟人化行为
    proxy="http://user:pass@residential-proxy:port",   # 住宅/移动代理
    geoip=True,                                        # 时区/语言匹配代理 IP
    args=["--fingerprint-webrtc-ip=auto"],             # WebRTC IP 防泄漏
)
```

### 11.2 场景化配置

| 场景 | 推荐配置 |
|------|----------|
| 简单站点（无 CF） | `launch()` 默认配置即可 |
| Cloudflare 保护 | `launch(humanize=True, headless=False, proxy=住宅代理)` |
| reCAPTCHA v3 | `launch(humanize=True)` + 住宅代理 |
| 高强度反爬（Kasada） | `launch(humanize=True, headless=False, proxy=移动代理, geoip=True)` |
| 大规模抓取 | cf-killer `fetch_all()` + 代理列表 |

### 11.3 浏览器实例生命周期管理

**原则：一个浏览器实例对应一个"用户身份"，不要在同一个实例上频繁切换身份。**

```python
# ✅ 推荐：一个实例完成一个完整任务
from cloakbrowser import launch

browser = launch(humanize=True, proxy="http://proxy1:port")
page = browser.new_page()
page.goto("https://site.com/login")
page.fill("#username", "user1")
page.fill("#password", "pass1")
page.click("#submit")
# ... 完成所有操作后关闭
browser.close()

# ❌ 不推荐：同一实例反复登录不同账号
browser = launch()
for user, pwd in accounts:
    page = browser.new_page()
    page.goto("https://site.com/login")
    page.fill("#username", user)
    page.fill("#password", pwd)
    page.click("#submit")
    page.close()
    # 问题：Cookie、localStorage 残留，账号间交叉污染
```

**多账号场景的正确做法**：

```python
from cloakbrowser import launch

# 方案 1：每个账号独立浏览器实例
for user, pwd, proxy in accounts:
    browser = launch(humanize=True, proxy=proxy)
    page = browser.new_page()
    # ... 操作
    browser.close()

# 方案 2：使用持久化上下文，每个账号独立 profile
from cloakbrowser import launch_persistent_context

for user, pwd in accounts:
    context = launch_persistent_context(
        user_data_dir=f"/profiles/{user}",
        humanize=True,
        proxy="http://proxy:port",
    )
    page = context.new_page()
    # ... 操作
    context.close()
```

### 11.4 代理与指纹的绑定策略

**核心原则：一个代理 IP + 一个浏览器指纹 = 一个"虚拟用户"，长期保持稳定。**

```python
# ✅ 推荐：代理与指纹绑定
PROXY_FP_MAP = {
    "http://proxy1:port": {"timezone": "America/New_York", "locale": "en-US"},
    "http://proxy2:port": {"timezone": "Europe/London", "locale": "en-GB"},
    "http://proxy3:port": {"timezone": "Asia/Tokyo", "locale": "ja-JP"},
}

def create_session(proxy_url):
    config = PROXY_FP_MAP[proxy_url]
    browser = launch(
        humanize=True,
        proxy=proxy_url,
        timezone=config["timezone"],
        locale=config["locale"],
        args=["--fingerprint-webrtc-ip=auto"],
    )
    return browser

# ❌ 不推荐：同一代理 IP 下频繁切换指纹
browser = launch(humanize=True, proxy="http://proxy1:port")
# ... 几分钟后
browser2 = launch(humanize=True, proxy="http://proxy1:port")  # 同 IP 不同指纹
# 问题：同一 IP 出现两个不同"浏览器"，比固定指纹更可疑
```

**代理选择优先级**：

```
移动代理（4G/5G） > 住宅代理 > 静态住宅代理 > 数据中心代理

原因：
- 移动代理：CGNAT 下成千上万真实用户共享同一 IP，反爬系统无法区分
- 住宅代理：真实 ISP 分配，但 IP 可能已被滥用
- 数据中心代理：ASN 直接标记为数据中心，最容易被拦截
```

### 11.5 请求频率与节奏控制

**原则：模拟真实用户的浏览节奏，而非机器人的匀速请求。**

```python
import random
import time
from cloakbrowser import launch

browser = launch(humanize=True)
page = browser.new_page()

# ✅ 推荐：随机化间隔
urls = [...]
for url in urls:
    page.goto(url)
    
    # 模拟阅读时间（与页面长度相关）
    content_length = len(page.content())
    read_time = max(2, content_length / 5000)  # 粗略估算阅读秒数
    time.sleep(read_time + random.uniform(1, 5))
    
    # 偶尔滚动页面
    if random.random() > 0.3:
        page.mouse.wheel(0, random.randint(200, 800))
        time.sleep(random.uniform(0.5, 2))

# ❌ 不推荐：匀速请求
for url in urls:
    page.goto(url)
    time.sleep(1)  # 固定 1 秒间隔，明显是机器人
```

**使用 humanize 自动处理节奏**：

```python
# humanize=True 已经内置了：
# - 鼠标移动的贝塞尔曲线（非瞬移）
# - 键盘输入的逐字符延迟
# - 滚动的加速/减速
# 但页面间的等待时间仍需手动控制
```

### 11.6 会话预热策略

**原则：不要直接访问目标页面，先模拟正常浏览路径。**

```python
from cloakbrowser import launch
import time

browser = launch(humanize=True, headless=False, proxy="http://residential-proxy:port")
page = browser.new_page()

# ✅ 推荐：模拟真实用户的浏览路径
# 1. 先访问首页
page.goto("https://target-site.com/")
time.sleep(random.uniform(2, 5))

# 2. 模拟滚动浏览
page.mouse.wheel(0, 500)
time.sleep(random.uniform(1, 3))

# 3. 点击导航（模拟从首页进入目标页面）
page.click("a.category-link")
time.sleep(random.uniform(2, 4))

# 4. 最终到达目标页面
page.click("a.target-item")

# ❌ 不推荐：直接访问深层页面
page.goto("https://target-site.com/deep/path/page?id=12345")
# 问题：真实用户不会直接输入深层 URL，反爬系统会检测 referer 链
```

### 11.7 Cookie 与会话复用

**原则：通过 CF 验证后，复用 Cookie 避免重复验证。**

```python
from cloakbrowser import launch_context, launch_persistent_context
import json

# 方案 1：storage_state 导出/导入
def first_run():
    context = launch_context(humanize=True, proxy="http://proxy:port")
    page = context.new_page()
    page.goto("https://protected-site.com")
    # 等待 CF 通过...
    page.wait_for_selector("#content", timeout=30000)
    
    # 保存会话状态
    context.storage_state(path="session_state.json")
    context.close()

def subsequent_runs():
    # 加载已保存的会话状态
    context = launch_context(
        storage_state="session_state.json",
        proxy="http://proxy:port",
    )
    page = context.new_page()
    page.goto("https://protected-site.com/data")  # 直接访问，无需再次验证
    # ...
    context.close()

# 方案 2：持久化上下文（更简单）
def persistent_approach():
    context = launch_persistent_context(
        user_data_dir="/profiles/session1",
        humanize=True,
        proxy="http://proxy:port",
    )
    page = context.new_page()
    page.goto("https://protected-site.com")
    # ... 首次通过 CF 验证
    context.close()
    
    # 下次运行，Cookie 自动保留
    context = launch_persistent_context(
        user_data_dir="/profiles/session1",
        proxy="http://proxy:port",
    )
    page = context.new_page()
    page.goto("https://protected-site.com/data")  # 直接访问
```

### 11.8 大规模抓取的架构设计

```python
"""
大规模抓取架构：
  - 分层降级：curl_cffi → CloakBrowser → cf-killer
  - 代理池 + 指纹绑定
  - 上下文回收防内存泄漏
"""

from curl_cffi import requests as curl_requests
from cloakbrowser import launch

def smart_fetch(url, proxy=None):
    """分层降级抓取策略"""
    
    # 第 1 层：curl_cffi 快速尝试（成本最低）
    try:
        r = curl_requests.get(url, impersonate="chrome", proxies={"https": proxy} if proxy else None, timeout=15)
        if r.status_code == 200 and not is_blocked(r.text):
            return {"source": "curl_cffi", "content": r.text}
    except Exception:
        pass
    
    # 第 2 层：CloakBrowser（成本中等，能过 CF）
    try:
        browser = launch(humanize=True, headless=True, proxy=proxy)
        page = browser.new_page()
        page.goto(url, timeout=30000)
        page.wait_for_timeout(3000)  # 等 CF 通过
        
        content = page.content()
        browser.close()
        
        if not is_blocked(content):
            return {"source": "cloakbrowser", "content": content}
    except Exception:
        pass
    
    # 第 3 层：cf-killer（成本最高，自动解盾）
    try:
        from cf_killer import fetch_url
        result = fetch_url(url, headless=True, solve_cf=True, proxy=proxy)
        if result and result.get("success"):
            return {"source": "cf_killer", "content": result["html"]}
    except Exception:
        pass
    
    return None

def is_blocked(html):
    """检测页面是否被反爬拦截"""
    block_signals = [
        "challenge-platform",
        "cf-browser-verification",
        "Just a moment",
        "Robot or human",
        "Access denied",
        "cf-challenge",
    ]
    html_lower = html.lower()
    return any(signal.lower() in html_lower for signal in block_signals)
```

### 11.9 资源管理最佳实践

```python
from cloakbrowser import launch
import psutil
import os

# 1. 始终使用上下文管理器确保资源释放
def safe_browse():
    browser = launch(humanize=True)
    try:
        page = browser.new_page()
        page.goto("https://example.com")
        # ... 操作
    finally:
        browser.close()  # 确保关闭

# 2. 监控内存，及时回收
def monitored_browse(urls, max_pages=20):
    browser = launch(humanize=True)
    pages_opened = 0
    
    for url in urls:
        page = browser.new_page()
        page.goto(url)
        # ... 提取数据
        page.close()
        pages_opened += 1
        
        # 定期回收
        if pages_opened >= max_pages:
            browser.close()
            browser = launch(humanize=True)
            pages_opened = 0
        
        # 内存检查
        mem = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        if mem > 2000:  # 超过 2GB 强制回收
            browser.close()
            browser = launch(humanize=True)
            pages_opened = 0

# 3. 并发控制（避免同时打开过多页面）
def concurrent_browse(urls, max_tabs=3):
    browser = launch(humanize=True)
    
    for i in range(0, len(urls), max_tabs):
        batch = urls[i:i + max_tabs]
        pages = []
        
        for url in batch:
            page = browser.new_page()
            page.goto(url)
            pages.append(page)
        
        # 等待所有页面加载完成
        for page in pages:
            page.wait_for_load_state("networkidle")
            # ... 提取数据
            page.close()
    
    browser.close()
```

### 11.10 常见问题排查

**问题：reCAPTCHA v3 评分仍低**

```python
# 解决：启用 humanize + 住宅代理 + 有头模式
browser = launch(
    humanize=True,
    headless=False,  # 关键：部分站点检测无头
    proxy="http://residential-proxy:port",
)
# 先浏览几个页面建立"真实用户"行为历史，再访问目标
```

**问题：Cloudflare Turnstile 不自动通过**

```python
# 解决：有头模式 + humanize + 等待
browser = launch(humanize=True, headless=False)
page = browser.new_page()
page.goto(url)
# 等待更长时间，让 humanize 模拟真实交互
page.wait_for_timeout(5000)
```

**问题：FingerprintJS 仍检测到**

```python
# 解决：确保使用最新版本 + 持久化上下文
browser = launch_persistent_context(
    user_data_dir="/path/to/profile",
    humanize=True,
)
```

**问题：代理环境下 WebRTC 泄漏真实 IP**

```python
# 解决：启用 WebRTC IP 伪装
browser = launch(
    proxy="http://proxy:port",
    args=["--fingerprint-webrtc-ip=auto"],
    # 或 geoip=True 自动注入
)
```

**问题：长时间运行内存持续增长**

```python
# 解决：定期回收浏览器上下文
# 方案 1：手动回收（每 N 页重建）
# 方案 2：使用 cf-killer 的 max_pages_per_context 自动回收
from cf_killer import CFPageFetcher

async with CFPageFetcher(max_pages_per_context=15) as fetcher:
    # 每 15 页自动回收上下文
    for url in urls:
        result = await fetcher.fetch(url)
```

### 11.11 最佳实践速查表

| 维度 | 最佳实践 | 反模式 |
|------|----------|--------|
| 实例管理 | 一个实例 = 一个用户身份 | 同一实例切换账号 |
| 代理绑定 | IP + 指纹 + 时区长期绑定 | 同 IP 频繁换指纹 |
| 请求节奏 | 随机间隔 + 阅读时间 | 匀速请求 |
| 浏览路径 | 首页 → 列表 → 详情 | 直接访问深层 URL |
| 会话复用 | storage_state / 持久化上下文 | 每次重新过 CF |
| 降级策略 | curl_cffi → CloakBrowser → cf-killer | 所有请求都用 CloakBrowser |
| 资源管理 | 定期回收上下文 + 内存监控 | 无限创建页面不关闭 |
| 并发控制 | 限制同时打开 tab 数 | 一次打开几十个 tab |
| 代理选择 | 移动代理 > 住宅 > 数据中心 | 数据中心代理 |
| 模式选择 | 有头模式（强反爬站点） | 无头模式（易被检测） |

---

## 十二、与 curl_cffi 的对比与互补

| 维度 | curl_cffi | CloakBrowser |
|------|-----------|--------------|
| **定位** | HTTP 客户端 | 完整浏览器 |
| **反检测层级** | TLS 指纹（网络层） | 浏览器指纹（应用层）+ TLS |
| **能执行 JS** | 否 | 是 |
| **能过 Turnstile** | 部分（非交互） | 是（含交互式） |
| **资源占用** | 极低（~10MB） | 高（~200MB 二进制 + 运行时内存） |
| **速度** | 极快（异步 HTTP） | 慢（浏览器启动 + 页面渲染） |
| **适用场景** | 静态页面、API | 动态页面、强反爬站点 |

**组合策略**：

```python
# 1. 先用 curl_cffi 快速尝试（成本低）
from curl_cffi import requests
r = requests.get(url, impersonate="chrome")
if is_blocked(r.text):
    # 2. 被拦截则用 CloakBrowser（成本高但能过）
    from cloakbrowser import launch
    browser = launch(humanize=True)
    page = browser.new_page()
    page.goto(url)
    # ...
```

---

## 十三、合规与注意事项

1. **CloakBrowser 不解 CAPTCHA**：它通过让浏览器"看起来真实"来**防止** CAPTCHA 出现，而非破解已出现的 CAPTCHA。
2. **不内置代理**：需自备代理，推荐住宅或移动代理，数据中心 IP 仍会被拦截。
3. **遵守 ToS**：应在合规前提下使用，尊重 robots.txt 和目标站点服务条款。
4. **资源消耗**：浏览器实例内存占用高，大规模抓取需配合 cf-killer 的上下文回收机制。
5. **版本更新**：CloakBrowser 会自动检查更新，保持最新 stealth build。也可通过 `cloakbrowser update` 手动更新。
6. **平台支持**：Linux x64/ARM64（v146）、macOS Intel/Apple Silicon（v145）、Windows x64（v146）。

---

## 参考资源

- CloakBrowser 官网：https://cloakbrowser.dev/
- CloakBrowser GitHub：https://github.com/CloakHQ/CloakBrowser
- CloakBrowser PyPI：https://pypi.org/project/cloakbrowser/
- CloakBrowser Manager：https://github.com/CloakHQ/CloakBrowser-Manager
- cf-killer GitHub：https://github.com/qihe-no-study/cf-killer
- cf-killer PyPI：https://pypi.org/project/cf-Killer/
- Playwright 文档：https://playwright.dev/
- Cloudflare Turnstile 文档：https://developers.cloudflare.com/turnstile/

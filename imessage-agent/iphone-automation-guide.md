# iPhone 自动化操作完全手册：从快捷指令到 AI 驱动

> 让手机替你干活，是人类永恒的追求。这篇文章将从零开始，带你系统了解 iPhone 自动化操作的完整知识体系，涵盖从苹果原生快捷指令到 AI 驱动的智能 Agent 方案，帮你找到最适合自己的自动化路径。

## 一、为什么需要自动化操作 iPhone？

日常使用 iPhone 的过程中，有大量重复性操作：每天早上打开同一个 App 查看信息、定时发送消息、批量处理照片、在多个 App 之间搬运数据……这些操作如果手动完成，既耗时又无聊。

自动化操作的核心价值：

- **省时**：把重复操作交给程序，一次配置永久生效
- **精准**：程序执行不会出错，比手动操作更可靠
- **可扩展**：一个脚本可以同时控制多台设备
- **智能化**：结合 AI，用自然语言就能控制手机

## 二、iPhone 自动化操作知识体系总览

iPhone 自动化操作可以从两个维度来理解：

**按控制层级分：**

| 层级 | 方案 | 特点 |
|------|------|------|
| 系统级 | 快捷指令 (Shortcuts) | 无需编程，Apple 官方支持 |
| 应用级 | URL Scheme / Deep Link | 通过 URL 唤起 App 并执行操作 |
| UI 级 | WebDriverAgent / Appium | 模拟用户点击、滑动等操作 |
| AI 级 | Open-AutoGLM 等 | 自然语言驱动，AI 理解屏幕并操作 |

**按技术门槛分：**

| 门槛 | 方案 | 适合人群 |
|------|------|----------|
| 零代码 | 快捷指令 | 所有用户 |
| 低代码 | Python + facebook-wda | 有基础编程能力的用户 |
| 中等代码 | Appium + Python | 测试工程师 |
| 高代码 | XCTest 原生开发 | iOS 开发者 |

下面我们逐一深入。

---

## 三、方案一：iOS 快捷指令——零代码自动化

快捷指令是 Apple 内置的自动化工具，无需安装任何额外软件，是入门自动化的最佳起点。

### 3.1 基本概念

- **快捷指令**：手动触发的一组操作序列
- **自动化**：由特定事件（时间、位置、设备状态）自动触发的快捷指令

### 3.2 创建个人自动化

1. 打开「快捷指令」App → 切换到「自动化」标签
2. 点击右上角「+」→ 选择「创建个人自动化」
3. 选择触发条件：
   - **时间**：特定时间/日出日落
   - **位置**：到达/离开某地
   - **设备状态**：低电量、连接充电器、连接蓝牙设备等
   - **App**：打开/关闭某个 App
4. 添加操作动作
5. 关闭「运行前问询」即可全自动执行

### 3.3 实用案例

**案例 1：每日晨报自动播报**

触发条件 → 时间（每天 7:30）
操作序列：
1. 获取天气信息
2. 获取日历今日日程
3. 拼接文本
4. 通过 Siri 朗读

**案例 2：到家自动开灯**

触发条件 → 到达家（位置）
操作序列：
1. 设置「客厅灯」为开启
2. 设置亮度为 60%

**案例 3：低电量自动省电**

触发条件 → 电池电量低于 20%
操作序列：
1. 开启低电量模式
2. 降低屏幕亮度
3. 关闭蓝牙

### 3.4 进阶技巧

- **变量与字典**：使用「脚本」类动作中的变量存储数据，用字典存储结构化数据
- **条件判断**：添加「如果-否则」逻辑，根据条件执行不同操作
- **API 调用**：使用「获取 URL 内容」动作调用外部 API，获取实时数据
- **Siri 语音触发**：为快捷指令设置语音唤醒词

### 3.5 局限性

- 只能操作 Apple 开放了快捷指令接口的 App
- 无法模拟点击屏幕上的任意位置
- 复杂逻辑表达能力有限
- 无法跨设备批量控制

---

## 四、方案二：WebDriverAgent——编程控制 iPhone 的核心

当你需要精确控制 iPhone 屏幕上的每一个元素（点击按钮、输入文字、滑动页面），就需要 WebDriverAgent（WDA）。它是几乎所有编程方案和 AI 方案的基础。

### 4.1 什么是 WebDriverAgent？

WebDriverAgent 是 Facebook（现 Meta）开源的 iOS 自动化测试框架，后来由 Appium 社区维护。它实现了 WebDriver 协议，允许你通过 HTTP 请求远程控制 iOS 设备。

**核心原理：**

```
你的代码 → HTTP 请求 → WebDriverAgent(运行在 iPhone 上) → XCTest 框架 → 模拟用户操作
```

WDA 运行在 iPhone 上作为一个 HTTP 服务器，接收来自电脑的指令，然后通过 Apple 的 XCTest 框架模拟用户的触摸、滑动、输入等操作。

### 4.2 环境准备

**硬件要求：**

- Mac 电脑（macOS 系统）
- iPhone（USB 数据线连接，注意不是仅充电线）
- Apple ID（免费开发者账号即可）

**软件要求：**

- Xcode（从 App Store 安装最新版）
- Homebrew
- libimobiledevice
- Python 3.10+

### 4.3 安装步骤

**第一步：安装基础工具**

```bash
# 安装 Homebrew（如果还没有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 libimobiledevice（包含 iproxy 端口转发工具）
brew install libimobiledevice

# 安装 usbmuxd（如果 iproxy 不可用）
brew install usbmuxd
```

**第二步：克隆并配置 WebDriverAgent**

```bash
# 克隆 WebDriverAgent 仓库
git clone https://github.com/appium/WebDriverAgent.git
cd WebDriverAgent
```

**第三步：Xcode 签名配置**

1. 用 Xcode 打开 `WebDriverAgent.xcodeproj`
2. 在 TARGETS 列表中选择 `WebDriverAgentLib`
3. 进入 `Signing & Capabilities`：
   - 勾选 `Automatically manage signing`
   - Team 选择你的 Apple ID（如果没有，点击 Add Account 添加）
   - 将 Bundle Identifier 改为唯一标识，如 `com.yourname.WebDriverAgentLib`
4. 对 `WebDriverAgentRunner` 重复上述操作，Bundle ID 改为 `com.yourname.WebDriverAgentRunner`
5. 对 `IntegrationApp` 也同样操作，Bundle ID 改为 `com.yourname.IntegrationApp`

> ⚠️ 三个 Target 的签名必须使用同一个 Apple ID，Bundle ID 不能重复。

**第四步：编译部署到 iPhone**

方式一：通过 Xcode GUI

1. 将 iPhone 通过 USB 连接到 Mac
2. 在 Xcode 顶部选择你的 iPhone 作为运行目标
3. 长按运行按钮（▶️），选择 `Test`
4. 等待编译完成并部署到手机

方式二：通过命令行

```bash
# 查看已连接设备
xcrun xctrace list devices

# 编译并运行（替换 UDID 和团队 ID）
xcodebuild -project WebDriverAgent.xcodeproj \
  -scheme WebDriverAgentRunner \
  -destination 'id=<你的设备UDID>' \
  -allowProvisioningUpdates \
  build test
```

**第五步：信任开发者证书**

首次部署后，iPhone 上需要手动信任：

1. 打开 iPhone「设置」→「通用」→「VPN与设备管理」（或「描述文件与设备管理」）
2. 找到你的 Apple ID 对应的开发者证书
3. 点击「信任」

**第六步：端口转发**

```bash
# 将 iPhone 的 8100 端口映射到 Mac 的 8100 端口
iproxy 8100 8100
```

**第七步：验证连接**

```bash
# 检查 WDA 是否正常运行
curl http://localhost:8100/status
```

如果返回 JSON 格式的状态信息，说明连接成功。

### 4.4 使用 facebook-wda 编写自动化脚本

facebook-wda 是 WebDriverAgent 的 Python 客户端，API 简洁易用。

**安装：**

```bash
pip install -U facebook-wda
```

**基本操作示例：**

```python
import wda

c = wda.Client("http://localhost:8100")

# 获取屏幕尺寸
print(c.window_size())

# 截图
c.screenshot("screen.png")

# 点击坐标
c.click(200, 300)

# 滑动（从下往上滑）
c.swipe(200, 800, 200, 200, duration=0.5)

# 输入文字（需要先点击输入框）
c.click(200, 400)
c.set_text("Hello World")

# 启动 App
c.app_launch("com.apple.MobileSMS")

# 返回主屏
c.home()

# 获取页面元素树
print(c.source())
```

**实战案例：自动发微信消息**

```python
import wda
import time

c = wda.Client("http://localhost:8100")

def send_wechat_message(contact_name, message):
    c.app_launch("com.tencent.xin")
    time.sleep(2)

    c.click(200, 800)
    time.sleep(1)

    c.set_text(contact_name)
    time.sleep(1)

    c.click(200, 400)
    time.sleep(1)

    c.click(200, 600)
    time.sleep(1)

    c.set_text(message)
    time.sleep(0.5)

    c.click(350, 800)

send_wechat_message("文件传输助手", "这是一条自动发送的消息")
```

### 4.5 常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 签名失败 | Bundle ID 冲突 | 修改为唯一标识符 |
| 设备连接不上 | 数据线仅充电 | 更换支持数据传输的线 |
| iproxy 端口映射失败 | usbmuxd 未安装 | `brew install usbmuxd` |
| WDA 启动后闪退 | 证书未信任 | 设置→通用→设备管理→信任 |
| curl 连接超时 | 防火墙/网络问题 | 检查网络，尝试 WiFi 模式 |

---

## 五、方案三：Appium——企业级跨平台自动化

Appium 是一个成熟的跨平台自动化测试框架，iOS 端底层也是依赖 WebDriverAgent，但提供了更丰富的 API 和更好的跨平台支持。

### 5.1 Appium vs 直接使用 WDA

| 对比项 | WebDriverAgent + facebook-wda | Appium |
|--------|-------------------------------|--------|
| 安装复杂度 | 低 | 高 |
| 学习曲线 | 平缓 | 较陡 |
| 跨平台支持 | 仅 iOS | iOS + Android |
| 元素定位 | 坐标为主 | 多种策略（ID、XPath等） |
| 社区生态 | 较小 | 成熟庞大 |
| 适用场景 | 个人自动化、快速脚本 | 企业级测试、团队协作 |

### 5.2 快速上手

```bash
# 安装 Appium
npm install -g appium

# 安装 XCUITest 驱动
appium driver install xcuitest

# 启动 Appium 服务
appium
```

```python
from appium import webdriver

capabilities = {
    "platformName": "iOS",
    "appium:deviceName": "iPhone",
    "appium:platformVersion": "18.0",
    "appium:automationName": "XCUITest",
    "appium:bundleId": "com.apple.MobileSMS",
    "appium:udid": "你的设备UDID",
}

driver = webdriver.Remote("http://127.0.0.1:4723", capabilities)

element = driver.find_element("accessibility id", "某个按钮")
element.click()

driver.quit()
```

### 5.3 适用场景

- 需要同时测试 iOS 和 Android 的团队
- 需要详细的测试报告和日志
- 需要集成到 CI/CD 流水线
- 需要多种元素定位策略

---

## 六、方案四：其他工具补充

### 6.1 pymobiledevice3

纯 Python 实现的 iOS 设备管理库，不依赖 Xcode。

```bash
pip install pymobiledevice3
```

特点：
- 支持设备信息查询、应用安装/卸载、文件管理
- 支持屏幕截图（不需要 WDA）
- 支持设备备份与恢复
- 不直接支持 UI 自动化操作（点击、滑动等）

适用场景：设备管理、批量操作，不涉及 UI 交互。

### 6.2 go-ios

Go 语言编写的跨平台 iOS 设备管理工具，最大优势是**不依赖 macOS**。

```bash
# 在 Windows/Linux/macOS 上均可使用
go-ios list
go-ios install --path /path/to/app.ipa
go-ios runwda --bundleid com.yourname.WebDriverAgentRunner
```

特点：
- 支持 Linux、Windows、macOS 三大平台
- 可以在 Windows 上启动 WDA
- 完全免费开源
- 快速部署

适用场景：没有 Mac 电脑但需要控制 iPhone 的场景。

### 6.3 Airtest

网易开源的跨平台自动化框架，提供可视化 IDE。

```python
from airtest.core.api import *

connect_ios("http://localhost:8100")
touch(Template("button.png"))
swipe(Template("start.png"), Template("end.png"))
text("Hello")
```

特点：
- 提供可视化 IDE（AirtestIDE），支持录制回放
- 支持图像识别定位元素
- 支持 Poco 控件检索
- 同时支持 iOS 和 Android

适用场景：游戏自动化、需要图像识别的场景。

---

## 七、方案五：AI 驱动——用自然语言控制 iPhone

这是当前最前沿的方向：用大语言模型理解手机屏幕内容，自动规划并执行操作。你只需要说一句话，AI 就能帮你完成整个操作流程。

### 7.1 Open-AutoGLM

Open-AutoGLM 是智谱 AI 开源的 Phone Agent 框架，核心组件包括：

- **AutoGLM-Phone**：视觉语言模型，理解手机屏幕内容
- **Phone Agent**：控制框架，负责执行操作

**工作原理：**

```
自然语言指令 → AutoGLM-Phone(理解屏幕+规划动作) → Phone Agent(通过WDA执行操作) → iPhone
```

**iOS 端配置步骤：**

1. 按照第四节的步骤配置好 WebDriverAgent
2. 安装 Open-AutoGLM：

```bash
git clone https://github.com/zai-org/Open-AutoGLM.git
cd Open-AutoGLM
pip install -r requirements.txt
```

3. 启动 iOS Agent：

```bash
python ios.py \
  --wda-url http://localhost:8100 \
  --base-url https://your-model-api-endpoint \
  --model autoglm-phone
```

4. 输入自然语言指令：

```
> 打开微信给文件传输助手发一条消息"测试成功"
> 打开支付宝查看余额
> 在小红书搜索深圳美食
```

AI 会自动：截图 → 理解屏幕 → 规划下一步操作 → 执行 → 循环直到任务完成。

### 7.2 AI 方案的优势与局限

**优势：**
- 零编程门槛，自然语言即可控制
- 适应性强，不同 App 不需要写不同脚本
- 可以处理意外情况（弹窗、广告等）

**局限：**
- 依赖模型能力，复杂操作可能出错
- 执行速度较慢（每步需要截图+推理）
- 需要调用大模型 API，有成本
- 隐私问题（屏幕内容需要发送到模型）

---

## 八、方案选择指南

根据你的需求，选择最合适的方案：

```
你的需求是什么？
│
├─ 只是想自动化一些日常操作（定时开关、条件触发）
│  └─ ✅ 快捷指令（零代码，开箱即用）
│
├─ 想精确控制 App 的 UI 操作（点击、输入、滑动）
│  ├─ 个人使用，快速上手
│  │  └─ ✅ WebDriverAgent + facebook-wda
│  ├─ 团队使用，需要跨平台
│  │  └─ ✅ Appium
│  └─ 没有 Mac 电脑
│     └─ ✅ go-ios + WebDriverAgent
│
├─ 想用自然语言控制手机
│  └─ ✅ Open-AutoGLM
│
└─ 只需要管理设备（安装App、查信息等）
   └─ ✅ pymobiledevice3
```

---

## 九、完整实战：从零搭建 iPhone 自动化环境

下面以最常用的 **WebDriverAgent + facebook-wda** 方案为例，给出完整的搭建流程。

### 9.1 环境清单

| 项目 | 要求 |
|------|------|
| 电脑 | Mac (macOS 13+) |
| 手机 | iPhone (iOS 16+) |
| 数据线 | 支持 USB 数据传输 |
| Xcode | 最新版（App Store 下载） |
| Python | 3.10+ |
| Apple ID | 免费（无需付费开发者账号） |

### 9.2 一键环境安装脚本

```bash
#!/bin/bash

echo "=== iPhone 自动化环境安装脚本 ==="

# 安装 Homebrew
if ! command -v brew &> /dev/null; then
    echo "安装 Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# 安装 libimobiledevice
echo "安装 libimobiledevice..."
brew install libimobiledevice

# 安装 Python 依赖
echo "安装 facebook-wda..."
pip3 install -U facebook-wda

# 克隆 WebDriverAgent
echo "克隆 WebDriverAgent..."
if [ ! -d "WebDriverAgent" ]; then
    git clone https://github.com/appium/WebDriverAgent.git
fi

echo ""
echo "=== 安装完成 ==="
echo "接下来请："
echo "1. 用 Xcode 打开 WebDriverAgent/WebDriverAgent.xcodeproj"
echo "2. 配置签名（Signing & Capabilities）"
echo "3. 连接 iPhone，选择设备后运行 Test"
echo "4. 在 iPhone 上信任开发者证书"
echo "5. 运行 iproxy 8100 8100 进行端口转发"
echo "6. 运行 curl http://localhost:8100/status 验证连接"
```

### 9.3 每次使用时的启动流程

```bash
# 终端 1：启动端口转发
iproxy 8100 8100

# 终端 2：运行 WebDriverAgent（如果未在 Xcode 中运行）
cd /path/to/WebDriverAgent
xcodebuild -project WebDriverAgent.xcodeproj \
  -scheme WebDriverAgentRunner \
  -destination 'id=<设备UDID>' \
  test

# 终端 3：运行你的 Python 脚本
python3 your_script.py
```

### 9.4 常用操作速查

```python
import wda

c = wda.Client("http://localhost:8100")

# 基础操作
c.home()                          # 回到主屏
c.screenshot("screen.png")        # 截图
c.click(x, y)                     # 点击坐标
c.double_click(x, y)              # 双击
c.swipe(fx, fy, tx, ty, d=0.5)   # 滑动
c.set_text("内容")                 # 输入文字

# App 操作
c.app_launch("com.tencent.xin")   # 启动 App
c.app_stop("com.tencent.xin")     # 关闭 App
c.app_current()                    # 获取当前 App

# 元素查找
el = c(text="确定")                # 按文本查找
el.click()                         # 点击元素
el.get_text()                      # 获取文本

# 等待
c.implicitly_wait(5)              # 隐式等待 5 秒
c.wait(text="加载完成", timeout=10) # 等待特定文本出现
```

---

## 十、安全与合规提醒

在使用 iPhone 自动化操作时，请注意以下几点：

1. **Apple 开发者协议**：免费开发者账号有 7 天签名限制，WDA 每周需要重新部署
2. **隐私保护**：自动化脚本可能访问敏感数据，注意数据安全
3. **App 使用条款**：部分 App 禁止自动化操作，请遵守相关规定
4. **设备安全**：不要在生产环境的主力手机上做实验，建议使用测试机
5. **AI 方案的数据安全**：屏幕截图发送到云端模型时，注意敏感信息泄露

---

## 十一、总结与展望

iPhone 自动化操作已经从最初的越狱插件时代，发展到了今天的多层次、多方案并存的成熟生态。回顾一下：

| 方案 | 门槛 | 灵活性 | 智能化 |
|------|------|--------|--------|
| 快捷指令 | ★☆☆ | ★★☆ | ★☆☆ |
| WebDriverAgent | ★★★ | ★★★ | ★☆☆ |
| Appium | ★★★ | ★★★ | ★★☆ |
| Open-AutoGLM | ★★☆ | ★★☆ | ★★★ |

未来的趋势很明确：**AI 将成为 iPhone 自动化的主流交互方式**。随着多模态模型能力的提升，我们终将实现真正的「动口不动手」。但在那之前，掌握 WebDriverAgent 等基础工具，依然是理解整个自动化体系的关键。

---

## 参考资源

- [WebDriverAgent - GitHub](https://github.com/appium/WebDriverAgent)
- [facebook-wda - GitHub](https://github.com/openatx/facebook-wda)
- [Appium 官方文档](https://appium.io/)
- [Open-AutoGLM - GitHub](https://github.com/zai-org/Open-AutoGLM)
- [Open-AutoGLM iOS 环境配置指南](https://github.com/zai-org/Open-AutoGLM/blob/main/docs/ios_setup/ios_setup.md)
- [pymobiledevice3 - GitHub](https://github.com/doronz88/pymobiledevice3)
- [go-ios - GitHub](https://github.com/danielpaulus/go-ios)
- [Airtest 官网](https://airtest.netease.com/)
- [Apple 快捷指令官方文档](https://support.apple.com/zh-cn/guide/shortcuts/welcome/ios)

# Burp Suite 实战使用指南

> Web 安全测试的瑞士军刀——从安装配置到常用功能的实操教程，每个功能都有可复现的步骤。

---

## 目录

- [一、Burp Suite 是什么](#一burp-suite-是什么)
- [二、安装与环境配置](#二安装与环境配置)
- [三、核心工作流总览](#三核心工作流总览)
- [四、Proxy（代理拦截）](#四proxy代理拦截)
- [五、Repeater（重放器）](#五repeater重放器)
- [六、Intruder（入侵者）](#六intruder入侵者)
- [七、Decoder（编解码器）](#七decoder编解码器)
- [八、Comparer（比较器）](#八comparer比较器)
- [九、Target（目标站点地图）](#九target目标站点地图)
- [十、Scanner（扫描器）— 专业版](#十scanner扫描器--专业版)
- [十一、BApp Store 扩展插件](#十一bapp-store-扩展插件)
- [十二、实战技巧与注意事项](#十二实战技巧与注意事项)
- [十三、速查表](#十三速查表)

---

## 一、Burp Suite 是什么

Burp Suite 是 PortSwigger 公司开发的 Web 应用安全测试平台，是渗透测试人员的标配工具。它的核心能力很简单：**拦截浏览器与服务器之间所有的 HTTP/HTTPS 请求和响应，让你查看、修改、重放、自动化攻击。**

### 社区版 vs 专业版

| 功能 | 社区版（免费） | 专业版（付费） |
|------|----------------|----------------|
| Proxy 拦截 | ✅ | ✅ |
| Repeater 重放 | ✅ | ✅ |
| Intruder 入侵者 | ⚠️ 限速（降速模式） | ✅ 无限制 |
| Decoder 编解码 | ✅ | ✅ |
| Comparer 比较 | ✅ | ✅ |
| Scanner 扫描器 | ❌ | ✅ |
| 被动扫描 | ❌ | ✅ |
| 项目文件保存 | ❌ | ✅ |
| 协作/云端 | ❌ | ✅ |

> 💡 **新手建议**：社区版足够学习所有核心操作。Intruder 限速只是慢一点，不影响学习。Scanner 是专业版最大卖点，但初学阶段手动测试能力比自动扫描更重要。

---

## 二、安装与环境配置

### 1. JDK 环境准备

Burp Suite 基于 Java，需要 JDK 17+：

```bash
# macOS
brew install openjdk@17

# Linux (Debian/Ubuntu)
sudo apt install -y openjdk-17-jdk

# 验证
java -version
# 应输出 openjdk version "17.x.x" 或更高
```

### 2. 下载与启动

```bash
# Kali Linux — 已预装，直接启动
burpsuite

# 其他系统 — 从官网下载
# https://portswigger.net/burp/communitydownload

# 命令行启动（指定内存）
java -jar -Xmx2048m burpsuite_community.jar
```

> 💡 建议至少分配 2GB 内存（`-Xmx2048m`），处理大流量时不会卡顿。

### 3. 浏览器代理配置

Burp 默认监听 `127.0.0.1:8080`。需要让浏览器流量走这个代理：

**Firefox + FoxyProxy（推荐）**：

1. 安装 FoxyProxy Standard 扩展
2. 点击 FoxyProxy 图标 → 选项 → 添加代理
3. IP：`127.0.0.1`，端口：`8080`，协议：HTTP
4. 使用时切换到该代理即可

**Chrome / Edge + SwitchyOmega**：

1. 安装 SwitchyOmega 扩展
2. 新建情景模式 → 代理服务器
3. 代理协议：HTTP，地址：`127.0.0.1`，端口：`8080`
4. 使用时切换情景模式

### 4. HTTPS 证书安装

不装证书，浏览 HTTPS 站点时会收到证书警告，部分请求无法正常拦截：

1. 浏览器代理设好后，访问 `http://burp`
2. 点击右上角 **"CA Certificate"** 下载证书文件
3. Firefox：设置 → 隐私与安全 → 查看证书 → 导入 → 选择下载的证书 → 勾选"信任此 CA 以标识网站"
4. Chrome/Edge：双击证书文件 → 安装 → 存储位置选"当前用户" → 放入"受信任的根证书颁发机构"

### 5. 常见坑与排查

| 问题 | 原因 | 解决 |
|------|------|------|
| 浏览器提示"连接不安全" | CA 证书未安装或未信任 | 重新导入证书，确认勾选"标识网站" |
| 代理设了但 Burp 没收到请求 | 浏览器有其他代理/VPN 冲突 | 关闭 VPN 或检查系统代理设置 |
| Burp 启动后浏览器无法上网 | Burp 没在运行或监听地址不对 | 确认 Proxy → Proxy settings 里监听 `127.0.0.1:8080` |
| 拦截 HTTPS 但内容是乱码 | 可能忘记安装 CA 证书 | 按上面步骤重新安装 |

---

## 三、核心工作流总览

一次典型的 Burp Suite 渗透流程：

```
浏览目标网站 → Proxy 拦截所有请求
     ↓
发现可疑参数 → 发送到 Repeater（手动测试）
     ↓
确认漏洞存在 → 发送到 Intruder（自动化攻击/批量验证）
     ↓
需要编解码 → Decoder 处理
     ↓
对比响应差异 → Comparer 分析
     ↓
整理发现 → 写报告
```

**核心思路：Proxy 是入口，Repeater 是主力，Intruder 是放大器。**

---

## 四、Proxy（代理拦截）

Proxy 是 Burp 最核心的功能——所有流量都从这里经过。

### Intercept is on / off

- **Intercept is on**：每个请求都会被拦截，停在你面前等你决定（Forward 放行 / Drop 丢弃）
- **Intercept is off**：请求自动放行，但仍记录在 HTTP History 里

> 💡 **日常使用建议**：大部分时间保持 `Intercept is off`，让流量自动流过并记录。只有在需要修改特定请求时才临时打开拦截。这样既不会被打断浏览，又不丢失任何请求记录。

### 拦截请求并修改

1. 打开 `Intercept is on`
2. 在浏览器中执行操作（如提交表单）
3. Burp 拦截到请求，在 Intercept 面板中显示原始请求
4. 直接修改请求内容（如修改 POST 参数 `username=admin` → `username=admin'`）
5. 点击 **Forward** 放行

### HTTP History

`Intercept is off` 时，所有请求都记录在 HTTP History 标签页：

- **过滤**：点击 Filter → 勾选/取消 MIME type、状态码、文件扩展名等
- **搜索**：在搜索框输入关键词，支持正则
- **排序**：点击列标题按 Host / Path / Status / Length 排序
- **快速操作**：右键请求 → Send to Repeater / Send to Intruder / Send to Decoder

### 实操：拦截 DVWA 登录请求

1. 启动 DVWA 靶场（`docker run -d -p 80:80 vulnerables/web-dvwa`）
2. 浏览器代理指向 Burp
3. 打开 `Intercept is on`
4. 在 DVWA 登录页面输入 `admin / password`，点击 Login
5. Burp 拦截到 POST 请求，可以看到 `username=admin&password=password&Login=Login`
6. 修改 `password` 参数为 `password'`，点击 Forward
7. 观察 DVWA 返回 SQL 报错——说明存在 SQL 注入点

---

## 五、Repeater（重放器）

Repeater 是手动测试漏洞的主力工具——你可以反复修改请求并查看响应，逐一手动验证每个假设。

### 基本操作

1. 从 Proxy / Intruder 中右键 → **Send to Repeater**（快捷键 `Ctrl+R`）
2. 切换到 Repeater 标签页，选中对应请求标签
3. 修改请求参数
4. 点击 **Send** 发送
5. 查看右侧响应面板

### 实操1：手动测试 SQL 注入

```
# 原始请求参数
username=admin&password=password

# 测试1：加单引号观察报错
username=admin'&password=password
→ 如果返回 SQL 报错，说明存在注入点

# 测试2：永真条件尝试绕过登录
username=admin' OR '1'='1&password=anything
→ 如果登录成功，确认 SQL 注入漏洞

# 测试3：注释符验证
username=admin'--&password=anything
→ 如果也登录成功，确认注释符可用，后续可构造更复杂 Payload
```

### 实操2：测试越权漏洞

```
# 用户A的请求
GET /api/user/profile?userId=1001 HTTP/1.1
Cookie: session=abc123

# 修改 userId 为用户B的ID
GET /api/user/profile?userId=1002 HTTP/1.1
Cookie: session=abc123

# 如果返回了用户B的数据 → 水平越权漏洞
# 如果返回用户A自己的数据 → 服务端做了权限校验，安全
```

> 💡 **Repeater 使用技巧**：每个测试点开一个独立标签页，用标签自命名功能（双击标签名）标记测试内容（如"SQLi-login"、"IDOR-userId"），避免标签一多就混乱。

---

## 六、Intruder（入侵者）

Intruder 是 Burp 的自动化攻击工具——把 Repeater 的手动逐条测试变成批量自动化。

### 四种攻击模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **Sniper** | 单参数位，逐个 payload 替换 | 单个参数测试（如密码爆破） |
| **Battering Ram** | 所有参数位用同一组 payload | 多处用同一字典（如同一密码试多个字段） |
| **Pitchfork** | 多参数位一一对应 | 用户名和密码一一配对测试 |
| **Cluster Bomb** | 多参数位笛卡尔积 | 用户名×密码的全组合爆破 |

> 💡 **社区版 Intruder 有请求速率限制**，跑得较慢但不影响学习。专业版无限制。

### Intruder 使用流程

1. 从 Proxy 右键 → **Send to Intruder**（快捷键 `Ctrl+I`）
2. 切换到 Intruder → Positions 标签
3. 选择攻击模式
4. 标记参数位：清除默认标记（`§ §`），选中你要替换的值，点击 **Add §**
5. 切换到 Payloads 标签，配置 payload
6. 点击 **Start attack**

### Payload 常用类型

| 类型 | 说明 | 示例 |
|------|------|------|
| Simple list | 手动输入或从文件加载 | `/usr/share/wordlists/rockyou.txt` |
| Numbers | 数字递增/递减 | 1 → 1000 |
| Brute forcer | 指定字符集全排列 | a-z, 0-9 生成短字符串 |
| Recursive grep | 从前一次响应中提取值 | 提取 CSRF token 用于下一次请求 |

### Grep-Match / Grep-Extract

在 Intruder 攻击结果的 **Options** 标签中配置：

- **Grep-Match**：在响应中搜索特定字符串（如"Login successful"），方便在结果表格里快速判断成功/失败
- **Grep-Extract**：从响应中提取特定值（如从响应头提取 token），可用于构造下一次请求

### 实操1：DVWA 登录密码爆破

1. Proxy 中拦截 DVWA 登录请求，右键 → Send to Intruder
2. Positions：选择 **Sniper** 模式，只标记 `password` 参数的值：
   ```
   username=admin&password=§password§&Login=Login
   ```
3. Payloads：选择 Simple list，加载密码字典
4. Options → Grep-Match：添加 `Login failed`（DVWA 登录失败时出现的文字）
5. Start attack
6. 在结果中找到 **Grep-Match 列不为勾**的请求——那大概率就是正确的密码

### 实操2：枚举用户 ID

```
# 请求
GET /api/user/§1§ HTTP/1.1

# Positions：标记 URL 中的数字
# Payloads：Numbers，范围 1 → 1000，步长 1
# Grep-Match：添加 "user not found"

# 攻击结果中：
# - Grep-Match 列无勾 → 有效用户ID
# - Grep-Match 列有勾 → 无效ID
# - 按状态码排序：200 = 有效，403/404 = 无效
```

---

## 七、Decoder（编解码器）

Decoder 是处理各种编码格式的瑞士军刀——解码还原混淆数据、编码构造攻击 Payload。

### 支持的格式

| 操作类型 | 支持格式 |
|----------|----------|
| 编码/解码 | Base64、URL、HTML、Hex、Gzip |
| 哈希计算 | MD5、SHA-1、SHA-256、SHA-512 |
| 智能识别 | Smart Decode（自动检测并解码） |

### 使用方式

1. 直接在 Decoder 标签页输入内容，或从其他模块右键 → Send to Decoder
2. 选择操作：Encode / Decode / Hash
3. 选择格式
4. 查看结果

### 实操：解码多层编码的 Cookie

```
# 原始 Cookie 值（看似乱码）
user=%7B%22id%22%3A1001%2C%22role%22%3A%22user%22%7D

# 第1步：URL 解码
→ user={"id":1001,"role":"user"}

# 第2步：发现是 JSON，修改 role 为 admin
→ user={"id":1001,"role":"admin"}

# 第3步：重新 URL 编码
→ user=%7B%22id%22%3A1001%2C%22role%22%3A%22admin%22%7D

# 第4步：用 Repeater 发送修改后的 Cookie，验证是否越权成功
```

> 💡 **Smart Decode**：不确定数据经过几层编码时，点 Smart Decode 让 Burp 自动识别并逐层解码，省去手动猜测。

---

## 八、Comparer（比较器）

Comparer 用于比较两次请求或响应的差异——当你修改了一个参数，想直观看到响应有什么变化时很有用。

### 使用方式

1. 在 Proxy History / Repeater 中选中两个请求/响应
2. 右键 → **Send to Comparer**
3. 切换到 Comparer 标签页
4. 选中两条记录，点击 **Compare**
5. Burp 会以文字/字节两种模式展示差异，差异部分高亮

### 实操：发现越权响应差异

```
# 请求A（用户A的合法请求）
GET /api/orders HTTP/1.1
Cookie: session=userA_session
→ 响应：3条订单，共 ¥500

# 请求B（修改Cookie为用户B的session）
GET /api/orders HTTP/1.1
Cookie: session=userB_session
→ 响应：5条订单，共 ¥1200

# Comparer 对比两个响应：
# - 订单数量不同（3 vs 5）
# - 金额不同（¥500 vs ¥1200）
# → 说明 session 校验不足或 Cookie 可伪造，确认越权
```

---

## 九、Target（目标站点地图）

Target 标签页自动汇总了所有代理经过的请求，按站点结构生成树形地图。

### 核心功能

- **Site map**：按域名/路径分层展示所有访问过的 URL，一目了然地看到站点的完整结构
- **Scope**：设定测试范围，只关注目标站点，过滤掉无关流量

### 配置 Scope

1. Target → Site map → 右键目标域名 → **Add to scope**
2. 在 Scope 设置中可以选择 **Include** / **Exclude** 模式
3. 设好 Scope 后，Proxy History / Scanner 等模块都会按此范围过滤

> 💡 **始终设定 Scope**。不设 Scope 的话，浏览器加载的第三方资源（广告、统计脚本、CDN）的请求也会混进来，严重干扰你关注目标站点。

---

## 十、Scanner（扫描器）— 专业版

Scanner 是 Burp 专业版的核心差异化功能，能够自动发现漏洞。

### 被动扫描 vs 主动扫描

| 类型 | 行为 | 风险 |
|------|------|------|
| **被动扫描** | 只分析已代理的流量，不发送新请求 | 零风险，不触发目标任何告警 |
| **主动扫描** | 向目标发送大量测试请求，主动探测漏洞 | 有风险，可能触发 WAF / IPS 告警 |

### 扫描流程

1. 在 Site map 中右键目标 → **Actively scan this host**
2. 配置扫描范围（Crawl + Audit / Audit only）
3. 等待扫描完成，在 Dashboard → Issue activity 中查看发现
4. 按严重程度排序（Critical / High / Medium / Low / Info）
5. 点击每个 Issue 查看详情、请求/响应、修复建议

### 误报排除

- 扫描结果中每个 Issue 都有 **Confidence**（信心等级）：Certain / Firm / Tentative
- 优先关注 Confidence 为 Certain 和 Firm 的发现
- Tentative 的可能是误报，需要用 Repeater 手动确认

> 💡 **社区版替代方案**：社区版无法使用 Scanner，但可以配合 SQLmap、Nikto、Nuclei 等开源工具实现类似效果：
> ```bash
> # 从 Burp 导出请求保存为文件 request.txt，然后用 SQLmap 测试
> sqlmap -r request.txt --batch --level 3
> 
> # Nikto 全站扫描
> nikto -h http://target.com
> 
> # Nuclei 漏洞模板扫描
> nuclei -u http://target.com -t cves/
> ```

---

## 十一、BApp Store 扩展插件

BApp Store 是 Burp 的插件市场，社区贡献了大量增强工具。

### 插件安装

1. Extender → BApp Store 标签页
2. 浏览或搜索插件
3. 点击 **Install** 安装
4. 已安装的插件在 Extender → Installed 中管理

### 必装插件推荐

| 插件 | 功能 | 适用场景 |
|------|------|----------|
| **HackBar** | 在 Burp 内快速构造攻击 Payload，支持编码转换 | SQL 注入 / XSS 手工测试 |
| **Logger++** | 增强版日志，记录所有模块的请求/响应，支持高级过滤 | 需要完整记录所有流量的场景 |
| **Autorize** | 自动化越权测试——用低权限 Cookie 重放高权限请求 | 水平/垂直越权批量检测 |
| **Copy as Python Requests** | 右键一键导出请求为 Python requests 代码 | 需要写 PoC 脚本时 |
| **Wappalyzer** | 识别目标站点的技术栈（框架/服务器/CMS） | 信息收集阶段 |
| **JSON Beautifier** | 格式化 JSON 响应，方便阅读 | API 测试时 JSON 响应可读性差 |
| **CSRF Token Tracker** | 自动更新 CSRF Token，避免 Intruder 攻击因 Token 过期而失败 | 有 CSRF 防护的目标 |
| **Turbo Intruder** | 高性能 Intruder 替代品，支持 Python 脚本化攻击 | 大规模爆破/竞态条件测试 |

> 💡 **Autorize 配合 Burp 使用**：安装后，在 Autorize 中配置低权限用户的 Cookie。之后用高权限账号正常浏览站点，Autorize 会自动用低权限 Cookie 重放每个请求，并标注哪些请求存在越权——省去了手动逐条测试的繁琐。

---

## 十二、实战技巧与注意事项

### 1. 上游代理链（访问内网目标）

当目标在内网，需要通过跳板机访问时：

Proxy → Proxy settings → Upstream Proxy Servers → Add

```
目标域名：*.internal.corp
代理地址：jump-host.corp
代理端口：1080
```

这样访问内网目标的流量会先经过跳板机，其他流量照常走直连。

### 2. 大文件上传/下载绕过代理

大文件流量经过 Burp 会导致卡顿，可以在 Proxy 设置中排除：

Proxy → Proxy settings → Intercept Client Requests → Add：

```
URL 匹配：\.zip$|\.iso$|\.tar\.gz$
动作：Drop 或 不拦截
```

### 3. 内存与性能调优

```bash
# 启动时分配更多内存
java -jar -Xmx4096m burpsuite_community.jar

# 运行中清理内存
# 1. Proxy History 全选 → 右键 → Delete（清除历史记录释放内存）
# 2. 临时关闭不需要的被动扫描（专业版）
```

### 4. 与 SQLmap 联动

从 Burp 导出请求给 SQLmap：

```
# 方法1：Proxy History 中右键请求 → Save items（保存为文件）
# 然后用 SQLmap 加载：
sqlmap -r saved_request.txt --batch

# 方法2：复制请求为原始文本，粘贴到文件
# 在 Repeater 中右键 → Copy to clipboard → 保存为 request.txt
sqlmap -r request.txt --dbs
```

### 5. 多用户/多角色测试

测试越权时的 Session 管理技巧：

- 在浏览器开多个 Profile（不同 Profile 用不同 Cookie）
- 用 FoxyProxy 配合 Burp，不同浏览器窗口共用同一个代理
- Autorize 插件自动用低权限 Cookie 重放，省去手动切换

> ⚠️ **合规提醒**：Burp Suite 仅用于授权的安全测试。未经许可对他人系统进行扫描或攻击是违法行为。始终确认你已获得目标系统所有者的书面授权。

---

## 十三、速查表

### 常用快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+R` | Send to Repeater |
| `Ctrl+I` | Send to Intruder |
| `Ctrl+D` | Send to Decoder |
| `Ctrl+F` | Forward（放行拦截的请求） |
| `Ctrl+T` | Toggle Intercept on/off |
| `Ctrl+U` | URL 编码选中内容 |
| `Ctrl+Shift+U` | URL 解码选中内容 |
| `Ctrl+H` | HTML 编码选中内容 |
| `Ctrl+Shift+H` | HTML 解码选中内容 |
| `Ctrl+B` | Base64 编码选中内容 |
| `Ctrl+Shift+B` | Base64 解码选中内容 |

### 常用操作路径

| 操作 | 路径 |
|------|------|
| 拦截请求修改 | Proxy → Intercept → 修改 → Forward |
| 发送到手动测试 | 右键请求 → Send to Repeater |
| 发送到自动化攻击 | 右键请求 → Send to Intruder |
| 编解码 | 右键选中内容 → Send to Decoder |
| 比较差异 | 选中两条 → 右键 → Send to Comparer |
| 设定测试范围 | Target → Site map → 右键域名 → Add to scope |
| 导出请求给SQLmap | 右键请求 → Save items → sqlmap -r file.txt |

### Payload 字典推荐

| 用途 | 字典路径（Kali Linux） |
|------|------------------------|
| 通用密码 | `/usr/share/wordlists/rockyou.txt` |
| SecLists 全集 | `/usr/share/seclists/` |
| Web 内容发现 | `/usr/share/seclists/Discovery/Web-Content/` |
| 用户名枚举 | `/usr/share/seclists/Usernames/` |
| Fuzzing | `/usr/share/seclists/Fuzzing/` |

### 状态码速查

| 状态码 | 含义 | 渗透中的意义 |
|--------|------|---------------|
| 200 | 成功 | 正常响应，检查内容是否泄露敏感信息 |
| 301/302 | 重定向 | 登录后跳转，关注重定向目标 |
| 401 | 未认证 | 需要有效凭据 |
| 403 | 禁止访问 | 有权限控制，测试能否绕过 |
| 404 | 不存在 | 路径/资源不存在 |
| 500 | 服务器错误 | 可能触发了漏洞（SQL注入常见） |

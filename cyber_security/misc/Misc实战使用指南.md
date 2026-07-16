# Misc 实战使用指南

> CTF 杂项方向全景指南——从题型分类、解题思路到工具深度使用，覆盖编码解码、隐写术、流量分析、压缩包取证、多媒体隐写等全部常见考点。

---

## 目录

- [一、Misc 是什么](#一misc-是什么)
- [二、题型全景与解题决策树](#二题型全景与解题决策树)
- [三、编码解码](#三编码解码)
- [四、隐写术](#四隐写术)
- [五、流量分析](#五流量分析)
- [六、压缩包取证](#六压缩包取证)
- [七、文件分析与修复](#七文件分析与修复)
- [八、多媒体隐写](#八多媒体隐写)
- [九、内存取证](#九内存取证)
- [十、OSINT 与社会工程](#十osint-与社会工程)
- [十一、脚本与自动化](#十一脚本与自动化)
- [十二、实战组合场景](#十二实战组合场景)
- [十三、常见陷阱与排查](#十三常见陷阱与排查)
- [十四、速查表](#十四速查表)

---

## 一、Misc 是什么

Misc（Miscellaneous，杂项）是 CTF 竞赛中覆盖面最广的方向，凡是无法归入 Web、Pwn、Reverse、Crypto 的题型都归 Misc。核心考察的是**信息隐藏与提取**的能力——出题人把 flag 藏在各种载体里，你需要找到正确的工具和方法把它挖出来。

### Misc vs 其他方向

| 特征 | Misc | Web | Crypto | Reverse/Pwn |
|------|------|-----|--------|-------------|
| 核心能力 | 信息提取、格式理解 | 漏洞利用 | 数学推导 | 逆向/漏洞利用 |
| 答题方式 | 找 flag → 提交 | 找漏洞 → 利用 | 推导 → 计算 | 分析 → 利用 |
| 工具依赖 | 重（大量专业工具） | 中（Burp/浏览器） | 轻（纸笔+Python） | 中（IDA/GDB） |
| 入门门槛 | 低（上手快） | 中 | 高 | 高 |

### Misc 核心技能模型

```
Misc 解题 = 格式认知 + 工具熟练 + 脚本能力 + 耐心
           ─────────   ─────────   ─────────   ────
           知道文件长什么样  知道用什么工具  能写自动化脚本  逐字节排查
```

---

## 二、题型全景与解题决策树

### 题型分类

| 大类 | 子题型 | 频率 | 难度 |
|------|--------|------|------|
| 编码解码 | Base 家族、Hex、URL、Unicode、Morse、Braille、ROT、多层嵌套 | ★★★★★ | ★★ |
| 隐写术 | 图片 LSB/MSB、文件追加、盲水印、图片拼接 | ★★★★★ | ★★★ |
| 流量分析 | HTTP/TCP/UDP/USB/ICMP/DNS、协议还原、文件提取 | ★★★★ | ★★★ |
| 压缩包取证 | ZIP 伪加密、密码爆破、嵌套压缩、CRC32、明文攻击 | ★★★★ | ★★★ |
| 文件修复 | 文件头损坏、高度裁剪、格式转换 | ★★★ | ★★ |
| 多媒体隐写 | 频谱图藏字、摩尔斯、SSTV、LSB 音频、双声道 | ★★★ | ★★★ |
| 内存取证 | Volatility 内存分析、进程/文件提取 | ★★★ | ★★★★ |
| OSINT | 图片定位、社交媒体溯源、EXIF 信息 | ★★ | ★★ |

### 解题决策树

```
拿到题目
├─ 纯文本 → 尝试各种解码（Base64/32/16 → Hex → URL → ROT → Morse → ...）
│          → 多层嵌套？逐层剥或扔给 CyberChef Magic
├─ 文件 → file 命令看类型
│       ├─ 图片 → exiftool 看元数据
│       │       → binwalk 看隐藏文件
│       │       → zsteg/StegSolve 看 LSB
│       │       → 010 Editor 看高度是否被裁剪
│       │       → 盲水印检测
│       ├─ 压缩包 → 伪加密？→ 修复
│       │          → 有密码？→ 爆破/明文攻击/CRC32
│       │          → 嵌套？→ 递归解压
│       ├─ 音频 → Audacity 看频谱图
│       │         → 摩尔斯电码？
│       │         → SSTV 解码？
│       │         → 双声道差分？
│       ├─ pcap → Wireshark 分析
│       │         → HTTP 文件还原
│       │         → TCP 流追踪
│       │         → USB 键鼠取证
│       ├─ 内存镜像 → Volatility 分析
│       └─ 未知 → binwalk 扫描 → xxd 看头部 → strings 找线索
└─ 组合题 → 按上述逐层拆解，每步提取的中间结果再套用决策树
```

---

## 三、编码解码

> 编码解码是 Misc 最基础的题型，也是很多复杂题的第一步。熟练掌握各种编码的特征和解码方法是基本功。

### 3.1 常见编码特征速判

| 编码 | 字符集 | 特征示例 | 识别技巧 |
|------|--------|----------|----------|
| Base64 | A-Z a-z 0-9 + / = | `ZmxhZ3toZWxsb30=` | 末尾 0-2 个 `=` 填充，长度 4 的倍数，大小写+数字混排 |
| Base32 | A-Z 2-7 = | `MZWGCZ33M5TGI===` | 只有大写+数字 2-7，末尾 `=` 填充 |
| Base16 (Hex) | 0-9 A-F | `666c61677b68656c6c6f7d` | 只有 0-9 和 A-F（或 a-f），偶数长度 |
| URL 编码 | %XX | `%66%6c%61%67` | `%` 后跟两位十六进制 |
| Unicode 转义 | \uXXXX | `\u0066\u006c\u0061\u0067` | `\u` 后跟 4 位十六进制 |
| HTML 实体 | &#XXX; | `&#102;&#108;&#97;&#103;` | `&#` 开头 `;` 结尾 |
| Morse | . - | `..-. .-.. .- --. ` | 只有 `.` `-` 和分隔符 |
| ROT13 | 旋转字母 | `synt{uryyb}` | 看起来像英文但无意义，字母偏移 13 |
| Braille | ⠍⠕⠗⠎⠑ | 盲文字符 | Unicode 盲文区块 U+2800-U+28FF |
| Bacon | A/B 五位组 | `AABBA AABAB` | 只有 A 和 B，5 位一组 |
| XXencode | + - 0-9 A-Z a-z | 类似 Base64 | 以 `+` 开头，罕见 |

### 3.2 Base 家族深度解码

**Base64 变体识别**：

```
标准 Base64:  字符集 A-Z a-z 0-9 + /   填充 =
URL-safe:     字符集 A-Z a-z 0-9 - _   无填充或 =
Base64u:      与标准相同但无填充
```

**手动解码步骤（面试/无工具时）**：

```python
# Base64 解码核心：查表 → 6bit → 拼接 → 按 8bit 截断
import base64

# 标准 Base64
base64.b64decode("ZmxhZ3toZWxsb30=")  # b'flag{hello}'

# URL-safe Base64（+ → -，/ → _）
base64.urlsafe_b64decode("ZmxhZ3toZWxsb30=")

# Base32
base64.b32decode("MZWGCZ33M5TGI===")

# Base16
base64.b16decode("666C61677B68656C6C6F7D")
```

**多层嵌套解码套路**：

```text
常见嵌套模式：
1. Base64( Hex( flag ) )           → From Base64 → From Hex
2. Base64( Base64( flag ) )        → From Base64 → From Base64
3. Base32( Base64( Hex( flag ) ))  → 逐层剥
4. URL( Base64( ROT13( flag ) ))   → URL Decode → From Base64 → ROT13

识别技巧：
- 先看最外层特征判断编码类型
- 解一层看一层，每层结果再套决策树
- 不确定就扔 CyberChef Magic（Depth 调到 5+）
```

### 3.3 CyberChef 深度使用

> CyberChef 完整操作分类、Recipe 管理、Magic 深度、Registers/Fork 进阶见 [CyberChef 实战使用指南](../crypto/CyberChef实战使用指南.md)。

**编码解码场景下 CyberChef 最佳实践**：

```text
场景1：未知编码 → Magic 一键识别
  Input: 粘贴数据
  拖入 Magic → Depth 调到 5 → 看结果列表
  Magic 会自动尝试 Base64/32/16/Hex/ROT13/... 排序输出

场景2：多层嵌套 → 逐层拖操作
  Recipe: From Base64 → From Hex → URL Decode
  每拖一个操作，Output 实时更新，随时确认中间结果

场景3：大量同类数据 → Fork 批量
  Input: 多行数据
  Recipe: Fork → From Base64 → Merge
  逐行处理，效率远超手动

场景4：编码 → 哈希验证
  Recipe: From Base64 → MD5
  解码后同时算哈希，对比题目给的哈希值

场景5：XOR 解密
  Recipe: XOR Brute Force（逐 key 尝试）
  或 XOR（已知 key）→ 看输出是否为可读文本

实用技巧：
- 拖操作到 Recipe 后可拖拽排序
- 双击操作可修改参数
- Recipe 区域右上角可保存/加载/分享 URL
- Input 支持拖文件进来（自动转 Hex）
- 右上角 Bake 按钮控制是否实时计算
```

### 3.4 非标准编码

**ROT 家族**：

```python
# ROT13（最常见，字母偏移 13，自反）
import codecs
codecs.decode("synt{uryyb}", "rot_13")  # 'flag{hello}'

# ROT47（ASCII 33-126 循环偏移 47）
def rot47(s):
    return ''.join(chr(33 + (ord(c) - 33 + 47) % 94) if 33 <= ord(c) <= 126 else c for c in s)

# ROT N（通用）
def rot_n(s, n):
    result = []
    for c in s:
        if 'a' <= c <= 'z':
            result.append(chr((ord(c) - ord('a') + n) % 26 + ord('a')))
        elif 'A' <= c <= 'Z':
            result.append(chr((ord(c) - ord('A') + n) % 26 + ord('A')))
        else:
            result.append(c)
    return ''.join(result)
```

**培根密码（Bacon Cipher）**：

```python
# 培根密码：A/B 五位组对应字母
BACON_TABLE = {
    'AAAAA':'A','AAAAB':'B','AAABA':'C','AAABB':'D','AABAA':'E',
    'AABAB':'F','AABBA':'G','AABBB':'H','ABAAA':'I','ABAAB':'K',
    'ABABA':'L','ABABB':'M','ABBAA':'N','ABBAB':'O','ABBBA':'P',
    'ABBBB':'Q','BAAAA':'R','BAAAB':'S','BAABA':'T','BAABB':'U',
    'BABAA':'W','BABAB':'X','BABBA':'Y','BABBB':'Z',
}

def bacon_decode(s):
    s = s.replace(' ', '').upper()
    return ''.join(BACON_TABLE.get(s[i:i+5], '?') for i in range(0, len(s), 5))
```

**栅栏密码（Rail Fence Cipher）**：

```python
def rail_fence_decrypt(ciphertext, rails):
    fence = [[] for _ in range(rails)]
    rail = 0
    direction = 1
    for c in ciphertext:
        fence[rail].append(c)
        rail += direction
        if rail == rails - 1 or rail == 0:
            direction *= -1
    # 重建
    indices = sorted(range(len(ciphertext)), key=lambda i: (i,))
    result = [''] * len(ciphertext)
    idx = 0
    for r in range(rails):
        for c in fence[r]:
            result[idx] = c
            idx += 1
    return ''.join(result)

# 不知道栏数？逐个尝试
for n in range(2, 20):
    print(f"rails={n}: {rail_fence_decrypt(cipher, n)}")
```

---

## 四、隐写术

> 隐写术（Steganography）是 Misc 最核心的题型——把信息藏进图片、音频等载体的冗余空间中，在不改变载体外观的前提下嵌入数据。

### 4.1 图片隐写分类

| 手法 | 原理 | 检测工具 | 提取工具 |
|------|------|----------|----------|
| LSB 隐写 | 修改像素最低位 | zsteg、StegSolve | zsteg、StegSolve Extract、Python 脚本 |
| 文件追加 | 图片末尾追加数据 | binwalk | binwalk -e、foremost |
| 高度裁剪 | 修改 IHDR 高度，裁掉含 flag 区域 | 010 Editor、PNG 结构分析 | 修改 IHDR 还原高度 |
| 盲水印 | 频域嵌入水印 | bwmforpy3 | bwmforpy3 decode |
| 图片拼接 | 两张图差分显示 | GIMP 差值模式 | GIMP 图层叠加 |
| EXIF 隐写 | 写入元数据字段 | exiftool | exiftool |
| 调色板隐写 | 修改索引颜色 | StegSolve、010 Editor | 手动提取 |
| 隐写密码保护 | Steghide/Outguess/F5 等加密隐写 | Stegseek、stegcracker | 暴力破解密码后提取 |
| 宽高 CRC 修复 | 修改宽高但未重算 CRC | PNG CRC 校验脚本 | 爆破正确宽高 |

### 4.2 PNG 结构深度理解

PNG 文件结构是图片隐写的基础知识：

```text
PNG 文件 = 文件头 + 若干数据块（Chunk）

文件头（8 字节）：89 50 4E 47 0D 0A 1A 0A

数据块结构：4字节长度 + 4字节类型 + 数据 + 4字节CRC

关键 Chunk：
┌──────────┬────────────┬─────────────────────────────────┐
│ 类型     │ 含义       │ 关键字段                         │
├──────────┼────────────┼─────────────────────────────────┤
│ IHDR     │ 图像头     │ 宽(4B) + 高(4B) + 位深 + 色彩类型 │
│ IDAT     │ 图像数据   │ deflate 压缩的像素数据           │
│ IEND     │ 图像结束   │ 无数据                           │
│ PLTE     │ 调色板     │ 索引颜色表的 RGB 三元组          │
│ tEXt     │ 文本数据   │ 关键字 + 值（可藏 flag）         │
│ iCCP     │ 色彩配置   │ ICC 颜色配置文件                 │
│ pHYs     │ 物理像素   │ 分辨率信息                       │
└──────────┴────────────┴─────────────────────────────────┘

IHDR 偏移量：
  宽度：0x10 - 0x13（大端序 4 字节）
  高度：0x14 - 0x17（大端序 4 字节）
```

**PNG CRC 校验与宽高爆破**：

```python
#!/usr/bin/env python3
"""PNG 宽高 CRC 爆破——题目修改了 IHDR 的宽/高但未重算 CRC"""

import struct
import zlib
import sys

def brute_png_ihdr(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()

    # 提取 IHDR 中的 CRC（紧跟 IHDR 数据后）
    ihdr_data = data[12:20+4]  # 类型+数据（不含长度和CRC本身）
    correct_crc = struct.unpack('>I', data[29:33])[0]

    width = struct.unpack('>I', data[16:20])[0]
    height = struct.unpack('>I', data[20:24])[0]

    print(f"当前宽: {width}, 高: {height}, CRC: 0x{correct_crc:08x}")

    # 爆破宽度（保持高度不变）
    for w in range(1, 4096):
        test_ihdr = b'IHDR' + struct.pack('>II', w, height) + data[24:29]
        if zlib.crc32(test_ihdr) & 0xFFFFFFFF == correct_crc:
            print(f"[+] 找到正确宽度: {w}")

    # 爆破高度（保持宽度不变）
    for h in range(1, 4096):
        test_ihdr = b'IHDR' + struct.pack('>II', width, h) + data[24:29]
        if zlib.crc32(test_ihdr) & 0xFFFFFFFF == correct_crc:
            print(f"[+] 找到正确高度: {h}")

if __name__ == '__main__':
    brute_png_ihdr(sys.argv[1])
```

### 4.3 LSB 隐写深度实践

**原理**：图像每个像素由 R/G/B 三通道各 8 位组成，修改最低位（LSB）对人眼不可见，但可嵌入 0/1 信息。

**zsteg 使用深度**：

```bash
# 基础检测
zsteg image.png                  # 默认检测，输出找到的数据

# 全通道扫描（推荐）
zsteg -a image.png               # 扫描所有通道+位平面组合

# 指定通道提取
# 通道格式：[r|g|b|a][1..8][,xY|,XY]
zsteg -e b1,lsb,xy image.png > output.bin   # 从蓝色通道 LSB 提取
zsteg -e r1,lsb,xy image.png > output.bin   # 从红色通道 LSB 提取
zsteg -e b2,msb,xy image.png > output.bin   # 从蓝色通道第2位 MSB 提取

# 尝试提取为文本
zsteg -e b1,lsb,xy image.png | strings

# 输出到文件进一步分析
zsteg -e b1,lsb,xy image.png > extracted.bin
file extracted.bin               # 看提取出来是什么
binwalk extracted.bin            # 可能里面还藏了东西
```

**StegSolve 使用步骤**：

```text
1. java -jar StegSolve.jar 打开图片
2. 逐通道查看：
   - 左右箭头切换位平面（Red Plane 0/1/7、Green Plane 0...）
   - Plane 0 = LSB，Plane 7 = MSB
   - 某个位平面可能出现隐藏图案/文字
3. Analyse → Data Extract：
   - 选择位平面（勾选 R/G/B 的 bit0）
   - 选择行/列遍历顺序
   - 点击 Preview → 看输出是否含 flag
4. Analyse → Frame Browser（GIF 多帧查看）
5. Image Combiner（两张图叠加）：
   - 打开第一张 → File → Combine → 选第二张
   - 切换运算模式（XOR/ADD/SUB/MUL）→ 看结果
```

**Python 手动提取 LSB**：

```python
#!/usr/bin/env python3
"""手动 LSB 提取——当 zsteg 不奏效时自己写"""

from PIL import Image
import sys

def extract_lsb(image_path, channels='rgb', bit=0):
    img = Image.open(image_path)
    pixels = list(img.getdata())

    bits = []
    for pixel in pixels:
        for i, ch in enumerate('rgb'):
            if ch in channels:
                bits.append((pixel[i] >> bit) & 1)

    # 每 8 位组成一个字节
    result = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        result.append(byte)

    # 尝试解码
    try:
        text = result.decode('utf-8', errors='ignore')
        if 'flag' in text.lower():
            # 找到 flag 附近的内容
            idx = text.lower().index('flag')
            print(f"[+] 在 LSB 中找到 flag: {text[idx:idx+50]}")
        else:
            print(f"[*] LSB 输出前 200 字符: {text[:200]}")
    except:
        print(f"[*] LSB 输出前 50 字节 (hex): {result[:50].hex()}")

if __name__ == '__main__':
    extract_lsb(sys.argv[1])
```

### 4.4 盲水印

**原理**：在频域（DFT/DCT）中嵌入水印，肉眼不可见，需要原图 + 水印图做差才能提取。

```bash
# bwmforpy3（Python 盲水印工具）
# 安装：pip install bwmforpy3

# 提取盲水印（需要原图和水印图）
python3 bwmforpy3.py decode original.png watermarked.png output.png

# 如果没有原图，尝试以下方法：
# 1. 频域分析（DFT）
# 2. 图片差分（两张相似图片做差）
# 3. GIMP 差值模式叠加
```

### 4.5 EXIF 隐写

```bash
# 查看所有元数据
exiftool image.jpg

# 常见藏 flag 位置：
# - ImageDescription
# - Artist / Author
# - UserComment
# - Copyright
# - GPS 坐标（可能指向 flag 相关位置）

# 修改 EXIF
exiftool -Artist="flag{xxx}" image.jpg

# 删除所有元数据
exiftool -all= image.jpg

# 批量查看
exiftool -r ./images/
```

### 4.6 隐写术暴力破解

> 很多隐写工具（Steghide、Outguess、F5、openstego 等）嵌入数据时支持设置密码，CTF 题目经常用这种方式增加难度。如果题目提示"密码是纯数字/6位/常见弱口令"，就需要暴力破解。

**常见加密隐写工具与对应爆破工具**：

| 隐写工具 | 支持格式 | 爆破工具 | 特点 |
|----------|---------|---------|------|
| Steghide | JPEG / BMP | ★Stegseek / stegbrute / stegcracker | Stegseek 最快（秒级百万次），stegbrute 多线程 Rust 实现 |
| JPHide | JPEG | Stegbreak（Stegdetect 套件） | Stegdetect 检测 + Stegbreak 爆破 |
| Outguess | JPEG | stego-toolkit / 自写脚本 + 字典 | stego-toolkit 的 brute_jpg.sh 自动遍历多种工具 |
| F5 | JPEG | stego-toolkit / 自写脚本 + 字典 | 同上 |
| openstego | PNG / BMP | 自写脚本 + 字典 | 无专用爆破工具 |
| Steg | PNG | 自写脚本 + 字典 | Python stegano 库 |

#### 4.6.1 Stegseek：Steghide 暴力破解利器

Stegseek 是 Steghide 的暴力破解插件，利用 Steghide 的密码验证机制直接跳过提取步骤，只验证密码正确性，速度比逐次调用 `steghide extract` 快几个数量级。

```bash
# 安装
# Ubuntu/Debian:
sudo apt install stegseek
# 或从源码编译：https://github.com/RickdeJager/stegseek
# Kali: apt install stegseek

# 基本爆破（使用内置词表）
stegseek --crack image.jpg /usr/share/wordlists/rockyou.txt
# 输出：stegseek: Trying password 'xxx'... 成功则显示密码

# 爆破并提取（密码正确后自动提取隐藏数据）
stegseek --crack image.jpg /usr/share/wordlists/rockyou.txt -xf output.txt
# -xf: 提取到的数据保存到指定文件

# 指定自定义字典
stegseek --crack image.jpg custom_wordlist.txt -xf hidden_data.bin

# 纯数字密码爆破（自建字典）
# 生成 000000-999999 的数字字典
crunch 6 6 0123456789 -o 6digit_num.txt
stegseek --crack image.jpg 6digit_num.txt -xf output.txt

# 查看图片隐写信息（不提取，只看是否用了 steghide）
steghide info image.jpg
# 如果提示 "Enter passphrase:" 说明有密码保护

# Steghide 手动提取（知道密码时）
steghide extract -sf image.jpg -p "password"
# -sf: 含隐写数据的文件
# -p: 密码
```

**Stegseek vs 手动循环 Steghide**：

```python
# ❌ 慢：每次调用 steghide 都要完整提取（每秒约 10-50 次）
import subprocess
with open('wordlist.txt') as f:
    for line in f:
        pw = line.strip()
        result = subprocess.run(
            ['steghide', 'extract', '-sf', 'image.jpg', '-p', pw],
            capture_output=True
        )
        if b'wrote' in result.stdout:
            print(f"[+] 密码: {pw}")
            break

# ✓ 快：Stegseek 只验证密码（每秒约 50-200 万次）
# stegseek --crack image.jpg wordlist.txt -xf output.txt
# 速度差距约 4-5 个数量级
```

#### 4.6.2 stegcracker：Steghide 爆破备选

```bash
# 安装
pip3 install stegcracker
# 或：sudo apt install stegcracker

# 基本用法
stegcracker image.jpg /usr/share/wordlists/rockyou.txt

# 输出：
# [+] Password found: xxx
# [+] Extracted data to: image.jpg.out

# 注意：stegcracker 底层是逐次调用 steghide，速度远慢于 stegseek
# 推荐优先用 stegseek，stegcracker 作为 stegseek 不可用时的备选
```

#### 4.6.3 stegbrute：多线程 Rust 爆破工具

stegbrute 用 Rust 编写，支持多线程并行调用 Steghide，速度比 stegcracker 快，但不如 Stegseek（因为底层仍是逐次调用 steghide，只是多了并行）。

```bash
# 安装（需先装 Rust + cargo）
cargo install stegbrute

# 或下载 deb 包
wget https://github.com/R4yGM/stegbrute/releases/download/0.1.1/stegbrute_0.1.1_amd64.deb
sudo dpkg --install stegbrute_0.1.1_amd64.deb

# 基本爆破
stegbrute -f image.jpg -w /usr/share/wordlists/rockyou.txt

# 指定线程数（默认 3）
stegbrute -f image.jpg -w rockyou.txt -t 8

# 指定提取结果输出文件
stegbrute -f image.jpg -w rockyou.txt -x output.txt

# 详细模式（显示每次尝试）
stegbrute -f image.jpg -w rockyou.txt -v

# Docker 方式运行
docker pull r4yan/stegbrute:latest
docker run -v $(pwd):/stegbrute_data -it r4yan/stegbrute -f /stegbrute_data/image.jpg -w /stegbrute_data/rockyou.txt

# 速度对比：
# stegseek  → 秒级百万次（直接验证密码，最快）
# stegbrute → 多线程并行调用 steghide（中等，依赖线程数）
# stegcracker → 单线程逐次调用 steghide（最慢）
```

#### 4.6.4 Stegbreak + Stegdetect：JPHide 检测与爆破

Stegdetect 用于检测 JPEG 图片是否使用了 JPHide / Outguess / JSteg 等隐写，Stegbreak 是配套的密码爆破工具。

```bash
# 安装
sudo apt install stegdetect

# Stegdetect：检测隐写方式
stegdetect image.jpg
# 输出示例：
#   image.jpg: jphide(***%)    ← 用了 JPHide
#   image.jpg: outguess(***%)  ← 用了 Outguess
#   image.jpg: jsteg(***%)     ← 用了 JSteg

# 调整检测灵敏度（默认 1，越大越敏感）
stegdetect -t 20 image.jpg

# Stegbreak：对检测到的隐写方式爆破密码
stegbreak -t p image.jpg
# -t p: 只试 JPHide（默认）
# -t j: 只试 JSteg
# -t o: 只试 Outguess

# 使用字典爆破
stegbreak -f wordlist.txt -t p image.jpg

# 批量检测目录下所有 JPEG
stegdetect -t 10 ./images/*.jpg
```

#### 4.6.5 stego-toolkit：Docker 一站式隐写工具集

stego-toolkit 是一个 Docker 镜像，预装了 Steghide、Outguess、F5、JPHide、openstego 等几乎所有隐写工具，并提供了自动检测和爆破脚本。

```bash
# 拉取镜像
docker pull dominicbreuker/stego-toolkit

# 运行容器（把当前目录挂载到 /data）
docker run -it -v $(pwd):/data dominicbreuker/stego-toolkit /bin/bash

# 容器内可用的自动检测脚本
check_jpg.sh image.jpg     # JPG 快速检测报告
check_png.sh image.png     # PNG 快速检测报告
check_wav.sh audio.wav     # WAV 快速检测报告

# 自动爆破：遍历多种隐写工具 + 字典
brute_jpg.sh image.jpg wordlist.txt
# 会自动尝试 steghide / outguess / jphide / f5 等所有工具

# GUI 工具（需要 X11 或 VNC）
start_vnc.sh    # 启动 VNC 服务，浏览器访问容器桌面
start_ssh.sh    # 启动 SSH，支持 X11 转发
```

**stego-toolkit 的价值**：不确定图片用了哪种隐写工具时，`brute_jpg.sh` 会自动遍历所有工具尝试爆破，省去逐个猜测的时间。

#### 4.6.6 通用隐写爆破脚本

对于没有专用爆破工具的隐写方式（Outguess、F5、openstego 等），需要自己写脚本循环调用提取命令：

```python
#!/usr/bin/env python3
"""
通用隐写密码爆破脚本
支持: steghide / outguess / f5 / openstego
用法: python3 stego_brute.py <image> <wordlist> <tool>
示例: python3 stego_brute.py image.jpg rockyou.txt steghide
"""

import subprocess
import sys

TOOL_CMDS = {
    'steghide': {
        'extract': ['steghide', 'extract', '-sf', '{file}', '-p', '{pw}', '-f'],
        'success': b'wrote extracted data',
    },
    'outguess': {
        'extract': ['outguess', '-k', '{pw}', '-r', '{file}', 'output.txt'],
        'success': b'Written output',
    },
    'f5': {
        # F5 提取需要 Java 环境
        'extract': ['java', 'Extract', '{file}', '-p', '{pw}'],
        'success': b'Writing',
    },
    'openstego': {
        'extract': ['openstego', 'extract', '-a', 'randomlsb', '-i', '{file}', '-p', '{pw}', '-x', 'output.txt'],
        'success': b'Extracted',
    },
}

def brute_stego(filepath, wordlist, tool_name):
    if tool_name not in TOOL_CMDS:
        print(f"[-] 不支持的工具: {tool_name}")
        print(f"    支持列表: {', '.join(TOOL_CMDS.keys())}")
        return

    cfg = TOOL_CMDS[tool_name]
    cmd_template = cfg['extract']
    success_marker = cfg['success']

    total = 0
    with open(wordlist, 'rb') as f:
        for line in f:
            total += 1

    with open(wordlist, 'rb') as f:
        for i, line in enumerate(f):
            pw = line.decode('utf-8', errors='ignore').strip()
            if not pw:
                continue

            cmd = [c.format(file=filepath, pw=pw) for c in cmd_template]
            result = subprocess.run(cmd, capture_output=True, timeout=10)

            if success_marker in result.stdout or success_marker in result.stderr:
                print(f"\n[+] 密码找到: {pw}")
                print(f"[+] 进度: {i+1}/{total}")
                return pw

            if (i + 1) % 1000 == 0:
                print(f"\r[*] 已尝试 {i+1}/{total} ...", end='', flush=True)

    print(f"\n[-] 密码未找到（共尝试 {total} 个）")
    return None

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(f"用法: {sys.argv[0]} <image> <wordlist> <tool>")
        print(f"tool: {', '.join(TOOL_CMDS.keys())}")
        sys.exit(1)
    brute_stego(sys.argv[1], sys.argv[2], sys.argv[3])
```

#### 4.6.7 字典制作技巧

隐写爆破的效率取决于字典质量。CTF 常见密码模式：

```bash
# 1. 常见弱口令字典
# Kali 自带: /usr/share/wordlists/rockyou.txt（1400万条）
# SecLists 项目: https://github.com/danielmiessler/SecLists
git clone https://github.com/danielmiessler/SecLists ~/SecLists

# 2. 纯数字字典（题目提示"6位纯数字"）
crunch 6 6 0123456789 -o 6digit.txt
# 4位: crunch 4 4 0123456789 -o 4digit.txt

# 3. 字母+数字组合
crunch 4 4 abcdefghijklmnopqrstuvwxyz0123456789 -o alnum4.txt

# 4. CTF 常见密码模式
# 很多题目密码就是文件名、题目标题、选手用户名等
echo -e "flag\nctf\nadmin\npassword\n123456\nqwerty\nctf2024\npwn\nmisc" > ctf_common.txt
# 动态生成包含题目标题的字典
echo "题目名称" | awk '{for(i=1;i<=9999;i++) print $1 i}' > title_nums.txt

# 5. 基于已知信息定制字典
# 如果题目描述提到"密码是我的名字"
# 生成常见姓名+数字组合
cat names.txt | awk '{for(i=0;i<=9999;i++) print $1 i}' > name_nums.txt

# 6. crunch 高级用法
# 指定模式：4位字母+2位数字
crunch 6 6 -t @@@@%% -o pattern.txt
# @ = 小写字母, , = 大写字母, % = 数字, ^ = 特殊字符

# 掩码爆破（类似 hashcat 掩码）
# 已知密码格式为 abcXXX（3字母+3数字）
crunch 6 6 -t abc%%% -o mask.txt
```

---

## 五、流量分析

> 完整 Wireshark 过滤器语法、文件还原、USB 取证、tshark 批处理见 [Wireshark 实战使用指南](Wireshark实战使用指南.md)。高级抓包、TLS/无线深度解析、网络取证工作流、Lua 解析器、自动化流水线见 [Wireshark 深度使用手册](Wireshark深度使用手册.md)。

### 5.1 流量分析题型分类

| 题型 | 特征 | 核心操作 |
|------|------|----------|
| HTTP 文件传输 | 有 GET/POST 请求 | Export Objects 还原文件 |
| TCP 逆向 Shell | 端口 4444/1234 等非常规 | Follow TCP Stream 看交互 |
| DNS 隐写 | 异常 DNS 查询 | 提取域名/子域名中的数据 |
| ICMP 隐写 | ICMP payload 非常规 | 提取 data 字段 |
| USB 键鼠取证 | USB HID 设备 | 提取键鼠数据还原操作 |
| TLS 加密流量 | 有密钥文件 | 配置密钥解密后分析 |
| 协议漏洞利用 | 异常报文 | 分析攻击 payload |

### 5.2 HTTP 流量还原文件

```bash
# Wireshark：File → Export Objects → HTTP
# 列出所有 HTTP 传输的文件，可逐个保存

# tshark 命令行批量提取
tshark -r capture.pcap --export-objects http,./exported/

# 提取 POST 请求的 body
tshark -r capture.pcap -Y "http.request.method==POST" -T fields -e http.file_data

# 提取 HTTP 响应中的文件
tshark -r capture.pcap -Y "http.response" -T fields -e http.content_type -e http.content_length
```

### 5.3 DNS 隐写提取

```bash
# DNS 隐写：把数据编码进 DNS 查询的域名中
# 例如：flagxxx.example.com → 子域名部分就是数据

# 提取所有 DNS 查询域名
tshark -r capture.pcap -Y "dns.qry.name" -T fields -e dns.qry.name

# 过滤特定域名模式
tshark -r capture.pcap -Y "dns.qry.name contains \"flag\"" -T fields -e dns.qry.name

# 提取后用 CyberChef 解码（域名常做 Hex/Base32 编码）
```

### 5.4 ICMP 隐写提取

```bash
# ICMP 隐写：把数据藏进 ICMP Echo Request/Reply 的 payload

# 提取 ICMP data
tshark -r capture.pcap -Y "icmp.type==8" -T fields -e data

# 提取并拼接
tshark -r capture.pcap -Y "icmp.type==8" -T fields -e data | tr -d '\n' | xxd -r -p > icmp_data.bin

# 查看内容
file icmp_data.bin
strings icmp_data.bin
```

### 5.5 USB 键鼠取证

```python
#!/usr/bin/env python3
"""USB 键盘流量还原——提取按键数据还原输入内容"""

# USB HID 键盘数据格式：每包 8 字节
# Byte 0: 修饰键 (Shift/Ctrl/Alt)
# Byte 2: 按键码 (HID Usage ID)

# HID 键码映射表（美式键盘，部分）
HID_KEY_MAP = {
    0x04:'a', 0x05:'b', 0x06:'c', 0x07:'d', 0x08:'e', 0x09:'f',
    0x0A:'g', 0x0B:'h', 0x0C:'i', 0x0D:'j', 0x0E:'k', 0x0F:'l',
    0x10:'m', 0x11:'n', 0x12:'o', 0x13:'p', 0x14:'q', 0x15:'r',
    0x16:'s', 0x17:'t', 0x18:'u', 0x19:'v', 0x1A:'w', 0x1B:'x',
    0x1C:'y', 0x1D:'z', 0x1E:'1', 0x1F:'2', 0x20:'3', 0x21:'4',
    0x22:'5', 0x23:'6', 0x24:'7', 0x25:'8', 0x26:'9', 0x27:'0',
    0x28:'\n', 0x2C:' ', 0x2D:'-', 0x2E:'=', 0x2F:'[', 0x30:']',
    0x33:';', 0x34:"'", 0x36:',', 0x37:'.', 0x38:'/',
    # Shift 修饰后的映射需额外处理
}

def decode_usb_keyboard(pcap_file):
    """用 tshark 提取 USB HID 数据并还原按键"""
    import subprocess
    result = subprocess.run(
        ['tshark', '-r', pcap_file, '-Y', 'usb.capdata',
         '-T', 'fields', '-e', 'usb.capdata'],
        capture_output=True, text=True
    )

    text = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        # 解析 hex 数据
        raw = bytes.fromhex(line.replace(':', ''))
        if len(raw) >= 8:
            modifier = raw[0]
            key_code = raw[2]
            if key_code == 0:
                continue  # 释放事件
            char = HID_KEY_MAP.get(key_code, '?')
            if modifier & 0x22:  # Shift 按下
                char = char.upper() if char.isalpha() else char
            text.append(char)

    print(''.join(text))
```

### 5.6 Wireshark 高效分析工作流

```text
Step 1: 快速概览
  - Statistics → Summary：看总包数、协议分布
  - Statistics → Protocol Hierarchy：看有哪些协议
  - 看有没有 HTTP/DNS/USB 等明显异常

Step 2: 定位异常
  - 按协议过滤：http / dns / icmp / usb
  - 按内容搜索：Edit → Find Packet → String "flag"
  - 按端口过滤：tcp.port == 4444

Step 3: 深入分析
  - Follow TCP/UDP Stream 看完整会话
  - Export Objects 还原文件
  - USB 流量用 tshark 提取

Step 4: 数据提取
  - tshark -T fields 批量提取特定字段
  - 提取后用 CyberChef/Python 进一步处理
```

---

## 六、压缩包取证

### 6.1 ZIP 伪加密

**原理**：ZIP 文件有两个地方记录加密标志——本地文件头和中央目录头。出题人只修改中央目录的加密标志位，使解压软件要求输入密码，但数据实际未加密。

```text
ZIP 本地文件头结构：
  偏移 0: PK\x03\x04（签名 4B）
  偏移 6: 通用位标志（2B）→ bit0 = 加密标志
  ...

ZIP 中央目录头结构：
  偏移 0: PK\x01\x02（签名 4B）
  偏移 8: 通用位标志（2B）→ bit0 = 加密标志
  ...

伪加密特征：
  - 本地文件头的加密位 = 0（数据未加密）
  - 中央目录头的加密位 = 1（声称加密）
  → 把中央目录加密位改为 0 即可解压
```

**修复方法**：

```bash
# 方法1：010 Editor 手动修改
# 找到 PK\x01\x02 → 偏移 8 处的通用位标志
# bit0 = 1 → 改为 0

# 方法2：Python 脚本自动修复（见 CTF主文档 2.4 节脚本）

# 方法3：binwalk 提取绕过
binwalk -e file.zip    # 直接 carving，不管 ZIP 头
```

### 6.2 ZIP 密码爆破

```bash
# fcrackzip（轻量，CPU）
fcrackzip -u -l 1-6 -c a file.zip          # 纯字母 1-6 位
fcrackzip -u -D -p /usr/share/wordlists/rockyou.txt file.zip  # 字典
fcrackzip -u -b -l 4-4 -c aA1 file.zip     # 字母+数字 4 位暴力

# John the Ripper（通用哈希破解，也支持 ZIP）
zip2john file.zip > hash.txt
john --wordlist=rockyou.txt hash.txt

# ARCHPR（Windows GUI，高级选项更多）
# 掩码攻击、明文攻击、字典攻击都支持
```

### 6.3 CRC32 爆破

**原理**：ZIP 内容被加密但 CRC32 校验值未加密。如果加密内容很短（如 4-6 字节），CRC32 可以唯一反推原文。

```python
#!/usr/bin/env python3
"""CRC32 爆破——短内容 ZIP 加密"""

import zipfile
import zlib
import struct
import string
import itertools

def crc32_bruteforce(zip_path):
    zf = zipfile.ZipFile(zip_path)

    for info in zf.infolist():
        crc = info.CRC
        size = info.file_size
        print(f"[*] {info.filename}: CRC=0x{crc:08x}, size={size}")

        if size <= 6:  # 只对短内容爆破
            print(f"[*] 尝试爆破 {info.filename}（{size} 字节）...")
            charset = string.printable.strip()

            for combo in itertools.product(charset, repeat=size):
                data = ''.join(combo).encode()
                if zlib.crc32(data) & 0xFFFFFFFF == crc:
                    print(f"[+] 找到: {info.filename} = {data.decode()}")
                    break

if __name__ == '__main__':
    crc32_bruteforce(sys.argv[1])
```

### 6.4 明文攻击

**原理**：已知 ZIP 中某个文件的明文内容（如 `README.txt` = `This is a readme`），利用已知明文+对应密文推导加密密钥，再解密其他文件。

```bash
# bkcrack（明文攻击工具，替代已停止维护的 PKCrack）
# 安装：https://github.com/kimci86/bkcrack

# Step 1: 准备明文文件（已知内容）
echo -n "known plaintext" > plain.txt

# Step 2: 执行明文攻击
bkcrack -C encrypted.zip -c known.txt -p plain.txt

# Step 3: 用恢复的密钥解密
bkcrack -C encrypted.zip -c known.txt -k KEY1 KEY2 KEY3 -d decrypted.zip

# 注意：明文至少需要 12 字节才能唯一确定密钥
```

### 6.5 嵌套压缩包

```bash
# 递归解压（常见套路：zip 套 zip 套 zip...）
# 方法1：脚本循环解压
#!/bin/bash
while [ -f *.zip ]; do
    unzip -o -P password *.zip 2>/dev/null || unzip -o *.zip
    rm *.zip
done

# 方法2：binwalk 递归提取
binwalk -eM file.zip

# 常见嵌套模式：
# zip → zip → zip → ... → flag.txt（每层可能有密码）
# zip → tar.gz → 7z → rar → flag.txt（不同压缩格式混用）
```

---

## 七、文件分析与修复

### 7.1 文件魔数（Magic Number）全表

```text
=== 图片 ===
PNG:    89 50 4E 47 0D 0A 1A 0A          结尾: 00 00 00 00 49 45 4E 44 AE 42 60 82  (IEND chunk)
JPEG:   FF D8 FF (E0/E1/E2...)           结尾: FF D9
GIF87a: 47 49 46 38 37 61                结尾: 3B  (分号)
GIF89a: 47 49 46 38 39 61                结尾: 3B  (分号)
BMP:    42 4D                            结尾: 无固定结尾
WebP:   52 49 46 46 .. .. .. .. 57 45 42 50  结尾: 无固定结尾
ICO:    00 00 01 00                       结尾: 无固定结尾
TIFF-LE:49 49 2A 00                       结尾: 无固定结尾
TIFF-BE:4D 4D 00 2A                       结尾: 无固定结尾
PSD:    38 42 50 53                       结尾: 无固定结尾

=== 压缩 ===
ZIP:    50 4B 03 04                       结尾: 50 4B 05 06 .. .. .. .. .. .. .. .. .. .. .. ..  (EOCD,22字节)
GZIP:   1F 8B                             结尾: 无固定结尾
RAR:    52 61 72 21 1A 07                 结尾: C4 3D 7B 00 40 07 00  (RAR4 结束块)
7z:     37 7A BC AF 27 1C                 结尾: 无固定结尾（尾部元数据可变）
XZ:     FD 37 7A 58 5A 00                 结尾: 59 5A  (YZ)
BZ2:    42 5A 68                          结尾: 无固定结尾
TAR:    无文件头（靠 512 字节块结构识别）       结尾: 00 * 1024  (两个全零块)
CAB:    4D 53 43 46 00 00 00 00           结尾: 无固定结尾

=== 文档 ===
PDF:    25 50 44 46                       结尾: 25 25 45 4F 46 0A  (%%EOF\n)
DOC/XLS/PPT:  D0 CF 11 E0 A1 B1 1A E1   结尾: 无固定结尾  (OLE2/CFB)
DOCX/PPTX/XLSX: 50 4B 03 04              结尾: 50 4B 05 06 .. .. .. ..  (实际是 ZIP)
RTF:    7B 5C 72 74 66 31                结尾: 7D  (右花括号)

=== 可执行 ===
ELF:    7F 45 4C 46                       结尾: 无固定结尾
PE:     4D 5A  (MZ)                       结尾: 无固定结尾
Mach-O: FE ED FA CE / CE FA ED BE / CA FE BA BE  结尾: 无固定结尾
DEX:    64 65 78 0A 30 33 35 00           结尾: 无固定结尾  (Android DEX)
CLASS:  CA FE BA BE                       结尾: 无固定结尾  (Java 字节码)

=== 音频/视频 ===
WAV:    52 49 46 46 .. .. .. .. 57 41 56 45  结尾: 无固定结尾
FLAC:   66 4C 61 43                       结尾: 无固定结尾
MP3-ID3:49 44 33                          结尾: FF FB/FF FC/FF F2/FF F3 帧后无固定结尾
OGG:    4F 67 67 53                       结尾: 4F 67 67 53 .. .. .. .. .. 04  (最后一页标志位 bit0=1)
MP4:    .. .. .. .. 66 74 79 70           结尾: 无固定结尾  (ftyp box)
AVI:    52 49 46 46 .. .. .. .. 41 56 49 20  结尾: 无固定结尾
FLV:    46 4C 56 01                       结尾: 46 4C 56 00 00 00 09  (上一个 tag 长度)
MKV:    1A 45 DF A3                       结尾: 无固定结尾  (EBML 头)
MIDI:   4D 54 68 64                       结尾: 无固定结尾

=== 数据库 ===
SQLite: 53 51 4C 69 74 65 20 66 6F 72 6D 61 74 20 33 00  结尾: 无固定结尾
```

### 7.2 文件头修复

```bash
# 最常见的 Misc 题型：文件头被破坏

# Step 1: 识别问题
file damaged.png     # 输出 "data"（不识别为 PNG）
xxd damaged.png | head -5  # 看头部字节

# Step 2: 对比正确文件头
# PNG 正确头：89 50 4E 47 0D 0A 1A 0A
# 当前头部：  00 00 00 00 0D 0A 1A 0A（前4字节被清零）

# Step 3: 修复（方法任选一种）

# 方法1：printf + dd
printf '\x89\x50\x4e\x47' | dd of=damaged.png bs=1 count=4 conv=notrunc

# 方法2：Python
python3 -c "
data = open('damaged.png','rb').read()
data = b'\x89PNG\r\n\x1a\n' + data[8:]
open('fixed.png','wb').write(data)
"

# 方法3：010 Editor（可视化，推荐）
# 打开文件 → 手动修改前 8 字节 → 保存

# Step 4: 验证
file fixed.png       # 应输出 "PNG image data"
```

### 7.3 图片高度修复

```text
常见套路：PNG 图片高度被改小，flag 在图片下方被裁掉

修复步骤（010 Editor）：
1. 打开 PNG → 自动应用模板，看到 IHDR 结构
2. 找到 height 字段 → 改大（如 200 → 500）
3. 保存 → 图片下方露出隐藏内容

修复步骤（Python）：
```

```python
#!/usr/bin/env python3
"""修改 PNG 高度"""
import struct
import sys

def change_png_height(filepath, new_height, output=None):
    output = output or filepath.replace('.png', '_tall.png')
    with open(filepath, 'rb') as f:
        data = bytearray(f.read())

    # 修改 IHDR 高度（偏移 0x14-0x17，大端序）
    struct.pack_into('>I', data, 0x14, new_height)
    # 注意：CRC 会不匹配，但大多数看图软件仍能显示

    with open(output, 'wb') as f:
        f.write(data)
    print(f"[+] 高度改为 {new_height}，输出: {output}")

# 不知道正确高度？逐个尝试
for h in range(200, 2000, 100):
    change_png_height('image.png', h)
    # 手动检查每张图
```

### 7.4 binwalk 深度使用

> binwalk 基础用法见 CTF 主文档 2.10 节。本节补充进阶技巧。

```bash
# 自定义签名扫描
# binwalk 的签名数据库在 /etc/binwalk/magic.bin
# 可追加自定义签名

# 手动指定提取签名
binwalk -D='png:image/png' file.bin       # 只提取 PNG
binwalk -D='zip:application/zip' file.bin  # 只提取 ZIP

# 提取所有（不管签名类型）
binwalk -D='.*:application/octet-stream' file.bin

# 指定扫描起始偏移
binwalk -s 0x1000 file.bin                # 从 0x1000 开始扫描

# 限制扫描长度
binwalk -l 0x10000 file.bin               # 只扫前 64KB

# 组合：从特定偏移提取特定类型
binwalk -s 0x200 -D='zlib:application/x-zlib' file.bin

# 提取后的 zlib 解压
python3 -c "import zlib; open('out','wb').write(zlib.decompress(open('extracted','rb').read()))"
```

---

## 八、多媒体隐写

### 8.1 音频隐写分类

| 手法 | 原理 | 检测方法 |
|------|------|----------|
| 频谱图藏字 | 把文字转高频信号 | Audacity 切换频谱图查看 |
| 摩尔斯电码 | 长短脉冲编码 | Audacity 波形识别 |
| DTMF | 双音多频拨号音 | multimon-ng 解码 |
| SSTV | 慢扫描电视，图片转音频 | qsstv / rx-sstv 解码 |
| LSB 隐写 | 修改采样点最低位 | silenteye / 自写脚本 |
| 双声道差异 | 左右声道藏不同数据 | Audacity 拆分对比 |
| 隐藏音轨 | 人耳不可听范围藏数据 | 频谱图看超低/超高频 |

### 8.2 Audacity 深度操作

```text
=== 频谱图查看（最常用） ===
1. 打开音频文件
2. 左侧轨道标题下拉 → 切换为"频谱图"(Spectrogram)
3. 高频区域可能出现文字/二维码
4. 拖动选区放大看细节
5. 调整频谱窗口大小：Edit → Preferences → Spectrogram → Window Size
   - 值越大频率分辨率越高，时间分辨率越低
   - 推荐先 1024 看，再 4096 看细节

=== 摩尔斯电码 ===
1. 波形图中：宽脉冲 = 嗒(-)，窄脉冲 = 滴(.)
2. 放大波形逐段识别
3. 或用工具自动解码：multimon-ng -t wav -a MORSE_CW file.wav

=== 双声道操作 ===
1. 拆分立体声：轨道下拉 → Split Stereo to Mono
2. 分别看两个声道
3. 两声道做差/做 XOR 可能出现隐藏信息

=== 速度/反向 ===
1. 效果 → 改变速度（变速不变调）→ 拉慢看细节
2. 效果 → 反向 → 反转播放（有时 flag 是反着藏的）
```

### 8.3 SSTV 解码

```bash
# SSTV（慢扫描电视）把图片编码为音频信号
# 常见模式：Robot36、Scottie S1/S2、Martin M1/M2

# 方法1：qsstv（Linux GUI）
qsstv
# → 打开音频文件 → 自动检测模式 → 解码出图片

# 方法2：rx-sstv（命令行）
# 安装：pip install rx-sstv
# 需要配合 pulseaudio/alsa
rx-sstv file.wav

# 方法3：在线工具
# https://www.sstv.at/hab/sstvweb/decoder.html

# 常见坑：
# - 需要正确选择 SSTV 模式（Robot36 最常见）
# - 音频采样率需要匹配
# - 解码图片可能需要调对比度
```

### 8.4 DTMF 解码

```bash
# DTMF（双音多频）= 电话拨号音
# 每个按键由两个频率叠加表示

# multimon-ng（多协议解码器）
# 安装：sudo apt install multimon-ng
multimon-ng -t wav -a DTMF file.wav

# 输出示例：DTMF: 1 DTMF: 8 DTMF: 0 DTMF: 0 ...
# 拼起来就是拨号号码

# DTMF 频率对照表：
#        1209  1336  1477  1633
#  697    1     2     3     A
#  770    4     5     6     B
#  852    7     8     9     C
#  941    *     0     #     D
```

### 8.5 视频隐写

```bash
# 视频隐写常见手法：
# 1. 逐帧提取 → 某帧藏 flag
# 2. 视频附加数据（文件末尾）
# 3. 视频流中的异常帧

# 逐帧提取（ffmpeg）
ffmpeg -i video.mp4 frames/%04d.png

# 查看帧数
ffprobe -v error -count_frames -select_streams v:0 \
  -show_entries stream=nb_read_frames -of csv=p=0 video.mp4

# 检查视频末尾附加数据
binwalk video.mp4
strings video.mp4 | grep -i flag

# GIF 逐帧查看
# StegSolve → Analyse → Frame Browser
# 或：convert gif:animation.gif frames/frame%03d.png（ImageMagick）
```

---

## 九、内存取证

### 9.1 Volatility3 使用

```bash
# Volatility3（Python3 重写版）
# 安装：pip install volatility3

# Step 1: 识别系统 Profile
vol -f memory.dmp windows.info.Info

# Step 2: 常用插件
# 进程列表
vol -f memory.dmp windows.pslist.PsList

# 进程树（看父子关系）
vol -f memory.dmp windows.pstree.PsTree

# 查找可疑进程（cmd.exe、powershell.exe、nc.exe...）
vol -f memory.dmp windows.pslist.PsList | grep -iE "cmd|powershell|nc|meterpreter"

# Step 3: 文件提取
# 列出文件
vol -f memory.dmp windows.filescan.FileScan

# 搜索含 flag 的文件
vol -f memory.dmp windows.filescan.FileScan | grep -i flag

# 提取文件（需要虚拟地址）
vol -f memory.dmp windows.dumpfiles.DumpFiles --virtaddr 0xXXXX

# Step 4: 注册表
vol -f memory.dmp windows.registry.hivelist.HiveList
vol -f memory.dmp windows.registry.printkey.PrintKey --key "Software\Microsoft\Windows\CurrentVersion\Run"

# Step 5: 命令历史
vol -f memory.dmp windows.cmdline.CmdLine

# Step 6: 网络连接
vol -f memory.dmp windows.netscan.NetScan
```

### 9.2 内存取证常见套路

```text
1. 找到可疑进程 → dump 该进程内存 → strings 找 flag
2. 找到可疑文件 → dump 该文件 → 分析
3. 命令历史 → 看执行了什么命令
4. 注册表 → 看自启动项/用户密码哈希
5. 剪贴板 → 看复制了什么内容
6. TrueCrypt/VeraCrypt 卷 → 挂载解密
```

---

## 十、OSINT 与社会工程

### 10.1 EXIF 信息利用

```bash
# 图片 EXIF 可能包含：
# - GPS 坐标 → 定位拍摄地点
# - 时间戳 → 确定事件时间
# - 设备型号 → 确定拍摄设备
# - 软件/作者 → 藏 flag

exiftool photo.jpg

# GPS 坐标定位
exiftool -n -gpslatitude -gpslongitude photo.jpg
# 输出经纬度 → Google Maps 定位
```

### 10.2 图片反查

```text
# 反向图片搜索（找图片来源/原图）
# Google Images: https://images.google.com
# TinEye: https://tineye.com
# 百度识图: https://graph.baidu.com
# Yandex: https://yandex.com/images/

# 社交媒体图片去元数据后仍可能通过视觉特征溯源
```

### 10.3 社交媒体溯源

```text
# 常见 OSINT 题型：
# 1. 给一张照片 → 找拍摄地点（GPS/地标/街景）
# 2. 给用户名 → 找该用户的社交账号
# 3. 给邮箱 → 找关联账号/泄露数据
# 4. 给域名/IP → Whois/反查/历史记录

# 工具：
# Sherlock：用户名批量查社交媒体
#   sherlock username
# theHarvester：邮箱/域名信息收集
#   theHarvester -d example.com -b google
# Whois：域名注册信息
#   whois example.com
```

---

## 十一、脚本与自动化

### 11.1 万能解码脚本

```python
#!/usr/bin/env python3
"""
CTF Misc 万能解码器
自动尝试常见编码/加密，支持多层嵌套探测
"""

import base64
import urllib.parse
import codecs
import re
import zlib
import sys

def try_all_decodes(s, depth=0, max_depth=5):
    """递归尝试所有解码方式"""
    if depth >= max_depth:
        return

    results = []

    # Base64
    try:
        d = base64.b64decode(s).decode('utf-8', errors='ignore')
        if d and any(c.isprintable() for c in d):
            results.append(('Base64', d))
    except: pass

    # Base32
    try:
        padded = s + '=' * ((8 - len(s) % 8) % 8)
        d = base64.b32decode(padded).decode('utf-8', errors='ignore')
        if d and any(c.isprintable() for c in d):
            results.append(('Base32', d))
    except: pass

    # Hex
    try:
        d = bytes.fromhex(s).decode('utf-8', errors='ignore')
        if d and any(c.isprintable() for c in d):
            results.append(('Hex', d))
    except: pass

    # URL
    if '%' in s:
        try:
            d = urllib.parse.unquote(s)
            if d != s:
                results.append(('URL', d))
        except: pass

    # ROT13
    try:
        d = codecs.decode(s, 'rot_13')
        if d != s and any(c.isalpha() for c in d):
            results.append(('ROT13', d))
    except: pass

    # Zlib
    try:
        d = zlib.decompress(bytes.fromhex(s) if all(c in '0123456789abcdefABCDEF' for c in s) else s.encode()).decode('utf-8', errors='ignore')
        if d:
            results.append(('Zlib', d))
    except: pass

    for method, decoded in results:
        prefix = "  " * depth
        print(f"{prefix}[{method}] → {decoded[:100]}")
        if 'flag' in decoded.lower():
            print(f"{prefix}*** 找到 FLAG: {decoded} ***")
        else:
            try_all_decodes(decoded.strip(), depth + 1, max_depth)

if __name__ == '__main__':
    data = sys.argv[1] if len(sys.argv) > 1 else input("输入: ")
    try_all_decodes(data.strip())
```

### 11.2 文件分析自动化

```bash
#!/bin/bash
# Misc 文件一键分析脚本

FILE=$1

echo "=== file ==="
file "$FILE"

echo -e "\n=== exiftool ==="
exiftool "$FILE" 2>/dev/null || echo "exiftool not available"

echo -e "\n=== binwalk ==="
binwalk "$FILE"

echo -e "\n=== strings (搜索flag) ==="
strings "$FILE" | grep -iE "flag\{|ctf\{|key\{"

echo -e "\n=== 头部 hex ==="
xxd "$FILE" | head -5

echo -e "\n=== 文件大小 ==="
ls -la "$FILE"
```

---

## 十二、实战组合场景

> 真实 CTF 题目往往组合多种手法，以下还原典型组合题的解题过程。

### 场景1：图片藏压缩包

```text
题目：给一张 PNG 图片

解题过程：
1. file image.png → 确认是 PNG
2. binwalk image.png → 发现末尾有 ZIP 签名
3. binwalk -e image.png → 提取出 secret.zip
4. unzip secret.zip → 要求密码
5. fcrackzip -u -D -p rockyou.txt secret.zip → 爆破密码
6. 解压得到 flag.txt
```

### 场景2：流量分析 + 文件提取 + 隐写

```text
题目：给一个 pcap 文件

解题过程：
1. Wireshark 打开 → Protocol Hierarchy → 有 HTTP 和 DNS
2. DNS 查询中域名异常 → tshark 提取 → 解码得到密码提示
3. HTTP Export Objects → 提取出一张 PNG
4. binwalk PNG → 末尾有加密 ZIP
5. 用 DNS 提取的密码解压 ZIP → 得到 flag
```

### 场景3：音频隐写 + 编码嵌套

```text
题目：给一个 WAV 文件

解题过程：
1. Audacity 打开 → 频谱图看到摩尔斯电码
2. 手动识别摩尔斯 → 解码得到 Base64 字符串
3. CyberChef: From Base64 → From Hex → 得到 flag
```

### 场景4：内存取证 + 加密文件

```text
题目：给一个内存镜像 + 加密 ZIP

解题过程：
1. Volatility: pslist → 发现 notepad.exe 在运行
2. Volatility: memdump → dump notepad 内存
3. strings dump | grep -i "password" → 找到 ZIP 密码
4. 用密码解压 ZIP → 得到 flag
```

### 场景5：GIF 逐帧 + 图片拼接

```text
题目：给一个 GIF 动图

解题过程：
1. ffmpeg -i animation.gif frames/%04d.png → 逐帧提取
2. 发现每帧都是二维码的一小块
3. Python 拼接所有帧 → 完整二维码
4. 扫描二维码 → 得到 flag
```

### 场景6：PDF 隐写

```text
题目：给一个 PDF 文件

解题过程：
1. pdfinfo document.pdf → 查看属性（可能在 Author/Subject 藏 flag）
2. pdftotext document.pdf - → 提取文本
3. binwalk document.pdf → 发现内嵌文件
4. strings document.pdf | grep -i flag
5. 或：PDF 白字隐写（文字颜色和背景同色）→ 全选复制到记事本
```

---

## 十三、常见陷阱与排查

### 13.1 解题 Checklist

```text
拿到题目后的标准流程：

□ 查看题目描述和提示（hint 经常直接告诉你方向）
□ 文件类型识别：file 命令
□ 如果是文本 → 直接尝试解码
□ 如果是文件 → 检查文件头是否正确
□ 元数据检查：exiftool
□ 搜索明文：strings | grep -i flag
□ 隐藏内容扫描：binwalk
□ 十六进制查看：xxd | head / xxd | tail
□ 根据文件类型深入分析（图片/音频/压缩包/流量...）
```

### 13.2 常见坑

| 坑 | 表现 | 解决 |
|----|------|------|
| 文件头被改 | `file` 输出 `data` | 对比正确魔数，手动修复 |
| 多层套娃 | 解一层还有一层 | 逐层剥，或写循环脚本 |
| 伪加密 | ZIP 要求密码但其实是伪加密 | 修改加密标志位 |
| LSB 顺序 | zsteg 默认顺序不对 | 尝试不同通道和遍历顺序 |
| 图片高度裁剪 | 图片下方被截 | 修改 IHDR 高度 |
| 盲水印 | 一张图看不出 | 需要原图做差 |
| 频谱图窗口 | Audacity 看不清 | 调整频谱窗口大小 |
| 字符编码 | UTF-8/GBK/GB2312 | Python decode 指定编码 |
| 大端小端 | 数据反了 | 尝试两种字节序 |
| ZIP 嵌套密码 | 每层不同密码 | 先找密码来源再解压 |
| 隐写密码保护 | steghide 等要求输入密码 | Stegseek 爆破，或从题目描述猜密码 |
| 字典不对 | 爆破跑完没结果 | 换字典/根据题目提示定制字典 |

### 13.3 工具安装速查

```bash
# Kali Linux（大部分已预装）
sudo apt install binwalk foremost exiftool steghide stegseek john fcrackzip audacity
pip3 install stegano zsteg  # zsteg 需 gem install zsteg（Ruby）

# StegSolve（Java GUI）
# 下载：https://github.com/eugenekolo/stegsolve
java -jar StegSolve.jar

# Volatility3
pip3 install volatility3

# bwmforpy3（盲水印）
pip3 install bwmforpy3

# bkcrack（明文攻击）
# https://github.com/kimci86/bkcrack

# multimon-ng（DTMF/摩尔斯解码）
sudo apt install multimon-ng
```

---

## 十四、速查表

### 按文件类型速查

| 文件类型 | 第一步 | 第二步 | 第三步 |
|----------|--------|--------|--------|
| 纯文本 | 尝试各编码解码 | CyberChef Magic | 递归剥嵌套 |
| PNG/JPG | exiftool | binwalk | zsteg/StegSolve |
| GIF | 逐帧提取 | 拼接/对比 | 搜索隐藏帧 |
| ZIP | 伪加密检测 | 密码爆破 | CRC32/明文攻击 |
| WAV/MP3 | Audacity 频谱图 | 摩尔斯/DTMF | SSTV/LSB |
| PCAP | Wireshark 概览 | 协议过滤 | 文件还原/数据提取 |
| PDF | pdfinfo + pdftotext | binwalk | 白字隐写 |
| 内存镜像 | Volatility info | 进程/文件/命令行 | 提取可疑数据 |
| 未知文件 | file + xxd head | binwalk | strings + grep |

### 核心工具速查

| 工具 | 一句话 | 最常用命令 |
|------|--------|------------|
| CyberChef | 编解码瑞士军刀 | Magic → From Base64 → From Hex |
| binwalk | 文件结构分析 | `binwalk -eM file` |
| zsteg | PNG LSB 检测 | `zsteg -a image.png` |
| StegSolve | 图片隐写 GUI | 逐通道 → Data Extract |
| exiftool | 元数据查看 | `exiftool file` |
| 010 Editor | 十六进制编辑 | 改文件头/高度/加密位 |
| Wireshark | 流量分析 | 过滤 → Follow Stream → Export |
| Audacity | 音频分析 | 频谱图/摩尔斯/双声道 |
| Volatility | 内存取证 | `vol -f dump windows.pslist` |
| fcrackzip | ZIP 爆破 | `fcrackzip -u -D -p dict.txt file.zip` |
| Stegseek | Steghide 隐写爆破 | `stegseek --crack image.jpg rockyou.txt -xf out` |
| foremost | 文件 carving | `foremost -i file -o out/` |

### 编码特征速判

| 特征 | 可能的编码 |
|------|-----------|
| 末尾有 `=`，大小写+数字+`+/` | Base64 |
| 只有大写+`2-7`+`=` | Base32 |
| 只有 `0-9`+`a-fA-F`，偶数长度 | Hex |
| `%` 后跟两位十六进制 | URL 编码 |
| `\u` 后跟 4 位十六进制 | Unicode 转义 |
| 只有 `.` `-` 空格 | Morse |
| 看起来像英文但无意义 | ROT13 |
| 只有 A 和 B，5 位一组 | Bacon |
| Unicode 盲文字符 | Braille |

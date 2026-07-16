#!/usr/bin/env python3
"""
Base 家族编码识别 + 递归自动解码

补充 decode_all.py：
    - Base16 / 32 (RFC 3548 / RFC 4648 / hex) / 64 / 85 (ASCII85 / z85)
    - Base58 (Bitcoin / ripple)
    - Base62
    - Base91
    - UUencode / XXencode
    - URL / HTML 实体 / 转义八进制十六进制
    - 摩尔斯电码（保留作为入口）
    - 嵌套递归自动解码

依赖:
    pip install base58 base65536  (可选, 仅在用了 base65536 时需要)
    base62 / base91 用纯 re 实现，无需依赖

用法:
    python3 base_family.py <编码字符串>
    python3 base_family.py -r <编码字符串>      # 递归自动解码
    python3 base_family.py --type base64 <串>   # 指定类型单次解码
    python3 base_family.py --identify <串>       # 只识别类型

可作为模块使用：
    from base_family import decode_all, identify
"""

import base64
import binascii
import codecs
import html
import re
import string
import sys
import urllib.parse

B58_ALPHABET = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
B58Ripple = b'rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxy'
B62_ALPHABET = string.digits + string.ascii_uppercase + string.ascii_lowercase
B91_ALPHABET = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!#$%&()*+,./:;<=>?@[]^_`{|}~\""


# ----------------------------------------------------------------------
# 编码识别
# ----------------------------------------------------------------------
def _charset(s):
    if not s:
        return set()
    return set(s)


def identify(s):
    """识别编码类型，返回列表（按可能性排序）"""
    s = s.strip()
    hits = []
    chars = _charset(s)

    if re.fullmatch(r'[0-9A-Fa-f]+', s) and len(s) % 2 == 0:
        hits.append('base16')
    if re.fullmatch(r'[A-Z2-7]+={0,6}', s):
        hits.append('base32-rfc4648')
    if re.fullmatch(r'[A-Za-z0-9+/]+={0,2}', s) and len(s) % 4 == 0:
        hits.append('base64')
    if re.fullmatch(r'[A-Za-z0-9\-_]+={0,2}', s) and len(s) % 4 == 0:
        hits.append('base64url')
    if re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]+', s):
        hits.append('base58')
    if chars.issubset(set(B62_ALPHABET)) and s:
        hits.append('base62')
    if chars.issubset(set(B91_ALPHABET)) and s:
        hits.append('base91')
    if '<~' in s and '~>' in s:
        hits.append('ascii85-adobe')
    if re.fullmatch(r'[0-9A-Za-z!#$%&()*+\-./:;<=>?@\[\]^_`{|}~"]+', s):
        hits.append('ascii85-z85')
    if s.startswith('begin ') and 'end' in s:
        hits.append('uuencode')
    if '%' in s and re.search(r'%[0-9A-Fa-f]{2}', s):
        hits.append('url')
    if '&' in s and ';' in s and re.search(r'&#?\d+;|&[a-zA-Z]+;', s):
        hits.append('html-entity')
    if re.fullmatch(r'[.\-/|\s]+', s):
        hits.append('morse')
    if '\\x' in s and re.search(r'\\x[0-9A-Fa-f]{2}', s):
        hits.append('hex-escape')
    if '\\' in s and re.search(r'\\[0-7]{1,3}', s):
        hits.append('octal-escape')
    return hits


# ----------------------------------------------------------------------
# 解码器
# ----------------------------------------------------------------------
def d_base16(s):
    return base64.b16decode(s, casefold=True)


def d_base32(s):
    return base64.b32decode(s + '=' * ((8 - len(s) % 8) % 8))


def d_base64_std(s):
    return base64.b64decode(s + '=' * (-len(s) % 4))


def d_base64url(s):
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))


def d_base58(s, alphabet=B58_ALPHABET):
    n = 0
    for c in s.encode():
        n = n * 58 + alphabet.index(c)
    # 算字节数
    if n == 0:
        return b''
    res = bytearray()
    while n > 0:
        res.append(n & 0xFF)
        n >>= 8
    res.reverse()
    # 前导 1 代表前导 0 字节
    pad = 0
    for c in s.encode():
        if c == alphabet[0]:
            pad += 1
        else:
            break
    return b'\x00' * pad + bytes(res)


def d_base62(s):
    n = 0
    for c in s:
        n = n * 62 + B62_ALPHABET.index(c)
    res = bytearray()
    while n > 0:
        res.append(n & 0xFF)
        n >>= 8
    # 前导 '0' = 前导 0 字节
    pad = 0
    for c in s:
        if c == '0':
            pad += 1
        else:
            break
    return b'\x00' * pad + bytes(res)


def d_base91(s):
    # Joshua Gao 的实现，纯 Python
    v = -1
    b = 0
    n = 0
    out = bytearray()
    for c in s.encode():
        if c not in B91_ALPHABET:
            continue
        if v < 0:
            v = B91_ALPHABET.index(c)
        else:
            v += B91_ALPHABET.index(c) * 91
            b |= v << n
            n += 13 if (v & 8191) > 88 else 14
            while True:
                out.append(b & 0xFF)
                b >>= 8
                n -= 8
                if n < 8:
                    break
            v = -1
    if v + 1:
        out.append((b | v << n) & 0xFF)
    return bytes(out)


def d_ascii85_adobe(s):
    s = s.strip()
    if s.startswith('<~'):
        s = s[2:]
    if s.endswith('~>'):
        s = s[:-2]
    s = re.sub(r'\s', '', s)
    return base64.a85decode(s, adobe=True)


def d_z85(s):
    # Z85 字母表
    z85 = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?&<>()[]{}@%$#'
    s = re.sub(r'\s', '', s)
    out = bytearray()
    # 每 5 个字符解成 4 字节
    for i in range(0, len(s), 5):
        chunk = s[i:i + 5]
        if len(chunk) < 5:
            break
        v = 0
        for c in chunk.encode():
            v = v * 85 + z85.index(c)
        out.extend(v.to_bytes(4, 'big'))
    return bytes(out)


def d_uuencode(s):
    # 处理整段，提取中间正文行
    lines = s.splitlines()
    out = bytearray()
    for line in lines:
        line = line.rstrip('\n').rstrip()
        if not line:
            continue
        if line.startswith('begin '):
            continue
        if line == 'end' or line.startswith('end'):
            break
        # 行首字符是长度 dup，长度 = ord(c) - 32
        length = ord(line[0]) - 32
        body = line[1:]
        for i in range(0, len(body), 4):
            grp = body[i:i + 4]
            if len(grp) < 4:
                grp += '@' * (4 - len(grp))
            n = 0
            for c in grp:
                n = (n << 6) | ((ord(c) - 32) & 0x3F)
            out.extend(n.to_bytes(3, 'big'))
    return bytes(out[:length]) if out else b''


def d_url(s):
    return urllib.parse.unquote(s).encode('utf-8', errors='ignore')


def d_html_entity(s):
    return html.unescape(s).encode('utf-8', errors='ignore')


def d_morse(s):
    tbl = {
        '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E',
        '..-.': 'F', '--.': 'G', '....': 'H', '..': 'I', '.---': 'J',
        '-.-': 'K', '.-..': 'L', '--': 'M', '-.': 'N', '---': 'O',
        '.--.': 'P', '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T',
        '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y',
        '--..': 'Z', '-----': '0', '.----': '1', '..---': '2', '...--': '3',
        '....-': '4', '.....': '5', '-....': '6', '--...': '7',
        '---..': '8', '----.': '9', '.-.-.-': '.', '--..--': ',',
    }
    sep = '/' if '/' in s else ('|' if '|' in s else ' ')
    out = []
    for word in s.strip().split('  '):
        for letter in word.strip().split(sep):
            letter = letter.strip()
            out.append(tbl.get(letter, '?'))
        out.append(' ')
    return ''.join(out).strip().encode('utf-8')


def d_hex_escape(s):
    return re.sub(r'\\x([0-9A-Fa-f]{2})',
                  lambda m: chr(int(m.group(1), 16)),
                  s).encode('utf-8', errors='ignore')


def d_octal_escape(s):
    return re.sub(r'\\([0-7]{1,3})',
                  lambda m: chr(int(m.group(1), 8)),
                  s).encode('utf-8', errors='ignore')


# 类型 -> (解码器函数, 描述)
DECODERS = {
    'base16': (d_base16, 'Base16 / Hex'),
    'base32-rfc4648': (d_base32, 'Base32 RFC4648'),
    'base64': (d_base64_std, 'Base64'),
    'base64url': (d_base64url, 'Base64URL'),
    'base58': (d_base58, 'Base58 (Bitcoin)'),
    'base62': (d_base62, 'Base62'),
    'base91': (d_base91, 'Base91'),
    'ascii85-adobe': (d_ascii85_adobe, 'ASCII85 (Adobe <~...~>)'),
    'ascii85-z85': (d_z85, 'Z85'),
    'uuencode': (d_uuencode, 'UUencode'),
    'url': (d_url, 'URL 编码'),
    'html-entity': (d_html_entity, 'HTML 实体'),
    'morse': (d_morse, '摩尔斯'),
    'hex-escape': (d_hex_escape, '\\xNN 形式转义'),
    'octal-escape': (d_octal_escape, '\\NNN 八进制转义'),
}


def _to_text(b):
    try:
        t = b.decode('utf-8')
        return t
    except Exception:
        return None


def decode_one(s, kind):
    """按指定类型解码，成功返回字节"""
    fn, _ = DECODERS[kind]
    try:
        return fn(s)
    except Exception:
        return None


def decode_all(s, depth=8):
    """递归自动解码：每轮尝试所有识别出的编码，任一成功则继续递归"""
    print(f"\n输入: {s[:80]}{'...' if len(s) > 80 else ''}")
    history = [(s, '原始')]
    current = s
    for i in range(depth):
        kinds = identify(current)
        for k in kinds:
            b = decode_one(current, k)
            if b is None:
                continue
            # 找到结果与原值不同的，视为成功
            t = _to_text(b)
            preview = t if t is not None else b
            str_preview = preview if isinstance(preview, str) else f'<bytes len={len(preview)}>'

            print(f'  [{i}] {DECODERS[k][1]} -> {str_preview[:200]}')
            # 如果是不可读字节，转回 hex 或类型的字符串形式继续尝试
            if t is not None:
                current = t
            else:
                # 不可读则换 hex string 继续递归看看
                current = binascii.hexlify(b).decode()
                print(f'    (不可读，转 hex 继续: {current[:80]})')
            if current == history[-1][0]:
                return history
            history.append((current, k))
            break
        else:
            # 这一轮没有命中任何解码器
            break
    return history


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def main():
    args = sys.argv[1:]
    if not args:
        print("用法: python3 base_family.py [-r|--identify|--type <类型>] <字符串>")
        print("类型:", ', '.join(DECODERS.keys()))
        print("\n示例:")
        print("  python3 base_family.py --identify ZmxhZ3toZWxsb30=")
        print("  python3 base_family.py --type base64 ZmxhZ3toZWxsb30=")
        print("  python3 base_family.py -r ZmxhZ3toZWxsb30=")
        return

    if args[0] == '--identify':
        s = args[1]
        hits = identify(s)
        print(f"识别结果: {hits if hits else '未识别'}")
        return

    if args[0] == '--type':
        kind = args[1]
        s = args[2]
        if kind not in DECODERS:
            print(f"未知类型: {kind}")
            print("支持:", ', '.join(DECODERS.keys()))
            return
        b = decode_one(s, kind)
        print(b if b else '(解码失败)')
        return

    if args[0] == '-r':
        decode_all(args[1])
        return

    s = args[0]
    print("自动尝试所有编码:")
    for k in identify(s):
        b = decode_one(s, k)
        if b:
            t = _to_text(b)
            print(f"  [{DECODERS[k][1]}] {t if t else b}")
    print("\n(加 -r 可递归自动解码)")


if __name__ == '__main__':
    main()

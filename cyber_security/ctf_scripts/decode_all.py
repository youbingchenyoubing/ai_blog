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
    found = False
    for decoder in decoders:
        result = decoder(s.strip())
        if result:
            print(result)
            found = True
    if not found:
        print("[-] 未识别出编码类型")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        auto_decode(sys.argv[1])
    else:
        print("用法: python3 decode_all.py <编码字符串>")
        print("\n--- 示例 ---")
        auto_decode("ZmxhZ3toZWxsb30=")       # Base64: flag{hello}
        auto_decode("666c61677b68656c6c6f7d")   # Hex: flag{hello}

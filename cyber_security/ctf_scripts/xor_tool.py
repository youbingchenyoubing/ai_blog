#!/usr/bin/env python3
"""
XOR 加解密工具
CTF 中常见的 XOR 题目辅助
"""

import sys


def xor_bytes(data, key):
    """对 data 用 key 循环 XOR"""
    if isinstance(key, int):
        key = bytes([key])
    elif isinstance(key, str):
        key = key.encode()
    return bytes(a ^ b for a, b in zip(data, key * (len(data) // len(key) + 1)))


def xor_single(data, key):
    """单字节 XOR"""
    return bytes(b ^ key for b in data)


def xor_bruteforce_single(data, min_key=0, max_key=255):
    """单字节 XOR 暴力破解，按可打印字符比例排序"""
    results = []
    for key in range(min_key, max_key + 1):
        decrypted = xor_single(data, key)
        printable = sum(1 for b in decrypted if 32 <= b <= 126)
        ratio = printable / len(decrypted) if decrypted else 0
        results.append((key, ratio, decrypted))

    results.sort(key=lambda x: x[1], reverse=True)
    for key, ratio, dec in results[:10]:
        try:
            text = dec.decode('utf-8', errors='replace')
        except:
            text = repr(dec)
        print(f"  key=0x{key:02x} ({key:3d}) printable={ratio:.1%}: {text[:80]}")


def auto_detect_xor_key(data):
    """通过频率分析自动检测单字节 XOR 密钥"""
    # 英文字母频率
    freq = {'a': 8.2, 'b': 1.5, 'c': 2.8, 'd': 4.3, 'e': 12.7,
            'f': 2.2, 'g': 2.0, 'h': 6.1, 'i': 7.0, 'j': 0.15,
            'k': 0.77, 'l': 4.0, 'm': 2.4, 'n': 6.7, 'o': 7.5,
            'p': 1.9, 'q': 0.095, 'r': 6.0, 's': 6.3, 't': 9.1,
            'u': 2.8, 'v': 0.98, 'w': 2.4, 'x': 0.15, 'y': 2.0,
            'z': 0.074, ' ': 13.0}

    best_key = 0
    best_score = 0
    for key in range(256):
        decrypted = xor_single(data, key)
        score = 0
        for b in decrypted:
            ch = chr(b).lower()
            if ch in freq:
                score += freq[ch]
            elif 32 <= b <= 126:
                score += 0.5
            else:
                score -= 5
        if score > best_score:
            best_score = score
            best_key = key

    return best_key


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("XOR 工具")
        print("")
        print("用法:")
        print("  python3 xor_tool.py encrypt <输入(hex)> <密钥(hex/str)> [--str]")
        print("  python3 xor_tool.py decrypt <输入(hex)> <密钥(hex/str)> [--str]")
        print("  python3 xor_tool.py brute <输入(hex)>                   单字节暴力")
        print("  python3 xor_tool.py auto <输入(hex)>                    自动检测密钥")
        print("")
        print("示例:")
        print("  python3 xor_tool.py encrypt 48656c6c6f 41 --str")
        print("  python3 xor_tool.py decrypt 092d2d2c2e 41 --str")
        print("  python3 xor_tool.py brute 092d2d2c2e")
        print("  python3 xor_tool.py auto 092d2d2c2e")
        sys.exit(1)

    mode = sys.argv[1]
    data = bytes.fromhex(sys.argv[2])

    if mode in ('encrypt', 'decrypt'):
        key_raw = sys.argv[3]
        is_str = '--str' in sys.argv
        if is_str:
            key = key_raw.encode()
        else:
            key = bytes.fromhex(key_raw)

        result = xor_bytes(data, key)
        print(f"结果 (hex): {result.hex()}")
        try:
            print(f"结果 (text): {result.decode()}")
        except:
            pass

    elif mode == 'brute':
        xor_bruteforce_single(data)

    elif mode == 'auto':
        key = auto_detect_xor_key(data)
        result = xor_single(data, key)
        print(f"[+] 检测到密钥: 0x{key:02x} ({key})")
        print(f"[+] 解密 (hex): {result.hex()}")
        try:
            print(f"[+] 解密 (text): {result.decode()}")
        except:
            print(f"[+] 解密 (repr): {repr(result)}")

    else:
        print(f"未知模式: {mode}")

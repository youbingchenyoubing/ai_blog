#!/usr/bin/env python3
"""
古典密码批量解密
凯撒 / 维吉尼亚 / 栅栏 / 培根 / ROT13
"""

import string
import sys


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
    if rails <= 1 or rails >= n:
        return ciphertext

    pattern = list(range(rails)) + list(range(rails - 2, 0, -1))
    indices = sorted(range(n), key=lambda i: (pattern[i % len(pattern)], i))
    result = [''] * n
    for i, idx in enumerate(indices):
        if i < len(ciphertext):
            result[idx] = ciphertext[i]
    return ''.join(result)


def fence_bruteforce(ciphertext, max_rails=20):
    """栅栏密码暴力破解"""
    print("[栅栏密码]")
    for rails in range(2, min(max_rails + 1, len(ciphertext))):
        result = fence_decrypt(ciphertext, rails)
        print(f"  栏数 {rails:2d}: {result}")


def bacon_decode(ciphertext):
    """培根密码解码"""
    bacon_table = {}
    for i, ch in enumerate(string.ascii_uppercase):
        code = format(i, '05b').replace('0', 'A').replace('1', 'B')
        bacon_table[code] = ch

    ab_seq = ''.join(ch.upper() for ch in ciphertext if ch.upper() in 'AB')
    result = ""
    for i in range(0, len(ab_seq) - 4, 5):
        code = ab_seq[i:i+5]
        if code in bacon_table:
            result += bacon_table[code]
        else:
            result += '?'
    return result


def rot13(s):
    """ROT13"""
    import codecs
    return codecs.decode(s, 'rot_13')


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 classic_crypto.py <模式> <密文> [密钥/参数]")
        print("")
        print("模式:")
        print("  caesar <密文>              凯撒暴力破解")
        print("  vigenere <密文> <密钥>     维吉尼亚解密")
        print("  fence <密文> [栏数]        栅栏解密(不指定栏数则暴力)")
        print("  bacon <密文>               培根解密")
        print("  rot13 <密文>               ROT13解密")
        print("")
        print("示例:")
        print("  python3 classic_crypto.py caesar 'gmbh{fdhvdu}'")
        print("  python3 classic_crypto.py vigenere 'RIJVS' KEY")
        print("  python3 classic_crypto.py fence 'flagishere' 3")
        sys.exit(1)

    mode = sys.argv[1].lower()
    ct = sys.argv[2]

    if mode == 'caesar':
        caesar_bruteforce(ct)
    elif mode == 'vigenere':
        if len(sys.argv) < 4:
            print("需要指定密钥")
            sys.exit(1)
        print(vigenere_decrypt(ct, sys.argv[3]))
    elif mode == 'fence':
        if len(sys.argv) >= 4:
            print(fence_decrypt(ct, int(sys.argv[3])))
        else:
            fence_bruteforce(ct)
    elif mode == 'bacon':
        print(bacon_decode(ct))
    elif mode == 'rot13':
        print(rot13(ct))
    else:
        print(f"未知模式: {mode}")

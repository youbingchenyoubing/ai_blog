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
            flag_offset = pos + 6
            flag = struct.unpack_from('<H', data, flag_offset)[0]
            encrypted = bool(flag & 0x01)
            if encrypted:
                print(f"[!] 位置 0x{flag_offset:04x}: 本地文件头加密标志位 = 1 (伪加密?)")
                data[flag_offset] = flag & 0xFE
                fixed = True
                print(f"[+] 已修复: 清除本地文件头加密位")

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

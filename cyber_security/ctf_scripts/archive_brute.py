#!/usr/bin/env python3
"""
压缩包爆破 / 已知明文攻击 / CRC32 字节碰撞

覆盖 CTF 常见压缩包考点：
    1. ZIP 字典 / 掩码爆破（纯 Python，无第三方依赖）
    2. ZIP 已知明文攻击 (pkcrack 风格思路说明 / 直接调用 pkcrack)
    3. ZIP CRC32 字符爆破（针对 6 字节以内的短文本文件）
    4. RAR 字典爆破（需要 unrar 命令）
    5. 7z 字典爆破（需要 7z 命令）
    6. Gzip 元数据 / 短压缩包爆破（需要 gzip 命令）

依赖（系统命令）：
    - unzip / unrar / 7z / gzip  (Linux/Mac 自带，Windows 装 7-zip + WinRAR)
    - pip install pyelftools  (可选，仅用于 ELF 区段判断)
    - pkcrack  (可选，已知明文攻击)

注意：
    本脚本只提供 CTF 题量级（密码不强）的爆破解题能力。
    真正强密码请直接用 hashcat -m 17200 / john the ripper 跑 GPU。

用法：
    python3 archive_brute.py <压缩包> --dict passwords.txt
    python3 archive_brute.py x.zip --mask 'flag{\?{a-z}{4}{0-9}{4}}'  # 不支持通配，需掩码
    python3 archive_brute.py x.zip --zip-crc --len 4                 # CRC32 爆短文本
    python3 archive_brute.py x.rar --dict passwords.txt --engine rar
"""

import argparse
import itertools
import os
import shutil
import string
import struct
import subprocess
import sys
import tempfile
import zipfile

# ----------------------------------------------------------------------
# 通用：日志
# ----------------------------------------------------------------------
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
RESET = '\033[0m'


def colored(s, c):
    return f"{c}{s}{RESET}" if sys.stdout.isatty() else s


def info(s):
    print(f"[*] {s}")


def found(s):
    print(colored(f"[+] {s}", GREEN))


def warn(s):
    print(colored(f"[!] {s}", YELLOW))


def err(s):
    print(colored(f"[-] {s}", RED))


# ----------------------------------------------------------------------
# 1. ZIP 爆破 (纯 Python)
# ----------------------------------------------------------------------
def zip_crack_zipfile(zip_path, password_iter, verbose_every=200):
    """用 zipfile 模块尝试密码，遇到正确密钥即返回"""
    info(f"开始爆破 ZIP: {zip_path}")
    count = 0
    for pwd in password_iter:
        count += 1
        if count % verbose_every == 0:
            print(f"\r[*] 已尝试 {count} ...", end='', flush=True)
        pwd_b = pwd.encode('utf-8') if isinstance(pwd, str) else pwd
        try:
            with zipfile.ZipFile(zip_path) as zf:
                # 找第一个加密项作为试探目标，如下便是对错误的密钥才产生 RuntimeError
                infos = zf.infolist()
                enc_entries = [inf for inf in infos if inf.flag_bits & 0x01]
                if not enc_entries:
                    # 没有加密项，密码就是空
                    return ''
                target_name = enc_entries[0].filename
                with zf.open(target_name, pwd=pwd_b) as f:
                    f.read(64)  # 读取一段。错密钥使 zlib 报 RuntimeError
            found(f"密码: {pwd}")
            return pwd
        except RuntimeError:
            continue
        except zipfile.BadZipFile:
            err("ZIP 文件损坏")
            return None
        except Exception:
            continue
    if count > verbose_every:
        print()
    return None


# ----------------------------------------------------------------------
# 2. ZIP CRC32 字符爆破
#    在 CTF 中常遇到：ZIP 内一个未加密的小文本文件，只给了 CRC32 校验值，
#    文件名暗示内容是 flag，文件可以是 4-6 字节字符。
#    给定长度 n 和字符集 charset，枚举所有组合并校验 CRC32，匹配的即原文本。
# ----------------------------------------------------------------------
def zip_crc_crack(crc32_target, length, charset=None, lower=True, upper=False,
                  digits=True, extra=''):
    if charset is None:
        cs = ''
        if lower:
            cs += string.ascii_lowercase
        if upper:
            cs += string.ascii_uppercase
        if digits:
            cs += string.digits
        cs += extra
    else:
        cs = charset

    info(f"CRC 爆破: 目标 CRC=0x{crc32_target:08x}  长度 {length}  字符集 {len(cs)} 字符")
    if length > 6:
        warn(f"长度 {length} 过大，组合 {len(cs) ** length} 个，建议改用 hashcat")
    target = crc32_target & 0xFFFFFFFF
    for combo in itertools.product(cs, repeat=length):
        s = ''.join(combo).encode('utf-8')
        if zlib_crc32(s) == target:
            found(f"明文: {s.decode('utf-8')}")
            return s.decode('utf-8')
    return None


def zlib_crc32(data):
    import zlib
    return zlib.crc32(data) & 0xFFFFFFFF


def list_zip_crc(zip_path):
    """列出 ZIP 内每个文件名 + CRC32"""
    info(f"列出 ZIP 内容及 CRC32:")
    with zipfile.ZipFile(zip_path) as zf:
        for inf in zf.infolist():
            enc = 'ENC' if inf.flag_bits & 0x01 else '   '
            print(f"  [{enc}] {inf.filename:<40} {inf.file_size:>8} bytes  CRC=0x{inf.CRC:08x}")


# ----------------------------------------------------------------------
# 3. 已知明文攻击 (pkcrack) 包装
# ----------------------------------------------------------------------
def known_plain_attack(zip_with_target, plain_text_file, in_zip_name,
                       engine='pkcrack'):
    info("已知明文攻击：")
    info(f"  目标 ZIP: {zip_with_target}")
    info(f"  已知文件: {plain_text_file}  (在压缩包内的文件名: {in_zip_name})")
    info("思路：先用相同压缩级别把已知文件打成 ZIP，再调用 pkcrack")
    info("若未安装 pkcrack，请在 Linux/Mac 通过源码或包管理器安装。")
    if shutil.which(engine) is None:
        err(f"未找到 {engine}，请先安装：")
        print("    Debian/Ubuntu: sudo apt install pkcrack")
        print("    源码编译：    https://www.unix-ag.uni-kl.de/~conrad/krypto/pkcrack/")
        return

    # 先制作 plain.zip
    plain_zip = os.path.join(tempfile.gettempdir(), 'plain.zip')
    with zipfile.ZipFile(plain_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(plain_text_file, in_zip_name)
    info(f"生成明文 zip: {plain_zip}")

    out_dir = tempfile.mkdtemp(prefix='pkcrack_')
    cmd = [
        engine, '-C', zip_with_target, '-c', in_zip_name,
        '-P', plain_zip, '-p', in_zip_name,
        '-d', out_dir,
    ]
    info(f"调用: {' '.join(cmd)}")
    subprocess.run(cmd)


# ----------------------------------------------------------------------
# 4. RAR 爆破（依赖 unrar 工具）
# ----------------------------------------------------------------------
def rar_crack(rar_path, password_iter, verbose_every=100):
    unrar = shutil.which('unrar') or shutil.which('rar')
    if not unrar:
        err("未找到 unrar/rar 命令，Windows 装 WinRAR，Linux 装 p7zip-rar 或 unrar")
        return None
    info(f"开始爆破 RAR: {rar_path}  引擎: {unrar}")

    tmp = tempfile.mkdtemp(prefix='rar_')
    count = 0
    for pwd in password_iter:
        count += 1
        if count % verbose_every == 0:
            print(f"\r[*] 已尝试 {count} ...", end='', flush=True)
        # unrar t -p<pwd> file
        proc = subprocess.run(
            [unrar, 't', f'-p{pwd}', '-y', '-inul', rar_path],
            capture_output=True, text=True,
        )
        if proc.returncode == 0:
            print()
            found(f"密码: {pwd}")
            return pwd
    print()
    return None


# ----------------------------------------------------------------------
# 5. 7z 爆破（依赖 7z 命令）
# ----------------------------------------------------------------------
def sevenz_crack(sevenz_path, password_iter, verbose_every=100):
    sz = shutil.which('7z') or shutil.which('7za') or shutil.which('7zr')
    if not sz:
        err("未找到 7z / 7za / 7zr，请安装 7-Zip")
        return None
    info(f"开始爆破 7z: {sevenz_path}  引擎: {sz}")

    for i, pwd in enumerate(password_iter, 1):
        if i % verbose_every == 0:
            print(f"\r[*] 已尝试 {i} ...", end='', flush=True)
        proc = subprocess.run(
            [sz, 't', f'-p{pwd}', sevenz_path],
            capture_output=True, text=True,
        )
        if proc.returncode == 0:
            print()
            found(f"密码: {pwd}")
            return pwd
    print()
    return None


# ----------------------------------------------------------------------
# 6. Gzip 短压缩爆破（CTF 常给一个 z 文件，文件名暗示 flag）
# ----------------------------------------------------------------------
def gzip_try(gz_path, password_iter):
    info("Gzip 本身没有密码。本函数用于 : 当文件名是不同长度 flag 的实验性爆破")
    # 没意义，只是占位
    err("Gzip 没有加密。若需要爆破 zip，请用 --engine zip")
    return None


# ----------------------------------------------------------------------
# 密码生成器：字典 / 掩码
# ----------------------------------------------------------------------
def load_dict(path):
    if not os.path.exists(path):
        err(f"字典不存在: {path}")
        return
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            pwd = line.rstrip('\r\n').strip()
            if pwd:
                yield pwd


def mask_iter(mask, charset_map=None):
    """
    简化版 hashcat 风格掩码：
        ?l = a-z
        ?u = A-Z
        ?d = 0-9
        ?s = 特殊字符
        ?a = 所有可见 ASCII
        其它字符按字面值
    例：flag{?a?a?a}
    """
    cs = {
        '?l': string.ascii_lowercase,
        '?u': string.ascii_uppercase,
        '?d': string.digits,
        '?s': '!@#$%^&*()-_=+[]{};:,.<>?/',
        '?a': string.ascii_lowercase + string.ascii_uppercase
              + string.digits + '!@#$%^&*()-_=+[]{};:,.<>?/',
    }
    if charset_map:
        cs.update(charset_map)

    # 解析 mask 成 token 列表：每个 token 是字符集字符串
    tokens = []
    i = 0
    while i < len(mask):
        if mask[i] == '?' and i + 1 < len(mask) and mask[i:i+2] in cs:
            tokens.append(cs[mask[i:i+2]])
            i += 2
        else:
            tokens.append(mask[i])  # 字面字符
            i += 1

    return [''.join(combo)
            for combo in itertools.product(*tokens)]


# ----------------------------------------------------------------------
# 自动识别压缩包类型并调用
# ----------------------------------------------------------------------
def auto_detect(path):
    with open(path, 'rb') as f:
        head = f.read(8)
    if head.startswith(b'PK\x03\x04') or head.startswith(b'PK\x05\x06'):
        return 'zip'
    if head.startswith(b'Rar!'):
        return 'rar'
    if head.startswith(b'7z\xbc\xaf\x27\x1c'):
        return '7z'
    if head.startswith(b'\x1f\x8b'):
        return 'gzip'
    return 'unknown'


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(
        description='压缩包爆破 / CRC32 爆破 / 已知明文攻击',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument('archive', help='压缩包路径')
    p.add_argument('--dict', help='字典文件路径')
    p.add_argument('--mask', help='hashcat 风格掩码，如 flag{?l?l?l?d?d}')
    p.add_argument('--engine', choices=['zip', 'rar', '7z', 'gzip'], default=None,
                   help='指定引擎；默认按文件头自动识别')
    p.add_argument('--list', action='store_true', help='仅列出 ZIP 内文件与 CRC')
    p.add_argument('--zip-crc', action='store_true', help='ZIP CRC32 短文本爆破')
    p.add_argument('--crc', help='--zip-crc 时使用，目标 CRC32 整数')
    p.add_argument('--len', type=int, help='--zip-crc 时使用，明文长度')
    p.add_argument('--charset', help='--zip-crc 时使用，自定义字符集')
    p.add_argument('--extra', default='', help='--zip-crc 时追加额外字符')
    p.add_argument('--known-plain', metavar='PLAIN_FILE', help='已知明文攻击')
    p.add_argument('--zip-name', help='--known-plain 时，明文在压缩包内的名字')

    args = p.parse_args()
    if not os.path.exists(args.archive):
        err(f"文件不存在: {args.archive}")
        sys.exit(1)

    engine = args.engine or auto_detect(args.archive)
    info(f"检测引擎: {engine}")

    # 1) 列出
    if args.list and engine == 'zip':
        list_zip_crc(args.archive)
        return

    # 2) CRC 爆破
    if args.zip_crc:
        crc = int(args.crc, 0) if args.crc else None
        if crc is None or args.len is None:
            err("--zip-crc 需要配合 --crc <int> --len <int>")
            sys.exit(1)
        zip_crc_crack(crc, args.len,
                      charset=args.charset,
                      extra=args.extra)
        return

    # 3) 已知明文攻击
    if args.known_plain:
        known_plain_attack(args.archive, args.known_plain, args.zip_name or 'flag.txt')
        return

    # 4) 字典 / 掩码爆破
    if args.dict and os.path.exists(args.dict):
        pwds = load_dict(args.dict)
    elif args.mask:
        pwds = mask_iter(args.mask)
    else:
        err("请指定 --dict 或 --mask 之一")
        sys.exit(1)

    if engine == 'zip':
        result = zip_crack_zipfile(args.archive, pwds)
    elif engine == 'rar':
        result = rar_crack(args.archive, pwds)
    elif engine == '7z':
        result = sevenz_crack(args.archive, pwds)
    elif engine == 'gzip':
        result = gzip_try(args.archive, pwds)
    else:
        err(f"未知引擎: {engine}")
        sys.exit(1)

    if not result:
        err("未找到密码。")


if __name__ == '__main__':
    main()

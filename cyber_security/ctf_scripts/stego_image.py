#!/usr/bin/env python3
"""
图片隐写自动化处理

覆盖 CTF 常见图片隐写思路：
    1. 文件结构分析（魔数、CRC、宽高修复）
    2. 末尾附加文件提取（PNG 后跟 ZIP/RAR 等）
    3. PNG 宽高修改修复（CRC 校验失败提示真实宽高）
    4. LSB 隐写提取（PNG 低位、按 R/G/B 通道）
    5. PNG IDAT 块拼接异常检测
    6. BMP 文件嵌入（最高位 / 最低位像素 plane）
    7. JPG APP 段 / EXIF 信息
    8. 文件 binwalk 简易扫描（不依赖 binwalk）
    9. PK / Rar! / 7z / Gzip 头在文件内的偏移定位

依赖:
    pip install Pillow numpy
    Pillow 用于像素操作

用法:
    python3 stego_image.py <图片文件> [--all]
    python3 stego_image.py x.png --lsb-rgb R --width 0 --height 400
    python3 stego_image.py x.png --fix-size
    python3 stego_image.py x.png --carve
"""

import argparse
import os
import struct
import sys
import zlib

# 尽量兼容没有 Pillow 的环境
try:
    from PIL import Image
    import numpy as np
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# 常见文件在文件内部的偏移
EMBED_SIGNATURES = [
    (b'PK\x03\x04',           'ZIP',  '.zip'),
    (b'Rar!\x1a\x07',         'RAR',  '.rar'),
    (b'7z\xbc\xaf\x27\x1c',   '7z',   '.7z'),
    (b'\x1f\x8b',             'GZIP', '.gz'),
    (b'\x89PNG\r\n\x1a\n',    'PNG',  '.png'),
    (b'\xff\xd8\xff',         'JPG',  '.jpg'),
    (b'BM',                   'BMP',  '.bmp'),
    (b'%PDF',                 'PDF',  '.pdf'),
    (b'\x7fELF',              'ELF',  '.elf'),
    (b'MZ',                   'PE',   '.exe'),
    (b'pK\x12',               'ZIP(空)','.zip'),
    (b'Pa\x00',               'PAQ',  None),
]


# ----------------------------------------------------------------------
# 文件读取工具
# ----------------------------------------------------------------------
def read_file(path):
    with open(path, 'rb') as f:
        return f.read()


def save_bytes(path, data):
    with open(path, 'wb') as f:
        f.write(data)
    print(f"  [+] 已保存: {path} ({len(data)} bytes)")


# ----------------------------------------------------------------------
# 1. PNG 宽高修复
# ----------------------------------------------------------------------
PNG_IHDR_OFFSET = 12  # 8 (signature) + 4 (length) + 4 ("IHDR")


def png_struct(data):
    """分析 PNG 结构，返回 (chunk_map, total_size)"""
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        return None, None
    pos = 8
    chunks = []
    while pos < len(data):
        if pos + 8 > len(data):
            break
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8].decode('ascii', 'replace')
        body_start = pos + 8
        body_end = body_start + length
        crc_stored = struct.unpack('>I', data[body_end:body_end + 4])[0] if body_end + 4 <= len(data) else None
        body = data[body_start:body_end]
        crc_calc = zlib.crc32(ctype.encode('ascii') + body) & 0xFFFFFFFF
        chunks.append({
            'offset': pos,
            'type': ctype,
            'length': length,
            'body': body,
            'crc_stored': crc_stored,
            'crc_calc': crc_calc,
            'ok': crc_stored == crc_calc,
        })
        pos = body_end + 4
        if ctype == 'IEND':
            break
    return chunks, pos


def fix_png_size(path):
    print("\n[PNG 宽高修复]")
    data = read_file(path)
    chunks, _ = png_struct(data)
    if chunks is None:
        print("  [-] 不是 PNG 文件")
        return
    ihdr = chunks[0]
    if ihdr['type'] != 'IHDR':
        print("  [-] 第一个 chunk 不是 IHDR")
        return

    body = ihdr['body']
    width = struct.unpack('>I', body[0:4])[0]
    height = struct.unpack('>I', body[4:8])[0]
    print(f"  当前宽: {width}  高: {height}")
    print(f"  IHDR CRC: {'OK' if ihdr['ok'] else '损坏!'}")

    if ihdr['ok']:
        print("  [+] IHDR CRC 正常，宽高未被篡改")
        return

    # CRC 正确，反推真实宽高
    expected_crc = ihdr['crc_stored']
    print(f"  [*] 用 CRC 反推真实宽高 (CRC=0x{expected_crc:08x})")
    found = False
    for w in range(1, 4096):
        for h in range(1, 4096):
            test_body = struct.pack('>II', w, h) + body[8:]
            if zlib.crc32(b'IHDR' + test_body) & 0xFFFFFFFF == expected_crc:
                print(f"  [+] 真实宽高: {w} x {h}")
                # 生成修复后文件
                body_offset = ihdr['offset'] + 8
                fixed = data[:body_offset] + struct.pack('>II', w, h) + body[8:] + data[body_offset + 8:]
                out = path.replace('.png', '_fixed.png')
                save_bytes(out, fixed)
                found = True
                break
        if found:
            break
    if not found:
        print("  [-] 未找到匹配的宽高组合")
        print("  提示: 可用 pngcheck -vf 查看，或手动用 IDAT 大小估算")


# ----------------------------------------------------------------------
# 2. 偏移搜索内嵌文件
# ----------------------------------------------------------------------
def carve(path):
    print("\n[内嵌文件提取]")
    data = read_file(path)
    found = []
    base_name = os.path.basename(path)
    root, _ = os.path.splitext(base_name)
    out_dir = root + '_carved'
    os.makedirs(out_dir, exist_ok=True)

    # 跳过主文件开头，避免提到自身
    skip = 0
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        # PNG 必须从 IHDR 处开始，跳到 IEND 后再搜
        pos = 8
        while pos < len(data) - 12:
            length = struct.unpack('>I', data[pos:pos + 4])[0]
            ctype = data[pos + 4:pos + 8]
            if ctype == b'IEND':
                skip = pos + 12
                break
            pos += 12 + length
    elif data.startswith(b'\xff\xd8\xff'):
        # JPG 找到 EOI (FFD9) 后再搜
        idx = data.rfind(b'\xff\xd9')
        if idx > 0:
            skip = idx + 2
    elif data.startswith(b'BM'):
        skip = struct.unpack('<I', data[2:6])[0]

    search_region = data[skip:]
    for sig, name, ext in EMBED_SIGNATURES:
        idx = 0
        while True:
            found_at = search_region.find(sig, idx)
            if found_at < 0:
                break
            absolute = skip + found_at
            # 不允许就找自己
            if absolute == 0:
                idx = found_at + 1
                continue
            print(f"  [!] 发现 {name} 偏移 0x{absolute:x}")
            if ext:
                filename = f'{out_dir}/offset_{absolute:08x}{ext}'
                save_bytes(filename, data[absolute:])
            found.append((name, absolute))
            idx = found_at + 1

    if not found:
        print("  [-] 未发现内嵌文件")


# ----------------------------------------------------------------------
# 3. LSB 隐写提取
# ----------------------------------------------------------------------
def lsb_extract(path, channels=None, bit=0, bit_count=1, width=0, height=0, output_hex=True):
    print(f"\n[LSB 提取] channels={channels} bit={bit} count={bit_count}")
    if not HAS_PIL:
        print("  [-] 需要 Pillow + numpy: pip install Pillow numpy")
        return
    img = Image.open(path).convert('RGB')
    arr = np.array(img)
    h, w = arr.shape[:2]
    # 1 bit or upper bits
    mask = ((1 << bit_count) - 1) << bit
    # channels: list of indices
    ch_idx = {'R': 0, 'G': 1, 'B': 2}
    if channels is None:
        channels = 'RGB'
    bits = []
    for row in arr:
        for px in row:
            for ch in channels:
                i = ch_idx[ch]
                v = px[i]
                bits.append((v & mask) >> bit)
    # 每个 pixel 通道贡献 bit_count 位，按从高到低拼字节
    bit_per_pixel = bit_count
    total_bits = len(bits) * bit_per_pixel
    out = bytearray()
    acc = 0
    acc_bits = 0
    for v in bits:
        for j in range(bit_count):
            bit_val = (v >> (bit_count - 1 - j)) & 1
            acc = (acc << 1) | bit_val
            acc_bits += 1
            if acc_bits == 8:
                out.append(acc & 0xFF)
                acc = 0
                acc_bits = 0

    if width and not height:
        out = out[:width]

    print(f"  提取字节长度: {len(out)}")
    print(f"  Hex (前 256): {bytes(out)[:256].hex()}")
    save_bytes(path + '.lsb.bin', bytes(out))
    try:
        text = bytes(out).decode('utf-8', errors='ignore')
        printable = ''.join(c for c in text if c.isprintable() or c in '\r\n\t')
        if printable.strip():
            print(f"  可见文本: {printable[:200]}")
    except Exception:
        pass


# ----------------------------------------------------------------------
# 4. PNG IDAT 异常检查
# ----------------------------------------------------------------------
def check_png_chunks(path):
    print("\n[PNG chunk 检查]")
    data = read_file(path)
    chunks, end = png_struct(data)
    if chunks is None:
        print("  [-] 不是 PNG")
        return
    print(f"  共 {len(chunks)} 个 chunk, IEND 后剩余字节: {len(data) - (end or 0)} bytes")
    for c in chunks:
        flag = '' if c['ok'] else ' [CRC 损坏!]'
        print(f"  {c['type']:<5}  off=0x{c['offset']:06x}  len={c['length']:>6d}{flag}")
    extra = len(data) - (end or 0)
    if extra > 0:
        tail = data[end or len(data):end or len(data) + 32]
        print(f"\n  [!] 尾部多余数据 (前 32B): {tail.hex()}")
        # 识别签名
        for sig, name, _ in EMBED_SIGNATURES:
            if (data[end or len(data):]).startswith(sig):
                print(f"  末尾疑似 {name} 文件 -> 可用 --carve 提取")


# ----------------------------------------------------------------------
# 5. JPG APP 段 / EXIF
# ----------------------------------------------------------------------
def jpg_segments(path):
    print("\n[JPG 段检查]")
    data = read_file(path)
    if not data.startswith(b'\xff\xd8\xff'):
        print("  [-] 不是 JPG")
        return
    pos = 2
    while pos < len(data) - 2:
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = struct.unpack('>H', data[pos:pos + 2])[0]
        if 0xFFD0 <= marker <= 0xFFD7 or marker == 0xFFD9:
            if marker == 0xFFD9:
                print(f"  EOI  位置 0x{pos:06x} (图像结束)")
                if pos < len(data):
                    tail = data[pos + 2:]
                    if tail.strip(b'\x00'):
                        print(f"  [!] EOI 后存在 {len(tail)} 字节额外数据")
                return
            print(f"  RST{marker & 0xF}  位置 0x{pos:06x}")
            pos += 2
            continue
        length = struct.unpack('>H', data[pos + 2:pos + 4])[0]
        seg_name = {
            0xFFE0: 'APP0 (JFIF)', 0xFFE1: 'APP1 (EXIF/XMP)', 0xFFE2: 'APP2',
            0xFFED: 'APP13 (IPTC/Photoshop)', 0xFFEE: 'APP14 (Adobe)',
            0xFFDB: 'DQT', 0xFFC0: 'SOF0', 0xFFC2: 'SOF2',
            0xFFC4: 'DHT', 0xFFDA: 'SOS', 0xFFD9: 'EOI',
            0xFFFE: 'COM (注释)',
        }.get(marker, f'未知 0x{marker:04x}')
        print(f"  {seg_name:<22} 位置 0x{pos:06x} 长度 {length}")
        # EXIF / IPTC 可能包含说明
        if marker in (0xFFE1, 0xFFED, 0xFFFE):
            body = data[pos + 4:pos + 2 + length]
            text = body.decode('utf-8', errors='ignore')
            printable = ''.join(c for c in text if c.isprintable() or c in '\r\n\t')
            if len(printable) > 4:
                print(f"    段内可读: {printable[:120]}")
        pos += 2 + length
        if marker == 0xFFDA:
            # SOS 后是熵编码，跳到 EOI
            eoi = data.find(b'\xff\xd9', pos)
            print(f"  扫描数据位置 0x{pos:06x} -> EOI 0x{eoi:06x}")
            return


# ----------------------------------------------------------------------
# 6. BMP 末尾 / 文件头检查
# ----------------------------------------------------------------------
def bmp_check(path):
    print("\n[BMP 检查]")
    data = read_file(path)
    if not data.startswith(b'BM'):
        print("  [-] 不是 BMP")
        return
    file_size = struct.unpack('<I', data[2:6])[0]
    pixel_offset = struct.unpack('<I', data[10:14])[0]
    width = struct.unpack('<i', data[18:22])[0]
    height = struct.unpack('<i', data[22:26])[0]
    print(f"  实际大小: {len(data)}  文件头声明: {file_size}")
    print(f"  像素偏移: 0x{pixel_offset:x}  宽: {width}  高: {height}")
    if len(data) > file_size:
        extra = data[file_size:]
        print(f"  [!] 实际超过声明 {len(extra)} 字节")
        print(f"  尾部: {extra[:32].hex()}")


# ----------------------------------------------------------------------
# 7. binwalk 风格扫描（不依赖 binwalk）
# ----------------------------------------------------------------------
def binwalk_scan(path):
    print("\n[binwalk 风格扫描]")
    data = read_file(path)
    for sig, name, _ in EMBED_SIGNATURES:
        idx = 0
        while True:
            pos = data.find(sig, idx)
            if pos < 0:
                break
            print(f"  0x{pos:08x}  {name}")
            idx = pos + 1
    # 同时找 zip End Of Central Directory
    pos = 0
    while True:
        p = data.find(b'PK\x05\x06', pos)
        if p < 0:
            break
        print(f"  0x{p:08x}  ZIP EOCD (中央目录尾)")
        pos = p + 1


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(
        description='CTF 图片隐写脚本',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument('image', help='图片文件路径')
    p.add_argument('--all', action='store_true', help='全部检查一遍')
    p.add_argument('--fix-size', action='store_true', help='PNG 宽高修复（基于 CRC）')
    p.add_argument('--carve', action='store_true', help='提取内嵌文件')
    p.add_argument('--lsb-rgb', metavar='CHANNELS', help='LSB 提取，如 RGB 或 RG 或 B')
    p.add_argument('--bit', type=int, default=0, help='提取起始位 (默认 0=最低位)')
    p.add_argument('--count', type=int, default=1, help='提取位数 (默认 1)')
    p.add_argument('--width', type=int, default=0, help='限制提取宽度')
    p.add_argument('--height', type=int, default=0, help='限制提取高度')
    p.add_argument('--chunks', action='store_true', help='检查 PNG chunk（含 CRC）')
    p.add_argument('--jpg', action='store_true', help='检查 JPG 段')
    p.add_argument('--bmp', action='store_true', help='检查 BMP')
    p.add_argument('--binwalk', action='store_true', help='binwalk 风格扫描')

    args = p.parse_args()
    if not os.path.exists(args.image):
        print(f"[-] 文件不存在: {args.image}")
        sys.exit(1)

    data = read_file(args.image)
    if args.all:
        args.fix_size = True
        args.carve = True
        args.chunks = True
        args.jpg = True
        args.bmp = True
        args.binwalk = True

    if args.fix_size or args.chunks:
        if data.startswith(b'\x89PNG'):
            if args.fix_size:
                fix_png_size(args.image)
            if args.chunks:
                check_png_chunks(args.image)
        else:
            print("\n[!] --fix-size / --chunks 仅适用于 PNG")

    if args.carve:
        carve(args.image)

    if args.lsb_rgb:
        lsb_extract(args.image, args.lsb_rgb, args.bit, args.count,
                    args.width, args.height)

    if args.jpg and data.startswith(b'\xff\xd8\xff'):
        jpg_segments(args.image)

    if args.bmp and data.startswith(b'BM'):
        bmp_check(args.image)

    if args.binwalk:
        binwalk_scan(args.image)

    if not any([args.all, args.fix_size, args.carve, args.lsb_rgb,
                args.chunks, args.jpg, args.bmp, args.binwalk]):
        p.print_help()


if __name__ == '__main__':
    main()

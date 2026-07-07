#!/usr/bin/env python3
"""
文件魔数识别
根据文件头部字节判断文件真实类型
CTF 中常遇到扩展名被修改的文件，需通过魔数判断真实类型
"""

import struct
import sys

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
    b'\x00\x00\x00\x1c': 'MP4 视频 (ftyp)',
    b'\x00\x00\x00\x20': 'MP4 视频 (ftyp)',
}


def identify(filepath):
    """识别文件真实类型"""
    with open(filepath, 'rb') as f:
        header = f.read(32)

    print(f"文件: {filepath}")
    print(f"头部 (Hex): {header[:16].hex()}")
    print(f"大小: {len(open(filepath, 'rb').read())} bytes")

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
    if len(sys.argv) > 1:
        for f in sys.argv[1:]:
            identify(f)
            print()
    else:
        print("用法: python3 file_id.py <文件路径> [文件路径2 ...]")

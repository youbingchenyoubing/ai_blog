#!/usr/bin/env python3
"""
CTF 流量取证自动化脚本

覆盖 CTF 流量题常见考点：
    1. 全流量概览（协议 / IP / 端口统计）
    2. flag 明文 / 正则搜索
    3. HTTP 请求、文件对象、凭据提取
    4. DNS 隧道检测
    5. TCP 流还原（客户端 / 服务端方向）
    6. TLS SNI 提取 + SSLKEYLOGFILE 解密
    7. USB HID 键盘还原
    8. 反弹 Shell / 可疑端口检测

依赖:
    pip install pyshark
    需系统已安装 tshark (Wireshark 自带)

用法:
    python3 pcap_forensics.py <pcap_file> [模式 ...]
    python3 pcap_forensics.py <pcap_file> --all
    python3 pcap_forensics.py capture.pcap --flag --http --dns --tcp 0
    python3 pcap_forensics.py capture.pcap --tls-keylog keylog.txt --http

如 tshark 不在 PATH 中，修改下方 TSHARK_PATH 或设置环境变量。
更详细的 pyshark 用法参见 ../pyshark实战使用指南.md
"""

import os
import re
import sys
import argparse
from collections import Counter, defaultdict

import pyshark

# ---- 配置：tshark 路径 ----------------------------------------------------
# Windows 默认路径，Linux/Mac 一般在 PATH 中可设为 None
TSHARK_PATH = r'C:/Program Files/Wireshark/tshark.exe' if os.name == 'nt' else None

FLAG_PATTERNS = [
    r'flag\{[^}]+\}',
    r'FLAG\{[^}]+\}',
    r'ctf\{[^}]+\}',
    r'CTF\{[^}]+\}',
    r'Flag\{[^}]+\}',
]


def _cap(path, **kwargs):
    """构造 FileCapture，统一传入 tshark_path"""
    if TSHARK_PATH and os.path.exists(TSHARK_PATH):
        kwargs.setdefault('tshark_path', TSHARK_PATH)
    return pyshark.FileCapture(input_file=path, keep_packets=False, **kwargs)


def _safe_close(cap):
    try:
        cap.close()
    except Exception:
        pass


def _has_layer(pkt, name):
    return hasattr(pkt, name)


def _has_field(layer, name):
    return hasattr(layer, name)


# ---- 1. 全流量概览 --------------------------------------------------------
def overview(path):
    print("\n" + "=" * 60)
    print(f"[1] 流量概览: {path}")
    print("=" * 60)

    cap = _cap(path)
    proto_count = Counter()
    conv = defaultdict(int)
    src_ips = Counter()
    dst_ports = Counter()
    total = 0

    for pkt in cap:
        total += 1
        proto_count[pkt.highest_layer] += 1
        if _has_layer(pkt, 'ip'):
            src_ips[pkt.ip.src] += 1
            if _has_layer(pkt, 'tcp'):
                dst_ports[('TCP', pkt.tcp.dstport)] += 1
            elif _has_layer(pkt, 'udp'):
                dst_ports[('UDP', pkt.udp.dstport)] += 1
            if _has_layer(pkt, 'ip') and _has_field(pkt.ip, 'dst'):
                conv[(pkt.ip.src, pkt.ip.dst)] += 1
    _safe_close(cap)

    print(f"\n总包数: {total}")
    print("\nTop 10 协议:")
    for k, v in proto_count.most_common(10):
        print(f"  {v:6d}  {k}")
    print("\nTop 10 源 IP:")
    for k, v in src_ips.most_common(10):
        print(f"  {v:6d}  {k}")
    print("\nTop 10 目的端口:")
    for (proto, port), v in dst_ports.most_common(10):
        print(f"  {v:6d}  {proto}/{port}")
    print("\nTop 10 通信对:")
    for (s, d), v in sorted(conv.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {v:6d}  {s} -> {d}")


# ---- 2. flag 搜索 ---------------------------------------------------------
def search_flag(path, patterns=None):
    print("\n" + "=" * 60)
    print("[2] flag 搜索")
    print("=" * 60)
    patterns = patterns or FLAG_PATTERNS

    found = set()
    cap = _cap(path)
    try:
        for pkt in cap:
            # 直接遍历每个包的字符串表示，能够命中 tshark 解析出的所有字段
            pkt_str = str(pkt)
            for pat in patterns:
                for m in re.findall(pat, pkt_str):
                    found.add(m)

            # 同时检查 TCP/HTTP 原始 payload 中的明文 flag
            if _has_layer(pkt, 'tcp') and _has_field(pkt.tcp, 'payload'):
                try:
                    raw = bytes.fromhex(pkt.tcp.payload.replace(':', ''))
                    text = raw.decode('utf-8', errors='ignore')
                    for pat in patterns:
                        for m in re.findall(pat, text):
                            found.add(m)
                except Exception:
                    pass
    finally:
        _safe_close(cap)

    if found:
        for f in sorted(found):
            print(f"  [FOUND] {f}")
    else:
        print("  [-] 未直接发现明文 flag，需尝试 TLS 解密 / 流还原 / 隐写")


# ---- 3. HTTP 提取 ---------------------------------------------------------
def http_extract(path):
    print("\n" + "=" * 60)
    print("[3] HTTP 分析")
    print("=" * 60)

    cap = _cap(path, display_filter='http')
    print("\n[请求]")
    print(f"  {'源IP':<16} {'方法':<6} {'Host':<28} URI")
    for pkt in cap:
        if not _has_layer(pkt, 'http'):
            continue
        src = pkt.ip.src if _has_layer(pkt, 'ip') else '-'
        if _has_field(pkt.http, 'request_method'):
            method = pkt.http.request_method
            host = pkt.http.host if _has_field(pkt.http, 'host') else '-'
            uri = pkt.http.request_uri if _has_field(pkt.http, 'request_uri') else '/'
            print(f"  {src:<16} {method:<6} {host:<28} {uri}")
    _safe_close(cap)

    print("\n[凭据]")
    cap = _cap(path, display_filter='http.authorization or (http.request.method == "POST" and http.file_data)')
    for pkt in cap:
        if _has_field(pkt.http, 'authorization'):
            print(f"  Basic Auth: {pkt.ip.src} -> {pkt.http.authorization}")
        if _has_field(pkt.http, 'file_data'):
            data = pkt.http.file_data
            if any(k in data.lower() for k in ('password', 'pwd', 'passwd', 'pass=')):
                print(f"  POST 凭据: {pkt.ip.src} -> {data}")
    _safe_close(cap)


# ---- 4. DNS 隧道 ----------------------------------------------------------
def dns_tunnel(path, threshold=30):
    print("\n" + "=" * 60)
    print(f"[4] DNS 隧道检测 (长子域阈值={threshold})")
    print("=" * 60)

    cap = _cap(path, display_filter='dns.qry.name')
    queries = Counter()
    suspicious = []
    for pkt in cap:
        if _has_field(pkt.dns, 'qry_name'):
            name = pkt.dns.qry_name
            queries[name] += 1
            parts = name.split('.')
            if parts and len(parts[0]) > threshold:
                suspicious.append(name)
    _safe_close(cap)

    print("\nTop 10 查询:")
    for n, c in queries.most_common(10):
        print(f"  {c:4d}  {n}")
    if suspicious:
        print(f"\n[!] 可疑长子域 {len(suspicious)} 个:")
        for n in suspicious[:10]:
            print(f"  {n}")
    else:
        print("\n[-] 未发现明显 DNS 隧道特征")


# ---- 5. TCP 流还原 --------------------------------------------------------
def tcp_streams(path):
    print("\n" + "=" * 60)
    print("[5] TCP 流列表")
    print("=" * 60)

    cap = _cap(path, display_filter='tcp.stream')
    streams = set()
    for pkt in cap:
        streams.add(pkt.tcp.stream)
    _safe_close(cap)
    print(f"\n共 {len(streams)} 条 TCP 流:")
    for s in sorted(streams, key=lambda x: int(x)):
        print(f"  stream #{s}")
    print("\n用 --tcp <stream_id> 还原指定流（见 dump_stream）")


def tcp_dump_stream(path, stream_index, outdir='.'):
    print(f"\n[TCP 流还原] stream #{stream_index}")
    cap = _cap(path, display_filter=f'tcp.stream eq {stream_index}')
    client_ip = None
    c_buf, s_buf = [], []
    for pkt in cap:
        if not _has_field(pkt.tcp, 'payload'):
            continue
        if client_ip is None and _has_layer(pkt, 'ip'):
            client_ip = pkt.ip.src
        try:
            raw = bytes.fromhex(pkt.tcp.payload.replace(':', ''))
        except Exception:
            continue
        if _has_layer(pkt, 'ip') and pkt.ip.src == client_ip:
            c_buf.append(raw)
        else:
            s_buf.append(raw)
    _safe_close(cap)

    client_bin = b''.join(c_buf)
    server_bin = b''.join(s_buf)
    print(f"  客户端 -> 服务端: {len(client_bin)} bytes")
    print(f"  服务端 -> 客户端: {len(server_bin)} bytes")

    c_path = os.path.join(outdir, f'stream{stream_index}_client.bin')
    s_path = os.path.join(outdir, f'stream{stream_index}_server.bin')
    with open(c_path, 'wb') as f:
        f.write(client_bin)
    with open(s_path, 'wb') as f:
        f.write(server_bin)
    print(f"  已保存: {c_path}, {s_path}")


# ---- 6. TLS ---------------------------------------------------------------
def tls_sni(path):
    print("\n" + "=" * 60)
    print("[6] TLS SNI")
    print("=" * 60)

    cap = _cap(path, display_filter='tls.handshake.extensions_server_name')
    sni_count = Counter()
    for pkt in cap:
        if _has_layer(pkt, 'tls') and _has_field(pkt.tls, 'handshake_extensions_server_name'):
            sni = pkt.tls.handshake_extensions_server_name
            sni_count[sni] += 1
    _safe_close(cap)
    if sni_count:
        for sni, c in sni_count.most_common(20):
            print(f"  {c:3d}  {sni}")
    else:
        print("  [-] 未发现 SNI")


def tls_decrypt_http(path, keylog_file):
    print("\n" + "=" * 60)
    print(f"[6+] TLS 解密 (keylog: {keylog_file})")
    print("=" * 60)

    cap = _cap(
        path,
        override_prefs={'tls.keylog_file': keylog_file},
        display_filter='http.request',
    )
    n = 0
    for pkt in cap:
        if _has_layer(pkt, 'http'):
            host = pkt.http.host if _has_field(pkt.http, 'host') else '-'
            uri = pkt.http.request_uri if _has_field(pkt.http, 'request_uri') else '/'
            print(f"  {host}{uri}")
            n += 1
    _safe_close(cap)
    print(f"\n共解密 {n} 个 HTTP 请求")


# ---- 7. USB HID 键盘还原 --------------------------------------------------
# 标准 USB HID 键盘扫描码 -> (小写, 大写)
_USB_KEYMAP = {
    0x04: ('a', 'A'), 0x05: ('b', 'B'), 0x06: ('c', 'C'), 0x07: ('d', 'D'),
    0x08: ('e', 'E'), 0x09: ('f', 'F'), 0x0a: ('g', 'G'), 0x0b: ('h', 'H'),
    0x0c: ('i', 'I'), 0x0d: ('j', 'J'), 0x0e: ('k', 'K'), 0x0f: ('l', 'L'),
    0x10: ('m', 'M'), 0x11: ('n', 'N'), 0x12: ('o', 'O'), 0x13: ('p', 'P'),
    0x14: ('q', 'Q'), 0x15: ('r', 'R'), 0x16: ('s', 'S'), 0x17: ('t', 'T'),
    0x18: ('u', 'U'), 0x19: ('v', 'V'), 0x1a: ('w', 'W'), 0x1b: ('x', 'X'),
    0x1c: ('y', 'Y'), 0x1d: ('z', 'Z'),
    0x1e: ('1', '!'), 0x1f: ('2', '@'), 0x20: ('3', '#'), 0x21: ('4', '$'),
    0x22: ('5', '%'), 0x23: ('6', '^'), 0x24: ('7', '&'), 0x25: ('8', '*'),
    0x26: ('9', '('), 0x27: ('0', ')'),
    0x28: ('\n', '\n'), 0x29: ('[ESC]', '[ESC]'), 0x2a: ('[BKSP]', '[BKSP]'),
    0x2b: ('\t', '\t'), 0x2c: (' ', ' '),
    0x2d: ('-', '_'), 0x2e: ('=', '+'), 0x2f: ('[', '{'), 0x30: (']', '}'),
    0x31: ('\\', '|'), 0x33: (';', ':'), 0x34: ("'", '"'),
    0x36: (',', '<'), 0x37: ('.', '>'), 0x38: ('/', '?'),
}


def usb_keyboard(path):
    print("\n" + "=" * 60)
    print("[7] USB HID 键盘还原")
    print("=" * 60)

    cap = _cap(path, display_filter='usb.capdata or usbhid.data')
    buf = []
    for pkt in cap:
        if _has_layer(pkt, 'usbhid') and _has_field(pkt.usbhid, 'data'):
            capdata = pkt.usbhid.data
        elif _has_layer(pkt, 'usb') and _has_field(pkt.usb, 'capdata'):
            capdata = pkt.usb.capdata
        else:
            continue
        if not capdata:
            continue
        hex_str = capdata.replace(':', '')
        if len(hex_str) < 16:
            continue
        shift = (int(hex_str[0:2], 16) & 0x22) != 0  # left/right shift
        # 字节 2..7 是最多 6 个同时按下的键
        for i in range(2, 8):
            code = int(hex_str[i * 2:i * 2 + 2], 16)
            if code == 0:
                continue
            if code in _USB_KEYMAP:
                buf.append(_USB_KEYMAP[code][1 if shift else 0])
                break  # 一个事件只取第一个非零键
    _safe_close(cap)

    text = ''.join(buf)
    print(f"\n还原结果: {text}")


# ---- 8. 反弹 Shell / 可疑端口 --------------------------------------------
REV_SHELL_PORTS = {4444, 5555, 6666, 7777, 8888, 9999, 1234, 31337, 9001, 1337}


def reverse_shell(path, extra_ports=None):
    print("\n" + "=" * 60)
    print("[8] 反弹 Shell / 可疑端口检测")
    print("=" * 60)

    ports = set(REV_SHELL_PORTS)
    if extra_ports:
        ports |= set(extra_ports)

    cap = _cap(path, display_filter='tcp.flags.syn == 1 and tcp.flags.ack == 0')
    hits = []
    for pkt in cap:
        try:
            dp = int(pkt.tcp.dstport)
        except Exception:
            continue
        if dp in ports:
            hits.append((pkt.ip.src, pkt.ip.dst, dp))
    _safe_close(cap)

    if hits:
        for s, d, p in hits:
            print(f"  [!] {s} -> {d}:{p}")
    else:
        print("  [-] 未发现 SYN 到可疑端口")


# ---- CLI -----------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description='CTF 流量取证脚本',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument('pcap', help='pcap / pcapng 文件路径')
    parser.add_argument('--all', action='store_true', help='除 TCP dump 外全部跑一遍')
    parser.add_argument('--overview', action='store_true')
    parser.add_argument('--flag', action='store_true')
    parser.add_argument('--http', action='store_true')
    parser.add_argument('--dns', action='store_true')
    parser.add_argument('--tcp', metavar='STREAM_ID', help='列出 TCP 流；指定 stream id 则还原')
    parser.add_argument('--tls-sni', action='store_true')
    parser.add_argument('--tls-keylog', metavar='FILE', help='用 SSLKEYLOGFILE 解密 HTTPS')
    parser.add_argument('--usb', action='store_true')
    parser.add_argument('--reverse-shell', action='store_true')
    parser.add_argument('--port', type=int, action='append', help='追加可疑端口，可多次')

    args = parser.parse_args()
    if not os.path.exists(args.pcap):
        print(f"[-] 文件不存在: {args.pcap}")
        sys.exit(1)

    if args.all:
        args.overview = args.flag = args.http = args.dns = True
        args.tls_sni = True
        args.reverse_shell = True

    if args.overview:
        overview(args.pcap)
    if args.flag:
        search_flag(args.pcap)
    if args.http:
        http_extract(args.pcap)
    if args.dns:
        dns_tunnel(args.pcap)
    if args.tcp is not None:
        if args.tcp == '' or args.tcp.lower() == 'list':
            tcp_streams(args.pcap)
        else:
            tcp_dump_stream(args.pcap, int(args.tcp))
    if args.tls_sni:
        tls_sni(args.pcap)
    if args.tls_keylog:
        tls_decrypt_http(args.pcap, args.tls_keylog)
    if args.usb:
        usb_keyboard(args.pcap)
    if args.reverse_shell:
        reverse_shell(args.pcap, args.port)

    if not any([args.all, args.overview, args.flag, args.http, args.dns,
                args.tcp, args.tls_sni, args.tls_keylog, args.usb,
                args.reverse_shell]):
        parser.print_help()


if __name__ == "__main__":
    main()

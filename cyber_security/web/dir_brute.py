#!/usr/bin/env python3
"""
目录遍历爆破脚本
用于 CTFHub 目录遍历类题目，URL 中包含数字目录需要枚举
支持探测隐藏目录（以 . 开头）和隐藏文件

用法:
  python3 dir_brute.py <基础URL> <目录层级深度> <每层范围> [--hidden]

示例:
  python3 dir_brute.py http://target.com/flag_in_here/ 3 5
  python3 dir_brute.py http://target.com/flag_in_here/ 3 5 --hidden
"""

import sys
import re
import requests
from itertools import product

# 常见隐藏目录名
HIDDEN_DIRS = [
    ".git", ".svn", ".flag", ".hidden", ".bak", ".backup",
    ".old", ".swp", ".htaccess", ".passwd", ".secret",
    ".admin", ".config", ".data", ".private", ".tmp",
]

# 常见隐藏文件名
HIDDEN_FILES = [
    ".flag", ".flag.txt", "flag.txt", ".hidden_flag",
    "index.php.bak", ".index.php.swp", "index.php~",
    ".htaccess", ".passwd", ".secret", ".env",
    "web.config", ".DS_Store", "robots.txt",
]


def parse_links(html: str, base_url: str) -> list:
    """从目录索引页面解析出链接"""
    links = []
    # 匹配 <a href="xxx"> 格式
    for match in re.findall(r'<a\s+href="([^"]+)"', html):
        if match in ("../", "./", "/"):
            continue
        links.append(match)
    return links


def brute_dirs(base_url: str, depth: int, range_size: int, scan_hidden: bool = False):
    print(f"[*] 基础URL: {base_url}")
    print(f"[*] 目录深度: {depth}")
    print(f"[*] 每层范围: 1-{range_size}")
    print(f"[*] 探测隐藏: {'是' if scan_hidden else '否'}")
    print(f"[*] 总组合数: {range_size ** depth}")
    print("[*] 开始遍历...\n")

    nums = range(1, range_size + 1)
    count = 0
    found = []

    for combo in product(nums, repeat=depth):
        count += 1
        path = "/".join(str(n) for n in combo)
        url = f"{base_url}{path}/"

        try:
            r = requests.get(url, timeout=10)
        except requests.RequestException:
            continue

        if r.status_code == 200:
            if "flag" in r.text.lower() or "ctfhub" in r.text.lower():
                print(f"[+] 找到! {url} (HTTP {r.status_code})")
                print(f"[+] 响应内容:")
                print(r.text[:500])
                print()
                found.append(url)
            else:
                print(f"[*] 200 OK: {url}")

            # 从页面解析链接，查找可能的文件
            links = parse_links(r.text, url)
            for link in links:
                if link.endswith("/"):
                    continue  # 子目录，跳过
                # 这是一个文件链接，请求它
                file_url = url + link
                try:
                    fr = requests.get(file_url, timeout=10)
                    if fr.status_code == 200 and ("flag" in fr.text.lower() or "ctfhub" in fr.text.lower()):
                        print(f"[+] 找到flag文件! {file_url}")
                        print(f"[+] 响应内容:")
                        print(fr.text[:500])
                        print()
                        found.append(file_url)
                except requests.RequestException:
                    pass

            # 探测隐藏目录和文件
            if scan_hidden:
                for hdir in HIDDEN_DIRS:
                    hurl = url + hdir + "/"
                    try:
                        hr = requests.get(hurl, timeout=10)
                        if hr.status_code == 200:
                            print(f"[+] 隐藏目录! {hurl}")
                            if "flag" in hr.text.lower() or "ctfhub" in hr.text.lower():
                                print(f"[+] 隐藏目录含flag!")
                                print(hr.text[:500])
                                found.append(hurl)
                    except requests.RequestException:
                        pass

                for hfile in HIDDEN_FILES:
                    hfile_url = url + hfile
                    try:
                        hr = requests.get(hfile_url, timeout=10)
                        if hr.status_code == 200:
                            print(f"[+] 隐藏文件! {hfile_url}")
                            if "flag" in hr.text.lower() or "ctfhub" in hr.text.lower():
                                print(f"[+] 隐藏文件含flag!")
                                print(hr.text[:500])
                                found.append(hfile_url)
                    except requests.RequestException:
                        pass

        elif r.status_code == 403:
            # 403 目录存在，探测隐藏内容
            if scan_hidden:
                for hfile in HIDDEN_FILES:
                    hfile_url = url + hfile
                    try:
                        hr = requests.get(hfile_url, timeout=10)
                        if hr.status_code == 200:
                            print(f"[+] 403目录下的隐藏文件! {hfile_url}")
                            if "flag" in hr.text.lower() or "ctfhub" in hr.text.lower():
                                found.append(hfile_url)
                    except requests.RequestException:
                        pass

        if count % 50 == 0:
            print(f"[.] 已尝试 {count}/{range_size ** depth}...")

    print(f"\n[*] 遍历完毕，共尝试 {count} 个路径")
    if found:
        print(f"[+] 共找到 {len(found)} 个flag位置:")
        for f in found:
            print(f"    {f}")
    else:
        print("[-] 未找到flag，尝试加大范围或使用 --hidden 参数")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python3 dir_brute.py <基础URL> <目录深度> <每层范围> [--hidden]")
        print("示例: python3 dir_brute.py http://target.com/flag_in_here/ 3 5")
        print("      python3 dir_brute.py http://target.com/flag_in_here/ 3 5 --hidden")
        sys.exit(1)

    base_url = sys.argv[1]
    depth = int(sys.argv[2])
    range_size = int(sys.argv[3])
    scan_hidden = "--hidden" in sys.argv

    brute_dirs(base_url, depth, range_size, scan_hidden)

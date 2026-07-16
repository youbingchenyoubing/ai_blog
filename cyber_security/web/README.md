# CTFHub HTTP 方向脚本工具集

> 用于 CTFHub Web 入门阶段 HTTP 方向题目的辅助脚本，涵盖请求方法、认证、Cookie、目录遍历、备份文件等题型。

---

## 脚本一览

| 脚本 | 语言 | 用途 | 对应题型 |
|------|------|------|----------|
| `basic_auth_brute.sh` | Bash | Basic Auth 暴力破解 | 基础认证 |
| `basic_auth_brute.py` | Python | Basic Auth 暴力破解 | 基础认证 |
| `dir_brute.py` | Python | 目录遍历爆破 | 目录遍历 |
| `backup_scan.py` | Python | 备份文件扫描与自动分析 | 备份文件下载 |
| `basic_search.sh` | Bash | 备份文件快速扫描（一行命令版） | 备份文件下载 |

---

## 1. basic_auth_brute.sh

**用途**：对 HTTP Basic Auth 进行密码字典暴力破解

**用法**：

```bash
bash basic_auth_brute.sh <目标URL> <用户名> <密码字典路径>
```

**示例**：

```bash
bash basic_auth_brute.sh "http://challenge-xxx.ctfhub.com:10800/flag.html" admin ../10_million_password_list_top_100.txt
```

**说明**：
- 逐行读取字典文件中的密码，逐个尝试
- 每尝试 10 次打印进度
- 找到非 401 响应时自动输出密码和响应内容

---

## 2. basic_auth_brute.py

**用途**：同上，Python 版本，更稳定

**用法**：

```python
python3 basic_auth_brute.py <目标URL> <用户名> <密码字典路径>
```

**示例**：

```python
python3 basic_auth_brute.py "http://challenge-xxx.ctfhub.com:10800/flag.html" admin ../10_million_password_list_top_100.txt
```

**说明**：
- 使用 `requests` 库的 `auth` 参数自动处理 Basic Auth
- 支持超时和异常处理
- 找到密码后自动输出 flag

---

## 3. dir_brute.py

**用途**：枚举多层数字目录，查找隐藏的 flag 文件

**用法**：

```python
python3 dir_brute.py <基础URL> <目录深度> <每层范围> [--hidden]
```

**示例**：

```python
# 遍历 /flag_in_here/{1-5}/{1-5}/{1-5}/
python3 dir_brute.py "http://challenge-xxx.ctfhub.com:10800/flag_in_here/" 3 5

# 加上隐藏目录/文件探测
python3 dir_brute.py "http://challenge-xxx.ctfhub.com:10800/flag_in_here/" 3 5 --hidden

# 加大范围
python3 dir_brute.py "http://challenge-xxx.ctfhub.com:10800/flag_in_here/" 3 10 --hidden
```

**参数说明**：

| 参数 | 说明 |
|------|------|
| `基础URL` | 目标目录的 URL，需以 `/` 结尾 |
| `目录深度` | URL 中数字目录的层级数 |
| `每层范围` | 每层目录数字的最大值（从 1 开始） |
| `--hidden` | 可选，启用隐藏目录和隐藏文件探测 |

**功能**：
- 自动枚举所有数字目录组合
- 自动解析目录索引页面中的文件链接并请求
- `--hidden` 模式下探测 `.git`、`.flag`、`.hidden` 等隐藏目录和文件
- 对 403 目录也会尝试探测隐藏文件

---

## 4. backup_scan.py

**用途**：扫描网站备份文件，自动下载并分析内容

**用法**：

```python
python3 backup_scan.py <目标URL>
```

**示例**：

```python
python3 backup_scan.py "http://challenge-xxx.ctfhub.com:10800/"
```

**功能**：
- 自动枚举 `文件名 × 后缀` 组合（web.zip、www.tar.gz、backup.rar 等）
- 找到备份文件后自动下载
- 如果是 zip 文件，自动解压并分析内容
- 发现 flag 文件名后，自动尝试在线访问获取真实 flag

**内置字典**：

| 类别 | 值 |
|------|-----|
| 文件名 | web, website, backup, back, www, wwwroot, temp, site, root, admin, db, data, src, source, code, test, old, new, 1, 0 |
| 后缀 | tar, tar.gz, zip, rar, 7z, gz, bz2, tar.bz2, sql, bak, swp, swo |

---

## 5. basic_search.sh

**用途**：一行命令快速扫描备份文件（轻量版）

**用法**：

```bash
# 修改脚本中的 URL 后直接运行
bash basic_search.sh
```

或直接在命令行使用：

```bash
for name in web website backup back www wwwroot temp; do
  for ext in tar tar.gz zip rar; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://目标URL/${name}.${ext}")
    if [ "$code" != "404" ]; then
      echo "[+] ${name}.${ext} → HTTP $code"
    fi
  done
done
```

**说明**：
- 最轻量，无需 Python 环境
- 只做扫描，不下载分析
- 需手动替换目标 URL

---

## 通用注意事项

1. **URL 用双引号**：命令行传 URL 时务必用双引号 `"http://..."`，不要用反引号
2. **靶机过期**：CTFHub 靶机有过期时间，长时间未操作需重新开启
3. **密码字典**：`basic_auth_brute` 脚本需配合字典文件使用，目录下有 `10_million_password_list_top_100.txt`
4. **依赖**：Python 脚本需要 `requests` 库（`pip install requests`）
5. **速度**：如遇请求过快被限制，可在脚本中增加 `time.sleep()`

---

## 题型与脚本对应速查

| 题型 | 解题思路 | 使用脚本 |
|------|----------|----------|
| 请求方法 | 修改 HTTP Method | `curl -X CTFHUB` |
| 302跳转 | 跟随重定向 | `curl -L` 或 `curl -v` 查看Location头 |
| Cookie | 伪造Cookie | 浏览器F12 / `curl -b "admin=1"` |
| 基础认证 | Basic Auth爆破 | `basic_auth_brute.sh` / `basic_auth_brute.py` |
| 响应头源代码 | 查看HTTP响应头 | `curl -i` / 浏览器F12 Network |
| 目录遍历 | 枚举数字目录 | `dir_brute.py` |
| 备份文件下载 | 枚举备份文件名 | `backup_scan.py` / `basic_search.sh` |

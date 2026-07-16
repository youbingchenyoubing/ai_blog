# CTF Reverse 题型与工具深度实战

> 按 CTF 逆向题的实际出题频率，将题型分为七大类，每类给出：识别特征、解题思路、易踩坑点、工具深度用法。不是工具说明书，是"拿到题怎么想、怎么用工具"的实战地图。

---

## 目录

- [一、题型总览与解题决策树](#一题型总览与解题决策树)
- [二、题型一：算法还原类](#二题型一算法还原类)
- [三、题型二：反调试类](#三题型二反调试类)
- [四、题型三：加壳脱壳类](#四题型三加壳脱壳类)
- [五、题型四：Android 逆向类](#五题型四android-逆向类)
- [六、题型五：非 x86 架构类](#六题型五非-x86-架构类)
- [七、题型六：脚本语言逆向类](#七题型六脚本语言逆向类)
- [八、题型七：混合与特殊类](#八题型七混合与特殊类)
- [九、工具深度用法：IDA Pro](#九工具深度用法ida-pro)
- [十、工具深度用法：Ghidra](#十工具深度用法ghidra)
- [十一、工具深度用法：GDB 动态调试](#十一工具深度用法gdb-动态调试)
- [十二、工具深度用法：angr 符号执行](#十二工具深度用法angr-符号执行)
- [十三、工具深度用法：z3 约束求解](#十三工具深度用法z3-约束求解)
- [十四、工具深度用法：Frida 动态 Hook](#十四工具深度用法frida-动态-hook)
- [十五、工具深度用法：radare2 / rizin](#十五工具深度用法radare2--rizin)
- [十六、解题实战模板](#十六解题实战模板)

---

## 一、题型总览与解题决策树

### 1.1 七大题型按频率排序

| 排序 | 题型 | 出现频率 | 核心难点 | 主力工具 |
|------|------|----------|----------|----------|
| 1 | 算法还原 | ★★★★★ | 识别加密算法、写逆运算 | IDA + z3/angr |
| 2 | 反调试 | ★★★★ | 定位反调试点、绕过 | IDA + GDB/x64dbg |
| 3 | 加壳脱壳 | ★★★★ | 识别壳类型、找 OEP | DIE + UPX + x64dbg |
| 4 | Android 逆向 | ★★★☆ | Java/smali + native .so | jadx + IDA + Frida |
| 5 | 非 x86 架构 | ★★★☆ | ARM/MIPS 汇编阅读 | Ghidra + qemu |
| 6 | 脚本语言逆向 | ★★☆☆ | pyc/Lua/JS 反编译 | uncompyle6/unluac |
| 7 | 混合与特殊 | ★★☆☆ | 组合技、非标格式 | 视情况而定 |

### 1.2 解题决策树

```
拿到题目
  │
  ├─ Step 1：file 看文件类型 → ELF / PE / APK / DEX / .pyc / 其他
  │
  ├─ Step 2：DIE / ExeinfoPE 查壳
  │     ├─ 有壳 → 先脱壳（题型三）
  │     └─ 无壳 → 继续
  │
  ├─ Step 3：strings 找关键线索
  │     ├─ 有 "flag"/"correct"/"wrong" → 字符串定位法
  │     ├─ 有算法特征常量 → 算法识别（题型一）
  │     └─ 无明显字符串 → 可能加密/混淆
  │
  ├─ Step 4：IDA / Ghidra 静态分析
  │     ├─ 代码清晰可读 → 算法还原（题型一）
  │     ├─ 有反调试检测 → 绕过（题型二）
  │     ├─ 架构非 x86 → 换 Ghidra（题型五）
  │     └─ 反编译失败或逻辑混乱 → 动态调试
  │
  └─ Step 5：选择求解方法
        ├─ 算法可逆 → 写解密脚本
        ├─ 约束清晰但逆推复杂 → z3 约束求解
        ├─ 路径明确但输入未知 → angr 符号执行
        └─ 都不行 → 动态调试 + 手动分析
```

---

## 二、题型一：算法还原类

### 2.1 识别特征

```
1. 程序要求输入 → 变换 → 比较 → 输出正确/错误
2. 反编译后能看到完整的加密/校验函数
3. 核心逻辑在一个函数内，或调用标准库函数（AES/DES/RC4/TEA/MD5）
4. 比较点明确（strcmp / memcmp / 逐字符比较）
```

### 2.2 解题思路

```
关键原则：找到比较点，逆推回去

路径 A —— 标准加密算法：
  识别算法 → 调用解密函数 → 得到明文
  识别方法：看特征常量（0x9E3779B9→TEA，0x67452301→MD5/SHA）
  注意：key 从程序中提取，IV/mode 不能搞错

路径 B —— 自定义逐字符变换：
  找到变换公式 → 逐个逆推
  常见变换：XOR、加减常量、查表、位运算组合
  逆推时注意：变换必须可逆（判断是否有信息损失）

路径 C —— 逻辑复杂但约束清晰：
  不逆推算法，直接用 z3 建模求解
  适用于：多变量交织、条件分支多、逐字符校验

路径 D —— 不想读代码：
  angr 符号执行，自动找路径
  适用于：逻辑清晰但写逆推太麻烦
```

### 2.3 常见算法还原速查

#### XOR 加密

```python
# 识别：反编译中看到 cipher[i] ^ key 或 xor 指令
# 特征：key 是固定值或固定数组

# 还原：XOR 自逆
cipher = [0x1a, 0x0b, 0x1e, 0x03, 0x15]
key = [0x66, 0x6c, 0x61, 0x67, 0x7b]

flag = bytes([c ^ k for c, k in zip(cipher, key)])
print(flag)  # b'flag{'
```

#### TEA / XTEA / XXTEA

```python
# 识别：魔数 delta = 0x9E3779B9，循环 32 次，+= / ^= 交替
# 坑点：XTEA 和 TEA 的解密顺序不同，务必确认版本

import struct

def tea_decrypt(v, key):
    """TEA 解密，v 是 8 字节密文，key 是 16 字节密钥"""
    v0, v1 = struct.unpack('>II', v)  # 注意字节序
    k0, k1, k2, k3 = struct.unpack('>IIII', key)
    delta = 0x9E3779B9
    sum_val = (delta * 32) & 0xFFFFFFFF
    for _ in range(32):
        v1 = (v1 - (((v0 << 4) + k2) ^ (v0 + sum_val) ^ ((v0 >> 5) + k3))) & 0xFFFFFFFF
        v0 = (v0 - (((v1 << 4) + k0) ^ (v1 + sum_val) ^ ((v1 >> 5) + k1))) & 0xFFFFFFFF
        sum_val = (sum_val - delta) & 0xFFFFFFFF
    return struct.pack('>II', v0, v1)
```

#### RC4

```python
# 识别：S 盒初始化 for(i=0;i<256;i++) S[i]=i，然后 swap + 异或
# 还原：RC4 加解密相同（对称），用同一 key 再跑一遍

def rc4(data, key):
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) % 256
        S[i], S[j] = S[j], S[i]
    i = j = 0
    out = []
    for byte in data:
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        out.append(byte ^ S[(S[i] + S[j]) % 256])
    return bytes(out)

# RC4 加密 = RC4 解密，key 和 cipher 都从程序提取
flag = rc4(ciphertext, key)
```

#### AES

```python
# 识别：S 盒 0x63,0x7c,0x77,0x7b...，轮常量 0x01,0x02,0x04...
# 还原：用 pycryptodome，注意 mode（ECB/CBC/CTR）和 IV

from Crypto.Cipher import AES

# 从程序中提取 key 和 IV
key = bytes([0x00] * 16)  # 替换为实际 key
iv = bytes([0x00] * 16)   # CBC 模式需要 IV，ECB 不需要

# 确认模式——反编译中看是否有 CBC/ECB 的区分
# CBC：加密前有 XOR 前一块密文的操作
# ECB：每块独立加密

cipher = AES.new(key, AES.MODE_CBC, iv)  # 或 AES.MODE_ECB
flag = cipher.decrypt(ciphertext)
# 去除 PKCS7 填充
pad_len = flag[-1]
flag = flag[:-pad_len]
```

#### Base64 变体

```python
# 识别：标准字符表 ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/
# 变体特征：字符表被替换（换表、换填充字符）

import base64

# 标准 Base64
flag = base64.b64decode(ciphertext)

# 自定义字符表的 Base64
def custom_b64_decode(data, custom_table):
    std_table = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    # 建立映射：自定义表 → 标准表
    trans = str.maketrans(custom_table, std_table)
    return base64.b64decode(data.translate(trans))

# 例：题目用了 !@#$%^&*() 替换了部分字符
custom_table = "ABCDEF...自定义表...+/="
flag = custom_b64_decode(ciphertext, custom_table)
```

### 2.4 坑点与对策

```
坑 1：算法参数藏在多个函数里
  对策：用 IDA 交叉引用追踪 key 的赋值链，不要只看加密函数内部

坑 2：多轮加密——先 AES 再 XOR 再 Base64
  对策：从比较点往前逆推，先逆最后一步再逆倒数第二步，不要跳步

坑 3：key 是动态生成的（如取时间戳、取进程 ID）
  对策：动态调试，在 key 生成后断下提取实际 key 值

坑 4：字节序搞反（大端 vs 小端）
  对策：x86/x64 是小端，网络字节序和部分加密算法是大端
        IDA 中看到的数据是按地址排列的，注意 pack/unpack 的字节序

坑 5：算法有微调（标准 TEA 改了 delta 或轮数）
  对策：不要直接套标准解密函数，逐行对照加密代码确认参数
```

---

## 三、题型二：反调试类

### 3.1 识别特征

```
1. 程序正常运行能输出，调试时行为不同或崩溃
2. 反编译中看到 ptrace / IsDebuggerPresent / NtQueryInformationProcess
3. 程序有多个看似正确的分支，调试时总走错的
4. 运行很快退出，但逻辑上看不应该退出
```

### 3.2 常见反调试手段及绕过

#### Linux 反调试

| 手段 | 代码特征 | 原理 | 绕过方法 |
|------|----------|------|----------|
| ptrace 自检 | `ptrace(PTRACE_TRACEME, 0, 1, 0)` | 一个进程只能被一个 tracer attach | patch ptrace 返回 0，或 NOP 填充调用 |
| /proc/self/status | 读取 TracerPid 字段 | 被调试时 TracerPid 非零 | hook fopen/read 返回伪造内容 |
| /proc/self/stat | 读取第 4 字段 | 同上 | 同上 |
| signal(SIGTRAP) | 发送 SIGTRAP 检测 | 调试器会拦截 SIGTRAP | 在 signal handler 下断观察 |
| 时间检测 | `time() - start > threshold` | 单步执行耗时远超正常 | hook time/gettimeofday 返回固定值 |
| int 3 检测 | 检查代码处是否有 0xCC | 软件断点插入 int 3 指令 | 用硬件断点（hbreak），不插 0xCC |

#### Windows 反调试

| 手段 | 代码特征 | 绕过方法 |
|------|----------|----------|
| IsDebuggerPresent | `if(IsDebuggerPresent())` | 修改返回值为 0，或 patch 跳转 |
| CheckRemoteDebuggerPresent | 同上 | 同上 |
| NtQueryInformationProcess | ProcessDebugPort / ProcessDebugObjectHandle | hook 返回 STATUS_PORT_NOT_SET |
| GetLastError 检测 | 故意触发异常看是否被调试器吞 | 用 ScyllaHide 插件 |
| TLS 回调 | 在 main 前执行检测 | IDA 看 TLS 目录，在 TLS 回调处也下断 |
| BeingDebugged 标志 | PEB.BeingDebugged | x64dbg 用 ScyllaHide 自动清零 |

### 3.3 解题思路

```
Step 1：确认有反调试
  - 不调试直接运行 → 正常输出/等待输入
  - GDB/x64dbg 启动 → 异常退出或输出错误
  → 确认有反调试

Step 2：定位反调试代码
  方法 A：IDA 中搜索反调试 API 名（ptrace/IsDebuggerPresent/...）
  方法 B：在 API 入口下条件断点，看哪个调用触发了检测
  方法 C：单步执行，在异常退出前回溯调用栈

Step 3：绕过
  方法 A —— Patch 静态绕过（推荐，一劳永逸）
    找到检测后的跳转指令 → 修改跳转方向（je→jmp 或 je→jne）
    IDA 中 Edit → Patch program → Assemble
    导出：Edit → Patch program → Apply patches to input file

  方法 B —— Hook 动态绕过
    GDB：在 ptrace/IsDebuggerPresent 入口下断 → 修改返回值后 continue
    Frida：Interceptor.attach 替换函数实现，返回 0

  方法 C —— 环境绕过
    x64dbg：安装 ScyllaHide 插件（自动绕过常见反调试）
    GDB：set environment LD_PRELOAD=./fake_ptrace.so

Step 4：绕过后重新分析
  反调试只影响运行时行为，不影响静态分析
  如果静态分析已经理解逻辑 → 绕过反调试只是为了让程序跑起来验证
```

### 3.4 IDA 中的反调试定位技巧

```
1. Strings 窗口搜索
   /proc/self/status、TracerPid、/proc/self/stat

2. Imports 窗口搜索
   ptrace、IsDebuggerPresent、CheckRemoteDebuggerPresent
   NtQueryInformationProcess、RtlAdjustPrivilege

3. 交叉引用追踪
   在 Imports 中找到 ptrace → X 看谁调用了它 → 跳到调用处
   → 看调用后的分支判断 → 确认是反调试

4. TLS 回调检测
   IDA → View → Open subviews → TLS directory
   如果有 TLS 回调 → 里面可能藏反调试（在 main 前执行）
```

### 3.5 实战绕过脚本

#### GDB 绕过 ptrace

```bash
# 方法 1：在 ptrace 入口下断，修改返回值
gdb ./program
b ptrace
commands 1
  return 0
  continue
end
r

# 方法 2：patch 掉 ptrace 调用
# IDA 中找到 ptrace 调用 → 把 call ptrace 改为 xor eax, eax（返回 0）
```

#### Frida 绕过 Android 反调试

```javascript
// frida -U -l bypass_anti_debug.js -f com.target.app

// 绕过 ptrace
Interceptor.attach(Module.findExportByName(null, "ptrace"), {
    onEnter: function(args) {
        console.log("[*] ptrace called, arg0: " + args[0]);
    },
    onLeave: function(retval) {
        retval.replace(0);  // 返回 0，假装没被调试
    }
});

// 绕过 android.os.Debug.isDebuggerConnected()
Java.perform(function() {
    var Debug = Java.use("android.os.Debug");
    Debug.isDebuggerConnected.implementation = function() {
        return false;
    };
});
```

---

## 四、题型三：加壳脱壳类

### 4.1 识别特征

```
1. DIE / ExeinfoPE 报壳名（UPX / VMP / ASPack / Themida / PECompact ...）
2. IDA 中 .text 段极小，入口点不在正常代码段
3. 节区名异常（UPX0 / UPX1 / .vmp / .nsp0 / .adata）
4. IDA 反编译后只有一小段 stub 代码，后面是大量未识别数据
5. 程序体积异常（比同类功能程序大很多 → 可能 VMP）
```

### 4.2 常见壳与脱壳方法

#### UPX（最常见，CTF 高频）

```bash
# 标准脱壳——一行命令
upx -d packed_file -o unpacked_file

# 脱壳失败的情况及对策：

# 情况 1：UPX 头部标志被修改（出题人改了 "UPX!" 标记）
# 对策：用十六进制编辑器找到被改的标志，恢复为 "UPX!" 后重试
# 定位方法：搜索 UPX0/UPX1 节区名，标志通常在文件末尾附近
xxd packed_file | grep -i "UPX"
# 找到被篡改的标志（如 "UPX." 或 "0UPX"）→ 改回 "UPX!" → 再 upx -d

# 情况 2：修改了 UPX 版本号或压缩选项
# 对策：用 -d 强制脱壳
upx -d -f packed_file -o unpacked_file  # -f 强制

# 情况 3：多层 UPX 壳
# 对策：反复 upx -d，直到 DIE 不再报壳
upx -d layer2 -o layer1
upx -d layer1 -o original
```

#### 自写壳 / 小众壳

```
解题思路——动态脱壳（通用方法）：

Step 1：找 OEP（Original Entry Point，原始入口点）
  方法 A —— 单步跟踪法：
    在当前 EP 下断 → 单步执行 → 观察跳转
    特征：一大段解密循环后，有一个跳转到高地址 → 跳转目标就是 OEP
    壳的解密过程通常是：pushad → 解密循环 → popad → jmp OEP

  方法 B —— ESP 定点法：
    在 EP 下断并运行 → 记录 ESP 值 → 对 ESP 下硬件写入断点
    → 运行 → 断在 popad 之后 → 单步到 jmp → 目标就是 OEP
    原理：壳开始 pushad 保存寄存器，popad 恢复时 ESP 回到原值

  方法 C —— 内存断点法：
    在 .text 段下内存写入断点 → 壳解密时往 .text 写代码会触发
    → 断下后单步到解密循环结束 → 找到 OEP

Step 2：Dump 内存
  x64dbg：跑到 OEP → Scylla 插件 → 选进程 → IAT AutoSearch
          → Get Imports → Dump → 保存
  GDB：跑到 OEP → dump memory result.bin 0x400000 0x401000

Step 3：修复 IAT（Import Address Table）
  Scylla → IAT Autosearch → Get Imports → Fix Dump
  如果自动修复失败 → 手动排查缺漏的导入项

Step 4：验证脱壳结果
  DIE 查壳 → 无壳 → IDA 反编译 → 代码可读 → 成功
```

#### VMP / Themida（高级壳）

```
VMP（VMProtect）和 Themida 是虚拟化保护壳：
  把代码翻译成自定义虚拟机的字节码，运行时由 VM 解释执行
  完全静态脱壳极难，CTF 中一般不要求脱壳

CTF 中的应对策略：
  1. 动态调试 + 内存断点 → 捕获关键数据（flag 比较点）
  2. 不脱壳，直接在运行时找答案
     - 在 strcmp/memcmp 下断 → 程序总要比较 → 断下看参数
     - 在输出函数下断 → 程序总要输出 → 断下回溯
  3. hook 关键函数 → 打印参数
```

### 4.3 脱壳验证清单

```
□ DIE 查壳，确认无壳
□ IDA 反编译 main，代码逻辑是否清晰
□ 字符串窗口是否有预期的字符串（flag/correct/wrong）
□ 交叉引用是否正常（函数调用链完整）
□ 运行脱壳后程序，功能是否正常
```

---

## 五、题型四：Android 逆向类

### 5.1 识别特征

```
1. 题目给 .apk 文件
2. 题目给 .dex 文件
3. 题目给 .so 文件（native 层）
4. 题目给已解包的 Android 项目
```

### 5.2 解题思路

```
Step 1：jadx-gui 打开 APK → 看整体结构
  找到主 Activity → 看关键校验函数
  常见校验位置：
    - onClick 事件处理
    - 自定义 check/verify/validate 函数
    - JNI 调用（System.loadLibrary + native 方法声明）

Step 2：判断校验逻辑在哪层
  Java 层（纯 Java/Kotlin）：
    → 直接读 jadx 反编译的 Java 代码
    → 还原算法或 patch smali

  Native 层（JNI → .so）：
    → IDA 打开 lib/armeabi-v7a/libxxx.so
    → 找到 JNI_OnLoad 或注册的 native 函数
    → 按 native 方法名或 JNI 注册表定位函数

  混淆层（ProGuard / DexGuard）：
    → 类名/方法名被替换为 a/b/c
    → 从调用链反推：看谁调用了系统 API（加密/网络/文件）
    → 或用 Frida hook 运行时追踪

Step 3：选择分析方法
  算法简单 → 静态还原
  算法在 native → IDA 分析 .so + 还原
  有混淆/反调试 → Frida 动态 hook
  需要改逻辑 → apktool 改 smali → 重打包签名
```

### 5.3 JNI 函数定位深度技巧

```
JNI 函数有两种注册方式：

1. 静态注册（最常见）
   函数名格式：Java_包名_类名_方法名
   如：Java_com_example_ctf_Check_verify
   IDA 中直接搜索这个函数名

2. 动态注册（JNI_OnLoad）
   在 JNI_OnLoad 中调用 RegisterNatives
   定位方法：
     IDA 打开 .so → 搜索 JNI_OnLoad → F5 看伪代码
     → 找到 RegisterNatives 调用 → 参数中含方法映射表
     → 映射表结构：{方法名, 签名, 函数指针}
     → 从函数指针定位实际实现

3. 导出表为空的情况
   .so 被剥离了符号表 → 无法通过名字定位
   对策：
     - Frida hook RegisterNatives 打印注册信息
     - 或运行时 hook JNI 调用，打印参数
```

### 5.4 Frida 实战 Hook 模板

```javascript
// frida -U -l hook.js -f com.target.app

// Hook Java 层方法
Java.perform(function() {
    // Hook 指定类的指定方法
    var Checker = Java.use("com.example.ctf.Checker");

    // Hook verify 方法，打印参数和返回值
    Checker.verify.implementation = function(input) {
        console.log("[*] verify called with: " + input);
        var result = this.verify(input);
        console.log("[*] verify returned: " + result);
        return result;  // 原样返回
        // return true;  // 强制返回 true（绕过校验）
    };

    // Hook 加密函数
    var Cipher = Java.use("javax.crypto.Cipher");
    Cipher.doFinal.overload('[B').implementation = function(data) {
        console.log("[*] Cipher.doFinal called");
        console.log("    Input: " + Java.array('byte', data));
        var result = this.doFinal(data);
        console.log("    Output: " + Java.array('byte', result));
        return result;
    };
});

// Hook Native 层函数
Interceptor.attach(Module.findExportByName("libnative.so", "Java_com_example_ctf_Check_verify"), {
    onEnter: function(args) {
        // args[0] = JNIEnv*, args[1] = jobject, args[2] = jstring
        this.input = Java.vm.getEnv().getStringUtfChars(args[2], null).readCString();
        console.log("[*] native verify called with: " + this.input);
    },
    onLeave: function(retval) {
        console.log("[*] native verify returned: " + retval);
    }
});
```

### 5.5 smali 修改绕过校验

```smali
# 原始 smali（校验返回值判断）：
const/4 v0, 0x0
if-eqz v0, :cond_0  # 如果返回 0（false），跳到失败分支

# 修改方案 1：改跳转方向
if-nez v0, :cond_0  # 改成非零时跳转，逻辑反转

# 修改方案 2：强制设为真
const/4 v0, 0x1     # 强制 v0 = 1（true）
if-eqz v0, :cond_0  # 永远不会跳，走成功分支

# 流程：apktool d app.apk → 改 smali → apktool b → 签名 → 安装
```

---

## 六、题型五：非 x86 架构类

### 6.1 识别特征

```
1. file 命令输出 ARM / MIPS / AARCH64 / RISC-V / PowerPC
2. 固件题：给 .bin / .fw / .img 文件
3. 嵌入式题：给 .elf 但架构异常
4. IDA 打开后提示不支持的处理器（Free 版限制）
```

### 6.2 常见架构与工具选择

| 架构 | 常见场景 | 推荐工具 | 运行环境 |
|------|----------|----------|----------|
| ARM (32) | Android .so / IoT 固件 | IDA Pro / Ghidra | qemu-arm |
| AARCH64 | Android 64位 .so / 新型 IoT | IDA Pro / Ghidra | qemu-aarch64 |
| MIPS (32) | 路由器固件 | Ghidra / IDA Pro | qemu-mips |
| RISC-V | 新型 IoT / 教学题 | Ghidra | qemu-riscv |
| PowerPC | 游戏机 / 老设备 | Ghidra | qemu-ppc |

### 6.3 解题思路

```
Step 1：确认架构
  file firmware.bin
  readelf -h firmware.elf  # 看Machine字段

Step 2：选择分析工具
  IDA Pro（有授权）→ 支持最多架构，首选
  Ghidra（免费）→ 内置多架构处理器，ARM/MIPS 支持好
  radare2 → 命令行快速分析，支持架构多

Step 3：处理固件提取（如果给的是 .bin / .img）
  binwalk -e firmware.bin  # 提取内嵌文件系统
  → 得到 squashfs / jffs2 / ubifs 文件系统
  → 在文件系统中找目标二进制

Step 4：阅读非 x86 汇编
  ARM 关键差异：
    - R0-R3 传参（类似 rdi/rsi/rdx/rcx）
    - 指令带条件后缀（MOVEQ / CMPNE）
    - LDR/STR 代替 mov（Load/Store 架构）
    - BL 调用函数，BX LR 返回
  MIPS 关键差异：
    - $a0-$a3 传参，$v0-$v1 返回值
    - 分支延迟槽（branch delay slot）：跳转指令后一条必定执行
    - LW/SW 代替 mov
    - J/JAL 跳转和调用

Step 5：动态调试
  qemu-user 模式运行 + GDB 远程调试
  qemu-arm -g 1234 ./arm_binary  # 启动并在 1234 端口等 GDB
  gdb-multiarch ./arm_binary
  (gdb) set architecture arm
  (gdb) target remote :1234
```

### 6.4 ARM 汇编阅读速查

```
寄存器：
  R0-R3   参数/返回值（类比 x64 的 rdi/rsi/rdx/rcx/rax）
  R4-R11  被调用者保存（类比 rbx/r12-r15）
  R12     临时寄存器（IP）
  R13     栈指针（SP）
  R14     链接寄存器（LR）→ 存返回地址，不需要 push 返回地址
  R15     程序计数器（PC）

常见指令：
  LDR R0, [R1]       → R0 = *R1（加载）
  STR R0, [R1]       → *R1 = R0（存储）
  MOV R0, #0x42      → R0 = 0x42
  ADD R0, R1, R2     → R0 = R1 + R2
  BL func            → 调用函数，LR 存返回地址
  BX LR              → 返回（跳转到 LR）
  CMP R0, R1         → 比较并设置标志
  BEQ label          → 等于时跳转
  BNE label          → 不等于时跳转

Thumb 模式（16位指令，Android .so 常见）：
  识别：指令是 16 位对齐（奇数地址）
  切换：BX Rn 的最低位为 1 → Thumb，为 0 → ARM
```

---

## 七、题型六：脚本语言逆向类

### 7.1 Python 逆向

```
场景 A：给 .pyc 文件

  Step 1：确认 Python 版本
    Python 2.x → uncompyle6
    Python 3.3-3.8 → uncompyle6
    Python 3.9+ → decompyle3 / pycdc

  Step 2：反编译
    uncompyle6 output.pyc      # 直接出源码
    decompyle3 output.pyc      # 3.9+ 用这个
    pycdc output.pyc           # uncompyle6 失败时的备选

  Step 3：反编译失败
    方法 A：dis 模块看字节码
      import dis, marshal
      with open('output.pyc', 'rb') as f:
          f.read(16)  # 跳过头部
          code = marshal.load(f)
      dis.dis(code)

    方法 B：xdis 库（支持更多版本）
      from xdis import disasm
      disasm('output.pyc')


场景 B：给 .exe（PyInstaller 打包）

  Step 1：解包
    python pyinstxtractor.py app.exe
    → 得到 .pyc 文件列表

  Step 2：修复 .pyc 头部（PyInstaller 去掉了 magic number）
    # 从 struct.pyc 复制前 16 字节到目标 .pyc
    # Python 3.8+ 的头部是 16 字节（magic + flags + timestamp + size）

  Step 3：反编译修复后的 .pyc
    uncompyle6 target.pyc


场景 C：给 .pye 文件（Nuitka 编译）

  Nuitka 把 Python 编译成 C 再编译成二进制
  → 本质上是 C 逆向，用 IDA 分析
  → 但变量名和逻辑可能保留 Python 风格
```

### 7.2 Lua 逆向

```
场景：游戏修改 / CTF Misc+Reverse 混合题

  标准 Lua 字节码 → unluac 反编译
    unluac script.luo > script.lua

  修改了 opcode 的 Lua → 需要恢复 opcode 映射
    1. 找到宿主程序的 Lua 虚拟机初始化代码
    2. 提取 opcode 映射表
    3. 用映射表修正 .luo 文件
    4. 再用 unluac 反编译
```

### 7.3 JavaScript / Node.js 逆向

```
场景 A：混淆的 JS 代码

  去混淆工具：
    - js-beautify → 格式化
    - deobfuscator.io → 在线去混淆
    - AST Explorer → 手动分析抽象语法树

  常见混淆手法：
    - 变量名替换（_0x1234 → 用 AST 还原）
    - 字符串数组 + 索引访问 → 提取数组，替换引用
    - 控制流平坦化 → 还原 switch-case 状态机

场景 B：Node.js 编译的 .exe（pkg / nexe）

  pkg 打包 → 用 pkg-fetch 提取或直接解包
  nexe 打包 → 末尾附加的 JS 源码，搜索特征字符串提取
```

---

## 八、题型七：混合与特殊类

### 8.1 Go 语言逆向

```
识别特征：
  - 文件大（Go 静态链接，包含运行时）
  - 函数名格式：main.main / main.check
  - IDA 中有大量 runtime.* 函数
  - 字符串大量内联

解题要点：
  1. Go 的符号表通常保留 → 函数名可读，降低了逆向难度
  2. Go 的字符串结构是 {ptr, len}，不是 C 的 null-terminated
     → IDA 中看到的字符串引用可能是结构体偏移
  3. Go 的调用约定：栈传参（Go 1.17 之前），或寄存器传参（Go 1.17+）
  4. GoReSym 工具可以恢复 Go 二进制的符号信息
```

### 8.2 Rust 逆向

```
识别特征：
  - 函数名被 mangling（如 _ZN4core3str21...E）
  - 大量 panic 相关的检查代码
  - 枚举和匹配编译为跳表

解题要点：
  1. rustfilt 工具可以 demangle Rust 符号名
  2. Rust 的 Result/Option 编译为枚举 → IDA 中看分支逻辑
  3. Rust 的边界检查（panic on overflow）可能干扰分析
     → 可以在 GDB 中 hook panic，确认是否是正常的检查
```

### 8.3 .NET 逆向

```
识别特征：
  - .exe / .dll 但 PE 头中有 CLR 标志
  - DIE 报 .NET 版本

工具：
  dnSpy（首选）→ 反编译 + 调试 + 修改，GUI 一体化
  ILSpy → 纯反编译，轻量

解题流程：
  1. dnSpy 打开 → 自动反编译为 C# 源码
  2. 找到校验函数 → 读逻辑
  3. 修改：右键 → Edit Method → 改 C# 代码 → File → Save Module
  4. 混淆：de4dot 去混淆 → 再用 dnSpy 分析

混淆识别：
  .NET Reactor / ConfuserEx / dotfuscator
  → de4dot 通用去混淆：de4dot obfuscated.exe -o clean.exe
```

### 8.4 Electron / NW.js 逆向

```
识别特征：
  - 给的 exe 很大（包含 Chromium + Node.js）
  - 目录中有 app.asar 文件

解题流程：
  1. 安装 asar 工具：npm install -g @electron/asar
  2. 解包：asar extract app.asar app_src/
  3. 得到 JS 源码 → 分析 JS 逻辑
  4. 关键逻辑在 native 模块 → IDA 分析 .node / .so 文件
```

---

## 九、工具深度用法：IDA Pro

> 基础用法见 [IDA Pro 实战使用指南](IDA_Pro实战使用指南.md)，这里只讲 CTF 逆向场景下的进阶技巧。

### 9.1 快速定位关键代码的五种方法

```
方法 1 —— 字符串引用法（最快，优先用）
  Shift+F12 → 字符串窗口
  搜 "flag" / "correct" / "wrong" / "input" / "password"
  双击字符串 → 在数据段看到字符串
  按 X → 交叉引用 → 跳到引用该字符串的代码

方法 2 —— 导入函数法
  Imports 标签 → 找 strcmp/memcmp/scanf/gets/read
  → X 交叉引用 → 跳到调用点
  适用于：程序没有明显的提示字符串

方法 3 —— 流程图法
  在 main 函数按 F5 反编译 → 空格键切换流程图视图
  流程图中：
    - 两个大分支 → if-else，重点看条件
    - 循环体 → 加密/校验逻辑
    - 调用外部函数 → 跟进去看

方法 4 —— 地址范围法
  看函数列表 → 找到自定义函数（非库函数）
  自定义函数通常集中在一段地址范围
  → 逐个 F5 查看逻辑

方法 5 —— 交叉引用链追踪
  从 main 开始 → 看调用了哪些函数 → 逐层追踪
  IDA 中双击函数名进入 → Ctrl+退格 返回
```

### 9.2 提高可读性的标注技巧

```
重命名（N键）：
  对象           示例
  加密函数       sub_401234 → tea_encrypt
  key 变量       v7 → key
  输入缓冲区     dest → user_input
  比较目标       v15 → expected_flag
  索引变量       v4 → i

改类型（Y键）：
  int *v3 → char *v3        （看到字符串操作）
  __int64 v5 → unsigned int v5  （看到无符号运算）
  int v7[4] → uint32_t key[4]    （加密的 key）

加注释（:键，在伪代码视图中）：
  // TEA 加密，delta = 0x9E3779B9, rounds = 32
  // key 从全局变量 0x405000 读取

创建结构体：
  View → Open subviews → Local types
  Insert → 定义结构体成员
  对变量按 Y → 设为结构体类型
  → 反编译输出会自动按成员访问显示
```

### 9.3 IDAPython 自动化脚本

#### 批量重命名函数

```python
# IDAPython：根据函数内的特征常量自动重命名
import idautils
import idc
import ida_bytes

for func_ea in idautils.Functions():
    func_name = idc.get_func_name(func_ea)
    
    # 检查函数内是否包含 TEA 的 delta 常量
    for head in idautils.FuncItems(func_ea):
        if idc.get_operand_value(head, 1) == 0x9E3779B9:
            idc.set_name(func_ea, "tea_encrypt", ida_name.SN_FORCE)
            print(f"Renamed {func_name} at {hex(func_ea)} to tea_encrypt")
            break
```

#### 提取所有整数常量

```python
# 提取函数中的所有立即数，帮助识别算法特征
import idautils
import idc

def extract_constants(func_ea):
    consts = set()
    for head in idautils.FuncItems(func_ea):
        for i in range(2):  # 两个操作数
            op_type = idc.get_operand_type(head, i)
            if op_type == idc.o_imm:  # 立即数
                val = idc.get_operand_value(head, i)
                if 0x100 < val < 0xFFFFFFFF:  # 过滤太小和太大的
                    consts.add(val)
    return sorted(consts)

# 用法
for c in extract_constants(idc.get_name_ea_simple("main")):
    print(hex(c))
```

#### 批量 XOR 解密字符串

```python
# IDAPython：对指定地址范围进行 XOR 解密
import ida_bytes
import idc

def xor_decrypt_range(start, end, key):
    """对 start~end 范围的数据 XOR 解密，直接修改 IDA 数据库"""
    key_len = len(key)
    for i in range(end - start):
        orig = ida_bytes.get_byte(start + i)
        decrypted = orig ^ key[i % key_len]
        ida_bytes.patch_byte(start + i, decrypted)
    print(f"XOR decrypted {hex(start)}-{hex(end)} with key {key.hex()}")

# 用法：对加密的数据段解密
# xor_decrypt_range(0x402000, 0x402100, b"secret_key")
```

### 9.4 处理反编译失败的技巧

```
情况 1：F5 报错 "positive sp value has been found"
  原因：IDA 分析栈帧出错（函数有动态栈操作或混淆）
  解决：
    - 选中函数 → Edit → Functions → Change stack frame size → 手动修正
    - 或在函数开头按 Alt+P 修改函数属性
    - 或用 Ghidra 试试（反编译器逻辑不同，可能成功）

情况 2：F5 输出全是 goto 和花指令
  原因：编译器优化或混淆
  解决：
    - 从控制流图理解分支逻辑
    - 标注 + 重命名 + 加注释，逐步理清
    - 混淆严重 → 动态调试观察运行时行为

情况 3：函数调用识别错误
  原因：间接调用（call [rax+0x10]）IDA 无法确定目标
  解决：
    - 动态调试，在间接调用处断下 → 看实际调用目标
    - 或从上下文推断：看 rax 的来源 → 是虚表？是函数指针数组？

情况 4：类型推断错误
  原因：IDA 把 char* 推断为 int
  解决：
    - Y 键手动修改类型
    - 创建结构体后应用到变量
```

---

## 十、工具深度用法：Ghidra

### 10.1 Ghidra 的优势场景

```
IDA 什么时候应该换 Ghidra：

1. 非 x86 架构（ARM/MIPS/RISC-V）
   Ghidra 内置的 SLEIGH 处理器支持更多架构

2. F5 反编译失败
   Ghidra 的反编译器逻辑不同，IDA 失败时 Ghidra 可能成功
   反过来也成立——两个工具互补

3. 需要协作分析
   Ghidra 有内置的多人协作（Git 后端），IDA 没有

4. 需要自定义处理器
   Ghidra 的 SLEIGH 语言可以定义新的指令集

5. 没有IDA 授权
   Ghidra 完全开源免费
```

### 10.2 Ghidra 关键操作

```
1. 导入分析
   File → Import → 选二进制 → 双击 → CodeBrowser
   自动分析对话框 → 勾选所有分析器 → Analyze
   等待分析完成（底部进度条）

2. 反编译查看
   左侧 Symbol Tree → Functions → main
   右侧 Decompile 窗口自动显示伪代码

3. 搜索字符串
   Search → For Strings → 搜关键词
   双击结果 → 跳到引用

4. 交叉引用
   在函数/变量上右键 → References → Find References to...

5. 重命名
   在 Decompile 窗口右键变量 → Rename Variable
   在函数上右键 → Rename Function

6. 修改类型
   右键变量 → Retype Variable

7. 导出
   File → Export → C/C++ → 导出反编译结果
```

### 10.3 Ghidra 脚本（Java / Python）

```java
// Ghidra Java 脚本示例：自动搜索特征常量并标注
// Window → Script Manager → New Script

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;

public class FindTEA extends GhidraScript {
    @Override
    public void run() throws Exception {
        long teaDelta = 0x9E3779B9L;
        
        // 遍历所有函数
        for (var func : currentProgram.getFunctionManager().getFunctions(true)) {
            // 遍历函数中的指令
            for (var instr : getInstructions(func.getEntryPoint(), true)) {
                for (int i = 0; i < instr.getNumOperands(); i++) {
                    if (instr.getScalar(i) != null && 
                        instr.getScalar(i).getValue() == teaDelta) {
                        println("TEA delta found in " + func.getName() + 
                                " at " + instr.getAddress());
                    }
                }
            }
        }
    }
}
```

---

## 十一、工具深度用法：GDB 动态调试

> 基础用法见 [GDB+pwndbg 实战使用指南](../pwn/GDB+pwndbg实战使用指南.md)，这里聚焦逆向场景的高级调试手法。

### 11.1 逆向场景下 GDB 的核心用法

```
场景 1：在比较点断下，直接看答案
  # 找到 strcmp 调用的地址（IDA 中看）
  b *0x401234
  r
  # 断下后，rdi 和 rsi 分别是两个字符串参数
  x/s $rdi   # 输入的字符串
  x/s $rsi   # 期望的字符串 → 这就是 flag

场景 2：追踪加密过程
  # 在加密函数入口和出口下断
  b tea_encrypt
  r
  # 入口处看输入
  x/8wx $rdi   # 看输入的 8 字节（TEA 块大小）
  # 在函数出口下断
  b *0x401300   # 加密函数 ret 的地址
  c
  # 出口处看输出
  x/8wx $rdi   # 加密后的数据

场景 3：修改跳转绕过校验
  # 找到 je 指令地址
  b *0x401250
  r
  # 把 je (0x74) 改成 jne (0x75)
  set {char}0x401250 = 0x75
  c
  # 程序走另一分支 → 输出正确结果

场景 4：提取解密后的内存
  # 自解密程序，跑到解密完成后
  b *0x401000   # OEP
  r
  # dump .text 段
  dump memory text_dump.bin 0x401000 0x402000
```

### 11.2 条件断点与自动化

```bash
# 条件断点——只在特定条件下断
b *0x401234 if $rdi == 0x41414141

# 自动化——断下后自动执行命令
b strcmp
commands 1
  printf "strcmp(\"%s\", \"%s\")\n", $rdi, $rsi
  continue
end
r
# 效果：每次 strcmp 都自动打印参数并继续

# 计数断点——跳过前 N 次才断
ignore 1 100   # 断点 1 忽略前 100 次
# 第 101 次才断下，适用于循环中只关心后期的迭代

# 追踪断点——记录每次经过的值
b *0x401234
commands 1
  printf "rax = 0x%lx\n", $rax
  continue
end
```

### 11.3 GDB + pwndbg 逆向增强命令

```bash
# pwndbg 特有命令（逆向中常用的）
vmmap              # 内存映射，找加载地址
telescope $rsp 10  # 递归解引用栈内容（看指针指向什么）
context            # 重新显示上下文（寄存器+代码+栈）
canary             # 查看栈 canary 值
searchmem pattern  # 搜索内存中的模式

# 远程调试（调试 ARM/MIPS 程序）
# 终端 1：启动 qemu + 等待 GDB 连接
qemu-arm -g 1234 ./arm_binary

# 终端 2：GDB 连接
gdb-multiarch ./arm_binary
set architecture arm
target remote :1234
b main
c
```

---

## 十二、工具深度用法：angr 符号执行

### 12.1 angr 适用场景

```
适合用 angr 的情况：
  1. 知道成功分支和失败分支的地址
  2. 程序逻辑复杂但不需要理解细节
  3. 算法逆推太麻烦，想自动求解
  4. 有多条路径，想找能到达目标的那条

不适合用 angr 的情况：
  1. 路径爆炸（循环次数多、分支多）→ angr 会卡住
  2. 程序有系统调用依赖 → angr 的 SimProcedure 可能模拟不准确
  3. 需要理解算法逻辑 → angr 只给答案不给过程
```

### 12.2 进阶用法

#### 指定输入起点和约束

```python
import angr
import claripy

proj = angr.Project('./program', auto_load_libs=False)

# 方法 1：从标准入口开始（最常见）
state = proj.factory.entry_state(
    stdin=angr.SimFile('/dev/stdin', size=64)  # 限制输入长度，加速
)

# 方法 2：从指定地址开始（跳过不相关的初始化代码）
state = proj.factory.blank_state(addr=0x401000)
# 手动设置寄存器和内存
state.regs.rdi = 0x7fffffffe000  # 设置参数
flag = claripy.BVS('flag', 8 * 32)  # 32 字节符号输入
state.memory.store(0x7fffffffe000, flag)  # 存到内存

# 添加约束：输入是可打印字符
for i in range(32):
    byte = flag.get_byte(i)
    state.solver.add(byte >= 0x20, byte <= 0x7e)

# 探索
simgr = proj.factory.simulation_manager(state)
simgr.explore(find=0x401850, avoid=[0x401830, 0x401860])

if simgr.found:
    found = simgr.found[0]
    # 从标准输入获取
    print(found.posix.dumps(0))
    # 从符号变量获取
    print(found.solver.eval(flag, cast_to=bytes))
```

#### 使用 SimProcedure 替代复杂函数

```python
# 当 angr 遇到无法模拟的函数（如自定义校验）时，用 hook 替代

class FakeCheck(angr.SimProcedure):
    def run(self, input_ptr, length):
        # 简化处理：直接返回符号值
        return self.state.solver.BVS("check_result", 32)

proj.hook(0x401000, FakeCheck)  # hook 指定地址的函数
```

#### 处理路径爆炸

```python
# 限制探索深度
simgr = proj.factory.simulation_manager(state)
simgr.explore(find=0x401850, avoid=0x401830)

# 或手动步进控制
for i in range(1000):  # 最多 1000 步
    if simgr.found:
        break
    simgr.step()

# 合并路径（path merging）减少状态数
simgr.merge(stashed='merge')

# 设置探索策略
simgr.use_technique(angr.exploration_techniques.DFS())  # 深度优先
simgr.use_technique(angr.exploration_techniques.BFS())  # 广度优先
```

### 12.3 angr 调试技巧

```python
# 查看当前活跃状态数
print(len(simgr.active))

# 查看各状态的当前位置
for s in simgr.active:
    print(hex(s.addr))

# 查看某个状态的历史路径
for addr in simgr.active[0].history.recent_bbl_addrs:
    print(hex(addr))
```

---

## 十三、工具深度用法：z3 约束求解

### 13.1 z3 适用场景

```
适合用 z3 的情况：
  1. 逐字符校验——每个字符有独立的约束
  2. 已知算法逻辑，只需要反解输入
  3. 约束条件能从反编译代码中提取
  4. 多变量交织，手动逆推容易出错

z3 vs angr 选择：
  - 约束清晰 → z3（更可控、更快）
  - 约束模糊 → angr（自动探索路径）
  - 约束极多 → 先试试 z3，超时再换 angr
```

### 13.2 常见约束建模模式

#### 模式 1：逐字符校验（最常见）

```python
from z3 import *

flag_len = 32
flag = [BitVec(f'f{i}', 8) for i in range(flag_len)]

s = Solver()

# 约束：可打印 ASCII
for c in flag:
    s.add(c >= 0x20, c <= 0x7e)

# 约束：flag{} 格式
s.add(flag[0] == ord('f'))
s.add(flag[1] == ord('l'))
s.add(flag[2] == ord('a'))
s.add(flag[3] == ord('g'))
s.add(flag[4] == ord('{'))
s.add(flag[31] == ord('}'))

# 从反编译代码逐条添加约束
# 示例：flag[i] ^ flag[i+1] == target[i]
target = [0x12, 0x34, 0x56, ...]  # 从程序提取
for i in range(5, 30):
    s.add(flag[i] ^ flag[i+1] == target[i-5])

if s.check() == sat:
    m = s.model()
    result = ''.join(chr(m[c].as_long()) for c in flag)
    print(f"flag = {result}")
else:
    print("No solution")
```

#### 模式 2：整数运算约束

```python
from z3 import *

# 32 位整数运算
x = BitVec('x', 32)
s = Solver()

# 模拟反编译中的运算链
# v1 = x * 0xDEADBEEF
# v2 = v1 + 0x12345678
# v3 = v2 ^ 0xCAFEBABE
# v4 = (v3 << 3) | (v3 >> 29)   # 循环左移 3 位
# assert v4 == 0x13371337

v1 = x * 0xDEADBEEF
v2 = v1 + 0x12345678
v3 = v2 ^ 0xCAFEBABE
v4 = (v3 << 3) | (LShR(v3, 29))  # 注意：>> 是算术右移，LShR 是逻辑右移

s.add(v4 == 0x13371337)

if s.check() == sat:
    print(f"x = {s.model()[x]}")
```

#### 模式 3：数组/内存约束

```python
from z3 import *

# 模拟查表操作
table = [BitVec(f't{i}', 32) for i in range(256)]  # 256 项的表
inp = BitVec('inp', 8)
out = BitVec('out', 32)

s = Solver()

# 表的内容已知（从程序中提取）
known_table = [0x12, 0x34, 0x56, ...]  # 256 个值
for i in range(256):
    s.add(table[i] == known_table[i])

# 约束：out = table[inp]
# z3 不支持直接用 BitVec 做数组索引，需要用 If 链
table_lookup = known_table[0]  # 默认值
for i in range(256):
    table_lookup = If(inp == i, known_table[i], table_lookup)

s.add(table_lookup == 0x42)  # 期望的输出值

if s.check() == sat:
    m = s.model()
    print(f"inp = {m[inp]} ({chr(m[inp].as_long())})")
```

### 13.3 z3 性能优化

```python
# 1. 尽早添加约束，减少搜索空间
# 先加 flag{...} 格式约束，再加算法约束

# 2. 拆分独立约束，分别求解
# 如果 flag[0:8] 和 flag[8:16] 的约束完全独立
# → 分成两个 Solver 分别求解，再合并

# 3. 用 Int 代替 BitVec（如果不需要位运算）
# Int 的求解通常比 BitVec 快

# 4. 设置超时
s.set("timeout", 30000)  # 30 秒超时（毫秒）
result = s.check()
if result == unknown:
    print("Timeout or unknown")

# 5. 用 incremental 模式（push/pop）
s.push()       # 保存当前约束状态
s.add(extra_constraint)
# ... 求解
s.pop()        # 恢复到 push 时的状态
```

---

## 十四、工具深度用法：Frida 动态 Hook

### 14.1 Frida 在逆向中的核心价值

```
Frida 解决的问题：
  1. 反调试绕过——hook 反调试函数，修改返回值
  2. 算法参数提取——hook 加密函数，打印 key/IV/输入/输出
  3. 校验绕过——hook 校验函数，强制返回 true
  4. 运行时追踪——自动记录所有函数调用和参数
  5. 内存搜索——在运行时搜索特定数据（flag 在内存中的位置）
```

### 14.2 Linux / Windows 进程 Hook

```javascript
// frida -p <PID> -l hook.js
// 或 frida ./program -l hook.js

// Hook strcmp——每次比较都打印
Interceptor.attach(Module.findExportByName(null, "strcmp"), {
    onEnter: function(args) {
        this.s1 = args[0].readUtf8String();
        this.s2 = args[1].readUtf8String();
    },
    onLeave: function(retval) {
        console.log(`strcmp("${this.s1}", "${this.s2}") = ${retval}`);
        // 如果 s2 看起来像 flag → 输出它
        if (this.s2 && this.s2.includes("flag")) {
            console.log("[!!!] FLAG FOUND: " + this.s2);
        }
    }
});

// Hook 自定义函数（按地址）
var base = Module.findBaseAddress("program");
var check_addr = base.add(0x1234);  // IDA 中的偏移

Interceptor.attach(check_addr, {
    onEnter: function(args) {
        console.log("[*] check called");
        console.log("    arg0: " + args[0]);
        console.log("    arg1: " + args[1]);
    },
    onLeave: function(retval) {
        console.log("    return: " + retval);
        // retval.replace(1);  // 强制返回 1
    }
});
```

### 14.3 内存搜索

```javascript
// 在进程内存中搜索包含 "flag{" 的字符串
Memory.scan(Process.enumerateRanges('r--'), "flag{", {
    onMatch: function(address, size) {
        console.log("[!!!] Found at: " + address);
        console.log("    Content: " + address.readUtf8String());
    },
    onComplete: function() {
        console.log("[*] Scan complete");
    }
});

// 搜索特定字节模式
// 如搜索 0x66 0x6c 0x61 0x67（"flag" 的十六进制）
Memory.scan(Process.enumerateRanges('r--'), "66 6c 61 67", {
    onMatch: function(address, size) {
        console.log("[!!!] Found 'flag' at: " + address);
        console.log("    Context: " + address.readUtf8String());
    },
    onComplete: function() {}
});
```

### 14.4 追踪模式（Stalker）

```javascript
// Stalker：追踪线程执行过的基本块
Stalker.follow(Process.getCurrentThreadId(), {
    transform: function(iterator) {
        var instruction;
        while ((instruction = iterator.next()) !== null) {
            // 记录每条指令的地址
            iterator.putCallout(function(context) {
                // 只记录感兴趣的地址范围
                // send(context.pc);
            });
        }
    }
});
```

---

## 十五、工具深度用法：radare2 / rizin

### 15.1 radare2 在逆向中的定位

```
radare2 的优势：
  1. 命令行操作——适合 SSH 远程分析 / 脚本自动化
  2. 多架构支持——ARM/MIPS/RISC-V/GameBoy/Z80 等
  3. 轻壳能力——内置 UPX/APK 脱壳
  4. 管道友好——输出可管道到其他工具

什么时候用 radare2：
  - SSH 到远程服务器分析（无 GUI）
  - 需要脚本自动化分析大量文件
  - IDA/Ghidra 不支持的架构
  - 快速看一眼（r2 -q -c "aaa;pdf@main" file）
```

### 15.2 radare2 逆向常用命令

```bash
# 启动
r2 -A program         # -A 自动分析（相当于 IDA 的自动分析）

# 信息查看
ii                    # 导入函数
iE                    # 导出函数
iz                    # 字符串
iS                    # 段信息

# 导航
s main                # 跳到 main 函数
s 0x401234            # 跳到地址
sf sym.func           # 跳到符号

# 反编译
pdf                   # 反汇编当前函数
pdr                   # 递归反汇编（含调用的子函数）
pd 20                 # 反汇编 20 条指令
VV                    # 可视化流程图（类似 IDA 流程图视图）

# 反编译为伪代码（需要 r2ghidra 插件）
r2 -AA program
af @ main             # 分析 main
pdg @ main            # Ghidra 反编译输出伪代码

# 交叉引用
axt @ sym.func        # 查看谁调用了这个函数
axf @ sym.func        # 查看这个函数调用了谁

# 重命名
afn new_name          # 重命名当前函数
avn new_name          # 重命名当前变量

# 搜索
/x flag               # 搜索字符串
/w 0x9E3779B9         # 搜索十六进制常量

# 调试
r2 -d program         # 调试模式
db main               # 下断点
dc                    # 继续执行
ds                    # 单步
dr                   # 查看寄存器
px 32 @ rsp           # 查看栈内存
```

---

## 十六、解题实战模板

### 16.1 一键信息收集脚本

```bash
#!/bin/bash
# CTF 逆向题一键信息收集
# 用法：./recon.sh target_binary

TARGET=$1
echo "=== File Type ==="
file $TARGET

echo -e "\n=== Strings ==="
strings $TARGET | head -50
echo "..."
strings $TARGET | grep -iE "flag|correct|wrong|password|key|input"

echo -e "\n=== ELF Info ==="
readelf -h $TARGET 2>/dev/null

echo -e "\n=== Symbols ==="
nm $TARGET 2>/dev/null | head -30

echo -e "\n=== Sections ==="
readelf -S $TARGET 2>/dev/null

echo -e "\n=== Security ==="
checksec $TARGET 2>/dev/null || readelf -l $TARGET | grep -i stack

echo -e "\n=== Dynamic Dependencies ==="
ldd $TARGET 2>/dev/null || echo "Static binary or not ELF"
```

### 16.2 z3 通用求解框架

```python
#!/usr/bin/env python3
"""
CTF Reverse 通用 z3 求解框架
使用方法：
  1. 从 IDA 反编译中提取约束条件
  2. 在 add_constraints() 函数中添加
  3. 运行脚本
"""

from z3 import *

FLAG_LEN = 32  # 修改为实际 flag 长度
flag = [BitVec(f'f{i}', 8) for i in range(FLAG_LEN)]

def add_constraints(solver, flag):
    """在这里添加从逆向中提取的约束"""

    # 1. 可打印字符约束
    for c in flag:
        solver.add(c >= 0x20, c <= 0x7e)

    # 2. flag{} 格式约束（如果确认是 flag{} 格式）
    # solver.add(flag[0] == ord('f'))
    # solver.add(flag[1] == ord('l'))
    # solver.add(flag[2] == ord('a'))
    # solver.add(flag[3] == ord('g'))
    # solver.add(flag[4] == ord('{'))
    # solver.add(flag[FLAG_LEN-1] == ord('}'))

    # 3. 从反编译代码逐条添加约束
    # 示例：
    # solver.add(flag[0] ^ flag[1] == 0x0a)
    # solver.add(flag[2] + flag[3] == 0xcc)
    # ... 根据实际题目添加

    pass


def solve():
    s = Solver()
    s.set("timeout", 60000)  # 60 秒超时

    add_constraints(s, flag)

    result = s.check()
    if result == sat:
        m = s.model()
        answer = ''.join(chr(m[c].as_long()) for c in flag)
        print(f"[+] Flag: {answer}")
        return answer
    elif result == unsat:
        print("[-] No solution exists (constraints are contradictory)")
    else:
        print("[?] Timeout or unknown - try simplifying constraints")
    return None


if __name__ == "__main__":
    solve()
```

### 16.3 angr 通用求解框架

```python
#!/usr/bin/env python3
"""
CTF Reverse 通用 angr 求解框架
使用方法：
  1. IDA 中找到成功分支地址（find_addr）
  2. IDA 中找到失败分支地址（avoid_addrs）
  3. 运行脚本
"""

import angr
import sys

def angr_solve(binary_path, find_addr, avoid_addrs=None, input_len=64):
    """
    binary_path: 二进制文件路径
    find_addr: 成功分支地址（如 "Correct!" 的代码地址）
    avoid_addrs: 失败分支地址列表（如 "Wrong!" 的代码地址）
    input_len: 输入长度估计值
    """
    proj = angr.Project(binary_path, auto_load_libs=False)

    # 创建初始状态
    state = proj.factory.entry_state(
        stdin=angr.SimFile('/dev/stdin', size=input_len)
    )

    # 符号执行
    simgr = proj.factory.simulation_manager(state)

    print(f"[*] Exploring: find={hex(find_addr)}, avoid={[hex(a) for a in (avoid_addrs or [])]}")
    simgr.explore(find=find_addr, avoid=avoid_addrs or [])

    if simgr.found:
        found = simgr.found[0]
        # 尝试从 stdout 获取
        try:
            stdout = found.posix.dumps(1).decode('utf-8', errors='ignore')
            if stdout:
                print(f"[+] stdout:\n{stdout}")
        except:
            pass

        # 尝试从 stdin 获取（满足约束的输入）
        try:
            stdin_input = found.posix.dumps(0)
            print(f"[+] stdin (satisfying input): {stdin_input}")
        except:
            pass

        return found
    else:
        print("[-] No path found to target address")
        print(f"[*] Active states: {len(simgr.active)}")
        print(f"[*] Deadended states: {len(simgr.deadended)}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python angr_solve.py <binary> <find_addr> [avoid_addr1,avoid_addr2,...]")
        print("Example: python angr_solve.py ./program 0x401850 0x401830,0x401860")
        sys.exit(1)

    binary = sys.argv[1]
    find = int(sys.argv[2], 16)
    avoid = [int(a, 16) for a in sys.argv[3].split(',')] if len(sys.argv) > 3 else None

    angr_solve(binary, find, avoid)
```

### 16.4 Frida 自动追踪模板

```javascript
// frida -p <PID> -l auto_trace.js
// 自动追踪常见加密/比较函数的参数

var targets = {
    // 标准库函数
    "strcmp": 2, "strncmp": 3, "memcmp": 3,
    "strcpy": 2, "strcat": 2,
    
    // 加密函数
    "AES_encrypt": 3, "AES_decrypt": 3,
    "DES_encrypt": 3, "DES_decrypt": 3,
    "RC4": 3,
};

for (var [name, argc] of Object.entries(targets)) {
    var addr = Module.findExportByName(null, name);
    if (addr) {
        Interceptor.attach(addr, {
            onEnter: function(args) {
                console.log(`[*] ${name} called`);
                for (var i = 0; i < argc; i++) {
                    try {
                        var s = args[i].readUtf8String(64);
                        console.log(`    arg${i} (str): "${s}"`);
                    } catch {
                        console.log(`    arg${i} (val): ${args[i]}`);
                    }
                }
            },
            onLeave: function(retval) {
                console.log(`    → return: ${retval}`);
            }
        });
        console.log(`[+] Hooked ${name} at ${addr}`);
    }
}
```

---

> 逆向的实战能力来自三个层次：第一层是工具操作（知道 IDA 怎么用），第二层是题型套路（知道这题是什么类型、该怎么想），第三层是代码阅读（能看懂反编译出来的东西）。本文覆盖前两层，第三层只能靠多练——每道题都完整标注、重命名、加注释，慢慢就快了。

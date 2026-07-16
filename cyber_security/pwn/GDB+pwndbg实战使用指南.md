# GDB + pwndbg 实战使用指南

> Linux 二进制动态调试的标配组合——GDB 是 GNU 调试器，pwndbg 让它从命令行黑洞变成信息丰富的可视化调试器。CTF PWN/逆向方向、二进制漏洞利用、崩溃分析的必备工具。

---

## 目录

- [一、GDB + pwndbg 是什么](#一gdb--pwndbg-是什么)
- [二、安装与环境配置](#二安装与环境配置)
- [三、核心工作流总览](#三核心工作流总览)
- [四、启动与基本操作](#四启动与基本操作)
- [五、断点管理（break / watch / catch）](#五断点管理break--watch--catch)
- [六、程序执行控制（run / step / continue）](#六程序执行控制run--step--continue)
- [七、寄存器查看与修改](#七寄存器查看与修改)
- [八、内存查看与修改](#八内存查看与修改)
- [九、栈操作与溢出分析](#九栈操作与溢出分析)
- [十、pwndbg 专有命令](#十pwndbg-专有命令)
- [十一、pwntools 配合 GDB 调试](#十一pwntools-配合-gdb-调试)
- [十二、常见题型调试实战](#十二常见题型调试实战)
- [十三、高级技巧：脚本化与自动化](#十三高级技巧脚本化与自动化)
- [十四、实战技巧与注意事项](#十四实战技巧与注意事项)
- [十五、速查表](#十五速查表)

---

## 一、GDB + pwndbg 是什么

### 1. GDB 是什么

GDB（GNU Debugger）是 GNU 项目推出的标准调试器，能对 C/C++/Rust/Go/汇编等编译的程序进行动态调试。核心能力：

- 设置断点，让程序停在指定位置
- 单步执行，逐条指令观察行为
- 查看和修改寄存器、内存、变量
- 分析崩溃原因（core dump）
- 追踪函数调用链（backtrace）

### 2. pwndbg 是什么

pwndbg（PWN Debug）是一个 GDB 插件，专门为二进制安全/PWN 题优化。它解决了一个痛点：**原生 GDB 的默认输出太简陋，调试时看不到上下文**。

pwndbg 安装后自动增强的功能：

| 功能 | 原生 GDB | pwndbg |
|------|----------|--------|
| 停下时显示上下文 | 无（需手动输入命令） | 自动显示寄存器 + 反汇编 + 栈 + 代码 |
| 内存映射 | 手动 `info proc mappings` | `vmmap` 一行命令 |
| 查保护机制 | 外部工具 checksec | 内置 `checksec` |
| 找偏移（cyclic） | 手动计算 | `cyclic` / `cyclic_find` 内置 |
| 搜索 gadget | 切到终端用 ROPgadget | `rop --grep "pop rdi"` |
| 搜索内存 | 手动 `find` | `searchmem` 增强 |

> 💡 **结论**：装了 pwndgb 后 GDB 才真正好用。两者是绑定使用的，不存在"只用 GDB 不用 pwndbg"的场景。

### 3. 适用场景

- **PWN 题**：栈溢出找偏移、ROP 链验证、格式化字符串调试、堆利用跟踪
- **逆向工程**：动态确认逻辑、绕过反调试、脱壳
- **漏洞利用开发**：写 PoC 时逐步验证 payload
- **崩溃分析**：core dump 定位崩溃点、还原调用链

---

## 二、安装与环境配置

### 1. 系统要求

```bash
# 操作系统：Linux（Kali Ubuntu Debian 均可）
# Python：3.7+
# GDB：9.2+（推荐 10+）

# 检查 GDB 版本
gdb --version
# GNU gdb (Ubuntu 13.1-0ubuntu2) 13.1 ...
```

### 2. 安装 pwndbg

```bash
# 方法一：一键安装（推荐，官方推荐方式）
git clone https://github.com/pwndbg/pwndbg.git
cd pwndbg
./setup.sh

# 方法二：如果 setup.sh 报权限问题
sudo ./setup.sh

# 方法三：pip 方式安装依赖
pip3 install capstone unicorn ropper
```

### 3. 验证安装

```bash
# 启动 GDB，看到 pwndbg 标志说明安装成功
gdb
# pwndbg: loaded 186 commands. Type pwndbg [filter] for a list.
# pwndbg: created $rebase, $ida GDB functions (can be used with print/break)
```

### 4. 可选增强插件（推荐安装）

```bash
# Pwngdb — 额外辅助命令（heap 视图等）
git clone https://github.com/scut-robot/Pwngdb.git
cp Pwngdb/.gdbinit ~/

# gef — 另一个 GEB 增强框架（和 pwndbg 二选一，不要同时装）
# pip3 install gef
# source ~/.gef.py

# 注意：pwndbg 和 gef 冲突！只能选一个
# 推荐 pwndbg（更新更活跃、社区更大）
```

### 5. 配置 .gdbinit

~/.gdbinit 是 GDB 启动时自动执行的配置文件：

```bash
cat >> ~/.gdbinit << 'EOF'
# 基本设置
set disassembly-flavor intel    # 用 Intel 语法（AT&T 默认，Intel 更直观）
set pagination off              # 关闭分页（避免按回车）
set confirm off                 # 不确认退出
set follow-fork-mode child      # fork 时跟子进程（fork server 场景）

# 显示设置
set print pretty on             # 结构体美观打印
set print array on              # 数组完整打印
set print array-indexes on      # 数组带索引

# 历史
set history save on
set history size 10000

# pwndbg 会自动加载，不需要手动 source
# 如果需要额外配置：
# set resolve-heap-via heuristic   # pwndbg 堆解析策略
EOF
```

### 6. Kali Linux 特殊情况

```bash
# Kali 通常已预装 GDB，但版本可能较旧
# 升级 GDB
# pwndbg 在 Kali 上直接 git clone + setup.sh 即可

# 如果遇到 capstone 编译错误
sudo apt install -y python3-dev libcapstone-dev
```

---

## 三、核心工作流总览

PWN 题标准调试流程：

1. **查保护**：`checksec ./pwn` 看 NX/PIE/Canary/RELRO
2. **启动 GDB**：`gdb ./pwn`
3. **设断点**：在漏洞函数或危险函数处 `b vuln` 或 `b *0x401234`
4. **运行**：`r < input.txt` 或直接 `r` 再手动输入
5. **触发漏洞**：输入超长数据，观察崩溃
6. **分析崩溃**：看寄存器状态（哪个被覆盖）、看栈内容（返回地址在哪）、看内存映射（哪些段可执行）
7. **验证 payload**：在 GDB 中构造 payload 测试，确认能跳转到目标地址
8. **写完整 exp**：回到 pwntools 写自动化脚本

---

## 四、启动与基本操作

### 1. 启动方式

```bash
# 最常用：指定二进制文件启动
gdb ./pwn

# 启动并立即运行
gdb -q ./pwn -ex 'r'

# 启动并加载脚本
gdb -q ./pwn -x my_script.gdb

# 附加到正在运行的进程
gdb -q -p $(pgrep pwn)

# 分析 core dump
gdb -q ./pwn core

# pwntools 方式（推荐，详见第十一章）
python3 exp.py GDB
```

### 2. 命令简写

GDB 支持命令缩写，常用简写：

```bash
b       → break          # 断点
r       → run            # 运行
c       → continue       # 继续
s       → step           # 单步进入函数
n       → next           # 单步跳过函数
ni      → nexti          # 单条指令（不进入）
si      → stepi          # 单条指令（进入 call）
fin     → finish         # 执行完当前函数返回
q       → quit           # 退出
p       → print          # 打印
x       → examine        # 检查内存
disas   → disassemble    # 反汇编
info    → info           # 信息查询
set     → set            # 设置
del     → delete         # 删除断点
```

### 3. 帮助系统

```bash
help break        # 查看 break 命令的帮助
help x            # 查看 examine 内存命令的帮助
apropos heap      # 搜索包含 heap 的命令
# pwndbg 专用：
pwndbg [filter]    # 列出所有 pwndbg 命令（可用 filter 过滤）
pwndbg stack       # 只看栈相关命令
pwndbg heap        # 只看堆相关命令
```

### 4. 退出与中断

```bash
(q)                  # 输入 q 回车退出
quit                 # 同上

# 运行中暂停（不退出）
Ctrl+C               # 暂停程序，回到 GDB 提示符
# 之后可以 c 继续运行
```

---

## 五、断点管理（break / watch / catch）

### 1. 代码断点（breakpoint）

```bash
# 在函数入口处断点
b main
b vuln
b printf

# 在地址处断点
b *0x401234
b *$rip+0x10       # 当前 rip 向后偏移 0x10

# 条件断点（满足条件才停）
b *0x401234 if $rax == 0
b main if argc > 1
b *0x401500 if *(int*)($rsp+8) == 0xdeadbeef

# 临时断点（命中一次后自动删除）
tb main
tb *0x401234

# 查看所有断点
info break
info b

# 删除断点
delete             # 删除所有断点
delete 2           # 删除编号为 2 的断点
clear main          # 清除 main 处的所有断点
clear *0x401234    # 清除该地址的断点

# 禁用 / 启用断点
disable 2          # 禁用 2 号断点
enable 2           # 启用 2 号断点
disable            # 禁用所有
enable             # 启用所有
```

### 2. 数据断点（watchpoint）

当某个内存地址被读取/写入时停下，非常适合追踪谁改了某个值：

```bash
# 监视某个变量/地址被写入
watch *(int*)0x601040        # 写入时停下
watch *(char*)$rsp           # 监视栈顶被写入
watch var_name                # 变量名（有符号表时）

# 监视被读取
rwatch *(int*)0x601040       # 读取时停下

# 读写都监视
awatch *(int*)0x601040       # 读写都停

# 查看监视点
info watchpoints
```

### 3. 捕获断点（catchpoint）

捕获特定事件：

```bash
# 捕获系统调用（非常实用）
catch syscall execve          # 调用 execve 时停下
catch syscall open            # 调用 open 时停下
catch syscall read            # 调用 read 时停下
catch syscall write           # 调用 write 时停下
catch syscall mmap            # 调用 mmap 时停下

# 捕获事件
catch load                    # 加载 .so 时
catch unload                  # 卸载 .so 时
catch fork                    # fork 时
catch exec                    # exec 时

# 捕获信号
handle SIGSEGV nostop         # 段错误不停（继续跑）
handle SIGSEGV stop           # 段错误时停下（默认）
handle SIGTRAP nostop pass    # 忽略断点陷阱信号
```

### 4. 断点命令序列（commands）

命中断点后自动执行一组命令：

```bash
b *0x401234
commands
silent                      # 静默，不打印停下的位置
printf "rax = 0x%lx\n", $rax
printf "rsp = 0x%lx\n", $rsp
x/20gx $rsp
c                           # 继续运行
end

# 实例：每次调用 printf 时打印参数
b printf
commands
silent
printf "fmt=%s\n", (char*)$rdi
c
end
```

---

## 六、程序执行控制（run / step / continue）

### 1. 启动与重启

```bash
r                           # 运行（无参数）
r AAAA                     # 将 AAAA 作为命令行参数
r < input.txt              # 从文件读入作为 stdin
r <<< "hello world"        # here-string 作为输入
r arg1 arg2 < input.txt    # 参数 + 文件输入

# 带环境变量运行
set env MYVAR=1234
r

# 重启（重新运行，保留断点）
r                          # 再次输入 r 即可
```

### 2. 单步执行

```bash
n                           # next：单步（不进入函数调用，相当于"跳过"）
s                           # step：单步（进入函数调用内部）
ni                          # nexti：单条指令（不进入 call）
si                          # stepi：单条指令（进入 call）

# 执行完当前函数返回
fin                         # finish：跑完当前函数并返回
fin 5                       # 但忽略前 5 层帧的信息（加速）
```

### 3. 继续

```bash
c                           # continue：继续运行直到下一个断点
c 100                       # 忽略当前断点 100 次（第 101 次才停）
fg                          # foreground：同 c（前台运行）
```

### 4. 反向执行（需要记录，较慢）

```bash
record full                # 开始记录执行过程（支持反向调试）
# ... 正常调试 ...
reverse-step              # 反向单步
reverse-next              # 反向单步（跳过函数）
reverse-continue          # 反向继续
record stop               # 停止记录
```

### 5. 跳转执行（谨慎使用）

```bash
jump *0x401200            # 强制跳到指定地址执行
jump *main                # 跳回 main 函数
# ⚠️ 这会改变执行流，可能导致不可预期的行为
# 主要用途：跳过某些检查、重试某段逻辑
```

### 6. 调用函数

```bash
# 在目标进程中调用函数
call puts("hello")        # 调用 puts 打印字符串
call malloc(0x100)        # 调用 malloc 分配内存
call system("/bin/sh")    # 直接拿 shell（如果 libc 已加载）
# 返回值在 $rax 中
print/d $rax
```

---

## 七、寄存器查看与修改

### 1. 查看寄存器

```bash
# pwndbg 启动后每次停下来会自动显示所有通用寄寄存器
# 也可以手动查看：

info registers            # 显示所有寄存器
info registers rax rbx    # 只显示指定的

# 打印单个寄存器
p $rax
p/x $rbx                  # 十六进制
p/d $rcx                  # 有符号十进制
p/u $rdx                  # 无符号十进制

# 64 位 vs 32 位访问（同一个寄存器的不同部分）
p $eax                    # rax 低 32 位
p $ax                     # rax 低 16 位
p $al                     # rax 低 8 位
p $ah                     # rax 8-15 位
```

### 2. 修改寄存器

```bash
set $rax = 0x41414141
set $rsp = 0x7fffffffe000
set $rip = 0x401200
set $eflags = 0x246       # 直接设置标志位
```

### 3. 修改单个标志位

```bash
# 设置 ZF = 1
set ($eflags |= (1 << 6))

# 清除 ZF
set ($eflags &= ~(1 << 6))

# 设置 CF = 1
set ($eflags |= 1)

# pwndbg 便捷方式
set $ZF = 1
set $CF = 0
```

### 4. 常用寄存器约定（System V AMD64 ABI）

| 寄存器 | 用途 | 函数调用中的角色 |
|--------|------|------------------|
| rax | 返回值 | 函数返回值 |
| rdi | 第 1 个参数 | 第 1 个整数参数 |
| rsi | 第 2 个参数 | 第 2 个整数参数 |
| rdx | 第 3 个参数 | 第 3 个整数参数 |
| rcx | 第 4 个参数 | 第 4 个整数参数 |
| r8 | 第 5 个参数 | 第 5 个整数参数 |
| r9 | 第 6 个参数 | 第 6 个整数参数 |
| rsp | 栈指针 | 指向栈顶 |
| rbp | 帧指针 | 指向当前栈帧底部 |
| rip | 指令指针 | 指向下一条要执行的指令 |

---

## 八、内存查看与修改

### 1. 检查内存（x 命令，最常用）

```bash
# 格式: x/[数量][格式][大小] 地址

# 格式类型:
#   x  十六进制
#   d  十进制
#   s  字符串
#   i  指令（反汇编）
#   t  二进制
#   o  八进制
#   a  地址
#   c  字符

# 大小:
#   b  字节 (1)
#   h  半字 (2)
#   w  字 (4)
#   g  双字 (8)

# 常用示例:

x/20gx $rsp              # 从 rsp 开始，显示 20 个 8 字节十六进制数（看栈）
x/10wx $rbp-0x20         # 从 rbp-0x20 开始，10 个 4 字节（32 位栈变量）
x/s 0x601040             # 查看字符串（遇到 \0 结束）
x/1s $rax                # 把 rax 当作指针看字符串
x/30i $rip               # 从 rip 开始反汇编 30 条指令
x/b $rip                 # 查看当前位置的字节
x/16xb 0x400000          # 查看 ELF header
```

### 2. pwndbg 增强：telescope

`telescope` 是 pwndbg 的王牌功能，递归解引用查看内容：

```bash
telescope $rsp 20        # 从 rsp 开始递归查看 20 个 QWORD
# 输出示例:
# 00: 00007fffffffde38 │+0x0000: 0x4141414141414141 ("AAAAAAAA")
# 01: 00007fffffffde40 │+0x0008: 0x0000000000401256  →  <vuln+86>
# 02: 00007fffffffde48 │+0x0010: 0x00007ffff7a2d090  →  <__libc_start_main+240>

telescope $rsp 20 4     # 最后一个数字是递归深度（默认 4）

# 对比原生的 x 命令:
# x/20gx $rsp 只显示原始数值
# telescope 会尝试把每个值解释为地址，再显示那个地址的内容
```

### 3. 查看内存映射

```bash
vmmap                        # pwndbg：显示所有内存段（最常用）
vmmap 0x601000              # 查看指定地址属于哪个段
vmmap stack                  # 只看栈段
vmmap heap                   # 只看堆段
vmmap libc                   # 只看 libc 相关段

# 原生 GDB 等价命令（但不好用）:
info proc mappings
cat /proc/<pid>/maps
```

### 4. 修改内存

```bash
# 写入字节
set {char}0x601040 = 0x41
set {short}0x601040 = 0x4242
set {int}0x601040 = 0x42424242
set {long}0x601040 = 0x4141414141414141

# 写入字符串
set {char[8]}0x601040 = "ABCDEFGH"

# 用 printf 写任意字节
printf "%s", "hello" @ 0x601040
printf "\x41\x42\x43\x44" @ 0x601040
```

### 5. 搜索内存

```bash
# pwndbg searchmem（比原生 find 好用）
searchmem 0x41414141       # 搜索 41414141 这个值
searchmem "/bin/sh\x00"    # 搜索字符串

# 原生 find 命令
find /0x601000, 0x602000, 0x41414141
find 0x601000, 0x602000, "/bin/sh"
```

### 6. 堆内存查看（基础）

```bash
# pwndbg 堆命令（需要先分配过内存才能看到）
heap                    # 显示堆布局概要
bins                    # 显示 bins 状态（堆利用时用）
arenas                  # 显示 arena 信息

# 查看特定 chunk
parse_heap             # 解析当前堆状态
```

---

## 九、栈操作与溢出分析

### 1. 栈帧结构理解

```
高地址
┌─────────────────┐
│   参数（caller  │  ← 函数参数（6个以上通过栈传递）
│   压入的第7+个）  │
├─────────────────┤
│   返回地址       │  ← rip 被覆盖就控制执行流
├─────────────────┤
│   保存的 rbp     │  ← rbp 被覆盖影响 caller 的栈帧
├─────────────────┤
│   局部变量       │  ← 缓冲区溢出的源头
│   （缓冲区）     │     gets/scanf/read 写入这里
├─────────────────┤
│   ...           │
└─────────────────┘
低地址  ← rsp（栈顶，向下增长）
```

### 2. cyclic 找偏移

这是 pwndbg 最常用的功能之一——精确找到溢出偏移：

```bash
# 生成 cyclic pattern 并发送（在 pwntools 或手动输入）
# 在 GDB 中崩溃后：

# 方法一：用 pwndbg 的 cyclic_find
# 先记下崩溃时 rsp 或 rip 指向的内容
cyclic_find(0x6161616961616169)   # 把崩溃地址填进去，直接算出偏移
# 输出: Found offset 72

# 方法二：用 pwntools（在 Python 中）
from pwn import *
offset = cyclic_find(0x6161616961616169)
```

### 3. 验证溢出 payload

```bash
# 偏移是 72，目标是 win 函数（地址 0x401176）
# 构造 payload 并测试

# 方法一：Python 里算好贴进来
payload = b'A' * 72 + p64(0x401176)   # 在 pwntools 里算好
# 然后 paste 到 GDB 输入

# 方法二：直接在 GDB 里构造
# 用 run 命令传入 payload
python3 -c "import sys;sys.stdout.buffer.write(b'A'*72+b'\x76\x11\x40\x00\x00\x00\x00\x00')" > payload.bin
gdb ./pwn
r < payload.bin
# 观察是否成功跳到 win 函数
```

### 4. 查看调用栈

```bash
bt                        # backtrace：查看调用栈
bt 10                     # 只显示 10 帧
bt full                   # 同时显示每帧的局部变量
frame 3                   # 切换到第 3 帧的上下文
up                        # 向上一帧（往 caller）
down                      # 向下一帧（往 callee）
info frame                # 当前帧的详细信息
info args                 # 当前帧的函数参数
info locals               # 当前帧的局部变量
```

### 5. 栈溢出排查步骤

```bash
# 1. 在可疑函数入口断点
b vuln
r

# 2. 单步到危险函数（gets/scanf/read）
# n 单步到 read(0, buf, 0x100)

# 3. 记录 buf 的地址和 rbp/返回地址的位置
p &buf
p $rbp
# 计算 offset = 返回地址地址 - buf地址

# 4. 输入超长数据触发溢出
# 观察返回地址是否被覆盖

# 5. 用 cyclic 精确测量
# 发送 cyclic(300)，崩溃后 cyclic_find
```

---

## 十、pwndbg 专有命令

### 1. checksec — 查保护机制

```bash
checksec                  # 查看当前二进制的保护
# 输出示例:
# [*] '/home/user/pwn'
#     Arch:     amd64-64-little
#     RELRO:    Full RELRO
#     Stack:    Canary found
#     NX:       NX enabled
#     PIE:      PIE enabled
```

各保护含义：

| 保护 | 开启时 | 影响 |
|------|--------|------|
| NX | 栈不可执行 | 不能放 shellcode 到栈上执行，必须用 ROP |
| PIE | 地址空间随机化 | 代码/数据地址每次运行不同，需先泄露基址 |
| Canary | 栈金丝雀 | 溢出时会检测到并终止，需泄露 canary 值 |
| Full RELRO | GOT 只读 | 不能通过覆写 GOT 劫持流程，需换目标（hook 等） |
| Partial RELRO | GOT 可写 | 可以覆写 GOT 表项 |

### 2. vmmap — 内存映射

```bash
vmmap
# 典型输出:
# Start              End                Perm             Name
# 0x00400000         0x00401000         r--p             /home/user/pwn
# 0x00401000         0x00402000         r-xp             /home/user/pwn    ← 代码段（可执行）
# 0x00402000         0x00403000         r--p             /home/user/pwn
# 0x00403000         0x00404000         rw-p             /home/user/pwn    ← 数据段（BSS/GOT，可写）
# 0x7f0000000000     0x7f0000010000     rw-p             [heap]            ← 堆
# 0x7ffff7a00000     0x7ffff7bcd000     r-xp             /lib/x86_64-linux-gnu/libc.so.6
# 0x7ffffffdd000     0x7ffffffff000     rw-p             [stack]           ← 栈
```

### 3. cyclic / cyclic_find — 偏移查找

```bash
# 生成指定长度的 cyclic pattern
cyclic 200              # 生成长度 200 的 pattern
cyclic 500 l            # 只生成最后几个字符（用于验证）

# 查找偏移
cyclic_find(0x6161616b6161616a)  # 输入崩溃时的值，得到偏移量
```

### 4. rop — 搜索 ROP gadget

```bash
# 搜索 gadget（内置 ROPgadget 功能）
rop                      # 列出所有 gadget（很长）
rop "pop rdi"            # 搜索 pop rdi 相关 gadget
rop "ret"                # 搜索 ret gadget
rop "pop rsi"            # 搜索 pop rsi

# 结果示例:
# 0x00000000004012a3 : pop rdi ; ret
# 0x00000000004012a1 : pop rbp ; pop rdi ; ret
```

### 5. heap — 堆相关

```bash
heap                     # 堆布局概览
bins                     # bin 状态（unsorted/small/large/fast/tcache）
 arenas                  # arena 信息
 parse_heap              # 详细解析堆块

# 分配追踪
brk                      # brk 段信息
```

### 6. procinfo — 进程信息

```bash
procinfo                 # PID、父PID、进程名、用户等
```

### 7. plt/got — 查看 PLT 和 GOT

```bash
plt                      # 显示 PLT 表
got                      # 显示 GOT 表（含真实地址）
```

### 8. 其他实用命令

```bash
codeaddr                 # 当前代码段的基址（PIE 时有用）
ld                       # ld.so / linker 信息
tls                      # 线程本地存储
distance 0x601000 0x602000   # 计两个地址的距离
hexdump $rsp 0x50        # 十六进制dump（类似 xxd 风格
vmmap libc               # 只看 libc 映射
canary                   # 查看 canary 值
```

---

## 十一、pwntools 配合 GDB 调试

### 1. gdb.attach — 附加到运行的进程

```python
from pwn import *

p = process('./pwn')
# 启动后附加 GDB（会在新终端打开 GDB）
gdb.attach(p, '''
b main
b vuln
c''')

input('按回车继续...')
p.sendline(b'A' * 100)
p.interactive()
```

### 2. gdb.debug — 直接在 GDB 中启动

```python
from pwn import *

# 推荐方式：直接在 GDB 下启动，自动执行 gdbscript
p = gdb.debug('./pwn', gdbscript='''
b *0x401234
b vuln
continue
''')
# 此时已经在 GDB 中，可以直接交互
p.sendline(b'test')
p.interactive()
```

### 3. 通用模板（本地 / 远程 / GDB 三模式切换）

```python
#!/usr/bin/env python3
"""
GDB+pwndbg + pwntools 通用模板
用法:
    python3 exp.py              本地运行
    python3 exp.py GDB          本地 + GDB 调试
    python3 exp.py REMOTE 1.2.3.4 9999   远程
"""
from pwn import *
import sys

context(arch='amd64', os='linux', log_level='info')
context.terminal = ['tmux', 'splitw', '-h']   # GDB 终端配置

BINARY = './pwn'
elf = ELF(BINARY)

def start():
    if args.GDB:
        return gdb.debug(BINARY, gdbscript='''
            b *0x401234
            continue
        ''')
    elif args.REMOTE:
        return remote(args.HOST, int(args.PORT))
    else:
        return process(BINARY)

io = start()

def sla(delim, data): io.sendlineafter(delim, data)
def sa(delim, data): io.sendafter(delim, data)
def ru(delim): return io.recvuntil(delim)

# ====== 你的 exploit 代码 ======
# ...

io.interactive()
```

### 4. tmux 终端配置

GDB 附加需要一个新的终端窗口来显示 GDB。常用配置：

```python
# tmux（推荐，Linux 服务器上最方便）
context.terminal = ['tmux', 'splitw', '-h']   # 水平分屏
context.terminal = ['tmux', 'splitw', '-v']   # 垂直分屏

# GNOME Terminal
context.terminal = ['gnome-terminal', '-x', 'sh', '-c']

# Konsole（KDE）
context.terminal = ['konsole', '-e', 'sh', '-c']

# XTerm
context.terminal = ['xterm', '-e']

# macOS Terminal.app
context.terminal = ['osascript', '-e',
    'tell app "Terminal" to do script "{}"']
```

### 5. GDB 脚本复用

把常用的 GDB 命令保存成脚本文件：

```bash
# 文件: debug_script.gdb
b *0x401234
b vuln
b main
set disassembly-flavor intel
define hook-stop
  telescope $rsp 8
end
continue

# 使用
gdb -q ./pwn -x debug_script.gdb

# 或在 pwntools 中引用
gdbscript=open('debug_script.gdb').read()
p = gdb.debug('./pwn', gdbscript=gdbscript)
```

---

## 十二、常见题型调试实战

### 1. ret2win —— 栈溢出跳转后门函数

场景：存在栈溢出，有一个 win() 函数打印 flag。

```bash
# Step 1: 查保护
checksec ./pwn
# NX enabled, PIE disabled, No canary → 简单题

# Step 2: IDA 确认 win 地址
# win @ 0x401176

# Step 3: GDB 调试找偏移
gdb ./pwn
b *vuln+0x30          # 在 read 返回后断点（大概位置）
r
# 输入 cyclic(200)，观察崩溃
# cyclic_find 得到偏移 = 72

# Step 4: 验证 payload
# 在 GDB 中重新运行
r <<< $(python3 -c "import sys;sys.stdout.buffer.write(b'A'*72+b'\x76\x11\x40\x00\x00\x00\x00\x00')")
# 观察 RIP 是否变成 0x401176（win 函数地址）

# Step 5: 写完整 exp（见 pwntools 指南模板）
```

### 2. ret2libc —— 泄露 libc 基址

场景：NX 开启没有后门函数，需要调用 libc 里的 system("/bin/sh")。

```bash
# Step 1: 查保护
checksec ./pwn
# NX enabled, PIE disabled → 可以用固定 gadget

# Step 2: 找 gadget
rop "pop rdi"
# 0x4011b3 : pop rdi ; ret
rop "ret"
# 0x401016 : ret

# Step 3: 构造泄露 payload
# 偏移 72，泄露 puts@got 的真实地址
# payload = padding + pop_rdi + got_puts + puts_plt + main_addr

# Step 4: GDB 中验证
b *puts                    # 在 puts 入口断点
r
# 输入 payload，断在 puts 时
p $rdi                     # 看第一个参数是否是 got['puts']
# c 继续运行，拿到泄露的真实地址

# Step 5: 计算 libc_base
# libc_base = leaked - libc.symbols['puts']
# system = libc_base + libc.symbols['system']
# bin_sh = libc_base + libc.search('/bin/sh')

# Step 6: 第二次溢出调 system
```

### 3. 格式化字符串漏洞调试

场景：printf(buf) 存在格式化字符串漏洞，可以读写任意内存。

```bash
# Step 1: 确定偏移
gdb ./pwn
b printf                   # 在 printf 入口断点
r
# 输入 AAAA%p.%p.%p.%p.%p.%p.%p.%p.
# 断在 printf 时看栈上的参数：
p/s $rdi                   # 格式串本身
# 看 $rsi+8*$n 找到 0x41414141 → 偏移就是 n

# Step 2: 验证任意读
# payload = p64(target_addr) + '%6$s'  （假设偏移是 6）
# 发送后看是否读到 target 地址的内容

# Step 3: 验证任意写（改 GOT）
# payload = fmtstr_payload(offset, {got_printf_addr: system_addr})
# 发送后再调用 printf → 实际调用 system

# pwndbg 调试 fmtstr 要点：
# - 断在 printf 入口，确认格式串内容和栈布局
# - 用 telescope 看栈上偏移对应关系
# - 写操作后用 got 命令确认 GOT 值已改变
```

### 4. 堆利用基础调试

场景：堆相关的漏洞（use after free、double free、heap overflow）。

```bash
# Step 1: 查保护，关注 PIE
checksec ./pwn

# Step 2: 在 malloc/free 断点
b malloc
b free
r

# 第一次 malloc 后：
heap                       # 看堆布局
# 分配 chunk 后看 chunk 结构

# free 后：
bins                       # 看是否进入了 bin

# use after free 验证：
# free(chunk_a)
# malloc(chunk_b)  # 可能重叠
# 往 chunk_b 写数据，看 chunk_a 是否也被改了
# telescope chunk_a_ptr 4  # 确认

# double free 验证：
# free(chunk_a); free(chunk_a);
# bins  → 看 fd/bk 指针
```

### 5. PIE 程序调试

PIE 开启后地址随机化，GDB 中有两种处理方式：

```bash
# 方法一：关掉 ASLR（仅调试时）
set disable-randomization on
r
# 这样 PIE 基址固定（一般是 0x555555554000），方便调试

# 方法二：用相对偏移（推荐，更接近实际）
# PIE 程序中，pwndbg 会显示相对地址：
# 0x555555555234 <main+34>
# ^^^^^^^^^^^^ 基址    ^^^^ 相对偏移
# 你只需要记住相对偏移即可

# IDA 中的地址都是相对偏移
# GDB 中的实际地址 = 基址 + IDA 地址
# 例：IDA 中 main = 0x1234
# GDB 中可能显示 0x555555555234
# 偏移还是 0x1234

# pwndbg 辅助：
codeaddr                  # 显示代码基址
# 之后可以用 $rebase(addr) 计算真实地址
p $rebase(0x1234)         # 输出真实地址
```

---

## 十三、高级技巧：脚本化与自动化

### 1. GDB Python API 基础

GDB 内嵌 Python 解释器，可以编写自定义命令：

```python
# 在 GDB 中直接执行 Python
python
import gdb
print("Hello from Python in GDB!")
end

# 定义自定义命令
python
class DumpStack(gdb.Command):
    """dump_stack: 打印栈内容"""
    def __init__(self):
        super(DumpStack, self).__init__("dump_stack", gdb.COMMAND_DATA)

    def invoke(self, arg, from_tty):
        rsp = gdb.parse_and_eval('$rsp')
        count = int(arg) if arg else 20
        for i in range(count):
            addr = int(rsp) + i * 8
            try:
                val = gdb.selected_inferior().read_memory(addr, 8)
                num = int.from_bytes(val, 'little')
                print(f"[{i*3d}] 0x{addr:x}: 0x{num:016x}")
            except:
                print(f"[{i*3d}] 0x{addr:x}: ???")

DumpStack()
end

# 使用
dump_stack 30
```

### 2. 常用 GDB 脚本

```python
# 文件: ~/.gdb/py_scripts/utils.py
# 或放在项目目录下

import gdb

# 快速查看内存区域
def dump_region(start, size, name=""):
    start = int(start)
    size = int(size)
    print(f"\n=== {name} (0x{start:x} - 0x{start+size:x}) ===")
    for i in range(0, size, 8):
        addr = start + i
        try:
            data = gdb.selected_inferior().read_memory(addr, min(8, size-i))
            hex_str = ' '.join(f'{b:02x}' for b in data)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
            print(f"  0x{addr:x}: {hex_str:<24s} {ascii_str}")
        except gdb.MemoryError:
            print(f"  0x{addr:x}: (无法读取)")

# 自动在函数入口打印参数
class TraceFunc(gdb.Command):
    def __init__(self):
        super().__init__("trace_func", gdb.COMMAND_BREAKPOINTS)

    def invoke(self, arg, from_tty):
        func_name = arg.strip()
        bp = gdb.Breakpoint(func_name)
        def handler(event):
            if isinstance(event, gdb.BreakpointEvent):
                frame = gdb.selected_frame()
                print(f"\n>>> 进入 {func_name}")
                print(f"    rip = {frame.pc()}")
                print(f"    rdi (arg1) = {frame.read_register('rdi')}")
                print(f"    rsi (arg2) = {frame.read_register('rsi')}")
        gdb.events.stop.connect(handler)
        print(f"已在 {func_name} 设置追踪")

TraceFunc()
```

### 3. 加载自定义脚本

```bash
# 方法一：在 .gdbinit 中 source
echo 'source ~/.gdb/py_scripts/utils.py\n' >> ~/.gdbinit

# 方法二：启动时加载
gdb -q ./pwn -x load_utils.gdb
# load_utils.gdb 内容:
# python
# import sys; sys.path.insert(0, '.')
# import utils
# end
```

### 4. pwndbg 配置文件

pwndbg 支持 ~/.pwndbg/ 目录下的配置：

```bash
mkdir -p ~/.pwndbg
cat > ~/.pwndbg/config.py << 'EOF'
# pwndbg 配置
config = {
    # 默认架构
    'default_arch': 'amd64',

    # 反汇编语法
    'syntax_theme': 'dark_visual',   # 主题风格

    # 堆显示选项
    'show_heap_contents': True,

    # 栈显示行数
    'context_lines': 8,
}
EOF
```

### 5. TTY 问题排查

当 gdb.attach 无法正常弹出终端时：

```python
from pwn import *

# 确保 terminal 设置正确
context.terminal = ['tmux', 'splitw', '-h']

# 如果 tmux 不可用，试试 screen
context.terminal = ['screen', '-t', 'gdb', '-D']

# 如果都不行，手动方式：
p = process('./pwn')
pid = p.pid
print(f"PID: {pid}, 请手动: gdb -q -p {pid}")
input('attach好后按回车...')
# 然后在另一个终端手动 gdb attach
```

---

## 十四、实战技巧与注意事项

### 1. 调试效率清单

1. **先 checksec**：知道有哪些保护，决定思路
2. **IDA 看伪代码**：找到漏洞点和关键函数地址
3. **GDB 找偏移**：cyclic + cyclic_find 精确测量
4. **GDB 验证 payload**：确认每个步骤的寄存器/内存状态符合预期
5. **写 exp**：用 pwntools 自动化
6. **本地通了再打远程**

### 2. 常见问题排查

| 现象 | 原因 | 解决方法 |
|------|------|----------|
| GDB 没有 pwndgb 增强 | pwndbg 没正确安装 | 重新执行 `./setup.sh`，检查 Python 路径 |
| attach 后没反应 | terminal 配置错 | 设置 `context.terminal`，确保 tmux/screen 可用 |
| PIE 程序地址每次不同 | ASLR 开启 | 调试用 `set disable-randomization on`，或用相对偏移 |
| 断点打不上 | 代码被优化掉或地址错 | 用 `disas` 确认地址，或断在函数名 |
| 单步太慢 | 进了大循环 | 用 `c` 跳过，或在循环内条件断点 |
| 看不到源码 | 没有调试符号 | 用 `disas` 看汇编，用 IDA 对照伪代码 |
| 堆命令报错 | 还没有堆操作 | 先执行一次 malloc/free |
| 寄存器值看起来不对 | 检查架构 | `set architecture i386:amd64` 切换 |

### 3. pwndbg vs gef vs peda 对比

| 特性 | pwndbg | gef | peda |
|------|--------|-----|------|
| 维护状态 | 活跃 ★ | 活跃 | 停滞（2017年后不再维护） |
| 上下文展示 | 丰富（寄存器+反汇编+栈+代码） | 类似 pwndbg | 简洁 |
| vmmap | ✅ | ✅ | ✅ |
| checksec | ✅ | ✅ | ✅ |
| cyclic/cyclic_find | ✅ | ✅ | ❌ |
| heap 命令 | 完善（配合 Pwngdb） | 内置完善 | 基础 |
| rop 搜索 | ✅ | ✅ | ❌ |
| 安装难度 | 简单 | 简单 | 简单 |
| 社区资源 | 最多 ★ | 多 | 少 |

> 💡 **建议**：新手直接用 pwndbg，文档多、问题容易搜到答案。gef 也是好选择。peda 已不建议新项目使用。

### 4. 性能优化

```bash
# 大型二进制启动慢（pwndbg 需要分析）
gdb -q ./pwn -nx         # -nx 不读 .gdbinit，最快启动
# 或临时关闭部分功能

# 关闭 pwndbg 的某些自动显示（加快响应）
set pwndbg-context-display-sections none
```

### 5. 安全提醒

- 调试时注意不要在目标机器上留下 core dump（含敏感信息）
- `call system("/bin/sh")` 在 GDB 中可以快速拿 shell，但这不等同于真正的 exploit
- GDB 中的内存状态和真实运行可能有细微差异（如地址随机化、时序）
- 最终一定要在不加 GDB 的情况下测试 exp（GDB 本身会影响一些行为）

---

## 十五、速查表

### 启动与退出

```bash
gdb ./pwn                 # 启动
gdb -q ./pwn              # 安静模式（少输出）
gdb -q ./pwn -x scr.gdb   # 加载脚本
gdb -q -p 1234            # 附加进程
gdb -q ./pwn core         # 分析 core dump
(q) / quit                # 退出
Ctrl+C                    # 运行中暂停
```

### 断点

```bash
b main                    # 函数断点
b *0x401234               # 地址断点
b *0x401234 if $rax==0    # 条件断点
tb main                   # 临时断点
info b                    # 查看断点
delete / del 2            # 删除断点
disable 2 / enable 2      # 禁用/启用
watch *(int*)addr         # 数据断点（写入时停）
catch syscall open        # 捕获系统调用
```

### 执行

```bash
r                         # 运行
r AAAA < input.txt        # 带参数+输入
c                         # 继续
s / si                    # 单步（进入函数/指令）
n / ni                    # 单步（跳过函数/指令）
fin                       # 跑完当前函数返回
jump *addr                # 强制跳转
call puts("hi")           # 调用函数
```

### 寄存器

```bash
info registers / info reg  # 所有寄存器
p $rax / p/x $rbx          # 打印寄存器
set $rax = 0x41            # 修改寄存器
set $ZF = 1                # 修改标志位
```

### 内存

```bash
x/20gx $rsp               # 查看内存（十六进制）
x/s 0x601040               # 查看字符串
x/30i $rip                 # 反汇编
set {int}addr = value     # 修改内存
searchmem 0x41414141       # 搜索内存
```

### pwndbg 专有

```bash
checksec                  # 查保护机制
vmmap                     # 内存映射
telescope $rsp 20         # 递归查看栈
cyclic 200                # 生成 cyclic pattern
cyclic_find(value)        # 查找偏移
rop "pop rdi"             # 搜索 ROP gadget
heap                      # 堆布局
bins                      # 堆 bin 状态
plt / got                 # PLT/GOT 表
procinfo                  # 进程信息
canary                    # canary 值
codeaddr                  # 代码基址（PIE）
distance a b              # 两地址距离
hexdump addr size         # 十六进制 dump
```

### 栈

```bash
bt / bt full              # 调用栈
frame 3 / up / down       # 切换帧
```

### pwntools 集成

```python
from pwn import *
context.terminal = ['tmux', 'splitw', '-h']
gdb.attach(p, 'b main\nc')          # 附加
gdb.debug('./pwn', 'b main\nc')     # GDB 中启动
```

### 常用调试套路

```bash
# 找溢出偏移
b *vuln_end  →  r  →  输入 cyclic(300)  →  cyclic_find($rsp)

# 验证 payload
r < payload.bin  →  看 rip/寄存器是否符合预期

# 泄露地址
b *leak_point  →  p $rax  →  记录泄露值

# 追踪函数调用
b function_name  →  commands > silent > bt > c > end

# 追踪内存修改
watch *(int*)target_addr  →  c  →  触发时看调用栈
```

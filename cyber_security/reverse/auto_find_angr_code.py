"""
angr 符号执行求解 Go 二进制 CTF 题目

二进制文件: f2b96dffdf5afc81b8024233227f5e51 (Go 编译)
目标: 找到使程序输出 "Congratulation" 的输入

=== 原脚本问题分析 ===

原脚本输出全零 b'\\x00'*32，原因:

1. blank_state 起点问题:
   - 从 0x48F1CB (call Compress) 开始用 blank_state
   - blank_state 不会初始化 Go runtime、全局变量、栈帧
   - 程序执行时大量读取未初始化内存 → angr 填入 unconstrained 符号值
   - 这些 unconstrained 值不受约束控制 → 最终"找到"的路径不依赖你的 flag 输入
   - 所以 solver.eval(flag_chars) 返回默认值 0

2. Go 调用约定错误:
   - Go 1.17+ 使用基于寄存器的调用约定 (不是 RSI/RDI)
   - Go 函数参数通过 AX, BX, CX, DI, SI 等传递 (不同于 System V ABI)
   - 仅设置 RSI/RDI 不够，且 Compress 接收的是 Go 切片结构 (ptr, len, cap)
   - 原脚本只设了 RSI=RDI=input_buffer_addr，没有设置 len 和 cap

3. 输入未接入约束路径:
   - 即使将 flag_chars 写入 0x1000000，Compress 内部可能从其他位置读取
   - 符号变量没有通过程序的加密/比较逻辑传播
   - target/avoid 分支的判断不依赖 flag_chars → solver 可以赋任意值 (默认 0)

=== 修复策略 ===

策略 A (推荐): 从 entry_state 开始，通过 stdin 注入符号输入
  - 让 angr 完整执行程序，包括 Go runtime 初始化
  - 用 SimFileStream 将 stdin 替换为符号内容
  - 程序从 stdin 读取时自动获得符号值，约束自然传播

策略 B: 从 main.main 开始，手动设置栈上的符号输入
  - 需要精确定位 main.main 和输入读取点
  - 比 entry_state 更快，但需要更多逆向信息

策略 C: 找到比较循环，直接提取密文逆向求解
  - 最快最可靠，但需要完全理解算法
  - 不依赖 angr
"""

import angr
import claripy
import logging

# 降低 angr 日志级别，减少 WARNING 刷屏
logging.getLogger('angr').setLevel(logging.ERROR)

BINARY_PATH = './f2b96dffdf5afc81b8024233227f5e51'

# ============================================================
# 关键地址 (需要根据 IDA 反编译结果确认)
# ============================================================
# 以下地址需要你根据实际二进制确认
# target: 打印 "Congratulation" 的基本块地址
# avoid:  打印 "Uh Oh Try Again" 的基本块地址
TARGET_ADDR = 0x48F330
AVOID_ADDR  = 0x48F2D6


# ============================================================
# 方法 1: entry_state + stdin 注入 (推荐, 最通用)
# ============================================================
def solve_via_stdin():
    """
    从程序入口开始执行，通过 stdin 注入符号输入
    优点: Go runtime 正常初始化，约束自然传播
    缺点: 较慢 (需要执行 Go runtime 初始化代码)
    """
    print("[*] 方法 1: entry_state + stdin 注入")

    proj = angr.Project(BINARY_PATH, auto_load_libs=False)

    # 创建符号 stdin 内容
    flag_length = 32  # 先设较大值，实际 flag 可能更短
    flag_chars = claripy.BVS('flag', flag_length * 8)

    # entry_state: 从 _start 开始，完整初始化 Go runtime
    # stdin 用 SimFileStream 替换，内容为符号变量
    state = proj.factory.entry_state(
        stdin=angr.SimFileStream(
            name='stdin',
            content=flag_chars,
            has_end=False  # 流没有终止符，允许读取任意长度
        )
    )

    # 可选: 对输入添加约束 (如可打印字符)，加速求解
    for i in range(flag_length):
        byte = flag_chars.get_byte(i)
        state.solver.add(byte >= 0x20)  # 可打印 ASCII
        state.solver.add(byte <= 0x7e)

    simgr = proj.factory.simulation_manager(state)

    print(f"  [*] 探索路径: find=0x{TARGET_ADDR:x}, avoid=0x{AVOID_ADDR:x}")
    simgr.explore(find=TARGET_ADDR, avoid=AVOID_ADDR)

    if simgr.found:
        found_state = simgr.found[0]
        # 从 stdin 获取满足条件的输入
        stdin_content = found_state.posix.dumps(0)
        # 也可以直接求 flag_chars
        flag_val = found_state.solver.eval(flag_chars, cast_to=bytes)
        # 截取到第一个 \n 或 \0
        flag_str = flag_val.split(b'\n')[0].split(b'\x00')[0]
        print(f"  [+] Flag found: {flag_str}")
        return flag_str
    else:
        print("  [-] 未找到满足条件的路径")
        return None


# ============================================================
# 方法 2: 从 main 函数开始 (更快，但需要定位 main 地址)
# ============================================================
def solve_from_main():
    """
    从 main.main (Go 的主函数) 开始执行
    需要 IDA 中找到 main.main 的地址
    优点: 跳过 Go runtime 初始化，更快
    缺点: 需要正确设置栈和全局状态
    """
    print("[*] 方法 2: 从 main.main 开始")

    proj = angr.Project(BINARY_PATH, auto_load_libs=False)

    # 需要在 IDA 中找到 main.main 的地址
    # Go 二进制中搜索: main.main
    # 可以用 proj.loader.main_object.get_symbol('main.main')
    try:
        main_symbol = proj.loader.main_object.get_symbol('main.main')
        main_addr = main_symbol.rebased_addr
        print(f"  [+] 找到 main.main: 0x{main_addr:x}")
    except:
        # 如果找不到符号，需要手动指定
        main_addr = 0x48F1CB  # 替换为 main.main 的实际地址
        print(f"  [*] 使用手动地址: 0x{main_addr:x}")

    flag_length = 64
    flag_chars = claripy.BVS('flag', flag_length * 8)

    state = proj.factory.blank_state(
        addr=main_addr,
        stdin=angr.SimFileStream(
            name='stdin',
            content=flag_chars,
            has_end=False
        )
    )

    # 设置栈 (blank_state 的栈需要手动分配)
    state.regs.rsp = 0x7ffffffffff0000
    state.regs.rbp = 0x7ffffffffff0000

    # 可打印约束
    for i in range(flag_length):
        byte = flag_chars.get_byte(i)
        state.solver.add(byte >= 0x20)
        state.solver.add(byte <= 0x7e)

    simgr = proj.factory.simulation_manager(state)
    simgr.explore(find=TARGET_ADDR, avoid=AVOID_ADDR)

    if simgr.found:
        found_state = simgr.found[0]
        flag_val = found_state.solver.eval(flag_chars, cast_to=bytes)
        flag_str = flag_val.split(b'\n')[0].split(b'\x00')[0]
        print(f"  [+] Flag found: {flag_str}")
        return flag_str
    else:
        print("  [-] 未找到满足条件的路径")
        return None


# ============================================================
# 方法 3: hook 比较函数 + call_state (最精确)
# ============================================================
def solve_with_hook():
    """
    找到比较循环/函数，用 SimProcedure hook 掉复杂逻辑
    只在比较点设置约束，跳过 Compress 等复杂计算
    适用于: 已经理解算法，只想让 angr 做约束求解
    """
    print("[*] 方法 3: hook 比较函数")

    proj = angr.Project(BINARY_PATH, auto_load_libs=False)

    # 假设比较函数的签名是: compare(input_ptr, input_len) -> bool
    # 我们需要 hook 这个函数，让它:
    #   1. 从 input_ptr 读取符号字节
    #   2. 与已知的密文逐字节比较
    #   3. 返回比较结果

    # 这种方法需要完整的逆向分析结果 (密文值、比较逻辑)
    # 适合你已经完全理解算法的情况

    print("  [-] 此方法需要完整的逆向分析，示例略")
    print("  [*] 思路: 用 proj.hook(addr, SimProcedure) 替换复杂函数")
    print("  [*] 在 SimProcedure 中直接建立 input[i] == expected[i] 的约束")
    return None


# ============================================================
# 方法 4: blank_state 精确注入 (修复原脚本)
# ============================================================
def solve_blank_state_fixed():
    """
    修复原脚本的问题:
    1. 正确设置 Go 切片参数 (ptr, len, cap 分别传入不同寄存器)
    2. 初始化必要的栈帧和返回地址
    3. 对符号输入添加约束
    注意: 此方法仍然依赖精确的逆向分析，Go 二进制推荐用方法 1
    """
    print("[*] 方法 4: blank_state 精确注入 (修复版)")

    proj = angr.Project(BINARY_PATH, auto_load_libs=False)

    flag_length = 32
    flag_chars = claripy.BVS('flag', flag_length * 8)

    # 从 call Compress 的前一条指令开始 (不是 call 本身，而是准备参数的位置)
    # 这样可以看到参数是如何被设置的
    call_addr = 0x48F1CB
    state = proj.factory.blank_state(addr=call_addr)

    # --- 修复 1: 初始化栈 ---
    stack_base = 0x7ffffffffff0000
    state.regs.rsp = stack_base
    state.regs.rbp = stack_base
    # 设置返回地址 (防止 call 返回时跳转到未初始化内存)
    ret_addr = 0x48F1D0  # call 的下一条指令地址
    state.memory.store(stack_base, ret_addr, endness='Iend_LE')  # 压入返回地址
    state.regs.rsp = stack_base - 8

    # --- 修复 2: 分配输入缓冲区并写入符号变量 ---
    input_buffer_addr = 0x1000000
    state.memory.store(input_buffer_addr, flag_chars)

    # --- 修复 3: Go 1.17+ 调用约定 ---
    # Go 的函数调用约定: 参数按顺序放入 AX, BX, CX, DI, SI, ...
    # 切片 (slice) 传递3个值: (ptr, len, cap)
    # Compress 函数签名可能是: Compress(input_slice) -> output_slice
    #   input_slice.ptr  → 第1个参数
    #   input_slice.len  → 第2个参数
    #   input_slice.cap  → 第3个参数
    #
    # 具体寄存器分配需要看 IDA 反汇编中 call 之前的 mov 指令!
    # 以下是一个典型 Go 调用的设置，需根据实际反汇编调整:

    # 假设 Compress(dst_ptr, dst_len, dst_cap, src_ptr, src_len, src_cap)
    # Go 1.17 寄存器顺序: AX, BX, CX, DI, SI, R8, R9, R10, R11
    state.regs.rax = input_buffer_addr    # src.ptr
    state.regs.rbx = flag_length          # src.len
    state.regs.rcx = flag_length          # src.cap
    # 如果 Compress 还需要输出缓冲区:
    output_buffer_addr = 0x2000000
    state.regs.rdi = output_buffer_addr   # dst.ptr
    state.regs.rsi = 0x100                # dst.len
    state.regs.r8  = 0x100                # dst.cap

    # --- 修复 4: 添加可打印约束 ---
    for i in range(flag_length):
        byte = flag_chars.get_byte(i)
        state.solver.add(byte >= 0x20)
        state.solver.add(byte <= 0x7e)

    simgr = proj.factory.simulation_manager(state)
    simgr.explore(find=TARGET_ADDR, avoid=AVOID_ADDR)

    if simgr.found:
        found_state = simgr.found[0]
        flag_val = found_state.solver.eval(flag_chars, cast_to=bytes)
        flag_str = flag_val.split(b'\n')[0].split(b'\x00')[0]
        print(f"  [+] Flag found: {flag_str}")
        return flag_str
    else:
        print("  [-] 未找到满足条件的路径")
        return None


# ============================================================
# 主入口
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("Go 二进制 angr 求解器")
    print("=" * 60)

    # 推荐先试方法 1 (entry_state + stdin)
    # 如果太慢，再试方法 2 或 4
    # 方法 3 需要完整逆向分析

    print("\n推荐执行顺序:")
    print("  1. solve_via_stdin()       - 最通用，Go runtime 完整初始化")
    print("  2. solve_from_main()       - 更快，需要 main.main 地址")
    print("  3. solve_blank_state_fixed()- 需要精确的寄存器参数分析")
    print("  4. solve_with_hook()        - 需要完整算法逆向")

    # 默认运行方法 1
    result = solve_via_stdin()
    if result is None:
        print("\n方法 1 失败，尝试方法 2...")
        result = solve_from_main()

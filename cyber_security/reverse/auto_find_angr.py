import angr
import os

proj = angr.Project('./program', auto_load_libs=False)

# 从输入点开始符号执行
state = proj.factory.entry_state(stdin=angr.SimFile('/dev/stdin', size=64))

# 定义找到和避免的地址
find_addr = 0x401234   # "correct"分支的地址
avoid_addr = 0x401256  # "wrong"分支的地址

simgr = proj.factory.simulation_manager(state)
simgr.explore(find=find_addr, avoid=avoid_addr)

if simgr.found:
    found = simgr.found[0]
    print(found.posix.dumps(0))  # 打印满足条件的输入
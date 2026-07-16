import base64

target = "aOYanlkVkemSmRgYlWi0Nc1P3JPIfoMoQJ2I20w="

# 假设 chang 是大小写互换
def swap_case(s):
    return s.swapcase()

after_chang = target      # 目标串本身就是 chang 的输出
before_chang = swap_case(after_chang)   # 反向
flag = base64.b64decode(before_chang + "=" * (-len(before_chang) % 4))
print(flag)
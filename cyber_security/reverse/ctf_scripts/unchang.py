def unchang(s):
    n = len(s)

    # 前半部分（偶数位）
    even_len = (n + 1) // 2
    even = s[:even_len]

    # 后半部分（奇数位）
    odd = s[even_len:]

    res = []

    for i in range(even_len):
        res.append(even[i])
        if i < len(odd):
            res.append(odd[i])

    return ''.join(res)


print(unchang("aOYanlkVkemSmRgYlWi0Nc1P3JPIfoMoQJ2I20w="))
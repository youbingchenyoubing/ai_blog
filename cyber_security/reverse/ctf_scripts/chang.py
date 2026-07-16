def chang(s):
    even = []
    odd = []
    flag = 0
    for c in s:
        if c == ' ':
            continue
        if flag == 0:
            even.append(c)
            flag = 1
        else:
            odd.append(c)
            flag = 0
    return ''.join(even) + ''.join(odd)

x = "abcdef"
y = chang(x)
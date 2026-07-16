# Crypto 实战使用指南

> CTF Crypto 方向完整题型梳理 + 解题思路 + 工具深度用法，从入门到进阶一站式覆盖。

## 目录

- [一、Crypto 方向总览](#一crypto-方向总览)
- [二、古典密码](#二古典密码)
- [三、RSA 家族](#三rsa-家族)
- [四、对称加密](#四对称加密)
- [五、哈希与消息认证](#五哈希与消息认证)
- [六、离散对数与 ElGamal](#六离散对数与-elgamal)
- [七、椭圆曲线密码](#七椭圆曲线密码)
- [八、格密码与 LLL](#八格密码与-lll)
- [九、流密码与 XOR](#九流密码与-xor)
- [十、编码与替换](#十编码与替换)
- [十一、工具深度使用手册](#十一工具深度使用手册)

***

## 一、Crypto 方向总览

### 1.1 题型分布

CTF Crypto 题目按考察频率和难度大致分布如下：

| 频率 | 题型大类 | 典型子类 | 难度范围 |
| --- | --- | --- | --- |
| 极高频 | RSA | 小指数 / 共模 / Wiener / Fermat / 多素数 | 入门 ~ 中等 |
| 高频 | 古典密码 | 凯撒 / 维吉尼亚 / 栅栏 / 培根 / 仿射 | 入门 |
| 高频 | 哈希 | MD5/SHA 破解 / 长度扩展 / 哈希碰撞 | 入门 ~ 中等 |
| 中频 | 对称加密 | AES-ECB/CBC / Padding Oracle / DES | 中等 |
| 中频 | 编码 | Base64/32/85 / Hex / 摩尔斯 / 自定义编码 | 入门 |
| 中频 | XOR / 流密码 | 已知明文 / 多次密钥重用 / LFSR | 中等 |
| 中频 | 离散对数 | ElGamal / DLP / Pohlig-Hellman | 中等 ~ 较难 |
| 低频 | 椭圆曲线 | ECDLP / Smart / Pohlig-Hellman / MOV | 较难 ~ 困难 |
| 低频 | 格密码 | LLL / CVP / 背包 / Hidden Number Problem | 较难 ~ 困难 |

### 1.2 通用解题流程

```
拿到题目
  │
  ├─ 看源码/附件 → 识别加密算法
  │    ├─ 代码中有 RSA/ElGamal/AES/... → 对应题型
  │    ├─ 只有密文无源码 → 先识别特征（编码/古典密码）
  │    └─ 有交互（nc 连接）→ 可能有 oracle / 选择密文攻击
  │
  ├─ 提取参数 → n, e, c, p, q, key, iv ...
  │
  ├─ 分析弱点 → 什么条件可以被利用
  │    ├─ RSA: e 太小？p/q 接近？d 太小？共享因子？多次加密？
  │    ├─ AES: ECB 可分组重排？CBC 有 Padding Oracle？IV 可控？
  │    ├─ 哈希: 可以长度扩展？salt 已知？可以碰撞？
  │    └─ ...
  │
  ├─ 选工具/写脚本 → 攻击
  │    ├─ 标准攻击 → 工具（RsaCtfTool / hashcat / SageMath）
  │    └─ 非标准 → 手写脚本（Python + gmpy2 / pycryptodome）
  │
  └─ 恢复明文 → 转字符串 → 提交 flag
```

### 1.3 核心库安装

```bash
# Python 密码学核心库（必装）
pip3 install pycryptodome    # AES/DES/RSA/ElGamal/ECC 等全套
pip3 install gmpy2           # 大数运算（iroot/invert/powmod）
pip3 install sympy           # 符号计算（solve/factor/modular）
pip3 install sage            # SageMath（可选，体积大但功能最强）

# 辅助库
pip3 install factordb-python # factordb 在线查
pip3 install hashid          # 哈希类型识别
pip3 install xortool         # XOR 分析
pip3 install pyhashcat       # hashcat Python 接口

# 数论工具
pip3 install pycrypto        # 旧版（部分题目的脚本依赖）
```

***

## 二、古典密码

### 2.1 题型特征与识别

古典密码题通常特征明显：

- 密文只有字母（可能保留大小写/空格/标点）
- 题目给出加密方式名称或暗示
- 密文长度较短，可直接暴力

| 密码类型 | 密文特征 | 破解难度 | 常用工具 |
| --- | --- | --- | --- |
| 凯撒（Caesar） | 字母偏移，保留词边界 | 极低 | 手动/脚本暴力 |
| 仿射（Affine） | 字母偏移+缩放 | 低 | 脚本暴力 |
| 维吉尼亚（Vigenère） | 多表替换，无明显频率 | 中 | Kasiski/重合指数 |
| 栅栏（Rail Fence） | 字母频率正常但乱序 | 低 | 2~N 暴力 |
| 培根（Bacon） | AB 序列或大小写隐写 | 低 | 脚本解码 |
| Playfair | 偶数长度，无重复双字母 | 中 | 已知关键词或暴力 |
| Hill | 矩阵运算，频率接近均匀 | 中 | 已知明文片段求逆矩阵 |
| 摩尔斯 | 点划序列 | 极低 | CyberChef/脚本 |
| 替换（Substitution） | 单表替换，频率异常 | 低 | quipqiup 自动 |

### 2.2 凯撒密码

**原理**：E(x) = (x + k) mod 26，只有 25 种可能偏移，暴力即可。

**解题思路**：

1. 26 种偏移全试，人工看哪个像正常英文
2. 程序自动判：检查常见词（the/and/flag）出现

```python
def caesar_bruteforce(ciphertext):
    """凯撒密码暴力，自动标注含常见词的结果"""
    common_words = ['the', 'and', 'flag', 'ctf', 'is', 'of']
    for shift in range(26):
        plain = ""
        for ch in ciphertext:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                plain += chr((ord(ch) - base - shift) % 26 + base)
            else:
                plain += ch
        # 自动标注
        lower = plain.lower()
        hits = [w for w in common_words if w in lower]
        marker = f" ← {hits}" if hits else ""
        print(f"偏移 {shift:2d}: {plain[:80]}{marker}")
```

**变体**：

- ROT13：偏移固定为 13（自逆），`codecs.decode(s, 'rot_13')`
- ROT47：对 ASCII 33~126 偏移 47，数字/符号也会变
- 偏移方向不确定时，加密和解密方向都试一遍

### 2.3 仿射密码

**原理**：E(x) = (a·x + b) mod 26，要求 gcd(a, 26) = 1。

**解题思路**：

1. 枚举所有合法 a（与 26 互素的 a ∈ {1,3,5,7,9,11,15,17,19,21,23,25}）
2. 枚举 b ∈ [0, 25]
3. 对每组 (a, b) 解密，检查结果是否有意义

```python
from math import gcd

def affine_bruteforce(ciphertext):
    """仿射密码暴力破解"""
    valid_a = [a for a in range(26) if gcd(a, 26) == 1]
    for a in valid_a:
        # 求 a 的模 26 逆元
        a_inv = pow(a, -1, 26)
        for b in range(26):
            plain = ""
            for ch in ciphertext:
                if ch.isalpha():
                    base = ord('A') if ch.isupper() else ord('a')
                    x = ord(ch.upper()) - ord('A')
                    plain += chr((a_inv * (x - b)) % 26 + base)
                else:
                    plain += ch
            if 'flag' in plain.lower() or 'the' in plain.lower():
                print(f"a={a:2d}, b={b:2d}: {plain}")
```

### 2.4 维吉尼亚密码

**原理**：多表凯撒，密钥周期重复。E(xᵢ) = (xᵢ + kᵢ mod len) mod 26。

**解题思路**：

1. 确定密钥长度：Kasiski 测试或重合指数法
2. 按密钥长度分组，每组做凯撒暴力（频率分析）
3. 合并得到明文

```python
def kasiski_test(ciphertext, min_len=3, max_len=20):
    """Kasiski 测试：找重复子串间距的 GCD 推断密钥长度"""
    from collections import Counter
    from math import gcd as math_gcd
    from functools import reduce

    # 找重复子串
    distances = []
    for length in range(min_len, min_len + 5):
        seen = {}
        for i in range(len(ciphertext) - length):
            sub = ciphertext[i:i+length]
            if sub in seen:
                distances.append(i - seen[sub])
            seen[sub] = i

    if not distances:
        return None

    # 间距的 GCD 即可能的密钥长度
    g = reduce(math_gcd, distances)
    # 列出所有因子
    factors = [d for d in range(1, max_len+1) if g % d == 0]
    return factors

def index_of_coincidence(text):
    """重合指数：英文约 0.065，随机约 0.038"""
    from collections import Counter
    freq = Counter(text)
    n = len(text)
    if n <= 1:
        return 0
    ic = sum(f * (f - 1) for f in freq.values()) / (n * (n - 1))
    return ic

def vigenere_key_length(ciphertext, max_len=20):
    """用重合指数法确定密钥长度"""
    alpha = ''.join(ch.upper() for ch in ciphertext if ch.isalpha())
    results = []
    for key_len in range(1, max_len + 1):
        # 按密钥位置分组
        ics = []
        for offset in range(key_len):
            group = alpha[offset::key_len]
            if len(group) > 1:
                ics.append(index_of_coincidence(group))
        avg_ic = sum(ics) / len(ics) if ics else 0
        results.append((key_len, avg_ic))
        # 英文 IC ≈ 0.065，接近则可能是正确密钥长度
        if abs(avg_ic - 0.065) < 0.01:
            print(f"密钥长度候选: {key_len} (IC={avg_ic:.4f})")
    return results
```

**已知密钥时的解密**：

```python
def vigenere_decrypt(ciphertext, key):
    """维吉尼亚密码解密"""
    plain = ""
    key = key.upper()
    ki = 0
    for ch in ciphertext:
        if ch.isalpha():
            base = ord('A') if ch.isupper() else ord('a')
            shift = ord(key[ki % len(key)]) - ord('A')
            plain += chr((ord(ch.upper()) - ord('A') - shift) % 26 + base)
            ki += 1
        else:
            plain += ch
    return plain
```

**在线工具**：quipqiup (https://www.quipqiup.com/) 可自动破解替换密码和维吉尼亚。

### 2.5 栅栏密码

**原理**：按之字形排列后按行读出。密钥只有栏数，暴力 2~N 即可。

```python
def rail_fence_decrypt(ciphertext, rails):
    """栅栏密码解密"""
    n = len(ciphertext)
    pattern = list(range(rails)) + list(range(rails - 2, 0, -1))
    indices = sorted(range(n), key=lambda i: (pattern[i % len(pattern)], i))
    result = [''] * n
    for i, idx in enumerate(indices):
        if i < len(ciphertext):
            result[idx] = ciphertext[i]
    return ''.join(result)

def rail_fence_bruteforce(ciphertext, max_rails=20):
    """栅栏密码暴力，试所有栏数"""
    for rails in range(2, min(max_rails, len(ciphertext))):
        plain = rail_fence_decrypt(ciphertext, rails)
        if 'flag' in plain.lower():
            print(f"栏数 {rails}: {plain}")
        else:
            print(f"栏数 {rails}: {plain[:60]}...")
```

### 2.6 培根密码

**原理**：每个字母编码为 5 位 A/B 序列（A=0, B=1），对应字母序号。

**隐写变体**：用大小写/粗细/字体等区分 A 和 B，5 个字符编码 1 个字母。

```python
def bacon_decode(ciphertext):
    """培根密码解码，支持多种 A/B 表示"""
    import string
    bacon_table = {}
    for i, ch in enumerate(string.ascii_uppercase):
        code = format(i, '05b').replace('0', 'A').replace('1', 'B')
        bacon_table[code] = ch

    # 尝试多种 A/B 映射
    # 方式1：直接 AB
    ab_seq = ''.join(ch.upper() for ch in ciphertext if ch.upper() in 'AB')
    # 方式2：大小写隐写（大写=A，小写=B 或反之）
    if not ab_seq:
        ab_seq = ''.join('A' if ch.isupper() else 'B' for ch in ciphertext if ch.isalpha())

    result = ""
    for i in range(0, len(ab_seq) - 4, 5):
        code = ab_seq[i:i+5]
        if code in bacon_table:
            result += bacon_table[code]
        else:
            result += '?'
    return result
```

### 2.7 替换密码

**原理**：单表替换，字母频率与英文一致但映射被打乱。

**解题方法**：

1. 字频分析：统计密文字母频率，对照英文字母频率表（E > T > A > O > I > N...）
2. 在线工具：quipqiup 支持已知明文片段约束，自动破解
3. 双字母/三字母频率：TH/HE/IN/THE/AND 等常见组合辅助

```
英文字母频率表（从高到低）：
E: 12.7%  T: 9.1%  A: 8.2%  O: 7.5%  I: 7.0%
N: 6.7%   S: 6.3%  H: 6.1%  R: 6.0%  D: 4.3%
L: 4.0%   C: 2.8%  U: 2.8%  M: 2.4%  W: 2.4%
F: 2.2%   G: 2.0%  Y: 2.0%  P: 1.9%  B: 1.5%
V: 1.0%   K: 0.8%  J: 0.2%  X: 0.2%  Q: 0.1%  Z: 0.1%
```

### 2.8 Hill 密码

**原理**：分组后矩阵乘法 C = M · P mod 26，M 是可逆矩阵。

**解题方法**：

1. 已知部分明文-密文对，求解加密矩阵 M
2. 求 M 的逆矩阵 M⁻¹，解密 P = M⁻¹ · C mod 26
3. det(M) 必须与 26 互素，否则矩阵不可逆

```python
import numpy as np
from math import gcd

def hill_decrypt(cipher_matrix, key_matrix, mod=26):
    """Hill 密码解密：求密钥矩阵的模逆再乘"""
    # 求行列式
    det = int(round(np.linalg.det(key_matrix)))
    if gcd(det, mod) != 1:
        print("矩阵不可逆！")
        return None
    # 求伴随矩阵 * 行列式逆元
    det_inv = pow(det, -1, mod)
    adj = np.round(np.linalg.inv(key_matrix) * det).astype(int)
    inv_matrix = (det_inv * adj) % mod
    # 解密
    plain_matrix = (np.dot(cipher_matrix, inv_matrix) % mod).astype(int)
    return plain_matrix
```

***

## 三、RSA 家族

RSA 是 CTF Crypto 出题频率最高的方向，变体极多。掌握每种变体的攻击条件和解法是核心能力。

### 3.1 RSA 基础回顾

```
密钥生成：选素数 p, q → n = p·q → φ = (p-1)(q-1) → 选 e → d = e⁻¹ mod φ
加密：c = m^e mod n
解密：m = c^d mod n
```

**拿到 RSA 题的第一步**：

1. 提取 n, e, c（有时给 p, q, d）
2. 查 factordb.com 看 n 是否已分解
3. 看 e 的大小、n 的位数、有无多组密文
4. 根据条件选攻击方法

### 3.2 题型与攻击方法速查表

| 题型特征 | 攻击方法 | 条件 | 难度 |
| --- | --- | --- | --- |
| e 很小（e=3） | 小公钥指数攻击 | m^e < n 或 m^e 刚好溢出 | 入门 |
| e 很小，多组密文 | Håstad 广播攻击 | e 组 (cᵢ, nᵢ)，同一明文 | 入门 |
| e 很大 | Wiener 攻击 | d < n^0.25 | 中等 |
| p 和 q 接近 | Fermat 分解 | \|p-q\| < n^0.25 | 中等 |
| 多组密文共享 n | 共模攻击 | gcd(e₁,e₂)=1 | 入门 |
| 多个 n 有共享因子 | 共享因子攻击 | gcd(n₁,n₂) = p | 入门 |
| p-1 平滑 | Pollard's p-1 | p-1 的素因子都较小 | 中等 |
| 已知明文高位 | Coppersmith 小根 | 已知 m 的高位，未知部分较小 | 较难 |
| dp/dq 泄露 | dp/dq 泄露攻击 | 已知 dp = d mod (p-1) | 中等 |
| n = p·q·r... | 多素数 RSA | n 有多个素因子 | 入门 |
| p = next_prime(q) | p 近似 q + Δ | p 和 q 差值很小 | 中等 |
| e = 1 | 直接解密 | c = m，无加密 | 入门 |
| d 泄露 | 已知 d 求分解 | 已知 d 可反推 p, q | 中等 |
| 低指数填充不当 | Padding Oracle / Bleichenbacher | PKCS#1 v1.5 填充 | 较难 |

### 3.3 小公钥指数攻击（e=3）

**场景 1：m^e < n，未取模**

此时 c = m^e（未溢出），直接开 e 次方根：

```python
from gmpy2 import iroot

def small_e_no_pad(c, e):
    """m^e < n 时直接开方"""
    m, is_exact = iroot(c, e)
    if is_exact:
        return int(m)
    return None
```

**场景 2：m^e 略大于 n，c = m^e mod n**

m^e = c + k·n，枚举 k 从 0 开始尝试开方：

```python
def small_e_overflow(c, e, n, max_k=100000):
    """m^e 略大于 n，枚举 k 使得 (c + k*n) 是完全 e 次方"""
    for k in range(max_k):
        m, is_exact = iroot(c + k * n, e)
        if is_exact:
            return int(m)
    return None
```

**场景 3：e=3 且有填充，但填充可构造**

如果明文格式已知（如 `m = pad + flag`），用 Coppersmith 方法求小根（见 3.9 节）。

### 3.4 Håstad 广播攻击

**条件**：同一明文 m 用 e 个不同模数 nᵢ 加密，且所有 eᵢ = e。

**原理**：用中国剩余定理（CRT）求 m^e mod (n₁·n₂·...·nₑ)，由于 m^e < n₁·n₂·...·nₑ，开 e 次方恢复 m。

```python
def hastad_broadcast(c_list, n_list, e):
    """Håstad 广播攻击：同一明文、多个模数、相同 e"""
    # CRT 求解 m^e mod (n1*n2*...)
    from functools import reduce

    N = reduce(lambda a, b: a * b, n_list)
    result = 0
    for i, (ci, ni) in enumerate(zip(c_list, n_list)):
        Ni = N // ni
        # 求 Ni 模 ni 的逆
        Ni_inv = pow(Ni, -1, ni)
        result += ci * Ni * Ni_inv
    m_e = result % N

    # 开 e 次方
    from gmpy2 import iroot
    m, is_exact = iroot(m_e, e)
    if is_exact:
        return int(m)
    return None

# 用法：e=3, 三组密文
# m = hastad_broadcast([c1, c2, c3], [n1, n2, n3], 3)
```

**RsaCtfTool 一键版**：

```bash
python3 RsaCtfTool.py -e 3 \
    --uncipherfile c1.txt --uncipherfile c2.txt --uncipherfile c3.txt \
    -n $(cat n1.txt) \
    --attack hastads
```

### 3.5 共模攻击

**条件**：同一明文 m 用相同 n 但不同 e₁, e₂ 加密，gcd(e₁, e₂) = 1。

**原理**：由扩展欧几里得算法求 s₁, s₂ 使得 e₁·s₁ + e₂·s₂ = 1，则 m = c₁^s₁ · c₂^s₂ mod n。

```python
def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    g, x1, y1 = extended_gcd(b % a, a)
    return g, y1 - (b // a) * x1, x1

def common_modulus_attack(c1, c2, e1, e2, n):
    """共模攻击：相同 n，不同 e"""
    g, s1, s2 = extended_gcd(e1, e2)
    if g != 1:
        print(f"gcd(e1,e2)={g}，无法直接共模攻击")
        return None
    # 处理负指数：c^(-s) = (c^(-1))^s mod n
    if s1 < 0:
        c1 = pow(c1, -1, n)
        s1 = -s1
    if s2 < 0:
        c2 = pow(c2, -1, n)
        s2 = -s2
    m = (pow(c1, s1, n) * pow(c2, s2, n)) % n
    return m
```

### 3.6 Wiener 攻击

**条件**：私钥 d < n^0.25（等价于 e 很大，接近 n）。

**原理**：对 e/n 做连分数展开，渐近分数 k/d 中可能包含真正的 d。

```python
def wiener_attack(e, n):
    """Wiener 攻击：d 很小时通过连分数恢复"""
    from math import isqrt

    def continued_fraction(a, b):
        cf = []
        while b:
            q, r = divmod(a, b)
            cf.append(q)
            a, b = b, r
        return cf

    def convergents(cf):
        convs = []
        h_prev, h_curr = 0, 1
        k_prev, k_curr = 1, 0
        for a in cf:
            h_prev, h_curr = h_curr, a * h_curr + h_prev
            k_prev, k_curr = k_curr, a * k_curr + k_prev
            convs.append((h_curr, k_curr))
        return convs

    cf = continued_fraction(e, n)
    for k, d in convergents(cf):
        if k == 0:
            continue
        phi_times = e * d - 1
        if phi_times % k != 0:
            continue
        phi = phi_times // k
        s = n - phi + 1  # p + q
        discriminant = s * s - 4 * n
        if discriminant < 0:
            continue
        sqrt_disc = isqrt(discriminant)
        if sqrt_disc * sqrt_disc == discriminant:
            p = (s + sqrt_disc) // 2
            q = (s - sqrt_disc) // 2
            if p * q == n and p > 1 and q > 1:
                return d, p, q
    return None
```

**RsaCtfTool 版**：`python3 RsaCtfTool.py -n N -e E --attack wiener --private`

### 3.7 Fermat 分解

**条件**：p 和 q 非常接近，\|p - q\| < n^0.25。

**原理**：n = p·q = (a-b)(a+b) = a² - b²，从 a = ⌈√n⌉ 开始枚举 a，检查 a² - n 是否完全平方数。

```python
from math import isqrt

def fermat_factor(n, max_iter=1000000):
    """Fermat 分解：p 和 q 接近时高效"""
    a = isqrt(n)
    if a * a == n:
        return a, a
    a += 1
    for _ in range(max_iter):
        b2 = a * a - n
        b = isqrt(b2)
        if b * b == b2:
            p, q = a + b, a - b
            if p * q == n:
                return p, q
        a += 1
    return None, None
```

### 3.8 共享因子攻击

**条件**：多组 (nᵢ, eᵢ, cᵢ) 中某两个 n 共享素因子 p。

**原理**：gcd(n₁, n₂) = p，直接分解。

```python
from math import gcd

def shared_factor_attack(n_list):
    """检查所有 n 对之间是否有共享因子"""
    results = []
    for i in range(len(n_list)):
        for j in range(i + 1, len(n_list)):
            p = gcd(n_list[i], n_list[j])
            if 1 < p < n_list[i]:
                q_i = n_list[i] // p
                q_j = n_list[j] // p
                results.append({
                    'pair': (i, j),
                    'p': p,
                    'q_i': q_i,
                    'q_j': q_j
                })
                print(f"n[{i}] 和 n[{j}] 共享因子 p = {p}")
    return results
```

**实战提示**：比赛有多道 RSA 题时，收集所有 n 互相求 gcd 是低投入高回报操作。

### 3.9 Pollard's p-1 分解

**条件**：p-1 是平滑的（所有素因子都较小，如 ≤ B）。

**原理**：选 a = 2，计算 a^(B!) mod n，则 gcd(a^(B!) - 1, n) 可能等于 p。

```python
def pollard_pm1(n, B=2**20):
    """Pollard's p-1 分解：p-1 平滑时有效"""
    a = 2
    for j in range(2, B):
        a = pow(a, j, n)
        d = gcd(a - 1, n)
        if 1 < d < n:
            return d, n // d
    return None, None

# SageMath 版（更灵活，可指定 B）
# sage: def pollard_pm1(n, B=2^20):
# ....:     a = 2
# ....:     for j in range(2, B): a = power_mod(a, j, n)
# ....:     d = gcd(a-1, n)
# ....:     return d if 1 < d < n else None
```

### 3.10 Coppersmith 小根攻击

**条件**：已知明文的高位部分，未知部分较小（< n^0.25 左右）。

**场景**：

1. 已知 m 的高位：m = m_high + x，x 很小
2. 已知 p 的高位：p = p_high + x
3. stereotyped message：消息格式已知，只有部分未知

```python
# SageMath 实现
def coppersmith_small_root(n, e, c, m_high, unknown_bits):
    """
    已知明文高位，用 Coppersmith 求小根
    m = m_high + x，x < 2^unknown_bits
    """
    P.<x> = PolynomialRing(Zmod(n))
    f = (m_high + x)^e - c
    # small_roots 参数：X=未知部分上界，beta=1 对应 n
    roots = f.small_roots(X=2^unknown_bits, beta=1)
    if roots:
        x_val = int(roots[0])
        m = m_high + x_val
        return m
    return None

# 已知 p 高位，分解 n
def coppersmith_factor(n, p_high, unknown_bits):
    """已知 p 的高位，用 Coppersmith 分解 n"""
    P.<x> = PolynomialRing(Zmod(n))
    f = p_high + x
    roots = f.small_roots(X=2^unknown_bits, beta=0.5)
    if roots:
        p = int(p_high + roots[0])
        if n % p == 0:
            return p, n // p
    return None, None
```

### 3.11 dp/dq 泄露攻击

**条件**：已知 dp = d mod (p-1) 或 dq = d mod (q-1)。

**原理**：枚举 k ∈ [0, e)，由 dp = d mod (p-1) 推出 p = gcd(n, pow(e·dp - 1, -1, ...))。

```python
def dp_leak_attack(e, n, dp):
    """已知 dp = d mod (p-1)，恢复 p, q"""
    for k in range(1, e):
        # p - 1 = (e * dp - 1) / k 的因子
        p_minus_1_candidate = (e * dp - 1) // k
        if (e * dp - 1) % k != 0:
            continue
        p_candidate = p_minus_1_candidate + 1
        if n % p_candidate == 0:
            p = p_candidate
            q = n // p
            return p, q
    return None, None
```

### 3.12 多素数 RSA

**条件**：n = p₁·p₂·...·pₖ（k > 2）。

**解法**：φ = (p₁-1)(p₂-1)...(pₖ-1)，其余步骤相同。factordb 或 yafu 分解 n 得到所有素因子即可。

```python
def multi_prime_rsa_decrypt(c, primes, e):
    """多素数 RSA 解密"""
    from functools import reduce
    n = reduce(lambda a, b: a * b, primes)
    phi = reduce(lambda a, b: a * b, [p - 1 for p in primes])
    d = pow(e, -1, phi)
    m = pow(c, d, n)
    return m
```

### 3.13 RSA 综合解题模板

完整脚本已抽离到 `ctf_scripts/rsa_template.py`，基于 `ctf_scripts/rsa_attacks.py` 已实现的攻击函数构建，根据题目条件**从快到慢自动选择攻击方法**，覆盖以下分支：

| 顺序 | 攻击 | 触发条件 |
| --- | --- | --- |
| 1 | 直接解密 | 已知 p/ q / d |
| 2 | dp 泄露 | 已知 dp |
| 3 | 共享因子 | 多组 n 共享 p |
| 4 | 共模攻击 | 同 n 不同 e，gcd(e₁,e₂)=1 |
| 5 | Håstad 广播 | ≥ e 组密文 |
| 6 | 小指数攻击 | e ≤ 5 |
| 7 | factordb 查询 | n 已被收录 |
| 8 | Wiener | e > n^0.3 |
| 9 | Fermat 分解 | p ≈ q |
| 10 | Pollard p-1 | p-1 平滑 |

**最简用法（填参数即跑）**：

```python
# 编辑 ctf_scripts/rsa_template.py 的 main()，填入 n, e, c
python3 ctf_scripts/rsa_template.py
```

**库方式调用（推荐，便于扩展）**：

```python
import sys
sys.path.insert(0, 'ctf_scripts')
from rsa_template import RSASolver

# 单组密文
solver = RSASolver(n=N, e=E, c=C)
m = solver.solve()                 # 自动尝试所有攻击

# 已知额外信息
RSASolver(n=N, e=E, c=C, p=P, q=Q).solve()
RSASolver(n=N, e=E, c=C, dp=DP).solve()
RSASolver(n=N, e=E, c=C, d=D).solve()

# 多组密文（共模 / 广播 / 共享因子）
solver = RSASolver(n=N1, e=E1, c=C1)
solver.add_group(c=C2, e=E2, n=N1)   # 相同 n = 共模
solver.add_group(c=C2, e=E1, n=N2)   # 不同 n = 广播 / 共享因子
solver.solve()
```

**所有内置攻击都失败时**会提示后续思路：
- 上 `RsaCtfTool --attack all`
- 用 SageMath Coppersmith（已知明文高位 / 已知 p 高位）
- Boneh-Durfee（d < n^0.292）
- d 泄露反推 p, q

***

## 四、对称加密

### 4.1 AES 常见题型

| 题型 | 模式 | 攻击方法 | 条件 |
| --- | --- | --- | --- |
| ECB 分组重排 | ECB | 交换密文分组改变明文 | 有分组语义（如用户角色） |
| CBC 翻转 | CBC | 修改 IV 或前一组密文翻转明文 | 已知明文结构，需修改某段 |
| Padding Oracle | CBC | 逐字节爆破 padding | 有解密 oracle（返回 padding 是否合法） |
| AES-CTR 重用 | CTR | XOR 两组密文消去密钥流 | 同一 key+nonce 加密多次 |
| AES-CFB 位翻转 | CFB | 修改密文翻转对应明文 | 类似 CBC 翻转 |
| 密钥泄露 | 任意 | 直接解密 | key 已知 |

### 4.2 AES-ECB 分组重排

**原理**：ECB 模式下相同明文分组产生相同密文分组，分组独立，可交换/删除/复制密文分组。

**典型场景**：Cookie / Token 结构为 `user=xxx&role=user`，攻击者通过调整输入使 `admin` 成为独立分组，然后将密文中的 `user` 分组替换为 `admin` 分组。

```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

def ecb_group_swap_example():
    """ECB 分组重排示例"""
    key = b'0123456789abcdef'  # 题目给的 key

    # 假设服务端加密逻辑：pad("user=" + input + "&role=user")
    # 我们输入 "admin" + 11个填充 + "user="
    # 明文分组: [user=admin\x0b\x0b...] [user=Axxx...] [dmin&role=] [user\x0c\x0c...]
    # 攻击：用第2组替换第1组实现 role=admin

    cipher = AES.new(key, AES.MODE_ECB)

    # 构造：使 admin 成为完整分组
    # 输入: "AAAAAAAAAA" (10字节) + "admin" (5字节) + "\x0b"*11 (PKCS7填充)
    # 明文: "user=AAAAAAAAAA" | "admin\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b" | "&role=user\x04\x04\x04\x04"
    # 同时再构造一个使 "admin" 出现在 role 位置的输入
    # 输入: "AAAAAAAAAAadmin" (15字节)
    # 明文: "user=AAAAAAAAAA" | "admin&role=user" | "\x01"

    # 实际利用需根据题目具体调整分组边界
    pass
```

**解题要点**：

1. 确定分组大小（AES = 16 字节）
2. 构造输入使目标值对齐到分组边界
3. 交换/替换密文分组

### 4.3 CBC 位翻转攻击

**原理**：在 CBC 模式中，Cᵢ = E(Pᵢ ⊕ Cᵢ₋₁)，修改 Cᵢ₋₁ 的第 j 字节会翻转 Pᵢ 的第 j 字节：Pᵢ' = Pᵢ ⊕ Δ。

```python
def cbc_bit_flip(ciphertext, iv, target_group, target_byte, desired_value, original_value):
    """
    CBC 位翻转攻击
    修改前一组密文(或 IV)来翻转目标明文分组
    target_group: 要修改的明文分组索引 (0-based)
    target_byte:  分组内字节索引
    desired_value: 想要的目标字节值
    original_value: 原始字节值
    """
    block_size = 16
    ct = bytearray(ciphertext)

    if target_group == 0:
        # 修改 IV
        iv_ba = bytearray(iv)
        iv_ba[target_byte] ^= original_value ^ desired_value
        return bytes(ct), bytes(iv_ba)
    else:
        # 修改前一组密文
        prev_group_start = (target_group - 1) * block_size
        ct[prev_group_start + target_byte] ^= original_value ^ desired_value
        return bytes(ct), iv
```

**典型场景**：修改加密 Cookie 中的 `role=user` → `role=admin`。

### 4.4 Padding Oracle 攻击

**条件**：服务端对密文解密后检查 PKCS7 padding，返回 padding 是否合法（如 HTTP 200 vs 500）。

**原理**：逐字节构造合法 padding，利用 oracle 反推中间值（Intermediate Value），进而恢复明文。

```python
def padding_oracle_attack(oracle, ciphertext, iv, block_size=16):
    """
    Padding Oracle 攻击
    oracle: 函数，输入 (iv, ciphertext)，返回 padding 是否合法 (bool)
    """
    blocks = [iv]
    for i in range(0, len(ciphertext), block_size):
        blocks.append(ciphertext[i:i+block_size])

    plaintext = b''

    for block_idx in range(1, len(blocks)):
        # 当前密文分组
        C = blocks[block_idx]
        # 前一组密文分组（要修改的部分）
        C_prev = bytearray(blocks[block_idx - 1])

        # 中间值 I = D(C)
        I = bytearray(block_size)

        # 从最后一个字节开始逐字节爆破
        for byte_pos in range(block_size - 1, -1, -1):
            pad_val = block_size - byte_pos  # 目标 padding 值

            # 已知的字节设为目标 padding
            for k in range(byte_pos + 1, block_size):
                C_prev[k] = I[k] ^ pad_val

            # 枚举当前字节
            found = False
            for guess in range(256):
                C_prev[byte_pos] = guess
                if oracle(bytes(C_prev), C):
                    # 可能是正确的 padding
                    # 但 byte_pos == block_size-1 时需要验证不是巧合
                    if byte_pos == block_size - 1:
                        # 验证：修改前一个字节，padding 应该不再合法
                        C_prev_check = bytearray(C_prev)
                        C_prev_check[byte_pos - 1] ^= 1
                        if not oracle(bytes(C_prev_check), C):
                            continue
                    I[byte_pos] = guess ^ pad_val
                    found = True
                    break

            if not found:
                print(f"[-] 字节 {byte_pos} 爆破失败")
                return None

        # 明文 = I ⊕ C_prev_original
        P = bytes(I[i] ^ blocks[block_idx - 1][i] for i in range(block_size))
        plaintext += P
        print(f"[+] 分组 {block_idx}: {P}")

    return plaintext
```

**pwntools 交互版**：

```python
from pwn import *

def padding_oracle_remote(host, port, ciphertext, iv):
    """远程 Padding Oracle 攻击"""
    def oracle(iv_bytes, ct_bytes):
        p = remote(host, port)
        # 根据题目协议发送 iv 和密文
        p.sendline(iv_bytes.hex() + ct_bytes.hex())
        resp = p.recvline()
        p.close()
        # 根据响应判断 padding 是否合法
        return b'OK' in resp or b'200' in resp

    return padding_oracle_attack(oracle, ciphertext, iv)
```

### 4.5 DES 与弱密钥

**DES 特殊题型**：

1. 弱密钥：DES 有 4 个弱密钥，E(E(m)) = m（加密两次等于没加密）
2. 双重 DES = 单 DES：中间相遇攻击可将 2^56×2^56 降为 2^56
3. 3DES：E-D-E 三次加密，常见但 CTF 中一般直接给 key

```python
from Crypto.Cipher import DES

# DES 弱密钥
DES_WEAK_KEYS = [
    b'\x00\x00\x00\x00\x00\x00\x00\x00',
    b'\xff\xff\xff\xff\xff\xff\xff\xff',
    b'\xe0\xe0\xe0\xe0\xf1\xf1\xf1\xf1',
    b'\x1f\x1f\x1f\x1f\x0e\x0e\x0e\x0e',
]

def des_weak_key_attack(ciphertext):
    """DES 弱密钥攻击：试所有弱密钥"""
    for key in DES_WEAK_KEYS:
        cipher = DES.new(key, DES.MODE_ECB)
        try:
            plain = cipher.decrypt(ciphertext)
            if b'flag' in plain or plain.isascii():
                print(f"弱密钥 {key.hex()}: {plain}")
        except:
            pass
```

### 4.6 RC4 流密码

RC4 是流密码，常见于 Web 题和 Crypto 题。密钥重用时 XOR 两组密文可消去密钥流。

```python
from Crypto.Cipher import ARC4

def rc4_decrypt(key, data):
    """RC4 解密"""
    cipher = ARC4.new(key)
    return cipher.decrypt(data)

def rc4_key_reuse(c1, c2, known_plain1):
    """RC4 密钥重用：已知一组明文，恢复另一组"""
    keystream = xor(c1, known_plain1)
    return xor(c2, keystream)
```

***

## 五、哈希与消息认证

### 5.1 常见哈希题型

| 题型 | 哈希类型 | 攻击方法 | 工具 |
| --- | --- | --- | --- |
| 密码哈希破解 | MD5/SHA/NTLM | 字典/暴力 | hashcat / John |
| 哈希长度扩展 | MD5/SHA1/SHA256 | 追加数据不改原哈希 | hashpump / hash_extender |
| 哈希碰撞 | MD5/SHA1 | 构造碰撞对 | fastcoll / SHA1Collider |
| 彩虹表 | 任意 | 预计算查表 | rtgen / ophcrack |
| MAC 伪造 | HMAC-MD5/SHA | 长度扩展 / 密钥泄露 | hashpump |
| 随机数预测 | MD5/SHA | 基于时间/种子可预测 | 脚本 |

### 5.2 hashcat 深度使用

**安装与 GPU 配置**：

```bash
# 安装
sudo apt install hashcat
# 或从源码编译（推荐，支持最新 GPU）
git clone https://github.com/hashcat/hashcat.git
cd hashcat && make && make install

# 检查 GPU
hashcat -I                    # 列出可用设备
hashcat -b                    # 性能基准测试
hashcat -b -m 0               # 仅测 MD5 速度
```

**哈希模式速查**：

```bash
# 常用模式
-m 0      MD5               # 32 字符 hex
-m 100    SHA1              # 40 字符 hex
-m 1400   SHA256            # 64 字符 hex
-m 1700   SHA512            # 128 字符 hex
-m 900    MD4
-m 1000   NTLM              # Windows
-m 3200   bcrypt            # $2a$... / $2b$...
-m 5600   NetNTLMv2         # 域认证
-m 2500   WPA-PBKDF2        # WiFi
-m 13100  Kerberoasting     # 域渗透
-m 18200  AS-REP Roasting

# 带 salt 的模式
-m 10     md5($pass.$salt)
-m 20     md5($salt.$pass)
-m 110    sha1($pass.$salt)
-m 1410   sha256($pass.$salt)
-m 1420   sha256($salt.$pass)

# 格式：hash:salt（冒号分隔）
```

**攻击模式**：

```bash
# -a 0: 字典攻击（最常用）
hashcat -m 0 hash.txt rockyou.txt

# -a 1: 组合攻击（两个字典拼接）
hashcat -m 0 hash.txt dict1.txt dict2.txt

# -a 3: 暴力攻击（掩码）
hashcat -m 0 -a 3 hash.txt ?a?a?a?a?a?a
# 掩码说明：
# ?l = abcdefghijklmnopqrstuvwxyz
# ?u = ABCDEFGHIJKLMNOPQRSTUVWXYZ
# ?d = 0123456789
# ?s = !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
# ?a = ?l?u?d?s（所有可打印）
# 常用掩码组合：
hashcat -m 0 -a 3 hash.txt ?d?d?d?d        # 纯数字4位
hashcat -m 0 -a 3 hash.txt ?l?l?l?l?l?l    # 纯小写6位
hashcat -m 0 -a 3 hash.txt ?u?l?l?l?d?d?d  # 首大写+小写+3数字

# -a 6: 字典+掩码（右边追加）
hashcat -m 0 -a 6 hash.txt dict.txt ?d?d?d?d
# -a 7: 掩码+字典（左边追加）
hashcat -m 0 -a 7 hash.txt ?d?d dict.txt
```

**规则变换**：

```bash
# 内置规则
hashcat -m 0 hash.txt dict.txt -r best64.rule     # 64 条常用变换
hashcat -m 0 hash.txt dict.txt -r d3ad0ne.rule    # 更激进的变换
hashcat -m 0 hash.txt dict.txt -r rockyou-30000.rule  # 基于 rockyou 统计

# 多规则叠加
hashcat -m 0 hash.txt dict.txt -r best64.rule -r toggles5.rule

# 自定义规则（每行一条规则）
# :       不变
# l       转小写
# u       转大写
# c       首字母大写
# t       大小写翻转
# r       反转
# d       双写（password → passwordpassword）
# $x      末尾追加字符 x
# ^x      开头追加字符 x
# [       删除首字符
# ]       删除末字符
```

**会话管理**：

```bash
# 恢复中断的破解
hashcat -m 0 hash.txt dict.txt --session mycrack
# 中断后恢复：
hashcat --session mycrack --restore

# 查看已破解结果
hashcat -m 0 hash.txt --show

# 输出格式
hashcat -m 0 hash.txt dict.txt -o cracked.txt       # 保存结果
hashcat -m 0 hash.txt dict.txt --outfile-format=2   # 仅输出密码
```

**特殊场景**：

```bash
# 带盐哈希（格式：hash:salt）
echo "5d41402abc4b2a76b9719d911017c592:mysalt" > hash.txt
hashcat -m 10 hash.txt dict.txt    # md5($pass.$salt)

# 增量模式（不知道长度时）
hashcat -m 0 -a 3 hash.txt --increment --increment-min=4 --increment-max=12 ?a?a?a?a?a?a?a?a?a?a?a?a

# 限制 GPU 温度/风扇
hashcat -m 0 hash.txt dict.txt --gpu-temp-retain=75   # 保持 75°C
```

### 5.3 哈希长度扩展攻击

**原理**：对于 Merkle-Damgård 构造的哈希（MD5/SHA1/SHA256），已知 H(message) 和 len(message)，可以计算 H(message ∥ padding ∥ suffix) 而不需要知道 message 本身。

**条件**：

1. 哈希算法是 Merkle-Damgård 构造（MD5/SHA1/SHA256/SHA512）
2. 已知 H(message) 和 len(message)
3. 验证逻辑为 `hash(secret ∥ data)`，secret 长度已知或可枚举

```bash
# hashpump 工具
# 安装：git clone https://github.com/bwall/HashPump.git && cd HashPump && g++ *.cpp -o hashpump -lssl -lcrypto

# 用法：hashpump <已知哈希> <已知数据> <追加数据> <密钥长度>
hashpump 6ee4a469cd6e329a8c41c7e7e51a9b2d "data=value" "&admin=1" 16

# 输出：新哈希 + 新数据（含 padding）
```

**Python 实现**：

```python
from hashpumpy import hashpump

def hash_length_extension(original_hash, original_data, append_data, key_length):
    """哈希长度扩展攻击"""
    new_hash, new_data = hashpump(
        original_hash,
        original_data,
        append_data,
        key_length
    )
    print(f"新哈希: {new_hash}")
    print(f"新数据: {new_data}")
    # new_data 中包含原始数据 + padding + 追加数据
    return new_hash, new_data
```

**手动实现（不依赖工具）**：

```python
import struct
import hashlib

def md5_length_extend(original_hash_hex, original_data, append_data, key_length, hash_func='md5'):
    """
    MD5 长度扩展攻击手动实现
    原理：将 MD5 内部状态设为 original_hash，继续哈希 append_data
    """
    from Crypto.Hash import MD5, SHA1, SHA256

    # 计算原始消息总长度（含密钥）
    original_len = key_length + len(original_data)
    # 计算填充后的长度
    padded_len = original_len + (56 - original_len % 64) % 64 + 64

    # 构造 padding
    padding = b'\x80'
    padding += b'\x00' * ((56 - (original_len + 1) % 64) % 64)
    padding += struct.pack('<Q', original_len * 8)  # MD5 小端序

    # 新数据 = original_data + padding + append_data
    new_data = original_data + padding + append_data

    # 构造新的哈希计算器，设置内部状态为 original_hash
    # 这需要用到底层 API 或 hlextend 库
    # 简化：使用 hash_extender 或 hlextend 库
    import hlextend
    for kl in range(key_length, key_length + 1):
        h = hlextend.new(hash_func, original_data, original_hash_hex, kl)
        new_hash = h.extend(append_data)
        new_msg = h.padded_msg
        print(f"key_len={kl}: hash={new_hash}")

    return new_data
```

### 5.4 MD5 碰撞

**工具**：fastcoll（快速生成 MD5 碰撞对）。

```bash
# 安装 fastcoll
git clone https://github.com/cr-marcstevens/fastcoll.git
cd fastcoll && g++ -O3 -o fastcoll fastcoll_v1.0.0.5.cpp

# 生成碰撞对
echo "prefix" > prefix.bin
./fastcoll prefix.bin
# 输出 msg1.bin 和 msg2.bin，MD5 相同但内容不同

# 验证
md5sum msg1.bin msg2.bin
```

**CTF 场景**：

1. 文件上传：上传两个 MD5 相同但内容不同的文件绕过校验
2. 签名绕过：构造两个 MD5 相同的消息，一个合法一个恶意
3. PDF 碰撞：用 `makepdf.py` 生成内容不同但 MD5 相同的 PDF

### 5.5 hashid 哈希识别

```bash
# 识别哈希类型
hashid -m '5d41402abc4b2a76b9719d911017c592'
# 输出：MD5, MD4, NTLM 等

# 常见哈希长度特征
# 32 字符 → MD5 / MD4 / NTLM / LM
# 40 字符 → SHA1
# 56 字符 → SHA224 / SHA3-224
# 64 字符 → SHA256 / SHA3-256
# 96 字符 → SHA384
# 128 字符 → SHA512

# 特殊前缀
# $2a$ / $2b$ / $2y$ → bcrypt
# $1$ → MD5-crypt (Unix)
# $5$ → SHA256-crypt
# $6$ → SHA512-crypt
# $krb5pa$ → Kerberos
```

***

## 六、离散对数与 ElGamal

### 6.1 离散对数问题（DLP）

**定义**：已知 g, h, p，求 x 使得 g^x ≡ h (mod p)。

**难度取决于**：

1. p 的位数（越大越难）
2. p-1 的分解（p-1 平滑时可用 Pohlig-Hellman）
3. 生成元 g 的阶

### 6.2 Pohlig-Hellman 算法

**条件**：p-1 是平滑的（所有素因子较小）。

**原理**：将 DLP 模大素数分解为模各素因子幂的子问题，用 CRT 合并。

```python
# SageMath 实现（最简单）
def pohlig_hellman_sage(g, h, p):
    """
    SageMath Pohlig-Hellman 解离散对数
    g: 生成元, h: 目标, p: 模数
    """
    F = GF(p)
    return discrete_log(F(h), F(g))

# 用法
# sage: p = 0; g = 2; h = 0
# sage: x = pohlig_hellman_sage(g, h, p)
# sage: print(x)
```

**Python 纯实现**：

```python
def pohlig_hellman(g, h, p):
    """
    Pohlig-Hellman: 解 g^x = h mod p
    需要 p-1 的分解
    """
    from sympy import factorint
    from math import gcd

    order = p - 1
    factors = factorint(order)  # {p1: e1, p2: e2, ...}

    remainders = []
    moduli = []

    for pi, ei in factors.items():
        # 子群阶 q = pi^ei
        q = pi ** ei
        # g_i = g^(order/q), h_i = h^(order/q)
        exp = order // q
        gi = pow(g, exp, p)
        hi = pow(h, exp, p)

        # 在阶为 q 的子群中解离散对数（暴力 / Baby-step Giant-step）
        xi = bsgs(gi, hi, p, q)
        if xi is None:
            print(f"子群 {pi}^{ei} 解失败")
            return None

        remainders.append(xi)
        moduli.append(q)

    # CRT 合并
    from sympy.ntheory.modular import crt
    result = crt(moduli, remainders)
    return result[0]

def bsgs(g, h, p, order=None):
    """Baby-step Giant-step 算法"""
    from math import isqrt
    if order is None:
        order = p - 1
    n = isqrt(order) + 1

    # Baby step: 存储 g^j
    table = {}
    for j in range(n):
        table[pow(g, j, p)] = j

    # Giant step: 查找 h * g^(-in)
    factor = pow(g, -n, p)
    gamma = h
    for i in range(n):
        if gamma in table:
            return i * n + table[gamma]
        gamma = (gamma * factor) % p

    return None
```

### 6.3 ElGamal 加密

**参数**：公钥 (p, g, y)，y = g^x mod p，私钥 x。

**加密**：c₁ = g^k mod p, c₂ = m · y^k mod p

**解密**：m = c₂ · c₁^(-x) mod p = c₂ / c₁^x mod p

**常见攻击**：

1. k 重用：两组密文用相同 k，c₁ 相同，m₁/m₂ = c₂₁/c₂₂ mod p
2. p-1 平滑：Pohlig-Hellman 求私钥 x
3. 小群攻击：g 的阶很小，k 可在小群内枚举

```python
def elgamal_decrypt(c1, c2, x, p):
    """ElGamal 解密：m = c2 * c1^(-x) mod p"""
    s = pow(c1, x, p)
    s_inv = pow(s, -1, p)
    m = (c2 * s_inv) % p
    return m

def elgamal_k_reuse(c1, c2_1, c2_2, m1, p):
    """k 重用：已知一组明文，恢复另一组"""
    # c2_1 = m1 * y^k, c2_2 = m2 * y^k
    # m2 = c2_2 * m1 / c2_1 mod p
    m2 = (c2_2 * m1 * pow(c2_1, -1, p)) % p
    return m2
```

***

## 七、椭圆曲线密码

### 7.1 椭圆曲线基础

椭圆曲线：y² = x³ + ax + b (mod p)

**CTF 中 ECC 题的核心**：解椭圆曲线离散对数（ECDLP）——已知 G 和 Q = k·G，求 k。

### 7.2 ECC 题型与攻击

| 题型 | 攻击方法 | 条件 | SageMath 代码 |
| --- | --- | --- | --- |
| 阶平滑 | Pohlig-Hellman | E 的阶因子都小 | `Q.log(G)` 或 `discrete_log(Q, G, operation='+')` |
| 异常曲线 (p = 阶) | Smart 攻击 | E 的阶 = p（异常曲线） | 提升到 Qp 上解 |
| 阶 = p | Smart 攻击 | #E(Fp) = p | 见下方 |
| 阶有小子群 | Pohlig-Hellman | 阶的因子较小 | `Q.log(G)` |
| MOV 攻击 | Weil 配对降维到 Fp^k | 嵌入度 k 小 | `weil_pairing` |
| 超奇异曲线 | MOV / Smart | p ≤ 阶或嵌入度 = 2 | MOV 攻击 |
| Twist 攻击 | Invalid curve | 点在 twist 上 | 构造无效曲线 |

### 7.3 SageMath ECC 操作

```python
# 定义椭圆曲线
E = EllipticCurve(GF(p), [a, b])    # y^2 = x^3 + ax + b

# 创建点
G = E(xG, yG)                        # 已知坐标
Q = E(xQ, yQ)

# 查看曲线阶
order = E.order()
print(f"曲线阶: {order}, 因子分解: {factor(order)}")

# 点运算
P2 = 2 * G                           # 标量乘法
P3 = G + G + G                       # 点加法
PQ = G + Q                           # 两点相加

# 解 ECDLP（SageMath 自动选择算法）
k = Q.log(G)                         # 求 k 使得 k*G = Q
# 等价写法
k = discrete_log(Q, G, operation='+')

# 有限域上的阶
G.order()                            # G 的阶
```

### 7.4 Smart 攻击（异常曲线）

**条件**：E 的阶 = p（异常曲线），正常应 ≈ p+1。

**原理**：将问题提升到 p-adic 数域 Qp 上，可在线性时间解 ECDLP。

```python
# SageMath 实现
def smart_attack(E, P, Q, p):
    """
    Smart 攻击：异常曲线（阶 = p）的 ECDLP
    """
    def _lift_point(E_p2, P, p):
        """将点提升到 E(Qp)"""
        x1, y1 = P.xy()
        x1 = ZZ(x1); y1 = ZZ(y1)
        # 在 E/Qp 上找提升点
        for t in range(p):
            x2 = x1 + t * p
            # y^2 = x^3 + ax + b mod p^2
            a, b = E.a4(), E.a6()
            rhs = x2**3 + a*x2 + b
            if rhs.is_square():
                y2 = rhs.sqrt()
                return E_p2(x2, y2)
        return None

    # 提升到 Fp^2 上的曲线
    R = Zmod(p**2)
    E2 = EllipticCurve(R, [ZZ(E.a4()), ZZ(E.a6())])

    P_lift = _lift_point(E2, P, p)
    Q_lift = _lift_point(E2, Q, p)

    # 在 Qp 上计算
    p_times_P = p * P_lift
    p_times_Q = p * Q_lift

    # 提取 p-adic 对数
    xP, yP = p_times_P.xy()
    xQ, yQ = p_times_Q.xy()

    uP = -(xP / yP)
    uQ = -(xQ / yQ)

    k = (uQ / uP) % p
    return ZZ(k)
```

### 7.5 MOV 攻击

**条件**：嵌入度 k 小（超奇异曲线 k=2，某些特殊曲线 k=3）。

**原理**：用 Weil 配对将 ECDLP 从 E(Fp) 映射到 Fp^k 的 DLP，后者可用数域筛法更快求解。

```python
# SageMath 实现
def mov_attack(E, P, Q, p, k=None):
    """
    MOV 攻击：用 Weil 配对降维
    k: 嵌入度（超奇异曲线 k=2）
    """
    n = P.order()

    if k is None:
        # 尝试找嵌入度
        for k_candidate in range(2, 20):
            if (p**k_candidate - 1) % n == 0:
                k = k_candidate
                break

    if k is None:
        print("未找到嵌入度")
        return None

    print(f"嵌入度 k = {k}")

    # 扩域
    Fpk = GF(p**k, 'z')
    E_ext = E.base_extend(Fpk)

    # 找一个点 T 使得 Weil 配对 e(T, P) != 1
    for _ in range(100):
        T = E_ext.random_point()
        T = T * (T.order() // n)  # 映射到 n 阶子群
        if T == E_ext(0):
            continue
        wp = T.weil_pairing(E_ext(P), n)
        if wp != 1:
            break

    # 计算 Weil 配对
    alpha = T.weil_pairing(E_ext(P), n)  # e(T, P)
    beta = T.weil_pairing(E_ext(Q), n)   # e(T, Q) = alpha^k

    # 在 Fp^k 中解 DLP
    k_val = discrete_log(beta, alpha)
    return k_val
```

***

## 八、格密码与 LLL

### 8.1 格基础

格（Lattice）是 n 维空间中离散点的规则排列，由基向量的整数线性组合生成。

**CTF 中格相关的题型**：

1. 背包密码（Knapsack）：超递增序列被大数隐藏，用 LLL 还原
2. Hidden Number Problem（HNP）：已知 MSB，恢复完整数
3. Coppersmith 相关：多项式小根 → 格规约
4. GGH / NTRU：格基密码体制

### 8.2 LLL 算法

**原理**：给定格的一组基，LLL 算法在多项式时间内找到一组"较短且近似正交"的基（约化基）。

**SageMath 使用**：

```python
# 基本 LLL
M = Matrix(ZZ, [
    [1, 0, 0, n],
    [0, 1, 0, e],
    [0, 0, 1, -1],
])
M_reduced = M.LLL()
print(M_reduced)

# 带权重 LLL（调整某些维度的重要性）
# 用对角矩阵乘原矩阵放大某些维度
D = diagonal_matrix([2^100, 2^100, 1, 1])
M_weighted = (D * M).LLL() * D^(-1)
```

### 8.3 背包密码攻击

**原理**：超递增背包序列用模乘隐藏，密文是选取项的和。LLL 可从非超递增序列恢复超递增序列。

```python
def knapsack_attack(pub_key, ciphertext):
    """
    背包密码 LLL 攻击
    pub_key: 公开序列 [a1, a2, ..., an]
    ciphertext: 密文 S = sum(xi * ai)
    """
    n = len(pub_key)

    # 构造格
    # | 2  0  0 ... 0  0  |
    # | 0  2  0 ... 0  0  |
    # | ...               |
    # | 0  0  0 ... 2  0  |
    # | a1 a2 a3... an S  |
    M = Matrix(ZZ, n + 1, n + 1)
    for i in range(n):
        M[i, i] = 2
    for i in range(n):
        M[n, i] = pub_key[i]
    M[n, n] = -ciphertext

    # LLL 约化
    M_reduced = M.LLL()

    # 找短向量，分量应为 0 或 ±1
    for row in M_reduced:
        if row[-1] == 0:
            bits = [(row[i] + 1) // 2 for i in range(n)]
            # 验证
            if sum(b * a for b, a in zip(bits, pub_key)) == ciphertext:
                return bits
    return None
```

### 8.4 Hidden Number Problem

**条件**：已知 tᵢ 和 αᵢ = MSB(s·tᵢ mod p)，求 s。

**典型场景**：DSA/ECDSA 中随机数 k 的部分位泄露（nonce leakage），可构造 HNP 用 LLL 恢复私钥。

```python
def hnp_solve(p, t_list, a_list, bound):
    """
    Hidden Number Problem：已知 a_i ≈ s*t_i mod p 的高位，恢复 s
    t_list: [t1, t2, ..., tn]
    a_list: [a1, a2, ..., an]（s*t_i mod p 的高位近似值）
    bound: 未知部分的界
    """
    n = len(t_list)

    # 构造格
    M = Matrix(ZZ, n + 2, n + 2)
    for i in range(n):
        M[i, i] = p
    for i in range(n):
        M[n, i] = t_list[i]
    for i in range(n):
        M[n+1, i] = a_list[i]
    M[n, n] = bound
    M[n+1, n+1] = bound
    M[n, n+1] = 0
    M[n+1, n] = 0

    # 更标准的构造
    M2 = Matrix(ZZ, n + 2, n + 2)
    for i in range(n):
        M2[i, i] = p
    for i in range(n):
        M2[n, i] = t_list[i]
    M2[n, n] = bound // p  # 权重
    for i in range(n):
        M2[n+1, i] = a_list[i]
    M2[n+1, n+1] = bound // p

    M2_reduced = M2.LLL()

    # 从短向量提取 s
    for row in M2_reduced:
        s_candidate = (row[n] * p) // bound
        # 验证
        valid = True
        for i in range(n):
            if abs((s_candidate * t_list[i] - a_list[i]) % p) > bound:
                valid = False
                break
        if valid:
            return s_candidate % p
    return None
```

***

## 九、流密码与 XOR

### 9.1 XOR 基础

XOR 的核心性质：自逆（a ⊕ a = 0）、交换律、结合律。

**关键推论**：

- 已知明文和密文 → 密钥流 = 明文 ⊕ 密文
- 已知两组密文和一组明文 → 另一组明文 = c₂ ⊕ c₁ ⊕ m₁
- 密钥重用 → 两组密文 XOR 消去密钥流，得到两明文 XOR

### 9.2 XOR 密钥重用

```python
def xor(data, key):
    """XOR 加/解密"""
    key = key * (len(data) // len(key) + 1)
    return bytes(a ^ b for a, b in zip(data, key))

def xor_key_reuse_attack(c1, c2, known_plain1=None):
    """
    XOR 密钥重用攻击
    c1 = m1 ⊕ key, c2 = m2 ⊕ key
    c1 ⊕ c2 = m1 ⊕ m2
    """
    m1_xor_m2 = xor(c1, c2)
    if known_plain1:
        m2 = xor(m1_xor_m2, known_plain1)
        return m2
    return m1_xor_m2  # 返回两明文 XOR，需要进一步分析

# 已知部分明文时的 crib dragging
def crib_dragging(c1_xor_c2, crib):
    """
    Crib dragging：已知两组密文 XOR 和部分明文片段
    尝试在各个位置匹配 crib，看是否产生有意义的文本
    """
    results = []
    crib_bytes = crib if isinstance(crib, bytes) else crib.encode()
    for offset in range(len(c1_xor_c2) - len(crib_bytes) + 1):
        segment = c1_xor_c2[offset:offset+len(crib_bytes)]
        candidate = xor(segment, crib_bytes)
        # 检查是否为可打印文本
        try:
            text = candidate.decode('ascii')
            if all(32 <= ord(ch) <= 126 for ch in text):
                results.append((offset, text))
        except:
            pass
    return results
```

### 9.3 xortool 使用

```bash
# xortool：自动分析 XOR 加密的密文
# 安装：pip3 install xortool

# 分析密钥长度
xortool -x cipher.txt
# 输出最可能的密钥长度和密钥

# 指定密钥长度
xortool -x -l 13 cipher.txt

# 指定最可能字符（默认 0x00）
xortool -x -c 0x20 cipher.txt   # 空格最常见

# 多文件 XOR
xortool -x -l 4 cipher1.bin cipher2.bin
```

### 9.4 LFSR（线性反馈移位寄存器）

**原理**：输出序列由初始状态和反馈多项式决定，具有线性性质。

**攻击方法**：

1. 已知输出序列和阶数 → 解线性方程组求反馈系数
2. 已知输出序列，阶数未知 → Berlekamp-Massey 算法自动求最小多项式

```python
def berlekamp_massey(sequence, mod=2):
    """
    Berlekamp-Massey 算法
    求生成序列的最小线性反馈多项式
    """
    n = len(sequence)
    C = [1]  # 连接多项式
    B = [1]  # 辅助多项式
    L = 0    # 当前 LFSR 长度
    m = 1    # 迭代计数
    b = 1    # 前一个差异

    for i in range(n):
        # 计算差异
        d = sequence[i]
        for j in range(1, L + 1):
            if j < len(C):
                d = (d + C[j] * sequence[i - j]) % mod

        if d == 0:
            m += 1
        elif 2 * L <= i:
            T = C[:]
            coef = (d * pow(b, -1, mod)) % mod
            while len(C) < len(B) + m:
                C.append(0)
            for j in range(len(B)):
                C[j + m] = (C[j + m] - coef * B[j]) % mod
            L = i + 1 - L
            B = T
            b = d
            m = 1
        else:
            coef = (d * pow(b, -1, mod)) % mod
            while len(C) < len(B) + m:
                C.append(0)
            for j in range(len(B)):
                C[j + m] = (C[j + m] - coef * B[j]) % mod
            m += 1

    return L, C

# 已知反馈多项式和初始状态，生成序列
def lfsr_generate(taps, state, length):
    """
    taps: 反馈多项式系数 [c1, c2, ..., cn]
    state: 初始状态 [s0, s1, ..., sn-1]
    """
    n = len(state)
    seq = list(state)
    for _ in range(length - n):
        new_bit = 0
        for i in range(n):
            new_bit ^= taps[i] & seq[-(i+1)]
        seq.append(new_bit)
    return seq
```

***

## 十、编码与替换

### 10.1 编码识别决策树

```
输入数据
  │
  ├─ 全是 0-9, A-F（可选空格/换行）→ Hex
  │    └─ bytes.fromhex() 解码
  │
  ├─ A-Z, a-z, 0-9, +, /, = 结尾 → Base64
  │    └─ base64.b64decode() 解码
  │
  ├─ A-Z, 2-7, = 结尾 → Base32
  │    └─ base64.b32decode() 解码
  │
  ├─ 可打印字符，包含 !-"-&' 等 → Base85/Ascii85
  │    └─ base64.a85decode() / base64.b85decode()
  │
  ├─ 只有 A 和 B → 培根密码
  │
  ├─ 只有 . 和 -（可选空格/|/） → 摩尔斯电码
  │
  ├─ 含 % 后跟两位 Hex → URL 编码
  │    └─ urllib.parse.unquote()
  │
  ├─ 只有 0 和 1（可选空格）→ 二进制
  │    └─ int(binary, 2) → chr()
  │
  ├─ Unicode 转义 \uXXXX 或 &#XXXX; → Unicode 编码
  │    └─ codecs.decode(s, 'unicode_escape')
  │
  └─ 不确定 → CyberChef Magic / 自动解码脚本
```

### 10.2 特殊编码

```python
# Base85
import base64
base64.a85decode(data)    # Ascii85
base64.b85decode(data)    # Base85

# Base36
def base36_decode(s):
    return int(s, 36)

# Base58（Bitcoin 用）
# pip install base58
import base58
base58.b58decode(data)

# Base91
# pip install base91
import base91
base91.decode(data)

# ZZ 编码（zlib 压缩后 Base85）
import zlib, base64
def zz_decode(data):
    compressed = base64.a85decode(data)
    return zlib.decompress(compressed)
```

### 10.3 自定义编码/替换

CTF 中常出现自定义字母表替换，如：

```python
def custom_substitution_decode(ciphertext, custom_alphabet, standard_alphabet='abcdefghijklmnopqrstuvwxyz'):
    """自定义字母表替换解码"""
    table = str.maketrans(custom_alphabet.lower() + custom_alphabet.upper(),
                          standard_alphabet.lower() + standard_alphabet.upper())
    return ciphertext.translate(table)

# 示例：自定义 Base64 字母表
def custom_base64_decode(data, custom_alphabet):
    """自定义 Base64 字母表解码"""
    import base64
    std = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    table = str.maketrans(custom_alphabet, std)
    return base64.b64decode(data.translate(table))
```

***

## 十一、工具深度使用手册

### 11.1 SageMath 深度用法

**安装与启动**：

```bash
# Ubuntu/Debian
sudo apt install sagemath

# Conda（推荐，版本更新）
conda install -c conda-forge sage

# Docker
docker pull sagemath/sagemath:latest
docker run -it sagemath/sagemath:latest

# 启动
sage                  # 交互式
sage script.sage      # 跑脚本
sage -python script.py  # 用 Sage 的 Python（自带 gmpy2 等）
```

**RSA 全流程**：

```python
# 已知 p, q 解密
sage: p, q, e = 3483342589, 5035239467, 65537
sage: n = p * q
sage: phi = (p-1) * (q-1)
sage: d = inverse_mod(e, phi)
sage: m = power_mod(c, d, n)
sage: bytes.fromhex(hex(m)[2:])

# 分解 n
sage: factor(n)                    # 小 n 直接分解
sage: factor(2^256 - 1)            # 大数分解

# 多项式求根（Coppersmith）
sage: P.<x> = PolynomialRing(Zmod(n))
sage: f = (m_high + x)^e - c
sage: f.small_roots(X=2^bits, beta=1)

# 离散对数
sage: F = GF(p)
sage: discrete_log(F(h), F(g))    # 有限域 DLP
sage: E = EllipticCurve(GF(p), [a, b])
sage: Q.discrete_log(G)            # ECDLP

# LLL 格规约
sage: M = Matrix(ZZ, [[...], [...]])
sage: M.LLL()
sage: M.BKZ()                      # BKZ 更强但更慢

# 中国剩余定理
sage: crt([r1, r2, r3], [m1, m2, m3])
```

**SageMath 脚本模板**：

```python
#!/usr/bin/env sage
"""
SageMath 解题脚本模板
"""

# 题目参数
n = 0
e = 0
c = 0

# 分解 n
factors = factor(n)
print(f"n 的因子: {factors}")

# 如果 n 可分解
p, q = list(factors)  # 根据实际分解结果调整
phi = (p - 1) * (q - 1)
d = inverse_mod(e, phi)
m = power_mod(c, d, n)

# 转字符串
flag = bytes.fromhex(hex(int(m))[2:])
print(f"flag = {flag}")
```

### 11.2 RsaCtfTool 深度用法

```bash
# === 基础攻击 ===
# 一键 all 攻击（推荐，先跑一遍）
python3 RsaCtfTool.py -n N -e E --uncipher C --attack all

# 单种攻击（调试/已知弱点类型）
python3 RsaCtfTool.py -n N -e E --attack wiener --private
python3 RsaCtfTool.py -n N -e E --attack fermat --private
python3 RsaCtfTool.py -n N -e E --attack pollard_rho --private
python3 RsaCtfTool.py -n N -e E --attack factordb --private

# === 多组密文攻击 ===
# 共模攻击
python3 RsaCtfTool.py -n N -e E1 --uncipher C1 -e E2 --uncipher C2 --attack common_modulus

# Håstad 广播攻击
python3 RsaCtfTool.py -e 3 --uncipherfile c1.txt --uncipherfile c2.txt --uncipherfile c3.txt --attack hastads

# === 已知部分信息 ===
# 已知 p 的高位
python3 RsaCtfTool.py -n N -e E --known_bits_p 123456 --uncipher C

# 已知 d 的高位
python3 RsaCtfTool.py -n N -e E --known_bits_d 123456 --uncipher C

# === 从文件读取 ===
python3 RsaCtfTool.py -n $(cat n.txt) -e $(cat e.txt) --uncipher $(cat c.txt) --attack all

# === 输出私钥 ===
python3 RsaCtfTool.py -n N -e E --private
# 输出 PEM 格式私钥，可用 openssl 查看

# === 所有支持的攻击 ===
python3 RsaCtfTool.py --listattacks
# 常见攻击名称：
#   wiener          Wiener 攻击（d 小）
#   fermat          Fermat 分解（p≈q）
#   pollard_rho     Pollard's rho
#   pollard_pm1     Pollard's p-1（p-1 平滑）
#   factordb        在线查 factordb
#   hastads         Håstad 广播攻击
#   common_modulus  共模攻击
#   smallq          q 很小
#   boneh_durfee   Boneh-Durfee 攻击（d < n^0.292）
#   partial_q      已知 q 部分位
#   londahl         Londahl 攻击
#   siqs            自实现 SIQS 分解

# === 性能提示 ===
# 1. all 攻击按从快到慢的顺序尝试，通常秒级出结果
# 2. n 很大（> 2048 bit）时 factordb 和 fermat 先跑，再试 pollard
# 3. 跑不出结果 → 手动分析条件 → 写 SageMath 脚本
```

### 11.3 pycryptodome 深度用法

```python
from Crypto.Cipher import AES, DES, ARC4
from Crypto.Util.Padding import pad, unpad
from Crypto.PublicKey import RSA, ElGamal, ECC
from Crypto.Hash import MD5, SHA1, SHA256, HMAC
from Crypto.Random import get_random_bytes
from Crypto.Util.number import bytes_to_long, long_to_bytes, inverse, GCD

# === AES ===
# ECB
cipher = AES.new(key, AES.MODE_ECB)
ct = cipher.encrypt(pad(plaintext, 16))
pt = unpad(cipher.decrypt(ct), 16)

# CBC
cipher = AES.new(key, AES.MODE_CBC, iv=iv)
ct = cipher.encrypt(pad(plaintext, 16))
# 解密
cipher = AES.new(key, AES.MODE_CBC, iv=iv)
pt = unpad(cipher.decrypt(ct), 16)

# CTR
cipher = AES.new(key, AES.MODE_CTR, nonce=nonce)
ct = cipher.encrypt(plaintext)

# GCM（认证加密）
cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
ct, tag = cipher.encrypt_and_digest(plaintext)
# 验证
cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
pt = cipher.decrypt_and_verify(ct, tag)

# === RSA ===
# 生成密钥
key = RSA.generate(2048)
# 从 n, e, d 构造
key = RSA.construct((n, e, d))
# 从 PEM 读取
key = RSA.import_key(open('private.pem').read())

# 加解密
from Crypto.Cipher import PKCS1_OAEP, PKCS1_v1_5
cipher = PKCS1_OAEP.new(key)
ct = cipher.encrypt(plaintext)
pt = cipher.decrypt(ct)

# === 哈希 ===
h = SHA256.new()
h.update(data)
print(h.hexdigest())

# HMAC
hmac = HMAC.new(key, digestmod=SHA256)
hmac.update(data)
print(hmac.hexdigest())

# === 数字转换 ===
m = bytes_to_long(b'flag{hello}')
data = long_to_bytes(m)

# === 模运算 ===
d = inverse(e, phi)     # 模逆
g = GCD(a, b)           # 最大公约数
```

### 11.4 gmpy2 深度用法

```python
import gmpy2
from gmpy2 import mpz, isqrt, iroot, invert, powmod, is_prime, next_prime

# 高精度大整数
n = mpz('123456789012345678901234567890')

# 开方
s = isqrt(n)              # 整数平方根
m, exact = iroot(n, 3)    # 整数立方根，exact=True 表示精确

# 模运算
d = invert(e, phi)        # 模逆（比 pow(e, -1, phi) 快）
m = powmod(c, d, n)       # 模幂（比 pow(c, d, n) 快）

# 素数
print(is_prime(n))        # 素性测试
p = next_prime(n)         # 下一个素数

# 位操作
print(n.bit_length())     # 位长度
print(n.digits(16))       # 转 16 进制字符串

# Jacobi 符号（二次剩余判定）
print(gmpy2.jacobi(a, p))  # 1=二次剩余, -1=非剩余, 0=a被p整除
```

### 11.5 factordb 深度用法

```bash
# === 网页端 ===
# 访问 http://factordb.com/
# 输入 n，查看结果状态：
#   FF (Fully Factored)  → 完全分解，直接拿 p, q
#   CF (Composite, Factors) → 部分分解
#   C  (Composite)       → 未分解，需其他方法
#   P  (Prime)           → 本身素数
#   U  (Unit)            → 1
#   N  (Negative)        → 负数

# === Python API ===
from factordb.factordb import FactorDB

def factordb_query(n):
    """查询 factordb"""
    f = FactorDB(n)
    f.connect()
    status = f.get_status()
    # 'FF' = 完全分解, 'CF' = 部分分解, 'C' = 未分解
    factors = f.get_factor_list()
    print(f"状态: {status}, 因子: {factors}")
    return status, factors

# 批量查询
def factordb_batch(n_list):
    """批量查询 factordb"""
    results = {}
    for n in n_list:
        status, factors = factordb_query(n)
        results[n] = (status, factors)
        if status == 'FF':
            print(f"[+] n={n} 已完全分解: {factors}")
    return results

# === 注意事项 ===
# 1. factordb 有查询频率限制，批量查询时加 sleep
# 2. 某些 n 的分解结果可能被隐藏（需登录）
# 3. 状态 C 不代表无法分解，只是 factordb 还没算出来
# 4. 查询前先检查 n 是否是素数（is_prime），素数无需分解
```

### 11.6 hashcat 完整实战流程

```bash
# 第一步：识别哈希类型
hashid -m HASH_VALUE
# 或人工识别（看长度/前缀/格式）

# 第二步：选模式
# 常用：
# -m 0    MD5           32字符
# -m 100  SHA1          40字符
# -m 1400 SHA256        64字符
# -m 1000 NTLM          32字符
# -m 3200 bcrypt        $2b$... 前缀

# 第三步：准备哈希文件
echo '5d41402abc4b2a76b9719d911017c592' > hash.txt

# 第四步：选攻击方式
# 优先级：字典 > 规则变换 > 掩码暴力

# 字典攻击
hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt

# 规则变换（字典没跑出时）
hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt -r best64.rule

# 暴力（字典和规则都失败时，从短到长）
hashcat -m 0 -a 3 hash.txt ?d?d?d?d         # 4位数字
hashcat -m 0 -a 3 hash.txt ?l?l?l?l?l?l     # 6位小写
hashcat -m 0 -a 3 hash.txt ?a?a?a?a?a?a?a?a # 8位任意

# 第五步：查看结果
hashcat -m 0 hash.txt --show

# 第六步：失败时尝试
# 1. 换更大的字典
# 2. 组合攻击：hashcat -a 1 hash.txt dict1.txt dict2.txt
# 3. 掩码+字典：hashcat -a 6 hash.txt dict.txt ?d?d?d?d
# 4. 考虑是否哈希类型识别错误，换模式重试
```

### 11.7 工具组合实战场景

**场景 1：拿到 RSA 题的标准流程**

```
1. 提取 n, e, c
2. factordb.com 查 n → FF? 直接拿 p, q
                      → C?  继续
3. 看 e 大小 → e≤5? 小指数攻击
            → e>n^0.3? Wiener
            → 正常? 继续
4. RsaCtfTool --attack all → 跑出? 完成
5. 手动检查：
   - gcd(n1, n2)? 共享因子
   - fermat_factor(n)? p≈q
   - pollard_pm1(n)? p-1平滑
6. 都失败 → SageMath 写攻击脚本
```

**场景 2：对称加密题**

```
1. 确定算法和模式（AES-CBC/ECB/CTR...）
2. 有交互（nc）? → 可能是 Oracle 攻击
3. ECB → 分组重排
4. CBC + 解密 oracle → Padding Oracle
5. CTR + nonce 重用 → XOR 分析
6. 已知 key → 直接解密
```

**场景 3：编码/古典密码题**

```
1. CyberChef Magic → 自动识别
2. 识别不出 → 手动看特征
3. 古典密码 → 凯撒/维吉尼亚/栅栏暴力
4. 自定义编码 → 分析映射关系写脚本
```

***

## 附录：常用数学公式速查

```
欧拉函数：φ(p^k) = p^k - p^(k-1), φ(pq) = (p-1)(q-1)
费马小定理：a^(p-1) ≡ 1 (mod p)，a^(-1) ≡ a^(p-2) (mod p)
RSA：m = c^d mod n, d = e^(-1) mod φ(n)
中国剩余定理：x ≡ rᵢ (mod mᵢ), gcd(mᵢ,mⱼ)=1 时有唯一解 mod M
离散对数：g^x ≡ h (mod p)，求 x
Baby-step Giant-step：O(√n) 解 DLP
Pohlig-Hellman：p-1 平滑时降维解 DLP
LLL：O(2^(n/4)) 近似最短向量
Coppersmith：多项式小根上界 X = n^(1/e - ε)
```

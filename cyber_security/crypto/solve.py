"""
CTF Crypto Challenge - Complete Solver

题目分析:
    task.py 中 gen_prime 生成的素数 p 满足: p-1 是光滑数 (smooth number)
    即 p-1 = product(多个20-bit素数) * product(small_primes中若干项)
    所有素因子都很小, 这构成了两个弱点:
      1. n = p*q 可用 Pollard p-1 攻击分解
      2. c_2 = pow(e, m_2, n) 中的离散对数可用 Pohlig-Hellman 求解

求解三步:
    Step 1: Pollard p-1 分解 n → 得到 p, q
    Step 2: 标准 RSA 解密 c_1 → 得到 m_1 (flag前半)
    Step 3: Pohlig-Hellman + CRT 求解离散对数 c_2 → 得到 m_2 (flag后半)
"""

from math import gcd, lcm
from Crypto.Util.number import long_to_bytes, isPrime

# ============================================================
# 题目参数
# ============================================================
n = 127253273656755041488061369327088666642658775150495004366734207251894053962795751622161708537666419494472986448057578123084334734003516808810993297670864587942963094922535025747145569669008578643232131137540834194554273087372338583584899887807562752077414752047575492161255201233084800885495422227087041
e = 0x10001
c_1 = 57974701828832728577967450465255788289923655791414772437088078343474290797872710812238826926559487379480041620453016799514334887870064277070080870305537633158647391760915619606965385553888677686830658607302407071864404909932680594946855739256156855739204639535723294574774070264939278760140163103832650
c_2 = 55312120533067544987183869320534977277494480648083277810412946782179206524603471723382520688342053257844455599889227031261498427604180888592220640480807184227590167045531489390410336954305032937351566198667403155696242903124672179982018054628152426002330933819747747129472442087675331347179609346470886


# ============================================================
# Step 1: Pollard p-1 攻击分解 n
# ============================================================
# 原理:
#   gen_prime 中 p-1 = getPrime(20)^25 * (可能乘 2,3,5,...,37 中的若干项)
#   即 p-1 的所有素因子都非常小 (≤ 2^20 或 ≤ 37), p-1 是 B-smooth 数
#
#   Pollard p-1 算法:
#     1. 选择光滑界 B, 计算 M = lcm(1,2,...,B) 或 M = ∏ prime^k (所有 ≤ B 的素数幂)
#     2. 任选 a (通常取2), 计算 a^M mod n
#     3. 由费马小定理: 若 p-1 是 B-smooth, 则 M 是 p-1 的倍数
#        → a^M ≡ 1 (mod p) → gcd(a^M - 1, n) 被 p 整除
#     4. d = gcd(a^M - 1, n), 若 1 < d < n, 则 d 就是 p 的一个因子

def pollard_pm1(n, B=2**21):
    """
    Pollard p-1 算法
    n: 待分解的合数
    B: 光滑界, 需要覆盖 p-1 的最大素因子
       p-1 的最大素因子约为 2^20 (getPrime(20)), 取 B = 2^21 足够
    返回: n 的一个非平凡因子, 或 None
    """
    # 计算 M: 对所有 ≤ B 的素数, 将其最高幂次 ≤ B 的值累乘
    # 等价于 M = lcm(1, 2, ..., B), 但用素数幂累乘更高效
    a = 2  # 随机基, 2 即可
    # 筛法生成 ≤ B 的所有素数
    primes = []
    sieve = [True] * (B + 1)
    for i in range(2, B + 1):
        if sieve[i]:
            primes.append(i)
            for j in range(i * i, B + 1, i):
                sieve[j] = False

    print(f"  [*] 光滑界 B = 2^21 = {B}")
    print(f"  [*] 素数个数: {len(primes)}")

    # 对每个素数 l, 计算 l^k ≤ B 的最高幂次, 然后 a = a^(l^k) mod n
    for prime in primes:
        # 找到最大的 pk 使得 prime^pk ≤ B
        pk = prime
        while pk * prime <= B:
            pk *= prime
        a = pow(a, pk, n)

    d = gcd(a - 1, n)
    if 1 < d < n:
        return d
    return None

print("=" * 60)
print("Step 1: Pollard p-1 攻击分解 n")
print("=" * 60)
print(f"  [*] 原理: p-1 是光滑数 (所有素因子 ≤ 2^20), 适用 Pollard p-1")
print(f"  [*] gen_prime 中 p-1 = ∏getPrime(20) × ∏small_primes")
print(f"  [*] 最大素因子约为 2^20 ≈ 10^6, 光滑界取 B = 2^21 即可")

p = pollard_pm1(n, B=2**21)
if p is None:
    # 如果 B 不够大, 尝试更大的界
    print("  [-] B=2^21 失败, 尝试 B=2^22...")
    p = pollard_pm1(n, B=2**22)

q = n // p
assert p * q == n and isPrime(p) and isPrime(q), "分解验证失败"

print(f"\n  [+] 分解成功!")
print(f"  [+] p = {p}")
print(f"  [+] q = {q}")
print(f"  [+] 验证: p*q == n ✓")


# ============================================================
# Step 2: 标准 RSA 解密 c_1
# ============================================================
# 原理:
#   c_1 = m_1^e mod n  (标准 RSA 加密)
#   解密: m_1 = c_1^d mod n, 其中 d = e^(-1) mod φ(n)
#   φ(n) = (p-1)(q-1)

print("\n" + "=" * 60)
print("Step 2: RSA 解密 c_1 → m_1")
print("=" * 60)

phi = (p - 1) * (q - 1)
d = pow(e, -1, phi)
m_1 = pow(c_1, d, n)
flag_1 = long_to_bytes(m_1)
print(f"  [*] φ(n) = (p-1)(q-1)")
print(f"  [*] d = e^(-1) mod φ(n)")
print(f"  [*] m_1 = c_1^d mod n")
print(f"  [+] flag 前半部分: {flag_1}")


# ============================================================
# Step 3: Pohlig-Hellman + CRT 求解离散对数 c_2 → m_2
# ============================================================
# 原理:
#   c_2 = e^m_2 mod n  (离散对数问题)
#   直接对 n 求离散对数极难, 但 n = p*q 可以分解问题:
#
#   (1) CRT 分解: 求 m_2 mod (p-1) 和 m_2 mod (q-1)
#       c_2 ≡ e^m_2 (mod p) → 离散对数 mod p → m_2 mod (p-1)
#       c_2 ≡ e^m_2 (mod q) → 离散对数 mod q → m_2 mod (q-1)
#
#   (2) Pohlig-Hellman 算法求 mod p 的离散对数:
#       p-1 是光滑数, 设 p-1 = l1^k1 * l2^k2 * ... * lr^kr
#       将离散对数问题分解到每个 li^ki 阶子群上:
#         - 对每个小素数幂 li^ki, 求 m_2 mod li^ki
#         - 因为 li 很小, 用 BSGS (Baby-step Giant-step) 在 O(√li^ki) 内求解
#       最后用 CRT 合并所有 m_2 mod li^ki → m_2 mod (p-1)
#
#   (3) CRT 合并:
#       由 m_2 mod (p-1) 和 m_2 mod (q-1) 用广义 CRT 求出 m_2 mod lcm(p-1,q-1)
#       因为 m_2 是 flag 的后半部分 (短字符串), 值远小于 lcm(p-1,q-1), 结果就是 m_2 本身

def bsgs(g, h, p, order):
    """
    Baby-step Giant-step 算法
    求解 g^x ≡ h (mod p), 已知 g 的阶为 order
    复杂度: O(√order)
    """
    n = int(order**0.5) + 1
    # Baby step: 计算 g^j mod p, j = 0,1,...,n-1, 存入查找表
    table = {}
    gj = 1
    for j in range(n):
        table[gj] = j
        gj = gj * g % p
    # Giant step: 计算 h * (g^(-n))^i, 查找匹配
    gn_inv = pow(g, -n, p)
    gamma = h
    for i in range(n):
        if gamma in table:
            x = i * n + table[gamma]
            if x < order:
                return x
        gamma = gamma * gn_inv % p
    return None

def pohlig_hellman(g, h, p, factors):
    """
    Pohlig-Hellman 算法
    求解 g^x ≡ h (mod p), g 的阶为 p-1
    factors: p-1 的因子分解 [(l1,k1), (l2,k2), ...], 即 p-1 = ∏ li^ki
    返回: x mod (p-1)
    """
    n = p - 1
    residues = []
    moduli = []
    for li, ki in factors:
        # 子群阶: li^ki
        pk = li ** ki
        # 将问题投影到 li^ki 阶子群
        # g_i = g^(n/pk) mod p, h_i = h^(n/pk) mod p
        # g_i^x ≡ h_i (mod p), g_i 的阶恰好为 pk
        exp = n // pk
        gi = pow(g, exp, p)
        hi = pow(h, exp, p)
        # 用 BSGS 求解 x mod li^ki
        xi = bsgs(gi, hi, p, pk)
        if xi is None:
            raise ValueError(f"BSGS 求解失败: l={li}, k={ki}")
        residues.append(xi)
        moduli.append(pk)
    # CRT 合并所有 x mod li^ki → x mod (p-1)
    return crt_solve(residues, moduli)

def factor_smooth(n):
    """
    光滑数的因子分解 (试除法, 适用于 p-1 这类光滑数)
    返回: [(l1,k1), (l2,k2), ...] 使得 n = ∏ li^ki
    """
    factors = []
    d = 2
    while d * d <= n:
        if n % d == 0:
            k = 0
            while n % d == 0:
                n //= d
                k += 1
            factors.append((d, k))
        d += 1
    if n > 1:
        factors.append((n, 1))
    return factors

def crt_solve(residues, moduli):
    """
    中国剩余定理 (CRT) 求解
    x ≡ residues[i] (mod moduli[i]) 对所有 i
    模数不必互素 (广义 CRT, 需要相容性条件)
    """
    x = residues[0]
    m = moduli[0]
    for i in range(1, len(residues)):
        r, n = residues[i], moduli[i]
        # 求解: x + m*t ≡ r (mod n) → m*t ≡ (r-x) (mod n)
        g = gcd(m, n)
        if (r - x) % g != 0:
            raise ValueError("CRT 无解: 模数不兼容")
        # 约化: (m/g)*t ≡ (r-x)/g (mod n/g)
        m_g = m // g
        n_g = n // g
        rhs = (r - x) // g
        # 求 m_g 在 mod n_g 下的逆元
        inv = pow(m_g, -1, n_g)
        t = rhs * inv % n_g
        x = x + m * t
        m = m * n_g  # lcm(m, n)
    return x % m

print("\n" + "=" * 60)
print("Step 3: Pohlig-Hellman 求解离散对数 c_2 → m_2")
print("=" * 60)

# ---- 3a: 求解 m_2 mod (p-1) ----
print("\n  [*] 3a: 求解 m_2 mod (p-1)")
c2_p = c_2 % p
e_p = e % p
factors_p = factor_smooth(p - 1)
print(f"  [*] p-1 因子分解: {len(factors_p)} 个素因子")
print(f"  [*] 最大素因子: {max(l for l,k in factors_p)}")
print(f"  [*] Pohlig-Hellman: 对每个小素数幂子群用 BSGS 求解")
m2_mod_p = pohlig_hellman(e_p, c2_p, p, factors_p)
print(f"  [+] m_2 mod (p-1) = {m2_mod_p}")

# 验证
assert pow(e_p, m2_mod_p, p) == c2_p, "mod p 离散对数验证失败"
print(f"  [+] 验证: e^(m_2 mod p-1) ≡ c_2 (mod p) ✓")

# ---- 3b: 求解 m_2 mod (q-1) ----
print("\n  [*] 3b: 求解 m_2 mod (q-1)")
c2_q = c_2 % q
e_q = e % q
factors_q = factor_smooth(q - 1)
print(f"  [*] q-1 因子分解: {len(factors_q)} 个素因子")
print(f"  [*] 最大素因子: {max(l for l,k in factors_q)}")
m2_mod_q = pohlig_hellman(e_q, c2_q, q, factors_q)
print(f"  [+] m_2 mod (q-1) = {m2_mod_q}")

# 验证
assert pow(e_q, m2_mod_q, q) == c2_q, "mod q 离散对数验证失败"
print(f"  [+] 验证: e^(m_2 mod q-1) ≡ c_2 (mod q) ✓")

# ---- 3c: CRT 合并 ----
print("\n  [*] 3c: CRT 合并 m_2 mod (p-1) 和 m_2 mod (q-1)")
print(f"  [*] gcd(p-1, q-1) = {gcd(p-1, q-1)}")
L = lcm(p - 1, q - 1)
m_2 = crt_solve([m2_mod_p, m2_mod_q], [p - 1, q - 1])
print(f"  [*] lcm(p-1, q-1) 位数: {L.bit_length()}")
print(f"  [+] m_2 = {m_2}")

# 验证
assert pow(e, m_2, n) == c_2, "离散对数最终验证失败"
print(f"  [+] 验证: e^m_2 ≡ c_2 (mod n) ✓")

flag_2 = long_to_bytes(m_2)
print(f"  [+] flag 后半部分: {flag_2}")


# ============================================================
# 输出完整 flag
# ============================================================
full_flag = flag_1 + flag_2
print(f"\n{'='*60}")
print(f"[+] 完整 flag: {full_flag.decode()}")
print(f"{'='*60}")

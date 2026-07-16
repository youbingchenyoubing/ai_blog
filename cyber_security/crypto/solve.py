"""
CTF Crypto Challenge - Complete Solver

题目: task.py
    gen_prime 生成的素数 p 满足: p-1 是光滑数 (smooth number)
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
#   task.py 中 gen_prime 的逻辑:
#     p = reduce(mul, [getPrime(20) for _ in range(512//20)])  # 25个20-bit素数相乘
#     for i in range(lim=7):
#         if isPrime(p+1): return p+1
#         p *= small_primes[i]   # small_primes = [2,3,5,7,11,13,17,19,23,29,31,37]
#
#   所以 p-1 = ∏(25个~2^20的素数) × ∏(small_primes中0~6项)
#   p-1 的所有素因子都非常小 (最大约 2^20), 即 p-1 是 B-smooth 数 (B ≈ 2^20)
#
#   Pollard p-1 算法利用这个弱点:
#     1. 选择光滑界 B ≥ max(p-1 的所有素因子), 这里取 B = 2^21
#     2. 计算 M = ∏ l^k (对所有素数 l, l^k ≤ B), 这保证 M 是 (p-1) 的倍数
#     3. 任选 a (通常取2), 计算 a_M = a^M mod n
#     4. 由费马小定理: a^(p-1) ≡ 1 (mod p), 而 M 是 (p-1) 的倍数
#        所以 a^M ≡ 1 (mod p), 即 (a^M - 1) 是 p 的倍数
#     5. d = gcd(a^M - 1, n), 若 1 < d < n, 则 d = p (或 p 的某个因子)
#        因为 a^M - 1 同时被 p 和可能被 q 整除的概率极低

def pollard_pm1(n, B=2**21):
    """
    Pollard p-1 算法分解 n
    n: 待分解的合数 (n = p*q)
    B: 光滑界, 需要覆盖 p-1 的最大素因子
       p-1 的最大素因子约为 2^20 (getPrime(20)), 取 B = 2^21 足够
    返回: n 的一个非平凡因子, 或 None
    """
    a = 2  # 基, 通常取 2 即可

    # 筛法生成 ≤ B 的所有素数
    primes = []
    sieve = [True] * (B + 1)
    for i in range(2, B + 1):
        if sieve[i]:
            primes.append(i)
            for j in range(i * i, B + 1, i):
                sieve[j] = False

    print(f"  [*] 光滑界 B = 2^21 = {B}")
    print(f"  [*] ≤ B 的素数个数: {len(primes)}")

    # 核心: 对每个素数 l, 计算 a = a^(l^k) mod n (l^k ≤ B 的最大幂)
    # 这等价于计算 a^M mod n, 其中 M = ∏ l^k
    # 每步用 pow(a, l^k, n) 而不是直接算 M, 避免中间结果溢出
    for prime in primes:
        pk = prime
        while pk * prime <= B:
            pk *= prime
        a = pow(a, pk, n)

    # gcd 检查
    d = gcd(a - 1, n)
    if 1 < d < n:
        return d
    return None

print("=" * 60)
print("Step 1: Pollard p-1 攻击分解 n")
print("=" * 60)
print(f"  [*] 原理: p-1 是光滑数 (所有素因子 ≤ 2^20)")
print(f"  [*] gen_prime 中 p-1 = ∏getPrime(20) × ∏small_primes[:i]")
print(f"  [*] 最大素因子 ≈ 2^20, 光滑界取 B = 2^21")

p = pollard_pm1(n, B=2**21)
if p is None:
    print("  [-] B=2^21 失败, 尝试 B=2^22...")
    p = pollard_pm1(n, B=2**22)

q = n // p
assert p * q == n and isPrime(p) and isPrime(q), "分解验证失败"

print(f"\n  [+] 分解成功!")
print(f"  [+] p = {p}")
print(f"  [+] q = {q}")
print(f"  [+] 验证: p*q == n ✓, p is prime ✓, q is prime ✓")


# ============================================================
# Step 2: 标准 RSA 解密 c_1
# ============================================================
# c_1 = m_1^e mod n  (标准 RSA 加密)
# 解密: m_1 = c_1^d mod n, 其中 d = e^(-1) mod φ(n)
# φ(n) = (p-1)(q-1)  (Euler 函数, n 是两个素数的乘积)

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
# 问题: c_2 = e^m_2 mod n, 已知 e, c_2, n, 求 m_2
# 这是离散对数问题 (DLP), 直接对 n 求解极难
# 但 n = p*q 且 p-1, q-1 都是光滑数, 可以高效求解:
#
# (1) CRT 分解: 将 mod n 的 DLP 分解为 mod p 和 mod q 的 DLP
#     c_2 ≡ e^m_2 (mod p) → 求 m_2 mod ord_p(e), ord_p(e) | (p-1)
#     c_2 ≡ e^m_2 (mod q) → 求 m_2 mod ord_q(e), ord_q(e) | (q-1)
#
# (2) Pohlig-Hellman 算法求 mod p 的离散对数:
#     设 p-1 = l1^k1 * l2^k2 * ... * lr^kr (光滑分解)
#     将大群 (Z/pZ)* 上的 DLP 分解为每个 li^ki 阶子群上的小 DLP:
#       a. 令 n = p-1, 对每个素数幂 li^ki:
#          gi = g^(n/li^ki) mod p  (投影到 li^ki 阶子群的生成元)
#          hi = h^(n/li^ki) mod p  (投影到 li^ki 阶子群的目标)
#          求 xi 使得 gi^xi ≡ hi (mod p), xi < li^ki
#       b. 因为 li 很小 (≤ 2^20), 用 BSGS 在 O(√li^ki) 内求解 xi
#       c. xi 就是 m_2 mod li^ki
#     CRT 合并所有 xi → m_2 mod (p-1)
#
# (3) CRT 合并 mod p 和 mod q 的结果:
#     m_2 mod (p-1) 和 m_2 mod (q-1) → m_2 mod lcm(p-1, q-1)
#     因为 m_2 是 flag 后半部分 (短字符串), 值远小于 lcm(p-1, q-1)
#     所以 CRT 结果就是 m_2 本身

def bsgs(g, h, p, order):
    """
    Baby-step Giant-step 算法
    求解 g^x ≡ h (mod p), 已知 g 的阶为 order
    时间/空间复杂度: O(√order)
    """
    n = int(order**0.5) + 1
    # Baby step: 预计算 g^j (j=0..n-1), 存入哈希表
    table = {}
    gj = 1
    for j in range(n):
        table[gj] = j
        gj = gj * g % p
    # Giant step: 对 i=0..n-1, 检查 h * (g^(-n))^i 是否在表中
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
    factors: p-1 的因子分解 [(l1,k1), (l2,k2), ...], p-1 = ∏ li^ki
    返回: x mod (p-1)
    """
    order = p - 1
    residues = []
    moduli = []
    for li, ki in factors:
        pk = li ** ki
        # 投影到 li^ki 阶子群
        exp = order // pk
        gi = pow(g, exp, p)   # 子群生成元, 阶 = li^ki
        hi = pow(h, exp, p)   # 子群目标
        # BSGS 求解 x mod li^ki
        xi = bsgs(gi, hi, p, pk)
        if xi is None:
            raise ValueError(f"BSGS 失败: l={li}, k={ki}")
        residues.append(xi)
        moduli.append(pk)
    # CRT 合并
    return crt_solve(residues, moduli)

def factor_smooth(n):
    """
    光滑数因子分解 (试除法)
    p-1 是光滑数, 所有因子很小, 试除法足够快
    返回: [(l1,k1), (l2,k2), ...], n = ∏ li^ki
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
    广义中国剩余定理 (CRT)
    求解: x ≡ residues[i] (mod moduli[i]) 对所有 i
    模数不必互素, 但需要相容性: residues[i] ≡ residues[j] (mod gcd(moduli[i], moduli[j]))
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
        inv = pow(m_g, -1, n_g)
        t = rhs * inv % n_g
        x = x + m * t
        m = m * n_g  # = lcm(m, n)
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
print(f"  [*] Pohlig-Hellman: 对每个素数幂子群用 BSGS 求解")
m2_mod_p = pohlig_hellman(e_p, c2_p, p, factors_p)
print(f"  [+] m_2 mod (p-1) = {m2_mod_p}")
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
assert pow(e_q, m2_mod_q, q) == c2_q, "mod q 离散对数验证失败"
print(f"  [+] 验证: e^(m_2 mod q-1) ≡ c_2 (mod q) ✓")

# ---- 3c: CRT 合并 ----
print("\n  [*] 3c: CRT 合并 m_2 mod (p-1) 和 m_2 mod (q-1)")
print(f"  [*] gcd(p-1, q-1) = {gcd(p-1, q-1)}")
L = lcm(p - 1, q - 1)
m_2 = crt_solve([m2_mod_p, m2_mod_q], [p - 1, q - 1])
print(f"  [*] lcm(p-1, q-1) 位数: {L.bit_length()}")
print(f"  [+] m_2 = {m_2}")
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

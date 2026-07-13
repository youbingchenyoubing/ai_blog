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
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")  # 强制 stdout 使用 utf-8, 避免 Windows GBK 编不下 ✓ 等符号
except AttributeError:
    pass
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

def _sieve_primes(B):
    """埃氏筛生成 <= B 的所有素数"""
    if B < 2:
        return []
    sieve = bytearray([1]) * (B + 1)
    sieve[0:2] = b"\x00\x00"
    i = 2
    while i * i <= B:
        if sieve[i]:
            sieve[i * i:: i] = b"\x00" * len(sieve[i * i:: i])
        i += 1
    return [i for i in range(2, B + 1) if sieve[i]]

def pollard_pm1(n, B, base=2, check_every=2000):
    """
    返回 (state, factor):
      state == 'factor' -> factor 为非平凡因子
      state == 'both'   -> gcd == n, 两个因子同时被覆盖, B 偏大
      state == 'trivial' -> gcd == 1, B 偏小 (或基不合适)
    """
    primes = _sieve_primes(B)
    a = base
    cnt = 0
    for pr in primes:
        pk = pr
        while pk * pr <= B:
            pk *= pr
        a = pow(a, pk, n)
        cnt += 1
        if cnt % check_every == 0:
            d = gcd(a - 1, n)
            if d == n:
                return ('both', None)
            if 1 < d < n:
                return ('factor', d)
    d = gcd(a - 1, n)
    if d == n:
        return ('both', None)
    if 1 < d < n:
        return ('factor', d)
    return ('trivial', None)

def pollard_pm1_auto(n, B_init=1 << 19, B_max=1 << 22):
    """
    自动调整 B:
      state == 'both'     -> B 太大, 让一个因子先被完整覆盖 -> 调小 B
      state == 'trivial'  -> B 太小, 没覆盖一个因子       -> 增大 B
      state == 'factor'   -> 返回该因子
    同一 B 多个底数 (2,3,5,7) 都失败才换方向
    """
    B = B_init
    while True:
        print(f"  [*] 尝试 B = {B}")
        saw_both = False
        for base in (2, 3, 5, 7):
            state, d = pollard_pm1(n, B, base=base, check_every=500)
            if state == 'factor':
                return d
            if state == 'both':
                saw_both = True
                break                       # 同一 B 下换基也没意义, 直接降 B
        if saw_both:
            if B <= 1 << 15:
                return None
            B >>= 1
        else:
            if B >= B_max:
                return None
            B <<= 1

print("=" * 60)
print("Step 1: Pollard p-1 攻击分解 n")
print("=" * 60)
print(f"  [*] 原理: p-1 是光滑数 (所有素因子 ≤ 2^20), 适用 Pollard p-1")
print(f"  [*] gen_prime 中 p-1 = ∏getPrime(20) × ∏small_primes")

p = pollard_pm1_auto(n, B_init=1 << 19, B_max=1 << 22)

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

def element_order(g, p, prime_factors_of_pm1):
    """
    求 g 在 F_p^* 里的阶.
    prime_factors_of_pm1: p-1 的素因子列表 (任意次幂均可, 只要包含每个素数即可)
    返回 ord(g) | p-1
    """
    order = p - 1
    for pr in prime_factors_of_pm1:
        while order % pr == 0 and pow(g, order // pr, p) == 1:
            order //= pr
    return order

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
print("\n  [*] 3c: 合并 m_2 mod ord_p(e) 和 m_2 mod ord_q(e)")
# 重要: DLP 在 F_p^* 的解空间模是 ord(e), 而不是 p-1
#       因为 e 的阶 ord_p(e) | (p-1), 而 m_2 唯一仅由 ord_p(e) 决定
#       直接把 (m2_mod_p, p-1) 与 (m2_mod_q, q-1) 做广义 CRT, 因为
#       gcd(p-1, q-1) 可能整除 (m_p - m_q) 的真值又恰好不整除残差 -- 看似无解
#       合并算法必须使用真正的群阶 ord(e).
order_p = element_order(e_p, p, [l for (l, _) in factors_p])
order_q = element_order(e_q, q, [l for (l, _) in factors_q])
print(f"  [*] ord_p(e) = {order_p}")
print(f"  [*] ord_q(e) = {order_q}")
print(f"  [*] gcd(ord_p, ord_q) = {gcd(order_p, order_q)}")
L = lcm(order_p, order_q)
m_2 = crt_solve([m2_mod_p % order_p, m2_mod_q % order_q], [order_p, order_q])
print(f"  [*] lcm(ord_p, ord_q) 位数: {L.bit_length()}")
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

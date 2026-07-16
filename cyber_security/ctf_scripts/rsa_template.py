#!/usr/bin/env python3
"""
RSA 综合解题模板

按题目条件自动选择攻击方法，从快到慢依次尝试：
    1. 已知 p/q/d   -> 直接解密
    2. factordb     -> 在线查 n 是否已分解
    3. 小指数 e<=5  -> 直接开方 / 枚举 k*n
    4. e 很大       -> Wiener (d < n^0.25)
    5. p≈q         -> Fermat 分解
    6. p-1 平滑     -> Pollard's p-1
    7. 多组密文     -> 共模 / 广播 / 共享因子
    8. dp 泄露      -> dp_leak 攻击
    9. 多素数 n     -> factordb 拿到多因子后直接解密

依赖:
    pip install gmpy2 pycryptodome factordb-python

用法:
    1. 直接修改下方 "题目参数" 区域填入 n/e/c 等
    2. python3 rsa_template.py
    3. 也可以 from rsa_template import RSASolver, 在代码里调用
"""

import sys
import time
from math import gcd, isqrt

# === 复用 ctf_scripts/rsa_attacks.py 中的攻击实现，避免重复造轮子 ===
from rsa_attacks import (
    extended_gcd, modinv, int_to_bytes,
    small_e_attack, common_module_attack, fermat_factor, wiener_attack,
)


# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------
def _try_decode(m):
    """尽量把整数转成可读字符串"""
    try:
        b = int_to_bytes(m)
        if all(32 <= c < 127 or c in (9, 10, 13) for c in b):
            return b.decode('utf-8', 'replace')
        return b
    except Exception:
        return None


def rsa_decrypt_with_factors(c, primes, e):
    """已知 n 的所有素因子，统一解密（支持多素数 RSA）"""
    from functools import reduce
    n = reduce(lambda a, b: a * b, primes)
    phi = reduce(lambda a, b: a * b, [p - 1 for p in primes])
    d = modinv(e, phi)
    return pow(c, d, n)


# ----------------------------------------------------------------------
# 额外的攻击实现 (rsa_attacks.py 里没有的)
# ----------------------------------------------------------------------
def pollard_pm1(n, B=2 ** 20):
    """Pollard p-1 分解：p-1 平滑时有效"""
    a = 2
    for j in range(2, B):
        a = pow(a, j, n)
        if j % 1000 == 0:
            d = gcd(a - 1, n)
            if 1 < d < n:
                return d, n // d
    d = gcd(a - 1, n)
    if 1 < d < n:
        return d, n // d
    return None, None


def dp_leak_attack(e, n, dp):
    """已知 dp = d mod (p-1)，恢复 p, q"""
    for k in range(1, e):
        if (e * dp - 1) % k:
            continue
        p_candidate = (e * dp - 1) // k + 1
        if n % p_candidate == 0:
            return p_candidate, n // p_candidate
    return None, None


def shared_factor_attack(n_list):
    """检查多组 n 之间是否共享素因子 p"""
    for i in range(len(n_list)):
        for j in range(i + 1, len(n_list)):
            p = gcd(n_list[i], n_list[j])
            if 1 < p < n_list[i]:
                return p, i, j
    return None, None


def hastad_broadcast(c_list, n_list, e):
    """Håstad 广播攻击：同一明文用 e 个不同模数加密"""
    from functools import reduce
    try:
        from gmpy2 import iroot
    except ImportError:
        print("[!] 需要 gmpy2")
        return None

    N = reduce(lambda a, b: a * b, n_list)
    result = 0
    for ci, ni in zip(c_list, n_list):
        Ni = N // ni
        result = (result + ci * Ni * pow(Ni, -1, ni)) % N
    m, exact = iroot(result, e)
    return int(m) if exact else None


def factordb_lookup(n):
    """在线查 factordb，返回因子列表或 None"""
    try:
        from factordb.factordb import FactorDB
    except ImportError:
        print("[!] 需要 factordb-python: pip install factordb-python")
        return None
    f = FactorDB(n)
    f.connect()
    status = f.get_status()
    factors = f.get_factor_list()
    if status == 'FF' and len(factors) >= 2:
        return factors
    return None


# ----------------------------------------------------------------------
# 综合解题器
# ----------------------------------------------------------------------
class RSASolver:
    """
    RSA 综合解题器：按条件从快到慢依次尝试攻击方法。

    使用方式:
        solver = RSASolver(n=..., e=..., c=...)
        solver.solve()

    高级用法 (传入额外信息):
        solver = RSASolver(n=..., e=..., c=..., dp=...)
        solver.solve()

    多组密文:
        solver = RSASolver(n=..., e=..., c=...)  # 主密文
        solver.add_group(c2, e2)                 # 第二组共模
        solver.add_group(c2, e2, n2)             # 第二组不同 n (广播/共享因子)
    """

    def __init__(self, n=None, e=None, c=None,
                 p=None, q=None, d=None, dp=None, dq=None,
                 verbose=True):
        self.n = n
        self.e = e
        self.c = c
        self.p = p
        self.q = q
        self.d = d
        self.dp = dp
        self.dq = dq
        self.verbose = verbose

        # 多组密文 (c, e, n)；第一组即上面的 n/e/c
        self.groups = []

    # ----------------- 日志 -----------------
    def log(self, msg):
        if self.verbose:
            print(msg)

    # ----------------- 多组密文管理 -----------------
    def add_group(self, c, e=None, n=None):
        self.groups.append({
            'c': c, 'e': e or self.e, 'n': n or self.n
        })

    # ----------------- 解密主流程 -----------------
    def decrypt_with_factors(self, primes):
        """已知 n 的素因子后统一解密"""
        m = rsa_decrypt_with_factors(self.c, primes, self.e)
        self.log(f"[+] 明文 (int): {m}")
        decoded = _try_decode(m)
        if decoded is not None:
            self.log(f"[+] 明文 (str): {decoded}")
        return m

    # ----------------- 单组攻击 -----------------
    def _try_direct(self):
        """已知 p, q 或 d，直接解密"""
        if self.p and self.q:
            self.log("[*] 已知 p, q，直接解密")
            assert self.p * self.q == self.n, "p*q != n"
            return self.decrypt_with_factors([self.p, self.q])
        if self.d and self.n:
            self.log("[*] 已知 d，直接解密")
            m = pow(self.c, self.d, self.n)
            self.log(f"[+] 明文 (int): {m}")
            decoded = _try_decode(m)
            if decoded is not None:
                self.log(f"[+] 明文 (str): {decoded}")
            return m
        return None

    def _try_factordb(self):
        """在线查 factordb 看 n 是否已分解"""
        self.log("[*] 尝试 factordb 查询...")
        factors = factordb_lookup(self.n)
        if factors:
            self.log(f"[+] factordb 已分解: {factors}")
            return self.decrypt_with_factors(factors)
        self.log("[-] factordb 未分解，跳过")
        return None

    def _try_small_e(self):
        """e 很小（<=5）时的小指数攻击"""
        if self.e is None or self.e > 5:
            return None
        self.log(f"[*] e={self.e} 很小，尝试小指数攻击")
        m = small_e_attack(self.c, self.e, self.n)
        if m is not None:
            self.log(f"[+] 明文 (int): {m}")
            decoded = _try_decode(m)
            if decoded is not None:
                self.log(f"[+] 明文 (str): {decoded}")
            return m
        self.log("[-] 小指数攻击失败")
        return None

    def _try_wiener(self):
        """e 很大时尝试 Wiener 攻击"""
        if self.e is None or self.n is None:
            return None
        if self.e <= self.n ** 0.3:
            return None
        self.log("[*] e 相对 n 较大，尝试 Wiener 攻击")
        result = wiener_attack(self.e, self.n)
        if result:
            d, p, q = result
            self.log(f"[+] Wiener 命中: d = {d}")
            self.p, self.q, self.d = p, q, d
            m = pow(self.c, d, self.n)
            self.log(f"[+] 明文 (int): {m}")
            decoded = _try_decode(m)
            if decoded is not None:
                self.log(f"[+] 明文 (str): {decoded}")
            return m
        self.log("[-] Wiener 攻击失败")
        return None

    def _try_fermat(self):
        """p/q 接近时尝试 Fermat 分解"""
        self.log("[*] 尝试 Fermat 分解 (p≈q)...")
        p, q = fermat_factor(self.n, max_iter=100000)
        if p and q:
            self.log(f"[+] Fermat 分解成功: p={p}, q={q}")
            self.p, self.q = p, q
            return self.decrypt_with_factors([p, q])
        self.log("[-] Fermat 分解失败")
        return None

    def _try_pollard_pm1(self):
        """p-1 平滑时尝试 Pollard p-1"""
        self.log("[*] 尝试 Pollard p-1 (p-1 平滑)...")
        p, q = pollard_pm1(self.n)
        if p and q:
            self.log(f"[+] Pollard p-1 成功: p={p}, q={q}")
            self.p, self.q = p, q
            return self.decrypt_with_factors([p, q])
        self.log("[-] Pollard p-1 失败")
        return None

    def _try_dp_leak(self):
        """dp 泄露攻击"""
        if self.dp is None:
            return None
        self.log("[*] 已知 dp，尝试 dp 泄露攻击")
        result = dp_leak_attack(self.e, self.n, self.dp)
        if result:
            p, q = result
            self.log(f"[+] dp 泄露命中: p={p}, q={q}")
            self.p, self.q = p, q
            return self.decrypt_with_factors([p, q])
        self.log("[-] dp 泄露攻击失败")
        return None

    # ----------------- 多组攻击 -----------------
    def _try_shared_factor(self):
        """多组 n 之间共享因子"""
        if len(self.groups) < 2:
            return None
        self.log("[*] 多组密文 -> 尝试共享因子攻击")
        n_list = [g['n'] for g in self.groups]
        r = shared_factor_attack(n_list)
        if r is None:
            self.log("[-] 共享因子攻击无果")
            return None
        p, i, j = r
        self.log(f"[+] n[{i}] 和 n[{j}] 共享因子 p = {p}")
        # 用第 i 组解密
        g = self.groups[i]
        q = g['n'] // p
        m = rsa_decrypt_with_factors(g['c'], [p, q], g['e'])
        self.log(f"[+] 明文 (int): {m}")
        decoded = _try_decode(m)
        if decoded is not None:
            self.log(f"[+] 明文 (str): {decoded}")
        return m

    def _try_common_modulus(self):
        """共模攻击：相同 n，不同 e"""
        if len(self.groups) < 2:
            return None
        if self.n is None:
            return None
        same_n = [g for g in self.groups if g['n'] == self.n and g['e'] != self.e]
        if not same_n:
            return None
        self.log("[*] 发现相同 n 不同 e -> 共模攻击")
        for g in same_n:
            if gcd(self.e, g['e']) != 1:
                continue
            m = common_module_attack(self.c, g['c'], self.e, g['e'], self.n)
            if m is not None:
                self.log(f"[+] 明文 (int): {m}")
                decoded = _try_decode(m)
                if decoded is not None:
                    self.log(f"[+] 明文 (str): {decoded}")
                return m
        self.log("[-] 共模攻击失败")
        return None

    def _try_hastad(self):
        """Håstad 广播攻击：e 个不同模数，相同 e"""
        if len(self.groups) < self.e:
            return None
        distinct_n = [g for g in self.groups if g['n'] != self.n]
        if len(distinct_n) + 1 < self.e:
            return None
        self.log(f"[*] 密文数 >= e={self.e}，尝试 Håstad 广播攻击")
        c_list = [self.c] + [g['c'] for g in distinct_n[:self.e - 1]]
        n_list = [self.n] + [g['n'] for g in distinct_n[:self.e - 1]]
        m = hastad_broadcast(c_list, n_list, self.e)
        if m is not None:
            self.log(f"[+] 明文 (int): {m}")
            decoded = _try_decode(m)
            if decoded is not None:
                self.log(f"[+] 明文 (str): {decoded}")
        else:
            self.log("[-] 广播攻击失败")
        return m

    # ----------------- 主入口 -----------------
    def solve(self):
        """按从快到慢的顺序依次尝试攻击方法"""
        # 1. 已知直接信息
        m = self._try_direct()
        if m is not None:
            return m

        # 2. dp 泄露
        m = self._try_dp_leak()
        if m is not None:
            return m

        # 3. 多组密文场景优先（在分解 n 之前）
        m = self._try_shared_factor()
        if m is not None:
            return m
        m = self._try_common_modulus()
        if m is not None:
            return m
        m = self._try_hastad()
        if m is not None:
            return m

        # 4. 小指数攻击
        m = self._try_small_e()
        if m is not None:
            return m

        # 5. factordb 查询
        m = self._try_factordb()
        if m is not None:
            return m

        # 6. Wiener (e 很大)
        m = self._try_wiener()
        if m is not None:
            return m

        # 7. Fermat 分解 (p≈q)
        m = self._try_fermat()
        if m is not None:
            return m

        # 8. Pollard p-1 (p-1 平滑)
        m = self._try_pollard_pm1()
        if m is not None:
            return m

        self.log("[!] 所有内置攻击均失败，建议：")
        self.log("    1. 上 RsaCtfTool --attack all")
        self.log("    2. 用 SageMath Coppersmith (已知明文高位 / 已知 p 高位)")
        self.log("    3. 检查是否 Boneh-Durfee (d < n^0.292)")
        self.log("    4. 看是否存在 d 泄露反推 p, q 的场景")
        return None


# ----------------------------------------------------------------------
# 命令行入口：用户可以在这里直接填参数跑，也可以 import RSASolver
# ----------------------------------------------------------------------
def main():
    # === 题目参数 (修改这里) ===
    n = 0
    e = 0
    c = 0

    # 可选：已知信息（根据题目填写，不知道就留 None）
    p = None
    q = None
    d = None
    dp = None

    # 可选：多组密文（共模 / 广播 / 共享因子）
    # extra_groups = [
    #     (c2, e2, n2),  # (c, e, n)
    # ]

    if n == 0 or e == 0 or c == 0:
        print("请先在 main() 中填入 n/e/c 等题目参数")
        print("或在脚本中 from rsa_template import RSASolver 直接调用")
        sys.exit(1)

    solver = RSASolver(n=n, e=e, c=c, p=p, q=q, d=d, dp=dp)

    # 多组密文：释放下面注释并填充
    # for c_, e_, n_ in extra_groups:
    #     solver.add_group(c_, e_, n_)

    t0 = time.time()
    m = solver.solve()
    if m is not None:
        print(f"\n[完成] 耗时: {time.time() - t0:.2f}s")
    else:
        print(f"\n[失败] 耗时: {time.time() - t0:.2f}s")


if __name__ == "__main__":
    main()

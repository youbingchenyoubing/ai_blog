#!/usr/bin/env python3
"""
RSA 常见攻击集合
- 小公钥指数攻击 (e=3)
- 共模攻击
- Fermat 分解 (p/q 接近)
- Wiener 攻击 (d 很小)
- 已知 p,q 解密

依赖: pip install gmpy2
"""

from math import gcd, isqrt


def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    g, x1, y1 = extended_gcd(b % a, a)
    return g, y1 - (b // a) * x1, x1


def modinv(a, m):
    g, x, _ = extended_gcd(a % m, m)
    if g != 1:
        raise Exception('模逆不存在')
    return x % m


def int_to_bytes(n):
    """大整数转字节串"""
    length = (n.bit_length() + 7) // 8
    return n.to_bytes(length, 'big')


# === 1. 小公钥指数攻击 (e=3, 明文m很小) ===
def small_e_attack(c, e, n):
    """当 e 很小且 m^e < n 时，c = m^e，直接开 e 次方"""
    try:
        from gmpy2 import iroot
    except ImportError:
        print("[!] 需要 gmpy2: pip install gmpy2")
        return None

    m, is_exact = iroot(c, e)
    if is_exact:
        return int(m)
    # m^e 可能在模 n 意义下未溢出，尝试 c + k*n 开方
    for k in range(1000):
        m, is_exact = iroot(c + k * n, e)
        if is_exact:
            return int(m)
    return None


# === 2. 共模攻击 ===
def common_module_attack(c1, c2, e1, e2, n):
    """同一明文用相同 n 不同 e 加密，gcd(e1,e2)=1 时可恢复"""
    g, s1, s2 = extended_gcd(e1, e2)
    if g != 1:
        print("[-] gcd(e1, e2) != 1，共模攻击不适用")
        return None
    if s1 < 0:
        c1 = modinv(c1, n)
        s1 = -s1
    if s2 < 0:
        c2 = modinv(c2, n)
        s2 = -s2
    m = (pow(c1, s1, n) * pow(c2, s2, n)) % n
    return m


# === 3. Fermat 分解 (p 和 q 接近) ===
def fermat_factor(n, max_iter=1000000):
    """当 p 和 q 接近时，Fermat 分解高效"""
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


# === 4. Wiener 攻击 (d 很小，e 很大) ===
def wiener_attack(e, n):
    """当 d < n^0.25 时，连分数展开可恢复 d"""
    def continued_fraction(e, n):
        cf = []
        while n:
            q, r = divmod(e, n)
            cf.append(q)
            e, n = n, r
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
    convs = convergents(cf)

    for k, d in convs:
        if k == 0:
            continue
        phi_times = e * d - 1
        if phi_times % k != 0:
            continue
        phi = phi_times // k
        s = n - phi + 1
        discriminant = s * s - 4 * n
        if discriminant < 0:
            continue
        sqrt_disc = isqrt(discriminant)
        if sqrt_disc * sqrt_disc == discriminant:
            p = (s + sqrt_disc) // 2
            q = (s - sqrt_disc) // 2
            if p * q == n:
                return d, p, q
    return None


# === 5. 已知 p,q 求明文 ===
def rsa_decrypt(c, p, q, e=65537):
    n = p * q
    phi = (p - 1) * (q - 1)
    d = modinv(e, phi)
    m = pow(c, d, n)
    return m


# === 6. 已知 n,e,c 从文件读取 ===
def load_params(filepath):
    """从 Python 字典文件读取参数"""
    with open(filepath) as f:
        return eval(f.read())


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("RSA 攻击脚本集合")
        print("")
        print("用法:")
        print("  python3 rsa_attacks.py small_e <c> <e> <n>")
        print("  python3 rsa_attacks.py common <c1> <c2> <e1> <e2> <n>")
        print("  python3 rsa_attacks.py fermat <n>")
        print("  python3 rsa_attacks.py wiener <e> <n>")
        print("  python3 rsa_attacks.py decrypt <c> <p> <q> [e]")
        print("")
        print("示例:")
        print("  python3 rsa_attacks.py small_e 12345 3 99999999")
        print("  python3 rsa_attacks.py fermat 99999999")
        print("  python3 rsa_attacks.py decrypt 12345 3571 2797")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == 'small_e':
        c, e, n = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
        m = small_e_attack(c, e, n)
        if m is not None:
            print(f"[+] 明文 (int): {m}")
            try:
                print(f"[+] 明文 (text): {int_to_bytes(m).decode()}")
            except:
                pass
        else:
            print("[-] 小公钥指数攻击失败")

    elif mode == 'common':
        c1, c2 = int(sys.argv[2]), int(sys.argv[3])
        e1, e2 = int(sys.argv[4]), int(sys.argv[5])
        n = int(sys.argv[6])
        m = common_module_attack(c1, c2, e1, e2, n)
        if m is not None:
            print(f"[+] 明文 (int): {m}")
            try:
                print(f"[+] 明文 (text): {int_to_bytes(m).decode()}")
            except:
                pass
        else:
            print("[-] 共模攻击失败")

    elif mode == 'fermat':
        n = int(sys.argv[2])
        p, q = fermat_factor(n)
        if p and q:
            print(f"[+] p = {p}")
            print(f"[+] q = {q}")
            print(f"[+] 验证: p*q == n: {p*q == n}")
        else:
            print("[-] Fermat 分解失败，p 和 q 可能差距较大")

    elif mode == 'wiener':
        e, n = int(sys.argv[2]), int(sys.argv[3])
        result = wiener_attack(e, n)
        if result:
            d, p, q = result
            print(f"[+] d = {d}")
            print(f"[+] p = {p}")
            print(f"[+] q = {q}")
        else:
            print("[-] Wiener 攻击失败，d 可能不够小")

    elif mode == 'decrypt':
        c = int(sys.argv[2])
        p, q = int(sys.argv[3]), int(sys.argv[4])
        e = int(sys.argv[5]) if len(sys.argv) > 5 else 65537
        m = rsa_decrypt(c, p, q, e)
        print(f"[+] 明文 (int): {m}")
        try:
            print(f"[+] 明文 (text): {int_to_bytes(m).decode()}")
        except:
            pass

    else:
        print(f"未知模式: {mode}")

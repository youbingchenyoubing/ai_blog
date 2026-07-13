# Pollard's p-1 与 Pohlig-Hellman: 一道光滑 RSA 题的完整破译

> 题目作者把 RSA 三个常见弱点打包到一个文件里:用 `getPrime(20)` 反复相乘构造 `p`,导致 `p-1` 是强 B-smooth;再把 `flag` 拆成两半,一半用标准 RSA 加密,另一半用 `pow(e, m_2, n)` 当作"底数为 e"的离散对数来加密。两个加密看似独立,其实都建立在"n 可分解"这一前提之上。本文从结构识别一路讲到 flag 还原,给出可直接运行的完整 exp。

---

## 目录

- [一、题目结构总览](#一题目结构总览)
- [二、生成器分析:为什么 p-1 是 B-smooth](#二生成器分析为什么-p-1-是-b-smooth)
- [三、第一步:Pollard's p-1 分解 n](#三第一步pollards-p-1-分解-n)
- [四、第二步:标准 RSA 解出 m_1](#四第二步标准-rsa-解出-m_1)
- [五、第三步:Pohlig-Hellman 解离散对数求 m_2](#五第三步pohlig-hellman-解离散对数求-m_2)
- [六、CRT 合并:还原 m_2 的真实值](#六crt-合并还原-m_2-的真实值)
- [七、完整 exp](#七完整-exp)
- [八、可能踩到的坑](#八可能踩到的坑)
- [九、题目作者的"陷阱思维"](#九题目作者的陷阱思维)

---

## 一、题目结构总览

题目的核心代码如下:

```python
small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]

def gen_prime(bits, lim = 7, sz = 20):
    while True:
        p = reduce(mul, [getPrime(sz) for _ in range(bits // sz)])
        for i in range(lim):
            if isPrime(p + 1):
                return p + 1
            p *= small_primes[i]

p = gen_prime(512)
q = gen_prime(512)
n = p * q
e = 0x10001

m_1 = bytes_to_long(flag[:len(flag) // 2])
m_2 = bytes_to_long(flag[len(flag) // 2:])

c_1 = pow(m_1, e, n)      # 标准 RSA
c_2 = pow(e, m_2, n)      # 底数为 e、指数为 m_2、模 n -- 离散对数
```

三个观察点:

| 观察点 | 含义 | 对应攻击 |
| --- | --- | --- |
| `getPrime(20)` ×25 个,再加上 `small_primes` 前 6 个 | `p-1` 全部由 ≤ 2²⁰ 的素数构成 | **Pollard's p-1** |
| `c_1 = pow(m_1, e, n)` | 标准 RSA | 一旦 n 分解即可直接解 |
| `c_2 = pow(e, m_2, n)` | `c_2 ≡ e^{m_2} (mod n)`,即从 `c_2` 求指数 `m_2` | **Pohlig-Hellman 离散对数** |

整道题的"破译顺序"是一个清晰的链:

```
n 可分解  ──►  p-1 光滑  ──►  Pollard p-1 得到 p, q
                                       │
                  ┌────────────────────┴───────────────────┐
                  ▼                                        ▼
        (p-1)(q-1) 已知 → RSA 解 m_1             p-1, q-1 光滑 → Pohlig-Hellman 解 m_2
                  └────────────────┬───────────────────────┘
                                   ▼
                            flag = m_1 || m_2
```

---

## 二、生成器分析:为什么 `p-1` 是 B-smooth

把 `gen_prime` 拆开看:

```
生成阶段  :
    p = ∏_{i=1..25} getPrime(20)            # 25 个 ~20 bit 的随机素数相乘
返回阶段 (最多 7 次循环) :
    for i in 0..6:
        if isPrime(p + 1): return p + 1
        p *= small_primes[i]
```

注意到循环里 `isPrime(p+1)` 检查的是 `p+1`,如果通过就返回 `p+1`,否则才把 `p` 乘以 `small_primes[i]` 再继续。也就是说,真正返回的素数 `P` 满足

```
P - 1 = (∏ 25 个 < 2²⁰ 素数) · (∏ small_primes[0..k])      (k < 6, 即乘到 13 为止)
```

或者更进一步,如果第一轮就 `isPrime(p+1)` 为真,那 `P-1` 完全是 25 个 20 位素数之积,不含额外的 `small_primes` 因子。

无论哪种情况,**`P - 1` 的所有素因子都 ≤ max(2²⁰, 17) = 2²⁰ ≈ 1,048,576`**。这意味着:

> `p - 1` 与 `q - 1` 都是 **B-smooth**,其中 `B = 2²⁰`。

Smooth 数是对 Pollard's p-1 与 Pohlig-Hellman 两种算法"开放"的钥匙。一个数越是 smooth,这两种算法越快。

---

## 三、第一步:Pollard's p-1 分解 n

### 3.1 算法原理回顾

如果 *p* 是 *n* 的素因子,且 *p-1* 是 **B-smooth**(所有素因子 ≤ B),那么:

1. 计算 `M = ∏_{pr ≤ B} pr^⌊log_{pr} B⌋`(即 `lcm(1, 2, ..., B)`)
2. 由于 `(p-1) | M`,由费马小定理 `2^M ≡ 1 (mod p)`,所以 `p | (2^M - 1)`
3. `gcd(2^M - 1, n)` 大概率就是 *p*

由上一节分析,本题 `B ≈ 2²⁰` 就足够。

### 3.2 关键实现

```python
def pollard_pm1(n, B):
    from math import gcd
    a = 2
    pr = 2
    while pr <= B:
        pp = pr
        while pp * pr <= B:
            pp *= pr
        a = pow(a, pp, n)        # 累乘到 a 上,避免一次构造超大 M
        pr = next_prime(pr)
    return gcd(a - 1, n)
```

要点:
- **不要**先构造出 `M` 再做 `pow(a, M, n)`,虽然 `M` 的值没有特别巨大(因为是 `lcm` 不是连乘),但 `pow(a, pp, n)` 用"边乘边模"方式 (`a = pow(a, pp, n)`) 比 `pow(a, M, n)` 在工程上更清晰,且等价(因为 `a^M = ((((a)^(p1^k1))^(p2^k2))...)`。
- 取 `B = 1 << 20` 即可覆盖 `getPrime(20)` 的输出。
- 若 `gcd` 等于 1,上调 B;若等于 n,说明两个因子都被同时"覆盖" 了,需下调或对中间结果提前做 `gcd`。

### 3.3 题目中的实际参数

`bits = 512, sz = 20`,所以 `bits // sz = 25`——共 25 个 20 位素数。每个都 < 2²⁰,所以:

```
B = 2²⁰ = 1,048,576
```

阶段 1 即可一次分解,无需阶段 2(阶段 2 假设"剩余单个大素数",而这题的剩余结构是 25 个并列的 20 位素数,不属于阶段 2 形态,直接靠阶段 1 在 B=2²⁰ 处全部"吃下")。

---

## 四、第二步:标准 RSA 解出 m_1

一旦拿到 `p, q`,这一步没有任何特别:

```python
phi = (p - 1) * (q - 1)
d   = inverse(e, phi)         # e = 0x10001 = 65537 与 phi 互素(否则就是另一个坑)
m_1 = pow(c_1, d, n)
flag_part_1 = long_to_bytes(m_1)
```

注意:**`getPrime(sz)` 仅保证返回素数**;`p-1` 有可能恰好被 `e=65537` 整除,但题目在生成时没刻意避开。若 `gcd(e, phi) ≠ 1`,`inverse` 会抛异常——这是这道题里少见的一个"小坑",但经验上 65537 不会整除 `p-1` 或 `q-1`(否则 `e | (p-1)` ⇒ `p ≡ 1 mod 65537`,依概率几乎不会主动走到这一支)。

---

## 五、第三步:Pohlig-Hellman 解离散对数求 m_2

### 5.1 把问题写清楚

`c_2 = pow(e, m_2, n)` 翻译成数学式:

```
c_2 ≡ e^{m_2}   (mod n)
```

这是 **离散对数问题(DLP)**:已知 `e, c_2, n`,求 `m_2`。

通用 DLP 是难的,但本题有两条捷径:

1. **`n = p·q`,所以 DLP 可拆成 mod p 与 mod q 上的两个子问题**(由中国剩余定理保证)
2. **`p-1` 与 `q-1` 都是 B-smooth**——这是核心的"加速器"

### 5.2 Pohlig-Hellman 速览

设群 `G` 的阶 `N = ∏ q_i^{e_i}`,且所有 `q_i` 都很小(或 `N` 是 smooth 的)。则 DLP 可被:

1. 拆成若干关于子群的小 DLP
2. 每个子问题在阶数为 `q_i` 的子群内,可用 BSGS(小步大步)解,复杂度 `O(√q_i)`
3. 子答案用 **CRT** 合并

复杂度从 `O(√N)` 降到 `O(Σ √q_i · e_i·log q_i)`。`p-1` 越光滑,`q_i` 越小,算法越快。

### 5.3 在本题中怎么用

1. 拆分:`c_2 ≡ e^{m_2} (mod p)`,求 `x_p ≡ m_2 (mod ord_p(e))`
   - `ord_p(e)` 表示 `e` 在 `(Z/pZ)*` 里的阶,且 `ord_p(e) | (p-1)`
2. 同理求 `x_q ≡ m_2 (mod ord_q(e))`
3. CRT 合并得到 `m_2 mod lcm(ord_p(e), ord_q(e))`

直接用 `sympy`:

```python
from sympy.ntheory.residues import discrete_log

x_p = discrete_log(p, c_2 % p, e % p)
x_q = discrete_log(q, c_2 % q, e % q)
```

`discrete_log(n, a, b)` 求出 `x` 使 `b^x ≡ a (mod n)`,内部用 Pohlig-Hellman,所以只要 `p-1`、`q-1` 因子分解不太大,瞬时就能出结果。

### 5.4 为什么要先求 `ord_p(e)`?

直接 CRT 合并 `x_p` 和 `x_q` 取模相同时只对 "模数互素" 才正确。本题里两个模数是:

- `ord_p(e)` —— `e` 在 `F_p^*` 中的阶
- `ord_q(e)` —— `e` 在 `F_q^*` 中的阶

它们通常**不互素**(都含 2 因子等),所以必须用"广义 CRT"(`crt` 函数里的 `g = gcd(m1, m2)`,先验证 `(r1 - r2) % g == 0`,再合并)。

求阶的常规做法:

```python
def element_order(g, p, prime_factors_of_pm1):
    """已知 p-1 的素因子, 求 g 在 F_p^* 里的阶."""
    order = p - 1
    for pr in prime_factors_of_pm1:
        while order % pr == 0 and pow(g, order // pr, p) == 1:
            order //= pr
    return order
```

即"从 `p-1` 出发,逐次砍掉不必要的素因子"。

---

## 六、CRT 合并:还原 `m_2` 的真实值

CRT 给出的是 `m_2 mod L`,其中 `L = lcm(ord_p(e), ord_q(e))`。

**`L` 通常远大于真正的 `m_2`**,但也不一定。`m_2 = bytes_to_long(flag[len(flag)//2:])`,长度大致是 half(flag) 个字节。如果:

```
L > m_2  ⟹  CRT 直接给出真值
L < m_2  ⟹  需要枚举 m_2 + k·L  (k = 0, 1, 2, ...) 找可打印解
```

按字节长度范围 + UTF-8/printable 检查筛出正确的那一份:`long_to_bytes` 解码后落在合理长度且可打印的就是 flag 后半段。

```python
from math import lcm
L = lcm(order_p, order_q)

m2_candidate = (x_p + order_p * ((x_q - x_p) // gcd(order_p, order_q)) * inv_cofactor) % L
# 或直接用 sympy CRT 或自己写 crt
```

---

## 七、完整 exp

下面这段脚本依赖 `pycryptodome` 与 `sympy`:

```
pip install pycryptodome sympy
```

```python
from math import gcd, lcm
from Crypto.Util.number import long_to_bytes, inverse
from sympy.ntheory.residues import discrete_log
from sympy import factorint

n = 127253273656755041488061369327088666642658775150495004366734207251894053962795751622161708537666419494472986448057578123084334734003516808810993297670864587942963094922535025747145569669008578643232131137540834194554273087372338583584899887807562752077414752047575492161255201233084800885495422227087041
c_1 = 57974701828832728577967450465255788289923655791414772437088078343474290797872710812238826926559487379480041620453016799514334887870064277070080870305537633158647391760915619606965385553888677686830658607302407071864404909932680594946855739256156855739204639535723294574774070264939278760140163103832650
c_2 = 55312120533067544987183869320534977277494480648083277810412946782179206524603471723382520688342053257844455599889227031261498427604180888592220640480807184227590167045531489390410336954305032937351566198667403155696242903124672179982018054628152426002330933819747747129472442087675331347179609346470886
e = 0x10001

# ---------- Step 1: Pollard p-1 ----------
def is_prime(x):
    if x < 2: return False
    i = 2
    while i * i <= x:
        if x % i == 0: return False
        i += 1
    return True

def next_prime(x):
    x += 1
    while not is_prime(x): x += 1
    return x

def pollard_pm1(n, B):
    a = 2
    pr = 2
    while pr <= B:
        pp = pr
        while pp * pr <= B:
            pp *= pr
        a = pow(a, pp, n)
        pr = next_prime(pr)
    d = gcd(a - 1, n)
    return d if 1 < d < n else None

print("[*] Pollard p-1 with B = 2^20 ...")
d = pollard_pm1(n, 1 << 20)
assert d, "Pollard p-1 failed"
p, q = d, n // d
assert p * q == n
print(f"p = {p}")
print(f"q = {q}")

# ---------- Step 2: 标准 RSA 解 m_1 ----------
phi = (p - 1) * (q - 1)
d_rsa = inverse(e, phi)
m_1 = pow(c_1, d_rsa, n)
flag_1 = long_to_bytes(m_1)
print(f"[*] flag part1 = {flag_1}")

# ---------- Step 3: Pohlig-Hellman 解 m_2 ----------
def element_order(g, p, factors):
    order = p - 1
    for pr in factors:
        while order % pr == 0 and pow(g, order // pr, p) == 1:
            order //= pr
    return order

fac_p = factorint(p - 1)
fac_q = factorint(q - 1)
order_p = element_order(e % p, p, list(fac_p.keys()))
order_q = element_order(e % q, q, list(fac_q.keys()))
print(f"ord_p(e) = {order_p}")
print(f"ord_q(e) = {order_q}")

# sympy 直接给最小非负解
x_p = discrete_log(p, c_2 % p, e % p)
x_q = discrete_log(q, c_2 % q, e % q)

# ---------- CRT 合并 (广义) ----------
def ext_gcd(a, b):
    if b == 0: return a, 1, 0
    g, x1, y1 = ext_gcd(b, a % b)
    return g, y1, x1 - (a // b) * y1

def crt(r1, m1, r2, m2):
    g = gcd(m1, m2)
    if (r1 - r2) % g != 0: return None, None
    L = lcm(m1, m2)
    _, u, _ = ext_gcd(m1 // g, m2 // g)
    r = r1 + m1 * (((r2 - r1) // g) * u)
    return r % L, L

m2_mod, L = crt(x_p, order_p, x_q, order_q)
print(f"m_2 mod {L} = {m2_mod}")

# ---------- 在合理字节长度内枚举 ----------
half = len(flag_1)
upper = 1 << (8 * (half + 2))
flag_2 = None
k = 0
while True:
    cand = m2_mod + k * L
    if cand > upper: break
    bb = long_to_bytes(cand)
    if half - 2 <= len(bb) <= half + 2:
        try:
            bb.decode("utf-8")
            flag_2 = bb
            break
        except UnicodeDecodeError:
            pass
    k += 1

if flag_2:
    print(f"[+] flag part2 = {flag_2}")
    print(f"\nFLAG = {(flag_1 + flag_2).decode()}")
else:
    print("[!] no printable candidate in range, raw value may not be flag-end directly")
    print(f"    raw bytes = {long_to_bytes(m2_mod)}")
```

---

## 八、可能踩到的坑

| 坑 | 表现 | 规避 |
| --- | --- | --- |
| **`gcd(e, p-1) ≠ 1`** | `inverse(e, phi)` 抛异常或 DLP 在该子群内有多个解 | 题目里 `e=65537` 是素数,要 `p-1` 含 65537 才会出问题。如真发生,需要在 DLP 端做"根号分支"枚举。本题几乎不会出现 |
| **`gcd(a-1, n) == 1`** | Pollard p-1 阶段 1 没找到因子 | 调大 B(例如 `1<<22`)再试,或在中途每个素数步临时取一次 `gcd(a-1, n)`,一旦非平凡就提前返回 |
| **`gcd(a-1, n) == n`** | 两个因子同时被平滑上界覆盖 | 缩小 B,或使用"提前 gcd"策略:每乘一个 `pp` 就检测一次 `gcd(a-1, n)` |
| **`discrete_log` 跑得慢** | sympy 内部对 `p-1` 因式分解 | 直接传入 `order=` 参数(实际上 sympy 1.10+ 会自动处理,但显式给 `p-1` 因子分解可以加快)|
| **CRT 给出的 `L` 反而 > 真实 `m_2`**,但仍想确认 | 直接拿 `m2_mod` 解码就是答案 | 先试 `long_to_bytes(m2_mod)`;若字节长度对、可解码就完事,不必枚举 k |
| **`flag` 两半长度不等** | `len(flag)//2` 是地板除,奇数长时 part2 比 part1 长 1 字节 | 枚举时把"长度上限"放宽到 `half+1` 而不是 `half` |

---

## 九、题目作者的"陷阱思维"

这道题妙就妙在它把三件事串成一条线:

1. **作者给了你"看起来"安全的 512+512 位 `n`** —— 一般 RSA-1024 应该没法分。
2. **但是 `gen_prime` 故意构造 smooth 的 `p-1`** ——第一阶段攻击成立的钥匙。
3. **而 `flag` 又被切两半,前后用了两种不同的密码学问题**(模幂 / 离散对数),让选手以为需要两套独立工具。

事实上 **两个问题共享同一个"前置条件"`n 可分解`**,一旦 Pollard p-1 出手,后半段几乎免费。

把握这种"同因异果"的结构,是 CTF Crypto 比赛中"一题多知识点"题目的常见模式:作者想考察的不是你会不会某一种攻击,而是你能不能看出 **多个看似不同的攻击共享同一个易受条件**。下次遇到 `pow(base, secret_exp, n)` 形式的"奇怪"加密,先问自己——**`n` 是否可被分解?分解后 `p-1`、`q-1` 是否 smooth?**

这两问一旦答"是",后续几乎都是机械步骤。

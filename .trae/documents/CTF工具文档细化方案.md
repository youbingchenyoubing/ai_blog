# CTF 工具集锦文档细化方案

## Context（背景）

`cyber_security/CTF工具集锦与脚本.md` 当前工具清单表格只有"一句话用法"列，过于简略（如 `sqlmap -u URL --dbs`），使用者无法判断何时选用哪个工具；同时存在多组功能相似的工具（如 dirsearch vs gobuster、IDA vs Ghidra、ROPgadget vs ropper、hashcat vs John）未给出推荐；部分功能极丰富的工具（Wireshark、IDA、SQLMap、pwntools）挤在主文档里无法展开。

本方案目标：
1. 主文档工具清单表格"一句话用法"细化为"关键用法"（2-3 条核心命令/操作）
2. 对功能相似的工具，用 ★ 标注推荐，并在表后加"工具选用建议"段落说明选用逻辑
3. 为 4 个功能最丰富的工具生成独立指南文件（参照已有的 `Burp Suite实战使用指南.md` 模板），主文档以链接引用

## 产出文件

### 新建 4 个独立工具指南（位于 cyber_security/）

均参照 `cyber_security/Burp Suite实战使用指南.md` 的结构：引言 → 目录 → 安装配置 → 核心工作流 → 各功能详解（配可复现步骤与代码） → 实战技巧 → 速查表。

1. `cyber_security/Wireshark实战使用指南.md`
   - 捕获过滤器 vs 显示过滤器语法
   - 协议分析（HTTP / DNS / TCP / TLS）
   - TCP/HTTP 流追踪与文件还原
   - USB 流量（键鼠数据提取）
   - tshark 命令行批量提取
   - 速查表：常用过滤器、tshark 命令

2. `cyber_security/IDA_Pro实战使用指南.md`
   - 反编译（F5）、交叉引用（X）、导航（G/N）
   - IDAPython 脚本、常用插件
   - 调试器使用
   - 与 Ghidra 对比与选用建议（开源替代方案）
   - 速查表：快捷键、常用脚本

3. `cyber_security/SQLMap实战使用指南.md`
   - 注入检测与等级（--level/--risk）
   - 爆库→爆表→爆字段→爆数据完整流程
   - POST / Cookie / Header 注入
   - tamper 绕过 WAF（常用脚本表）
   - OS Shell / 文件读写 / udf 提权
   - 速查表：常用参数、tamper 脚本

4. `cyber_security/pwntools实战使用指南.md`
   - 连接管理（process/remote）、context 配置
   - IO 交互（send/recv/sendlineafter）
   - ELF 文件操作（symbols/got/plt/search）
   - payload 打包（p32/p64/u64）
   - ROP 链构造、fmtstr_payload
   - shellcraft 与 asm
   - GDB 调试 attach
   - 速查表：API、模板

### 修改主文档 `cyber_security/CTF工具集锦与脚本.md`

对 5 个方向的工具清单表格统一改造（Web/Misc/Crypto/Reverse/PWN）：

1. 表头列：`工具 | 用途 | 关键用法 | GitHub 地址`（"一句话用法"→"关键用法"）
   - 关键用法列写入 2-3 条核心命令或操作步骤（用 `<br>` 换行分隔）
2. 推荐工具在工具名前加 `★` 标记
3. 复杂工具在"关键用法"列末尾加 `→ 详见 [指南名](指南路径)`
4. 每个表格后新增 `### X.X 工具选用建议` 子章节，覆盖该方向所有相似工具组：

   - **Web**：目录扫描（dirsearch★/gobuster）、HTTP 请求（curl★/Postman）、抓包（Burp★→已有指南）、SQL 注入（SQLMap★→新指南）、WebShell（AntSword★）、爆破（hydra）
   - **Misc**：文件提取（binwalk★/foremost）、PNG 隐写（zsteg★/StegSolve）、流量分析（Wireshark★→新指南/tshark）、ZIP 破解（fcrackzip/John）、编解码（CyberChef★）
   - **Crypto**：大数分解（factordb★在线/RsaCtfTool/yafu）、哈希破解（hashcat★GPU/John CPU）、RSA 攻击（RsaCtfTool★）、数论（SageMath）、编解码（CyberChef★/CaptfEncoder）
   - **Reverse**：静态逆向（IDA★→新指南/Ghidra）、动态调试（x64dbg Win/GDB+pwndbg★Linux）、ROP 查找（ROPgadget★/ropper）、符号执行（angr）、约束求解（z3）、Android（jadx★/apktool/dex2jar）
   - **PWN**：框架（pwntools★→新指南）、ROP 查找（ROPgadget★/ropper）、gadget（one_gadget）、沙箱（seccomp-tools）、libc 查询（libc-database/libc.rip）

5. 主文档中已有的简短命令速查段（如 1.3 SQLMap 速查、2.5 流量分析、3.4 哈希破解、4.4 GDB 命令）保留，但在开头加一行指引："完整参数与进阶用法见 [独立指南](路径)"

### 更新 `09_项目纪要.md`

任务完成后追加一条纪要，记录本次细化工作。

## 执行顺序

1. 创建 4 个独立工具指南文件（并行可行，但需逐一保证质量）
2. 改造主文档 5 个方向的工具清单表格 + 选用建议段落
3. 在主文档相关速查段加入独立指南链接指引
4. 更新 09_项目纪要.md

## 验证方式

- 检查 4 个新指南文件章节完整、代码块语法正确、无占位空段
- 检查主文档 5 个表格表头统一为"关键用法"、推荐工具带★、相似工具组均有选用建议
- 检查主文档到 4 个新指南的链接路径正确（相对路径）
- 通读主文档确认无重复内容（独立指南展开的细节在主文档只保留速查+链接）

## 不做的事

- 不删除主文档现有的实战脚本代码段（SQL 注入脚本、RSA 攻击脚本、pwntools 模板等保留）
- 不动 `ctf_scripts/` 下既有脚本
- 不为 hashcat / SageMath / angr / GDB 单独建文件（在主文档速查段足够，必要时表后选用建议中说明）

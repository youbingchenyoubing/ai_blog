# OpenSpec 规范驱动开发完整指南

> 当 AI 写代码越来越快，你却发现越来越难控制它写了什么——这篇指南帮你从"随性编码"走向"规范驱动"。

你一定经历过这样的场景：让 AI 帮你写一个功能，它三分钟就交出了代码，你一看——功能是有了，但命名风格和项目完全不一致，还顺手重构了你没要求改的模块，甚至悄悄引入了一个你根本不需要的依赖。你改回来，它又偏出去。来回拉扯，比手写还累。这就是典型的"vibe coding"困境：AI 写代码没有规范约束，需求理解漂移，返工不断。OpenSpec 正是为了解决这个痛点而生。

## 一、OpenSpec 是什么

OpenSpec 是由 Fission-AI 开源的规范驱动开发（Spec-Driven Development，SDD）框架，目前在 GitHub 上已获得 23.7k+ Star。它的核心理念可以用一句话概括：**先定规矩，再写代码**（Agree before you build）。

传统开发中，我们习惯直接让 AI 开工——"帮我写个用户登录功能"，然后祈祷它理解正确。但 AI 的理解往往和你心里想的有偏差，而偏差在代码层面会被指数级放大。OpenSpec 的做法是：在写代码之前，先让 AI 和你达成共识——把需求变成结构化的规范文档，确认无误后再动手。

| 维度 | 传统 Vibe Coding | OpenSpec 规范驱动 |
|------|------------------|-------------------|
| 需求传递 | 自然语言一句话 | 结构化规范文档 |
| 确认时机 | 写完代码再检查 | 写代码前先确认规范 |
| 变更管理 | 无，AI 随意修改 | changes/ 目录隔离变更 |
| 返工率 | 高，反复拉扯 | 低，一次到位 |

关键在于：**在写代码之前，先让 AI 和你达成共识**。这不是多此一举，而是把"返工"的成本前置为"确认"的成本——后者要便宜得多。

## 二、核心设计：specs/ 与 changes/ 分离

OpenSpec 最精妙的设计在于目录结构的分离。初始化后，项目根目录下会出现 `openspec/` 文件夹，内部结构如下：

```
openspec/
├── specs/          # 已确认的规范（类似 Git 的 main 分支）
│   ├── proposal.md
│   ├── design.md
│   ├── spec.md
│   └── tasks.md
└── changes/        # 正在进行的变更（类似 Git 的 feature 分支）
    └── feature-login/
        ├── proposal.md
        ├── design.md
        ├── spec.md
        └── tasks.md
```

打个比方：`specs/` 就像 Git 的 main 分支，存放的是经过确认、当前生效的规范；`changes/` 就像 feature 分支，每个新功能或修改都在独立的子目录中起草，确认后才合并回 `specs/`。

这个分离至关重要。当 AI 修改某个功能时，它只会操作 `changes/` 下的对应目录，不会触碰 `specs/` 中已有的其他规范。这就像 Git 的分支隔离——你在 feature 分支上折腾，不会影响 main 分支的稳定性。没有这种隔离，AI 在修改 A 功能时可能悄悄改掉 B 功能的规范，而你浑然不知。

## 三、安装与初始化

安装 OpenSpec 非常简单，一条命令搞定：

```bash
npm install -g @fission-ai/openspec@latest
```

安装完成后验证版本：

```bash
openspec --version
```

进入你的项目目录并初始化：

```bash
cd your-project
openspec init
```

初始化过程中，OpenSpec 会让你选择当前使用的 AI 编码工具。它支持 20+ 主流工具，包括 Cursor、Windsurf、Claude Code、GitHub Copilot 等，确保生成的规范能被你的工具正确读取。

> 💡 Windows PowerShell 用户注意：如果遇到执行策略限制，先运行 `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`，再执行 init 命令。

## 四、OPSX 核心工作流

OpenSpec 的核心工作流由四个命令组成，简称 EPSA 循环：

| 命令 | 作用 | 何时使用 |
|------|------|----------|
| `/opsx:explore` | 探索需求，理解上下文 | 开始新功能前，先让 AI 理解项目现状 |
| `/opsx:propose` | 提出变更方案，生成 proposal | 需求明确后，让 AI 起草变更提案 |
| `/opsx:apply` | 应用变更，将 changes/ 合并到 specs/ | 方案确认无误，正式写入规范 |
| `/opsx:archive` | 归档已完成的变更 | 功能开发完毕，清理 changes/ 目录 |

完整的工作流是一条清晰的链路：

```
explore（探索） → propose（提案） → apply（应用） → archive（归档）
```

如果你需要更严格的流程控制，可以切换到自定义配置文件，解锁扩展命令：

```bash
openspec config profile custom
openspec update
```

自定义配置下会额外提供 `verify`（一致性校验）、`sync`（规范同步）、`continue`（继续上次中断的流程）三个命令，适合对质量要求更高的团队。

## 五、与 Superpowers 协同：三段式流程

Superpowers 是另一个工程化工作流框架（GitHub 115k+ Star），它的核心理念是"不信任 AI 的自发性"——强制 AI 遵循最佳实践，包括 TDD、代码审查、工作区隔离等。OpenSpec 和 Superpowers 不是竞争关系，而是互补：OpenSpec 管"做什么"，Superpowers 管"怎么做"。

两者协同形成三段式流程：

**第一阶段：Superpowers 探索性规划**

用 Superpowers 的 brainstorm 能力进行需求探索、方案讨论、设计草稿。这个阶段允许自由发散，不急于定型。

**第二阶段：OpenSpec 锁定规范**

当设计方向明确后，切换到 OpenSpec 流程：propose → design → spec → tasks。把模糊的想法变成精确的规范文档，经人工确认后锁定。

**第三阶段：Superpowers 执行编码 → OpenSpec 归档**

规范锁定后，回到 Superpowers 执行：TDD 编码、测试、验证。全部通过后，用 OpenSpec 的 archive 命令归档变更。

三道关卡贯穿始终：

| 关卡 | 规则 | 意义 |
|------|------|------|
| 设计未确认 | 不进入 OpenSpec 流程 | 避免把模糊需求固化成规范 |
| 规范未完成 | 不开始编码 | 避免基于不确定的规范写代码 |
| 无真实测试验证 | 不算完成 | TDD 强制执行 RED-GREEN-REFACTOR 循环 |

Superpowers 对 TDD 的执行极其严格：没有测试的代码直接删除，不允许先写实现再补测试。这和 OpenSpec 的"先规范后代码"理念一脉相承——都是把验证前置。

## 六、任务粒度控制：2/8 法则

OpenSpec 生成的 `tasks.md` 是 AI 执行的指令清单。但这里有个常见陷阱：任务粒度太粗，AI 就会在细节处"夹带私货"——用自己偏好的方式填充你没想到的部分。

| 对比维度 | 粗粒度任务 | 细粒度任务 |
|----------|-----------|-----------|
| 典型写法 | "实现用户登录接口" | "在 auth.ts 中创建 login 函数，接收 email 和 password，调用 bcrypt.compare 验证，成功返回 JWT，失败抛出 AuthError" |
| AI 自由度 | 高，自行决定实现细节 | 低，按指令精确执行 |
| 夹带私货风险 | 高 | 低 |
| 返工概率 | 高 | 低 |

2/8 法则的核心洞察：**花 20% 的精力升级 tasks 指令，就能获得 80% 的质量提升**。具体操作分三步：

**第一步：创建 config.yaml**

```yaml
context:
  - "本项目使用 FastAPI + SQLAlchemy"
  - "所有 API 必须包含错误处理中间件"
rules:
  - id: review
    description: "设计完成后必须经过人工审查"
```

**第二步：Fork schema，升级 tasks instruction**

每个步骤花 2-5 分钟，附上完整的代码示例、命令和预期输出。不要只写"添加路由"，要写"在 `routes/user.py` 中添加 `POST /api/users` 路由，请求体 schema 如下……"。

**第三步：插入 review artifact**

在 design 和 tasks 之间插入审查环节，作为设计到任务转换的关卡。

这三步构成三层防线：

| 防线 | 机制 | 贡献度 |
|------|------|--------|
| 源头控制 | 升级 tasks instruction | 80% 质量 |
| 过程检查 | review + verify 环节 | 安全网 |
| 最终确认 | 归档前人工检查 | 兜底保障 |

日常工作的六阶段流程：explore → propose → 人工检查 → apply → verify → archive。其中"人工检查"不可省略——它是你把控质量的关键节点。

## 七、三层架构：规范→纪律→协作

OpenSpec 并非孤立存在，它与 Superpowers、Harness/OMO 构成完整的三层架构：

| 层级 | 工具 | 职责 | 类比 |
|------|------|------|------|
| 规范层 | OpenSpec | 定义"做什么" | 建筑蓝图 |
| 纪律层 | Superpowers | 定义"怎么做" | 施工标准 |
| 协作层 | Harness/OMO | 定义"谁来做、怎么协同" | 项目经理 |

三层的协作链条：OpenSpec 产出规范文档 → Superpowers 按规范执行开发（TDD、审查、验证）→ Harness/OMO 协调多个 Agent 的分工与权限。

缺失任何一层都会出问题：

- 没有 OpenSpec：各 Agent 各自为政，对需求理解不一致，做出来的东西对不上
- 没有 Superpowers：Agent 走捷径，跳过测试、跳过审查，代码质量失控
- 没有 Harness：Agent 协作混乱，权限冲突，互相覆盖代码

核心洞察：**规范不变、流程不变、团队可弹性扩展**。规范层稳定了需求基线，纪律层保证了执行质量，协作层让团队规模可以灵活伸缩——一个人用 OpenSpec + Superpowers 就够，多人协作再加 Harness。

## 八、场景选择指南

不是所有场景都需要全套工具。根据项目复杂度和团队规模，选择合适的组合：

| 场景 | 推荐工具组合 | 理由 |
|------|-------------|------|
| 快速原型验证 | OMO | 只需快速出活，不需要规范约束 |
| 核心业务代码 | Superpowers | 需要质量保障，但需求明确无需规范管理 |
| 团队协作 + 文档沉淀 | OpenSpec | 规范即文档，保证团队认知一致 |
| 生产级项目 | OpenSpec + Superpowers + Harness | 全链路质量保障 |
| 简单 Bug 修复 | 原生 AI 编码工具 | 杀鸡不用牛刀 |

推荐的采纳顺序：

1. **先上 OpenSpec**——建立规范意识，让 AI 的输出可预期
2. **再学 Superpowers 核心技能**——TDD、审查流程，提升代码质量
3. **最后引入 Harness/Agent Team**——多 Agent 协作，扩展团队产能

不要一上来就全套上马。工具的学习成本叠加，容易导致团队抵触。循序渐进，每一步都感受到价值，自然就会走向完整的三层架构。

## 九、常见问题与避坑

**Q1：输入 `/opsx:verify` 提示命令不存在？**

需要先切换到自定义配置文件：`openspec config profile custom`，然后运行 `openspec update`。默认的 default 配置只包含四个核心命令。

**Q2：tasks.md 和实际代码不一致，正常吗？**

正常。tasks.md 是 Plan Agent 的初始规划，Execute Agent 在执行过程中会根据实际情况动态调整。只要最终结果符合 spec.md 的要求即可，tasks.md 不是必须逐条执行的死命令。

**Q3：三个工具必须全用吗？**

不必。根据场景选择，参考第八节的指南。简单项目用 OpenSpec 就够了。

**常见坑点：**

| 坑点 | 说明 | 解决方案 |
|------|------|----------|
| rules 的 key 与 artifact id 不匹配 | config.yaml 中的 rules key 必须和对应的 artifact id 完全一致，否则规则不生效 | 仔细核对命名，建议复制粘贴 |
| verify 只做文本一致性检查 | verify 比对的是规范文档之间的一致性，不是运行时验证 | 运行时验证交给 Superpowers 的测试流程 |
| review 是自我审查，容易放水 | AI 审查自己的输出，倾向于"看起来没问题" | 关键变更必须人工审查，不要完全依赖 AI review |
| 一次性加载所有 Superpowers 技能 | 技能太多会撑爆上下文窗口，AI 反而表现更差 | 按需加载，只启用当前任务需要的技能 |

---

| 工具 | 核心职责 | 一句话总结 | 必用场景 |
|------|----------|-----------|----------|
| OpenSpec | 规范管理 | 先定规矩，再写代码 | 需求复杂、多人协作 |
| Superpowers | 执行纪律 | 不信任 AI 的自发性 | 核心业务代码、TDD 要求 |
| Harness/OMO | 协作编排 | 让多个 Agent 各司其职 | 多 Agent 并行开发 |

不是工具越多越好，而是知道什么时候用什么。OpenSpec 给你的是一种思维方式：在 AI 替你写代码之前，先替 AI 写好规范。这个顺序的翻转，就是从 vibe coding 到工程化开发的分水岭。

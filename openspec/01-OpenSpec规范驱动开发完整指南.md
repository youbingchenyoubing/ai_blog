# OpenSpec 规范驱动开发完整指南

> 当 AI 写代码越来越快，你却发现越来越难控制它写了什么——这篇指南帮你从"随性编码"走向"规范驱动"。

你一定经历过这样的场景：让 AI 帮你写一个功能，它三分钟就交出了代码，你一看——功能是有了，但命名风格和项目完全不一致，还顺手重构了你没要求改的模块，甚至悄悄引入了一个你根本不需要的依赖。你改回来，它又偏出去。来回拉扯，比手写还累。

这就是典型的"vibe coding"困境：AI 写代码没有规范约束，需求理解漂移，返工不断。更致命的是，当你让 AI 改核心业务逻辑时，你根本不敢让它直接动——因为一旦改偏，排查成本远超手写。

OpenSpec 正是为了解决这个痛点而生。而它和 Superpowers、Harness/OMO 的组合，标志着 AI 编程从早期的"炼丹术"正式迈入了"工程学"阶段。

## 一、OpenSpec 是什么

OpenSpec 是由 Fission-AI 开源的规范驱动开发（Spec-Driven Development，SDD）框架，目前在 GitHub 上已获得 23.7k+ Star。它的核心理念可以用一句话概括： 先定规矩，再写代码 （Agree before you build）。

传统开发中，我们习惯直接让 AI 开工——"帮我写个用户登录功能"，然后祈祷它理解正确。但 AI 的理解往往和你心里想的有偏差，而偏差在代码层面会被指数级放大。OpenSpec 的做法是：在写代码之前，先让 AI 和你达成共识——把需求变成结构化的规范文档，确认无误后再动手。

| 维度 | 传统 Vibe Coding | OpenSpec 规范驱动 |
|------|------------------|-------------------|
| 需求传递 | 自然语言一句话 | 结构化规范文档 |
| 确认时机 | 写完代码再检查 | 写代码前先确认规范 |
| 变更管理 | 无，AI 随意修改 | changes/ 目录隔离变更 |
| 返工率 | 高，反复拉扯 | 低，一次到位 |

关键在于： 在写代码之前，先让 AI 和你达成共识 。这不是多此一举，而是把"返工"的成本前置为"确认"的成本——后者要便宜得多。

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

## 五、Superpowers 深度解析：让 AI 守规矩的执行纪律层

### 5.1 Superpowers 是什么

Superpowers 是由 Jesse Vincent（obra）创建的工程化工作流框架（GitHub 200k+ Star，MIT 协议），它的核心理念只有一句话： 不信任 AI 的自发性 。

你一定遇到过：让 AI 写个功能，它跳过设计直接写代码，跳过测试直接声明完成，甚至悄悄改了不相关的模块。Superpowers 就是为了治这个病——它通过 14 个可组合的 Skill（技能文件），强制 AI 在写任何代码之前，先走完"头脑风暴 → 设计文档 → 任务规划 → TDD → 代码审查"这套标准流程。

没有 Superpowers 的 AI 像一个热情但没纪律的实习生——干活快，但经常跑偏。装上 Superpowers 后，它变成了一个遵循 ISO 9001 质量体系的自动化工厂。

### 5.2 安装与配置

```bash
# 方式一：通过 Claude Code Plugin Marketplace 安装（推荐）
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace

# 方式二：通过 npx skills 工具安装
npm install -g @vercel-labs/skills
npx skills add obra/superpowers

# 方式三：手动安装
git clone https://github.com/obra/superpowers.git ~/.claude/superpowers
ln -s ~/.claude/superpowers/skills ~/.claude/skills/superpowers
```

安装后重启 AI 代理，Superpowers 的主技能（using-superpowers SKILL.md）会自动注入到每个会话中。它的规则极其强硬：

> *"IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT. This is not negotiable."*

这意味着 AI 不能"跳过"任何适用的技能——它必须先思考，再动手。

### 5.3 核心 Skill 详解

Superpowers 的 14 个 Skill 不是全都要加载。根据任务复杂度，按需选择：

| Skill | 触发时机 | 核心规则 | 你需要它的场景 |
|-------|---------|---------|--------------|
| brainstorming | 检测到"我要做 X" | 苏格拉底式提问，不提问不设计 | 需求不明确时，强迫 AI 先问清楚 |
| using-git-worktrees| 设计确认后，准备编码 | 每个变更独立 worktree，主分支不动 | 防止 AI 直接在 main 上乱改 |
| writing-plans| 开始实现前 | 拆分为 2-5 分钟小任务，每个任务含文件路径+完整代码+验证步骤 | 防止 AI 一步完成整个功能，夹带私货 |
| subagent-driven-dev  | 执行任务时 | 每个子任务启动独立子代理，上下文隔离 | 大型任务并行执行，避免上下文漂移 |
|  test-driven-development  | 写任何实现代码前 |  先写失败测试 → 看它失败 → 写最小实现 → 看它通过 → 重构  | 核心纪律，没有测试的代码直接删除 |
|  requesting-code-review  | 任务完成后 | 两阶段审查：先审 Spec 合规，再审代码质量 | 防止 AI 自己审查自己，容易放水 |
|  verification-before-completion  | 声明完成前 | 必须提供证据（测试通过、lint 通过、构建通过） | 防止 AI 说"做完了"但其实没验证 |

 Skill 选择策略（重要） ：不要全量加载 14 个 Skill！全量加载会消耗 ~50K tokens，撑爆上下文窗口，AI 反而表现更差。推荐组合：

| 组合 | 包含 Skill | Token 消耗 | 适用场景 |
|------|-----------|-----------|---------|
| 最小集（3 个） | TDD、verification、writing-plans | ~8K | 小改动、Bug 修复 |
| 推荐集（5 个） | TDD、verification、writing-plans、code-review、brainstorming | ~15K | 日常功能开发 |
| 完整集（7 个） | 推荐集 + git-worktrees、subagent-dev | ~22K | 大型重构、多模块任务 |

### 5.4 TDD 铁律：RED → GREEN → REFACTOR

Superpowers 最核心的价值就是强制 TDD。它不是"建议你写测试"，而是"不写测试就不让你写代码"。具体流程：

 RED 阶段 ：先写一个一定会失败的测试

```javascript
// auth.test.js
describe('AuthService', () => {
  it('should register user with valid email and password', async () => {
    const user = await authService.register('test@example.com', 'password123');
    expect(user.email).toBe('test@example.com');
    expect(user.password).not.toBe('password123'); // 必须加密
  });
});
// ❌ 运行测试：失败（因为 authService 还不存在）
```

 GREEN 阶段 ：写最小的代码让测试通过

```javascript
// AuthService.js
class AuthService {
  async register(email, password) {
    const password_hash = await bcrypt.hash(password, 10);
    return User.create({ email, password_hash });
  }
}
// ✅ 运行测试：通过
```

 REFACTOR 阶段 ：在不改变行为的前提下优化代码

```javascript
// 添加输入验证、错误处理、日志记录
// ✅ 运行测试：仍然通过
```

如果 AI 试图在 RED 之前写实现代码，Superpowers 会直接拦截并删除，强制回到 TDD 流程。这条铁律不可绕过。

### 5.5 两阶段代码审查

Superpowers 的代码审查不是走过场，而是分两个独立阶段：

 第一阶段：Spec 合规审查 ——只看"是否满足规范"

```
✅ 需求1：邮箱格式验证 — 已实现，测试覆盖
✅ 需求2：密码强度要求 — 已实现，测试覆盖
❌ 需求3：Token 刷新机制 — 未实现
审查结果：⚠️ DONE_WITH_CONCERNS
```

 第二阶段：代码质量审查 ——只看"代码写得好不好"

```
✅ 代码规范：符合 ESLint
✅ 安全性：密码已加密，SQL 注入已防护
⚠️ 测试覆盖率：92%（目标 ≥80%，通过）
审查结果：✅ APPROVED
```

两阶段分离的意义：Spec 审查和代码质量审查标准不同，混在一起会导致"一个说满足规格就行，另一个说结构不行要重构"，推进停滞。

### 5.6 与 OpenSpec 的协同：三段式流程

OpenSpec 管"做什么"（规范层），Superpowers 管"怎么做"（纪律层）。两者不是简单叠加，而是形成严格的接力关系：

 第一阶段：Superpowers 探索性规划 

用 Superpowers 的 brainstorm 能力进行需求探索、方案讨论、设计草稿。这个阶段允许自由发散，不急于定型。AI 会主动提问："你要邮箱登录还是手机号登录？""需要第三方登录吗？""密码强度有什么要求？"

 第二阶段：OpenSpec 锁定规范 

当设计方向明确后，切换到 OpenSpec 流程：`/opsx:propose` → proposal → design → spec → tasks。把模糊的想法变成精确的规范文档，经人工确认后锁定。这一步的关键是把 brainstorm 的结论"冻结"成契约——AI 后续必须按此执行。

 第三阶段：Superpowers 执行编码 → OpenSpec 归档 

规范锁定后，回到 Superpowers 执行：TDD 编码、测试、两阶段审查。全部通过后，用 OpenSpec 的 `/opsx:archive` 归档变更。

三道关卡贯穿始终：

| 关卡 | 规则 | 意义 |
|------|------|------|
| 设计未确认 | 不进入 OpenSpec 流程 | 避免把模糊需求固化成规范 |
| 规范未完成 | 不开始编码 | 避免基于不确定的规范写代码 |
| 无真实测试验证 | 不算完成 | TDD 强制执行 RED-GREEN-REFACTOR 循环 |

 为什么必须合体？  单独用 OpenSpec：你有了蓝图（WHAT），但施工队（AI）依然可能偷工减料，不知道怎么盖（HOW）。单独用 Superpowers：施工很细，但没有蓝图管控，干完活发现不是业主要的。OpenSpec 管"What"，Superpowers 管"How"，缺一不可。

## 六、任务粒度控制：2/8 法则

OpenSpec 生成的 `tasks.md` 是 AI 执行的指令清单。但这里有个常见陷阱：任务粒度太粗，AI 就会在细节处"夹带私货"——用自己偏好的方式填充你没想到的部分。

| 对比维度 | 粗粒度任务 | 细粒度任务 |
|----------|-----------|-----------|
| 典型写法 | "实现用户登录接口" | "在 auth.ts 中创建 login 函数，接收 email 和 password，调用 bcrypt.compare 验证，成功返回 JWT，失败抛出 AuthError" |
| AI 自由度 | 高，自行决定实现细节 | 低，按指令精确执行 |
| 夹带私货风险 | 高 | 低 |
| 返工概率 | 高 | 低 |

2/8 法则的核心洞察： 花 20% 的精力升级 tasks 指令，就能获得 80% 的质量提升 。具体操作分三步：

 第一步：创建 config.yaml 

```yaml
context:
  - "本项目使用 FastAPI + SQLAlchemy"
  - "所有 API 必须包含错误处理中间件"
rules:
  - id: review
    description: "设计完成后必须经过人工审查"
```

 第二步：Fork schema，升级 tasks instruction 

每个步骤花 2-5 分钟，附上完整的代码示例、命令和预期输出。不要只写"添加路由"，要写"在 `routes/user.py` 中添加 `POST /api/users` 路由，请求体 schema 如下……"。

 第三步：插入 review artifact 

在 design 和 tasks 之间插入审查环节，作为设计到任务转换的关卡。

这三步构成三层防线：

| 防线 | 机制 | 贡献度 |
|------|------|--------|
| 源头控制 | 升级 tasks instruction | 80% 质量 |
| 过程检查 | review + verify 环节 | 安全网 |
| 最终确认 | 归档前人工检查 | 兜底保障 |

日常工作的六阶段流程：explore → propose → 人工检查 → apply → verify → archive。其中"人工检查"不可省略——它是你把控质量的关键节点。

## 七、Harness/OMO 深度解析：多 Agent 协作的编排层

### 7.1 为什么需要编排层

OpenSpec 解决了"做什么"，Superpowers 解决了"怎么做"。但当项目大到需要多个 Agent 同时工作时，新问题出现了：

-  前端 Agent 和后端 Agent 同时改 API 接口 ，一个改了字段名，另一个不知道，合并就炸了
-  三个 Agent 各自理解需求 ，对同一个"用户认证"的实现完全不同
-  Agent 之间互相覆盖代码 ，A 刚写完，B 又改回去了

这就是 Harness/OMO 存在的意义——它定义"谁来做、怎么协同"。

### 7.2 OMO (Oh My OpenAgent) 是什么

OMO（原名 oh-my-opencode）是一个开源的多模型 Agent 编排框架（GitHub 48k+ Star），它的核心能力是 把单个 AI 编码代理变成一个协调的虚拟开发团队 。

OMO 的架构分三层：

```
规划层 (Prometheus/Metis)    → 理解需求，拆解任务
编排层 (Atlas)               → 分配任务，协调执行
执行层 (Sisyphus-Junior 等)  → 各司其职，并行干活
```

它内置了 10+ 专业化 Agent，每个 Agent 有明确的角色和偏好的模型：

| Agent | 角色 | 典型模型选择 | 职责 |
|-------|------|-------------|------|
| Prometheus | 规划师 | Claude Opus 4.6 | 需求拆解、方案设计 |
| Atlas | 编排者 | Claude Sonnet 4 | 任务分配、进度协调 |
| Sisyphus-Junior | 执行者 | Claude Sonnet 4 | 逐任务实现代码 |
| Oracle | 架构师 | Claude Opus 4.6 | 架构评审、技术决策 |
| Frontend | 前端工程师 | Gemini Flash | UI 组件、样式实现 |
| Librarian | 文档专家 | Gemini Flash | 文档查找、OSS 研究 |
| Momus | 审查员 | Claude Opus 4.6 | 代码质量审查 |

关键创新： 多模型路由 。不是所有任务都用最贵的模型——规划用 Opus（深度推理），前端用 Gemini Flash（快速生成），审查再用 Opus（精准判断）。实测成本可比单一模型降低 30-50%。

### 7.3 OpenHarness 是什么

OpenHarness 是 OMO 的底层基础设施（Python 实现），提供 Agent 运行所需的核心能力：

| 组件 | 功能 | 类比 |
|------|------|------|
| 执行循环 (Agent Loop) | 流式工具调用、并行执行、Token 计费追踪 | 工人的手 |
| 工具注册表 (Tool Registry) | 43 种工具（文件、Shell、搜索、Web、MCP） | 工具箱 |
| 上下文管理器 (Context Manager) | CLAUDE.md 发现、上下文压缩、会话恢复 | 工人的记忆 |
| 状态存储 (State Store) | 持久化记忆、会话历史 | 工人的笔记本 |
| 生命周期钩子 (Lifecycle Hooks) | PreToolUse/PostToolUse 拦截、权限控制 | 安全护栏 |
| 子代理调度 (Subagent Spawning) | 派遣子代理、团队注册、后台任务管理 | 工头 |

### 7.4 安装与配置

```bash
# 安装 OMO
curl -s https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/docs/guide/installation.md | bash

# 安装 OpenHarness（底层基础设施）
pip install openharness-ai

# 验证安装
oh --version
```

配置文件 `opencode.json` 示例：

```json
{
  "agents": {
    "planner": { "model": "claude-opus-4-6", "role": "规划" },
    "frontend": { "model": "gemini-flash", "role": "前端开发" },
    "backend": { "model": "claude-sonnet-4", "role": "后端开发" },
    "reviewer": { "model": "claude-opus-4-6", "role": "代码审查" }
  },
  "orchestration": {
    "ultrawork": true,
    "max_parallel_workers": 5
  }
}
```

OMO 的核心命令：

| 命令 | 作用 | 场景 |
|------|------|------|
| `/autopilot` | 自动检测意图，编排 19 个 Agent | 不确定用什么流程时 |
| `/ultrawork` | 启动最多 5 个并行 Worker | 大型重构、批量测试生成 |
| `/ralph` | 循环"计划→执行→验证→修复"直到任务完成 | 顽固 Bug 修复 |
| `/team N` | 启动 N 个协调 Agent，共享任务列表 | 多模块并行开发 |

### 7.5 OMO 的杀手级特性：Hash-Anchored Editing

所有 AI 编码工具都有一个致命问题：AI 试图编辑一行已经变化的代码，编辑失败，重试，再失败——循环烧 Token。OMO 发明了  Hash-Anchored Editing ：每行代码生成一个内容哈希指纹，编辑前先检查指纹是否匹配。如果代码已变，自动定位新位置。实测编辑成功率从 6.7% 飙升到 68.3%——10 倍提升。

## 八、三层架构协作：规范→纪律→协作

### 8.1 三者的精确分工

OpenSpec、Superpowers、Harness/OMO 不是三个独立工具的简单叠加，而是形成了一套严密的接力系统。每一层只做一件事，且只信任上一层的输出：

```
┌─────────────────────────────────────────────────────────┐
│  规范层 (OpenSpec)                                       │
│  输入：模糊的需求                                        │
│  输出：proposal.md + spec.md + tasks.md                  │
│  铁律：没有确认的规范，不进入下一层                       │
├─────────────────────────────────────────────────────────┤
│  纪律层 (Superpowers)                                    │
│  输入：OpenSpec 的 tasks.md（作为执行蓝图）               │
│  输出：经过 TDD 验证的代码 + 两阶段审查报告               │
│  铁律：没有失败测试，不写实现代码                         │
├─────────────────────────────────────────────────────────┤
│  协作层 (Harness/OMO)                                    │
│  输入：OpenSpec 的 spec.md（作为统一规范源）              │
│  输出：多个 Agent 并行执行，互不冲突                      │
│  铁律：所有 Agent 共享同一份 spec，禁止各自理解           │
└─────────────────────────────────────────────────────────┘
```

### 8.2 数据如何流转：一个完整的需求旅程

用一个真实场景走一遍："给电商平台添加订单系统"。

 第一站：OpenSpec（规范层）——把模糊变精确 

```
你："添加订单系统"
↓
/opsx:propose "add order system"
↓
AI 生成：
  openspec/changes/add-order-system/
  ├── proposal.md  → 为什么要做、做什么、不做什么
  ├── design.md    → 技术选型（订单状态机、支付回调、库存扣减）
  ├── specs/
  │   ├── order-creation/spec.md   → "系统 SHALL 在创建订单时原子扣减库存"
  │   └── order-payment/spec.md    → "系统 SHALL 在支付超时后自动取消订单"
  └── tasks.md     → 分 3 阶段 12 个任务，每个含文件路径+验证步骤
↓
你审查 proposal.md，确认"非目标"：不做退款、不做拆单
↓
/opsx:apply → 规范锁定，进入执行
```

 第二站：Superpowers（纪律层）——按规范严格执行 

```
Superpowers 读取 tasks.md，开始 TDD 流程：
↓
Task 1.1: 创建 Order 模型
  RED:   先写 test_order_creation.py → 测试失败 ✗
  GREEN: 写最小实现 Order model → 测试通过 ✓
  REFACTOR: 添加索引、优化字段 → 测试仍通过 ✓
↓
Task 1.2: 实现库存原子扣减
  RED:   先写 test_stock_deduction.py → 测试失败 ✗
  GREEN: 用 SELECT FOR UPDATE 实现行锁 → 测试通过 ✓
↓
... 逐任务执行 ...
↓
两阶段审查：
  Spec 审查：对照 spec.md，12 个需求全部覆盖 ✓
  质量审查：覆盖率 91%，无安全漏洞 ✓
```

 第三站：Harness/OMO（协作层）——多 Agent 并行 

当订单系统大到需要多人并行时，OMO 接管编排：

```
OMO 读取 openspec/specs/ 中的 spec.md（统一规范源）
↓
Prometheus（规划 Agent）：拆解为前端/后端/测试三条线
↓
Atlas（编排层）：分配任务
  ├── Frontend Agent (Gemini Flash) → 订单列表页、详情页
  │   └── 读取 spec: order-creation/spec.md → 知道字段有哪些
  ├── Backend Agent (Claude Sonnet) → 订单 CRUD API
  │   └── 读取 spec: order-payment/spec.md → 知道超时逻辑怎么写
  └── Reviewer Agent (Claude Opus) → 代码审查
      └── 对照 spec.md 逐条检查，不是凭感觉审
↓
三个 Agent 产出合并，因为共享同一份 spec，不会"对不上"
```

### 8.3 缺失任何一层的真实后果

| 缺失层 | 真实场景 | 后果 |
|--------|---------|------|
| 没有 OpenSpec | 3 个 Agent 各自理解"订单系统" | 前端做了购物车，后端做了支付，测试做了物流——拼不上 |
| 没有 Superpowers | Agent 直接写代码，跳过测试 | 上线后库存扣减出现并发 Bug，超卖 200 单 |
| 没有 Harness | 多人同时改同一文件 | A 刚写完支付回调，B 把接口参数改了，A 的代码全废 |

### 8.4 三层协作的核心原则

 原则一：规范是唯一的真相来源 

所有 Agent、所有 Skill、所有工具，都以 `openspec/specs/` 目录下的 spec.md 为准。不允许任何 Agent "按自己理解"做——理解不一致时，回去改 spec，而不是各自为政。

 原则二：每层只信任上一层的输出 

- Superpowers 不信任 AI 的"自由发挥"，只信任 OpenSpec 的 tasks.md
- Harness 不信任 Agent 的"自行理解"，只信任 OpenSpec 的 spec.md
- 人不信任 AI 的"自我审查"，关键节点必须人工确认

 原则三：规范不变、流程不变、团队可弹性扩展 

- 一个人用：OpenSpec + Superpowers 就够
- 2-3 人小团队：OpenSpec + Superpowers + Git 分支协作
- 5+ 人团队：OpenSpec + Superpowers + OMO 多 Agent 编排

规范层稳定了需求基线，纪律层保证了执行质量，协作层让团队规模可以灵活伸缩。三层各自独立，但通过 spec.md 这个"合约"紧密耦合。

## 九、场景选择指南

不是所有场景都需要全套工具。根据项目复杂度和团队规模，选择合适的组合：

| 场景 | 推荐工具组合 | 理由 |
|------|-------------|------|
| 快速原型验证 | OMO | 只需快速出活，不需要规范约束 |
| 核心业务代码 | Superpowers | 需要质量保障，但需求明确无需规范管理 |
| 团队协作 + 文档沉淀 | OpenSpec | 规范即文档，保证团队认知一致 |
| 生产级项目 | OpenSpec + Superpowers + Harness | 全链路质量保障 |
| 简单 Bug 修复 | 原生 AI 编码工具 | 杀鸡不用牛刀 |
| 遗留系统重构 | OpenSpec + Superpowers | 先锁定变更边界，再 TDD 逐步替换 |

推荐的采纳顺序：

1.  先上 OpenSpec ——建立规范意识，让 AI 的输出可预期
2.  再学 Superpowers 核心技能 ——TDD、审查流程，提升代码质量
3.  最后引入 Harness/Agent Team ——多 Agent 协作，扩展团队产能

不要一上来就全套上马。工具的学习成本叠加，容易导致团队抵触。循序渐进，每一步都感受到价值，自然就会走向完整的三层架构。

## 九、主流编程工具与三层架构组合最佳实践

本节介绍 IT 行业常用的 AI 编程工具（Trae、Cursor、Claude Code、Windsurf 等）如何与 OpenSpec、Superpowers、Harness/OMO 组合使用，提供真实可操作的最佳实践。

### 9.1 工具生态概览

当前主流的 AI 编程工具可以归为三类：

| 类别 | 代表工具 | 特点 | 与 OpenSpec 集成方式 |
|------|---------|------|---------------------|
| AI IDE（集成开发环境） | Trae、Cursor、Windsurf | 图形界面，深度集成编辑器，支持 MCP 和规则文件 | `openspec init` 自动生成 `.trae/`、`.cursor/` 等目录的 slash commands 和规则文件 |
| 终端 AI 代理 | Claude Code、Codex CLI、Gemini CLI | 终端命令行，擅长多文件操作和自动化 | `openspec init` 生成 CLAUDE.md、AGENTS.md 等上下文文件，支持 `/opsx:` 系列斜杠命令 |
| 多 Agent 编排层 | OMO (Oh My OpenAgent)、OpenHarness | 协调多个 AI Agent 并行工作，路由不同模型 | 通过 OpenSpec 规范文档作为各 Agent 的统一输入源 |

>  关键点 ：OpenSpec 已原生支持 20+ 工具，包括 Trae、Cursor、Claude Code、Windsurf、Codex、Gemini CLI 等。对于不支持斜杠命令的工具，OpenSpec 会生成根目录 `AGENTS.md` 文件作为上下文指令。

### 10.2 个人开发者最佳实践：Trae + OpenSpec + Superpowers

 适用场景 ：独立开发者或 2-3 人小团队，日常功能开发和重构。

#### 第一步：环境准备

```bash
# 1. 安装 OpenSpec
npm install -g @fission-ai/openspec@latest

# 2. 在项目根目录初始化（自动检测 Trae 并生成 .trae/ 配置）
cd your-project
openspec init
```

初始化后，Trae 项目根目录 `.trae/` 下会生成：
- `.trae/rules/` —— OpenSpec 生成的项目规则文件，Trae Agent 会自动读取
- `AGENTS.md` —— 包含 OpenSpec 工作流指令，供 AI 代理读取
- `openspec/` —— 规范目录（specs/ 和 changes/）

#### 第二步：Trae 规则配置

在 Trae 中设置项目规则（Settings → Rules → Create Project Rule），创建 `openspec-workflow.md`：

```markdown
## OpenSpec 工作流规则
- 收到新功能需求时，先执行 /opsx:propose 生成变更提案
- 提案必须经过人工审查确认后才能执行 /opsx:apply
- 所有变更必须在 changes/ 目录下进行，不得直接修改 specs/
- 完成后使用 /opsx:archive 归档
```

设置为  Always Apply  模式，确保每次对话都遵循规范驱动流程。

#### 第三步：Superpowers 集成

```bash
# 在 Claude Code 或终端中安装 Superpowers（作为纪律层）
# 通过 Claude Code Plugin Marketplace 安装
/plugin install superpowers@superpowers
```

 日常工作流程 ：

```
1. Trae IDE 中：/opsx:explore "添加用户登录功能"
   → AI 探索项目上下文，理解现有代码结构

2. Trae IDE 中：/opsx:propose "添加用户登录功能"
   → 生成 openspec/changes/add-user-login/
     ├── proposal.md（变更提案）
     ├── design.md（技术方案）
     ├── spec.md（规范增量）
     └── tasks.md（任务清单）

3. 人工审查 proposal.md 和 design.md，确认无误

4. Trae IDE 中：/opsx:apply
   → AI 按 tasks.md 逐项实现代码

5. 在终端/ Claude Code 中用 Superpowers 验证：
   → 自动触发 TDD 流程：写测试 → 看失败 → 写实现 → 看通过 → 重构

6. 测试通过后：/opsx:archive
   → 变更归档，specs/ 更新
```

#### 关键配置点

| 配置项 | 位置 | 内容 |
|--------|------|------|
| Trae 项目规则 | `.trae/rules/openspec-workflow.md` | 强制 OpenSpec 工作流 |
| OpenSpec 配置 | `openspec/config.yaml` | 定义项目技术栈和规则 |
| AGENTS.md | 项目根目录 `AGENTS.md` | 包含 OpenSpec 核心指令，供所有 AI 工具读取 |

### 9.3 团队开发最佳实践：Cursor/Claude Code + OpenSpec + OMO

 适用场景 ：5+ 人团队，多特性并行开发，需要多模型协同。

#### 架构设计

```
规范层 (OpenSpec)          纪律层 (Superpowers)       协作层 (OMO)
─────────────────          ──────────────────          ──────────────────
定义"做什么"                定义"怎么做"               定义"谁来做"
proposal → spec            TDD → 测试 → 审查           多 Agent 并行执行
```

#### 操作步骤

 1. 统一团队规范（OpenSpec 一次配置，全团队生效） 

```bash
# 技术负责人执行
npm install -g @fission-ai/openspec@latest
cd project
openspec init  # 选择团队主要使用的工具（如 Cursor）

# 创建团队 config.yaml
cat > openspec/config.yaml << 'EOF'
context:
  - "本项目使用 Next.js 14 + TypeScript + Prisma"
  - "所有 API 使用 tRPC"
  - "测试使用 Vitest + React Testing Library"
rules:
  - id: review
    description: "所有变更必须经过人工审查后才能 apply"
  - id: tdd
    description: "所有业务逻辑必须有对应测试"
EOF

git add openspec/ AGENTS.md && git commit -m "chore: init OpenSpec with team conventions"
```

 2. 团队成员开发流程 

每位成员在自己的分支上操作：

```bash
# 成员 A：开发用户认证功能
git checkout -b feat/auth
/opsx:propose "add user authentication with JWT"
# 审查 proposal → /opsx:apply → 测试 → /opsx:archive

# 成员 B：开发支付功能（并行）
git checkout -b feat/payment
/opsx:propose "add stripe payment integration"
# 审查 proposal → /opsx:apply → 测试 → /opsx:archive
```

由于 specs/ 和 changes/ 的分离设计，两人不会互相干扰各自的规范。

 3. 引入 OMO 多 Agent 编排（处理复杂任务） 

当单个任务涉及多个模块时，用 OMO 编排多个 Agent 并行：

```json
// opencode.json (OMO 配置)
{
  "agents": {
    "planner": { "model": "claude-opus-4-6", "role": "规划" },
    "frontend": { "model": "gemini-flash", "role": "前端开发" },
    "backend": { "model": "claude-sonnet-4", "role": "后端开发" },
    "reviewer": { "model": "claude-opus-4-6", "role": "代码审查" }
  },
  "orchestration": {
    "ultrawork": true,  // 启用全自动并行模式
    "spec_source": "openspec/"  // 以 OpenSpec 规范为统一输入
  }
}
```

OMO 的 Agent 自动读取 `openspec/specs/` 中的规范文档，按任务拆解并行执行：

```
用户指令："实现完整的订单系统"
↓
Prometheus（规划 Agent）：读取 OpenSpec spec.md，拆分子任务
↓
Atlas（编排层）：分配任务
  ├── Frontend Agent → 订单列表页、详情页
  ├── Backend Agent → 订单 CRUD API
  └── Reviewer Agent → 代码审查
↓
所有 Agent 共享同一份 OpenSpec 规范，确保输出一致
```

### 9.4 各工具与 OpenSpec 的集成速查表

| 工具 | 安装方式 | 规则文件位置 | 斜杠命令支持 | 备注 |
|------|---------|-------------|-------------|------|
|  Trae  | `openspec init` | `.trae/rules/` + `AGENTS.md` | ✅ 通过 AGENTS.md | 支持 `.rules` 文件和嵌套规则，MCP 集成 |
|  Cursor  | `openspec init` | `.cursor/rules/` | ✅ 原生 | 支持 `.mdc` 规则文件 |
|  Claude Code  | `openspec init` | `CLAUDE.md` + `.claude/commands/` | ✅ 原生 | 推荐，集成最完整 |
|  Windsurf  | `openspec init` | `.windsurfrules` | ✅ 原生 | Cascade 面板直接操作 |
|  Codex CLI  | `openspec init` | `AGENTS.md` | ✅ 原生 | OpenAI 官方终端代理 |
|  Gemini CLI  | `openspec init` | `GEMINI.md` | ✅ 原生 | Google 终端代理 |
|  GitHub Copilot  | `openspec init` | `.github/copilot-instructions.md` | ✅ 原生 | 通过指令文件 |
|  Qwen Code  | `openspec init` | 自动生成对应配置 | ✅ 原生 | 阿里通义千问编码代理 |

### 9.5 典型场景实战：从零搭建规范驱动开发环境

 场景 ：你是一名后端开发，需要在 Trae IDE 中开发一个新的 REST API 项目，使用 OpenSpec + Superpowers 确保代码质量。

#### 环境初始化（5 分钟）

```bash
# 1. 全局安装
npm install -g @fission-ai/openspec@latest

# 2. 创建项目
mkdir my-api && cd my-api
# 在 Trae 中打开该项目

# 3. 初始化 OpenSpec（选择 Trae 作为主工具）
openspec init
# → 自动生成 .trae/ 配置和 AGENTS.md

# 4. 创建 OpenSpec 自定义配置
cat > openspec/config.yaml << 'EOF'
context:
  - "本项目使用 FastAPI + SQLAlchemy + PostgreSQL"
  - "API 版本控制在 URL 路径中（/api/v1/...）"
  - "所有端点必须有 Pydantic schema 验证"
  - "使用 pytest 做单元测试，覆盖率 ≥ 80%"
rules:
  - id: tdd
    description: "业务逻辑必须先写测试再写实现"
  - id: review
    description: "spec.md 变更后必须人工审查"
EOF
```

#### 开发第一个功能：用户注册 API（15 分钟）

```
# 在 Trae Agent 聊天中输入：
/opsx:propose "add user registration endpoint"

# AI 生成变更提案，你审查以下内容：
# openspec/changes/add-user-registration/proposal.md
# openspec/changes/add-user-registration/spec.md
# openspec/changes/add-user-registration/tasks.md

# 确认无误后执行：
/opsx:apply

# Trae Agent 按 tasks.md 逐项实现：
# ✅ 1.1 创建 User Pydantic model
# ✅ 1.2 编写 POST /api/v1/users 路由
# ✅ 1.3 添加密码加密逻辑 (bcrypt)
# ✅ 1.4 编写单元测试
# ✅ 1.5 运行测试，确保通过

# 全部完成并验证后：
/opsx:archive
# → 变更归档到 openspec/changes/archive/
# → openspec/specs/user-registration/spec.md 更新
```

#### 关键验证点

| 阶段 | 验证方式 | 预期结果 |
|------|---------|---------|
| 提案生成 | 人工审查 proposal.md | 需求描述清晰，无遗漏 |
| 规范确认 | 对比 spec.md 与项目现状 | 规范与现有架构一致 |
| 代码实现 | 运行 `pytest --cov=src tests/` | 测试全部通过，覆盖率 ≥ 80% |
| 归档检查 | 检查 archive/ 目录 | 变更完整归档，specs/ 已更新 |

### 10.6 进阶实战：重构"幽灵订单"支付回调系统

上面的用户注册是"从零开始"的简单场景。但现实工作中，更常见也更痛苦的是 重构遗留系统 ——代码已经存在，逻辑纠缠不清，AI 一改就出事。下面这个案例，展示了 OpenSpec + Superpowers 如何在复杂重构中真正发挥作用。

 背景 ：一个老旧的交易系统，需要接入新的 V3 版支付接口，解决旧版频繁出现的"回调掉单"问题。如果直接让 AI 改代码，它大概率会写出一堆看似能用、但缺乏边界判断的毛坯代码。

#### 第一步：用 OpenSpec 锁定"共识"（不再鸡同鸭讲）

不要直接说"改支付接口"，而是通过 OpenSpec 明确边界：

```
/opsx:propose "重构支付回调系统，接入V3接口"
```

系统自动生成 `changes/revise-payment-callback/` 目录。在 proposal.md 中，通过自然语言硬性约束边界：

```markdown
## 改动范围
- 仅限 PaymentService，不触碰订单模块

## 必须保留
- 旧版 V1 接口的兼容性（灰度期间双版本并行）

## 核心新增
- 引入幂等性校验机制，防止重复入账
- 网络超时的退避重试策略
```

此时 OpenSpec 生成的 tasks.md 才是真正的需求文档——不仅你看得懂，AI 也看得懂，而且必须严格执行。

#### 第二步：Superpowers 开启"深度设计"（杜绝乱写）

启动 Superpowers 的 Brainstorming 技能，AI 不会直接写代码，而是开始自我提问：

- "新旧接口返回的字段映射差异如何解决？"
- "网络超时的重试策略是退避还是立即重试？"
- "幂等性校验放在哪一层？数据库还是缓存？"

它生成了一份 design.md，里面甚至画出了时序图，标注了哪一步是"关键事务"，哪一步是"异步补偿"。这个阶段强迫 AI 把隐藏的复杂性挖出来，而不是在代码里埋雷。

#### 第三步：TDD 驱动下的"降维打击"（闭眼写代码）

编码阶段变得异常丝滑——AI 此刻更像一个纯执行者。它自动遵循 TDD 原则：在写 PaymentService 之前，先写出测试用例 PaymentCallbackTest，覆盖了"签名错误""重复回调""数据不一致"等 7 个异常场景。

这就是碾压级的优势：传统开发中你要手动 Mock 数据，现在 AI 基于 Spec 直接把测试基架搭好，你甚至不需要运行，一眼看过去就知道逻辑是闭环的。

#### 第四步：归档与进化（不再产生"遗产"）

代码合并后执行归档：

```
/opsx:archive
```

OpenSpec 将这次变更的所有 Spec 同步到主分支。下次你再让 AI 改支付逻辑，它甚至记得上次为什么这里要加一个"幂等性校验"。 闭环形成，这才是真正的工程资产。 

### 10.7 失败路径修复手册：5 个最常见的卡点

很多教程只写顺风局，但你真正需要的是：出问题时能把项目拉回正轨。以下 5 个场景，是团队里最常见、也最容易导致返工的卡点。

 卡点 1：Specs 写得很全，但 AI 还是偏离需求 

| 项目 | 内容 |
|------|------|
|  症状  | 代码"看起来都对"，但和 specs/*.md 的约束对不上；PR 里出现"顺便加了个功能" |
|  根因  | tasks.md 只有"做什么"，缺少"做到什么算完成"（DoD）；实现阶段一次性加载太多上下文，注意力漂移 |
|  修复  | 回到 tasks.md：给每个任务补 1 行 DoD（状态码/错误分支/测试覆盖点）；把 proposal.md 的"非目标"同步到 tasks.md 顶部，作为实现阶段护栏 |
|  防复发  | Spec Reviewer 用"对照打勾"方式审：只判定是否满足 specs + DoD |

 卡点 2：TDD 卡住（写不出合理测试，或测试很脆弱） 

| 项目 | 内容 |
|------|------|
|  症状  | 红灯阶段写不出一个合理的失败测试；测试依赖 DB/网络，跑不稳定 |
|  根因  | 一个任务包含多个行为，测试无法聚焦；依赖未隔离，很难 mock |
|  修复  | 把任务拆到 2-5 分钟粒度：一条测试只覆盖一个行为；先写"纯校验/纯映射"测试，再写 I/O 测试；对 DB/网络先做"内存实现 + 契约测试"，最后再换真实实现 |
|  防复发  | 在 tasks.md 每个任务里写明：1 个失败用例 + 1 个边界用例 |

 卡点 3：Worktree 管不住（目录/分支混乱） 

| 项目 | 内容 |
|------|------|
|  症状  | 同一个变更出现多个 worktree；或在错误 worktree 上改代码；合并时发现漏文件 |
|  根因  | worktree 命名缺少映射规则，无法"一眼看懂" |
|  修复  | 约定命名：`../<repo>-<change>-<yyyyMMdd>`；每次开工先 `git worktree list` 确认路径↔分支；只保留 ≤3 个活跃 worktree |
|  防复发  | 在变更任务清单顶部写清楚：worktree 路径 + 分支名 |

 卡点 4：verify 不通过（测试挂了 / lint 挂了 / 行为没覆盖） 

| 项目 | 内容 |
|------|------|
|  症状  | 验证报告提示某些任务未覆盖，或测试/构建失败 |
|  根因  | 把验证当成"最后一步"，导致失败集中爆雷 |
|  修复  | 把失败项映射回 tasks.md：属于哪个任务的 DoD 没满足；先修"便宜失败"（lint/类型/单测），再修系统性失败（集成/架构）；修复后补 1 条"回归测试点" |
|  防复发  | 每完成 2-3 个小任务就做一次快速验证，不要堆到最后 |

 卡点 5：Spec Reviewer 与 Code Reviewer 意见冲突 

| 项目 | 内容 |
|------|------|
|  症状  | 一个说"满足规格就行"，另一个说"结构不行要重构"，推进停滞 |
|  根因  | 审查标准没分层：规格合规 vs 代码质量混在一起 |
|  修复  | 先过规格：只讨论"是否满足 specs + DoD"；再过质量：限定重构边界（不改行为、不改外部接口）；若确需大改：回到 design.md 补一条决策记录 |
|  防复发  | 固定两阶段审查输出：Spec 只给"缺口清单"，Quality 只给"风险清单" |

### 10.8 避坑指南：多工具组合的常见陷阱

| 陷阱 | 表现 | 解决方案 |
|------|------|---------|
|  规则文件冲突  | Cursor 的 `.cursorrules` 和 Trae 的 `.trae/rules/` 规则不一致 | 以 `AGENTS.md` 为唯一真相来源，`openspec sync` 自动同步到各工具规则文件 |
|  斜杠命令不生效  | 在 Trae 中直接输 `/opsx:propose` 没反应 | Trae 通过 AGENTS.md 识别 OpenSpec 命令，确保 `openspec init` 已完成，或在自然语言中说"用 OpenSpec 提案" |
|  Agent 上下文丢失  | Trae 会话重启后忘了 OpenSpec 规范 | `.trae/rules/` 中的项目规则持久生效，或创建 Always Apply 规则 |
|  多 Agent 规范不一致  | OMO 的不同 Agent 对同一规范理解不同 | 统一以 `openspec/specs/` 目录下的 spec.md 为唯一输入源 |
|  Superpowers 与 OpenSpec 流程打架  | Superpowers 的 brainstorm 和 OpenSpec 的 propose 产生冲突 | 先用 Superpowers brainstorm 做探索性讨论，方向明确后再用 OpenSpec propose 锁定规范 |

## 十一、常见问题与避坑

 Q1：输入 `/opsx:verify` 提示命令不存在？ 

需要先切换到自定义配置文件：`openspec config profile custom`，然后运行 `openspec update`。默认的 default 配置只包含四个核心命令。

 Q2：tasks.md 和实际代码不一致，正常吗？ 

正常。tasks.md 是 Plan Agent 的初始规划，Execute Agent 在执行过程中会根据实际情况动态调整。只要最终结果符合 spec.md 的要求即可，tasks.md 不是必须逐条执行的死命令。

 Q3：三个工具必须全用吗？ 

不必。根据场景选择，参考第八节的指南。简单项目用 OpenSpec 就够了。

 常见坑点： 

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

AI 不会取代程序员，但会用工具的迟早会。从 Vibe Coding 到 Spec Coding，就是你和一个成熟架构师之间最大的鸿沟。现在，去给你的项目装上这套动态引擎，把掌控权拿回来。

---

## 参考文章

- [OpenCode 生态铁三角：OpenSpec + Superpowers + OMO，搞懂三者的关系才算真正会用](https://www.toutiao.com/article/7623696555203166755/)
- [AI 编程工程化三层基础设施：OpenSpec 管"做什么"，Superpowers 管"怎么做"，Harness 管"谁来做"](https://m.toutiao.com/article/7628121721748455951/)
- [Superpowers 搭配 OpenSpec 的三段式流程：从不确定的需求到可落地、可验收、可追溯的成果](https://www.toutiao.com/article/7629572762553582143/)
- [Superpowers 完整指南：让 AI 守规矩的工程化工作流框架](https://m.toutiao.com/article/7633948930383987226/)
- [OpenSpec 任务粒度控制：2/8 法则与三步配置法](https://www.toutiao.com/article/7638433345973518854/)
- [Claude Code Superpowers 与 OpenCode OpenSpec 对比指南](https://www.toutiao.com/article/7631032112321184299/)
- [还在让 AI 帮你"写 Bug"？OpenSpec + Superpowers 组合拳让代码确定性提升 10 倍](https://www.toutiao.com/article/7646459603399492146/)
- [AI 编程进阶：OpenSpec + Superpowers 组合方案深度使用教程](https://www.toutiao.com/article/7646330100308361768/)
- [Claude Code + OpenSpec + Superpowers，AI 协同开发实战详解（从入门到精通）](https://blog.csdn.net/u013970991/article/details/159598155)

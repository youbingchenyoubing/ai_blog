# OpenSpec 文章撰写 Spec

## Why
用户希望基于6篇参考文章，撰写一篇关于 OpenSpec 的中文技术文章，发布到其博客项目中。参考文章涵盖了 OpenSpec 的概念、安装、核心工作流、与 Superpowers/Harness/OMO 的协同、任务粒度控制、以及对比指南等丰富内容，需要整合提炼为一篇结构清晰、内容完整的原创文章。

## What Changes
- 在 `/Users/chenyoubing/WorkPlaces/blog/` 下新建 `openspec/` 主题目录
- 创建文章文件 `01-OpenSpec规范驱动开发完整指南.md`，涵盖以下核心内容：
  - OpenSpec 是什么：规范驱动开发(SDD)框架的定位与核心理念
  - 核心设计：specs/ 与 changes/ 分离的目录结构
  - 安装与初始化：全局安装、项目初始化步骤
  - OPSX 工作流：explore → propose → apply → archive 四步核心命令
  - 与 Superpowers 的协同：三段式流程（探索→锁定规范→执行编码）
  - 任务粒度控制：2/8 法则，三步配置法（config.yaml → fork schema → review 工件）
  - 与 Harness/OMO 的三层架构：规范层→纪律层→协作层
  - 场景选择指南：什么场景用什么工具
  - 常见问题与避坑

## Impact
- Affected specs: 无已有 spec 受影响（新文章）
- Affected code: 仅新增 markdown 文件，不修改任何已有代码

## ADDED Requirements

### Requirement: 创建 OpenSpec 主题目录
系统 SHALL 在博客项目根目录下创建 `openspec/` 目录，与已有 `openclaw/`、`imessage-agent/` 目录平级。

#### Scenario: 目录创建成功
- **WHEN** 创建 `openspec/` 目录
- **THEN** 该目录与 `openclaw/`、`imessage-agent/` 平级存在于项目根目录下

### Requirement: 撰写 OpenSpec 完整指南文章
系统 SHALL 创建 `openspec/01-OpenSpec规范驱动开发完整指南.md` 文件，内容基于6篇参考文章整合提炼，遵循以下要求：

#### Scenario: 文章格式符合博客规范
- **WHEN** 文章被创建
- **THEN** 文章以 `# 标题` 开头，无 YAML frontmatter
- **THEN** 章节使用中文序号（一、二、三...）
- **THEN** 全文使用中文撰写
- **THEN** 代码块带有语言标签
- **THEN** 使用表格进行对比说明

#### Scenario: 文章内容覆盖核心知识点
- **WHEN** 文章被创建
- **THEN** 文章涵盖 OpenSpec 的定义与核心理念（规范驱动开发、先定规矩再写代码）
- **THEN** 文章涵盖 specs/ 与 changes/ 分离的目录结构设计
- **THEN** 文章涵盖安装与初始化步骤（npm install、openspec init）
- **THEN** 文章涵盖 OPSX 核心工作流（explore、propose、apply、archive）
- **THEN** 文章涵盖与 Superpowers 的三段式协同流程
- **THEN** 文章涵盖任务粒度控制方法论（2/8法则、三步配置）
- **THEN** 文章涵盖三层架构（OpenSpec + Superpowers + Harness/OMO）
- **THEN** 文章涵盖场景选择指南和常见问题

#### Scenario: 文章内容为原创整合
- **WHEN** 文章被创建
- **THEN** 文章内容基于参考文章整合提炼，而非直接复制
- **THEN** 文章有自己的逻辑结构和叙述线索
- **THEN** 关键概念和引用有明确出处说明

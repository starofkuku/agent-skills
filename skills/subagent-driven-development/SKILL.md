---
name: subagent-driven-development
description: 当你有实现计划、且计划中的任务相互独立（适合并行/隔离执行）时，使用此 skill 派子代理执行：每个任务派一个全新 implementer 子代理，任务后派 reviewer 子代理审查，最后做整体审查。用 Codex 的 spawn_agent / send_message / wait_agent 工具完成。
---

# 子代理驱动开发（Codex 版）

通过派子代理执行实现计划：**每个任务一个全新的 implementer 子代理**，每个任务完成后**一个 reviewer 子代理审查**（规格合规 + 代码质量），全部完成后**一次整体审查**。

**为什么用子代理：** 子代理拥有隔离的上下文，专注于单个任务，不会被主代理的会话历史污染。主代理负责精确构造每个子代理所需的上下文，并保留自己的上下文用于协调。子代理**不应继承**主代理的完整历史——由主代理构造它们恰好需要的内容。

**核心原则：** 每任务全新子代理 + 任务后审查（规格 + 质量）+ 最终整体审查 = 高质量、快速迭代。

**持续执行：** 在任务之间不要停下来问用户。按计划连续执行所有任务。唯一停止的原因是：无法解决的 BLOCKED 状态、真正阻碍进展的歧义、或全部任务完成。

## 前置条件

- Codex 多代理工具可用（V2：`features.multi_agent_v2 = true`，工具在 `collaboration` 命名空间；或 V1 的 `multi_agent_v1` 命名空间）
- 有一个实现计划，且任务相互独立

## 何时使用

```
有实现计划？ ──否──▶ 先做计划或直接执行
   │是
任务大部分独立？ ──否──▶ 手动执行（任务耦合紧密）
   │是
在当前会话执行？ ──否──▶ 并行会话
   │是
▶ subagent-driven-development
```

## 流程

### Setup（准备）
1. 读取实现计划，确认任务列表相互独立
2. 创建工作区/台账文件（见下方 ledger）
3. 通读计划，识别全局约束（跨任务的架构约定）

### 每个任务（Per Task）
1. **派 implementer 子代理**（用 `spawn_agent`，message 按 `implementer-prompt.md` 模板构造，`fork_turns` 设为 `none` 或按需）
2. implementer 实现、测试、自审，返回报告
3. **派 task reviewer 子代理**审查该任务（规格合规 + 代码质量），message 按 `task-reviewer-prompt.md` 模板
4. 审查通过 → 更新 ledger，标记完成，进入下一个任务
5. 审查发现冲突 → 修复循环（最多 5 轮：前 3 轮续用原 implementer，第 4 轮起换新 implementer）
6. 无法解决的冲突 → 上报 BLOCKED 给用户

### 最终整体审查
- 所有任务完成后，派 reviewer 子代理做整支审查
- 处理残留发现，确认无 load-bearing 问题
- 更新 ledger，收尾

## Codex 工具用法

### 派 implementer 子代理
```
工具：spawn_agent（V2 下 collaboration.spawn_agent，V1 下 multi_agent_v1.spawn_agent）
参数：
  task_name: "task-N-<任务名>"
  message:   (按 implementer-prompt.md 模板生成的完整任务提示)
  fork_turns: "none"   # 关键：子代理不继承主代理上下文，由你构造它需要的一切
  model:      (可选，需要时指定)
```

### 子代理执行期间
- 子代理后台运行时，主代理可继续其他工作
- 用 `wait_agent` 等待结果（带超时），或 `send_message` 交互，`interrupt_agent` 打断，`list_agents` 查看

### 派 reviewer 子代理
```
工具：spawn_agent
参数：
  task_name: "review-task-N"
  message:   (按 task-reviewer-prompt.md 模板生成的审查提示)
  fork_turns: "none"
```

## 台账（Ledger）

在工作区维护一个 ledger 文件（如 `AGENTS-LEDGER.md`），按任务记录：

```markdown
## Task 1: <任务名>
- 状态: [in-progress | done | blocked]
- 子代理: <agent 引用>
- 审查发现:
  - [ ] <发现1>（裁定：已修复 / 忽略）
- 备注:
```

- 每个任务完成后追加完成记录
- 审查发现与裁定必须记录，便于后续追溯
- BLOCKED 时在 ledger 里标注原因

## 图片处理规则

如果任务涉及**图片**（用户上传了图片、或任务描述中包含图片）：

1. **主代理必须亲自查看图片**，理解图片内容和用户的真实意图（主代理通常支持图片输入）。
2. **不要直接把图片传给子代理**——子代理（如 deepseek-v4-flash）可能**不支持图片输入**，即使传入也会被剥离或无法理解。
3. 主代理把图片内容/意图**提炼成详细的文字描述**（画面内容、关键信息、布局、数据、隐含要求等），再把这个文字作为子代理的 `message` 任务消息发出去。
4. 子代理只处理文字/代码任务，**不负责解读图片**。
5. 如果某个任务完全依赖图片理解且无法用文字转述，主代理应在本地完成该任务，或明确向用户说明限制，**不要强行派给不支持图片的子代理**。

## 注意事项

- **上下文隔离**：默认 `fork_turns: "none"`。只有子代理明确需要主代理历史时才用 `all` 或正整数
- **子代理数量**：受并发限制约束（V2 `max_concurrent_threads_per_session`），不要超过上限同时派
- **审查不可省**：每个任务后审查是质量保证的关键环节
- **不要频繁打断用户**：按计划连续执行，除非真的被阻塞

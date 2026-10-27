---
name: ai-memory-rescue-session
description: 把超过 ai-memory backfill 体积限制、无法自动导入的巨型会话文件，提炼为可检索的项目记忆（decisions/concepts 页面）。使用 `$ai-memory-rescue-session <agent名> <会话文件路径或session-id前缀>`，例如 `$ai-memory-rescue-session pi 019f88e3`；当 backfill 报 "exceeds the … limit" 或用户要求抢救某个大会话的历史知识时使用。必须在目标项目目录内调用。
---

# Rescue Session：巨型会话文件 → 项目记忆

## 目的

`ai-memory backfill` 对单条记录 >1MB、单会话 >4096 事件、文件 >64MB 的会话会拒绝导入（编译期硬限制，不可配置）。这些会话里往往沉淀着项目的关键知识。本 skill 把这类"读不完的流水账"提炼成几页可检索、可注入简报的 wiki 页面：

```
巨型会话文件（几十 MB，95% 是工具输出）
   ↓ 提取骨架（用户输入全程 + 助手结论尾部，通常 <2MB）
   ↓ 分块消化（LLM 工作）
   ↓ 总结落库（memory_write_page）
几页 decisions/concepts 知识页
```

## 参数

1. **agent 名**：`codex` 或 `pi`（决定提取器）；`zcode` 仅支持探测式兜底
2. **会话定位**：文件完整路径，**或 session-id 前缀**（backfill 报错输出的那种，如 `019f88e3`，脚本会自动搜索定位）

## 前提（必须先确认）

**当前工作目录必须是目标项目目录**——最终 `memory_write_page` 按 cwd 解析项目归属。跨项目调用会把知识落错库。第一步就向用户确认或检查 cwd。

## 执行流程

### 1. 提取骨架（确定性工作，交给脚本）

```bash
python3 <skill目录>/scripts/extract.py --agent <codex|pi> --target <路径或id> [--out-dir /tmp/rescue-<id>]
```

脚本输出三个文件并打印统计：

| 文件 | 内容 |
|---|---|
`user-all.txt` | 全程用户消息（骨架主体） |
`asst-tail.txt` | 助手消息尾部（默认 150 条，含最终结论） |
`meta.txt` | 来源文件、会话 cwd、条数/字节数、建议分块数 |

**脚本以非零退出并报"格式未识别"时，停止并如实报告**——不要自己猜格式硬解析。

### 2. 分块消化（LLM 工作）

按 meta.txt 的建议块数，分块读取 `user-all.txt`（每块约 500 行，用 read 的 offset/limit）：

- 每读完一块，把该段要点（每段一两句）**追加**写入 `<out-dir>/notes.md`
- 绝不试图一次读完整个文件（会撑爆上下文，前段内容被截断）

### 3. 综合总结

读齐三份材料后输出四段总结：

```
① 项目做了什么、分了哪几个阶段
② 关键技术决策及选择原因
③ 当前进度、完成度
④ 遗留问题和下一步
```

总结时**结合当前代码库状态**佐证"怎么做"的部分（代码是最终事实）；保持项目原语言（中文项目出中文总结）。

### 4. 落库（memory_write_page）

- 会话脉络页：`concepts/rescued-<session-id>.md`（固定路径，见下方幂等规则）
- 有独立价值的决策可另写 `decisions/<slug>.md`
- frontmatter 建议：`entities`（模块/技术名词）、`tier: semantic`

## 幂等规则

同一会话重复处理时，**更新同一路径**（`concepts/rescued-<id>.md`），不要新建页面。开头标注来源会话 id 与处理日期。

## 边界与注意事项

- 产物是**提炼页**，不是会话记录：原会话仍在 agent 本地历史中，本 skill 不动它
- `user-all.txt` 超过 2MB 时提醒用户 token 成本，建议确认后再继续
- 提取器只认 `codex` 与 `pi` 的已验证格式；`--agent zcode` 或 `auto` 走通用探测，失败率不保证，失败时建议人工分析文件结构后扩展脚本
- 此流程与 backfill 互补不冲突：backfill 能导的会话不需要本 skill

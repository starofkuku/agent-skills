---
name: session-handoff
description: 在长时间 Codex 对话之间创建或消费仓库本地交接文档，避免恢复庞大会话历史。无参数使用 `$session-handoff`：旧会话中生成或刷新 `HANDOFF.local.md`，新会话中读取并核验交接，成功恢复后删除该一次性文件并继续任务。适用于会话日志过大、resume 缓慢、需要通过 `/new` 切换到干净会话的场景。
---

# Session Handoff

## 选择模式

先读取 `HANDOFF.local.md`（如果存在），再选择模式：

- **准备交接**：文件不存在，或当前对话包含比文件更新、更完整的任务上下文。
- **恢复任务**：文件存在，当前是缺少任务历史的新会话，用户只调用了本 Skill 或要求继续交接任务。

不确定时比较文件记录的时间、分支、HEAD 和当前仓库状态。不要在读取旧文件前覆盖它。

## 准备交接

1. 读取适用的 `AGENTS.md`、`CONTRIBUTING.md` 和项目文档。把 `AGENTS.md` 视为长期规则，不向其中写入临时任务状态。
2. 以当前对话提取目标、决策、失败路径和未完成事项；以仓库状态验证所有代码事实。至少检查：

   ```bash
   git rev-parse --show-toplevel
   git status --short --branch
   git diff --stat
   git diff
   git diff --cached
   git log -10 --oneline --decorate
   ```

3. 在仓库根目录创建或完整刷新 `HANDOFF.local.md`。只修改该文件和 Git 的本地 exclude，不修改业务代码，不提交任何内容。
4. 使用 `git rev-parse --git-path info/exclude` 定位当前 worktree 的 exclude 文件，确保其中有且只有一条 `/HANDOFF.local.md`。不要改动项目 `.gitignore`。
5. 保持文档紧凑、可执行。包含以下章节：

   ```markdown
   # Session Handoff
   ## Snapshot
   ## Goal And Scope
   ## Verified Facts
   ## Completed Work
   ## Decisions And Constraints
   ## Working Tree Ownership
   ## Validation Results
   ## Known Issues And Failed Attempts
   ## Next Steps
   ## Environment
   ## Session Locator
   ## Uncertainties
   ```

6. 在 `Snapshot` 中记录生成时间、仓库根目录、当前分支、HEAD 和工作区摘要。在 `Working Tree Ownership` 中逐项说明未提交文件属于当前任务还是用户已有改动，并标出禁止误删内容。
7. 记录实际运行过的命令及准确结果；未运行的测试写明“未运行”，不能写成通过。环境变量只记录名称和用途，禁止记录 token、密码、密钥或其他秘密值。
8. 明确区分已验证事实与推测。文件和符号尽量写精确路径/名称；下一步按优先级写成可直接执行的动作。

## 会话定位信息

如果运行时已经提供当前 Session ID，或能从 `/status` 的已知结果获得它，则记录。只有在已有可靠信息、且无需扫描或读取全部历史记录时，才记录 transcript/JSONL 路径。无法确认时明确写 `Unavailable`，不要猜测内部目录结构，也不要为填写该字段加载完整 JSONL。

原始会话记录只是兜底档案。`HANDOFF.local.md` 必须能让新会话在通常情况下直接继续工作。

## 完成交接

写完后重新读取交接文件，并用当前 Git 状态核对分支、HEAD、改动和下一步。报告文件路径与摘要，然后给出两条后续输入：

```text
/new <基于任务生成的简短名称>
$session-handoff
```

先完成交接再新建会话。不要建议使用 `/fork` 作为干净交接，因为它会复制当前聊天；不要依赖 Memories 代替即时交接文档。

## 恢复任务

1. 完整读取所有适用的 `AGENTS.md` 和 `HANDOFF.local.md`。
2. 重新检查 `git status --short --branch`、`git diff`、`git diff --cached` 和最近提交。仓库当前状态是代码事实源；交接文件是目标、决策和历史上下文源。
3. 对比二者并标出过期或冲突信息。先简要说明当前目标、已完成状态、未提交改动归属和最高优先级下一步。
4. 仅当交接缺少一个阻碍执行的精确信息时，才根据 Session ID 或可靠 transcript 路径查询旧记录。使用精确关键词、文件名、符号名或错误文本做有界搜索；不要一次性读取完整 JSONL。
5. 如果交接文件不存在、读取失败、与仓库存在未解决冲突或不足以确定任务，不要猜测，也不要删除文件。报告缺失内容并请求最小必要信息，以便重试恢复。
6. 只有在完整读取交接、核验仓库状态并确认当前会话已获得足够上下文后，才删除仓库根目录的 `HANDOFF.local.md`。确认文件已不存在，但永久保留 `.git/info/exclude` 中的 `/HANDOFF.local.md`，供下次交接复用。
7. 删除成功后直接继续最高优先级的未完成任务，不要求用户复述任务。删除失败时明确报告，不要声称交接已消费。

之后再次调用 `$session-handoff` 时，由于旧交接已消费，应根据当前会话和仓库的最新事实创建一份全新的交接文件。

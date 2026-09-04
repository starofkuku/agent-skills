---
name: publish-merge
description: 将开发分支合并到主分支，创建合并提交并推送主分支，最后切回开发分支。无参数时执行 `dev` 到仓库默认主分支的合并；也支持 `$publish-merge dev main` 指定源分支和目标分支。当用户要求发布当前开发分支或完成 dev 到主分支的合并时使用。
---

# Publish Merge

## 参数与分支

无参数调用 `$publish-merge` 时使用：

- 源分支：`dev` (如果是`*` 则是当前分支 比如 `$publish-merge * dev` 就是操作当前分支到dev分支 )
- 目标分支：仓库默认分支，优先识别 `main`，其次识别 `master`
- 远程：`origin`

也可以使用 `$publish-merge dev main` 显式指定源分支和目标分支。先从仓库配置和已有文档确认实际名称，不能静默猜测错误分支。

## 执行流程
> 不要推送源分支 除非  `$publish-merge dev main --push-origin` 后面添加--push-origin 这个参数
1. 阅读仓库根目录及相关目录中的 `AGENTS.md`、`CONTRIBUTING.md`、README 和 Git 配置，遵守分支保护与合并约定。
2. 要求工作区干净：

   ```bash
   git status --short --branch
   git diff
   git diff --cached
   ```

   存在未跟踪改动时需要询问用户是否提交 未跟踪的文件，不要 stash、删除或覆盖改动。 如果AGETNT.md文件有相关约束可直接根据AGENT.md文件直接执行。
3. 获取远程最新状态，确认源分支和目标分支没有无法安全处理的分叉。若源分支有本地未推送提交，先停止并报告；不要把未知版本直接合并到目标分支。
4. 切换到源分支并以 fast-forward 方式同步远程，再切换到目标分支并同步远程：

   ```bash
   git switch dev
   git pull --ff-only origin dev
   git switch main
   git pull --ff-only origin main
   ```

   使用调用参数和仓库实际分支名替换示例中的 `dev`、`main`。
5. 遵循仓库已有的合并策略。没有明确策略时，使用 `--no-ff` 保留一次明确的发布合并提交：

   ```bash
   git merge --no-ff dev
   ```

6. 确认合并结果和 commit 内容后推送目标分支：

   ```bash
   git push origin main
   ```

   禁止强制推送。合并提交已经包含提交动作，不要再创建空提交。
7. 推送成功后切回源分支并检查状态：

   ```bash
   git switch dev
   git status --short --branch
   ```

## 异常处理

- 目标分支受保护或项目要求 Pull Request 时，不绕过规则；报告需要的后续动作。
- 发生合并冲突时不要猜测解决。执行 `git merge --abort` 恢复合并前状态，切回源分支并报告冲突文件。
- 目标分支已经包含源分支时，不创建重复合并，确认状态后切回源分支。
- 任一步骤失败时停止，不自动回滚已推送的提交。

## 完成报告

报告源分支 SHA、目标分支合并 SHA、推送结果和最终当前分支；最终应停留在源分支。

---
name: commit-push
description: 在当前 Git 仓库中检查改动、创建提交并推送到指定分支。使用 `$commit-push` 加目标分支名，例如 `$commit-push dev`；当用户只需要完成 commit 和 push，不需要合并或发布时使用。
---

# Commit and Push

## 参数与目标

将调用中的第一个参数作为目标分支，例如 `$commit-push dev`。如果未提供参数，使用 `dev`。使用仓库实际配置的远程名，默认远程为 `origin`。

## 执行流程

1. 阅读仓库根目录及相关目录中的 `AGENTS.md`、`CONTRIBUTING.md`、README 和 Git 配置，遵守项目已有约定。
2. 检查当前状态、分支和远程：

   ```bash
   git status --short --branch
   git branch --show-current
   git remote -v
   git diff
   git diff --cached
   ```

3. 保护用户已有的未提交改动。不要使用 `reset --hard`、强制 checkout、删除未跟踪文件或未经请求的 stash。如果当前分支不是目标分支，只有在工作区干净时才切换；目标分支不存在时先确认远程是否存在对应分支。
4. 获取远程最新状态，确认目标分支没有发生无法安全处理的分叉。若本地和远程已分叉，暂停并报告，不要覆盖远程提交。
5. 按仓库约定运行必要的格式化、lint 或提交前检查。检查失败时修复或报告，不要创建未验证的提交。
6. 只暂存本次任务相关文件，查看 staged diff；不要使用 `git add -A` 混入无关文件。
7. 根据改动和仓库历史生成简洁、符合项目约定的提交信息，然后创建提交。没有约定时使用 Conventional Commit 风格，例如 `fix: handle empty response`。
8. 推送目标分支：

   ```bash
   git push origin <target-branch>
   ```

   新建的远程跟踪分支才使用 `-u`；禁止 `--force` 或 `--force-with-lease`。

## 边界情况

- 工作区没有改动时，不创建空提交，直接报告当前分支和最新 commit。
- 推送被拒绝时，先读取远程状态并报告原因，不通过强推解决。
- 遇到分支保护、权限问题或提交钩子失败时，保留现场并说明阻塞点。

## 完成报告

报告目标分支、提交 SHA、提交信息、运行过的检查和推送结果，并确认最终工作区状态。

---
name: publish-merge
description: 将源分支合并到目标分支，创建合并提交并推送，最后切回源分支。无参数时执行 `dev` 到仓库默认主分支的合并；也支持 `$publish-merge feature dev` 这类任意分支对。仅当目标分支是仓库主分支（`main`/`master`，即发布分支）时，才在合并后自动创建递增的版本 tag（**仅本地创建，不推送远程**）；合并到其他分支（如 `develop`、`test`）一律不打 tag。当用户要求发布分支或将某分支合并到另一分支时使用。
---

# Publish Merge

## 参数与分支

无参数调用 `$publish-merge` 时使用：

- 源分支：`dev` (如果是`*` 则是当前分支 比如 `$publish-merge * dev` 就是操作当前分支到dev分支 )
- 目标分支：仓库默认分支，优先识别 `main`，其次识别 `master`
- 远程：`origin`

也可以使用 `$publish-merge dev main` 显式指定源分支和目标分支。先从仓库配置和已有文档确认实际名称，不能静默猜测错误分支。

典型的两阶段发布：

```text
$publish-merge * develop     # 开发环境 → 测试环境（目标非主分支，不打 tag）
$publish-merge develop master # 测试环境 → 主分支发布（自动打递增 tag）
$publish-merge develop master --prefix ieioms  # 打 ieioms-v0.0.x 系列的 tag
```

| 参数 | 作用 |
| ---- | ---- |
| `--push-origin` | 合并前先把源分支推送到远程。不传且源分支领先远程时，停下询问用户是否推送 |
| `--no-tag` | 跳过合并后的自动打 tag（自动打 tag 只在目标分支为主分支时才会发生） |
| `--prefix <前缀>` | tag 加前缀：`--prefix ieioms` → `ieioms-v0.0.1`。不同前缀是各自独立的版本序列，互不干扰 |

## 执行流程

> 不传 `--push-origin` 时不要推送源分支。

1. 阅读仓库根目录及相关目录中的 `AGENTS.md`、`CONTRIBUTING.md`、README 和 Git 配置，遵守分支保护与合并约定。
2. 要求工作区干净：

   ```bash
   git status --short --branch
   git diff
   git diff --cached
   ```

   存在未跟踪改动时需要询问用户是否提交 未跟踪的文件，不要 stash、删除或覆盖改动。如果 `AGENTS.md` 文件有相关约束可直接根据 `AGENTS.md` 文件直接执行。
   **工作区改动的提交永远发生在源分支（切分支之前）；目标分支上只会有合并提交，不会出现由工作区改动生成的普通提交。**
3. 获取远程最新状态，显式检查源分支与远程的领先/分叉情况：

   ```bash
   git fetch origin
   git rev-list --count origin/<源分支>..<源分支>   # 源分支领先远程的提交数
   git rev-list --count <源分支>..origin/<源分支>   # 远程领先源分支的提交数
   ```

   注意：`git pull --ff-only` **拦不住**「源分支本地领先」的情况（实测输出 `Already up to date.` 且退出码为 0），必须用 `rev-list` 显式计数，不要依赖 pull 的结果做判断。

   - 远程领先或已分叉：停止并报告，不要尝试合并未知版本。
   - 源分支领先（有未推送提交）：传了 `--push-origin` 就先 `git push origin <源分支>`；没传就停下询问用户是否推送，不要自行决定。
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
7. **创建版本 tag（不推送）**——**仅当目标分支是仓库主分支（`main` 或 `master`）时才执行这一步**。合并到其他分支（`develop`、`test` 等，例如发布到测试环境）**一律不打 tag**：版本号只用来标记真正进入主分支的发布，不能被中间环节的合并撑爆。未指定 `--no-tag` 且目标为主分支时，在合并推送成功后、切回源分支之前，在刚推送的合并提交上打 tag。本 skill 面向纯 Git 环境，不依赖任何托管平台，tag 规则自包含（patch 递增、annotated）：

   tag 名 = `<前缀>-v<主>.<次>.<修订>`；未传 `--prefix` 时就是 `v<主>.<次>.<修订>`。**不同前缀是各自独立的版本序列**：`ieioms-v0.0.2` 与 `v0.0.5` 互不干扰、各自递增。查“该系列最新一个”必须带前缀过滤，**不能全库取最新**（实测混排时不同前缀交错，全局最新是错误语义）：

   ```bash
   # 无前缀系列
   LATEST=$(git tag --list 'v[0-9]*' --sort=-v:refname \
     | grep -E '^v[0-9]+(\.[0-9]+)+$' | head -1)

   # --prefix ieioms（前缀系列，其余前缀同理）
   LATEST=$(git tag --list 'ieioms-v[0-9]*' --sort=-v:refname \
     | grep -E '^ieioms-v[0-9]+(\.[0-9]+)+$' | head -1)
   ```

   - 该系列没有任何 tag → 从 `<前缀>-v0.0.1`（无前缀则 `v0.0.1`）开始；**其他系列的 tag 不影响起步**。
   - 已有 → 取该系列**版本序最新**的一个，patch 位加一：`ieioms-v0.0.1 → ieioms-v0.0.2`、`ieioms-v0.1.9 → ieioms-v0.1.10`。
   - 必须叠加 `grep -E` 纯数字点分过滤：只按 `--sort=-v:refname` 取最新会被 `ieioms-v2-alpha` 这类 tag 干扰（实测它反而排在最前）。
   - 前缀只允许字母、数字、连字符，不要以 `-` 结尾（模板是 `<前缀>-v…`，前缀带 `-` 会产生双连字符）。
   - 版本部分的 `v` 必须**小写**：git 通配匹配区分大小写（实测 `v*` 不匹配 `V0.0.1`），仓库若有按 `v*` 匹配 tag 的流水线，大写 tag 不会被命中。

   ```bash
   git tag -a <tag> -m "Release <tag>"
   ```

   - **不要推送 tag。** tag 只作为本机的发布锚点，不进入远程；因此也不会触发任何远端流水线。只有用户**明确要求**推送时才执行 `git push origin <tag>`，不要顺手推。

   - 本 skill 在纯 Git 环境（不用 GitHub）同样适用，打 tag 不依赖任何托管平台。若将来把本地 tag 手动推送到 GitHub 且仓库配置了按 `v*` 触发的 workflow，会顺带触发它们。
   - 目标 tag 已存在（本地或远程）时不覆盖、不改写，停止并报告。
8. 推送成功后切回源分支并检查状态：

   ```bash
   git switch dev
   git status --short --branch
   ```

## 异常处理

- 目标分支受保护或项目要求 Pull Request 时，不绕过规则；报告需要的后续动作。
- 发生合并冲突时不要猜测解决。执行 `git merge --abort` 恢复合并前状态，切回源分支并报告冲突文件。
- 目标分支已经包含源分支时，不创建重复合并，**也不打 tag**（没有新的发布内容可标记），确认状态后切回源分支。
- tag 已存在时停止，保留现场并报告已完成的步骤；禁止删除或改写已有 tag。tag 只创建在本地，不存在推送失败的场景。
- 任一步骤失败时停止，不自动回滚已推送的提交。

## 完成报告

报告源分支 SHA、目标分支合并 SHA、推送结果和最终当前分支；目标分支为主分支且执行了打 tag 时，同时报告**本次创建的 tag 名与指向的 SHA（仅本地，未推送）**；目标不是主分支时明确说明本次未打 tag。最终应停留在源分支。

## 与其他 skill 的配合

- 与 `plain-change-report` 配对使用：本 skill **每次合并到主分支**打一个递增 tag 作为锚点，之后用 `plain-change-report --from <上一个tag> --to <本次tag>` 生成这两个版本之间改动的通俗汇报，作为发布说明发给非技术读者（本地 tag 就够用，`--from/--to` 读的是本地 tag）。合并到测试环境等中间分支时没有锚点产生，不在此链路内。
- 注意：tag 不推送远程，只在本机生效——换机器或其他人看不到这些锚点。需要共享锚点时手动 `git push origin <tag>`。
- 本 skill 面向纯 Git 环境，与 `release-tag-push`（GitHub Actions 发布场景专用）没有依赖关系，tag 规则互不干涉。

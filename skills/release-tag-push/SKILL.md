---
name: release-tag-push
description: 在 GitHub 项目中将当前改动提交为新 commit，依据项目版本文件或已有 tag 生成下一个版本 tag，并推送当前分支和 tag。使用无参数命令 `$release-tag-push` 完成一次版本发布准备；保留必要的格式化和轻量 lint，但明确跳过本地单元测试、集成测试、E2E、完整构建及其他耗时验证。
---

# Release Tag Push

## 默认行为

只输入 `$release-tag-push`，使用当前分支和仓库默认远程 `origin`。完成以下动作：

1. 检查当前改动和项目版本规则。
2. 提交当前改动。
3. 创建新的 annotated tag。
4. 推送当前分支和 tag。

推送 tag 是真实的版本发布动作。不要等待或模拟外部构建结果，只报告 Git 操作结果。

## 验证范围

- 运行项目明确要求的格式化工具；可以运行明显快速且必要的 lint。
- 不要主动运行任何本地测试，包括单元测试、集成测试、E2E、回归测试、覆盖率和基准测试。
- 不要运行完整构建、打包、发布检查、CI 模拟或其他耗时验证，即使仓库的一般开发说明建议执行这些步骤。
- 不要调用 `npm test`、`pytest`、`cargo test`、`go test`、`mvn test`、`gradle test` 或同类测试命令。
- 完成格式化和必要的轻量检查后，直接继续 Git commit、tag 和 push，不要因缺少本地测试结果而暂停。

## 执行前检查

1. 阅读仓库根目录及相关目录中的 `AGENTS.md`、`CONTRIBUTING.md`、README、发布文档和 Git 配置，遵守项目已有约定。
2. 检查当前分支、远程和改动：

   ```bash
   git status --short --branch
   git branch --show-current
   git remote -v
   git diff
   git diff --cached
   ```

3. 当前分支必须不是 detached HEAD，工作区必须包含本次任务的改动。没有改动时不要创建空提交或只打 tag，直接报告原因。
4. 保护用户已有改动，不要使用 `reset --hard`、强制 checkout、删除未跟踪文件或未经请求的 stash。获取远程和 tag 的最新状态；如果当前分支与远程分叉，先暂停并报告。

## 确定版本号和 tag 格式

按以下优先级确定版本，不要要求用户额外传参：

1. 读取本次改动中的项目版本字段，例如 `package.json`、`pyproject.toml`、`Cargo.toml`、`pom.xml` 或项目文档；使用已经明确更新到新版本的值。
2. 如果项目没有可用版本字段，读取已有 semver tag，沿用其前缀和格式，并默认递增 patch，例如 `v1.2.3` 生成 `v1.2.4`。
3. 如果仓库文档、脚本或历史使用其他明确的 tag 规则，遵循该规则。

如果版本来源互相矛盾、没有可识别的版本规则，或目标 tag 已存在于本地/远程，停止并报告，不猜版本、不覆盖 tag。

## 提交、打 tag 和推送

1. 按“验证范围”运行必要的格式化和轻量 lint；明确跳过所有本地测试、完整构建和耗时发布检查。
2. 只暂存本次任务相关文件，查看 staged diff；不要使用 `git add -A` 混入无关文件。
3. 按项目已有提交格式创建提交。没有明确约定时使用 `chore: release <tag>`，例如 `chore: release v1.2.4`。
4. 在新 commit 上创建 annotated tag；遵循项目已有的 lightweight/annotated tag 约定，没有约定时使用：

   ```bash
   git tag -a <tag> -m "Release <tag>"
   ```

5. 先推送当前分支，再推送 tag：

   ```bash
   git push origin <current-branch>
   git push origin <tag>
   ```

   使用实际远程名和分支名，禁止强制推送或覆盖已有 tag。

## 异常处理与报告

- 提交失败、tag 创建失败或任一次 push 失败时停止，保留现场并报告已成功完成的步骤。
- 如果分支受保护或没有推送权限，不绕过规则。
- 完成后报告当前分支、commit SHA、tag 名称、tag 指向的 SHA、推送结果、执行过的格式化或轻量 lint，并明确注明本地测试已按 Skill 规则跳过。

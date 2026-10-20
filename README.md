# agent-skills

适配 **Codex**（OpenAI Codex CLI）的 agent skills 集合。通过 [Vercel Labs 的 `skills` CLI](https://github.com/vercel-labs/skills) 安装。

## 包含的 skills

| Skill | 说明 |
|-------|------|
| `subagent-driven-development` | 子代理驱动开发：每任务一个全新 implementer 子代理 + 任务后审查 + 整体审查，用 Codex 的 `spawn_agent` 工具执行 |
| `commit-push` | 将当前改动提交并推送到指定分支 |
| `publish-merge` | 将开发分支合并到主分支、推送并切回开发分支 |
| `release-tag-push` | 格式化后跳过本地测试，提交当前改动、创建版本 tag 并推送 |
| `session-handoff` | 在单仓库或多项目工作区中用一次性交接文档继续长任务 |
| `gha-docker-release` | 在 fork 中用 GitHub Actions 构建推送 Docker 镜像，tag 触发时创建 GitHub Release，并按 `--channel` 发送一封合并的结果通知（邮件/飞书；`--no-release` 可关闭 Release） |
| `plain-change-report` | 把代码改动整理成面向非技术读者的通俗中文汇报；支持未提交改动、提交区间、最近 N 次及两个 tag 之间的发布对比（--from/--to），前后端分仓/多前端共一后端时自动合并为一份报告 |

## 安装

任意位置，使用 `npx skills add`：

```bash
# 安装全部 skills 到 Codex
npx skills add starofkuku/agent-skills -a codex

# 只安装某个 skill
npx skills add starofkuku/agent-skills --skill subagent-driven-development -a codex

# 只安装提交推送 skill
npx skills add starofkuku/agent-skills --skill commit-push -a codex

# 只安装合并发布 skill
npx skills add starofkuku/agent-skills --skill publish-merge -a codex

# 只安装版本 tag 推送 skill
npx skills add starofkuku/agent-skills --skill release-tag-push -a codex

# 只安装会话交接 skill
npx skills add starofkuku/agent-skills --skill session-handoff -a codex

# 只安装 GitHub Actions 镜像发布 skill
npx skills add starofkuku/agent-skills --skill gha-docker-release -a codex

# 只安装通俗改动汇报 skill
npx skills add starofkuku/agent-skills --skill plain-change-report -a codex

# 全局安装（到 ~/.codex/skills）
npx skills add -g starofkuku/agent-skills --skill subagent-driven-development -a codex
```

安装后：
- 默认安装到当前项目 `./.agents/skills/`
- 加 `-g` 全局安装到 `~/.codex/skills/`

## 前置条件

- Codex CLI（含多代理能力）
- 建议启用 V2：`[features.multi_agent_v2] enabled = true`

## 目录结构

```
skills/
├── subagent-driven-development/
│   ├── SKILL.md                  # 主文件（触发描述 + 流程）
│   ├── implementer-prompt.md     # implementer 子代理提示模板
│   └── task-reviewer-prompt.md   # reviewer 子代理提示模板
├── commit-push/
│   ├── SKILL.md                  # 提交并推送指定分支
│   └── agents/openai.yaml        # Codex UI 元数据
├── publish-merge/
│   ├── SKILL.md                  # 合并主分支并推送
│   └── agents/openai.yaml        # Codex UI 元数据
├── release-tag-push/
│   ├── SKILL.md                  # 提交、打 tag 并推送版本
│   └── agents/openai.yaml        # Codex UI 元数据
├── session-handoff/
│   ├── SKILL.md                  # 创建或读取本地会话交接
│   └── agents/openai.yaml        # Codex UI 元数据
├── gha-docker-release/
│   ├── SKILL.md                  # 镜像构建推送与合并结果通知
│   ├── agents/openai.yaml        # Codex UI 元数据
│   └── references/
│       ├── credentials.md        # 组织级 Variables/Secrets（含飞书机器人）
│       └── workflow-templates.md # 可复制的 workflow 模板（含通知合并与飞书签名）
└── plain-change-report/
    ├── SKILL.md                  # 改动通俗汇报（未提交/区间/指定提交）
    ├── agents/openai.yaml        # Codex UI 元数据
    └── references/
        ├── plain-language.md     # 代码改动 → 通俗表达的对照表
        └── git-ranges.md         # 各汇报范围的命令、边界与多仓库规则
```

## 本地开发

```bash
# 列出本地 skills
npx skills list ./agent-skills

# 预览某个 skill 生成的 prompt
npx skills use ./agent-skills --skill subagent-driven-development
```

在 Codex 中安装后，可以直接输入以下命令，不需要额外的自然语言描述：

```text
$commit-push dev
$publish-merge
$release-tag-push
$session-handoff
$gha-docker-release
$plain-change-report
```

`$commit-push dev` 提交并推送 `dev`；`$publish-merge` 将 `dev` 合并到主分支、推送并切回 `dev`；`$release-tag-push` 提交当前改动、创建版本 tag 并推送；`$session-handoff` 在旧会话生成交接，在 `/new` 后再次调用即可恢复任务并删除已消费的交接文件。

`$session-handoff` 不要求当前目录是 Git 仓库。对于包含多个子项目的聚合目录，它只核验当前任务涉及的路径和仓库。

`$gha-docker-release` 用于 fork 场景下的镜像发布：组织级 Variables/Secrets（含 `DOCKERHUB_USERNAME`、`DOCKERHUB_ACCESSTOKEN`）、镜像构建推送、GitHub Release 创建，以及发布结果通知。通知渠道由 `--channel` 指定，默认 `email`：`$gha-docker-release --channel feishu` 只发飞书机器人，`$gha-docker-release --channel email,feishu` 两种都发。一次发布（一次 run）只发一封通知，正文汇总该 run 内全部 job 的结果。`v*` tag 推送时**默认创建 GitHub Release**（自动生成说明，可重复执行不会报已存在）；`--no-release` 显式关闭；分支上手动触发只构建推送不建 Release。

`$plain-change-report` 把工作区里未提交的改动整理成一份**不懂技术的人也能看懂**的中文汇报：按「新增功能 / 问题修复 / 体验优化 / 其他调整」分类，每条标注业务模块，末尾给出「需要留意」的上线关注点。报告写入仓库根目录的 `CHANGE-REPORT.local.md`（自动加入 `.git/info/exclude`，不会误提交），同时在对话里输出一份。它只读不改，不会提交或修改代码。

汇报范围可由参数指定：无参数为未提交的改动；`--since v1.1.0` 汇报自某版本/提交以来；`--from v0.0.1 --to v0.0.2` 汇报**两次发布之间**的净变化（`--to` 可省略，缺省取版本序最新的 `v*` tag），配合 `publish-merge` 的自动 tag 可直接生成这次发布的通俗说明；`--commits a1b2c3d e4f5a6b` 汇报指定的几次提交；`--last 5` 汇报最近 5 次提交；`--repo admin-front,backend` 限定只看哪几个仓库。总结多次提交时只写**最终结果**（净变化），中途加过又删掉的内容不会出现在报告里。

**前后端分仓或多前端共用一个后端时**，在共同父目录调用即可：skill 会自动发现子目录里的各仓库，未提交模式只纳入有改动的仓库，并把同一个功能在前后端的改动合并成一条——报告里不出现仓库/前端/后端这些词，读者看到的仍是一份按功能分类的说明。想跨仓库汇报必须在共同父目录调用；在单个仓库内部调用时只看该仓库。

## License

Apache-2.0

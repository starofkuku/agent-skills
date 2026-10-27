# Repository Guidelines

## 项目性质

本仓库是**适配 Codex（OpenAI Codex CLI）的 agent skills 集合**，不是可编译应用：没有源码目录、构建产物和自动化测试。仓库由 [Vercel Labs 的 `skills` CLI](https://github.com/vercel-labs/skills) 发现和安装，远程仓库为 `starofkuku/agent-skills`。

一切改动都是 Markdown / YAML 文本改动，验证手段是 CLI 发现结果与人工阅读。

## 目录结构与组织

```text
README.md                    # 安装说明 + skills 清单（中文）
AGENTS.md                    # 本文件
skills/<skill-name>/         # 每个 skill 一个 kebab-case 目录
├── SKILL.md                 # 必需：frontmatter(name, description) + 流程
├── agents/openai.yaml       # Codex UI 元数据（display_name / short_description / default_prompt）
├── references/*.md          # 可选：按需加载的细节文档或可复制模板
└── scripts/                 # 可选：skill 依赖的脚本（纯标准库、无网络，如 ai-memory-rescue-session/scripts/extract.py）
tmpmd/                       # 本地草稿，已被 .gitignore 忽略，永不提交
```

- 每个 skill 的 `SKILL.md` 是唯一入口，其余文件都是按需补充的模板或参考。
- 当前 skills：`subagent-driven-development`（含 `implementer-prompt.md`、`task-reviewer-prompt.md`）、`commit-push`、`publish-merge`、`release-tag-push`、`session-handoff`、`gha-docker-release`（含 `references/`）、`plain-change-report`（含 `references/`）、`ai-memory-rescue-session`（含 `scripts/extract.py`）。
- 新增或重命名 skill 后，必须同步更新 `README.md` 的清单表格、安装示例和目录结构图。

## 验证命令

无编译步骤。从仓库**父目录**执行（或把 `./agent-skills` 换成实际路径）：

```bash
npx skills list ./agent-skills
npx skills use ./agent-skills --skill subagent-driven-development
npx skills add -g starofkuku/agent-skills --skill <skill-name> -a codex
```

改动 `SKILL.md` 后至少跑一次 `npx skills list` 确认可发现；涉及 prompt 生成逻辑时再跑 `npx skills use` 阅读生成结果。仓库未配置 formatter / linter，不要为此新增工具链。

## 写作与命名规范

- `SKILL.md` frontmatter 只保留 `name` 和 `description`，不添加额外字段。
- `description` 必须写清**触发场景**（何时该用），因为它是 skill 被自动选中的唯一依据。
- 目录名使用 lowercase kebab-case；入口文件固定大写 `SKILL.md`；其余支撑文档用小写描述性文件名。
- 正文沿袭现有风格：中文说明、英文标识符/命令/日志保持原样、短段落、用 fenced code block 承载命令与流程。
- 写作要可操作、避免重复描述；同一规则只在一个文件陈述，并在 `SKILL.md` 中说明其存在。
- 保持职责单一：一个 skill 只做一件事，需要更细步骤时拆到 `references/`，不要堆进 `SKILL.md`。

## Skill 编写注意事项

- 修改模板（implementer / reviewer / workflow 模板）时必须保留 skill 的触发描述与流程边界，并让 `SKILL.md` 与模板保持同步。
- 若 skill 引入特殊处理规则（例如跳过本地测试、非 Git 目录可用、参数约定），必须在 `SKILL.md` 中写明，不能只写在模板里。
- 参数约定要被显式记录，例如 `$commit-push dev`、`$publish-merge dev main`、`$publish-merge * dev` 中 `*` 表示当前分支。

## 提交规范

使用简短的 Conventional Commit 前缀，例如 `feat:`、`fix:`、`docs:`、`chore:`，格式为 `<type>: <imperative summary>`，一次提交只做一件事。

```text
feat: add gha-docker-release skill
docs: clarify installation
chore: ignore tmpmd directory
```

不要把 `tmpmd/` 或任何临时草稿提交进仓库。

# agent-skills

适配 **Codex**（OpenAI Codex CLI）的 agent skills 集合。通过 [Vercel Labs 的 `skills` CLI](https://github.com/vercel-labs/skills) 安装。

## 包含的 skills

| Skill | 说明 |
|-------|------|
| `subagent-driven-development` | 子代理驱动开发：每任务一个全新 implementer 子代理 + 任务后审查 + 整体审查，用 Codex 的 `spawn_agent` 工具执行 |

## 安装

任意位置，使用 `npx skills add`：

```bash
# 安装全部 skills 到 Codex
npx skills add starofkuku/agent-skills -a codex

# 只安装某个 skill
npx skills add starofkuku/agent-skills --skill subagent-driven-development -a codex

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
└── subagent-driven-development/
    ├── SKILL.md                  # 主文件（触发描述 + 流程）
    ├── implementer-prompt.md     # implementer 子代理提示模板
    └── task-reviewer-prompt.md   # reviewer 子代理提示模板
```

## 本地开发

```bash
# 列出本地 skills
npx skills list ./agent-skills

# 预览某个 skill 生成的 prompt
npx skills use ./agent-skills --skill subagent-driven-development
```

## License

Apache-2.0

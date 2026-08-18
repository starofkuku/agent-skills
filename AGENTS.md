# Repository Guidelines

## Project Structure & Module Organization

This repository contains Codex agent skills rather than an application. The root `README.md` documents installation and local usage. Each skill lives in `skills/<skill-name>/` and should contain a required `SKILL.md` plus any focused supporting templates or references. For example, `skills/subagent-driven-development/` contains the skill definition and separate implementer and reviewer prompt templates. There are currently no source-code, asset, or automated-test directories.

## Build, Test, and Development Commands

There is no compilation step. Use the Vercel `skills` CLI to validate discovery and generated prompts:

```bash
npx skills list ./agent-skills
npx skills use ./agent-skills --skill subagent-driven-development
```

Run these commands from the repository's parent directory, or replace `./agent-skills` with the repository path. Review Markdown changes directly and check that the README's installation examples remain accurate.

## Coding Style & Naming Conventions

Write clear Markdown with descriptive `#`/`##` headings, short paragraphs, and fenced code blocks for commands. Keep `SKILL.md` frontmatter valid and limited to the required `name` and `description` metadata. Use lowercase kebab-case for skill directories (for example, `subagent-driven-development`); use uppercase `SKILL.md` and descriptive lowercase filenames for supporting documents. Keep instructions operational, avoid duplicate guidance, and update the README when adding or renaming a skill. No formatter or linter is configured.

## Testing Guidelines

No automated framework or coverage threshold is configured. Every skill change should be checked with `npx skills list` and, when prompt behavior changes, `npx skills use`. Also inspect the resulting Markdown for valid frontmatter, accurate paths, and consistent examples.

## Commit & Pull Request Guidelines

Recent history uses concise Conventional Commit-style prefixes such as `feat:` and `docs:` (for example, `docs: clarify installation`). Follow `<type>: <imperative summary>` and keep each commit focused. Pull requests should explain the skill or documentation behavior changed, identify affected paths, link a related issue when one exists, and list the validation commands run. Include rendered-output screenshots only when a documentation presentation change makes them useful.

## Skill Authoring Notes

Preserve the skill's activation description and workflow boundaries when editing templates. If a skill introduces special handling rules, document them in its `SKILL.md` and keep related prompt templates synchronized.

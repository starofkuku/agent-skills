---
name: gha-docker-release
description: 在 fork 的 GitHub 仓库中用 GitHub Actions 构建并推送 Docker 镜像，复用组织级 Variables 和 Secrets，并在发布结束后发送结果邮件。适用于配置或修复镜像构建、Docker Hub 登录推送、tag 触发发布、workflow 结果通知等任务。
---

# GitHub Actions Docker Release

## 目标

在 fork 中建立一条可验证的发布链路：

```text
tag 推送或手动触发 → 构建 Docker 镜像 → 登录 Docker Hub 并推送 → 发送结果邮件
```

动手前先确认三件事，缺一不可：

1. fork 归属。组织级 Variables/Secrets 只对该组织下、且被授权访问的仓库可见；上游仓库的 secrets 不会复制到 fork。
2. 目标 registry 与镜像仓库名，默认 Docker Hub 的 `<DOCKERHUB_USERNAME>/<image>`。
3. 触发方式，默认 `v*` tag 推送加 `workflow_dispatch`。

沿仓库既有约定（`AGENTS.md`、已有 workflow、命名习惯）落地。不要顺手改动与本发布链路无关的 workflow、业务代码或仓库设置。

## 凭据模型

两类配置不要混用：

- Actions **Variables**（`vars.*`）：非敏感值，如 `SMTP_HOST`、`SMTP_PORT`、`DOCKERHUB_USERNAME`。
- Actions **Secrets**（`secrets.*`）：敏感值，如 `SMTP_PASSWORD`、`NOTIFY_EMAIL_TO`、`DOCKERHUB_ACCESSTOKEN`。

关键约束：

- `DOCKERHUB_ACCESSTOKEN` 是 Docker Hub Personal Access Token，不是账号密码；推送镜像需要 Read & Write 权限。
- 登录统一走 `docker/login-action`，密码只经 `secrets.*` 注入。不要 echo secrets，不要写入镜像、构建参数或日志。
- 不要把 secrets 暴露给来自 fork 的 `pull_request` 事件。需要 secrets 的构建只应在 `push` tag、`workflow_dispatch` 或受信任分支上运行。
- `GITHUB_TOKEN` 由 Actions 自动提供，不需要手动创建；只有创建 GitHub Release 时才需要 `permissions: contents: write`。

完整变量清单、组织级配置步骤和 fork 注意事项见 [references/credentials.md](references/credentials.md)。

## Workflow 结构

没有既有约定时按以下方式组织：

- `.github/workflows/release.yml`：由 `v*` tag 和 `workflow_dispatch` 触发，构建并推送镜像，最后一个 job 发送结果邮件。
- 其他需要通知的 workflow（例如只发前端产物的）：各自追加一个 notify job。只配置好 Variables 和 Secrets 不会自动发邮件。

可直接复制的 YAML 模板见 [references/workflow-templates.md](references/workflow-templates.md)。

notify job 必须满足：

- `needs` 列出该 workflow 中全部发布 job，否则会提前结束。
- 使用 `if: always()`，前置 job 失败时仍发送结果。
- 正文逐项引用 `needs.<job>.result`，让邮件能区分成功、失败和取消。
- 每个 job 只申请所需的最小 `permissions`。

## 验证

1. 先用 `workflow_dispatch` 手动跑一次，再验证 `v*` tag 触发路径。
2. 在 Actions 页面确认构建推送 job 与 `Email workflow result` job 都执行，且邮件正文状态与实际结果一致。
3. 在 Docker Hub 对应仓库的 tags 页面确认镜像已推送，tag 与触发版本一致。

失败时按以下顺序定位：

| 现象 | 优先检查 |
| ---- | -------- |
| 变量或 secrets 取值为空 | 组织级配置是否授权给该仓库；fork 是否属于该组织 |
| `denied: requested access to the resource is denied` | `DOCKERHUB_ACCESSTOKEN` 权限、镜像仓库名、账号对该仓库的写权限 |
| 登录成功但推送失败 | 镜像名是否缺少 `<DOCKERHUB_USERNAME>/` 前缀 |
| 邮件未发送 | 该 workflow 是否真的包含 notify job；job 名称是否与 `needs` 一致 |
| 邮件发送失败 | SMTP host/port、App Password、`SMTP_FROM` 是否与登录账号一致 |

不要把“已配置好 Variables 和 Secrets”当作发布链路已验证。

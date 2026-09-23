---
name: gha-docker-release
description: 在 fork 的 GitHub 仓库中用 GitHub Actions 构建并推送 Docker 镜像，复用组织级 Variables 和 Secrets，并在发布结束后发送一封合并的结果通知（邮件或飞书机器人）。适用于配置或修复镜像构建、Docker Hub 登录推送、tag 触发发布、workflow 结果邮件/飞书通知等任务。
---

# GitHub Actions Docker Release

## 参数

`--channel` 指定通知渠道，逗号分隔，**默认 `email`**：

| 调用 | 通知渠道 |
| ---- | -------- |
| `$gha-docker-release` | 邮件 |
| `$gha-docker-release --channel feishu` | 飞书机器人 |
| `$gha-docker-release --channel email,feishu` | 邮件 + 飞书 |

只为 `--channel` 指定的渠道生成 notify step，未指定的渠道不要生成。渠道不改变其余行为。

## 目标

在 fork 中建立一条可验证的发布链路：

```text
tag 推送或手动触发 → 构建 Docker 镜像 → 登录 Docker Hub 并推送 → 发送结果通知（邮件 / 飞书）
```

动手前先确认三件事，缺一不可：

1. fork 归属。组织级 Variables/Secrets 只对该组织下、且被授权访问的仓库可见；上游仓库的 secrets 不会复制到 fork。
2. 目标 registry 与镜像仓库名，默认 Docker Hub 的 `<DOCKERHUB_USERNAME>/<image>`。
3. 触发方式，默认 `v*` tag 推送加 `workflow_dispatch`。

沿仓库既有约定（`AGENTS.md`、已有 workflow、命名习惯）落地。不要顺手改动与本发布链路无关的 workflow、业务代码或仓库设置。

## 凭据模型

两类配置不要混用：

- Actions **Variables**（`vars.*`）：非敏感值，如 `SMTP_HOST`、`SMTP_PORT`、`DOCKERHUB_USERNAME`。
- Actions **Secrets**（`secrets.*`）：敏感值，如 `SMTP_PASSWORD`、`NOTIFY_EMAIL_TO`、`DOCKERHUB_ACCESSTOKEN`、`FEISHU_WEB_HOOK`、`FEISHU_SIGN`。

关键约束：

- `DOCKERHUB_ACCESSTOKEN` 是 Docker Hub Personal Access Token，不是账号密码；推送镜像需要 Read & Write 权限。
- 登录统一走 `docker/login-action`，密码只经 `secrets.*` 注入。不要 echo secrets，不要写入镜像、构建参数或日志。
- 不要把 secrets 暴露给来自 fork 的 `pull_request` 事件。需要 secrets 的构建只应在 `push` tag、`workflow_dispatch` 或受信任分支上运行。
- `FEISHU_SIGN` 存的是飞书机器人后台的**签名密钥**，不是要发送的 `sign` 字段。`sign` 每次发送前用 `HMAC-SHA256` 现算，固定值发过去会被判签名失败。
- `GITHUB_TOKEN` 由 Actions 自动提供，不需要手动创建；只有创建 GitHub Release 时才需要 `permissions: contents: write`。

完整变量清单、组织级配置步骤和 fork 注意事项见 [references/credentials.md](references/credentials.md)。

## Workflow 结构

没有既有约定时按以下方式组织：

- `.github/workflows/release.yml`：由 `v*` tag 和 `workflow_dispatch` 触发，构建并推送镜像，最后一个 job 发送结果通知。
- 其他需要通知的 workflow（例如只发前端产物的）：各自追加**一个** notify job。只配置好 Variables 和 Secrets 不会自动发通知。

可直接复制的 YAML 模板见 [references/workflow-templates.md](references/workflow-templates.md)。

### 通知必须合并成一封

一次发布（一次 run）只发一封通知，把该 run 内所有 job 的结果汇总进去。为此 notify job 必须满足：

- **一个 workflow 只允许一个 notify job。** 给每个发布 job 各挂一个通知 job，就会变成一次发布发多封，禁止这样写。
- **`needs` 必须列出该 workflow 的全部发布 job。** `needs` 只包含**直接依赖**，链式依赖（A → B → C）里只写 C 拿不到 A、B 的结果。漏写的 job 不会报错，只会让通知里静默少一项——这是本方案唯一的静默故障点，改 workflow 时必须同步维护 `needs`。
- 正文用 `toJSON(needs)` 自动列出全部 job 的 `result`，不要手写逐项，避免新增 job 时漏改正文。
- 每个渠道各占一个 step，但共用同一份汇总正文，不要在各自的 step 里重复拼一遍。
- 使用 `if: always()`，前置 job 失败时仍发送结果。若要「取消时不发通知」，改用 `if: ${{ !cancelled() }}`（官方推荐写法），并在文档里说明取舍。
- 每个 job 只申请所需的最小 `permissions`。

`failure` 之后的下游 job 会显示 `skipped`，这是正常现象，不是独立故障。

## 验证

1. 先用 `workflow_dispatch` 手动跑一次，再验证 `v*` tag 触发路径。
2. 在 Actions 页面确认构建推送 job 与 `Notify workflow result` job 都执行，且通知正文里每个 job 的状态与实际结果一致，没有遗漏的 job。
3. 按渠道确认通知真的送达：邮件看收件箱，飞书看群消息；飞书 step 的日志里应能看到 `HTTP 200: {"code":0,...}`。
4. 在 Docker Hub 对应仓库的 tags 页面确认镜像已推送，tag 与触发版本一致。

失败时按以下顺序定位：

| 现象 | 优先检查 |
| ---- | -------- |
| 变量或 secrets 取值为空 | 组织级配置是否授权给该仓库；fork 是否属于该组织 |
| `denied: requested access to the resource is denied` | `DOCKERHUB_ACCESSTOKEN` 权限、镜像仓库名、账号对该仓库的写权限 |
| 登录成功但推送失败 | 镜像名是否缺少 `<DOCKERHUB_USERNAME>/` 前缀 |
| 通知未发送 | 该 workflow 是否真的包含 notify job；该渠道的 step 是否被 `--channel` 保留；notify job 的 `needs` 里 job id 是否写对 |
| 邮件发送失败 | SMTP host/port、App Password、`SMTP_FROM` 是否与登录账号一致 |
| 通知里少了某个 job | 该 job 是否已加入 notify job 的 `needs`（`needs` 只覆盖直接依赖） |
| 飞书返回 `code:19021` | 签名密钥或时间窗问题：`FEISHU_SIGN` 是否为机器人后台的签名密钥；runner 时钟与标准时间偏差是否超过 1 小时 |
| 飞书返回非 0 的 `code` | 请求体字段与 `msg_type`；机器人安全设置（签名校验 / 关键词 / IP 白名单）是否与发送方式匹配 |
| 飞书通知看似「没报错但没收到」 | 飞书业务错误时 **HTTP 仍为 200**，只看 curl/HTTP 状态会漏判；必须检查响应体 `code` 是否为 0 |

不要把“已配置好 Variables 和 Secrets”当作发布链路已验证。

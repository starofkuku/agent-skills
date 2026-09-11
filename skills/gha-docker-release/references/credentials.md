# 凭据与组织级配置

在仓库或组织的 **Settings → Secrets and variables → Actions** 中配置。多个仓库共享时配置在组织级别，并把目标仓库加入可访问范围。

## Actions Variables

| Name | Example | 用途 |
| ---- | ------- | ---- |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP 服务器地址 |
| `SMTP_PORT` | `465` | SMTP 端口；当前模板使用隐式 TLS |
| `DOCKERHUB_USERNAME` | `example-org` | Docker Hub 登录用户名，同时用于拼接镜像名 |

`DOCKERHUB_USERNAME` 本身不敏感，建议放 Variables。如果组织已经把它建成了 Secret，把模板中的 `vars.DOCKERHUB_USERNAME` 改成 `secrets.DOCKERHUB_USERNAME` 即可，不要同时创建两份。

## Actions Secrets

| Name | 用途 |
| ---- | ---- |
| `DOCKERHUB_ACCESSTOKEN` | Docker Hub Personal Access Token，登录并推送镜像 |
| `SMTP_USERNAME` | SMTP 登录名，通常是完整邮箱地址 |
| `SMTP_PASSWORD` | SMTP 密码或服务商 App Password |
| `SMTP_FROM` | 发件地址，通常与登录账号一致 |
| `NOTIFY_EMAIL_TO` | 收件地址；action 支持时可用逗号分隔多个 |

`GITHUB_TOKEN` 由 GitHub Actions 自动注入，不需要手动创建。

## Docker Hub Access Token

1. 登录 Docker Hub，进入 **Account settings → Personal access tokens**。
2. 新建 token，权限选择 **Read & Write**（只读 token 无法推送镜像）。
3. 把生成的 token 存为 `DOCKERHUB_ACCESSTOKEN`。token 只在创建时显示一次，丢失后需要重建。
4. 若镜像推送到组织命名空间，确认该账号属于对应团队且拥有写权限。

不要用 Docker Hub 账号密码代替 access token：启用 2FA 后密码无法用于登录，且 token 可单独撤销和限制权限。

## Gmail 邮件配置

1. 为发送账号启用两步验证。
2. 创建 Google App Password，把它作为 `SMTP_PASSWORD`，不要使用 Google 账号主密码。
3. `SMTP_FROM` 与 `SMTP_USERNAME` 一般是同一个地址，否则部分 SMTP 服务会拒绝发信。

## 组织级配置与 fork 注意事项

- 组织级 Variables/Secrets 需要显式授权给仓库；未加入可访问范围的仓库读到的值为空。
- 上游仓库的 secrets 不会随 fork 复制。fork 若不在该组织下，就必须在 fork 自己的仓库设置里单独配置。
- 同一名称的仓库级配置会覆盖组织级配置。排查取值为空时，先确认实际生效的层级。
- fork 的 Actions 默认可能处于未启用状态；首次运行前需在 Actions 页面启用，必要时确认 workflow 运行许可。
- 不要把 secrets 传给由 fork 的 `pull_request` 事件触发的 job，也不要使用 `pull_request_target` 检出并执行未审查的 fork 代码。
- secrets 不会自动脱敏所有输出。避免 `set -x`、`docker build --build-arg` 或日志打印凭据。

## 轮换与最小权限

- Docker Hub token 泄露或人员变动时立即撤销并重新生成，然后更新组织级 Secret。
- 只授予推送所必需的 Read & Write，不授予账号级管理权限。
- 收件地址、SMTP 主机等非敏感配置优先放 Variables，减少 Secret 数量。

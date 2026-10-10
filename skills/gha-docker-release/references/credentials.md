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
| `FEISHU_WEB_HOOK` | 飞书自定义机器人的 Webhook 地址，形如 `https://open.feishu.cn/open-apis/bot/v2/hook/<uuid>` |
| `FEISHU_SIGN` | 飞书机器人安全设置里的**签名密钥**，用于现算 `sign` |

只有被 `--channel` 选中的渠道，对应的 Secrets 才是必需：只发邮件不需要 `FEISHU_*`，只发飞书不需要 `SMTP_*` / `NOTIFY_EMAIL_TO`。

`GITHUB_TOKEN` 由 GitHub Actions 自动注入，不需要手动创建。创建 GitHub Release 用的就是它：release job 单独声明 `permissions: contents: write`，不要把写权限放宽到整个 workflow。

## Docker Hub Access Token

1. 登录 Docker Hub，进入 **Account settings → Personal access tokens**。
2. 新建 token 时在 **Access permissions** 里勾选 **Write**（推送镜像必需）；需要拉取再加 `Read`；`Delete` 不要勾选。
   注意现在的权限是 `Read` / `Write` / `Delete` 三个**独立勾选**项，旧版下拉框里的 "Read-only" / "Read & Write" 档位已经不存在，不要在界面上找它们。
3. 把生成的 token 存为 `DOCKERHUB_ACCESSTOKEN`。token 只在创建时显示一次，丢失后需要重建。
4. 若镜像推送到组织命名空间，确认该账号属于对应团队且拥有写权限。

不要用 Docker Hub 账号密码代替 access token：启用 2FA 后密码无法用于登录，且 token 可单独撤销和限制权限。

## Gmail 邮件配置

1. 为发送账号启用两步验证。
2. 创建 Google App Password，把它作为 `SMTP_PASSWORD`，不要使用 Google 账号主密码。
3. `SMTP_FROM` 与 `SMTP_USERNAME` 一般是同一个地址，否则部分 SMTP 服务会拒绝发信。

## 飞书机器人配置

1. 在目标群聊里添加 **自定义机器人**（群设置 → 群机器人 → 添加机器人）。
2. 复制生成的 Webhook 地址，存为 `FEISHU_WEB_HOOK`。地址里包含 token，属凭据，**放 Secret 而不是 Variable**。
3. 安全设置选 **签名校验**，复制签名密钥存为 `FEISHU_SIGN`。本 skill 的模板按签名校验实现；若机器人改用其他安全设置（如关键词或 IP 白名单），需要相应调整发送逻辑，模板不覆盖。
4. 消息会发到机器人所属的群；需要迁到另一个群时，在新群里重新添加机器人并更新 `FEISHU_WEB_HOOK`。
5. 国际版 Lark 的域名是 `open.larksuite.com`（飞书为 `open.feishu.cn`），除域名外流程相同。

### 签名机制（模板已实现，改脚本时别改错）

- 待签名字符串为 `<timestamp>\n<secret>`，`timestamp` 是**秒级** Unix 时间戳。
- `sign = base64(HMAC-SHA256(key = 待签名字符串, message = 空))`。注意 **key 是「时间戳 + 换行 + 密钥」、message 为空**，与习惯上的「key = 密钥、message = 内容」相反；写反了会直接签名失败。
- `FEISHU_SIGN` 存的是**长期不变的签名密钥**。`sign` 必须每次都现算，不能把一次算出来的 `sign` 当成固定值存进 Secret。
- 请求体：`{"timestamp": "<秒级>", "sign": "<base64>", "msg_type": "text", "content": {"text": "..."}}`。
- `timestamp` 与飞书服务器时间偏差超过 **1 小时**会被拒，错误信息为 `sign match fail or timestamp is not within one hour from current time`；runner 时钟不准会直接发送失败。
- **业务错误时 HTTP 状态仍是 200**，响应体形如 `{"code":19021,"msg":"..."}`。判定成功必须看 `code == 0`，不能只看 HTTP 状态或 curl 退出码。
- 本模板每次 run 只发一条汇总消息（见 `SKILL.md` 的「通知必须合并成一封」）。

## 组织级配置与 fork 注意事项

- 组织级 Variables/Secrets 需要显式授权给仓库；未加入可访问范围的仓库读到的值为空。
- 上游仓库的 secrets 不会随 fork 复制。fork 若不在该组织下，就必须在 fork 自己的仓库设置里单独配置。
- 同一名称的仓库级配置会覆盖组织级配置。排查取值为空时，先确认实际生效的层级。
- fork 的 Actions 默认可能处于未启用状态；首次运行前需在 Actions 页面启用，必要时确认 workflow 运行许可。
- 不要把 secrets 传给由 fork 的 `pull_request` 事件触发的 job，也不要使用 `pull_request_target` 检出并执行未审查的 fork 代码。
- secrets 不会自动脱敏所有输出。避免 `set -x`、`docker build --build-arg` 或日志打印凭据。

## 轮换与最小权限

- Docker Hub token 泄露或人员变动时立即撤销并重新生成，然后更新组织级 Secret。
- 只勾选推送所必需的 `Write`，需要拉取时再加 `Read`；不要勾选 `Delete`。
- 收件地址、SMTP 主机等非敏感配置优先放 Variables，减少 Secret 数量。

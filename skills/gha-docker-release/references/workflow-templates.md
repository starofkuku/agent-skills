# Workflow 模板

按仓库实际技术栈调整 `context`、`file` 和镜像名。模板假设版本 tag 形如 `v1.2.3`。

通知渠道由 `--channel` 决定：保留对应渠道的 step，删掉未指定的渠道 step（见「通知渠道」）。

## release.yml

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

permissions:
  contents: read

jobs:
  docker:
    name: Build and push image
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ vars.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_ACCESSTOKEN }}

      - name: Derive image tags
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ vars.DOCKERHUB_USERNAME }}/example-image
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,format=short
            type=raw,value=latest,enable=${{ github.ref_type == 'tag' }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # 一个 workflow 只能有这一个通知 job；所有发布 job 都汇总到这里
  notify:
    name: Notify workflow result
    needs: [docker]
    if: ${{ always() }}
    runs-on: ubuntu-latest
    steps:
      # 汇总正文只算一次，各渠道共用
      - name: Build result summary
        id: summary
        env:
          NEEDS_JSON: ${{ toJSON(needs) }}
          REPO: ${{ github.repository }}
          REF: ${{ github.ref_name }}
          SHA: ${{ github.sha }}
        run: |
          python3 - <<'PY' >> "$GITHUB_OUTPUT"
          import json, os

          needs = json.loads(os.environ["NEEDS_JSON"])
          results = [info.get("result", "unknown") for info in needs.values()]
          if "failure" in results:
              overall = "failure"
          elif "cancelled" in results:
              overall = "cancelled"
          else:
              overall = "success"

          lines = [
              f"[{os.environ['REPO']}] {os.environ['REF']} - {overall}",
              "",
              f"Repository: {os.environ['REPO']}",
              f"Ref: {os.environ['REF']}",
              f"Commit: {os.environ['SHA']}",
              "",
              "Jobs:",
          ]
          lines += [f"- {job}: {info.get('result', 'unknown')}" for job, info in needs.items()]

          print("text<<SUMMARY_EOF")
          print("\n".join(lines))
          print("SUMMARY_EOF")
          PY

      # --channel 不含 email 时删除此 step
      - name: Notify by email
        uses: dawidd6/action-send-mail@v6
        with:
          server_address: ${{ vars.SMTP_HOST }}
          server_port: ${{ vars.SMTP_PORT }}
          secure: true
          username: ${{ secrets.SMTP_USERNAME }}
          password: ${{ secrets.SMTP_PASSWORD }}
          from: ${{ secrets.SMTP_FROM }}
          to: ${{ secrets.NOTIFY_EMAIL_TO }}
          subject: "[${{ github.repository }}] release ${{ github.ref_name }}"
          body: ${{ steps.summary.outputs.text }}

      # --channel 不含 feishu 时删除此 step
      - name: Notify by Feishu
        env:
          FEISHU_WEB_HOOK: ${{ secrets.FEISHU_WEB_HOOK }}
          FEISHU_SIGN: ${{ secrets.FEISHU_SIGN }}
          SUMMARY: ${{ steps.summary.outputs.text }}
        run: |
          python3 - <<'PY'
          import base64, hashlib, hmac, json, os, sys, time, urllib.error, urllib.request

          timestamp = str(int(time.time()))
          string_to_sign = f"{timestamp}\n{os.environ['FEISHU_SIGN']}"
          sign = base64.b64encode(
              hmac.new(string_to_sign.encode(), b"", hashlib.sha256).digest()
          ).decode()

          request = urllib.request.Request(
              os.environ["FEISHU_WEB_HOOK"],
              data=json.dumps({
                  "timestamp": timestamp,
                  "sign": sign,
                  "msg_type": "text",
                  "content": {"text": os.environ["SUMMARY"]},
              }).encode(),
              headers={"Content-Type": "application/json"},
          )
          try:
              with urllib.request.urlopen(request, timeout=30) as response:
                  status, body = response.status, response.read().decode()
          except urllib.error.HTTPError as error:
              status, body = error.code, error.read().decode()

          print(f"HTTP {status}: {body}")
          code = json.loads(body).get("code")
          if code != 0:
              sys.exit(f"Feishu notify failed: code={code}, body={body}")
          PY
```

## 通知渠道

`--channel` 决定保留哪些 step，默认 `email`：

| `--channel` | notify job 内保留的 step |
| ----------- | ------------------------ |
| 不写或 `email` | `Build result summary` + `Notify by email` |
| `feishu` | `Build result summary` + `Notify by Feishu` |
| `email,feishu` | 三个 step 全保留 |

`Build result summary` 与渠道无关，任何渠道组合都要保留：多个渠道共用同一份汇总正文，不要在各自的 step 里重复拼一遍。

## 追加到其他 workflow

只配好 Variables/Secrets 不会自动发邮件或飞书。需要通知的 workflow 各自追加**一个** notify job，其余内容与 `release.yml` 的 notify job 完全一致，整段复制，不要改写：

```yaml
  notify:
    name: Notify workflow result
    needs: [publish]          # ← 只改这里：换成该 workflow 的全部发布 job
    if: ${{ always() }}
    runs-on: ubuntu-latest
    steps:
      # ← 以下 steps 与 release.yml 的 notify job 完全相同，整段复制
```

## 使用要点

- **一个 workflow 只允许一个 notify job。** 给每个 job 各挂一个通知 job，就会变成"每个任务发一封"。
- `needs` 必须列出该 workflow 的**全部**发布 job。`needs` 只包含**直接依赖**，链式依赖（A → B → C）里只写 C 拿不到 A、B 的结果；漏写的 job 不会报错，只会让通知静默少一项。
- 正文用 `toJSON(needs)` 自动生成，新增 job 只要加进 `needs` 就会自动出现在通知里。正文里显示的是 **job id**（不是 `name`），需要显示名就在汇总脚本里加一份映射。
- `failure` 之后的下游 job 会显示 `skipped`，这是正常现象，不是独立故障。
- `if: always()` 表示取消时也发通知。如果不想在取消时发通知，改用官方推荐的 `if: ${{ !cancelled() }}`。
- 各渠道 step 互相独立：默认任一渠道失败会让 notify job 失败（配置缺失会立刻暴露）。若希望某渠道失败不影响整体，单独给该 step 加 `continue-on-error: true`。
- 汇总与飞书两个 step 依赖 runner 自带的 `python3`（`ubuntu-latest` 自带；自托管 runner 需自行确认）。
- 飞书签名有 **1 小时**时间窗，runner 时钟偏差会导致签名校验失败。
- `type=raw,value=latest` 只在 tag 触发时启用，避免手动运行覆盖 `latest`。
- 需要发布 GitHub Release 时，给对应 job 单独加 `permissions: contents: write`，不要放宽整个 workflow。

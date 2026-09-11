# Workflow 模板

按仓库实际技术栈调整 `context`、`file` 和镜像名。模板假设版本 tag 形如 `v1.2.3`。

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

  notify:
    name: Email workflow result
    needs: [docker]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Send workflow result email
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
          body: |
            Repository: ${{ github.repository }}
            Ref: ${{ github.ref_name }}
            Commit: ${{ github.sha }}
            Build and push: ${{ needs.docker.result }}
```

## 追加到其他 workflow

只配好 Variables/Secrets 不会自动发邮件。需要通知的 workflow 各自追加 notify job，并把 `needs` 换成该 workflow 的真实 job 名：

```yaml
  notify:
    name: Email workflow result
    needs: [publish]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Send workflow result email
        uses: dawidd6/action-send-mail@v6
        with:
          server_address: ${{ vars.SMTP_HOST }}
          server_port: ${{ vars.SMTP_PORT }}
          secure: true
          username: ${{ secrets.SMTP_USERNAME }}
          password: ${{ secrets.SMTP_PASSWORD }}
          from: ${{ secrets.SMTP_FROM }}
          to: ${{ secrets.NOTIFY_EMAIL_TO }}
          subject: "[${{ github.repository }}] workflow result"
          body: |
            Repository: ${{ github.repository }}
            Ref: ${{ github.ref_name }}
            Commit: ${{ github.sha }}
            Result: ${{ needs.publish.result }}
```

## 使用要点

- `needs` 必须覆盖该 workflow 的全部发布 job；漏写会导致邮件在部分 job 结束前就发出。
- 必须保留 `if: always()`，否则前置 job 失败时 notify job 会被跳过。
- 多 job 时在正文逐项列出各自的 `needs.<job>.result`。
- `type=raw,value=latest` 只在 tag 触发时启用，避免手动运行覆盖 `latest`。
- 需要发布 GitHub Release 时，给对应 job 单独加 `permissions: contents: write`，不要放宽整个 workflow。

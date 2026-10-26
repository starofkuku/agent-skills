# 范围取值与命令

各汇报范围的精确命令，以及已经验证过的边界与坑。**所有命令都在仓库根目录执行**，先 `git rev-parse --show-toplevel` 确认在 Git 仓库内。

## 目录

- [通用校验](#通用校验)
- [工作区模式判定与多仓库](#工作区模式判定与多仓库)
- [未提交改动（默认）](#未提交改动默认)
- [--since](#--since)
- [--from / --to](#--from----to)
- [--mine（只总结自己的提交）](#mine只总结自己的提交)
- [--commits](#--commits)
- [--last](#--last)
- [取出净变化](#取出净变化)
- [覆盖范围那一行怎么算](#覆盖范围那一行怎么算)
- [已踩过的坑](#已踩过的坑)

## 通用校验

任何 ref（提交号、tag、分支名）都要先确认存在，再往下走：

```bash
git rev-parse --verify --quiet "<ref>^{commit}" >/dev/null || echo "ref 不存在"
```

`git rev-parse` 对不存在的 ref **退出码为 128**，而 `git log nosuchref..HEAD` 也会返回 128 —— 两者都能靠退出码判断，但**不要用管道后的 `$?`**（会被 `head`、`xargs` 之类吃掉）。直接用 `if git rev-parse --verify --quiet ...; then` 的形式。

ref 无效时**停止并告诉调用者**，不要静默退化成默认模式。

## 工作区模式判定与多仓库

把调用时的当前目录作为工作区根目录：

```bash
git rev-parse --show-toplevel        # 成功 → 单仓库模式；失败(128) → 看子目录
```

多仓库模式下找出全部子仓库（排除依赖目录，限深度防止误扫）：

```bash
find . -mindepth 2 -maxdepth 3 -name .git -not -path '*/node_modules/*' \
  | xargs -n1 dirname | sort
```

- `.git` 可能是文件（worktree、submodule），所以**不要加 `-type d`**。
- 多仓库模式下，后面所有 git 命令都要加 `git -C <repo>`。

逐仓库查未提交改动，用于自动筛选纳入清单：

```bash
for d in <仓库清单>; do
  n=$(git -C "$d" status --porcelain=v1 -uall | wc -l)
  echo "$d $n"
done
```

`--repo` 名单匹配用**目录名**（`basename "$d"`）：

```bash
basename ./admin-front        # → admin-front
```

多仓库 + 范围参数时逐仓库校验 ref，没有该 ref 的仓库跳过并把原因写进对话（前后端 tag 不同步是常态）；**全部仓库都没有该 ref 才报错停止**。报告里绝不按仓库分节，同一功能前后端的改动合并成一条，合并不了的宁可分开写。

## 未提交改动（默认）

```bash
git rev-parse --show-toplevel                  # 仓库根目录
git status --porcelain=v1 -uall                # 必须带 -uall
git diff --stat HEAD                           # 已暂存 + 未暂存，一次覆盖
git diff HEAD                                  # 上面的正文
git status --porcelain=v1 -uall | awk '/^\?\?/{print $2}'   # 未跟踪文件清单
```

- **`git diff HEAD` 同时包含已暂存和未暂存改动**：`git diff` 只看未暂存，`git diff --cached` 只看已暂存，分开跑容易漏一半。
- **`git diff HEAD` 仍然不含未跟踪文件**，新增的文件必须按清单逐个读内容。
- `-uall` 不能省：不加的话新增目录只显示成一行 `?? src/views/invoice/`，目录里的文件全部看不见。
- 删除的文件会以 `D` 出现在 `status` 里，`git diff HEAD` 也能看到，别漏。

## --since

`--since <ref>` 表示「自该 ref 以来到当前」，即 `<ref>..HEAD`：

```bash
git rev-parse --verify --quiet "<ref>^{commit}"        # 先校验
git log --oneline --no-merges "<ref>..HEAD"
git diff --stat "<ref>..HEAD"                          # 净变化
```

- `A..B` **不包含 A 自身**，只含 A 之后的提交。所以 `--since v1.1.0` 汇报的是 v1.1.0 之后发生的事，符合直觉。
- 区间为空（`ref` 就是 HEAD）时提交数为 0、diff 也为空，按「该范围内没有改动」处理。
- 用 `--since` 的**表达式**而不是 `git log --since=<日期>`：后者按**提交时间**过滤，遇到换机器、rebase、时间倒挂会漏提交，不要用。

## --from / --to

`--from <tagA> --to <tagB>` 汇报**两次发布之间**的净变化，配合 `publish-merge` 合并后自动打的递增 tag 使用（作为发布说明）。

两端都要先校验；`--to` 省略时取**与 `--from` 同前缀**的系列里最新的一个，并把实际取到的值报给调用者。先从 `--from` 识别前缀（`ieioms-v0.0.1` → `ieioms-`；`v0.0.3` → 无前缀），再在该系列内查找：

```bash
git rev-parse --verify --quiet "<from>^{commit}"
git rev-parse --verify --quiet "<to>^{commit}"

# --to 省略时：<前缀> 从 --from 识别（ieioms-v0.0.1 → 'ieioms-'；v0.0.3 → ''）
# 查找必须带前缀隔离，不能全库取最新（见坑表）
TO=$(git tag --list '<前缀>v[0-9]*' --sort=-v:refname \
  | grep -E '^<前缀>v[0-9]+(\.[0-9]+)+$' | head -1)
```

这与 `publish-merge` 打 tag 用的查找规则一致（`--prefix` 前缀系列独立递增），行为必须保持同步。

取改动（区间语义与 `--since` 相同，`A..B` 不含 A 自身）：

```bash
git log --oneline --no-merges "<from>..<to>"
git diff --stat "<from>..<to>"
```

与 `--since` 的区别：`--since X` 终点是**当前 HEAD**（含 tag 之后的新提交，进展视角）；`--from/--to` 两端都是 tag（这次发布相对上次发布变了什么，对比视角）。刚打完 tag 且 HEAD 就是该 tag 时两者结果相同，但 `--from/--to` 不会受后续新提交影响。

**边界硬规则：区间必须是 `from..to`，绝不写 `from^..to`。** `A..B` 不含 A 自身引入的改动（这是正确语义）；写成 `A^..B` 会把 from 那次发布已包含的内容全部带进报告——实测踩过的错。写报告前自查：`git log --oneline --no-merges "<from>..<to>"` 列出的最早一个提交，必须是 from **之后**的，不能属于 from 所在的那次合并。

多仓库模式：任一端点在某仓库不存在就跳过该仓库并说明（前后端 tag 不同步是常态）；全部仓库都缺同一端点才报错停止。

## --mine（只总结自己的提交）

分支里混有上游同步（merge 进来的、不是自己写的）时，tag 区间只能圈定范围、圈定不了归属，必须叠加归属过滤。

**主方案（单人开发）——按作者过滤：**

```bash
EMAIL=$(git config user.email)
# 我的提交清单
git log --oneline --no-merges --author="$EMAIL" "<区间>"
# 报告正文的取材依据：我的提交的补丁
git log -p --no-merges --author="$EMAIL" "<区间>"
# 上游提交数（供一句话带过用差值法，不要逐个读它们的 patch）
TOTAL=$(git rev-list --count --no-merges "<区间>")
MINE=$(git rev-list --count --no-merges --author="$EMAIL" "<区间>")
UPSTREAM=$((TOTAL - MINE))
```

**替代方案（团队多人，按拓扑排除）：** 上游是 merge 自某个可引用的远程分支时，可用 `^` 排除法精确圈出非上游提交（rebase/squash 同步会失效，此时只能靠作者过滤）：

```bash
git log --oneline --no-merges "<区间>" ^upstream/master
```

**取材规则：** `git diff` 无法按作者过滤，所以用了 `--mine` 后**不能拿净 diff 当正文依据**；以上面过滤后的提交补丁为准，自己的多个提交对同一处反复修改时按最终效果描述。上游部分在「其他调整」里写一句：「另含上游同步的更新，未在本报告展开」。

## --commits

`--commits a1b2c3d e4f5a6b` 指定**离散**的几次提交。这种情况**不能**用 `A..B` 区间 diff。

```bash
git log --no-walk --format='%h %ad %s' --date=short <sha1> <sha2> ...
git show <sha>                    # 逐个取该提交自己的改动
```

为什么不能退化成区间 diff：`A..B` 会把 A、B 之间**所有**提交（包括你没选中的）都算进去。举例，历史是 `A → B → C → D`，只选 A 和 D：

```bash
git diff --name-status A D
# M  a.txt     ← 来自未选中的 B
# A  c.txt     ← 来自未选中的 C
```

未选中的改动被算进了报告，读者会以为那些是他选的这批。所以 `--commits` 必须逐个 `git show`，然后**在报告层面合并同类项**（同一处改动多次出现就合成一条，只保留最终状态）。

合并时的顺序：按提交时间正序读取，遇到后一次推翻前一次的改动，以最后一次为准。

## --last

`--last N` 取最近 N 次提交，等价于 `HEAD~N..HEAD`。

```bash
T=$(git rev-list --count HEAD)      # 提交总数
```

- `N` 必须是 **≥1 的整数**；不是整数或小于 1 时直接报错，不要猜。
- 边界在 `N < T` 时才成立：

```bash
if [ "$N" -lt "$T" ]; then
  base="HEAD~$N"
else
  base=$(git hash-object -t tree /dev/null)   # 空树哈希，表示「从最初开始」
fi
git log --oneline --no-merges "$base..HEAD"
git diff --stat "$base..HEAD"
```

- `N >= T` 时 `HEAD~N` 不存在（`git rev-parse` 退出码 128），**必须回退到空树**，否则命令直接失败。
- 空树哈希是固定的 `4b825dc642cb6eb9a060e54bf8d69288fbee4904`，用 `git hash-object -t tree /dev/null` 取更稳妥。
- `N = 1` 时是「最近 1 次提交」，不要理解成「从最初开始」。

## 取出净变化

除了 `--commits`，其余模式都取**一次净变化**，不要逐提交罗列：

```bash
git diff --stat "<range>"     # 先看规模
git diff "<range>"            # 正文
git diff --name-status "<range>"   # 只看有哪些文件发生了什么类型的改动
```

净变化意味着：中途新增又删除的东西不会出现，这正是报告想要的语义。

## 覆盖范围那一行怎么算

报告第二行的「覆盖 X 至 Y 的 N 次更新」按下面的方式算，**一律用日期和次数，不要出现提交号、分支名、tag 名**。

```bash
# 区间与 --last：N 是区间内非 merge 提交数
FIRST=$(git log --reverse --no-merges --format=%ad --date=short "<range>" | head -1)
LAST=$(git log --no-merges --format=%ad --date=short "<range>" | head -1)
N=$(git log --no-merges --oneline "<range>" | wc -l)

# --commits：只算被选中的那几个
git log --no-walk --format=%ad --date=short <sha...>
N=$(git log --no-walk --oneline <sha...> | wc -l)
```

- 用 `--no-merges`：合并动作本身不是一条改动，把它算进次数会让「N 次更新」虚高。
- **merge 提交的 `git show` 会显示合并带来的内容**（组合 diff），所以它对使用者其实是可见的改动，但它同时也会出现在被合并分支的提交里，逐个提交模式下会重复计数。用 `--no-merges` 加净变化 diff 就自然去掉了重复。

## 已踩过的坑

| 坑 | 后果 | 正确做法 |
| --- | ---- | -------- |
| 区间写成 `from^..to`（闭区间直觉） | 把 from 那次发布已含的内容全带进报告（实测） | 区间必须 `from..to`；自查最早提交不属 from 那次发布 |
| 用了 `--mine` 还拿净 diff 当正文 | 净 diff 含上游文件，无法按作者过滤 | 正文取材用 `git log -p --author` 过滤后的补丁 |
| 多前缀 tag 混排时取“全局最新” | 不同系列交错，会拿到别的产品线的 tag（实测 `v1.2.3`、`v0.0.5`、`ieioms-v2-alpha` 交错排列） | 按前缀隔离查找：`--from` 是 `ieioms-v0.0.1` 就只在 `ieioms-v*` 里找 |
| 只用 `--sort=-v:refname` 取最新 tag | `v2-alpha` 这类非语义化 tag 会排在最前（实测） | 叠加 `grep -E '^v[0-9]+(\.[0-9]+)+$'` 过滤 |
| 大写 `V0.0.1` 的 tag | git 通配区分大小写，不会被 `v*` 匹配，也触发不了按 `v*` 触发的 workflow（实测） | tag 一律小写 `v` 开头 |
| `git status --porcelain` 不带 `-uall` | 新增目录被折叠成一行，目录内文件全看不见 | 必须 `-uall` |
| 只跑 `git diff` | 漏掉全部已暂存改动 | 用 `git diff HEAD` |
| 只看 diff 不看未跟踪文件 | 漏掉全部新增文件 | 逐个读 `??` 清单里的文件 |
| `--commits` 用区间 diff | 把未选中的提交也算进报告 | 逐个 `git show` 再合并 |
| `--last N` 且 `N >= 提交总数` | `HEAD~N` 不存在，命令报错 | 回退到空树哈希 |
| `git log --since=<日期>` | 按提交时间过滤，会漏提交 | 用 `ref..HEAD` 区间 |
| ref 不存在时静默降级 | 报告范围与调用者要求不符 | 先 `git rev-parse --verify` 校验并报错 |
| 从单个仓库内部调用想跨仓库汇报 | 后端仓库不在扫描范围内，报告会漏一半 | 到前后端的**共同父目录**调用 |
| 子仓库没改动也纳入 | 多前端场景报告里一堆「无改动」 | 未提交模式只纳入 `status -uall` 非空的仓库 |
| `find -name .git -type d` | worktree/submodule 的 `.git` 是文件，会被漏掉 | 不加 `-type d` |
| 多仓库模式下改子仓库的 exclude | 报告文件不在子仓库管辖内，改了也没意义 | 只有工作区根目录本身是仓库时才排除 |

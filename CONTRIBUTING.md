# Contributing to SoulSync

## 版本管理规范（严格遵守，防止版本混乱）

### 单一事实源
版本号唯一来源是仓库根的 **`VERSION`** 文件。`server/pyproject.toml`、
`app/app/build.gradle.kts`（versionName）、`server/soulsync/main.py`（FastAPI version）
三处由脚本从 VERSION 同步，**禁止手工单独改其中一处**。

### 发布流程（一版一提交）

```bash
# 1. 功能提交：正常开发提交，绝不夹带版本号变更
git commit -m "feat: ..."

# 2. 发布：一条命令完成 bump+commit+tag+push
python3 scripts/release.py release 0.3.0 "一句话摘要"

# 3. 本地校验 / CI 校验
python3 scripts/release.py check
```

`release.py release` 会依次：写 VERSION → 同步三处版本号 → 创建**独立的
release commit**（只含版本变更）→ 打 annotated tag `vX.Y.Z` → push main + tag。

### 提交纪律

| 规则 | 原因 |
|---|---|
| 功能 commit 一律不碰 VERSION/版本号字段 | 版本与内容一一对应，diff 干净 |
| release commit 只含版本 bump（VERSION + 3 处同步 + CHANGELOG） | `git show vX.Y.Z` 即该版本完整快照 |
| tag 必须 annotated（`git tag -a`）且打在 release commit 上 | 可追溯 tagger/时间/说明 |
| CHANGELOG 每版本一节，发布前写好 | tag 内 CHANGELOG 与代码永远自洽 |
| 版本号语义化：major.minor.patch（破坏性/功能/修复） | 依赖方与用户可预期 |

### 禁止事项

- ❌ 手工 `git tag` 后 push 而不走 release 脚本（会绕过版本同步）
- ❌ 一次提交里同时出现功能变更和版本 bump
- ❌ 在 CHANGELOG 未更新的情况下发布新 tag

### CI

`.github/workflows/ci.yml` 在测试前执行 `python3 scripts/release.py check`，
任何版本号不同步都会直接红。

## 开发环境

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[llm-local]"     # 基础
pip install -e ".[perception]"    # 人脸/声纹（可选）
pip install -e ".[speech-emo]"    # emotion2vec 语音情绪（可选）

python -m pytest tests/ -q        # 全量测试
```

## 提交信息格式

```
<type>(<scope>): <summary>

<body: 动机 + 关键改动点>
```

type ∈ feat / fix / docs / test / refactor / release。

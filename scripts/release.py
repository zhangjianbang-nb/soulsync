#!/usr/bin/env python3
"""版本发布脚本：单一事实源 VERSION → 同步 bump 全部版本号。

用法：
  python3 scripts/release.py check              # 校验各处版本一致（CI 也用）
  python3 scripts/release.py bump 0.3.0         # 写 VERSION + 同步所有文件（不提交）
  python3 scripts/release.py release 0.3.0 "msg" # bump + git commit + tag + push

规范（CONTRIBUTING.md 同款）：
- 版本唯一事实源 = 仓库根 VERSION 文件
- 一版一提交：release commit 只含版本 bump（CHANGELOG/VERSION/代码内版本号），
  功能 commit 一律不带版本号变更，避免版本与内容错位
- tag 一律 annotated（git tag -a vX.Y.Z），且必须打在 release commit 上
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"

# (文件, 匹配 pattern, 替换 template)，{v} 为新版本号
TARGETS = [
    (ROOT / "server/pyproject.toml", r'^version = ".*"$', 'version = "{v}"'),
    (ROOT / "app/app/build.gradle.kts", r'^        versionName = ".*"$', '        versionName = "{v}"'),
    (ROOT / "server/soulsync/main.py", r'version=".*"', 'version="{v}"'),
]


def read_version() -> str:
    return VERSION_FILE.read_text().strip()


def write_version(v: str):
    VERSION_FILE.write_text(v + "\n")


def sync(v: str) -> list[str]:
    changed = []
    for path, pat, tpl in TARGETS:
        text = path.read_text()
        new = re.sub(pat, tpl.format(v=v), text, count=1, flags=re.M)
        if new != text:
            path.write_text(new)
            changed.append(str(path.name))
    return changed


def check() -> int:
    v = read_version()
    bad = []
    for path, pat, _tpl in TARGETS:
        text = path.read_text()
        m = re.search(pat, text, flags=re.M)
        got = m.group(0).rsplit('"', 2)[-2] if m else "?"
        if got != v:
            bad.append(f"{path.relative_to(ROOT)}: {got} != {v}")
    if bad:
        print("MISMATCH vs VERSION", v)
        for b in bad:
            print(" ", b)
        return 1
    print(f"all versions in sync: {v}")
    return 0


def sh(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    action = sys.argv[1]

    if action == "check":
        return check()

    if action == "bump":
        v = sys.argv[2]
        write_version(v)
        changed = sync(v)
        print(f"VERSION -> {v}; synced: {changed or 'none needed'}")
        return 0

    if action == "release":
        v, msg = sys.argv[2], sys.argv[3]
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            print("version must be X.Y.Z")
            return 2
        write_version(v)
        sync(v)
        sh(["git", "add", "-A"])
        sh(["git", "commit", "-m", f"release: v{v} — {msg}"])
        sh(["git", "tag", "-a", f"v{v}", "-m", f"SoulSync v{v} — {msg}"])
        sh(["git", "push", "origin", "main"])
        sh(["git", "push", "origin", f"v{v}"])
        print(f"released v{v}")
        return 0

    print("unknown action", action)
    return 2


if __name__ == "__main__":
    sys.exit(main())

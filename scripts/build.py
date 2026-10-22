#!/usr/bin/env python3
"""从 rules/ 生成各客户端规则集到 dist/。

用法：python3 scripts/build.py
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import emitters
from rule import Comment, Rule, load, normalize

ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = ROOT / "rules"
DIST_DIR = ROOT / "dist"

# (客户端目录, 产物扩展名, 渲染函数)
TARGETS = (
    ("surge", ".list", emitters.surge),
    ("loon", ".list", emitters.loon),
    ("clash", ".yaml", emitters.clash),
    ("quantumultx", ".list", emitters.quantumultx),
    ("singbox", ".json", emitters.singbox),
)


def build_header() -> str:
    """产物头部的构建时间，统一用 UTC，避免本地与 Actions 时区不一致。"""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"构建时间: {stamp}"


def main() -> int:
    sources = sorted(RULES_DIR.glob("*.list"))
    if not sources:
        print(f"未在 {RULES_DIR} 找到任何 .list 文件", file=sys.stderr)
        return 1

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    header = build_header()

    for source in sources:
        try:
            parsed = load(source)
        except ValueError as exc:
            print(f"解析失败: {exc}", file=sys.stderr)
            return 1

        tokens = normalize(parsed)
        total = sum(isinstance(token, Rule) for token in parsed)
        kept = sum(isinstance(token, Rule) for token in tokens)
        comments = sum(isinstance(token, Comment) for token in parsed)
        print(f"{source.name}: {total} 条规则 / {comments} 条注释 -> 保留 {kept} 条")

        for client, suffix, render in TARGETS:
            text, skipped = render(tokens, header=header)
            target = DIST_DIR / client / f"{source.stem}{suffix}"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")

            if skipped:
                detail = ", ".join(sorted({rule.type.value for rule in skipped}))
                print(f"  ! {client}: 跳过 {len(skipped)} 条不支持的规则 ({detail})")
            else:
                print(f"  - {client}: {kept} 条")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

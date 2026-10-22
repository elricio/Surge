#!/usr/bin/env python3
"""从 rules/ 生成各客户端规则集到 dist/。

用法：python3 scripts/build.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import emitters
from rule import load, normalize

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


def main() -> int:
    sources = sorted(RULES_DIR.glob("*.list"))
    if not sources:
        print(f"未在 {RULES_DIR} 找到任何 .list 文件", file=sys.stderr)
        return 1

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    for source in sources:
        try:
            parsed = load(source)
        except ValueError as exc:
            print(f"解析失败: {exc}", file=sys.stderr)
            return 1

        rules = normalize(parsed)
        print(f"{source.name}: {len(parsed)} 条 -> 规范化后 {len(rules)} 条")

        for client, suffix, render in TARGETS:
            text, skipped = render(rules)
            target = DIST_DIR / client / f"{source.stem}{suffix}"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")

            if skipped:
                detail = ", ".join(sorted({rule.type.value for rule in skipped}))
                print(f"  ! {client}: 跳过 {len(skipped)} 条不支持的规则 ({detail})")
            else:
                print(f"  - {client}: {len(rules)} 条")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

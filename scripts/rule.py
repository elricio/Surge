"""Surge 规则集解析与规范化。

源文件统一使用 Surge 语法（`TYPE,value[,options]`），本模块只负责把它
解析成结构化的 Rule，并做去重与冗余剪枝，不关心输出格式。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class RuleType(str, Enum):
    DOMAIN = "DOMAIN"
    DOMAIN_SUFFIX = "DOMAIN-SUFFIX"
    DOMAIN_KEYWORD = "DOMAIN-KEYWORD"
    DOMAIN_REGEX = "DOMAIN-REGEX"
    IP_CIDR = "IP-CIDR"
    IP_CIDR6 = "IP-CIDR6"
    GEOIP = "GEOIP"
    IP_ASN = "IP-ASN"
    URL_REGEX = "URL-REGEX"
    USER_AGENT = "USER-AGENT"
    PROCESS_NAME = "PROCESS-NAME"
    DST_PORT = "DST-PORT"
    SRC_PORT = "SRC-PORT"


# 这些类型的值本身可能包含逗号（例如 URL-REGEX 里的量词 {1,3}），
# 因此只能把整个剩余部分当作值，不能按逗号切出参数。
_SINGLE_VALUE_TYPES = frozenset(
    {
        RuleType.DOMAIN,
        RuleType.DOMAIN_SUFFIX,
        RuleType.DOMAIN_KEYWORD,
        RuleType.DOMAIN_REGEX,
        RuleType.URL_REGEX,
        RuleType.USER_AGENT,
    }
)


@dataclass(frozen=True)
class Rule:
    type: RuleType
    value: str
    options: tuple[str, ...] = ()

    def key(self) -> tuple[RuleType, str]:
        return self.type, self.value.lower()


def parse_line(line: str, where: str = "") -> Rule | None:
    """解析单行规则，注释和空行返回 None，语法错误抛 ValueError。"""
    stripped = line.strip()
    if not stripped or stripped[0] in "#;":
        return None

    raw_type, sep, raw_rest = stripped.partition(",")
    if not sep:
        raise ValueError(f"{where}: 缺少逗号分隔 -> {line!r}")

    try:
        rule_type = RuleType(raw_type.strip().upper())
    except ValueError as exc:
        raise ValueError(f"{where}: 未知规则类型 {raw_type.strip()!r}") from exc

    if rule_type in _SINGLE_VALUE_TYPES:
        value, options = raw_rest.strip(), ()
    else:
        parts = [part.strip() for part in raw_rest.split(",")]
        value, options = parts[0], tuple(part for part in parts[1:] if part)

    if not value:
        raise ValueError(f"{where}: 规则值为空 -> {line!r}")

    return Rule(rule_type, value, options)


def load(path: Path) -> list[Rule]:
    """读取规则文件，出错时抛 ValueError 并带上文件名和行号。"""
    rules: list[Rule] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        rule = parse_line(line, f"{path.name}:{lineno}")
        if rule is not None:
            rules.append(rule)
    return rules


def normalize(rules: list[Rule]) -> list[Rule]:
    """去重，并删除已被同一文件内 DOMAIN-SUFFIX 覆盖的规则。"""
    unique: list[Rule] = []
    seen: set[tuple[RuleType, str]] = set()
    for rule in rules:
        key = rule.key()
        if key in seen:
            continue
        seen.add(key)
        unique.append(rule)

    suffixes = {r.value.lower() for r in unique if r.type is RuleType.DOMAIN_SUFFIX}

    def covered(domain: str, skip_self: bool) -> bool:
        parts = domain.lower().split(".")
        # skip_self 用于 DOMAIN-SUFFIX 自身：只检查更短的父后缀是否已覆盖它
        start = 1 if skip_self else 0
        return any(".".join(parts[i:]) in suffixes for i in range(start, len(parts)))

    result: list[Rule] = []
    for rule in unique:
        if rule.type is RuleType.DOMAIN and covered(rule.value, skip_self=False):
            continue
        if rule.type is RuleType.DOMAIN_SUFFIX and covered(rule.value, skip_self=True):
            continue
        result.append(rule)
    return result

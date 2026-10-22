"""把 Rule 序列渲染成各客户端的规则集格式。

每个 emitter 返回 (文本, 被跳过的规则)，被跳过的规则会在构建时告警，
不会静默丢弃。
"""

from __future__ import annotations

import json

from rule import Rule, RuleType

_ALL = frozenset(RuleType)

# Loon 与 Surge 语法一致，但不支持 Surge 的部分类型。
_LOON_SUPPORTED = frozenset(
    {
        RuleType.DOMAIN,
        RuleType.DOMAIN_SUFFIX,
        RuleType.DOMAIN_KEYWORD,
        RuleType.IP_CIDR,
        RuleType.IP_CIDR6,
        RuleType.GEOIP,
        RuleType.IP_ASN,
        RuleType.URL_REGEX,
        RuleType.USER_AGENT,
        RuleType.PROCESS_NAME,
        RuleType.DST_PORT,
        RuleType.SRC_PORT,
    }
)

# mihomo / Clash Premium 支持的类型集合。
_CLASH_SUPPORTED = _ALL

# Quantumult X 用小写类型名，且类型名与 Surge 不同。
_QX_TYPES = {
    RuleType.DOMAIN: "host",
    RuleType.DOMAIN_SUFFIX: "host-suffix",
    RuleType.DOMAIN_KEYWORD: "host-keyword",
    RuleType.IP_CIDR: "ip-cidr",
    RuleType.IP_CIDR6: "ip6-cidr",
    RuleType.GEOIP: "geoip",
    RuleType.IP_ASN: "ip-asn",
    RuleType.URL_REGEX: "url-regex",
    RuleType.USER_AGENT: "user-agent",
}

# sing-box 规则集是纯匹配条件，不含策略；部分 Surge 类型没有等价字段。
_SINGBOX_FIELDS = {
    RuleType.DOMAIN: "domain",
    RuleType.DOMAIN_SUFFIX: "domain_suffix",
    RuleType.DOMAIN_KEYWORD: "domain_keyword",
    RuleType.DOMAIN_REGEX: "domain_regex",
    RuleType.IP_CIDR: "ip_cidr",
    RuleType.IP_CIDR6: "ip_cidr",
    RuleType.PROCESS_NAME: "process_name",
}


def _format(
    rules: list[Rule],
    supported: frozenset[RuleType] | set[RuleType],
    names: dict[RuleType, str] | None = None,
    sep: str = ",",
) -> tuple[list[str], list[Rule]]:
    lines: list[str] = []
    skipped: list[Rule] = []
    for rule in rules:
        if rule.type not in supported:
            skipped.append(rule)
            continue
        name = rule.type.value if names is None else names[rule.type]
        lines.append(sep.join((name, rule.value, *rule.options)))
    return lines, skipped


def surge(rules: list[Rule]) -> tuple[str, list[Rule]]:
    lines, skipped = _format(rules, _ALL)
    return "\n".join(lines) + ("\n" if lines else ""), skipped


def loon(rules: list[Rule]) -> tuple[str, list[Rule]]:
    lines, skipped = _format(rules, _LOON_SUPPORTED)
    return "\n".join(lines) + ("\n" if lines else ""), skipped


def clash(rules: list[Rule]) -> tuple[str, list[Rule]]:
    lines, skipped = _format(rules, _CLASH_SUPPORTED)
    if not lines:
        return "payload: []\n", skipped
    # json.dumps 生成的字符串是合法 YAML 双引号标量，可以安全处理正则里的特殊字符
    body = "\n".join(f"  - {json.dumps(line, ensure_ascii=False)}" for line in lines)
    return f"payload:\n{body}\n", skipped


def quantumultx(rules: list[Rule]) -> tuple[str, list[Rule]]:
    lines, skipped = _format(rules, set(_QX_TYPES), names=_QX_TYPES, sep=", ")
    return "\n".join(lines) + ("\n" if lines else ""), skipped


def singbox(rules: list[Rule]) -> tuple[str, list[Rule]]:
    groups: dict[str, list[str]] = {}
    skipped: list[Rule] = []
    for rule in rules:
        field = _SINGBOX_FIELDS.get(rule.type)
        if field is None:
            skipped.append(rule)
            continue
        groups.setdefault(field, []).append(rule.value)
    payload = {"version": 1, "rules": [{name: values} for name, values in groups.items()]}
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n", skipped

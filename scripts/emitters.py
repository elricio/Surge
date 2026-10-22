"""把 Token 序列渲染成各客户端的规则集格式。

每个 emitter 返回 (文本, 被跳过的规则)，被跳过的规则会在构建时告警，
不会静默丢弃。sing-box 的 JSON 格式不支持注释，该客户端的注释与构建时间
会被忽略。
"""

from __future__ import annotations

import json

from rule import Comment, Rule, RuleType, Token

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


def _comment(text: str, indent: str = "") -> str:
    return f"{indent}# {text}".rstrip()


def _render(
    tokens: list[Token],
    supported: frozenset[RuleType] | set[RuleType],
    names: dict[RuleType, str] | None = None,
    sep: str = ",",
) -> tuple[list[str], list[Rule]]:
    lines: list[str] = []
    skipped: list[Rule] = []
    for token in tokens:
        if isinstance(token, Comment):
            lines.append(_comment(token.text))
            continue
        if token.type not in supported:
            skipped.append(token)
            continue
        name = token.type.value if names is None else names[token.type]
        lines.append(sep.join((name, token.value, *token.options)))
    return lines, skipped


def _plain(
    tokens: list[Token],
    supported: frozenset[RuleType] | set[RuleType],
    names: dict[RuleType, str] | None = None,
    sep: str = ",",
    header: str | None = None,
) -> tuple[str, list[Rule]]:
    lines, skipped = _render(tokens, supported, names, sep)
    if header:
        lines.insert(0, _comment(header))
        if len(lines) > 1:
            lines.insert(1, "")
    return "\n".join(lines) + ("\n" if lines else ""), skipped


def surge(tokens: list[Token], header: str | None = None) -> tuple[str, list[Rule]]:
    return _plain(tokens, _ALL, header=header)


def loon(tokens: list[Token], header: str | None = None) -> tuple[str, list[Rule]]:
    return _plain(tokens, _LOON_SUPPORTED, header=header)


def quantumultx(tokens: list[Token], header: str | None = None) -> tuple[str, list[Rule]]:
    return _plain(tokens, set(_QX_TYPES), names=_QX_TYPES, sep=", ", header=header)


def clash(tokens: list[Token], header: str | None = None) -> tuple[str, list[Rule]]:
    rows: list[str] = []
    skipped: list[Rule] = []
    has_rules = False

    for token in tokens:
        if isinstance(token, Comment):
            rows.append(_comment(token.text, indent="  "))
            continue
        if token.type not in _CLASH_SUPPORTED:
            skipped.append(token)
            continue
        has_rules = True
        # json.dumps 生成的字符串是合法 YAML 双引号标量，可以安全处理正则里的特殊字符
        line = ",".join((token.type.value, token.value, *token.options))
        rows.append(f"  - {json.dumps(line, ensure_ascii=False)}")

    head = _comment(header) + "\n" if header else ""
    if not has_rules:
        body = "\n".join(rows)
        if body:
            return f"{head}{body}\npayload: []\n", skipped
        return f"{head}payload: []\n", skipped

    return f"{head}payload:\n" + "\n".join(rows) + "\n", skipped


def singbox(tokens: list[Token], header: str | None = None) -> tuple[str, list[Rule]]:
    groups: dict[str, list[str]] = {}
    skipped: list[Rule] = []
    for token in tokens:
        if isinstance(token, Comment):
            continue
        field = _SINGBOX_FIELDS.get(token.type)
        if field is None:
            skipped.append(token)
            continue
        groups.setdefault(field, []).append(token.value)
    payload = {"version": 1, "rules": [{name: values} for name, values in groups.items()]}
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n", skipped

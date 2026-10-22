# proxy-rules

只维护一份源规则，自动生成 Surge、Loon、Clash (mihomo)、Quantumult X、sing-box 五种格式的规则集。

## 目录结构

```
rules/                 # 唯一的源规则，Surge 语法
├── direct.list
└── reject.list
scripts/
├── rule.py            # 解析、去重、剪枝
├── emitters.py        # 各客户端格式渲染
└── build.py           # 构建入口，输出到 dist/
dist/                  # 构建产物（由 Actions 自动提交，请勿手改）
├── surge/  loon/  clash/  quantumultx/  singbox/
.github/workflows/
└── build.yml          # push 后自动构建并提交 dist/
```

## 维护方式

只改 `rules/*.list`，使用 Surge 语法，一行一条：

```
# 注释以 # 开头
DOMAIN-SUFFIX,centaline.com
DOMAIN,www.example.com
IP-CIDR,10.0.0.0/8,no-resolve
URL-REGEX,^https:\/\/api\.example\.com\/ad$
```

构建时会做两件事：同一文件内去重；删除已被本文件 `DOMAIN-SUFFIX` 覆盖的 `DOMAIN` 和子级 `DOMAIN-SUFFIX`。

源文件里的 `#` 注释会原样带到产物中，被剪枝规则前的注释会顺延到下一条保留规则；产物开头会写入一行 UTC 构建时间。sing-box 的 JSON 格式不支持注释，该格式只输出规则本身。

push 到 main 后 GitHub Actions 自动重新生成 `dist/` 并提交回来。本地预览：

```bash
python3 scripts/build.py
```

脚本零第三方依赖，只需要 Python 3.9+。

## 各客户端引用

把 `elricio/proxy-rules` 换成你的仓库地址即可。

### Surge

```
[Rule]
RULE-SET, https://raw.githubusercontent.com/elricio/proxy-rules/main/dist/surge/direct.list, DIRECT
RULE-SET, https://raw.githubusercontent.com/elricio/proxy-rules/main/dist/surge/reject.list, REJECT
```

### Loon

```
[Remote Rule]
https://raw.githubusercontent.com/elricio/proxy-rules/main/dist/loon/direct.list, policy=DIRECT, tag=direct
https://raw.githubusercontent.com/elricio/proxy-rules/main/dist/loon/reject.list, policy=REJECT, tag=reject
```

### Clash / mihomo

```yaml
rule-providers:
  direct:
    type: http
    behavior: classical
    format: yaml
    url: https://raw.githubusercontent.com/elricio/proxy-rules/main/dist/clash/direct.yaml
    path: ./ruleset/direct.yaml
    interval: 86400
  reject:
    type: http
    behavior: classical
    format: yaml
    url: https://raw.githubusercontent.com/elricio/proxy-rules/main/dist/clash/reject.yaml
    path: ./ruleset/reject.yaml
    interval: 86400

rules:
  - RULE-SET,reject,REJECT
  - RULE-SET,direct,DIRECT
```

产物保留了规则类型前缀，所以 `behavior` 必须是 `classical`，不能用 `domain`。

### Quantumult X

```
[filter_remote]
https://raw.githubusercontent.com/elricio/proxy-rules/main/dist/quantumultx/direct.list, tag=direct, force-policy=direct, enabled=true
https://raw.githubusercontent.com/elricio/proxy-rules/main/dist/quantumultx/reject.list, tag=reject, force-policy=reject, enabled=true
```

### sing-box

```json
{
  "route": {
    "rule_set": [
      {
        "type": "remote",
        "tag": "direct",
        "format": "source",
        "url": "https://raw.githubusercontent.com/elricio/proxy-rules/main/dist/singbox/direct.json"
      }
    ],
    "rules": [
      { "rule_set": "direct", "outbound": "direct" }
    ]
  }
}
```

### Stash / Egern

无需额外产物，直接复用：

- Stash 兼容 Clash 配置，用 `dist/clash/*.yaml`
- Egern 兼容 Surge 文本规则，用 `dist/surge/*.list`

## 已知限制

格式差异无法完全抹平，生成时会跳过不支持的规则并在构建日志里告警：

| 规则类型 | Loon | Clash | QX | sing-box |
|---|---|---|---|---|
| `URL-REGEX` | ✅ | ✅ | ✅ `url-regex` | ❌ 无等价语义 |
| `DOMAIN-REGEX` | ❌ | ✅ | ❌ | ✅ `domain_regex` |
| `GEOIP` | ✅ | ✅ | ✅ | ❌ 改用 rule-set |
| `PROCESS-NAME` | ✅ | ✅ | ❌ | ✅ |
| `DST-PORT` / `SRC-PORT` | ✅ | ✅ | ❌ | ❌ |

其他约定：

- sing-box 的 JSON 规则集不支持注释，`dist/singbox/*.json` 不含源注释与构建时间。
- 出现未知规则类型时构建会直接失败并指出文件行号，避免拼写错误导致规则被静默丢弃。
- `dist/` 是生成物，改源文件后由 Actions 覆盖，手改会在下次构建时丢失。

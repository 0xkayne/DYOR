# CryptoPanic API Profile

> **Profile 版本**：1.0  
> **生成日期**：2026-03-10  
> **文档来源**：用户提供的 API Reference 文档（https://cryptopanic.com/developers/api/）  
> **API 版本**：developer/v2  
> **提取方式**：手动读取文档（用户直接提供）  
> **下次建议复查**：2026-06-08（生成日期 + 90 天）
>
> **可信度声明**：本 Profile 忠实反映用户提供的文档内容。  
> `✅ 已验证` = Smoke Test 通过 | `⚠️ 待验证` = 需实际调用确认 | `🚫 计划限制` = 仅高级计划可用

---

## 0. Profile 元信息

| 属性 | 值 |
|------|-----|
| 官方文档 | https://cryptopanic.com/developers/api/ |
| OpenAPI Spec | 不存在（手动文档，无机器可读 Spec） |
| 官方 SDK | 无（文档未提及） |
| 服务状态页 | ⚠️ 待验证 — 文档未提及 |
| 更新日志 | ⚠️ 待验证 — 文档未提及 |

### 环境变量命名约定（Claude Code 直接使用）

| 环境变量名 | 用途 | 示例值格式 |
|-----------|------|-----------|
| `CRYPTOPANIC_API_KEY` | 主认证 Token（auth_token） | 40位十六进制字符串 |

---

## 1. 服务概述

CryptoPanic 提供加密货币新闻聚合 API，支持按货币、区域、情绪过滤器（如 bullish/bearish）检索新闻帖子，并包含 votes（社区情绪投票）和 panic_score（市场影响力评分）字段。当前用户 API Level 为 **DEVELOPER**。

---

## 2. Base URL

```
https://cryptopanic.com/api/developer/v2
```

---

## 3. 认证

### 认证类型
- [x] API Key（**Query Parameter**） — 参数名：`auth_token`

### 精确参数名（原文，区分大小写）
```
?auth_token={YOUR_API_KEY}
```

> ⚠️ service-hints 提示：历史上在 `auth_token` 和 `api_key` 之间变化过，当前文档使用 `auth_token`，以此为准。

### 官方认证示例（原文）
```
/api/developer/v2/posts/?auth_token={YOUR_AUTH_TOKEN}
```

### API 级别差异

| 计划 | 级别名称 | 认证参数 |
|------|---------|---------|
| 基础版 | DEVELOPER | `auth_token` |
| 中级版 | GROWTH | `auth_token` |
| 高级版 | ENTERPRISE | `auth_token` |

> 认证参数名相同，但可用端点/参数范围不同（见端点章节中的 Availability 列）。

### 环境变量约定
| 变量名 | 用途 |
|--------|------|
| `CRYPTOPANIC_API_KEY` | 唯一 API Key（DEVELOPER/GROWTH/ENTERPRISE 通用） |

---

## 4. 速率限制

| 计划 | Level 1（每秒） | Level 2（每月） |
|------|--------------|--------------|
| DEVELOPER | ⚠️ 待验证（文档仅举例"2/sec"，未明确 Developer 数值） | ⚠️ 待验证（文档仅举例"1,000/month"） |
| GROWTH | ⚠️ 待验证 | ⚠️ 待验证 |
| ENTERPRISE | ⚠️ 待验证（文档仅举例"10/sec"） | ⚠️ 待验证（文档仅举例"300,000/month"） |

- 超限 HTTP 状态码：`403 Forbidden` 或 `429 Too Many Requests`
- 超限触发条件：超过 Level 1（每秒上限）或 Level 2（月度上限）均可触发
- Retry-After 响应头：⚠️ 待验证 — 文档未说明是否返回此 Header

---

## 5. 端点参考

### 5.1 获取新闻列表 `[P1/P2/P3]`

| 字段 | 内容 |
|------|------|
| HTTP 方法 | GET |
| 路径 | `/posts/` |
| 完整 URL | `https://cryptopanic.com/api/developer/v2/posts/` |
| 功能描述 | Retrieve a list of news posts |
| 认证要求 | 必须（`auth_token` Query 参数） |
| API 版本 | developer/v2 |

> **注意**：多种使用场景（按币种过滤、按情绪过滤、RSS 等）**全部共用此同一端点**，通过不同参数组合区分功能。

#### 请求参数

| 参数名 | 位置 | 类型 | 必填 | 默认值 | 枚举值/格式说明 | 计划可用性 | 来源 |
|--------|------|------|------|--------|---------------|-----------|------|
| `auth_token` | query | string | ✅ | — | 40位十六进制 Key | Developer/Growth/Enterprise | 文档原文 |
| `public` | query | boolean | ❌ | — | `true` | Developer/Growth/Enterprise | 文档原文 |
| `currencies` | query | string | ❌ | — | 货币代码，多个逗号分隔，如 `BTC,ETH` | Developer/Growth/Enterprise | 文档原文 |
| `regions` | query | string | ❌ | `en` | `en`, `de`, `nl`, `es`, `fr`, `it`, `pt`, `ru`, `tr`, `ar`, `zh`, `ja`, `ko` | Developer/Growth/Enterprise | 文档原文 |
| `filter` | query | string | ❌ | — | `rising`, `hot`, `bullish`, `bearish`, `important`, `saved`, `lol` | Developer/Growth/Enterprise | 文档原文 |
| `kind` | query | string | ❌ | `all` | `news`, `media`, `all` | Developer/Growth/Enterprise | 文档原文 |
| `following` | query | boolean | ❌ | — | `true`；仅 Private 模式有效（与 `public=true` 互斥） | Developer/Growth/Enterprise | 文档原文 |
| `last_pull` | query | string | ❌ | — | ISO 8601 datetime，如 `"2026-03-10T10:19:47.957Z"` | 🚫 仅 Enterprise | 文档原文 |
| `panic_period` | query | string | ❌ | — | `1h`, `6h`, `24h` | 🚫 仅 Enterprise | 文档原文 |
| `panic_sort` | query | string | ❌ | — | `asc`, `desc`；**必须同时传 `panic_period`** | 🚫 仅 Enterprise | 文档原文 |
| `size` | query | integer | ❌ | ⚠️ 待验证 | 1 ~ 500 | 🚫 仅 Enterprise | 文档原文 |
| `with_content` | query | boolean | ❌ | — | `true` | 🚫 仅 Enterprise | 文档原文 |
| `search` | query | string | ❌ | — | 字符串关键词 | 🚫 仅 Enterprise | 文档原文 |
| `format` | query | string | ❌ | — | `rss`（返回 RSS 格式，固定 20 条，不受计划影响） | Developer/Growth/Enterprise | 文档原文 |

> ⚠️ **`currencies` 格式待验证**：文档示例为 `&currencies=BTC,ETH`（逗号分隔单次传参），是否支持多次传同名参数未验证。

#### 响应结构（原文）

```json
{
  "next": "url",
  "previous": "url",
  "results": [
    "... array of items ..."
  ]
}
```

#### 顶层响应字段

| 字段 | 类型 | 描述 | 来源 |
|------|------|------|------|
| `next` | string \| null | 下一页完整 URL（ISO 8601 URI），无则为 null | 文档原文 |
| `previous` | string \| null | 上一页完整 URL（ISO 8601 URI），无则为 null | 文档原文 |
| `results` | array of Item | 新闻条目列表 | 文档原文 |

#### Item 对象字段

| 字段 | 类型 | 描述 | 来源 |
|------|------|------|------|
| `id` | integer | 帖子唯一标识符 | 文档原文 |
| `slug` | string | URL 友好的短标题 | 文档原文 |
| `title` | string | 帖子完整标题 | 文档原文 |
| `description` | string | 摘要或简介 | 文档原文 |
| `published_at` | string (ISO 8601) | 发布时间 | 文档原文 |
| `created_at` | string (ISO 8601) | 系统创建时间 | 文档原文 |
| `kind` | string | 内容类型：`news`, `media`, `blog`, `twitter`, `reddit` | 文档原文 |
| `source` | object | 来源信息，见 Source 对象 | 文档原文 |
| `original_url` | string (uri) | 原文链接 | 文档原文 |
| `url` | string (uri) | CryptoPanic 托管页面链接 | 文档原文 |
| `image` | string (uri) | 封面图 URL | 文档原文 |
| `instruments` | array of Instrument | 涉及的加密货币列表 | 文档原文 |
| `votes` | object | 社区情绪投票，见 Votes 对象 | 文档原文 |
| `panic_score` | integer (0–100) | 市场影响力评分（专有指标） | 文档原文 |
| `panic_score_1h` | integer (0–100) | 第一小时内市场影响力评分 | 文档原文 |
| `author` | string | 文章作者名 | 文档原文 |
| `content` | object | 正文内容，见 Content 对象 | 文档原文 |

#### Instrument 对象字段

| 字段 | 类型 | 描述 | 来源 |
|------|------|------|------|
| `code` | string | 代币代码（如 `BTC`） | 文档原文 |
| `title` | string | 全名（如 `Bitcoin`） | 文档原文 |
| `slug` | string | URL 友好标识符 | 文档原文 |
| `url` | string (uri) | 该代币页面链接 | 文档原文 |
| `market_cap_usd` | number | 美元市值 | 文档原文 |
| `price_in_usd` | number | 当前美元价格 | 文档原文 |
| `price_in_btc` | number | 当前 BTC 价格 | 文档原文 |
| `price_in_eth` | number | 当前 ETH 价格 | 文档原文 |
| `price_in_eur` | number | 当前欧元价格 | 文档原文 |
| `market_rank` | integer | 全球市值排名 | 文档原文 |

#### Source 对象字段

| 字段 | 类型 | 描述 | 来源 |
|------|------|------|------|
| `title` | string | 发布者名称 | 文档原文 |
| `region` | string | 语言代码（如 `en`, `fr`） | 文档原文 |
| `domain` | string | 发布者域名 | 文档原文 |
| `type` | string | 来源类型：`feed`, `blog`, `twitter`, `media`, `reddit` | 文档原文 |

#### Votes 对象字段

| 字段 | 类型 | 描述 | 来源 |
|------|------|------|------|
| `negative` | integer | 负面投票数 | 文档原文 |
| `positive` | integer | 正面投票数 | 文档原文 |
| `important` | integer | 重要标记数 | 文档原文 |
| `liked` | integer | 喜欢数 | 文档原文 |
| `disliked` | integer | 不喜欢数 | 文档原文 |
| `lol` | integer | 搞笑反应数 | 文档原文 |
| `toxic` | integer | 有毒标记数 | 文档原文 |
| `saved` | integer | 收藏数 | 文档原文 |
| `comments` | integer | 评论数 | 文档原文 |

#### Content 对象字段

| 字段 | 类型 | 描述 | 来源 |
|------|------|------|------|
| `original` | string \| null | 原始 HTML/Markup（如可用） | 文档原文 |
| `clean` | string \| null | 纯文本版本 | 文档原文 |

---

### 5.2 获取投资组合 `[P4]` 🚫 GROWTH/ENTERPRISE 专属

| 字段 | 内容 |
|------|------|
| HTTP 方法 | GET |
| 路径 | `/portfolio/` |
| 完整 URL | `https://cryptopanic.com/api/developer/v2/portfolio/` |
| 功能描述 | Retrieve your portfolio |
| 认证要求 | 必须（`auth_token` Query 参数） |
| 计划限制 | 🚫 仅 GROWTH 和 ENTERPRISE 可用，DEVELOPER 无法访问 |

> ⚠️ 响应结构文档中未提供，需升级计划后实际调用确认。

---

### 5.3 RSS Feed `[P4]`

| 字段 | 内容 |
|------|------|
| 路径 | `/posts/?format=rss` |
| 说明 | 在 `/posts/` 参数基础上增加 `format=rss`，返回 RSS 格式 |
| 固定限制 | **无论任何计划，均只返回 20 条**（原文："only 20 items will be returned in the response, regardless of your API plan"） |

示例（原文）：
```
/api/developer/v2/posts/?auth_token={KEY}&currencies=ETH&filter=rising&format=rss
/api/developer/v2/posts/?auth_token={KEY}&following=true&format=rss
```

---

## 6. 错误处理

| HTTP 状态码 | 含义 | 文档说明（原文） |
|------------|------|---------------|
| 401 | 认证失败 | "Unauthorized - Invalid or missing auth_token" |
| 403 | 禁止访问 | "Forbidden - Rate limit exceeded or no access to this endpoint" |
| 429 | 请求过多 | "Too Many Requests - You are being rate limited" |
| 500 | 服务端错误 | "Internal Server Error" |

> ⚠️ 错误响应体的 JSON 格式文档未提供，待实际验证。

---

## 7. 特殊约定

### 时间格式
- 响应中时间字段：ISO 8601 datetime（`published_at`, `created_at`）
- 请求参数 `last_pull`：ISO 8601 格式（示例原文：`"2026-03-10T10:19:47.957Z"`）

### 分页
- 分页方式：cursor-based，使用响应中 `next` / `previous` 字段的完整 URL 翻页
- 每页条数：⚠️ 待验证 — DEVELOPER 计划默认每页数量文档未明确（`size` 参数仅 ENTERPRISE 可用）

### Public 模式 vs Private 模式
- **Private 模式**（默认）：使用用户个人设置（自定义来源、禁用来源），适合 ticker/bot/自定义 App
- **Public 模式**（`&public=true`）：通用新闻流，适合面向公众的移动/Web App；高流量需本地缓存

### `kind` 字段的两种语义
- 请求参数 `kind` 可选值：`news`, `media`, `all`（默认 `all`）
- 响应 Item 中 `kind` 字段取值范围更广：`news`, `media`, `blog`, `twitter`, `reddit`

---

## 8. 待验证项目汇总

| # | 位置 | 问题描述 | 验证方法 | 状态 |
|---|------|---------|---------|------|
| 1 | 速率限制 | DEVELOPER 计划具体每秒/每月上限数值 | 查看账户控制台或联系支持 | ⚠️ 待验证 |
| 2 | `/posts/` `currencies` | 多货币逗号分隔 vs 多次传参，哪种有效？ | `&currencies=BTC,ETH` 与 `&currencies=BTC&currencies=ETH` 分别测试 | ⚠️ 待验证 |
| 3 | `/posts/` 分页 | DEVELOPER 计划默认每页返回多少条？ | 实际调用观察 `results` 数组长度 | ⚠️ 待验证 |
| 4 | 错误响应体 | 401/403/429/500 的 JSON 响应体格式？ | 故意传 INVALID_TOKEN 触发 401 | ⚠️ 待验证 |
| 5 | `/portfolio/` | 响应字段结构？（DEVELOPER 无权限） | 升级计划后验证 | ⚠️ 待验证（需升级） |
| 6 | `size` 默认值 | DEVELOPER 计划不可用 `size`，默认每页数是多少？ | 观察实际响应 `results` 长度 | ⚠️ 待验证 |
| 7 | Retry-After Header | 429 时是否返回 `Retry-After` 响应头？ | 触发速率限制后检查响应头 | ⚠️ 待验证 |

---

## 9. Smoke Test 脚本

```bash
#!/bin/bash
# CryptoPanic API Smoke Test
# 使用前设置：export CRYPTOPANIC_API_KEY="your_auth_token_here"

BASE_URL="https://cryptopanic.com/api/developer/v2"
KEY="${CRYPTOPANIC_API_KEY}"

echo "=== Test 1: 认证验证 + 基本新闻列表 ==="
curl -s -w "\nHTTP %{http_code}\n" \
  "${BASE_URL}/posts/?auth_token=${KEY}&public=true"

echo ""
echo "=== Test 2: 按货币过滤（验证逗号分隔格式）==="
curl -s -w "\nHTTP %{http_code}\n" \
  "${BASE_URL}/posts/?auth_token=${KEY}&currencies=BTC,ETH&public=true"

echo ""
echo "=== Test 3: 情绪过滤（bullish）==="
curl -s -w "\nHTTP %{http_code}\n" \
  "${BASE_URL}/posts/?auth_token=${KEY}&filter=bullish&public=true"

echo ""
echo "=== Test 4: kind=news 过滤 ==="
curl -s -w "\nHTTP %{http_code}\n" \
  "${BASE_URL}/posts/?auth_token=${KEY}&kind=news&public=true"

echo ""
echo "=== Test 5: 错误认证（验证 401 响应格式）==="
curl -s -v -w "\nHTTP %{http_code}\n" \
  "${BASE_URL}/posts/?auth_token=INVALID_TOKEN_XXXXX" 2>&1 | grep -E "(HTTP|{|<)"

echo ""
echo "=== Test 6: RSS 格式（验证固定 20 条）==="
RESULT=$(curl -s "${BASE_URL}/posts/?auth_token=${KEY}&currencies=BTC&format=rss")
echo "$RESULT" | grep -c "<item>" && echo "条目数量（应为 20）"
```

---

## 10. 集成注意事项（供 Claude Code 参考）

1. **认证参数名为 `auth_token`（Query 参数）**：不是 Header，不是 `api_key`，不是 Bearer Token。

2. **DEVELOPER 计划有 6 个参数完全不可用**：`last_pull`、`panic_period`、`panic_sort`、`size`、`with_content`、`search` — 传入后的行为待验证（可能静默忽略或报错）。

3. **RSS 固定 20 条限制**：原文："only 20 items will be returned in the response, regardless of your API plan"，不可通过任何参数调整。

4. **Public 模式高流量需缓存**：原文："For high-traffic web apps, local caching is strongly recommended"。

5. **`following=true` 为纯私有模式**：与 `public=true` 互斥，勿同时传递。

6. **`panic_sort` 必须搭配 `panic_period`**：文档标注为"Mandatory param: panic_period=<period>"，两者需同时传且均为 ENTERPRISE 专属。

7. **分页使用 cursor URL**：翻页应直接使用响应 `next` 字段的完整 URL，不要手动拼接页码参数。

8. **`/portfolio/` 端点 DEVELOPER 不可访问**：调用会返回 403，需 GROWTH 及以上计划。

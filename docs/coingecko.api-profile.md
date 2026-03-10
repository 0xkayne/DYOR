# CoinGecko API Profile

> **Profile 版本**：1.0
> **生成日期**：2026-03-10
> **文档来源**：https://docs.coingecko.com/v3.0.1/reference/introduction
> **API 版本**：v3
> **提取方式**：手动读取文档（多页）+ pycoingecko SDK 源码交叉验证
> **下次建议复查**：2026-06-10
>
> **可信度说明**：`✅ 已验证` = 文档原文明确 + SDK 源码交叉确认 | `⚠️ 待验证` = 需本地 curl 实际确认 | `🚫 Pro专属` = 需付费计划

---

## 0. Profile 元信息

| 属性 | 值 |
|------|----|
| 官方文档（Demo） | https://docs.coingecko.com/v3.0.1/reference/introduction |
| 官方文档（Pro） | https://docs.coingecko.com/reference/introduction |
| OpenAPI Spec | 未找到可下载文件（文档使用 Mintlify 渲染） |
| 官方 Python SDK | https://github.com/man-c/pycoingecko（非官方但官方推荐，广泛使用） |
| 服务状态页 | https://status.coingecko.com |
| 更新日志 | https://docs.coingecko.com/changelog |
| 定价页 | https://www.coingecko.com/en/api/pricing |

### 环境变量命名约定（Claude Code 直接使用）

| 环境变量名 | 用途 | Key 格式示例 |
|-----------|------|------------|
| `COINGECKO_API_KEY` | Demo（免费）API Key | `CG-xxxxxxxxxxxxxxxxxxxxxxxxx` |
| `COINGECKO_PRO_API_KEY` | Pro API Key（付费） | `CG-xxxxxxxxxxxxxxxxxxxxxxxxx` |

---

## 1. 服务概述

"CoinGecko API offers the most comprehensive and reliable crypto market data through RESTful JSON endpoints." 覆盖 18,000+ 枚代币、1,000+ 交易所，同时通过 GeckoTerminal 提供 250+ 链上的 DEX 数据。响应格式统一为 JSON。

---

## 2. Base URL

```
# Demo（免费）计划
https://api.coingecko.com/api/v3/

# Pro（付费）计划  ← 注意与 Demo 完全不同的域名
https://pro-api.coingecko.com/api/v3/
```

> ⚠️ **重要**：Demo Key 只能用于 `api.coingecko.com`，Pro Key 只能用于 `pro-api.coingecko.com`。
> 用错域名会返回 `10010` 或 `10011` 错误码。

---

## 3. 认证

### 认证类型
- [x] API Key（Header）—— 推荐方式
- [x] API Key（Query Parameter）—— 便于测试，生产环境不推荐（有泄露风险）
- [x] 无需认证（部分公共端点，但速率更严格）

### 精确的 Header / 参数名（✅ 文档原文 + SDK 源码确认，区分大小写）

| 计划 | Header 名 | Query 参数名 |
|------|-----------|------------|
| Demo（免费） | `x-cg-demo-api-key` | `x_cg_demo_api_key` |
| Pro（付费） | `x-cg-pro-api-key` | `x_cg_pro_api_key` |

> ⚠️ **关键陷阱**：Header 名和 Query 参数名写法不同（Header 用 `-`，Query 用 `_`）。

### 官方认证示例（文档原文）

**Header 方式（推荐）：**
```bash
curl --request GET \
     --url https://api.coingecko.com/api/v3/ping \
     --header 'x-cg-demo-api-key: YOUR_API_KEY'
```

**Query 参数方式（便于测试）：**
```
https://api.coingecko.com/api/v3/ping?x_cg_demo_api_key=YOUR_API_KEY
```

### 获取 Demo API Key
注册：https://www.coingecko.com/en/api/pricing（免费，无需信用卡）

---

## 4. 速率限制

| 计划 | 速率限制 | 月度配额 | 费用 |
|------|---------|---------|------|
| 公共（无 Key） | ~10 次/分钟（随流量波动） | 无明确上限，不稳定 | 免费 |
| Demo（有 Key） | 30 次/分钟 | 10,000 次/月 | 免费 |
| Analyst（付费最低档） | 500 次/分钟 | 500,000 次/月 | $129/月起 |
| Pro | 500-1,000 次/分钟 | 更高 | 按计划 |

**超限行为：**
- HTTP 状态码：`429 Too Many Requests`
- 响应错误码：`10005`（访问受限端点时）
- `⚠️ 待验证`：429 响应体具体格式，文档未提供示例 JSON

**重要规则（文档原文）：**
> "Regardless of the HTTP status code returned (including 4xx and 5xx errors), all API requests will count towards your minute rate limit."

**推荐重试策略（官方文档）：**
指数退避（Exponential Backoff）：
```
尝试 1: 429 → 等 1 秒
尝试 2: 429 → 等 2 秒
尝试 3: 429 → 等 4 秒
```

---

## 5. 端点参考

> 端点标注：`[P1]` 核心查询 | `[P2]` 搜索/列表 | `[P3]` 详情/历史 | `[P4]` 辅助 | `[🚫 Pro]` 付费专属

---

### 5.1 GET /ping `[P4]`

| 字段 | 内容 |
|------|------|
| 完整 URL（Demo） | `https://api.coingecko.com/api/v3/ping` |
| 功能 | 检查 API 服务器状态 |
| 认证 | 可选 |

**响应（文档原文）：**
```json
{
  "gecko_says": "(V3) To the Moon!"
}
```

---

### 5.2 GET /simple/price `[P1]` ✅

| 字段 | 内容 |
|------|------|
| 完整路径 | `/simple/price` |
| 完整 URL | `https://api.coingecko.com/api/v3/simple/price` |
| 功能 | 获取一个或多个代币的当前价格（及可选的市值、交易量、涨跌幅） |
| 认证 | 可选（有 Key 速率更高） |

**请求参数：**

| 参数名 | 位置 | 类型 | 必填 | 默认值 | 说明 | 来源 |
|--------|------|------|------|--------|------|------|
| `ids` | query | string | ✅ | — | 逗号分隔的 coin id，如 `bitcoin,ethereum` | 文档原文 |
| `vs_currencies` | query | string | ✅ | — | 逗号分隔的目标货币，如 `usd,eur,btc` | 文档原文 |
| `include_market_cap` | query | boolean | ❌ | `false` | 是否包含市值 | SDK 源码 |
| `include_24hr_vol` | query | boolean | ❌ | `false` | 是否包含 24h 交易量 | SDK 源码 |
| `include_24hr_change` | query | boolean | ❌ | `false` | 是否包含 24h 涨跌幅 | SDK 源码 |
| `include_last_updated_at` | query | boolean | ❌ | `false` | 是否包含最后更新时间（UNIX 秒） | SDK 源码 |
| `precision` | query | string/integer | ❌ | — | 价格小数位数 | ⚠️ 推断-待验证 |

**响应示例（文档原文结构）：**
```json
{
  "bitcoin": {
    "usd": 67500.12,
    "usd_market_cap": 1330000000000,
    "usd_24h_vol": 25000000000,
    "usd_24h_change": 2.34,
    "last_updated_at": 1717200000
  }
}
```

**注意事项：**
- `ids` 必须是 CoinGecko coin id（如 `bitcoin`），不是 symbol（如 `BTC`）
- 对应关系获取：调用 `/coins/list` 端点
- 合法的 `vs_currencies` 值：调用 `/simple/supported_vs_currencies` 获取完整列表

---

### 5.3 GET /coins/markets `[P1]` ✅

| 字段 | 内容 |
|------|------|
| 完整路径 | `/coins/markets` |
| 完整 URL | `https://api.coingecko.com/api/v3/coins/markets` |
| 功能 | 批量获取代币市场数据（价格、市值、交易量、涨跌幅等） |
| 认证 | 可选 |

**请求参数：**

| 参数名 | 位置 | 类型 | 必填 | 默认值 | 说明 | 来源 |
|--------|------|------|------|--------|------|------|
| `vs_currency` | query | string | ✅ | — | 目标货币，单个值，如 `usd` | 文档原文 |
| `ids` | query | string | ❌ | — | 逗号分隔的 coin id（不传则返回全市场） | 文档原文 |
| `order` | query | string | ❌ | `market_cap_desc` | 排序方式，见下方枚举 | 文档原文 |
| `per_page` | query | integer | ❌ | `100` | 每页数量，最大 `250` | 文档原文 |
| `page` | query | integer | ❌ | `1` | 页码 | 文档原文 |
| `sparkline` | query | boolean | ❌ | `false` | 是否包含 7 日价格走势迷你图数据 | 文档原文 |
| `price_change_percentage` | query | string | ❌ | — | 额外涨跌幅时间段，如 `1h,24h,7d,14d,30d,200d,1y` | ⚠️ 待验证枚举完整性 |

**`order` 合法枚举值（⚠️ 文档列举了部分，以下来自文档原文）：**
`market_cap_desc`、`market_cap_asc`、`volume_asc`、`volume_desc`、`id_asc`、`id_desc`

**响应示例（文档原文）：**
```json
[
  {
    "id": "bitcoin",
    "symbol": "btc",
    "name": "Bitcoin",
    "image": "https://assets.coingecko.com/coins/images/1/large/bitcoin.png?1696501400",
    "current_price": 70187,
    "market_cap": 1381651251183,
    "market_cap_rank": 1,
    "fully_diluted_valuation": 1474623675796,
    "total_volume": 20154184933,
    "high_24h": 70215,
    "low_24h": 68060,
    "price_change_24h": 2126.88,
    "price_change_percentage_24h": 3.12502,
    "market_cap_change_24h": 44287678051,
    "market_cap_change_percentage_24h": 3.31157,
    "circulating_supply": 19675987,
    "total_supply": 21000000,
    "max_supply": 21000000,
    "ath": 73738,
    "ath_change_percentage": -4.77063,
    "ath_date": "2024-03-14T07:10:36.635Z",
    "atl": 67.81,
    "atl_change_percentage": 103455.83335,
    "atl_date": "2013-07-06T00:00:00.000Z",
    "roi": null,
    "last_updated": "2024-04-07T16:49:31.736Z"
  }
]
```

**注意事项：**
- `total_volume` 和 `price_change_percentage_24h` 是**滚动 24 小时**窗口，不是按 UTC 00:00 重置
- `current_price` 和 `market_cap` 可能返回 `null`（数据暂时不可用时），**不等于 0**，必须做 null 判断

---

### 5.4 GET /coins/list `[P2]` ✅

| 字段 | 内容 |
|------|------|
| 完整路径 | `/coins/list` |
| 完整 URL | `https://api.coingecko.com/api/v3/coins/list` |
| 功能 | 获取全量代币列表（id、symbol、name），无需分页 |
| 认证 | 可选 |

**请求参数：**

| 参数名 | 位置 | 类型 | 必填 | 默认值 | 说明 | 来源 |
|--------|------|------|------|--------|------|------|
| `include_platform` | query | boolean | ❌ | `false` | 是否包含各链合约地址 | 文档原文 |
| `status` | query | string | ❌ | `active` | `active` 或 `inactive` | 文档原文 |

**响应示例（文档原文）：**
```json
[
  {
    "id": "bitcoin",
    "symbol": "btc",
    "name": "Bitcoin"
  },
  {
    "id": "1inch",
    "symbol": "1inch",
    "name": "1inch",
    "platforms": {
      "ethereum": "0x111111111117dc0aa78b770fa6a738034120c302",
      "polygon-pos": "0x9c2c5fd7b07e95ee044ddeba0e97a665f142394f"
    }
  }
]
```

**最佳实践（官方文档）：**
> 建议本地缓存此列表，每 24 小时刷新一次，用于 symbol → id 映射，避免重复调用消耗速率配额。

---

### 5.5 GET /search `[P2]` ✅

| 字段 | 内容 |
|------|------|
| 完整路径 | `/search` |
| 完整 URL | `https://api.coingecko.com/api/v3/search` |
| 功能 | 按名称或 symbol 搜索代币、交易所、NFT、分类 |
| 认证 | 可选 |

**请求参数：**

| 参数名 | 位置 | 类型 | 必填 | 说明 | 来源 |
|--------|------|------|------|------|------|
| `query` | query | string | ✅ | 搜索关键词，如 `bitcoin` 或 `BTC` | 文档原文 |

**响应结构（文档原文，仅 coins 部分）：**
```json
{
  "coins": [
    {
      "id": "bitcoin",
      "name": "Bitcoin",
      "symbol": "BTC",
      "market_cap_rank": 1,
      "score": 0
    }
  ],
  "exchanges": [...],
  "icos": [...],
  "categories": [...],
  "nfts": [...]
}
```

---

### 5.6 GET /search/trending `[P1]` ✅

| 字段 | 内容 |
|------|------|
| 完整路径 | `/search/trending` |
| 完整 URL | `https://api.coingecko.com/api/v3/search/trending` |
| 功能 | 获取过去 24h 在 CoinGecko 上搜索量最高的前 7 个代币（按热度排序） |
| 认证 | 可选 |

**请求参数：** 无

**响应结构（文档原文）：**
```json
{
  "coins": [
    {
      "item": {
        "id": "solana",
        "name": "Solana",
        "symbol": "SOL",
        "market_cap_rank": 5,
        "score": 0
      }
    }
  ],
  "nfts": [...],
  "categories": [...]
}
```

---

### 5.7 GET /coins/{id}/market_chart `[P3]` ✅

| 字段 | 内容 |
|------|------|
| 完整路径 | `/coins/{id}/market_chart` |
| 完整 URL | `https://api.coingecko.com/api/v3/coins/{id}/market_chart` |
| 功能 | 获取指定代币的历史价格、市值、交易量时间序列 |
| 认证 | 可选 |

**路径参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `id` | string | ✅ | coin id，如 `bitcoin` |

**请求参数：**

| 参数名 | 位置 | 类型 | 必填 | 说明 | 来源 |
|--------|------|------|------|------|------|
| `vs_currency` | query | string | ✅ | 目标货币，如 `usd` | 文档原文 |
| `days` | query | string/integer | ✅ | 天数，如 `1`、`7`、`30`、`90`、`365`、`max` | 文档原文 |
| `interval` | query | string | ❌ | `⚠️ 待验证`：文档说粒度自动，此参数效果不确定 | ⚠️ 推断 |

**数据粒度（自动，文档原文）：**

| `days` 范围 | 返回粒度 |
|------------|---------|
| `1`（当前时刻起 1 天） | 每 5 分钟 |
| `1`（非当前时刻） | 每小时 |
| `2` ~ `90` | 每小时 |
| > `90` | 每天（UTC 00:00） |

> ⚠️ 注意：无法单次请求超过 90 天的小时级数据。需要更长时间范围请使用 `/market_chart/range`。

**响应结构（文档原文）：**
```json
{
  "prices": [
    [1717200000000, 67500.12],
    [1717203600000, 67800.00]
  ],
  "market_caps": [
    [1717200000000, 1330000000000]
  ],
  "total_volumes": [
    [1717200000000, 25000000000]
  ]
}
```

> 时间戳为 **UNIX 毫秒**（需 ÷ 1000 转换为秒）

---

### 5.8 GET /coins/{id}/market_chart/range `[P3]` ✅

| 字段 | 内容 |
|------|------|
| 完整路径 | `/coins/{id}/market_chart/range` |
| 功能 | 按 UNIX 时间戳范围获取历史数据 |

**请求参数：**

| 参数名 | 位置 | 类型 | 必填 | 说明 | 来源 |
|--------|------|------|------|------|------|
| `vs_currency` | query | string | ✅ | 目标货币 | 文档原文 |
| `from` | query | integer | ✅ | 开始时间（UNIX **秒**） | 文档原文 |
| `to` | query | integer | ✅ | 结束时间（UNIX **秒**） | 文档原文 |

> ⚠️ `from`/`to` 是 UNIX **秒**，响应数据中时间戳是 UNIX **毫秒**，注意单位不同！

---

### 5.9 GET /coins/{id}/history `[P3]` ✅

| 字段 | 内容 |
|------|------|
| 完整路径 | `/coins/{id}/history` |
| 功能 | 获取某代币在特定历史日期的市场快照（价格、市值、交易量） |

**请求参数：**

| 参数名 | 位置 | 类型 | 必填 | 格式 | 来源 |
|--------|------|------|------|------|------|
| `date` | query | string | ✅ | `dd-mm-yyyy`（如 `10-11-2020`） | 文档原文 |
| `localization` | query | boolean | ❌ | 是否包含多语言 | ⚠️ 待验证 |

---

### 5.10 GET /simple/supported_vs_currencies `[P4]` ✅

| 字段 | 内容 |
|------|------|
| 完整路径 | `/simple/supported_vs_currencies` |
| 完整 URL | `https://api.coingecko.com/api/v3/simple/supported_vs_currencies` |
| 功能 | 获取所有合法的 `vs_currency` 值列表 |
| 认证 | 可选 |

**响应（文档原文）：**
```json
["btc","eth","ltc","bch","bnb","usd","eur","jpy","gbp","aud",...]
```

---

### 5.11 GET /simple/token_price/{id} `[P3]`

| 字段 | 内容 |
|------|------|
| 完整路径 | `/simple/token_price/{id}` |
| 功能 | 通过合约地址查询代币价格（适用于长尾链上代币） |

**路径参数：**

| 参数名 | 说明 |
|--------|------|
| `id` | 链的 asset platform id，如 `ethereum`、`polygon-pos` |

**请求参数：**

| 参数名 | 位置 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
| `contract_addresses` | query | string | ✅ | 逗号分隔的合约地址 |
| `vs_currencies` | query | string | ✅ | 目标货币 |

**示例：**
```
https://api.coingecko.com/api/v3/simple/token_price/ethereum?contract_addresses=0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48&vs_currencies=usd
```

---

## 6. 错误处理

### HTTP 状态码

| 状态码 | 含义 | 文档说明（原文） |
|--------|------|----------------|
| `400` | Bad Request | "due to an invalid request and the server could not process the user's request" |
| `401` | Unauthorized | "due to the lack of valid authentication credentials for the requested resource" |
| `403` | Forbidden | "your access is blocked by our server, and we're unable to authorize your request" |
| `408` | Timeout | "server did not receive your complete request within our allowed time frame" |
| `429` | Too Many Requests | "rate limit has reached. The user should reduce the number of calls made" |
| `500` | Internal Server Error | "server has encountered an unexpected issue" |
| `503` | Service Unavailable | "check the API status at https://status.coingecko.com" |
| `1020` | Access Denied | "violation of CDN firewall rule" |
| `10002` | Missing API Key | "pass in x_cg_demo_api_key or x_cg_pro_api_key" |
| `10005` | No Access | "This request is limited Pro API subscribers" |
| `10010` | Invalid API Key | "using Demo key but at pro-api.coingecko.com domain" |
| `10011` | Invalid API Key | "using Pro key but at api.coingecko.com domain" |

### 已知 null 情况（必须处理，文档原文）
> "Data fields like current_price or market_cap may return null when market data is unavailable. A value of null indicates 'no data available' and should not be treated as zero."

---

## 7. 特殊约定

### 时间戳格式
- **请求参数**（`from`、`to`）：UNIX **秒**
- **响应数据**（`prices`、`market_caps`）数组中的时间：UNIX **毫秒**
- **响应数据**中的日期字符串（如 `last_updated`、`ath_date`）：ISO 8601，UTC 时区

### Coin ID 与 Symbol 的区别（⚠️ 最常见错误来源）

| 类型 | 示例 | 用于 API |
|------|------|---------|
| Coin ID | `bitcoin`、`ethereum`、`solana` | ✅ 必须用此值 |
| Symbol | `BTC`、`ETH`、`SOL` | ❌ 不可直接用于 API |

> symbol 不唯一（多个代币可能都叫 `SOL`），必须先通过 `/coins/list` 或 `/search` 获取对应 id。

### 分页

| 端点 | 分页参数 | 每页最大 |
|------|---------|---------|
| `/coins/markets` | `page` + `per_page` | 250 |
| `/coins/list` | 无需分页（返回全量） | — |

### 数据单位
- 价格：以 `vs_currency` 为单位的浮点数
- 市值：以 `vs_currency` 为单位
- 交易量（`total_volume`）：滚动 24 小时，**不在 UTC 00:00 重置**

---

## 8. 待验证项目汇总

| # | 位置 | 问题 | 验证方法 |
|---|------|------|---------|
| 1 | `/simple/price` `precision` 参数 | 合法取值范围（0~18 还是其他）？ | `curl .../simple/price?ids=bitcoin&vs_currencies=usd&precision=5` 是否成功 |
| 2 | 速率限制 / 429 响应体 | 响应体 JSON 具体格式？是否包含 `Retry-After` Header？ | 触发 429 后检查完整响应 |
| 3 | `/coins/markets` `price_change_percentage` | 合法时间段枚举完整列表 | 查看 `/reference/coins-markets` 文档页面 |
| 4 | `/coins/{id}/market_chart` `interval` 参数 | 是否真的存在此参数？效果如何？ | 加 `&interval=hourly` 测试 |
| 5 | `/coins/{id}/history` `localization` | 具体取值范围（true/false？语言代码？） | 读取对应文档页面 |

---

## 9. Smoke Test 脚本

> 在本地配置好 `COINGECKO_API_KEY` 后执行，所有测试应返回 200

```bash
#!/bin/bash
# CoinGecko API Smoke Test
# 使用前：export COINGECKO_API_KEY="your_demo_key_here"

BASE="https://api.coingecko.com/api/v3"
KEY="$COINGECKO_API_KEY"

echo "=== Test 1: Ping（认证验证）==="
curl -s -w "\nHTTP %{http_code}\n" \
  -H "x-cg-demo-api-key: $KEY" \
  "$BASE/ping"

echo ""
echo "=== Test 2: Simple Price ==="
curl -s -w "\nHTTP %{http_code}\n" \
  -H "x-cg-demo-api-key: $KEY" \
  "$BASE/simple/price?ids=bitcoin&vs_currencies=usd"

echo ""
echo "=== Test 3: Coins Markets ==="
curl -s -w "\nHTTP %{http_code}\n" \
  -H "x-cg-demo-api-key: $KEY" \
  "$BASE/coins/markets?vs_currency=usd&per_page=3&page=1" | python3 -m json.tool | head -30

echo ""
echo "=== Test 4: Search ==="
curl -s -w "\nHTTP %{http_code}\n" \
  -H "x-cg-demo-api-key: $KEY" \
  "$BASE/search?query=bitcoin" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['coins'][:2])"

echo ""
echo "=== Test 5: Trending ==="
curl -s -w "\nHTTP %{http_code}\n" \
  -H "x-cg-demo-api-key: $KEY" \
  "$BASE/search/trending"

echo ""
echo "=== Test 6: 错误响应格式（无效 coin id）==="
curl -s -v -H "x-cg-demo-api-key: $KEY" \
  "$BASE/coins/INVALID_COIN_XXXXX_9999" 2>&1 | grep -E "HTTP|{|}"

echo ""
echo "=== Test 7: 参数错误（验证 429 错误体格式，快速连续调用）==="
for i in {1..35}; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "x-cg-demo-api-key: $KEY" "$BASE/ping")
  echo "Request $i: HTTP $STATUS"
  if [ "$STATUS" = "429" ]; then
    # 打印完整 429 响应体
    curl -s -H "x-cg-demo-api-key: $KEY" "$BASE/ping"
    break
  fi
done
```

---

## 10. 集成注意事项（供 Claude Code 参考）

1. **coin id 是前置依赖**：几乎所有端点都需要 coin id。Agent 启动时应调用 `/coins/list` 建立 `symbol→id` 的本地映射，缓存 24 小时，避免每次查询都消耗速率配额。

2. **Demo 月度配额 10,000 次紧张**：投研 Agent 频繁刷新数据时，优先使用批量端点（`/coins/markets`），避免逐个调用 `/simple/price`。

3. **null 值必须处理**：`current_price`、`market_cap`、`total_volume` 等字段均可能为 `null`，代码中必须有 null guard，不能直接做数学运算。

4. **历史数据粒度陷阱**：Agent 需要小时级数据时，`days` 参数不能超过 90，否则自动降级为日线数据。

5. **Demo Key 限于 `api.coingecko.com`**：配置环境变量时如果同时有 Demo 和 Pro Key，必须根据 Key 类型选择不同 Base URL，不要混用。

6. **搜索结果需要人工确认**：`/search` 可能返回多个同名代币（如多个链的 `USDC`），需要根据 `market_cap_rank` 取最高权重的结果，或提示用户确认。

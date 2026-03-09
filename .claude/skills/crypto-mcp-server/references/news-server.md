# News MCP Server — 详细设计

## 数据源策略

优先级排序：
1. **CryptoPanic API** (免费 tier: 需注册, 200 req/hour) — 结构化新闻聚合
2. **Web Search Fallback** — 用搜索引擎抓取（当 CryptoPanic 不可用时）
3. **本地模拟数据** — Demo 用途

## 工具清单

### 1. get_latest_news(coin_id: str, limit: int = 10) → dict
- **功能**：获取指定代币的最新新闻
- **CryptoPanic API**：`GET /api/v1/posts/?auth_token={token}&currencies={symbol}&limit={limit}`
- **返回 schema**：
```json
{
  "coin_id": "arbitrum",
  "articles": [
    {
      "title": "Arbitrum announces major upgrade",
      "source": "CoinDesk",
      "published_at": "2025-03-09T10:00:00Z",
      "url": "https://...",
      "sentiment": "positive"
    }
  ],
  "total_count": 10,
  "fetched_at": "2025-03-09T12:00:00Z"
}
```

### 2. search_news(query: str, limit: int = 10) → dict
- **功能**：关键词搜索 crypto 新闻
- **实现方式**：CryptoPanic search 或 web search fallback
- **返回 schema**：同 get_latest_news

### 3. analyze_sentiment(headlines: list[str]) → dict
- **功能**：对新闻标题列表做情感分析
- **实现方式**：用 LLM 做 batch sentiment classification
- **返回 schema**：
```json
{
  "overall_sentiment": "positive",
  "sentiment_score": 0.65,
  "breakdown": {
    "positive": 6,
    "neutral": 3,
    "negative": 1
  },
  "key_positive": ["Arbitrum announces major upgrade"],
  "key_negative": ["Regulatory concerns emerge"]
}
```

### 4. get_social_metrics(coin_id: str) → dict
- **功能**：社交媒体热度指标
- **数据源**：CoinGecko `/coins/{id}` 的 community_data 字段
- **返回 schema**：
```json
{
  "coin_id": "arbitrum",
  "twitter_followers": 850000,
  "reddit_subscribers": 45000,
  "github_stars": 2300,
  "developer_activity_score": 78
}
```

## CryptoPanic API 注意事项

- 免费注册获取 auth_token
- 代币用 symbol（如 `ARB`），不是 coin_id
- `filter=important` 参数可以只获取重要新闻
- 返回值中 `votes` 字段有 positive/negative 投票
- 如果无 API token，可以用 `public=true` 参数获取公开新闻（较少）

## LLM 情感分析 Prompt

```python
SENTIMENT_PROMPT = """分析以下加密货币新闻标题的情感倾向。

标题列表:
{headlines}

输出 JSON:
{{
  "results": [
    {{"title": "标题", "sentiment": "positive|neutral|negative", "confidence": 0.0-1.0}}
  ],
  "overall": "positive|neutral|negative",
  "score": -1.0 到 1.0 (负数偏空, 正数偏多)
}}

评判标准:
- positive: 利好消息（升级、合作、融资、用户增长）
- negative: 利空消息（黑客、监管、团队出走、代币抛售）
- neutral: 中性或事实性报道
"""
```

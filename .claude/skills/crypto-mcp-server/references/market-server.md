# Market MCP Server — 详细设计

## 工具清单

### 1. get_price(coin_id: str) → dict
- **功能**：实时价格 + 24h 涨跌 + 市值
- **API**：`GET /simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true`
- **返回 schema**：
```json
{
  "coin_id": "arbitrum",
  "price_usd": 1.23,
  "change_24h_pct": -2.5,
  "market_cap_usd": 1234567890,
  "last_updated": "2025-03-09T12:00:00Z"
}
```

### 2. get_price_history(coin_id: str, days: int = 30) → dict
- **功能**：历史价格走势（用于画图和计算技术指标）
- **API**：`GET /coins/{coin_id}/market_chart?vs_currency=usd&days={days}`
- **返回 schema**：
```json
{
  "coin_id": "arbitrum",
  "days": 30,
  "prices": [
    {"timestamp": "2025-02-07T00:00:00Z", "price": 1.15},
    {"timestamp": "2025-02-08T00:00:00Z", "price": 1.18}
  ],
  "total_data_points": 30
}
```

### 3. get_market_overview() → dict
- **功能**：全市场概览（总市值、BTC 占比）
- **API**：`GET /global`
- **返回 schema**：
```json
{
  "total_market_cap_usd": 2500000000000,
  "btc_dominance_pct": 52.3,
  "eth_dominance_pct": 17.1,
  "active_cryptocurrencies": 14000,
  "market_cap_change_24h_pct": 1.5
}
```

### 4. calculate_technical_indicators(coin_id: str, indicators: list[str]) → dict
- **功能**：基于历史价格计算技术指标
- **实现方式**：先调 get_price_history 获取数据，然后本地计算
- **支持的指标**：MA7, MA25, MA99, RSI14, BOLL
- **返回 schema**：
```json
{
  "coin_id": "arbitrum",
  "indicators": {
    "ma7": 1.20,
    "ma25": 1.15,
    "ma99": 1.08,
    "rsi14": 55.3,
    "bollinger": {"upper": 1.35, "middle": 1.20, "lower": 1.05}
  },
  "trend_summary": "neutral",
  "calculated_at": "2025-03-09T12:00:00Z"
}
```

**技术指标计算参考**：

```python
import numpy as np

def calculate_ma(prices: list[float], window: int) -> float:
    if len(prices) < window:
        return prices[-1]
    return np.mean(prices[-window:])

def calculate_rsi(prices: list[float], period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0  # 默认中性
    deltas = np.diff(prices[-(period+1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger(prices: list[float], window: int = 20) -> dict:
    if len(prices) < window:
        mid = prices[-1]
        return {"upper": mid, "middle": mid, "lower": mid}
    recent = prices[-window:]
    mid = np.mean(recent)
    std = np.std(recent)
    return {"upper": mid + 2*std, "middle": mid, "lower": mid - 2*std}
```

### 5. get_coin_info(coin_id: str) → dict
- **功能**：代币基础信息（描述、官网、社区链接等）
- **API**：`GET /coins/{coin_id}?localization=false&tickers=false&market_data=false`
- **返回 schema**：
```json
{
  "coin_id": "arbitrum",
  "name": "Arbitrum",
  "symbol": "ARB",
  "description": "Arbitrum is a Layer 2 scaling solution...",
  "homepage": "https://arbitrum.io",
  "categories": ["Layer 2", "Ethereum Ecosystem"]
}
```

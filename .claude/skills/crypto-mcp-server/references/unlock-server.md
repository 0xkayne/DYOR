# Token Unlock MCP Server — 详细设计

## 数据源策略

代币解锁数据不像行情数据那样有成熟的免费 API，因此采用混合策略：
1. **本地 JSON 数据**：主流代币（ARB, OP, APT, SUI, SEI, TIA 等）的解锁计划预置
2. **DeFiLlama Unlocks API**：`https://api.llama.fi/protocol/{protocol}` 作为补充
3. **CoinGecko tickers**：获取流通量/总量比例

## 工具清单

### 1. get_unlock_schedule(token_symbol: str, days_ahead: int = 90) → dict
- **功能**：查询未来的代币解锁事件
- **数据源**：本地 JSON + DeFiLlama
- **返回 schema**：
```json
{
  "token_symbol": "ARB",
  "unlock_events": [
    {
      "date": "2025-03-16",
      "amount": 92650000,
      "amount_usd": 113000000,
      "pct_of_circulating": 2.34,
      "category": "team",
      "description": "Team and advisor vesting unlock"
    }
  ],
  "total_unlock_amount": 185300000,
  "total_unlock_value_usd": 226000000,
  "risk_level": "high",
  "risk_reasoning": "未来90天内将解锁流通量的4.7%，其中团队解锁占比大"
}
```

### 2. get_token_distribution(token_symbol: str) → dict
- **功能**：代币分配和持仓分布
- **数据源**：本地 JSON
- **返回 schema**：
```json
{
  "token_symbol": "ARB",
  "total_supply": 10000000000,
  "circulating_supply": 3960000000,
  "circulating_ratio": 0.396,
  "distribution": {
    "team_and_advisors": {"pct": 26.94, "vesting_end": "2027-03"},
    "investors": {"pct": 17.53, "vesting_end": "2027-03"},
    "dao_treasury": {"pct": 42.78, "status": "governed by DAO"},
    "airdrop": {"pct": 12.75, "status": "fully distributed"}
  },
  "top_holders_concentration": {
    "top10_pct": 48.5,
    "top50_pct": 72.3
  }
}
```

### 3. get_vesting_info(token_symbol: str) → dict
- **功能**：完整的 vesting schedule 信息
- **返回 schema**：
```json
{
  "token_symbol": "ARB",
  "tge_date": "2023-03-23",
  "vesting_schedules": [
    {
      "category": "team",
      "total_allocation": 2694000000,
      "cliff_months": 12,
      "vesting_months": 48,
      "start_date": "2023-03-23",
      "end_date": "2027-03-23",
      "unlocked_pct": 45.2,
      "remaining": 1477000000
    }
  ]
}
```

## 本地数据格式

预置数据存放在 `data/token_unlocks/` 目录：

```
data/token_unlocks/
├── ARB.json
├── OP.json
├── APT.json
├── SUI.json
├── SEI.json
├── TIA.json
└── _template.json
```

每个文件的 schema：
```json
{
  "symbol": "ARB",
  "name": "Arbitrum",
  "total_supply": 10000000000,
  "tge_date": "2023-03-23",
  "distribution": { ... },
  "vesting_schedules": [ ... ],
  "upcoming_unlocks": [
    {
      "date": "2025-03-16",
      "amount": 92650000,
      "category": "team",
      "description": "Monthly team vesting"
    }
  ]
}
```

## 解锁风险评估逻辑

```python
def assess_unlock_risk(unlock_events: list, circulating_supply: float) -> dict:
    """评估解锁对价格的潜在影响。"""
    total_unlock = sum(e["amount"] for e in unlock_events)
    unlock_ratio = total_unlock / circulating_supply
    
    # 分类评估
    team_unlock = sum(e["amount"] for e in unlock_events if e["category"] == "team")
    investor_unlock = sum(e["amount"] for e in unlock_events if e["category"] == "investor")
    
    # 风险评级
    if unlock_ratio > 0.05:  # 超过流通量 5%
        risk = "high"
    elif unlock_ratio > 0.02:  # 2-5%
        risk = "medium"
    else:
        risk = "low"
    
    # 团队/投资人解锁风险更高（抛售意愿强）
    if (team_unlock + investor_unlock) / max(total_unlock, 1) > 0.7:
        risk = "high" if risk != "high" else risk
    
    reasoning_parts = []
    reasoning_parts.append(
        f"未来解锁量占流通量 {unlock_ratio*100:.1f}%"
    )
    if team_unlock > 0:
        reasoning_parts.append(
            f"其中团队解锁 {team_unlock/1e6:.0f}M"
        )
    
    return {
        "risk_level": risk,
        "risk_reasoning": "，".join(reasoning_parts),
    }
```

## DeFiLlama API 补充

当本地数据没有覆盖某个代币时，尝试 DeFiLlama：

```python
async def fetch_from_defillama(protocol: str) -> dict | None:
    """从 DeFiLlama 获取协议数据作为补充。"""
    client = await get_client()
    try:
        resp = await client.get(f"https://api.llama.fi/protocol/{protocol}")
        resp.raise_for_status()
        data = resp.json()
        return {
            "tvl": data.get("tvl"),
            "mcap_to_tvl": data.get("mcap/tvl"),
            "category": data.get("category"),
        }
    except Exception:
        return None
```

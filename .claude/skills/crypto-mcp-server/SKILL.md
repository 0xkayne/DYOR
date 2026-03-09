---
name: crypto-mcp-server
description: >
  加密货币数据 MCP (Model Context Protocol) Server 开发技能。用于构建为 AI Agent 提供 crypto 
  实时数据的 MCP Server，包括行情数据（CoinGecko）、新闻聚合（CryptoPanic）、代币解锁计划（TokenUnlocks）、
  链上数据等外部 API 的 MCP 封装，以及 MCP 工具动态注册与发现机制。
  当用户需要以下任务时触发此技能：创建 crypto 相关 MCP Server、封装 CoinGecko/CoinMarketCap API、
  实现新闻聚合 MCP 工具、构建代币解锁查询服务、实现 MCP 工具注册中心、
  让 Agent 能动态发现和选择 MCP 工具。即使用户只是提到 "MCP server"、"crypto API"、
  "行情数据"、"CoinGecko"、"代币解锁"、"MCP tool"、"FastMCP"、"tool registry"、
  "动态工具发现" 等关键词，也应触发此技能。
  不适用于非 crypto 领域的 MCP Server（通用 MCP 开发请参考 mcp-builder 技能）。
---

# Crypto MCP Server Skill

为 AI Agent 构建加密货币数据服务层。本技能专注于用 FastMCP 封装 crypto 数据 API 为 MCP 工具，
并实现动态工具注册与发现机制。

## 核心理念

MCP Server 是 Agent 获取外部数据的桥梁。在 crypto 投研场景中，Agent 需要实时行情、
新闻舆情、代币经济学数据。将这些数据源封装为 MCP Server 有两个好处：

1. **标准化接口**：所有数据源通过统一的 MCP 协议暴露，Agent 不需要关心底层 API 差异
2. **动态发现**：Agent 运行时可以查询有哪些工具可用，而不是硬编码工具调用

---

## FastMCP Server 模板

每个 MCP Server 遵循以下标准结构：

```python
"""
{Server 名称} — DYOR MCP Server
提供 {功能描述}
"""
import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from src.config import settings

mcp = FastMCP("{server-name}")

# ========== Pydantic Models ==========
# 用 Pydantic 规范化所有返回值

class PriceData(BaseModel):
    coin_id: str
    price_usd: float
    change_24h_pct: float = Field(description="24小时涨跌幅百分比")
    market_cap_usd: float
    volume_24h_usd: float
    last_updated: str

# ========== HTTP Client ==========
# 全局复用，不要每次调用都创建新 client

_client: httpx.AsyncClient | None = None

async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            headers={"Accept": "application/json"},
        )
    return _client

# ========== Tools ==========

@mcp.tool()
async def get_price(coin_id: str) -> dict:
    """获取指定代币的实时价格、24h涨跌幅和市值。

    用于快速了解某个代币的当前市场表现。
    
    Args:
        coin_id: CoinGecko 代币 ID，如 'bitcoin', 'ethereum', 'arbitrum'
    
    Returns:
        包含 price_usd, change_24h_pct, market_cap_usd, volume_24h_usd 的字典
    """
    # 实现...

# ========== Entry Point ==========

if __name__ == "__main__":
    mcp.run()
```

---

## Tool Docstring 规范

**这是整个 skill 中最重要的部分。** LLM 完全依赖 docstring 来理解工具的用途和使用方式。
写不好 docstring = Agent 不会正确调用你的工具。

### 好的 docstring 包含：

1. **功能描述**（第一行）：这个工具做什么
2. **使用场景**（第二段）：什么时候应该用这个工具
3. **Args**：每个参数的含义、格式、示例值
4. **Returns**：返回什么数据

```python
# ✅ 完整的好 docstring
@mcp.tool()
async def get_token_unlock_schedule(
    token_symbol: str, 
    days_ahead: int = 90
) -> dict:
    """查询代币的未来解锁计划，包括解锁日期、数量和占流通量比例。

    用于分析代币的卖压风险。大量代币解锁通常会导致短期价格下行压力，
    因此了解未来的解锁节奏是投资决策的重要参考。

    Args:
        token_symbol: 代币符号（大写），如 'ARB', 'OP', 'APT', 'SUI'
        days_ahead: 查询未来多少天内的解锁事件，默认90天，最大365天

    Returns:
        包含以下字段的字典:
        - unlock_events: 解锁事件列表，每个事件有 date, amount, 
          pct_of_circulating, category (team/investor/ecosystem)
        - total_unlock_value_usd: 所有事件的总解锁价值
        - risk_level: 解锁风险评级 (high/medium/low)
    """
```

```python
# ❌ 差的 docstring — Agent 无法理解
@mcp.tool()
async def get_unlock(symbol: str) -> dict:
    """获取解锁数据"""
```

---

## 错误处理模板

每个 tool 必须处理所有外部 API 可能的异常，**永远不能让未捕获异常传播到 Agent**。

```python
@mcp.tool()
async def get_price(coin_id: str) -> dict:
    """..."""
    client = await get_client()
    try:
        resp = await client.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        
        if coin_id not in data:
            return {"error": "not_found", "coin_id": coin_id,
                    "message": f"代币 '{coin_id}' 未找到，请检查 CoinGecko ID"}
        
        return PriceData(
            coin_id=coin_id,
            price_usd=data[coin_id]["usd"],
            change_24h_pct=data[coin_id].get("usd_24h_change", 0),
            market_cap_usd=data[coin_id].get("usd_market_cap", 0),
            volume_24h_usd=0,  # simple/price 不含 volume
            last_updated=str(data[coin_id].get("last_updated_at", "")),
        ).model_dump()
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            return {"error": "rate_limited", "retry_after_seconds": 60,
                    "message": "CoinGecko API 请求频率超限，请稍后重试"}
        return {"error": f"http_{e.response.status_code}", "coin_id": coin_id}
    except httpx.TimeoutException:
        return {"error": "timeout", "coin_id": coin_id,
                "message": "请求超时，CoinGecko API 可能暂时不可用"}
    except Exception as e:
        return {"error": "unexpected", "detail": str(e), "coin_id": coin_id}
```

**关键原则：**
- 错误返回值也是 dict（不是 raise exception）
- 包含 `error` 字段让 Agent 能识别失败
- 包含 `message` 字段给出人类可读的说明
- Rate limit 返回 `retry_after_seconds`

---

## 三个 MCP Server 规划

详见 `references/` 目录下的各 Server 详细设计：

| Server | 文件 | 参考文档 | 外部 API |
|--------|------|----------|----------|
| crypto-market | market_server.py | `references/market-server.md` | CoinGecko Free |
| crypto-news | news_server.py | `references/news-server.md` | CryptoPanic / Web Search |
| token-unlock | unlock_server.py | `references/unlock-server.md` | 本地数据 + DeFiLlama |

---

## MCP Tool Registry（动态发现）

除了单独的 Server，还需要一个 Registry 让 Agent 在运行时发现可用工具：

```python
# src/mcp_servers/registry.py
from dataclasses import dataclass

@dataclass
class ToolMeta:
    name: str
    description: str
    server: str
    parameters: dict

class MCPToolRegistry:
    """工具注册中心：Agent 查询可用工具并选择最合适的组合。"""
    
    def __init__(self):
        self._tools: dict[str, ToolMeta] = {}
    
    def register(self, tool: ToolMeta):
        self._tools[tool.name] = tool
    
    def list_tools(self, category: str | None = None) -> list[ToolMeta]:
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if category in t.server]
        return tools
    
    async def discover_for_task(self, task_description: str, llm) -> list[ToolMeta]:
        """用 LLM 根据任务描述选择最合适的工具组合。"""
        all_tools = self.list_tools()
        tool_descriptions = "\n".join(
            f"- {t.name}: {t.description}" for t in all_tools
        )
        prompt = f"""从以下可用工具中，选择完成任务所需的最小工具集合。
        
任务: {task_description}

可用工具:
{tool_descriptions}

输出 JSON 数组（工具名列表）: ["tool_name_1", "tool_name_2"]"""
        
        result = await llm.ainvoke(prompt)
        selected_names = json.loads(result)
        return [self._tools[n] for n in selected_names if n in self._tools]
```

---

## CoinGecko API 注意事项

- 免费 tier 限制：30 calls/min
- 不需要 API key（基础端点）
- coin_id 是小写字符串（如 `"bitcoin"`, `"arbitrum"`），不是 symbol
- `/simple/price` 最轻量，只返回价格
- `/coins/{id}/market_chart` 返回历史数据，可选 1/7/14/30/90/365 天
- 文档：https://docs.coingecko.com/reference/introduction

---

## 禁止事项

- ❌ 不要在每次 tool 调用时创建新的 httpx.AsyncClient
- ❌ 不要用同步 requests 库
- ❌ 不要硬编码 API key（读环境变量）
- ❌ 不要返回原始 API JSON（用 Pydantic model 规范化）
- ❌ 不要让异常传播到 Agent（必须 try/except）
- ❌ 不要忘记 timeout 设置（默认 10s）
- ❌ Tool docstring 不要少于 3 行

# DYOR — 产品需求文档 (PRD)

## 1. 产品概述

**产品名称**: DYOR— AI 驱动的加密货币投研助手  
**版本**: v1.0  
**定位**: 多智能体协作的加密货币投资研究分析系统，通过 RAG 技术整合私有投研报告，结合实时市场数据，为用户提供结构化投资建议。

**核心价值主张**: 将分散在多篇投研报告中的深度分析与实时市场动态、代币经济学数据统一编排，通过多 Agent 协作生成综合投资建议，帮助用户在信息过载的 crypto 市场中做出更理性的决策。

---

## 2. 用户画像

**主要用户**: 具备一定 crypto 知识的个人投资者/研究员  
**使用场景**: 在考虑是否投资某个代币前，希望快速获取该项目的基本面评估、实时市场状态、近期新闻舆情和筹码结构变化的综合分析。

---

## 3. 功能需求

### 3.1 核心工作流 (Workflows)

#### WF-1: Deep Dive — 单项目深度分析
- **触发**: 用户输入如 "帮我分析 Arbitrum 是否值得投资"
- **流程**: RAG 检索项目基本面 → 获取实时行情 → 聚合近期新闻 → 查询解锁计划 → 综合分析 → 质量审查 → 输出结构化报告
- **输出**: 包含基本面评估、市场数据、新闻情感、筹码分析的结构化 JSON + 可视化报告

#### WF-2: Compare — 项目对比分析
- **触发**: 用户输入如 "对比 Arbitrum 和 Optimism 哪个更值得投资"
- **流程**: 对两个项目分别执行 Deep Dive 流程 → 生成对比维度表 → 综合对比分析
- **输出**: 多维度雷达图 + 对比表格 + 综合推荐

#### WF-3: Morning Brief — 持仓简报
- **触发**: 用户输入如 "给我今天的持仓简报" (需提前配置关注列表)
- **流程**: 批量获取关注代币的价格变动 → 扫描重大新闻 → 检查解锁事件 → 生成简报
- **输出**: 概览 Dashboard + 异常预警

#### WF-4: 知识问答 — 投研知识查询
- **触发**: 用户输入如 "这个项目的团队背景是什么"
- **流程**: 纯 RAG 检索 → 直接回答（附引用来源）
- **输出**: 简洁回答 + 引用的报告段落

### 3.2 功能模块

| 模块 | 描述 | 优先级 |
|------|------|--------|
| RAG 知识库 | 导入、索引、检索私有投研报告 | P0 |
| 实时行情 | 价格、市值、交易量、历史走势 | P0 |
| 新闻聚合 | 近期新闻抓取 + 情感分析 | P0 |
| 代币解锁 | 解锁计划查询、筹码分布变化 | P0 |
| 综合分析引擎 | 多维度结构化分析 + 投资建议 | P0 |
| 质量审查 | 报告质量检查 + 合规 guardrails | P1 |
| 知识图谱 | 项目关系图谱增强检索 | P1 |
| 用户记忆 | 记忆用户偏好和历史对话 | P2 |
| 可视化报告 | 图表 + Dashboard 渲染 | P1 |

### 3.3 输出规范

Analyst Agent 生成的结构化输出 JSON Schema:

```json
{
  "project_name": "string",
  "analysis_date": "ISO8601",
  "workflow_type": "deep_dive | compare | brief",
  "fundamental_analysis": {
    "summary": "string",
    "team_score": "1-10",
    "product_score": "1-10",
    "track_score": "1-10",
    "tokenomics_score": "1-10",
    "sources": ["报告引用列表"]
  },
  "market_data": {
    "current_price": "number",
    "price_change_24h": "percent",
    "price_change_7d": "percent",
    "market_cap": "number",
    "volume_24h": "number",
    "technical_indicators": {}
  },
  "news_sentiment": {
    "overall_sentiment": "positive | neutral | negative",
    "key_events": [],
    "sentiment_score": "-1 to 1"
  },
  "tokenomics": {
    "next_unlock": {},
    "circulating_supply_ratio": "percent",
    "top_holders_concentration": "percent"
  },
  "investment_recommendation": {
    "rating": "strong_buy | buy | hold | sell | strong_sell",
    "confidence": "0-1",
    "key_reasons": [],
    "risk_factors": [],
    "disclaimer": "string"
  }
}
```

### 3.4 Guardrails 规则

1. 所有输出必须包含投资风险免责声明
2. 禁止使用绝对化表述（"一定涨"、"必须买"）
3. 引用 RAG 内容时必须标注来源报告名称和段落
4. 如果 RAG 知识库中无相关信息，必须明确告知用户
5. 价格数据必须标注时间戳，避免用过时数据误导

---

## 4. 非功能需求

| 需求 | 指标 |
|------|------|
| 响应时间 | Deep Dive 全流程 < 30s（流式输出首 token < 3s）|
| 并发 | 支持单用户多轮对话 |
| RAG 准确度 | Faithfulness > 0.8 (RAGAS) |
| 可用性 | 本地部署，支持 Docker 一键启动 |

---

## 5. 技术约束

- LLM: Claude API (claude-sonnet-4-20250514) 或 DeepSeek V3
- 向量数据库: ChromaDB (本地开发) / Qdrant (生产)
- Python >= 3.11
- 前端: Streamlit (MVP) → React (可选迭代)
- 所有外部数据源通过 MCP Server 封装

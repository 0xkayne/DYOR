# DYOR — 技术设计文档 (TDD)

## 1. 系统架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                        Frontend (Streamlit)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│  │ Chat UI  │ │Dashboard │ │ Compare  │ │ Report Renderer  │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘    │
└──────────────────────┬───────────────────────────────────────────┘
                       │ HTTP/WebSocket
┌──────────────────────▼───────────────────────────────────────────┐
│                     FastAPI Backend                                │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────────────────┐  │
│  │ /chat (WS)  │ │ /analyze     │ │ /reports (CRUD)           │  │
│  └─────────────┘ └──────────────┘ └───────────────────────────┘  │
└──────────────────────┬───────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────┐
│                  LangGraph Orchestration Layer                     │
│                                                                    │
│  ┌────────┐    ┌──────────┐                                       │
│  │ Router │───▶│ Planner  │                                       │
│  └────────┘    └──────────┘                                       │
│                     │                                              │
│       ┌─────────────┼─────────────┬─────────────┐                 │
│       ▼             ▼             ▼             ▼                 │
│  ┌─────────┐  ┌──────────┐ ┌──────────┐ ┌───────────┐           │
│  │Agentic  │  │ Market   │ │  News    │ │Tokenomics │           │
│  │  RAG    │  │  Agent   │ │  Agent   │ │  Agent    │           │
│  │+GraphRAG│  │          │ │          │ │           │           │
│  └─────────┘  └──────────┘ └──────────┘ └───────────┘           │
│       │             │             │             │                 │
│       └─────────────┼─────────────┴─────────────┘                 │
│                     ▼                                              │
│              ┌───────────┐     ┌───────────┐                      │
│              │  Analyst   │────▶│  Critic   │──┐                  │
│              └───────────┘     └───────────┘  │ 不合格则循环       │
│                     ▲                          │                   │
│                     └──────────────────────────┘                   │
└──────────────────────────────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌────────────┐
│  MCP Servers │ │ RAG      │ │ Knowledge  │
│ (市场/新闻/  │ │ Engine   │ │ Graph      │
│  解锁数据)   │ │ (向量DB) │ │ (Neo4j/NX) │
└──────────────┘ └──────────┘ └────────────┘
```

---

## 2. 项目目录结构

```
dyor/
├── pyproject.toml                 # 项目依赖 (uv/poetry)
├── .env.example                   # 环境变量模板
├── docker-compose.yml             # 一键启动
├── CLAUDE.md                      # Claude Code 项目级指导
├── .claude/
│   └── agents/                    # subagent 配置文件
│       ├── rag-developer.md
│       ├── mcp-developer.md
│       ├── agent-developer.md
│       ├── api-developer.md
│       └── frontend-developer.md
│
├── src/
│   ├── __init__.py
│   ├── config.py                  # 全局配置 (pydantic-settings)
│   │
│   ├── rag/                       # RAG 引擎模块
│   │   ├── __init__.py
│   │   ├── ingest.py              # 文档加载 + chunking pipeline
│   │   ├── embeddings.py          # Embedding 模型封装
│   │   ├── vectorstore.py         # 向量数据库操作
│   │   ├── retriever.py           # 高级检索策略 (hybrid/rerank/agentic)
│   │   ├── graph_rag.py           # 知识图谱增强检索
│   │   └── evaluator.py           # RAG 质量评估 (RAGAS)
│   │
│   ├── mcp_servers/               # MCP Server 模块
│   │   ├── __init__.py
│   │   ├── market_server.py       # CoinGecko 行情 MCP
│   │   ├── news_server.py         # 新闻聚合 MCP
│   │   ├── unlock_server.py       # 代币解锁 MCP
│   │   └── registry.py            # MCP 工具注册与动态发现
│   │
│   ├── agents/                    # Agent 定义模块
│   │   ├── __init__.py
│   │   ├── router.py              # 路由智能体
│   │   ├── planner.py             # 计划智能体
│   │   ├── rag_agent.py           # RAG 智能体 (含 self-RAG 循环)
│   │   ├── market_agent.py        # 行情智能体
│   │   ├── news_agent.py          # 新闻智能体
│   │   ├── tokenomics_agent.py    # 代币经济学智能体
│   │   ├── analyst.py             # 综合分析智能体
│   │   ├── critic.py              # 质量审查智能体
│   │   └── prompts/               # 各 Agent 的 system prompt
│   │       ├── router_prompt.py
│   │       ├── planner_prompt.py
│   │       ├── rag_prompt.py
│   │       ├── market_prompt.py
│   │       ├── news_prompt.py
│   │       ├── tokenomics_prompt.py
│   │       ├── analyst_prompt.py
│   │       └── critic_prompt.py
│   │
│   ├── graph/                     # LangGraph 工作流
│   │   ├── __init__.py
│   │   ├── state.py               # AgentState 定义
│   │   ├── workflow.py            # 主工作流编排
│   │   ├── nodes.py               # 图节点定义
│   │   └── edges.py               # 条件边定义
│   │
│   ├── memory/                    # 记忆模块
│   │   ├── __init__.py
│   │   ├── checkpointer.py        # LangGraph checkpoint
│   │   └── user_preferences.py    # 用户偏好存储
│   │
│   ├── schemas/                   # 数据模型
│   │   ├── __init__.py
│   │   ├── analysis.py            # 分析结果 schema
│   │   ├── market.py              # 市场数据 schema
│   │   ├── news.py                # 新闻数据 schema
│   │   └── tokenomics.py          # 代币经济学 schema
│   │
│   └── guardrails/                # 安全护栏
│       ├── __init__.py
│       ├── output_validator.py    # 输出校验
│       └── disclaimer.py          # 免责声明注入
│
├── api/                           # FastAPI 后端
│   ├── __init__.py
│   ├── main.py                    # FastAPI app
│   ├── routes/
│   │   ├── chat.py                # WebSocket 聊天接口
│   │   ├── analyze.py             # 分析接口
│   │   └── reports.py             # 报告管理接口
│   └── middleware/
│       └── streaming.py           # 流式响应中间件
│
├── ui/                            # Streamlit 前端
│   ├── app.py                     # 主入口
│   ├── pages/
│   │   ├── chat.py                # 对话页
│   │   ├── dashboard.py           # Dashboard 页
│   │   └── compare.py             # 对比分析页
│   └── components/
│       ├── charts.py              # 图表组件
│       └── report_card.py         # 报告卡片组件
│
├── data/
│   ├── reports/                   # 投研报告原始文件
│   └── knowledge_graph/           # 知识图谱数据
│
├── eval/                          # 评估模块
│   ├── test_cases.json            # 黄金测试用例
│   ├── run_eval.py                # 评估脚本
│   └── metrics.py                 # 指标计算
│
└── tests/                         # 单元测试
    ├── test_rag/
    ├── test_agents/
    ├── test_mcp/
    └── test_api/
```

---

## 3. 核心模块设计

### 3.1 RAG Engine

#### 3.1.1 文档处理 Pipeline

```python
# src/rag/ingest.py 核心流程
class DocumentIngester:
    """
    Pipeline: Load → Clean → Chunk → Enrich Metadata → Embed → Store
    """
    def ingest(self, file_path: str):
        # 1. 加载文档 (支持 .md, .pdf, .txt)
        doc = self.loader.load(file_path)
        
        # 2. 语义切分 (非固定大小)
        chunks = self.semantic_chunker.split(doc)
        
        # 3. Metadata 增强
        for chunk in chunks:
            chunk.metadata.update({
                "project_name": self.extract_project_name(chunk),
                "report_date": self.extract_date(file_path),
                "analysis_dimension": self.classify_dimension(chunk),
                # 维度: team/product/track/tokenomics/valuation/risks
            })
        
        # 4. 生成 embedding 并存储
        self.vectorstore.add_documents(chunks)
        
        # 5. 更新知识图谱
        self.graph_rag.update_graph(chunks)
```

#### 3.1.2 高级检索策略

```python
# src/rag/retriever.py
class AgenticRetriever:
    """
    实现 Agentic RAG: Agent 自主决定检索策略，而非固定 pipeline
    """
    async def retrieve(self, query: str, state: AgentState) -> RetrievalResult:
        # Step 1: Query Analysis — 判断是否需要检索
        analysis = await self.llm.analyze_query(query)
        if analysis.can_answer_directly:
            return RetrievalResult(strategy="direct", docs=[])
        
        # Step 2: Query Decomposition — 复杂问题拆解
        sub_queries = await self.decompose_query(query)
        
        # Step 3: Hybrid Search — 向量 + BM25 融合
        candidates = []
        for sq in sub_queries:
            dense_results = self.vectorstore.similarity_search(sq, k=10)
            sparse_results = self.bm25_retriever.search(sq, k=10)
            fused = self.reciprocal_rank_fusion(dense_results, sparse_results)
            candidates.extend(fused)
        
        # Step 4: Graph-enhanced — 知识图谱补充关联项目
        graph_results = self.graph_rag.find_related(query, candidates)
        candidates.extend(graph_results)
        
        # Step 5: Reranking — Cross-encoder 重排序
        reranked = self.reranker.rerank(query, candidates, top_k=5)
        
        # Step 6: Self-RAG Check — 验证结果充分性
        if not await self.is_sufficient(query, reranked):
            # 自动 reformulate 并重试
            new_query = await self.reformulate(query, reranked)
            return await self.retrieve(new_query, state)  # 递归，最多 2 次
        
        return RetrievalResult(strategy="agentic", docs=reranked)
```

#### 3.1.3 知识图谱增强 (Graph RAG)

```python
# src/rag/graph_rag.py
class GraphRAG:
    """
    构建项目关系图谱：
    - 节点: 项目、赛道、投资机构、人物
    - 边: 竞争关系、投资关系、生态关系、团队流动
    
    从投研报告中自动抽取实体和关系，增强检索时的关联发现能力。
    """
    def build_graph(self, chunks: list[Document]):
        # 用 LLM 从每个 chunk 中抽取三元组
        for chunk in chunks:
            triples = self.llm.extract_triples(chunk.text)
            # triples: [(Arbitrum, competes_with, Optimism), 
            #           (Arbitrum, invested_by, a16z), ...]
            self.graph.add_triples(triples)
    
    def find_related(self, query: str, existing_results: list) -> list:
        # 从已检索到的项目出发，沿图谱找关联项目
        project_nodes = self.extract_projects(existing_results)
        related = []
        for node in project_nodes:
            neighbors = self.graph.get_neighbors(node, max_hops=2)
            related_docs = self.vectorstore.search_by_metadata(
                project_name__in=[n.name for n in neighbors]
            )
            related.extend(related_docs)
        return related
```

### 3.2 MCP Servers

#### 3.2.1 Market MCP Server

```python
# src/mcp_servers/market_server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("crypto-market")

@mcp.tool()
async def get_price(coin_id: str) -> dict:
    """获取代币实时价格、24h涨跌幅、市值"""
    ...

@mcp.tool()
async def get_price_history(coin_id: str, days: int = 30) -> dict:
    """获取历史价格走势"""
    ...

@mcp.tool()
async def get_market_overview() -> dict:
    """获取市场总览: 总市值、BTC 占比、恐惧贪婪指数"""
    ...

@mcp.tool()
async def calculate_technical_indicators(
    coin_id: str, indicators: list[str] = ["MA7", "MA25", "RSI"]
) -> dict:
    """基于历史价格计算技术指标"""
    ...
```

#### 3.2.2 MCP Tool Registry (动态发现)

```python
# src/mcp_servers/registry.py
class MCPToolRegistry:
    """
    动态工具注册与发现。Agent 运行时查询 registry 决定使用哪些工具,
    而非硬编码工具调用。
    """
    def __init__(self):
        self.servers: dict[str, MCPServerConfig] = {}
    
    def register(self, name: str, server: MCPServerConfig):
        self.servers[name] = server
    
    async def discover_tools(self, task_description: str) -> list[Tool]:
        """根据任务描述，用 LLM 选择最合适的工具组合"""
        all_tools = []
        for server in self.servers.values():
            all_tools.extend(await server.list_tools())
        
        selected = await self.llm.select_tools(task_description, all_tools)
        return selected
```

### 3.3 LangGraph Workflow

#### 3.3.1 State 定义

```python
# src/graph/state.py
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # 输入
    messages: Annotated[list, add_messages]
    user_query: str
    workflow_type: str  # deep_dive | compare | brief | qa
    
    # Planner 输出
    execution_plan: list[str]  # 计划执行的步骤
    
    # 各 Agent 输出
    rag_result: dict | None
    market_data: dict | None
    news_data: dict | None
    tokenomics_data: dict | None
    
    # Analyst 输出
    analysis_report: dict | None
    
    # Critic 输出
    critic_feedback: str | None
    critic_approved: bool
    revision_count: int  # 防止无限循环，最多 2 次修订
```

#### 3.3.2 工作流编排

```python
# src/graph/workflow.py
from langgraph.graph import StateGraph, END

def build_workflow() -> StateGraph:
    graph = StateGraph(AgentState)
    
    # 添加节点
    graph.add_node("router", router_node)
    graph.add_node("planner", planner_node)
    graph.add_node("rag_agent", rag_agent_node)
    graph.add_node("market_agent", market_agent_node)
    graph.add_node("news_agent", news_agent_node)
    graph.add_node("tokenomics_agent", tokenomics_agent_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("critic", critic_node)
    
    # 入口
    graph.set_entry_point("router")
    
    # Router → Planner
    graph.add_edge("router", "planner")
    
    # Planner → 并行 Agent (条件路由)
    graph.add_conditional_edges("planner", route_to_agents, {
        "parallel_all": ["rag_agent", "market_agent", "news_agent", "tokenomics_agent"],
        "rag_only": ["rag_agent"],
        "market_and_rag": ["rag_agent", "market_agent"],
    })
    
    # 并行 Agent → Analyst (全部完成后汇总)
    graph.add_edge("rag_agent", "analyst")
    graph.add_edge("market_agent", "analyst")
    graph.add_edge("news_agent", "analyst")
    graph.add_edge("tokenomics_agent", "analyst")
    
    # Analyst → Critic
    graph.add_edge("analyst", "critic")
    
    # Critic → END 或回到 Analyst
    graph.add_conditional_edges("critic", should_revise, {
        "approved": END,
        "revise": "analyst",
    })
    
    return graph.compile(checkpointer=MemorySaver())
```

### 3.4 评估体系 (Evaluation)

```python
# eval/metrics.py
class CryptoAgentEvaluator:
    """
    三层评估:
    1. RAG 层: RAGAS 指标 (faithfulness, answer_relevancy, context_precision)
    2. Agent 层: 工具调用准确率、计划执行完整度
    3. 端到端: Golden test cases 通过率
    """
    
    # Golden test cases 示例
    TEST_CASES = [
        {
            "query": "Arbitrum 最近值不值得投资？",
            "expected_tools_used": ["rag_search", "get_price", "get_news", "get_unlock_schedule"],
            "expected_output_fields": ["fundamental_analysis", "market_data", "news_sentiment", 
                                       "tokenomics", "investment_recommendation"],
            "expected_has_disclaimer": True,
        },
        {
            "query": "对比 Arbitrum 和 Optimism",
            "expected_workflow": "compare",
            "expected_projects_analyzed": 2,
        },
    ]
```

---

## 4. 依赖清单

```toml
# pyproject.toml 核心依赖
[project]
name = "dyor"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    # LLM & Agent
    "langchain>=0.3",
    "langgraph>=0.2",
    "langchain-anthropic>=0.3",  # 或 langchain-openai
    "langchain-community>=0.3",
    
    # RAG
    "chromadb>=0.5",
    "sentence-transformers>=3.0",  # BGE-M3
    "rank-bm25>=0.2",              # BM25 sparse retrieval
    "flashrank>=0.2",              # 轻量 reranker (本地)
    
    # MCP
    "mcp[cli]>=1.0",
    "httpx>=0.27",
    
    # Knowledge Graph
    "networkx>=3.3",               # 轻量图谱 (无需 Neo4j)
    
    # API & Frontend
    "fastapi>=0.115",
    "uvicorn>=0.32",
    "websockets>=13",
    "streamlit>=1.39",
    "plotly>=5.24",                # 图表可视化
    
    # Data & Utils
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    
    # Evaluation
    "ragas>=0.2",
]
```

---

## 5. 关键设计决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| Agent 编排框架 | LangGraph (非 CrewAI/AutoGen) | 更底层灵活，支持自定义 state/edge，面试可深聊实现细节 |
| 向量数据库 | ChromaDB | 零配置本地运行，够用且面试不会在 DB 选型上纠缠 |
| 知识图谱 | NetworkX (非 Neo4j) | 轻量无外部依赖，项目量级不需要图数据库 |
| Embedding | BGE-M3 | 中英双语 + dense/sparse 双表示 + 开源免费 |
| Reranker | flashrank (本地) | 无需 API key，离线可用 |
| 前端 | Streamlit | 快速出 demo，重点在后端 Agent 架构 |
| MCP vs Function Calling | MCP | 更前沿，展示对新协议的理解 |

# DYOR (Do Your Own Research)

基于 LangGraph 的多智能体加密货币投研助手，结合 RAG 检索私有投研报告，通过 MCP Server 获取实时市场数据，生成结构化投资分析报告。

## 功能特性

- **多 Agent 协作** — 8 个专职 Agent 协作（Router → Planner → RAG / Market / News / Tokenomics → Analyst → Critic）
- **RAG 混合检索** — BGE-M3 Embedding + ChromaDB 向量库 + BM25 关键词检索 + flashrank Reranking + Self-RAG 自验证
- **3 个 MCP Server** — CoinGecko 行情、CryptoPanic 新闻聚合、代币解锁计划
- **Guardrails 安全校验** — 输出结构化校验，防止绝对化投资建议
- **流式对话** — FastAPI WebSocket 流式输出 + REST API
- **可视化前端** — Streamlit 三页面（聊天对话 / 分析 Dashboard / 项目对比）+ Plotly 图表
- **知识图谱增强** — NetworkX 构建项目关系图谱，增强检索上下文
- **RAGAS 评估** — 基于 RAGAS 框架的 RAG 质量评估体系

## 技术栈

Python 3.11+ · uv · LangGraph · LangChain · ChromaDB · BGE-M3 · FastMCP · FastAPI · Streamlit · Plotly · NetworkX · Pydantic v2 · structlog

## 环境要求

- Python >= 3.11, < 3.13
- [uv](https://github.com/astral-sh/uv) 包管理器

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# 或
pip install uv
```

## 环境配置

复制 `.env.example` 并填入 API 密钥：

```bash
cp .env.example .env
```

| 变量 | 必需 | 默认值 | 说明 |
|------|:----:|--------|------|
| `ANTHROPIC_API_KEY` | 是 | — | Claude API 密钥 |
| `COINGECKO_API_KEY` | 否 | — | CoinGecko API（无则功能降级） |
| `CRYPTOPANIC_API_KEY` | 否 | — | CryptoPanic 新闻 API |
| `CHROMA_PERSIST_DIR` | 否 | `./data/chroma_db` | 向量库持久化路径 |
| `EMBEDDING_MODEL` | 否 | `BAAI/bge-m3` | Embedding 模型 |
| `API_HOST` | 否 | `0.0.0.0` | API 服务地址 |
| `API_PORT` | 否 | `8000` | API 服务端口 |
| `MAX_REVISION_COUNT` | 否 | `2` | Critic 最大修订次数 |
| `AGENT_TIMEOUT` | 否 | `30` | Agent 超时秒数 |
| `KNOWLEDGE_GRAPH_PATH` | 否 | `./data/knowledge_graph/graph.graphml` | 知识图谱存储路径 |

## 快速开始

```bash
# 克隆并安装依赖
git clone <repo-url> && cd DYOR
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY

# 索引投研文档到 ChromaDB
uv run python -m src.rag.ingest

# 启动 API 服务 (http://localhost:8000)
uv run uvicorn api.main:app --reload

# 启动前端 (http://localhost:8501)
uv run streamlit run ui/app.py
```

## 使用方式

### Web 界面

Streamlit 提供 3 个页面：
- **聊天对话** — 与投研助手自然语言交互
- **分析 Dashboard** — 查看结构化分析报告和可视化图表
- **项目对比** — 多项目横向对比分析

### API

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v1/analyze` | 提交分析请求 |
| WebSocket | `/api/v1/chat/ws/{session_id}` | 流式对话 |
| GET | `/api/v1/reports` | 获取历史报告 |

### MCP Server

```bash
uv run python -m src.mcp_servers.market_server      # CoinGecko 行情
uv run python -m src.mcp_servers.news_server         # CryptoPanic 新闻
uv run python -m src.mcp_servers.token_unlock_server # 代币解锁
```

## 项目结构

```
src/                → 核心业务代码
├── rag/            → RAG 引擎（文档处理、检索、图谱）
├── mcp_servers/    → MCP Server 定义
├── agents/         → Agent 逻辑定义
│   └── prompts/    → 各 Agent 的 system prompt
├── graph/          → LangGraph 工作流编排
├── schemas/        → Pydantic 数据模型
├── guardrails/     → 输出安全校验
├── memory/         → 对话记忆与用户偏好
└── config.py       → 全局配置
api/                → FastAPI 路由和中间件
ui/                 → Streamlit 前端页面
eval/               → 评估脚本和测试用例
tests/              → 单元测试
data/reports/       → 投研报告原始文件
```

## 架构

```
START → Router → Planner → [RAG, Market, News, Tokenomics] → Analyst → Critic → END
                                                                  ↑                |
                                                                  └─ revision (max 2) ─┘
```

- **Router** — 意图识别，将用户查询路由到合适的处理流程
- **Planner** — 制定分析计划，决定需要调用哪些数据源
- **RAG / Market / News / Tokenomics** — 并行执行数据采集
- **Analyst** — 汇总所有数据，生成结构化分析报告
- **Critic** — 审查报告质量，不达标则触发修订（最多 2 次）

## 测试

```bash
# 运行全部测试
uv run pytest tests/ -v

# 带覆盖率
uv run pytest tests/ --cov=src --cov=api --cov=eval --cov-report=term-missing

# 生成测试报告
uv run python tests/generate_report.py

# 运行 RAG 评估
uv run python eval/run_eval.py
```

## 开发

- 代码检查与格式化：`uv run ruff check src/` / `uv run ruff format src/`
- 类型标注：所有函数签名必须有 type hints
- Docstring：Google 风格
- Git commit：`type(scope): description`（如 `feat(rag): add hybrid search`）
- 详细规范见 [CLAUDE.md](./CLAUDE.md)

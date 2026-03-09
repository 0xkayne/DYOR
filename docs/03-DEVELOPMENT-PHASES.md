# DYOR — 开发阶段总览与 Subagent 编排方案

## 分阶段策略

项目开发分为 4 个阶段，每个阶段内根据文件作用域的独立性决定是否并行。
核心原则：**文件作用域不重叠的任务才并行，有共享文件的任务必须串行。**

```
Phase 1 (串行)        Phase 2 (并行)          Phase 3 (串行)         Phase 4 (并行)
┌──────────────┐     ┌──────────────────┐    ┌──────────────┐     ┌──────────────────┐
│  Foundation   │     │ ┌──────────────┐ │    │ Agent System │     │ ┌──────────────┐ │
│  scaffolding  │────▶│ │ RAG Engine   │ │───▶│ + LangGraph  │────▶│ │ API Backend  │ │
│  + config     │     │ │ src/rag/*    │ │    │ + Guardrails │     │ │ api/*        │ │
│  + schemas    │     │ └──────────────┘ │    │ src/agents/* │     │ └──────────────┘ │
└──────────────┘     │ ┌──────────────┐ │    │ src/graph/*  │     │ ┌──────────────┐ │
                      │ │ MCP Servers  │ │    │ src/guards/* │     │ │ Frontend     │ │
                      │ │ src/mcp/*    │ │    └──────────────┘     │ │ ui/*         │ │
                      │ └──────────────┘ │                         │ └──────────────┘ │
                      │ ┌──────────────┐ │                         │ ┌──────────────┐ │
                      │ │ Graph RAG    │ │                         │ │ Eval + Tests │ │
                      │ │ (知识图谱)    │ │                         │ │ eval/*       │ │
                      │ └──────────────┘ │                         │ tests/*        │ │
                      └──────────────────┘                         └──────────────────┘

时间: ~2h agent work   ~3h (并行≈1.5h)        ~3h agent work        ~3h (并行≈1.5h)
```

---

## Phase 1: Foundation (串行, 单 Agent)

### 为什么串行
此阶段创建 pyproject.toml、src/config.py、src/schemas/*.py 等基础文件，
所有后续阶段都依赖这些文件。拆分会导致多个 agent 修改同一个 pyproject.toml。

### 任务清单
1. 创建项目目录结构（严格按 TDD 文档）
2. 编写 pyproject.toml，安装所有依赖
3. 编写 src/config.py (pydantic-settings)
4. 编写 src/schemas/*.py (所有 Pydantic 数据模型)
5. 编写 .env.example
6. 创建 data/reports/ 目录，放入示例投研报告
7. 验证：`uv sync` + `uv run python -c "from src.config import settings; print(settings)"`

### Subagent
使用 **foundation-builder** (单 agent, 无 worktree)

### 完成标志
- [ ] `uv sync` 无报错
- [ ] 所有 schemas 可正常 import
- [ ] config 能读取 .env

---

## Phase 2: RAG Engine + MCP Servers + Graph RAG (并行, 3 Agents)

### 冲突分析
| Agent | 文件作用域 | 交集 |
|-------|-----------|------|
| rag-developer | src/rag/*.py | ∅ |
| mcp-developer | src/mcp_servers/*.py | ∅ |
| graph-rag-developer | src/rag/graph_rag.py, data/knowledge_graph/ | ⚠️ |

**风险评估**: rag-developer 和 graph-rag-developer 都在 src/rag/ 目录下，但操作不同文件。
rag-developer 负责 ingest.py, embeddings.py, vectorstore.py, retriever.py, evaluator.py；
graph-rag-developer 仅负责 graph_rag.py 和 data/knowledge_graph/。
文件级别无交集 → **LOW RISK**，可以并行。

但 rag-developer 的 retriever.py 中会 import graph_rag，需要约定接口：
- graph-rag-developer 先完成 `GraphRAG.find_related()` 方法签名
- rag-developer 中 graph_rag 调用暂时 mock，Phase 3 集成时再对接

### 任务清单

**rag-developer:**
1. 实现 src/rag/ingest.py (文档加载 + 语义切分 + metadata 增强)
2. 实现 src/rag/embeddings.py (BGE-M3 封装)
3. 实现 src/rag/vectorstore.py (ChromaDB 操作)
4. 实现 src/rag/retriever.py (hybrid search + reranking + self-RAG)
5. 实现 src/rag/evaluator.py (RAGAS 评估封装)
6. 用 data/reports/ 中的示例报告跑通完整 pipeline
7. 验证: 能对示例报告进行索引和检索

**mcp-developer:**
1. 实现 src/mcp_servers/market_server.py (CoinGecko API 4-5 个 tools)
2. 实现 src/mcp_servers/news_server.py (新闻聚合 3-4 个 tools)
3. 实现 src/mcp_servers/unlock_server.py (解锁计划 3-4 个 tools)
4. 实现 src/mcp_servers/registry.py (工具注册与发现)
5. 为每个 server 编写基本测试
6. 验证: 每个 MCP server 可独立 `mcp.run()` 启动

**graph-rag-developer:**
1. 实现 src/rag/graph_rag.py (NetworkX 知识图谱)
2. 实现实体和关系抽取（用 LLM 从 chunk 中提取三元组）
3. 实现 find_related() 方法（图遍历找关联项目）
4. 创建 data/knowledge_graph/ 下的图谱序列化
5. 验证: 能从示例报告构建图谱并查询关联

### Subagent 文件
- `.claude/agents/rag-developer.md`
- `.claude/agents/mcp-developer.md`
- `.claude/agents/graph-rag-developer.md`

### 启动命令
```bash
# 确保 Phase 1 已合并到 main
git checkout main

# 启动 3 个并行 worktree
claude --worktree "实现 RAG 引擎: ingest + hybrid search + reranking + self-RAG" --tmux
claude --worktree "实现 3 个 MCP Server: market + news + unlock + registry" --tmux
claude --worktree "实现 Graph RAG 知识图谱模块" --tmux
```

### 合并顺序
1. 先合并 graph-rag-developer（最独立）
2. 再合并 mcp-developer（独立）
3. 最后合并 rag-developer（可能需要微调 graph_rag import）

### 完成标志
- [ ] RAG pipeline 能索引示例报告并返回相关 chunks
- [ ] 3 个 MCP server 各自可启动并响应工具调用
- [ ] 知识图谱能从报告中抽取实体并做关联查询
- [ ] hybrid search + reranking 工作正常

---

## Phase 3: Agent System + LangGraph Workflow (串行, 单 Agent)

### 为什么串行
Agent 系统是项目的核心编排层，每个 Agent 都需要调用 RAG 和 MCP 的接口，
且 LangGraph 的 State、节点、边高度耦合。拆分会导致：
- 多个 agent 修改 src/graph/state.py (shared state 定义)
- Agent 之间有数据依赖 (Analyst 依赖其他 Agent 的输出)
- prompts/ 目录中的 prompt 与对应 Agent 紧密绑定

强制串行确保架构一致性。

### 任务清单
1. 定义 src/graph/state.py (AgentState TypedDict)
2. 实现 src/agents/router.py + prompts/router_prompt.py
3. 实现 src/agents/planner.py + prompts/planner_prompt.py
4. 实现 src/agents/rag_agent.py (调用 RAG retriever)
5. 实现 src/agents/market_agent.py (调用 Market MCP)
6. 实现 src/agents/news_agent.py (调用 News MCP)
7. 实现 src/agents/tokenomics_agent.py (调用 Unlock MCP)
8. 实现 src/agents/analyst.py (综合分析, structured output)
9. 实现 src/agents/critic.py (质量审查 + reflection 循环)
10. 实现 src/guardrails/output_validator.py
11. 实现 src/guardrails/disclaimer.py
12. 实现 src/graph/nodes.py (所有节点函数)
13. 实现 src/graph/edges.py (条件边逻辑)
14. 实现 src/graph/workflow.py (组装完整工作流)
15. 实现 src/memory/checkpointer.py
16. 端到端测试: 输入一个查询，跑通完整工作流
17. 导出工作流可视化图 (mermaid)

### Subagent
使用 **agent-system-builder** (单 agent, 无 worktree)

### 完成标志
- [ ] 输入 "分析 Arbitrum" 能跑通完整 Router → Planner → 并行 Agent → Analyst → Critic 流程
- [ ] 输出符合 PRD 中定义的 JSON schema
- [ ] Critic 的 reflection 循环工作正常（不合格时回退到 Analyst）
- [ ] guardrails 能检测并拒绝不当投资建议
- [ ] 可导出 workflow.png 可视化图

---

## Phase 4: API + Frontend + Eval (并行, 3 Agents)

### 冲突分析
| Agent | 文件作用域 | 交集 |
|-------|-----------|------|
| api-developer | api/*.py | ∅ |
| frontend-developer | ui/*.py | ∅ |
| eval-developer | eval/*.py, tests/*.py | ∅ |

三者文件完全不重叠 → **LOW RISK**

### 任务清单

**api-developer:**
1. 实现 api/main.py (FastAPI app, CORS, 生命周期管理)
2. 实现 api/routes/chat.py (WebSocket 流式聊天)
3. 实现 api/routes/analyze.py (RESTful 分析接口)
4. 实现 api/routes/reports.py (报告 CRUD)
5. 实现 api/middleware/streaming.py (流式响应)
6. 编写 API 文档 (FastAPI 自动生成 OpenAPI)
7. 验证: `uvicorn api.main:app` 可启动，所有端点可调用

**frontend-developer:**
1. 实现 ui/app.py (Streamlit 主入口 + 导航)
2. 实现 ui/pages/chat.py (聊天交互页, 连接 WebSocket)
3. 实现 ui/pages/dashboard.py (分析结果 Dashboard)
4. 实现 ui/pages/compare.py (对比分析页)
5. 实现 ui/components/charts.py (Plotly 图表: 价格走势、雷达图、解锁时间线)
6. 实现 ui/components/report_card.py (结构化报告卡片)
7. 验证: `streamlit run ui/app.py` 可启动，页面渲染正常

**eval-developer:**
1. 编写 eval/test_cases.json (10-15 个黄金测试用例)
2. 实现 eval/metrics.py (RAG 指标 + Agent 指标 + 端到端指标)
3. 实现 eval/run_eval.py (评估脚本，输出评估报告)
4. 编写 tests/test_rag/ 下的单元测试
5. 编写 tests/test_agents/ 下的单元测试
6. 编写 tests/test_mcp/ 下的单元测试
7. 编写 tests/test_api/ 下的集成测试
8. 验证: `pytest tests/ -v` 全部通过

### Subagent 文件
- `.claude/agents/api-developer.md`
- `.claude/agents/frontend-developer.md`
- `.claude/agents/eval-developer.md`

### 启动命令
```bash
git checkout main  # 确保 Phase 3 已合并

claude --worktree "实现 FastAPI 后端: WebSocket 聊天 + REST 分析接口" --tmux
claude --worktree "实现 Streamlit 前端: 聊天页 + Dashboard + 对比分析页" --tmux
claude --worktree "实现评估体系: RAGAS 指标 + 黄金测试用例 + 单元测试" --tmux
```

### 合并顺序
1. 先合并 eval-developer（最独立，只读源码）
2. 再合并 api-developer
3. 最后合并 frontend-developer
4. 合并后做一次端到端集成测试

### 完成标志
- [ ] API 所有端点正常工作，WebSocket 流式输出正常
- [ ] Streamlit UI 能展示完整的分析报告+图表
- [ ] 评估脚本能运行并输出 metrics
- [ ] pytest 通过率 > 90%

---

## 后续打磨 (Phase 5, 可选)

1. 编写 docker-compose.yml 一键部署
2. 编写完整 README.md（含架构图、截图、Quick Start）
3. 录制 Demo 视频
4. 准备面试讲解稿（重点技术决策和 trade-off）

# CLAUDE.md — DYOR 项目开发指南

## 项目概述
DYOR 是一个多智能体协作的加密货币投研助手。使用 LangGraph 编排多个专职 Agent，
结合 RAG 技术检索私有投研报告，通过 MCP Server 获取实时市场数据，生成结构化投资分析报告。

## 技术栈
- **语言**: Python 3.11+
- **包管理**: uv (优先) 或 poetry
- **Agent 框架**: LangGraph + LangChain
- **向量数据库**: ChromaDB
- **Embedding**: BGE-M3 (BAAI/bge-m3)
- **MCP**: FastMCP (mcp[cli])
- **后端**: FastAPI + uvicorn
- **前端**: Streamlit
- **图谱**: NetworkX
- **LLM**: Claude API (langchain-anthropic)

## 项目结构约定
```
src/               → 核心业务代码，所有模块在此
src/rag/           → RAG 引擎（文档处理、检索、图谱）
src/mcp_servers/   → MCP Server 定义
src/agents/        → Agent 逻辑定义
src/agents/prompts/→ 各 Agent 的 system prompt (独立文件)
src/graph/         → LangGraph 工作流编排
src/schemas/       → Pydantic 数据模型
src/guardrails/    → 输出安全校验
src/memory/        → 对话记忆与用户偏好
api/               → FastAPI 路由和中间件
ui/                → Streamlit 前端页面
eval/              → 评估脚本和测试用例
tests/             → 单元测试
data/reports/      → 投研报告原始文件
```

## 编码规范

### Python 风格
- 使用 type hints（所有函数签名必须有类型标注）
- 使用 Pydantic v2 做数据验证
- 异步优先：所有 I/O 操作使用 async/await
- docstring 使用 Google 风格
- 每个模块顶部要有模块级 docstring 说明用途

### 命名约定
- 文件名: snake_case
- 类名: PascalCase
- 函数/方法: snake_case
- 常量: UPPER_SNAKE_CASE
- Agent prompt 文件: `{agent_name}_prompt.py`

### Import 规范
```python
# 标准库
import os
from pathlib import Path

# 第三方库
from langchain_core.documents import Document
from langgraph.graph import StateGraph

# 项目内部
from src.schemas.analysis import AnalysisReport
from src.config import settings
```

### 错误处理
- 外部 API 调用必须有 try/except + 超时设置
- MCP tool 调用失败时返回 fallback 结果（不能让整个工作流崩溃）
- 使用 structlog 做结构化日志

### 测试
- 每个模块在 tests/ 下有对应测试文件
- mock 所有外部 API 调用
- RAG 测试使用固定的测试文档集

## Agent Prompt 规范
所有 Agent 的 system prompt 必须包含:
1. **角色定义**: 你是什么角色，负责什么
2. **输入说明**: 你会收到什么数据
3. **输出格式**: 必须输出的 JSON schema
4. **约束规则**: 不能做什么（如不能给绝对化投资建议）
5. **质量标准**: 什么样的输出算合格

## LangGraph 规范
- State 使用 TypedDict 定义，每个字段有注释
- 节点函数签名统一: `async def node_name(state: AgentState) -> dict`
- 条件边的判断函数要有清晰的日志输出
- revision_count 上限为 2，防止无限循环

## MCP Server 规范
- 每个 server 独立文件，使用 FastMCP 创建
- 每个 tool 必须有完整的 docstring（LLM 靠这个理解工具用途）
- 返回值使用 Pydantic model 序列化为 dict
- 所有 HTTP 请求使用 httpx.AsyncClient + 超时配置

## Git 工作流
- main 分支保护，不直接 push
- 开发使用 feature branch: `feat/{module}-{description}`
- 使用 git worktree 支持并行开发
- commit message 格式: `type(scope): description`
  - type: feat/fix/refactor/docs/test/chore
  - scope: rag/mcp/agent/api/ui/eval

## 开发分阶段
Phase 1: 项目初始化 + RAG 核心
Phase 2: MCP Servers + Agent 系统
Phase 3: API + 前端 + Eval
详见 phases/ 目录下的阶段文档。

## 常用命令
```bash
# 启动开发
uv run python -m src.rag.ingest        # 索引文档
uv run python -m src.mcp_servers.market_server  # 启动 MCP server
uv run uvicorn api.main:app --reload    # 启动 API
uv run streamlit run ui/app.py          # 启动前端

# 测试
uv run pytest tests/ -v
uv run python eval/run_eval.py          # 运行评估

# 代码质量
uv run ruff check src/
uv run ruff format src/
```

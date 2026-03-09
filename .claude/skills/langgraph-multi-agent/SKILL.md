---
name: langgraph-multi-agent
description: >
  LangGraph 多智能体工作流开发技能。用于设计和实现基于 LangGraph 的 stateful multi-agent 系统，
  包括 State 定义、节点函数编写、条件路由、并行 fan-out/fan-in、reflection 循环、checkpointing 记忆。
  当用户需要以下任务时触发此技能：构建 LangGraph 工作流、编排多个 Agent 协作、实现 Agent 间通信、
  添加 self-critique/reflection 机制、配置 LangGraph checkpoint 做对话记忆、
  处理并行 Agent 的结果汇总。即使用户只是提到 "langgraph"、"multi-agent"、"工作流"、
  "agent 编排"、"状态机"、"条件路由"、"reflection loop"、"plan-and-execute" 等关键词，
  也应触发此技能。适用于任何基于 LangGraph 构建 Agent 系统的场景，
  不适用于纯 LangChain AgentExecutor 或 CrewAI/AutoGen 等其他框架。
---

# LangGraph Multi-Agent Workflow Skill

构建基于 LangGraph 的生产级多智能体系统的完整规范。本技能覆盖从 State 设计到工作流编排的全流程。

## 核心理念

LangGraph 的本质是一个**有状态的图执行引擎**。和 LangChain 的线性 Chain 不同，
LangGraph 允许你定义节点（Agent 或函数）和边（路由逻辑），支持循环、分支、并行，
使得复杂的 Agent 协作模式成为可能。

理解 LangGraph 的关键在于三个概念：**State 是共享内存**，**Node 是执行单元**，**Edge 是控制流**。

---

## State 设计

State 是整个工作流的共享数据层。所有节点读取 State、执行逻辑、返回 State 更新。

### 设计原则

1. **扁平化**：每个 Agent 的输出是 State 的顶层字段，不要深度嵌套
2. **可选字段用 `| None`**：并行 Agent 未完成时字段为 None，下游必须处理
3. **使用 Annotated reducer**：messages 字段必须用 `add_messages`
4. **字段即文档**：每个字段加注释说明来源和用途

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # 对话历史 (自动追加，不覆盖)
    messages: Annotated[list, add_messages]
    
    # 用户输入
    user_query: str
    workflow_type: str          # 由 Router 填充
    
    # Planner 输出
    execution_plan: list[str]   # 计划执行的步骤列表
    
    # 各 Agent 输出 (并行执行，可能为 None)
    rag_result: dict | None
    market_data: dict | None
    
    # 综合分析输出
    analysis_report: dict | None
    
    # Critic 审查
    critic_feedback: str | None
    critic_approved: bool
    revision_count: int         # 防止无限循环
```

**反模式 — 不要这样做：**
```python
# ❌ 把所有结果塞进一个 dict
class BadState(TypedDict):
    results: dict  # 无法区分哪个 Agent 产出了什么

# ❌ 深度嵌套
class BadState(TypedDict):
    agents: dict[str, dict[str, Any]]  # 可读性和类型安全都很差
```

---

## 节点函数

每个节点函数代表一个执行单元（通常是一个 Agent 的调用）。

### 标准模板

```python
async def my_agent_node(state: AgentState) -> dict:
    """
    节点名称：简述职责。
    
    读取: state.user_query, state.execution_plan
    写入: {"my_result": {...}}
    """
    try:
        # 业务逻辑
        result = await my_agent.invoke(state["user_query"])
        return {"my_result": result}
    except Exception as e:
        logger.error(f"MyAgent failed: {e}")
        return {"my_result": {"error": str(e), "fallback": True}}
```

### 关键规则

- **返回 dict**：key 是要更新的 State 字段名，LangGraph 自动合并
- **必须 try/except**：节点失败不能让整个工作流崩溃，返回带 error 标记的 fallback
- **不要直接修改 state**：通过返回值更新，LangGraph 管理 immutable state
- **一个节点 = 一个职责**：不要在一个节点里调用多个 LLM
- **处理 None**：并行节点的上游结果可能还没到

```python
# ✅ 正确处理 None
async def analyst_node(state: AgentState) -> dict:
    rag = state.get("rag_result") or {"status": "unavailable"}
    market = state.get("market_data") or {"status": "unavailable"}
    # ... 即使部分数据缺失也能生成报告
```

---

## 边与路由

### 无条件边（固定流向）
```python
graph.add_edge("router", "planner")  # Router 永远流向 Planner
```

### 条件边（动态路由）

条件边的判断函数必须返回明确的路由标签字符串：

```python
def route_after_planner(state: AgentState) -> str:
    """根据 Planner 的执行计划决定激活哪些 Agent"""
    plan = state.get("execution_plan", [])
    if "market" in plan and "news" in plan:
        return "parallel_all"
    if "rag_only" in plan:
        return "rag_only"
    return "parallel_all"  # 默认全部激活

graph.add_conditional_edges("planner", route_after_planner, {
    "parallel_all": ["rag_agent", "market_agent", "news_agent"],
    "rag_only": ["rag_agent"],
})
```

### Reflection 循环（Critic → Revise）

这是实现 self-critique 的核心模式。**必须设置循环上限**。

```python
def should_revise(state: AgentState) -> str:
    if state["critic_approved"]:
        return "approved"
    if state["revision_count"] >= 2:
        logger.warning("Max revisions reached, forcing approval")
        return "approved"  # 硬性上限，防止无限循环
    return "revise"

graph.add_conditional_edges("critic", should_revise, {
    "approved": END,
    "revise": "analyst",  # 打回给 Analyst 重写
})
```

在 Analyst 节点中递增计数器：
```python
async def analyst_node(state: AgentState) -> dict:
    count = state.get("revision_count", 0)
    feedback = state.get("critic_feedback")
    # 如果有 feedback，说明是被打回的，参考 feedback 重写
    report = await generate_report(state, feedback=feedback)
    return {"analysis_report": report, "revision_count": count + 1}
```

---

## 并行执行

LangGraph 原生支持并行：从同一节点出发的多条边会并行执行。

```python
# 这四个节点会并行执行
graph.add_edge("planner", "rag_agent")
graph.add_edge("planner", "market_agent")
graph.add_edge("planner", "news_agent")
graph.add_edge("planner", "tokenomics_agent")

# analyst 会等所有并行节点完成后才执行 (fan-in)
graph.add_edge(["rag_agent", "market_agent", "news_agent", "tokenomics_agent"], "analyst")
```

**不要手动用 asyncio.gather**，让 LangGraph 处理并行调度。

---

## Checkpointing（对话记忆）

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer)

# 调用时传入 thread_id 维持多轮会话
config = {"configurable": {"thread_id": "user_session_123"}}
result = await graph.ainvoke(initial_state, config=config)
```

---

## 工作流组装完整示例

详见 `references/workflow-assembly.md` 中的完整代码示例。

---

## Agent Prompt 规范

每个 Agent 的 system prompt 放在独立文件中（如 `prompts/analyst_prompt.py`），
导出一个字符串常量。Prompt 必须包含以下部分：

1. **角色定义**：你是什么角色，核心职责
2. **输入说明**：你会收到什么数据（从 State 中哪些字段）
3. **输出格式**：必须输出的结构（JSON schema 或模板）
4. **约束规则**：不能做什么（如不能给绝对化建议）
5. **质量标准**：什么样的输出算合格

详见 `references/prompt-templates.md` 中的各 Agent prompt 模板。

---

## 调试与可视化

```python
# 导出工作流为 Mermaid 图
graph.get_graph().draw_mermaid_png(output_file_path="workflow.png")

# 使用 LangSmith 追踪 (可选)
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "my-project"
```

---

## 禁止事项

- ❌ 不要用 LangChain 的 AgentExecutor（已过时），用 LangGraph 原生节点
- ❌ 不要在一个节点里调用多个 LLM
- ❌ 不要忽略 None 检查
- ❌ 不要硬编码 LLM model name，从 config 读取
- ❌ 不要让 reflection 循环没有上限
- ❌ 不要用 asyncio.gather 做并行，让 LangGraph 管理
- ❌ 不要把所有逻辑塞进 workflow.py，节点定义和边定义分文件

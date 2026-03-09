# Workflow Assembly — 完整代码参考

本文件包含从零组装一个 LangGraph 多智能体工作流的完整代码示例。

## Table of Contents

1. [State 定义](#state-定义)
2. [节点函数](#节点函数)
3. [条件边](#条件边)
4. [图组装](#图组装)
5. [调用方式](#调用方式)

---

## State 定义

```python
# src/graph/state.py
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """多智能体工作流的共享状态。
    
    每个 Agent 节点读取相关字段、执行逻辑、返回更新的字段。
    LangGraph 自动将返回的 dict merge 进 State。
    """
    # 对话历史（自动追加）
    messages: Annotated[list, add_messages]
    
    # 用户输入
    user_query: str
    workflow_type: str  # Router 填充: deep_dive | compare | brief | qa
    target_entities: list[str]  # Router 提取的目标实体名
    
    # Planner 输出
    execution_plan: list[str]  # 要执行的 Agent 列表
    
    # 子 Agent 输出（并行执行，初始为 None）
    rag_result: dict | None
    market_data: dict | None
    news_data: dict | None
    tokenomics_data: dict | None
    
    # Analyst 输出
    analysis_report: dict | None
    
    # Critic 审查
    critic_feedback: str | None
    critic_approved: bool
    revision_count: int
```

---

## 节点函数

```python
# src/graph/nodes.py
import structlog
from src.graph.state import AgentState
from src.agents.router import RouterAgent
from src.agents.planner import PlannerAgent
from src.agents.rag_agent import RAGAgent
from src.agents.market_agent import MarketAgent
from src.agents.news_agent import NewsAgent
from src.agents.tokenomics_agent import TokenomicsAgent
from src.agents.analyst import AnalystAgent
from src.agents.critic import CriticAgent

logger = structlog.get_logger()

# 实例化（在模块加载时创建，节点函数中复用）
router = RouterAgent()
planner = PlannerAgent()
rag_agent = RAGAgent()
market_agent = MarketAgent()
news_agent = NewsAgent()
tokenomics_agent = TokenomicsAgent()
analyst = AnalystAgent()
critic = CriticAgent()


async def router_node(state: AgentState) -> dict:
    """路由节点：识别用户意图和目标实体。"""
    try:
        result = await router.invoke(state["user_query"])
        return {
            "workflow_type": result["workflow_type"],
            "target_entities": result["entities"],
        }
    except Exception as e:
        logger.error("Router failed", error=str(e))
        return {
            "workflow_type": "deep_dive",  # 默认 fallback
            "target_entities": [],
        }


async def planner_node(state: AgentState) -> dict:
    """计划节点：根据意图生成执行计划。"""
    try:
        plan = await planner.invoke(
            workflow_type=state["workflow_type"],
            query=state["user_query"],
        )
        return {"execution_plan": plan}
    except Exception as e:
        logger.error("Planner failed", error=str(e))
        # 默认全部激活
        return {"execution_plan": ["rag", "market", "news", "tokenomics"]}


async def rag_agent_node(state: AgentState) -> dict:
    """RAG 节点：从知识库检索相关信息。"""
    try:
        result = await rag_agent.invoke(
            query=state["user_query"],
            entities=state.get("target_entities", []),
        )
        return {"rag_result": result}
    except Exception as e:
        logger.error("RAG Agent failed", error=str(e))
        return {"rag_result": {"error": str(e), "fallback": True}}


async def market_agent_node(state: AgentState) -> dict:
    """行情节点：获取实时市场数据。"""
    try:
        entities = state.get("target_entities", [])
        result = await market_agent.invoke(entities=entities)
        return {"market_data": result}
    except Exception as e:
        logger.error("Market Agent failed", error=str(e))
        return {"market_data": {"error": str(e), "fallback": True}}


async def news_agent_node(state: AgentState) -> dict:
    """新闻节点：聚合新闻 + 情感分析。"""
    try:
        entities = state.get("target_entities", [])
        result = await news_agent.invoke(entities=entities)
        return {"news_data": result}
    except Exception as e:
        logger.error("News Agent failed", error=str(e))
        return {"news_data": {"error": str(e), "fallback": True}}


async def tokenomics_agent_node(state: AgentState) -> dict:
    """代币经济学节点：查询解锁计划和筹码分布。"""
    try:
        entities = state.get("target_entities", [])
        result = await tokenomics_agent.invoke(entities=entities)
        return {"tokenomics_data": result}
    except Exception as e:
        logger.error("Tokenomics Agent failed", error=str(e))
        return {"tokenomics_data": {"error": str(e), "fallback": True}}


async def analyst_node(state: AgentState) -> dict:
    """综合分析节点：汇总所有 Agent 输出，生成结构化报告。"""
    count = state.get("revision_count", 0)
    feedback = state.get("critic_feedback")
    
    try:
        report = await analyst.invoke(
            query=state["user_query"],
            rag_result=state.get("rag_result"),
            market_data=state.get("market_data"),
            news_data=state.get("news_data"),
            tokenomics_data=state.get("tokenomics_data"),
            previous_feedback=feedback,
        )
        return {
            "analysis_report": report,
            "revision_count": count + 1,
        }
    except Exception as e:
        logger.error("Analyst failed", error=str(e))
        return {
            "analysis_report": {"error": str(e)},
            "revision_count": count + 1,
        }


async def critic_node(state: AgentState) -> dict:
    """质量审查节点：检查报告质量和合规性。"""
    report = state.get("analysis_report", {})
    
    if "error" in report:
        # 报告生成失败，直接通过（避免循环）
        return {"critic_approved": True, "critic_feedback": None}
    
    try:
        result = await critic.invoke(report=report)
        return {
            "critic_approved": result["approved"],
            "critic_feedback": result.get("feedback"),
        }
    except Exception as e:
        logger.error("Critic failed", error=str(e))
        return {"critic_approved": True, "critic_feedback": None}
```

---

## 条件边

```python
# src/graph/edges.py
import structlog
from src.graph.state import AgentState

logger = structlog.get_logger()


def route_to_agents(state: AgentState) -> str:
    """Planner 之后的条件路由：决定激活哪些 Agent。"""
    plan = state.get("execution_plan", [])
    
    if set(plan) >= {"rag", "market", "news", "tokenomics"}:
        return "parallel_all"
    elif plan == ["rag"]:
        return "rag_only"
    elif set(plan) >= {"rag", "market"}:
        return "rag_and_market"
    else:
        return "parallel_all"  # 默认全部


def should_revise(state: AgentState) -> str:
    """Critic 之后的条件路由：决定是否需要修订。"""
    if state.get("critic_approved", False):
        logger.info("Critic approved the report")
        return "approved"
    
    revision_count = state.get("revision_count", 0)
    if revision_count >= 2:
        logger.warning("Max revisions reached, forcing approval",
                       revision_count=revision_count)
        return "approved"
    
    logger.info("Critic requested revision",
                revision_count=revision_count,
                feedback=state.get("critic_feedback", "")[:100])
    return "revise"
```

---

## 图组装

```python
# src/graph/workflow.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.graph.state import AgentState
from src.graph.nodes import (
    router_node, planner_node,
    rag_agent_node, market_agent_node,
    news_agent_node, tokenomics_agent_node,
    analyst_node, critic_node,
)
from src.graph.edges import route_to_agents, should_revise


def build_workflow(checkpointer=None):
    """构建并编译多智能体工作流。
    
    Args:
        checkpointer: LangGraph checkpointer 实例，用于对话记忆。
                      默认使用 MemorySaver (内存存储)。
    
    Returns:
        编译后的 CompiledGraph，可通过 .ainvoke() 调用。
    """
    if checkpointer is None:
        checkpointer = MemorySaver()
    
    graph = StateGraph(AgentState)
    
    # --- 添加节点 ---
    graph.add_node("router", router_node)
    graph.add_node("planner", planner_node)
    graph.add_node("rag_agent", rag_agent_node)
    graph.add_node("market_agent", market_agent_node)
    graph.add_node("news_agent", news_agent_node)
    graph.add_node("tokenomics_agent", tokenomics_agent_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("critic", critic_node)
    
    # --- 入口 ---
    graph.set_entry_point("router")
    
    # --- 固定边 ---
    graph.add_edge("router", "planner")
    
    # --- Planner → 子 Agent (条件路由) ---
    graph.add_conditional_edges("planner", route_to_agents, {
        "parallel_all": ["rag_agent", "market_agent", 
                         "news_agent", "tokenomics_agent"],
        "rag_only": ["rag_agent"],
        "rag_and_market": ["rag_agent", "market_agent"],
    })
    
    # --- 子 Agent → Analyst (fan-in) ---
    graph.add_edge("rag_agent", "analyst")
    graph.add_edge("market_agent", "analyst")
    graph.add_edge("news_agent", "analyst")
    graph.add_edge("tokenomics_agent", "analyst")
    
    # --- Analyst → Critic ---
    graph.add_edge("analyst", "critic")
    
    # --- Critic → END 或回到 Analyst ---
    graph.add_conditional_edges("critic", should_revise, {
        "approved": END,
        "revise": "analyst",
    })
    
    # --- 编译 ---
    return graph.compile(checkpointer=checkpointer)
```

---

## 调用方式

```python
# 基本调用
import asyncio
from src.graph.workflow import build_workflow

async def main():
    graph = build_workflow()
    
    result = await graph.ainvoke(
        {
            "messages": [],
            "user_query": "分析 Arbitrum 是否值得投资",
            "workflow_type": "",
            "target_entities": [],
            "execution_plan": [],
            "rag_result": None,
            "market_data": None,
            "news_data": None,
            "tokenomics_data": None,
            "analysis_report": None,
            "critic_feedback": None,
            "critic_approved": False,
            "revision_count": 0,
        },
        config={"configurable": {"thread_id": "session_001"}},
    )
    
    print(result["analysis_report"])

asyncio.run(main())
```

```python
# 流式输出
async def stream_main():
    graph = build_workflow()
    
    async for event in graph.astream(initial_state, config=config):
        for node_name, output in event.items():
            print(f"[{node_name}] completed")
            # 可以在这里把中间结果推送给前端
```

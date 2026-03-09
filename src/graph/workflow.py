"""Main workflow orchestration graph built with LangGraph.

Assembles the full multi-agent StateGraph with:
- Sequential: router -> planner
- Parallel fan-out: specialist agents (rag, market, news, tokenomics)
- Sequential fan-in: analyst -> critic
- Conditional loop: critic -> analyst (revision) or END
"""

from __future__ import annotations

import structlog
from langgraph.graph import END, StateGraph

from src.graph.edges import route_after_critic, route_after_planner
from src.graph.nodes import (
    run_analyst,
    run_critic,
    run_market_agent,
    run_news_agent,
    run_planner,
    run_rag_agent,
    run_router,
    run_tokenomics_agent,
)
from src.graph.state import AgentState
from src.memory.checkpointer import get_checkpointer

logger = structlog.get_logger(__name__)


def _build_graph() -> StateGraph:
    """Build the raw StateGraph without compiling.

    Returns:
        An uncompiled StateGraph with all nodes and edges defined.
    """
    graph = StateGraph(AgentState)

    # --- Add nodes ---
    graph.add_node("router", run_router)
    graph.add_node("planner", run_planner)
    graph.add_node("rag_agent", run_rag_agent)
    graph.add_node("market_agent", run_market_agent)
    graph.add_node("news_agent", run_news_agent)
    graph.add_node("tokenomics_agent", run_tokenomics_agent)
    graph.add_node("analyst", run_analyst)
    graph.add_node("critic", run_critic)

    # --- Sequential edges ---
    graph.set_entry_point("router")
    graph.add_edge("router", "planner")

    # --- Fan-out from planner to specialist agents ---
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "rag_agent": "rag_agent",
            "market_agent": "market_agent",
            "news_agent": "news_agent",
            "tokenomics_agent": "tokenomics_agent",
        },
    )

    # --- Fan-in: all specialists converge to analyst ---
    graph.add_edge("rag_agent", "analyst")
    graph.add_edge("market_agent", "analyst")
    graph.add_edge("news_agent", "analyst")
    graph.add_edge("tokenomics_agent", "analyst")

    # --- Analyst to Critic ---
    graph.add_edge("analyst", "critic")

    # --- Critic conditional: approve -> END, reject -> analyst ---
    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "analyst": "analyst",
            "__end__": END,
        },
    )

    logger.info("workflow_built")
    return graph


def build_workflow(checkpointer=None):
    """Build and compile the multi-agent workflow graph.

    The workflow follows this structure:
        START -> router -> planner -> [fan-out: specialists] -> analyst -> critic
        critic -> analyst (if revision needed, up to 2x)
        critic -> END (if approved)

    Args:
        checkpointer: LangGraph checkpointer instance. Defaults to MemorySaver.

    Returns:
        A compiled LangGraph app ready for .ainvoke() or .astream().
    """
    graph = _build_graph()
    if checkpointer is None:
        checkpointer = get_checkpointer()
    app = graph.compile(checkpointer=checkpointer)
    logger.info("workflow_compiled")
    return app


# Alias for backward compatibility
compile_workflow = build_workflow


def create_initial_state(user_query: str) -> dict:
    """Create a properly initialized state dict for workflow invocation.

    Args:
        user_query: The user's natural language query.

    Returns:
        A dict with all AgentState fields set to sensible defaults.
    """
    return {
        "messages": [],
        "user_query": user_query,
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
    }


def get_graph_visualization() -> StateGraph:
    """Return the raw uncompiled StateGraph for visualization.

    Use this for exporting Mermaid diagrams or PNG visualizations:
        graph = get_graph_visualization()
        compiled = graph.compile()
        compiled.get_graph().draw_mermaid_png(output_file_path="workflow.png")

    Returns:
        An uncompiled StateGraph.
    """
    return _build_graph()

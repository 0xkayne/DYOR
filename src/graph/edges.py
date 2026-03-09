"""Conditional edge definitions for routing between graph nodes.

Contains routing functions used by LangGraph's add_conditional_edges
to determine the next node(s) based on current state.
"""

from __future__ import annotations

from typing import Literal

import structlog

from src.graph.state import AgentState

logger = structlog.get_logger(__name__)


def route_after_planner(
    state: AgentState,
) -> list[str]:
    """Determine which specialist agents to fan-out to after planning.

    Reads the execution_plan from state and returns the list of node
    names to invoke in parallel.

    Args:
        state: Current workflow state with execution_plan.

    Returns:
        List of node names to invoke.
    """
    plan = state.get("execution_plan", [])

    # Map plan agent names to graph node names
    agent_to_node = {
        "rag_agent": "rag_agent",
        "market_agent": "market_agent",
        "news_agent": "news_agent",
        "tokenomics_agent": "tokenomics_agent",
        # Also accept short names
        "rag": "rag_agent",
        "market": "market_agent",
        "news": "news_agent",
        "tokenomics": "tokenomics_agent",
    }

    nodes = []
    for agent_name in plan:
        node = agent_to_node.get(agent_name)
        if node and node not in nodes:
            nodes.append(node)

    if not nodes:
        logger.warning("route_after_planner_empty_plan", defaulting_to="rag_agent")
        nodes = ["rag_agent"]

    logger.info("route_after_planner", nodes=nodes)
    return nodes


def route_after_critic(
    state: AgentState,
) -> Literal["analyst", "__end__"]:
    """Determine whether to revise the report or finish.

    If the critic approved, go to __end__. Otherwise, loop back
    to the analyst for revision.

    Args:
        state: Current workflow state with critic_approved.

    Returns:
        "analyst" for revision or "__end__" to finish.
    """
    approved = state.get("critic_approved", False)

    if approved:
        logger.info("route_after_critic", decision="end")
        return "__end__"
    else:
        logger.info("route_after_critic", decision="revise")
        return "analyst"

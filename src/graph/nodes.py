"""Graph node definitions wrapping each agent as a LangGraph node.

Each node function has the signature:
    async def node_name(state: AgentState) -> dict

Node functions handle None gracefully since parallel agents may not
have finished or may have been skipped by the planner.
"""

from __future__ import annotations

import structlog

from src.agents.analyst import analyst_node
from src.agents.critic import critic_node
from src.agents.market_agent import market_agent_node
from src.agents.news_agent import news_agent_node
from src.agents.planner import planner_node
from src.agents.rag_agent import rag_agent_node
from src.agents.router import router_node
from src.agents.tokenomics_agent import tokenomics_agent_node
from src.graph.state import AgentState

logger = structlog.get_logger(__name__)


async def run_router(state: AgentState) -> dict:
    """Router node: classify query and extract entities.

    Args:
        state: Current workflow state.

    Returns:
        State update with workflow_type and target_entities.
    """
    logger.info("node_start", node="router")
    result = await router_node(state)
    logger.info("node_end", node="router", workflow_type=result.get("workflow_type"))
    return result


async def run_planner(state: AgentState) -> dict:
    """Planner node: generate execution plan.

    Args:
        state: Current workflow state.

    Returns:
        State update with execution_plan.
    """
    logger.info("node_start", node="planner")
    result = await planner_node(state)
    logger.info("node_end", node="planner", plan=result.get("execution_plan"))
    return result


async def run_rag_agent(state: AgentState) -> dict:
    """RAG agent node: retrieve knowledge base documents.

    Args:
        state: Current workflow state.

    Returns:
        State update with rag_result.
    """
    logger.info("node_start", node="rag_agent")
    result = await rag_agent_node(state)
    logger.info("node_end", node="rag_agent", has_result=result.get("rag_result") is not None)
    return result


async def run_market_agent(state: AgentState) -> dict:
    """Market agent node: fetch real-time market data.

    Args:
        state: Current workflow state.

    Returns:
        State update with market_data.
    """
    logger.info("node_start", node="market_agent")
    result = await market_agent_node(state)
    logger.info("node_end", node="market_agent", has_result=result.get("market_data") is not None)
    return result


async def run_news_agent(state: AgentState) -> dict:
    """News agent node: fetch news and sentiment data.

    Args:
        state: Current workflow state.

    Returns:
        State update with news_data.
    """
    logger.info("node_start", node="news_agent")
    result = await news_agent_node(state)
    logger.info("node_end", node="news_agent", has_result=result.get("news_data") is not None)
    return result


async def run_tokenomics_agent(state: AgentState) -> dict:
    """Tokenomics agent node: fetch token economics data.

    Args:
        state: Current workflow state.

    Returns:
        State update with tokenomics_data.
    """
    logger.info("node_start", node="tokenomics_agent")
    result = await tokenomics_agent_node(state)
    logger.info(
        "node_end", node="tokenomics_agent",
        has_result=result.get("tokenomics_data") is not None,
    )
    return result


async def run_analyst(state: AgentState) -> dict:
    """Analyst node: synthesize all data into a report.

    Args:
        state: Current workflow state.

    Returns:
        State update with analysis_report.
    """
    logger.info("node_start", node="analyst")
    result = await analyst_node(state)
    logger.info("node_end", node="analyst", has_report=result.get("analysis_report") is not None)
    return result


async def run_critic(state: AgentState) -> dict:
    """Critic node: review report quality.

    Args:
        state: Current workflow state.

    Returns:
        State update with critic_approved, critic_feedback, revision_count.
    """
    logger.info("node_start", node="critic")
    result = await critic_node(state)
    logger.info("node_end", node="critic", approved=result.get("critic_approved"))
    return result

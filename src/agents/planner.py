"""Planner agent that creates execution plans based on query analysis.

Determines which specialist agents to invoke based on the workflow type
and query content, producing an ordered execution plan.
"""

from __future__ import annotations

import asyncio
import json

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.prompts.planner_prompt import PLANNER_SYSTEM_PROMPT
from src.config import settings
from src.graph.state import AgentState

logger = structlog.get_logger(__name__)

_VALID_AGENTS = {"rag_agent", "market_agent", "news_agent", "tokenomics_agent"}

# Map short names to full agent names and vice versa
_SHORT_TO_FULL = {
    "rag": "rag_agent",
    "market": "market_agent",
    "news": "news_agent",
    "tokenomics": "tokenomics_agent",
}

# Static fallback plans when LLM is unavailable
_FALLBACK_PLANS: dict[str, list[str]] = {
    "deep_dive": ["rag_agent", "market_agent", "news_agent", "tokenomics_agent"],
    "compare": ["rag_agent", "market_agent", "news_agent", "tokenomics_agent"],
    "brief": ["rag_agent", "market_agent"],
    "qa": ["rag_agent"],
}


class PlannerAgent:
    """Creates execution plans determining which agents to invoke.

    Uses a lightweight Sonnet model for fast planning decisions.
    """

    def __init__(self) -> None:
        """Initialize the PlannerAgent with a ChatAnthropic LLM."""
        self._llm = ChatAnthropic(
            model=settings.llm_model_sonnet,
            api_key=settings.anthropic_api_key,
            temperature=settings.llm_temperature,
            max_tokens=512,
        )

    async def invoke(self, workflow_type: str, query: str) -> list[str]:
        """Generate an execution plan for the given workflow type and query.

        Args:
            workflow_type: One of deep_dive, compare, brief, qa.
            query: The original user query.

        Returns:
            Ordered list of agent names to invoke.
        """
        try:
            result = await asyncio.wait_for(
                self._call_llm(workflow_type, query),
                timeout=settings.agent_timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.error("planner_timeout", workflow_type=workflow_type)
            return self._fallback(workflow_type)
        except Exception as exc:
            logger.error("planner_error", workflow_type=workflow_type, error=str(exc))
            return self._fallback(workflow_type)

    async def _call_llm(self, workflow_type: str, query: str) -> list[str]:
        """Send the planning request to the LLM and parse the response.

        Args:
            workflow_type: The classified workflow type.
            query: The original user query.

        Returns:
            List of agent names to invoke.
        """
        user_content = (
            f"Workflow type: {workflow_type}\n"
            f"User query: {query}\n\n"
            "Generate the execution plan."
        )
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]
        response = await self._llm.ainvoke(messages)
        raw = response.content
        if isinstance(raw, list):
            raw = raw[0].get("text", "") if raw else ""

        logger.debug("planner_raw_response", response=raw)

        # Handle markdown code blocks
        raw_str = str(raw).strip()
        if "```" in raw_str:
            start = raw_str.find("{")
            end = raw_str.rfind("}") + 1
            if start >= 0 and end > start:
                raw_str = raw_str[start:end]

        parsed = json.loads(raw_str)
        plan = parsed.get("plan") or parsed.get("execution_plan") or []

        # Normalize: accept both short and full agent names
        valid_plan: list[str] = []
        for agent in plan:
            agent_str = str(agent).strip()
            if agent_str in _VALID_AGENTS:
                valid_plan.append(agent_str)
            elif agent_str in _SHORT_TO_FULL:
                valid_plan.append(_SHORT_TO_FULL[agent_str])

        if not valid_plan:
            logger.warning("planner_empty_plan", parsed_plan=plan)
            return self._fallback(workflow_type)

        logger.info("planner_result", plan=valid_plan, reasoning=parsed.get("reasoning", ""))
        return valid_plan

    def _fallback(self, workflow_type: str) -> list[str]:
        """Return a static fallback plan when the LLM is unavailable.

        Args:
            workflow_type: The classified workflow type.

        Returns:
            Default plan for the given workflow type.
        """
        return _FALLBACK_PLANS.get(workflow_type, ["rag_agent"])


_planner = PlannerAgent()


async def planner_node(state: AgentState) -> dict:
    """LangGraph node function wrapping the PlannerAgent.

    Args:
        state: Current agent state with workflow_type and user_query.

    Returns:
        Dict with execution_plan list to merge into state.
    """
    workflow_type = state.get("workflow_type", "qa")
    user_query = state.get("user_query", "")

    plan = await _planner.invoke(workflow_type, user_query)

    logger.info("planner_node_result", execution_plan=plan)
    return {"execution_plan": plan}

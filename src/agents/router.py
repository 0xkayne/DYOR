"""Router agent that classifies user queries and determines workflow type.

Classifies queries into workflow types (deep_dive, compare, brief, qa)
and extracts target crypto project entities using an LLM.
"""

from __future__ import annotations

import asyncio
import json
import re

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.prompts.router_prompt import ROUTER_SYSTEM_PROMPT
from src.config import settings
from src.graph.state import AgentState

logger = structlog.get_logger(__name__)

_VALID_WORKFLOW_TYPES = {"deep_dive", "compare", "brief", "qa"}


class RouterAgent:
    """Classifies user queries and extracts target entities.

    Uses a lightweight Sonnet model for fast intent classification.
    Returns the workflow type and a list of entity names.
    """

    def __init__(self) -> None:
        """Initialize the RouterAgent with a ChatAnthropic LLM."""
        self._llm = ChatAnthropic(
            model=settings.llm_model_sonnet,
            api_key=settings.anthropic_api_key,
            temperature=settings.llm_temperature,
            max_tokens=512,
        )

    async def invoke(self, query: str) -> dict:
        """Classify a user query and extract target entities.

        Args:
            query: The user's natural language query.

        Returns:
            Dict with keys:
                - workflow_type: one of deep_dive, compare, brief, qa
                - target_entities: list of project name strings
                - reasoning: brief classification rationale
        """
        try:
            result = await asyncio.wait_for(
                self._call_llm(query),
                timeout=settings.agent_timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.error("router_timeout", query=query)
            return self._fallback(query)
        except Exception as exc:
            logger.error("router_error", query=query, error=str(exc))
            return self._fallback(query)

    async def _call_llm(self, query: str) -> dict:
        """Send the query to the LLM and parse the JSON response.

        Args:
            query: The user's query.

        Returns:
            Parsed classification dict.
        """
        messages = [
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=query),
        ]
        response = await self._llm.ainvoke(messages)
        raw = response.content
        if isinstance(raw, list):
            raw = raw[0].get("text", "") if raw else ""

        logger.debug("router_raw_response", response=raw)

        # Handle markdown code blocks
        raw_str = str(raw).strip()
        if "```" in raw_str:
            start = raw_str.find("{")
            end = raw_str.rfind("}") + 1
            if start >= 0 and end > start:
                raw_str = raw_str[start:end]

        parsed = json.loads(raw_str)

        # Normalize field names (prompt may use target_entities or entities)
        workflow_type = parsed.get("workflow_type", "qa")
        if workflow_type not in _VALID_WORKFLOW_TYPES:
            workflow_type = "qa"

        target_entities = parsed.get("target_entities") or parsed.get("entities") or []
        if not isinstance(target_entities, list):
            target_entities = [str(target_entities)]

        return {
            "workflow_type": workflow_type,
            "target_entities": target_entities,
            "reasoning": parsed.get("reasoning", ""),
        }

    def _fallback(self, query: str) -> dict:
        """Return a heuristic fallback classification when LLM call fails.

        Uses keyword matching to classify intent and extract entity names.

        Args:
            query: The original user query.

        Returns:
            Fallback classification with best-effort workflow type.
        """
        q = query.lower()
        # Detect workflow type by keywords
        if any(kw in q for kw in ["对比", "比较", "vs", " vs ", "哪个更好"]):
            wf = "compare"
        elif any(kw in q for kw in ["分析", "值得", "投资", "怎么样", "前景", "研究"]):
            wf = "deep_dive"
        elif any(kw in q for kw in ["简报", "概览", "持仓", "关注"]):
            wf = "brief"
        else:
            wf = "qa"

        # Best-effort entity extraction from common patterns
        entities: list[str] = []
        # Match "分析 X" or "X 是否值得"
        for pattern in [
            r"分析\s*(\S+?)(?:\s|是否|值得|的|$)",
            r"(\S+?)\s*(?:是否|值得|怎么样|前景)",
            r"(?:对比|比较)\s*(\S+?)\s*(?:和|与|vs)",
            r"(?:和|与|vs)\s*(\S+?)(?:\s|$)",
        ]:
            matches = re.findall(pattern, query)
            entities.extend(m.strip() for m in matches if m.strip())
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_entities: list[str] = []
        for e in entities:
            if e not in seen:
                seen.add(e)
                unique_entities.append(e)

        return {
            "workflow_type": wf,
            "target_entities": unique_entities,
            "reasoning": "Heuristic fallback due to router error",
        }


# Singleton instance
_router = RouterAgent()


async def router_node(state: AgentState) -> dict:
    """LangGraph node function wrapping the RouterAgent.

    Args:
        state: Current agent state containing user_query.

    Returns:
        Dict with workflow_type and target_entities to merge into state.
    """
    user_query = state.get("user_query", "")
    if not user_query:
        logger.warning("router_empty_query")
        return {"workflow_type": "qa", "target_entities": []}

    result = await _router.invoke(user_query)

    logger.info(
        "router_classified",
        workflow_type=result["workflow_type"],
        entities=result["target_entities"],
    )

    return {
        "workflow_type": result["workflow_type"],
        "target_entities": result["target_entities"],
    }

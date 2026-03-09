"""Analyst agent that synthesizes data from all sources into a comprehensive report.

Receives outputs from RAG, market, news, and tokenomics agents and produces
a structured AnalysisReport using the Opus model for complex reasoning.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.prompts.analyst_prompt import ANALYST_SYSTEM_PROMPT
from src.config import settings
from src.graph.state import AgentState
from src.guardrails.disclaimer import inject_disclaimer
from src.schemas.analysis import AnalysisReport

logger = structlog.get_logger(__name__)


def _format_data_section(name: str, data: dict | None) -> str:
    """Format a data section for the analyst prompt.

    Args:
        name: Human-readable section name.
        data: Data dict from the corresponding agent, or None.

    Returns:
        Formatted string for inclusion in the prompt.
    """
    if data is None:
        return f"\n## {name}\nData unavailable for this dimension.\n"
    return f"\n## {name}\n```json\n{json.dumps(data, ensure_ascii=False, default=str)}\n```\n"


class AnalystAgent:
    """Synthesizes multi-source data into a structured analysis report.

    Uses the Opus model for complex long-context reasoning and synthesis.
    Validates output against the AnalysisReport schema.
    """

    def __init__(self) -> None:
        """Initialize the AnalystAgent with a ChatAnthropic LLM."""
        self._llm = ChatAnthropic(
            model=settings.llm_model_opus,
            api_key=settings.anthropic_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

    async def invoke(
        self,
        query: str,
        rag_result: dict | None,
        market_data: dict | None,
        news_data: dict | None,
        tokenomics_data: dict | None,
        workflow_type: str = "deep_dive",
        entities: list[str] | None = None,
        previous_feedback: str | None = None,
    ) -> dict:
        """Generate a structured analysis report from all available data.

        Args:
            query: The original user query.
            rag_result: Results from the RAG agent, or None.
            market_data: Results from the market agent, or None.
            news_data: Results from the news agent, or None.
            tokenomics_data: Results from the tokenomics agent, or None.
            workflow_type: The workflow type (deep_dive, compare, brief, qa).
            entities: Target entity names.
            previous_feedback: Critic feedback for revision, or None.

        Returns:
            Dict conforming to the AnalysisReport schema.
        """
        try:
            result = await asyncio.wait_for(
                self._generate(
                    query=query,
                    rag_result=rag_result,
                    market_data=market_data,
                    news_data=news_data,
                    tokenomics_data=tokenomics_data,
                    workflow_type=workflow_type,
                    entities=entities or [],
                    previous_feedback=previous_feedback,
                ),
                timeout=settings.agent_timeout * 2,  # Analyst gets extra time for synthesis
            )
            return result
        except asyncio.TimeoutError:
            logger.error("analyst_timeout", query=query)
            return self._fallback(query, workflow_type, entities or [])
        except Exception as exc:
            logger.error("analyst_error", query=query, error=str(exc))
            return self._fallback(query, workflow_type, entities or [])

    async def _generate(
        self,
        query: str,
        rag_result: dict | None,
        market_data: dict | None,
        news_data: dict | None,
        tokenomics_data: dict | None,
        workflow_type: str,
        entities: list[str],
        previous_feedback: str | None,
    ) -> dict:
        """Build the prompt and call the LLM for report generation.

        Args:
            query: The original query.
            rag_result: RAG retrieval results.
            market_data: Market data results.
            news_data: News and sentiment results.
            tokenomics_data: Tokenomics results.
            workflow_type: Workflow type string.
            entities: Target entities.
            previous_feedback: Previous critic feedback.

        Returns:
            Parsed and validated report dict.
        """
        project_name = entities[0] if entities else "Unknown"

        # Build data context
        context_parts = [
            f"# Analysis Request\n"
            f"- Query: {query}\n"
            f"- Project: {project_name}\n"
            f"- Workflow Type: {workflow_type}\n"
            f"- Analysis Date: {datetime.now().isoformat()}\n",
        ]

        context_parts.append(_format_data_section("RAG Knowledge Base Results", rag_result))
        context_parts.append(_format_data_section("Market Data", market_data))
        context_parts.append(_format_data_section("News & Sentiment", news_data))
        context_parts.append(_format_data_section("Tokenomics", tokenomics_data))

        if previous_feedback:
            context_parts.append(
                f"\n## Revision Request\n"
                f"The previous version of this report was rejected. "
                f"Please address the following feedback:\n{previous_feedback}\n"
            )

        # Count available data sources for confidence calibration
        available_sources = sum(
            1 for d in [rag_result, market_data, news_data, tokenomics_data]
            if d is not None
        )
        context_parts.append(
            f"\n## Data Availability\n"
            f"Available data sources: {available_sources}/4. "
            f"Adjust confidence accordingly (lower when fewer sources available).\n"
        )

        user_content = "\n".join(context_parts)

        messages = [
            SystemMessage(content=ANALYST_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]

        response = await self._llm.ainvoke(messages)
        raw = response.content
        if isinstance(raw, list):
            raw = raw[0].get("text", "") if raw else ""

        logger.debug("analyst_raw_response_length", length=len(raw))

        # Extract JSON from response (handle markdown code blocks)
        json_str = self._extract_json(raw)
        parsed = json.loads(json_str)

        # Validate against schema
        try:
            report = AnalysisReport(**parsed)
            result = report.model_dump(mode="json")
        except Exception as validation_err:
            logger.warning(
                "analyst_schema_validation_warning",
                error=str(validation_err),
            )
            # Return raw parsed dict even if schema validation has issues
            # The critic will catch problems
            result = parsed

        logger.info(
            "analyst_completed",
            project=project_name,
            workflow_type=workflow_type,
        )

        return result

    def _extract_json(self, text: str) -> str:
        """Extract JSON content from a response that may contain markdown.

        Args:
            text: Raw LLM response text.

        Returns:
            Cleaned JSON string.
        """
        # Try to find JSON in code blocks
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            return text[start:end].strip()
        if "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            return text[start:end].strip()

        # Try to find JSON object directly
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1:
            return text[first_brace:last_brace + 1]

        return text.strip()

    def _fallback(
        self,
        query: str,
        workflow_type: str,
        entities: list[str],
    ) -> dict:
        """Generate a minimal fallback report when the LLM fails.

        Args:
            query: The original query.
            workflow_type: Workflow type.
            entities: Target entities.

        Returns:
            Minimal report dict.
        """
        project_name = entities[0] if entities else "Unknown"
        return {
            "project_name": project_name,
            "analysis_date": datetime.now().isoformat(),
            "workflow_type": workflow_type,
            "fundamental_analysis": {
                "summary": "Analysis generation failed due to a system error. Please retry.",
                "team_score": 5.0,
                "product_score": 5.0,
                "track_score": 5.0,
                "tokenomics_score": 5.0,
                "sources": [],
            },
            "market_data": None,
            "news_sentiment": None,
            "tokenomics": None,
            "investment_recommendation": {
                "rating": "hold",
                "confidence": 0.1,
                "key_reasons": ["Analysis could not be completed due to system error"],
                "risk_factors": ["Insufficient data for proper analysis"],
                "disclaimer": (
                    "This analysis is for informational purposes only and does not "
                    "constitute financial advice. Always do your own research before "
                    "making investment decisions."
                ),
            },
        }


_analyst = AnalystAgent()


async def analyst_node(state: AgentState) -> dict:
    """LangGraph node function wrapping the AnalystAgent.

    Reads all specialist agent outputs from state and generates
    a structured analysis report.

    Args:
        state: Current agent state with all agent outputs.

    Returns:
        Dict with analysis_report key to merge into state.
    """
    user_query = state.get("user_query", "")
    workflow_type = state.get("workflow_type", "deep_dive")
    target_entities = state.get("target_entities", [])
    rag_result = state.get("rag_result")
    market_data = state.get("market_data")
    news_data = state.get("news_data")
    tokenomics_data = state.get("tokenomics_data")
    critic_feedback = state.get("critic_feedback")

    report = await _analyst.invoke(
        query=user_query,
        rag_result=rag_result,
        market_data=market_data,
        news_data=news_data,
        tokenomics_data=tokenomics_data,
        workflow_type=workflow_type,
        entities=target_entities,
        previous_feedback=critic_feedback,
    )

    # Ensure disclaimer is always present
    report = inject_disclaimer(report)

    logger.info("analyst_node_completed", project=report.get("project_name", "unknown"))
    return {"analysis_report": report}

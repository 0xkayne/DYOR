"""RAG agent with self-RAG loop for retrieving and validating research data.

Retrieves relevant documents from the knowledge base using the AgenticRetriever
and formats them with source citations. Does NOT call an LLM directly.
"""

from __future__ import annotations

import asyncio

import structlog

from src.config import settings
from src.graph.state import AgentState
from src.rag.retriever import AgenticRetriever

logger = structlog.get_logger(__name__)


class RAGAgent:
    """Retrieves and formats research data from the knowledge base.

    Uses the AgenticRetriever for hybrid search with reranking.
    No LLM call is made -- results are returned as-is with citations.
    """

    def __init__(self) -> None:
        """Initialize the RAGAgent with an AgenticRetriever."""
        self._retriever = AgenticRetriever()

    async def invoke(self, query: str, entities: list[str]) -> dict:
        """Retrieve relevant documents for the query and entities.

        Args:
            query: The user's original query.
            entities: List of target project names for context.

        Returns:
            Dict with keys:
                - results: list of result dicts (content, source, project_name, relevance_score)
                - sources: deduplicated list of source document names
                - query: the original query
        """
        try:
            result = await asyncio.wait_for(
                self._retrieve(query, entities),
                timeout=settings.agent_timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.error("rag_agent_timeout", query=query)
            return self._fallback(query)
        except Exception as exc:
            logger.error("rag_agent_error", query=query, error=str(exc))
            return self._fallback(query)

    async def _retrieve(self, query: str, entities: list[str]) -> dict:
        """Execute retrieval for the query and optionally for each entity.

        Args:
            query: The user's query.
            entities: Target project names.

        Returns:
            Formatted retrieval results.
        """
        all_results = []

        # Primary retrieval on the full query
        primary_results = await self._retriever.retrieve(query)
        all_results.extend(primary_results)

        # Supplementary retrieval per entity if not already well-covered
        for entity in entities:
            if entity.lower() not in query.lower():
                entity_results = await self._retriever.retrieve(
                    f"{entity} 项目分析",
                    top_k=3,
                )
                all_results.extend(entity_results)

        # Deduplicate by source + chunk_index
        seen: set[str] = set()
        unique_results: list[dict] = []
        for r in all_results:
            key = f"{r.source}_{r.chunk_index}"
            if key not in seen:
                seen.add(key)
                unique_results.append({
                    "content": r.content,
                    "source": r.source,
                    "project_name": r.project_name,
                    "relevance_score": r.relevance_score,
                })

        # Sort by relevance
        unique_results.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Collect unique sources
        sources = list(dict.fromkeys(
            r["source"] for r in unique_results if r["source"]
        ))

        logger.info(
            "rag_agent_completed",
            query=query,
            result_count=len(unique_results),
            source_count=len(sources),
        )

        return {
            "results": unique_results,
            "sources": sources,
            "query": query,
        }

    def _fallback(self, query: str) -> dict:
        """Return an empty result set on failure.

        Args:
            query: The original query.

        Returns:
            Empty results dict.
        """
        return {
            "results": [],
            "sources": [],
            "query": query,
        }


_rag_agent = RAGAgent()


async def rag_agent_node(state: AgentState) -> dict:
    """LangGraph node function wrapping the RAGAgent.

    Args:
        state: Current agent state with user_query and target_entities.

    Returns:
        Dict with rag_result key to merge into state.
    """
    user_query = state.get("user_query", "")
    target_entities = state.get("target_entities", [])

    if not user_query:
        logger.warning("rag_agent_node_empty_query")
        return {"rag_result": None}

    result = await _rag_agent.invoke(user_query, target_entities)
    return {"rag_result": result}

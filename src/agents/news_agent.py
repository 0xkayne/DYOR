"""News agent for aggregating and analyzing crypto news sentiment.

Calls CryptoPanic MCP tools to search for news and analyze sentiment
for target crypto entities.
"""

from __future__ import annotations

import asyncio

import structlog

from src.config import settings
from src.graph.state import AgentState
from src.mcp_servers.news_server import analyze_sentiment, search_news

logger = structlog.get_logger(__name__)

# Common project name -> ticker for CryptoPanic search
_TICKER_MAP: dict[str, str] = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "arbitrum": "ARB",
    "optimism": "OP",
    "solana": "SOL",
    "polygon": "MATIC",
    "avalanche": "AVAX",
    "polkadot": "DOT",
    "cosmos": "ATOM",
    "uniswap": "UNI",
    "aave": "AAVE",
    "chainlink": "LINK",
    "cardano": "ADA",
    "sui": "SUI",
    "aptos": "APT",
    "sei": "SEI",
    "celestia": "TIA",
    "starknet": "STRK",
    "near": "NEAR",
    "injective": "INJ",
}


def _resolve_ticker(entity: str) -> str:
    """Resolve a project name to a ticker symbol for news search.

    Args:
        entity: Project name or ticker.

    Returns:
        Ticker symbol string.
    """
    normalized = entity.lower().strip()
    return _TICKER_MAP.get(normalized, entity.upper())


class NewsAgent:
    """Aggregates news articles and sentiment analysis for crypto entities.

    Calls MCP tool functions directly to search news and analyze sentiment.
    """

    async def invoke(self, entities: list[str]) -> dict:
        """Fetch news and sentiment for all target entities.

        Args:
            entities: List of project names or tickers.

        Returns:
            Dict with per-entity news and sentiment data.
        """
        try:
            result = await asyncio.wait_for(
                self._fetch_all(entities),
                timeout=settings.agent_timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.error("news_agent_timeout", entities=entities)
            return self._fallback(entities)
        except Exception as exc:
            logger.error("news_agent_error", entities=entities, error=str(exc))
            return self._fallback(entities)

    async def _fetch_all(self, entities: list[str]) -> dict:
        """Fetch news data for all entities concurrently.

        Args:
            entities: List of project names.

        Returns:
            Combined news data dict.
        """
        entity_data: dict[str, dict] = {}

        tasks = []
        for entity in entities:
            tasks.append(self._fetch_entity(entity))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for entity, result in zip(entities, results):
            if isinstance(result, Exception):
                logger.warning(
                    "news_entity_fetch_error",
                    entity=entity,
                    error=str(result),
                )
                entity_data[entity] = {"error": str(result)}
            else:
                entity_data[entity] = result

        logger.info("news_agent_completed", entity_count=len(entity_data))

        return {"entities": entity_data}

    async def _fetch_entity(self, entity: str) -> dict:
        """Fetch news articles and sentiment for a single entity.

        Args:
            entity: Project name or ticker.

        Returns:
            Dict with news and sentiment data.
        """
        ticker = _resolve_ticker(entity)

        # Fetch news and sentiment concurrently
        news_task = search_news(currencies=ticker, count=10)
        sentiment_task = analyze_sentiment(currencies=ticker)

        news_data, sentiment_data = await asyncio.gather(
            news_task, sentiment_task, return_exceptions=True
        )

        result: dict = {"ticker": ticker}

        if isinstance(news_data, Exception):
            logger.warning("news_fetch_error", entity=entity, error=str(news_data))
            result["news"] = {"error": str(news_data)}
        else:
            result["news"] = news_data

        if isinstance(sentiment_data, Exception):
            logger.warning("sentiment_fetch_error", entity=entity, error=str(sentiment_data))
            result["sentiment"] = {"error": str(sentiment_data)}
        else:
            result["sentiment"] = sentiment_data

        return result

    def _fallback(self, entities: list[str]) -> dict:
        """Return empty news data on failure.

        Args:
            entities: The requested entities.

        Returns:
            Fallback dict with error markers.
        """
        return {
            "entities": {
                entity: {"error": "News data unavailable"} for entity in entities
            },
        }


_news_agent = NewsAgent()


async def news_agent_node(state: AgentState) -> dict:
    """LangGraph node function wrapping the NewsAgent.

    Args:
        state: Current agent state with target_entities.

    Returns:
        Dict with news_data key to merge into state.
    """
    target_entities = state.get("target_entities", [])

    if not target_entities:
        logger.warning("news_agent_node_no_entities")
        return {"news_data": None}

    result = await _news_agent.invoke(target_entities)
    return {"news_data": result}

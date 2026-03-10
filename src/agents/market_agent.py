"""Market agent for fetching and analyzing real-time market data via MCP.

Calls CoinGecko MCP tools to get price data, technical indicators,
and market overview for target crypto entities.
"""

from __future__ import annotations

import asyncio

import structlog

from src.config import settings
from src.graph.state import AgentState
from src.mcp_servers.market_server import (
    calculate_technical_indicators,
    get_market_overview,
    get_price,
)

logger = structlog.get_logger(__name__)

# Common project name -> CoinGecko ID mapping
_COIN_ID_MAP: dict[str, str] = {
    "bitcoin": "bitcoin",
    "btc": "bitcoin",
    "ethereum": "ethereum",
    "eth": "ethereum",
    "arbitrum": "arbitrum",
    "arb": "arbitrum",
    "optimism": "optimism",
    "op": "optimism",
    "solana": "solana",
    "sol": "solana",
    "polygon": "matic-network",
    "matic": "matic-network",
    "avalanche": "avalanche-2",
    "avax": "avalanche-2",
    "polkadot": "polkadot",
    "dot": "polkadot",
    "cosmos": "cosmos",
    "atom": "cosmos",
    "uniswap": "uniswap",
    "uni": "uniswap",
    "aave": "aave",
    "chainlink": "chainlink",
    "link": "chainlink",
    "cardano": "cardano",
    "ada": "cardano",
    "sui": "sui",
    "aptos": "aptos",
    "apt": "aptos",
    "sei": "sei-network",
    "celestia": "celestia",
    "tia": "celestia",
    "starknet": "starknet",
    "strk": "starknet",
    "near": "near",
    "injective": "injective-protocol",
    "inj": "injective-protocol",
    "kite ai": "kiteai",
    "kite": "kiteai",
    "kiteai": "kiteai",
}


async def _resolve_coin_id(entity: str) -> str:
    """Resolve a project name or ticker to a CoinGecko coin ID.

    Checks the static mapping first (fast path, no API call), then
    falls back to the dynamic CoinGecko coins/list cache, and finally
    returns the input as-is if nothing matches.

    Args:
        entity: Project name or ticker symbol.

    Returns:
        CoinGecko coin ID string.
    """
    normalized = entity.lower().strip()
    # Fast path: static mapping
    if normalized in _COIN_ID_MAP:
        return _COIN_ID_MAP[normalized]
    # Dynamic resolution via cached coins/list
    from src.mcp_servers.market_server import resolve_coin_id

    resolved = await resolve_coin_id(normalized)
    if resolved:
        return resolved
    # Final fallback: use input as-is
    return normalized


class MarketAgent:
    """Fetches real-time market data for crypto entities.

    Calls MCP tool functions directly (not via MCP protocol) to get
    price, technical indicators, and market overview.
    """

    async def invoke(self, entities: list[str]) -> dict:
        """Fetch market data for all target entities.

        Args:
            entities: List of project names or tickers.

        Returns:
            Dict with keys:
                - entities: per-entity market data
                - market_overview: overall market conditions
        """
        try:
            result = await asyncio.wait_for(
                self._fetch_all(entities),
                timeout=settings.agent_timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.error("market_agent_timeout", entities=entities)
            return self._fallback(entities)
        except Exception as exc:
            logger.error("market_agent_error", entities=entities, error=str(exc))
            return self._fallback(entities)

    async def _fetch_all(self, entities: list[str]) -> dict:
        """Fetch market data for all entities concurrently.

        Args:
            entities: List of project names.

        Returns:
            Combined market data dict.
        """
        entity_data: dict[str, dict] = {}

        # Fetch per-entity data concurrently
        tasks = []
        for entity in entities:
            tasks.append(self._fetch_entity(entity))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for entity, result in zip(entities, results):
            if isinstance(result, Exception):
                logger.warning(
                    "market_entity_fetch_error",
                    entity=entity,
                    error=str(result),
                )
                entity_data[entity] = {"error": str(result)}
            else:
                entity_data[entity] = result

        # Fetch market overview
        overview = await self._fetch_overview()

        logger.info(
            "market_agent_completed",
            entity_count=len(entity_data),
            has_overview=overview is not None,
        )

        return {
            "entities": entity_data,
            "market_overview": overview,
        }

    async def _fetch_entity(self, entity: str) -> dict:
        """Fetch price and technical indicators for a single entity.

        Args:
            entity: Project name or ticker.

        Returns:
            Dict with price and technical_indicators data.
        """
        coin_id = await _resolve_coin_id(entity)

        # Fetch price and indicators concurrently
        price_task = get_price(coin_id)
        indicators_task = calculate_technical_indicators(coin_id)

        price_data, indicators_data = await asyncio.gather(
            price_task, indicators_task, return_exceptions=True
        )

        result: dict = {"coin_id": coin_id}

        if isinstance(price_data, Exception):
            logger.warning("price_fetch_error", entity=entity, error=str(price_data))
            result["price"] = {"error": str(price_data)}
        else:
            result["price"] = price_data

        if isinstance(indicators_data, Exception):
            logger.warning("indicators_fetch_error", entity=entity, error=str(indicators_data))
            result["technical_indicators"] = {"error": str(indicators_data)}
        else:
            result["technical_indicators"] = indicators_data

        return result

    async def _fetch_overview(self) -> dict | None:
        """Fetch the overall crypto market overview.

        Returns:
            Market overview dict, or None on failure.
        """
        try:
            overview = await get_market_overview()
            if "error" in overview:
                logger.warning("market_overview_error", error=overview["error"])
                return None
            return overview
        except Exception as exc:
            logger.warning("market_overview_exception", error=str(exc))
            return None

    def _fallback(self, entities: list[str]) -> dict:
        """Return empty market data on failure.

        Args:
            entities: The requested entities.

        Returns:
            Fallback dict with None values.
        """
        return {
            "entities": {entity: {"error": "Market data unavailable"} for entity in entities},
            "market_overview": None,
        }


_market_agent = MarketAgent()


async def market_agent_node(state: AgentState) -> dict:
    """LangGraph node function wrapping the MarketAgent.

    Args:
        state: Current agent state with target_entities.

    Returns:
        Dict with market_data key to merge into state.
    """
    target_entities = state.get("target_entities", [])

    if not target_entities:
        logger.warning("market_agent_node_no_entities")
        return {"market_data": None}

    result = await _market_agent.invoke(target_entities)
    return {"market_data": result}

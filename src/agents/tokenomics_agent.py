"""Tokenomics agent for analyzing token economics, supply, and unlock schedules.

Calls token unlock MCP tools to get unlock schedules and token distribution
data for target crypto entities.
"""

from __future__ import annotations

import asyncio

import structlog

from src.config import settings
from src.graph.state import AgentState
from src.mcp_servers.unlock_server import get_token_distribution, get_unlock_schedule

logger = structlog.get_logger(__name__)

# Common project name -> token symbol mapping
_SYMBOL_MAP: dict[str, str] = {
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


def _resolve_symbol(entity: str) -> str:
    """Resolve a project name to a token symbol.

    Args:
        entity: Project name or ticker.

    Returns:
        Token symbol string (uppercase).
    """
    normalized = entity.lower().strip()
    return _SYMBOL_MAP.get(normalized, entity.upper())


class TokenomicsAgent:
    """Fetches token economics data for crypto entities.

    Calls MCP tool functions directly to get unlock schedules
    and token distribution breakdowns.
    """

    async def invoke(self, entities: list[str]) -> dict:
        """Fetch tokenomics data for all target entities.

        Args:
            entities: List of project names or tickers.

        Returns:
            Dict with per-entity tokenomics data.
        """
        try:
            result = await asyncio.wait_for(
                self._fetch_all(entities),
                timeout=settings.agent_timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.error("tokenomics_agent_timeout", entities=entities)
            return self._fallback(entities)
        except Exception as exc:
            logger.error("tokenomics_agent_error", entities=entities, error=str(exc))
            return self._fallback(entities)

    async def _fetch_all(self, entities: list[str]) -> dict:
        """Fetch tokenomics data for all entities concurrently.

        Args:
            entities: List of project names.

        Returns:
            Combined tokenomics data dict.
        """
        entity_data: dict[str, dict] = {}

        tasks = []
        for entity in entities:
            tasks.append(self._fetch_entity(entity))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for entity, result in zip(entities, results):
            if isinstance(result, Exception):
                logger.warning(
                    "tokenomics_entity_fetch_error",
                    entity=entity,
                    error=str(result),
                )
                entity_data[entity] = {"error": str(result)}
            else:
                entity_data[entity] = result

        logger.info("tokenomics_agent_completed", entity_count=len(entity_data))

        return {"entities": entity_data}

    async def _fetch_entity(self, entity: str) -> dict:
        """Fetch unlock schedule and distribution for a single entity.

        Args:
            entity: Project name or ticker.

        Returns:
            Dict with unlock_schedule and distribution data.
        """
        symbol = _resolve_symbol(entity)

        # Fetch unlock schedule and distribution concurrently
        unlock_task = get_unlock_schedule(symbol=symbol)
        distribution_task = get_token_distribution(symbol=symbol)

        unlock_data, distribution_data = await asyncio.gather(
            unlock_task, distribution_task, return_exceptions=True
        )

        result: dict = {"symbol": symbol}

        if isinstance(unlock_data, Exception):
            logger.warning("unlock_fetch_error", entity=entity, error=str(unlock_data))
            result["unlock_schedule"] = {"error": str(unlock_data)}
        else:
            result["unlock_schedule"] = unlock_data

        if isinstance(distribution_data, Exception):
            logger.warning("distribution_fetch_error", entity=entity, error=str(distribution_data))
            result["distribution"] = {"error": str(distribution_data)}
        else:
            result["distribution"] = distribution_data

        return result

    def _fallback(self, entities: list[str]) -> dict:
        """Return empty tokenomics data on failure.

        Args:
            entities: The requested entities.

        Returns:
            Fallback dict with error markers.
        """
        return {
            "entities": {
                entity: {"error": "Tokenomics data unavailable"} for entity in entities
            },
        }


_tokenomics_agent = TokenomicsAgent()


async def tokenomics_agent_node(state: AgentState) -> dict:
    """LangGraph node function wrapping the TokenomicsAgent.

    Args:
        state: Current agent state with target_entities.

    Returns:
        Dict with tokenomics_data key to merge into state.
    """
    target_entities = state.get("target_entities", [])

    if not target_entities:
        logger.warning("tokenomics_agent_node_no_entities")
        return {"tokenomics_data": None}

    result = await _tokenomics_agent.invoke(target_entities)
    return {"tokenomics_data": result}

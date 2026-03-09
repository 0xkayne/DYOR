"""Token unlock schedule MCP server for tracking vesting and unlock events."""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import structlog
from mcp.server.fastmcp import FastMCP

from src.schemas.tokenomics import TokenomicsData, UnlockEvent

logger = structlog.get_logger(__name__)
mcp = FastMCP("token-unlock")

TOKEN_DATA_DIR = Path("data/token_data")

_http_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    """Return a reusable async HTTP client, creating one if needed.

    Returns:
        An open httpx.AsyncClient instance with a 10-second timeout.
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


def _load_token_data(symbol: str) -> dict | None:
    """Load token data from the local JSON store.

    Args:
        symbol: Token symbol (e.g. "ARB", "ETH"). Case-insensitive.

    Returns:
        Parsed JSON dict if the file exists, otherwise None.
    """
    path = TOKEN_DATA_DIR / f"{symbol.lower()}.json"
    if path.exists():
        try:
            with open(path) as fh:
                return json.load(fh)
        except Exception as exc:
            logger.warning("local_token_data_load_error", symbol=symbol, error=str(exc))
    return None


async def _fetch_from_defillama(symbol: str) -> dict | None:
    """Fetch token protocol data from DeFiLlama as a fallback.

    Args:
        symbol: Token symbol or protocol slug (e.g. "arb", "uniswap").

    Returns:
        Parsed JSON dict on success, None on any error.
    """
    client = await _get_client()
    url = f"https://api.llama.fi/protocol/{symbol.lower()}"
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.warning("defillama_fetch_failed", symbol=symbol, error=str(exc))
        return None


async def _get_token_info(symbol: str) -> dict:
    """Resolve token data from local store or DeFiLlama fallback.

    Tries local JSON first. If not found, queries DeFiLlama. If neither
    source returns data, returns an error dict.

    Args:
        symbol: Token symbol (e.g. "ARB", "BTC").

    Returns:
        Token data dict with an added "source" key ("local" or "defillama"),
        or {"error": "<message>"} if no data is available.
    """
    local = _load_token_data(symbol)
    if local is not None:
        return local | {"source": "local"}

    defillama = await _fetch_from_defillama(symbol)
    if defillama is not None:
        return defillama | {"source": "defillama"}

    return {"error": f"No data found for token: {symbol}"}


def _parse_unlock_events(raw_events: list[dict], token_name: str) -> list[UnlockEvent]:
    """Parse raw unlock event dicts into UnlockEvent instances.

    Args:
        raw_events: List of dicts with keys: date, amount, percentage, category.
        token_name: Token symbol to attach to each event.

    Returns:
        List of UnlockEvent instances (skipping unparseable entries).
    """
    events: list[UnlockEvent] = []
    for e in raw_events:
        try:
            events.append(
                UnlockEvent(
                    date=datetime.fromisoformat(e["date"]),
                    amount=float(e["amount"]),
                    percentage=float(e.get("percentage", 0.0)),
                    token_name=token_name,
                    category=e.get("category", "unknown"),
                )
            )
        except Exception as exc:
            logger.warning("unlock_event_parse_error", error=str(exc), raw=e)
    return events


@mcp.tool()
async def get_unlock_schedule(symbol: str) -> dict:
    """Get token unlock schedule and vesting timeline for a cryptocurrency.

    Loads the token's full unlock schedule from the local data store. Falls
    back to DeFiLlama API data if no local file is present. Identifies the
    next upcoming unlock event relative to the current date.

    Args:
        symbol: Token ticker symbol (e.g. "ARB", "SOL"). Case-insensitive.

    Returns:
        Dict containing next_unlock (UnlockEvent dict or None),
        circulating_supply_ratio, top_holders_concentration,
        unlock_schedule (list of UnlockEvent dicts), symbol, data_source,
        and fetched_at. Returns {"error": ...} if no data is available.
    """
    try:
        info = await _get_token_info(symbol)
        if "error" in info:
            return {"error": info["error"], "data_source": "local", "symbol": symbol.upper()}

        source = info.get("source", "local")

        if source == "local":
            raw_events = info.get("unlock_schedule", [])
            unlock_events = _parse_unlock_events(raw_events, symbol.upper())

            now = datetime.now(timezone.utc)
            next_unlock: UnlockEvent | None = None
            for event in sorted(unlock_events, key=lambda e: e.date):
                event_dt = event.date
                # Make event_dt timezone-aware for comparison
                if event_dt.tzinfo is None:
                    event_dt = event_dt.replace(tzinfo=timezone.utc)
                if event_dt > now:
                    next_unlock = event
                    break

            total_supply = info.get("total_supply", 1)
            circulating_supply = info.get("circulating_supply", 0)
            circulating_ratio = circulating_supply / total_supply if total_supply else 0.0
            top_holders = info.get("top_holders_pct", 0.0)

            tokenomics = TokenomicsData(
                next_unlock=next_unlock,
                circulating_supply_ratio=min(1.0, max(0.0, circulating_ratio)),
                top_holders_concentration=min(1.0, max(0.0, top_holders)),
                unlock_schedule=unlock_events,
            )
        else:
            # DeFiLlama data — limited structure
            tokenomics = TokenomicsData(
                next_unlock=None,
                circulating_supply_ratio=0.0,
                top_holders_concentration=0.0,
                unlock_schedule=[],
            )

        return tokenomics.model_dump() | {
            "symbol": symbol.upper(),
            "data_source": source,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("get_unlock_schedule_error", symbol=symbol, error=str(exc))
        return {"error": str(exc), "data_source": "local", "symbol": symbol.upper()}


@mcp.tool()
async def get_token_distribution(symbol: str) -> dict:
    """Get token distribution breakdown by category for a cryptocurrency.

    Returns the allocation percentages across categories such as team,
    investors, DAO treasury, airdrop, and ecosystem. Data is sourced from
    local JSON files for major tokens; DeFiLlama is used as a fallback.

    Args:
        symbol: Token ticker symbol (e.g. "ARB", "ETH"). Case-insensitive.

    Returns:
        Dict containing a "distribution" sub-dict (category -> fraction),
        symbol, total_supply, circulating_supply, data_source, and
        fetched_at. Returns {"error": ...} if no data is available.
    """
    try:
        info = await _get_token_info(symbol)
        if "error" in info:
            return {"error": info["error"], "data_source": "local", "symbol": symbol.upper()}

        source = info.get("source", "local")

        if source == "local":
            return {
                "symbol": symbol.upper(),
                "distribution": info.get("distribution", {}),
                "total_supply": info.get("total_supply", 0),
                "circulating_supply": info.get("circulating_supply", 0),
                "data_source": source,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            # DeFiLlama may carry some supply info
            return {
                "symbol": symbol.upper(),
                "distribution": {},
                "total_supply": info.get("totalSupply", 0),
                "circulating_supply": info.get("circulatingSupply", 0),
                "data_source": source,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as exc:
        logger.error("get_token_distribution_error", symbol=symbol, error=str(exc))
        return {"error": str(exc), "data_source": "local", "symbol": symbol.upper()}


@mcp.tool()
async def get_vesting_info(symbol: str) -> dict:
    """Get vesting period information for a token including start and end dates.

    Provides vesting timeline details such as the vesting start date, end
    date, total and circulating supply, and how far through the vesting
    period the token currently is (expressed as a 0–1 progress ratio).

    Args:
        symbol: Token ticker symbol (e.g. "ARB", "SOL"). Case-insensitive.

    Returns:
        Dict containing vesting_start, vesting_end, total_supply,
        circulating_supply, circulating_ratio, vesting_progress (0–1
        fraction of elapsed vesting duration), symbol, data_source, and
        fetched_at. Returns {"error": ...} if no data is available.
    """
    try:
        info = await _get_token_info(symbol)
        if "error" in info:
            return {"error": info["error"], "data_source": "local", "symbol": symbol.upper()}

        source = info.get("source", "local")

        if source == "local":
            vesting_start_str = info.get("vesting_start", "")
            vesting_end_str = info.get("vesting_end", "")
            total_supply = info.get("total_supply", 0)
            circulating_supply = info.get("circulating_supply", 0)
            circulating_ratio = circulating_supply / total_supply if total_supply else 0.0

            # Compute progress through vesting period
            vesting_progress = 0.0
            if vesting_start_str and vesting_end_str:
                try:
                    start_dt = datetime.fromisoformat(vesting_start_str).replace(
                        tzinfo=timezone.utc
                    )
                    end_dt = datetime.fromisoformat(vesting_end_str).replace(
                        tzinfo=timezone.utc
                    )
                    now = datetime.now(timezone.utc)
                    total_duration = (end_dt - start_dt).total_seconds()
                    elapsed = (now - start_dt).total_seconds()
                    if total_duration > 0:
                        vesting_progress = max(0.0, min(1.0, elapsed / total_duration))
                except Exception as exc:
                    logger.warning("vesting_progress_calc_error", error=str(exc))

            return {
                "symbol": symbol.upper(),
                "vesting_start": vesting_start_str,
                "vesting_end": vesting_end_str,
                "total_supply": total_supply,
                "circulating_supply": circulating_supply,
                "circulating_ratio": round(circulating_ratio, 4),
                "vesting_progress": round(vesting_progress, 4),
                "data_source": source,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            # DeFiLlama fallback — return what's available
            return {
                "symbol": symbol.upper(),
                "vesting_start": None,
                "vesting_end": None,
                "total_supply": info.get("totalSupply", 0),
                "circulating_supply": info.get("circulatingSupply", 0),
                "circulating_ratio": 0.0,
                "vesting_progress": 0.0,
                "data_source": source,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as exc:
        logger.error("get_vesting_info_error", symbol=symbol, error=str(exc))
        return {"error": str(exc), "data_source": "local", "symbol": symbol.upper()}


if __name__ == "__main__":
    mcp.run()

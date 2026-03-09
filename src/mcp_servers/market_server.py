"""CoinGecko market data MCP server for price, history, and technical indicators."""

import asyncio
from datetime import datetime, timezone
from math import sqrt

import httpx
import structlog
from mcp.server.fastmcp import FastMCP

from src.config import settings
from src.schemas.market import MarketData, MarketOverview, PriceHistory

logger = structlog.get_logger(__name__)
mcp = FastMCP("crypto-market")

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


async def _cg_request(path: str, params: dict | None = None) -> dict:
    """Perform a CoinGecko API request with retry and exponential back-off.

    Retries up to 3 times on HTTP 429 / 5xx responses or timeouts (max 2
    retries for timeouts). Waits 2**attempt seconds between attempts.

    Args:
        path: API path to append to the base URL (e.g. "/coins/bitcoin").
        params: Optional query-string parameters.

    Returns:
        Parsed JSON response as a dict, or {"error": "<message>"} on failure.
    """
    client = await _get_client()
    url = settings.coingecko_base_url + path
    headers: dict[str, str] = {}
    if settings.coingecko_api_key:
        headers["x-cg-demo-api-key"] = settings.coingecko_api_key

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code == 429 or response.status_code >= 500:
                wait = 2 ** attempt
                logger.warning(
                    "cg_request_retry",
                    status=response.status_code,
                    attempt=attempt,
                    wait=wait,
                    path=path,
                )
                await asyncio.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            last_exc = exc
            if attempt >= 2:
                break
            wait = 2 ** attempt
            logger.warning("cg_request_timeout", attempt=attempt, wait=wait, path=path)
            await asyncio.sleep(wait)
        except Exception as exc:
            last_exc = exc
            break

    err_msg = str(last_exc) if last_exc else "Max retries exceeded"
    logger.error("cg_request_failed", path=path, error=err_msg)
    return {"error": err_msg}


@mcp.tool()
async def get_price(coin_id: str, currency: str = "usd") -> dict:
    """Get current price and market data for a cryptocurrency.

    Fetches real-time price, 24-hour and 7-day percentage changes, market
    capitalisation, and 24-hour trading volume from CoinGecko.

    Args:
        coin_id: CoinGecko coin identifier (e.g. "bitcoin", "ethereum").
        currency: Target fiat or crypto currency for pricing (default "usd").

    Returns:
        Dict containing current_price, price_change_24h, price_change_7d,
        market_cap, volume_24h, technical_indicators, data_source, and
        fetched_at. Returns {"error": ..., "data_source": "coingecko"} on
        failure.
    """
    try:
        data = await _cg_request(
            f"/coins/{coin_id}",
            {
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false",
            },
        )
        if "error" in data:
            return {"error": data["error"], "data_source": "coingecko"}

        md = data["market_data"]
        market = MarketData(
            current_price=md["current_price"].get(currency, 0.0),
            price_change_24h=md.get("price_change_percentage_24h") or 0.0,
            price_change_7d=md.get("price_change_percentage_7d") or 0.0,
            market_cap=md["market_cap"].get(currency, 0.0),
            volume_24h=md["total_volume"].get(currency, 0.0),
            technical_indicators={},
        )
        return market.model_dump() | {
            "data_source": "coingecko",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("get_price_error", coin_id=coin_id, error=str(exc))
        return {"error": str(exc), "data_source": "coingecko"}


@mcp.tool()
async def get_price_history(coin_id: str, days: int = 30, currency: str = "usd") -> dict:
    """Get historical price data for a cryptocurrency over a specified time period.

    Retrieves OHLCV-style market chart data from CoinGecko and returns
    a time-series of daily closing prices.

    Args:
        coin_id: CoinGecko coin identifier (e.g. "bitcoin", "ethereum").
        days: Number of days of history to retrieve (default 30, max 365 for
            free tier without interval granularity concerns).
        currency: Target currency for prices (default "usd").

    Returns:
        Dict containing coin_id, dates (ISO strings), prices (floats),
        currency, data_source, and fetched_at. Returns {"error": ...} on
        failure.
    """
    try:
        data = await _cg_request(
            f"/coins/{coin_id}/market_chart",
            {"vs_currency": currency, "days": str(days)},
        )
        if "error" in data:
            return {"error": data["error"], "data_source": "coingecko"}

        raw_prices = data.get("prices", [])
        dates = [
            datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()
            for ts, _ in raw_prices
        ]
        prices = [price for _, price in raw_prices]

        history = PriceHistory(
            coin_id=coin_id,
            dates=dates,
            prices=prices,
            currency=currency,
        )
        return history.model_dump() | {
            "data_source": "coingecko",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("get_price_history_error", coin_id=coin_id, error=str(exc))
        return {"error": str(exc), "data_source": "coingecko"}


@mcp.tool()
async def get_market_overview() -> dict:
    """Get overall crypto market overview including fear and greed index.

    Fetches total crypto market capitalisation and Bitcoin dominance from
    CoinGecko's /global endpoint, then supplements with the Fear & Greed
    Index from alternative.me. Falls back to a neutral score of 50 if the
    Fear & Greed API is unreachable.

    Returns:
        Dict containing total_market_cap, btc_dominance, fear_greed_index,
        timestamp, data_source, and fetched_at. Returns {"error": ...} on
        CoinGecko failure.
    """
    try:
        data = await _cg_request("/global")
        if "error" in data:
            return {"error": data["error"], "data_source": "coingecko"}

        global_data = data["data"]
        total_market_cap = global_data["total_market_cap"].get("usd", 0.0)
        btc_dominance = global_data["market_cap_percentage"].get("btc", 0.0)

        # Fear & Greed index — best-effort, default to 50 on any failure
        fear_greed = 50
        try:
            client = await _get_client()
            fg_response = await client.get("https://api.alternative.me/fng/", timeout=10.0)
            fg_data = fg_response.json()
            fear_greed = int(fg_data["data"][0]["value"])
        except Exception as fg_exc:
            logger.warning("fear_greed_fetch_failed", error=str(fg_exc))

        overview = MarketOverview(
            total_market_cap=total_market_cap,
            btc_dominance=btc_dominance,
            fear_greed_index=fear_greed,
            timestamp=datetime.now(timezone.utc),
        )
        return overview.model_dump() | {
            "data_source": "coingecko",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("get_market_overview_error", error=str(exc))
        return {"error": str(exc), "data_source": "coingecko"}


@mcp.tool()
async def calculate_technical_indicators(coin_id: str, days: int = 30) -> dict:
    """Calculate technical indicators (SMA, RSI, volatility) for a cryptocurrency.

    Fetches historical price data and computes:
    - SMA-7: Simple moving average over the last 7 data points.
    - SMA-20: Simple moving average over the last 20 data points.
    - RSI-14: Relative Strength Index over the last 14 periods.
    - Volatility: Annualised standard deviation of daily returns.

    Args:
        coin_id: CoinGecko coin identifier (e.g. "bitcoin", "ethereum").
        days: Number of days of price history to use for calculations
            (default 30; minimum 20 recommended for meaningful indicators).

    Returns:
        Dict containing sma_7, sma_20, rsi_14, volatility (as a decimal),
        data_points (number of price samples used), data_source, and
        fetched_at. Returns {"error": ...} on failure.
    """
    try:
        data = await _cg_request(
            f"/coins/{coin_id}/market_chart",
            {"vs_currency": "usd", "days": str(days)},
        )
        if "error" in data:
            return {"error": data["error"], "data_source": "coingecko"}

        prices = [price for _, price in data.get("prices", [])]
        if not prices:
            return {"error": "No price data available", "data_source": "coingecko"}

        # Simple Moving Averages
        sma_7 = sum(prices[-7:]) / min(7, len(prices))
        sma_20 = sum(prices[-20:]) / min(20, len(prices))

        # RSI-14
        changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [max(c, 0.0) for c in changes]
        losses = [abs(min(c, 0.0)) for c in changes]
        avg_gain = sum(gains[-14:]) / 14
        avg_loss = sum(losses[-14:]) / 14
        if avg_loss == 0:
            rsi_14 = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_14 = 100.0 - 100.0 / (1.0 + rs)

        # Volatility (standard deviation of daily returns)
        daily_returns = [
            (prices[i] - prices[i - 1]) / prices[i - 1]
            for i in range(1, len(prices))
            if prices[i - 1] != 0
        ]
        if daily_returns:
            mean_return = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
            volatility = sqrt(variance)
        else:
            volatility = 0.0

        return {
            "coin_id": coin_id,
            "sma_7": round(sma_7, 6),
            "sma_20": round(sma_20, 6),
            "rsi_14": round(rsi_14, 2),
            "volatility": round(volatility, 6),
            "data_points": len(prices),
            "data_source": "coingecko",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("calculate_technical_indicators_error", coin_id=coin_id, error=str(exc))
        return {"error": str(exc), "data_source": "coingecko"}


if __name__ == "__main__":
    mcp.run()

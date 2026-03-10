"""News aggregation MCP server for fetching and summarizing crypto news."""

import asyncio
from datetime import datetime, timezone

import httpx
import structlog
from mcp.server.fastmcp import FastMCP

from src.config import settings
from src.schemas.news import NewsItem, NewsSentiment

logger = structlog.get_logger(__name__)
mcp = FastMCP("crypto-news")

_http_client: httpx.AsyncClient | None = None

_VALID_FILTERS = {"rising", "hot", "bullish", "bearish", "important", "saved", "lol"}
_VALID_REGIONS = {"en", "de", "nl", "es", "fr", "it", "pt", "ru", "tr", "ar", "zh", "ja", "ko"}

# Warn at startup if API key is missing
if not settings.cryptopanic_api_key:
    logger.warning(
        "cryptopanic_key_missing",
        message="CRYPTOPANIC_API_KEY is not configured. All crypto-news tools will be unavailable.",
    )


async def _get_client() -> httpx.AsyncClient:
    """Return a reusable async HTTP client, creating one if needed.

    Returns:
        An open httpx.AsyncClient instance with a 10-second timeout.
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


async def _cp_request(path: str, params: dict | None = None) -> dict:
    """Perform a CryptoPanic API request with retry and exponential back-off.

    Returns an error dict immediately if the API key is not configured.
    Retries up to 3 times on HTTP 429 / 5xx responses. Waits 2**attempt
    seconds between attempts.

    Args:
        path: API path to append to the base URL (e.g. "/posts/").
        params: Optional query-string parameters (auth_token injected here).

    Returns:
        Parsed JSON response as a dict, or {"error": "<message>"} on failure.
    """
    if not settings.cryptopanic_api_key:
        return {"error": "CryptoPanic API key not configured"}

    merged_params = dict(params or {})
    merged_params["auth_token"] = settings.cryptopanic_api_key

    client = await _get_client()
    url = settings.cryptopanic_base_url + path

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = await client.get(url, params=merged_params)
            if response.status_code in (403, 429) or response.status_code >= 500:
                wait = 2 ** attempt
                logger.warning(
                    "cp_request_retry",
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
            logger.warning("cp_request_timeout", attempt=attempt, wait=wait, path=path)
            await asyncio.sleep(wait)
        except Exception as exc:
            last_exc = exc
            break

    err_msg = str(last_exc) if last_exc else "Max retries exceeded"
    logger.error("cp_request_failed", path=path, error=err_msg)
    return {"error": err_msg}


def _map_sentiment(votes: dict | None) -> str:
    """Map CryptoPanic vote counts to a sentiment label.

    Args:
        votes: Dict of vote type to count from CryptoPanic API, or None.

    Returns:
        "positive", "negative", or "neutral" based on vote balance.
    """
    if not votes:
        return "neutral"
    positive = votes.get("positive", 0) + votes.get("important", 0)
    negative = votes.get("negative", 0) + votes.get("toxic", 0)
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    return "neutral"


def _parse_news_items(results: list[dict], limit: int) -> list[NewsItem]:
    """Convert raw CryptoPanic result dicts to NewsItem instances.

    Skips items that cannot be parsed without raising.

    Args:
        results: List of raw result dicts from CryptoPanic API.
        limit: Maximum number of items to return.

    Returns:
        List of NewsItem instances, up to `limit` in length.
    """
    items: list[NewsItem] = []
    for r in results[:limit]:
        try:
            published_at = datetime.fromisoformat(
                r["published_at"].replace("Z", "+00:00")
            )
            items.append(
                NewsItem(
                    title=r.get("title", ""),
                    source=r.get("source", {}).get("title", "unknown"),
                    url=r.get("url", ""),
                    published_at=published_at,
                    sentiment=_map_sentiment(r.get("votes")),  # type: ignore[arg-type]
                    summary="",
                )
            )
        except Exception as exc:
            logger.warning("news_item_parse_error", error=str(exc))
    return items


@mcp.tool()
async def get_latest_news(filter: str = "all", count: int = 10, regions: str = "") -> dict:
    """Get latest cryptocurrency news articles with sentiment analysis.

    Fetches recent news posts from CryptoPanic filtered by type. Each
    article's sentiment is derived from community vote counts.

    Args:
        filter: Post filter type. Valid values: "all" (default), "rising",
            "hot", "bullish", "bearish", "important", "saved", "lol".
            Invalid values are silently reset to "all".
        count: Maximum number of articles to return (default 10).
        regions: Comma-separated language region codes to filter news.
            Valid values: "en", "de", "nl", "es", "fr", "it", "pt", "ru".
            Empty string means no region filter (default).

    Returns:
        Dict containing news (list of NewsItem dicts), count, filter used,
        regions, data_source, and fetched_at. Returns {"error": ...} if the
        API key is missing or the request fails.
    """
    try:
        if filter != "all" and filter not in _VALID_FILTERS:
            logger.warning("invalid_news_filter", filter=filter, fallback="all")
            filter = "all"

        params: dict = {"kind": "news"}
        if filter != "all":
            params["filter"] = filter
        if regions:
            validated = ",".join(
                r for r in regions.split(",") if r.strip() in _VALID_REGIONS
            )
            if validated:
                params["regions"] = validated
            if validated != regions:
                logger.warning("invalid_regions_ignored", raw=regions, validated=validated)

        data = await _cp_request("/posts/", params)
        if "error" in data:
            return {"error": data["error"], "data_source": "cryptopanic"}

        results = data.get("results", [])
        items = _parse_news_items(results, count)

        return {
            "news": [item.model_dump() for item in items],
            "count": len(items),
            "filter": filter,
            "regions": regions,
            "data_source": "cryptopanic",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("get_latest_news_error", error=str(exc))
        return {"error": str(exc), "data_source": "cryptopanic"}


@mcp.tool()
async def search_news(currencies: str, count: int = 10, filter: str = "all", regions: str = "") -> dict:
    """Search cryptocurrency news by coin ticker codes.

    Queries CryptoPanic for news articles mentioning the specified currency
    tickers. Only uppercase ticker codes are accepted (e.g. "BTC", "ETH",
    "BTC,ETH"). Arbitrary keyword search requires an Enterprise plan.

    Args:
        currencies: Comma-separated uppercase ticker codes (e.g. "BTC",
            "BTC,ETH"). Passed directly to CryptoPanic's currencies param.
        count: Maximum number of articles to return (default 10).
        filter: Post filter type. Valid values: "all" (default), "rising",
            "hot", "bullish", "bearish", "important", "saved", "lol".
        regions: Comma-separated language region codes (e.g. "en", "de").

    Returns:
        Dict containing news (list of NewsItem dicts), count, currencies,
        data_source, and fetched_at. Returns {"error": ...} if the API key
        is missing or the request fails.
    """
    try:
        params: dict = {"currencies": currencies, "kind": "news"}
        if filter != "all":
            if filter in _VALID_FILTERS:
                params["filter"] = filter
            else:
                logger.warning("invalid_news_filter", filter=filter, fallback="all")
        if regions:
            validated = ",".join(
                r for r in regions.split(",") if r.strip() in _VALID_REGIONS
            )
            if validated:
                params["regions"] = validated
            if validated != regions:
                logger.warning("invalid_regions_ignored", raw=regions, validated=validated)

        data = await _cp_request("/posts/", params)
        if "error" in data:
            return {"error": data["error"], "data_source": "cryptopanic"}

        results = data.get("results", [])
        items = _parse_news_items(results, count)

        return {
            "news": [item.model_dump() for item in items],
            "count": len(items),
            "currencies": currencies,
            "data_source": "cryptopanic",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("search_news_error", currencies=currencies, error=str(exc))
        return {"error": str(exc), "data_source": "cryptopanic"}


@mcp.tool()
async def analyze_sentiment(currencies: str) -> dict:
    """Analyze overall news sentiment for a specific cryptocurrency.

    Fetches recent news for the given coin and aggregates sentiment across
    all articles using CryptoPanic community vote data. Returns an overall
    sentiment label and a normalised score in [-1, 1].

    Args:
        currencies: Uppercase ticker code (e.g. "BTC", "ETH"). Passed
            directly to CryptoPanic as a currencies filter.

    Returns:
        Dict containing overall_sentiment ("positive"/"neutral"/"negative"),
        key_events (list of up to 5 NewsItem dicts), sentiment_score (float),
        total_articles, data_source, and fetched_at. Returns {"error": ...}
        if the API key is missing or the request fails.
    """
    try:
        data = await _cp_request("/posts/", {"currencies": currencies, "kind": "news"})
        if "error" in data:
            return {"error": data["error"], "data_source": "cryptopanic"}

        results = data.get("results", [])
        # Parse all available items for scoring
        items = _parse_news_items(results, len(results))

        positive_count = sum(1 for item in items if item.sentiment == "positive")
        negative_count = sum(1 for item in items if item.sentiment == "negative")
        total = len(items) or 1  # avoid division by zero

        raw_score = (positive_count - negative_count) / total
        score = max(-1.0, min(1.0, raw_score))

        if score > 0.2:
            overall = "positive"
        elif score < -0.2:
            overall = "negative"
        else:
            overall = "neutral"

        sentiment = NewsSentiment(
            overall_sentiment=overall,  # type: ignore[arg-type]
            key_events=items[:5],
            sentiment_score=round(score, 3),
        )

        return sentiment.model_dump() | {
            "total_articles": len(items),
            "data_source": "cryptopanic",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("analyze_sentiment_error", currencies=currencies, error=str(exc))
        return {"error": str(exc), "data_source": "cryptopanic"}


if __name__ == "__main__":
    mcp.run()

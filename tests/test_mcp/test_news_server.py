"""Tests for the CryptoPanic news aggregation MCP server."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.mcp_servers.news_server import (
    _VALID_REGIONS,
    _map_sentiment,
    _parse_news_items,
    analyze_sentiment,
    get_latest_news,
    search_news,
)

SAMPLE_RESULTS = [
    {
        "title": "Bitcoin hits new all-time high",
        "source": {"title": "CoinDesk"},
        "url": "https://coindesk.com/btc-ath",
        "published_at": "2026-03-09T10:00:00Z",
        "votes": {"positive": 5, "negative": 1, "important": 2, "toxic": 0},
    },
    {
        "title": "Ethereum upgrade delayed",
        "source": {"title": "Decrypt"},
        "url": "https://decrypt.co/eth-delay",
        "published_at": "2026-03-09T09:00:00Z",
        "votes": {"positive": 0, "negative": 8, "important": 0, "toxic": 2},
    },
    {
        "title": "DeFi TVL reaches record levels",
        "source": {"title": "The Block"},
        "url": "https://theblock.co/defi-tvl",
        "published_at": "2026-03-09T08:00:00Z",
        "votes": {"positive": 3, "negative": 3, "important": 1, "toxic": 0},
    },
]

CP_POSTS_RESPONSE = {"results": SAMPLE_RESULTS}


class TestMapSentiment:
    def test_positive_when_more_positive_votes(self):
        assert _map_sentiment({"positive": 5, "negative": 1}) == "positive"

    def test_negative_when_more_negative_votes(self):
        assert _map_sentiment({"positive": 1, "negative": 5}) == "negative"

    def test_neutral_when_equal_votes(self):
        assert _map_sentiment({"positive": 3, "negative": 3}) == "neutral"

    def test_neutral_on_none(self):
        assert _map_sentiment(None) == "neutral"

    def test_neutral_on_empty_dict(self):
        assert _map_sentiment({}) == "neutral"

    def test_important_votes_add_to_positive(self):
        assert _map_sentiment({"positive": 0, "important": 5, "negative": 2}) == "positive"

    def test_toxic_votes_add_to_negative(self):
        assert _map_sentiment({"positive": 1, "negative": 0, "toxic": 5}) == "negative"


class TestParseNewsItems:
    def test_parses_correct_count(self):
        items = _parse_news_items(SAMPLE_RESULTS, limit=2)
        assert len(items) == 2

    def test_parses_all_when_limit_exceeds_count(self):
        items = _parse_news_items(SAMPLE_RESULTS, limit=100)
        assert len(items) == 3

    def test_title_and_source_correct(self):
        items = _parse_news_items(SAMPLE_RESULTS, limit=1)
        assert items[0].title == "Bitcoin hits new all-time high"
        assert items[0].source == "CoinDesk"

    def test_sentiment_mapped_correctly(self):
        items = _parse_news_items(SAMPLE_RESULTS, limit=3)
        assert items[0].sentiment == "positive"
        assert items[1].sentiment == "negative"
        # Third item: positive=3+important=1=4 vs negative=3 -> positive
        assert items[2].sentiment == "positive"

    def test_published_at_is_datetime(self):
        items = _parse_news_items(SAMPLE_RESULTS, limit=1)
        assert isinstance(items[0].published_at, datetime)

    def test_skips_malformed_items(self):
        bad = [{"no_title": True}]  # Missing required fields
        items = _parse_news_items(bad, limit=10)
        assert len(items) == 0


class TestGetLatestNews:
    @pytest.mark.asyncio
    async def test_returns_news_list(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value=CP_POSTS_RESPONSE,
        ):
            result = await get_latest_news(filter="all", count=3)

        assert "news" in result
        assert result["count"] == 3
        assert result["filter"] == "all"
        assert result["data_source"] == "cryptopanic"
        assert "fetched_at" in result

    @pytest.mark.asyncio
    async def test_invalid_filter_resets_to_all(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value=CP_POSTS_RESPONSE,
        ):
            result = await get_latest_news(filter="invalid_filter")

        assert result["filter"] == "all"

    @pytest.mark.asyncio
    async def test_count_limits_results(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value=CP_POSTS_RESPONSE,
        ):
            result = await get_latest_news(count=1)

        assert result["count"] == 1
        assert len(result["news"]) == 1

    @pytest.mark.asyncio
    async def test_returns_error_on_api_failure(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value={"error": "API key not configured"},
        ):
            result = await get_latest_news()

        assert "error" in result

    @pytest.mark.asyncio
    async def test_valid_filters_accepted(self):
        valid_filters = ["rising", "hot", "bullish", "bearish", "important"]
        for f in valid_filters:
            with patch(
                "src.mcp_servers.news_server._cp_request",
                new_callable=AsyncMock,
                return_value=CP_POSTS_RESPONSE,
            ):
                result = await get_latest_news(filter=f)
            assert result["filter"] == f


class TestSearchNews:
    @pytest.mark.asyncio
    async def test_returns_news_for_currencies(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value=CP_POSTS_RESPONSE,
        ):
            result = await search_news(currencies="BTC", count=3)

        assert "news" in result
        assert result["currencies"] == "BTC"
        assert result["data_source"] == "cryptopanic"

    @pytest.mark.asyncio
    async def test_returns_error_on_api_failure(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value={"error": "not configured"},
        ):
            result = await search_news(currencies="ETH")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_count_limits_results(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value=CP_POSTS_RESPONSE,
        ):
            result = await search_news(currencies="BTC", count=2)

        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            side_effect=Exception("network failure"),
        ):
            result = await search_news(currencies="BTC")

        assert "error" in result
        assert result["data_source"] == "cryptopanic"

    @pytest.mark.asyncio
    async def test_search_news_with_filter(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value=CP_POSTS_RESPONSE,
        ) as mock_req:
            result = await search_news(currencies="BTC", filter="hot")

        call_params = mock_req.call_args[0][1]
        assert call_params["filter"] == "hot"
        assert result["currencies"] == "BTC"


class TestAnalyzeSentiment:
    @pytest.mark.asyncio
    async def test_returns_sentiment_result(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value=CP_POSTS_RESPONSE,
        ):
            result = await analyze_sentiment("BTC")

        assert "overall_sentiment" in result
        assert result["overall_sentiment"] in ("positive", "neutral", "negative")
        assert "sentiment_score" in result
        assert -1.0 <= result["sentiment_score"] <= 1.0
        assert "key_events" in result
        assert result["total_articles"] == 3
        assert result["data_source"] == "cryptopanic"

    @pytest.mark.asyncio
    async def test_positive_sentiment_for_all_positive_news(self):
        all_positive = {
            "results": [
                {
                    "title": f"Good news {i}",
                    "source": {"title": "Source"},
                    "url": "https://example.com",
                    "published_at": "2026-03-09T10:00:00Z",
                    "votes": {"positive": 10, "negative": 0, "important": 0, "toxic": 0},
                }
                for i in range(5)
            ]
        }
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value=all_positive,
        ):
            result = await analyze_sentiment("BTC")

        assert result["overall_sentiment"] == "positive"
        assert result["sentiment_score"] > 0.2

    @pytest.mark.asyncio
    async def test_negative_sentiment_for_all_negative_news(self):
        all_negative = {
            "results": [
                {
                    "title": f"Bad news {i}",
                    "source": {"title": "Source"},
                    "url": "https://example.com",
                    "published_at": "2026-03-09T10:00:00Z",
                    "votes": {"positive": 0, "negative": 10, "important": 0, "toxic": 0},
                }
                for i in range(5)
            ]
        }
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value=all_negative,
        ):
            result = await analyze_sentiment("ETH")

        assert result["overall_sentiment"] == "negative"
        assert result["sentiment_score"] < -0.2

    @pytest.mark.asyncio
    async def test_key_events_limited_to_5(self):
        many_results = {
            "results": [
                {
                    "title": f"News {i}",
                    "source": {"title": "Source"},
                    "url": "https://example.com",
                    "published_at": "2026-03-09T10:00:00Z",
                    "votes": {},
                }
                for i in range(10)
            ]
        }
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value=many_results,
        ):
            result = await analyze_sentiment("BTC")

        assert len(result["key_events"]) <= 5

    @pytest.mark.asyncio
    async def test_returns_error_on_api_failure(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value={"error": "API key not configured"},
        ):
            result = await analyze_sentiment("BTC")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            side_effect=Exception("timeout"),
        ):
            result = await analyze_sentiment("BTC")

        assert "error" in result
        assert result["data_source"] == "cryptopanic"


class TestRetryOn403:
    @pytest.mark.asyncio
    async def test_retries_on_403(self):
        """Verify that HTTP 403 triggers retry logic like 429."""
        mock_403 = MagicMock()
        mock_403.status_code = 403

        mock_ok = MagicMock()
        mock_ok.status_code = 200
        mock_ok.json.return_value = CP_POSTS_RESPONSE

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_403, mock_ok])

        with (
            patch(
                "src.mcp_servers.news_server._get_client",
                new_callable=AsyncMock,
                return_value=mock_client,
            ),
            patch("src.mcp_servers.news_server.settings") as mock_settings,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_settings.cryptopanic_api_key = "test-key"
            mock_settings.cryptopanic_base_url = "https://cryptopanic.com/api/developer/v2"
            from src.mcp_servers.news_server import _cp_request
            result = await _cp_request("/posts/", {"kind": "news"})

        assert "results" in result
        assert mock_client.get.call_count == 2


class TestFilterAllDefault:
    """Verify that filter='all' is a valid default that doesn't trigger warnings."""

    @pytest.mark.asyncio
    async def test_filter_all_no_warning(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value=CP_POSTS_RESPONSE,
        ) as mock_req, patch(
            "src.mcp_servers.news_server.logger",
        ) as mock_logger:
            result = await get_latest_news(filter="all", count=3)

        assert result["filter"] == "all"
        mock_logger.warning.assert_not_called()
        # "all" should not be sent as a filter param to the API
        call_params = mock_req.call_args[0][1]
        assert "filter" not in call_params

    @pytest.mark.asyncio
    async def test_new_regions_accepted(self):
        """Verify newly added regions (tr, ar, zh, ja, ko) are valid."""
        for region in ("tr", "ar", "zh", "ja", "ko"):
            assert region in _VALID_REGIONS

        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value=CP_POSTS_RESPONSE,
        ) as mock_req:
            result = await get_latest_news(regions="zh,ja", count=2)

        call_params = mock_req.call_args[0][1]
        assert call_params["regions"] == "zh,ja"


class TestRegionsParam:
    @pytest.mark.asyncio
    async def test_regions_param_passed(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value=CP_POSTS_RESPONSE,
        ) as mock_req:
            result = await get_latest_news(regions="en", count=3)

        call_params = mock_req.call_args[0][1]
        assert call_params["regions"] == "en"
        assert result["regions"] == "en"

    @pytest.mark.asyncio
    async def test_invalid_regions_ignored(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value=CP_POSTS_RESPONSE,
        ) as mock_req:
            result = await get_latest_news(regions="xx", count=3)

        call_params = mock_req.call_args[0][1]
        assert "regions" not in call_params

    @pytest.mark.asyncio
    async def test_mixed_regions_filters_invalid(self):
        with patch(
            "src.mcp_servers.news_server._cp_request",
            new_callable=AsyncMock,
            return_value=CP_POSTS_RESPONSE,
        ) as mock_req:
            result = await get_latest_news(regions="en,xx,de", count=3)

        call_params = mock_req.call_args[0][1]
        assert call_params["regions"] == "en,de"

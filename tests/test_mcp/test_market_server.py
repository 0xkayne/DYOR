"""Tests for the CoinGecko market data MCP server."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.mcp_servers.market_server import (
    _cg_request,
    calculate_technical_indicators,
    get_market_overview,
    get_price,
    get_price_history,
)


def _make_mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Build a mock httpx.Response with the given JSON payload."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    return mock


BITCOIN_COIN_RESPONSE = {
    "id": "bitcoin",
    "market_data": {
        "current_price": {"usd": 65000.0},
        "price_change_percentage_24h": 2.5,
        "price_change_percentage_7d": -1.2,
        "market_cap": {"usd": 1_280_000_000_000.0},
        "total_volume": {"usd": 35_000_000_000.0},
    },
}

MARKET_CHART_RESPONSE = {
    "prices": [
        [1700000000000, 40000.0],
        [1700086400000, 41000.0],
        [1700172800000, 42000.0],
        [1700259200000, 43000.0],
        [1700345600000, 44000.0],
        [1700432000000, 45000.0],
        [1700518400000, 46000.0],
        [1700604800000, 47000.0],
        [1700691200000, 48000.0],
        [1700777600000, 49000.0],
        [1700864000000, 50000.0],
        [1700950400000, 51000.0],
        [1701036800000, 52000.0],
        [1701123200000, 53000.0],
        [1701209600000, 54000.0],
        [1701296000000, 55000.0],
        [1701382400000, 56000.0],
        [1701468800000, 57000.0],
        [1701555200000, 58000.0],
        [1701641600000, 59000.0],
        [1701728000000, 60000.0],
    ]
}

GLOBAL_RESPONSE = {
    "data": {
        "total_market_cap": {"usd": 2_500_000_000_000.0},
        "market_cap_percentage": {"btc": 52.3},
    }
}

FEAR_GREED_RESPONSE = {
    "data": [{"value": "72"}]
}


class TestCgRequest:
    @pytest.mark.asyncio
    async def test_successful_request(self):
        mock_resp = _make_mock_response({"id": "bitcoin"})
        with patch(
            "src.mcp_servers.market_server._get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_get_client.return_value = mock_client

            result = await _cg_request("/coins/bitcoin")
            assert result == {"id": "bitcoin"}

    @pytest.mark.asyncio
    async def test_returns_error_on_exception(self):
        with patch(
            "src.mcp_servers.market_server._get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("connection refused"))
            mock_get_client.return_value = mock_client

            result = await _cg_request("/coins/nonexistent")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_retries_on_429(self):
        throttled = _make_mock_response({}, status_code=429)
        success = _make_mock_response({"ok": True}, status_code=200)
        with patch(
            "src.mcp_servers.market_server._get_client",
            new_callable=AsyncMock,
        ) as mock_get_client, patch("asyncio.sleep", new_callable=AsyncMock):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[throttled, success])
            mock_get_client.return_value = mock_client

            result = await _cg_request("/test")
            assert result == {"ok": True}


class TestGetPrice:
    @pytest.mark.asyncio
    async def test_returns_market_data(self):
        with patch(
            "src.mcp_servers.market_server._cg_request",
            new_callable=AsyncMock,
            return_value=BITCOIN_COIN_RESPONSE,
        ):
            result = await get_price("bitcoin")

        assert result["current_price"] == 65000.0
        assert result["price_change_24h"] == 2.5
        assert result["price_change_7d"] == -1.2
        assert result["market_cap"] == 1_280_000_000_000.0
        assert result["volume_24h"] == 35_000_000_000.0
        assert result["data_source"] == "coingecko"
        assert "fetched_at" in result

    @pytest.mark.asyncio
    async def test_returns_error_on_api_failure(self):
        with patch(
            "src.mcp_servers.market_server._cg_request",
            new_callable=AsyncMock,
            return_value={"error": "coin not found"},
        ):
            result = await get_price("notacoin")

        assert "error" in result
        assert result["data_source"] == "coingecko"

    @pytest.mark.asyncio
    async def test_returns_error_on_exception(self):
        with patch(
            "src.mcp_servers.market_server._cg_request",
            new_callable=AsyncMock,
            side_effect=Exception("network error"),
        ):
            result = await get_price("bitcoin")

        assert "error" in result
        assert result["data_source"] == "coingecko"

    @pytest.mark.asyncio
    async def test_custom_currency(self):
        resp = {
            "id": "bitcoin",
            "market_data": {
                "current_price": {"eur": 60000.0},
                "price_change_percentage_24h": 1.0,
                "price_change_percentage_7d": 0.5,
                "market_cap": {"eur": 1_200_000_000_000.0},
                "total_volume": {"eur": 30_000_000_000.0},
            },
        }
        with patch(
            "src.mcp_servers.market_server._cg_request",
            new_callable=AsyncMock,
            return_value=resp,
        ):
            result = await get_price("bitcoin", currency="eur")

        assert result["current_price"] == 60000.0


class TestGetPriceHistory:
    @pytest.mark.asyncio
    async def test_returns_price_history(self):
        with patch(
            "src.mcp_servers.market_server._cg_request",
            new_callable=AsyncMock,
            return_value=MARKET_CHART_RESPONSE,
        ):
            result = await get_price_history("bitcoin", days=21)

        assert result["coin_id"] == "bitcoin"
        assert len(result["dates"]) == 21
        assert len(result["prices"]) == 21
        assert result["prices"][0] == 40000.0
        assert result["data_source"] == "coingecko"
        assert "fetched_at" in result

    @pytest.mark.asyncio
    async def test_returns_error_on_api_failure(self):
        with patch(
            "src.mcp_servers.market_server._cg_request",
            new_callable=AsyncMock,
            return_value={"error": "not found"},
        ):
            result = await get_price_history("fakecoin")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_dates_are_iso_strings(self):
        with patch(
            "src.mcp_servers.market_server._cg_request",
            new_callable=AsyncMock,
            return_value=MARKET_CHART_RESPONSE,
        ):
            result = await get_price_history("bitcoin")

        for date_str in result["dates"]:
            # Should parse without error
            datetime.fromisoformat(date_str)


class TestGetMarketOverview:
    @pytest.mark.asyncio
    async def test_returns_market_overview(self):
        mock_fg_resp = _make_mock_response(FEAR_GREED_RESPONSE)
        with patch(
            "src.mcp_servers.market_server._cg_request",
            new_callable=AsyncMock,
            return_value=GLOBAL_RESPONSE,
        ), patch(
            "src.mcp_servers.market_server._get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_fg_resp)
            mock_get_client.return_value = mock_client

            result = await get_market_overview()

        assert result["total_market_cap"] == 2_500_000_000_000.0
        assert result["btc_dominance"] == 52.3
        assert result["fear_greed_index"] == 72
        assert result["data_source"] == "coingecko"

    @pytest.mark.asyncio
    async def test_fear_greed_defaults_to_50_on_failure(self):
        with patch(
            "src.mcp_servers.market_server._cg_request",
            new_callable=AsyncMock,
            return_value=GLOBAL_RESPONSE,
        ), patch(
            "src.mcp_servers.market_server._get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("unreachable"))
            mock_get_client.return_value = mock_client

            result = await get_market_overview()

        assert result["fear_greed_index"] == 50

    @pytest.mark.asyncio
    async def test_returns_error_on_cg_failure(self):
        with patch(
            "src.mcp_servers.market_server._cg_request",
            new_callable=AsyncMock,
            return_value={"error": "service unavailable"},
        ):
            result = await get_market_overview()

        assert "error" in result


class TestCalculateTechnicalIndicators:
    @pytest.mark.asyncio
    async def test_returns_indicators(self):
        with patch(
            "src.mcp_servers.market_server._cg_request",
            new_callable=AsyncMock,
            return_value=MARKET_CHART_RESPONSE,
        ):
            result = await calculate_technical_indicators("bitcoin", days=21)

        assert "sma_7" in result
        assert "sma_20" in result
        assert "rsi_14" in result
        assert "volatility" in result
        assert result["data_points"] == 21
        assert result["data_source"] == "coingecko"
        assert "fetched_at" in result

    @pytest.mark.asyncio
    async def test_sma_values_are_reasonable(self):
        with patch(
            "src.mcp_servers.market_server._cg_request",
            new_callable=AsyncMock,
            return_value=MARKET_CHART_RESPONSE,
        ):
            result = await calculate_technical_indicators("bitcoin", days=21)

        # Prices go from 40000 to 60000; SMA-7 of last 7 should be ~54k-58k range
        assert 50000 < result["sma_7"] < 62000
        assert 40000 < result["sma_20"] < 62000

    @pytest.mark.asyncio
    async def test_rsi_in_valid_range(self):
        with patch(
            "src.mcp_servers.market_server._cg_request",
            new_callable=AsyncMock,
            return_value=MARKET_CHART_RESPONSE,
        ):
            result = await calculate_technical_indicators("bitcoin")

        # Consistently rising prices → RSI close to 100
        assert 0 <= result["rsi_14"] <= 100

    @pytest.mark.asyncio
    async def test_returns_error_on_empty_prices(self):
        with patch(
            "src.mcp_servers.market_server._cg_request",
            new_callable=AsyncMock,
            return_value={"prices": []},
        ):
            result = await calculate_technical_indicators("bitcoin")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_returns_error_on_api_failure(self):
        with patch(
            "src.mcp_servers.market_server._cg_request",
            new_callable=AsyncMock,
            return_value={"error": "rate limited"},
        ):
            result = await calculate_technical_indicators("bitcoin")

        assert "error" in result

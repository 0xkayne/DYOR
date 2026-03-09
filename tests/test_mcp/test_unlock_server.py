"""Tests for the token unlock schedule MCP server."""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp_servers.unlock_server import (
    _fetch_from_defillama,
    _get_token_info,
    _load_token_data,
    _parse_unlock_events,
    get_token_distribution,
    get_unlock_schedule,
    get_vesting_info,
)

# Sample local token data matching the arb.json structure
SAMPLE_ARB_DATA = {
    "symbol": "ARB",
    "total_supply": 10000000000,
    "circulating_supply": 3500000000,
    "top_holders_pct": 0.42,
    "unlock_schedule": [
        {"date": "2026-06-16", "amount": 92650000, "percentage": 0.93, "category": "team"},
        {"date": "2026-09-16", "amount": 92650000, "percentage": 0.93, "category": "team"},
        {"date": "2027-03-16", "amount": 92650000, "percentage": 0.93, "category": "team"},
    ],
    "distribution": {
        "team": 0.267,
        "investors": 0.175,
        "dao_treasury": 0.427,
        "airdrop": 0.112,
    },
    "vesting_start": "2023-03-23",
    "vesting_end": "2027-03-23",
}

DEFILLAMA_RESPONSE = {
    "name": "Arbitrum",
    "symbol": "ARB",
    "totalSupply": 10000000000,
    "circulatingSupply": 3500000000,
}


class TestLoadTokenData:
    def test_returns_none_for_unknown_symbol(self, tmp_path):
        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path):
            result = _load_token_data("UNKNOWN")
        assert result is None

    def test_loads_existing_file(self, tmp_path):
        token_file = tmp_path / "arb.json"
        token_file.write_text(json.dumps(SAMPLE_ARB_DATA))

        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path):
            result = _load_token_data("ARB")

        assert result is not None
        assert result["symbol"] == "ARB"
        assert result["total_supply"] == 10000000000

    def test_case_insensitive_lookup(self, tmp_path):
        token_file = tmp_path / "arb.json"
        token_file.write_text(json.dumps(SAMPLE_ARB_DATA))

        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path):
            result_upper = _load_token_data("ARB")
            result_lower = _load_token_data("arb")

        assert result_upper is not None
        assert result_lower is not None

    def test_returns_none_on_invalid_json(self, tmp_path):
        token_file = tmp_path / "bad.json"
        token_file.write_text("not valid json {{{")

        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path):
            result = _load_token_data("BAD")

        assert result is None


class TestFetchFromDefillama:
    @pytest.mark.asyncio
    async def test_returns_data_on_success(self):
        import httpx
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = DEFILLAMA_RESPONSE
        mock_resp.raise_for_status = MagicMock()

        with patch(
            "src.mcp_servers.unlock_server._get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_get_client.return_value = mock_client

            result = await _fetch_from_defillama("arb")

        assert result == DEFILLAMA_RESPONSE

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        with patch(
            "src.mcp_servers.unlock_server._get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("connection refused"))
            mock_get_client.return_value = mock_client

            result = await _fetch_from_defillama("unknown")

        assert result is None


class TestGetTokenInfo:
    @pytest.mark.asyncio
    async def test_returns_local_data_when_available(self, tmp_path):
        token_file = tmp_path / "arb.json"
        token_file.write_text(json.dumps(SAMPLE_ARB_DATA))

        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path):
            result = await _get_token_info("ARB")

        assert result["source"] == "local"
        assert result["symbol"] == "ARB"

    @pytest.mark.asyncio
    async def test_falls_back_to_defillama(self, tmp_path):
        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path), patch(
            "src.mcp_servers.unlock_server._fetch_from_defillama",
            new_callable=AsyncMock,
            return_value=DEFILLAMA_RESPONSE,
        ):
            result = await _get_token_info("ARB")

        assert result["source"] == "defillama"

    @pytest.mark.asyncio
    async def test_returns_error_when_no_data(self, tmp_path):
        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path), patch(
            "src.mcp_servers.unlock_server._fetch_from_defillama",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await _get_token_info("UNKNOWN")

        assert "error" in result


class TestParseUnlockEvents:
    def test_parses_valid_events(self):
        raw = [
            {"date": "2026-06-16", "amount": 92650000, "percentage": 0.93, "category": "team"}
        ]
        events = _parse_unlock_events(raw, "ARB")
        assert len(events) == 1
        assert events[0].amount == 92650000
        assert events[0].category == "team"
        assert events[0].token_name == "ARB"

    def test_skips_malformed_events(self):
        raw = [{"bad_field": True}]
        events = _parse_unlock_events(raw, "ARB")
        assert len(events) == 0

    def test_returns_empty_for_empty_list(self):
        assert _parse_unlock_events([], "ARB") == []


class TestGetUnlockSchedule:
    @pytest.mark.asyncio
    async def test_returns_schedule_from_local_data(self, tmp_path):
        token_file = tmp_path / "arb.json"
        token_file.write_text(json.dumps(SAMPLE_ARB_DATA))

        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path):
            result = await get_unlock_schedule("ARB")

        assert result["symbol"] == "ARB"
        assert result["data_source"] == "local"
        assert "unlock_schedule" in result
        assert len(result["unlock_schedule"]) == 3
        assert "circulating_supply_ratio" in result
        assert "fetched_at" in result

    @pytest.mark.asyncio
    async def test_circulating_supply_ratio_correct(self, tmp_path):
        token_file = tmp_path / "arb.json"
        token_file.write_text(json.dumps(SAMPLE_ARB_DATA))

        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path):
            result = await get_unlock_schedule("ARB")

        expected_ratio = 3500000000 / 10000000000
        assert abs(result["circulating_supply_ratio"] - expected_ratio) < 0.001

    @pytest.mark.asyncio
    async def test_next_unlock_is_future_event(self, tmp_path):
        token_file = tmp_path / "arb.json"
        token_file.write_text(json.dumps(SAMPLE_ARB_DATA))

        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path):
            result = await get_unlock_schedule("ARB")

        # All unlock dates in sample data are in the future (2026+)
        if result["next_unlock"] is not None:
            # model_dump() returns datetime objects; accept both datetime and str
            raw_date = result["next_unlock"]["date"]
            if isinstance(raw_date, str):
                next_date = datetime.fromisoformat(raw_date)
            else:
                next_date = raw_date
            now = datetime.now(timezone.utc)
            if next_date.tzinfo is None:
                next_date = next_date.replace(tzinfo=timezone.utc)
            assert next_date > now

    @pytest.mark.asyncio
    async def test_returns_error_for_unknown_token(self, tmp_path):
        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path), patch(
            "src.mcp_servers.unlock_server._fetch_from_defillama",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await get_unlock_schedule("UNKNOWN")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_defillama_fallback_returns_empty_schedule(self, tmp_path):
        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path), patch(
            "src.mcp_servers.unlock_server._fetch_from_defillama",
            new_callable=AsyncMock,
            return_value=DEFILLAMA_RESPONSE,
        ):
            result = await get_unlock_schedule("ARB")

        assert result["data_source"] == "defillama"
        assert result["unlock_schedule"] == []


class TestGetTokenDistribution:
    @pytest.mark.asyncio
    async def test_returns_distribution_from_local(self, tmp_path):
        token_file = tmp_path / "arb.json"
        token_file.write_text(json.dumps(SAMPLE_ARB_DATA))

        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path):
            result = await get_token_distribution("ARB")

        assert result["symbol"] == "ARB"
        assert result["data_source"] == "local"
        assert "distribution" in result
        assert result["distribution"]["team"] == 0.267
        assert result["total_supply"] == 10000000000
        assert result["circulating_supply"] == 3500000000

    @pytest.mark.asyncio
    async def test_returns_error_for_unknown_token(self, tmp_path):
        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path), patch(
            "src.mcp_servers.unlock_server._fetch_from_defillama",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await get_token_distribution("UNKNOWN")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_defillama_fallback_returns_empty_distribution(self, tmp_path):
        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path), patch(
            "src.mcp_servers.unlock_server._fetch_from_defillama",
            new_callable=AsyncMock,
            return_value=DEFILLAMA_RESPONSE,
        ):
            result = await get_token_distribution("ARB")

        assert result["data_source"] == "defillama"
        assert result["distribution"] == {}


class TestGetVestingInfo:
    @pytest.mark.asyncio
    async def test_returns_vesting_info_from_local(self, tmp_path):
        token_file = tmp_path / "arb.json"
        token_file.write_text(json.dumps(SAMPLE_ARB_DATA))

        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path):
            result = await get_vesting_info("ARB")

        assert result["symbol"] == "ARB"
        assert result["vesting_start"] == "2023-03-23"
        assert result["vesting_end"] == "2027-03-23"
        assert result["total_supply"] == 10000000000
        assert result["data_source"] == "local"
        assert "fetched_at" in result

    @pytest.mark.asyncio
    async def test_vesting_progress_between_0_and_1(self, tmp_path):
        token_file = tmp_path / "arb.json"
        token_file.write_text(json.dumps(SAMPLE_ARB_DATA))

        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path):
            result = await get_vesting_info("ARB")

        assert 0.0 <= result["vesting_progress"] <= 1.0

    @pytest.mark.asyncio
    async def test_circulating_ratio_correct(self, tmp_path):
        token_file = tmp_path / "arb.json"
        token_file.write_text(json.dumps(SAMPLE_ARB_DATA))

        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path):
            result = await get_vesting_info("ARB")

        expected = 3500000000 / 10000000000
        assert abs(result["circulating_ratio"] - expected) < 0.001

    @pytest.mark.asyncio
    async def test_vesting_progress_is_positive_since_2023_start(self, tmp_path):
        """Vesting started 2023-03-23; today (2026-03-09) means >0 progress."""
        token_file = tmp_path / "arb.json"
        token_file.write_text(json.dumps(SAMPLE_ARB_DATA))

        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path):
            result = await get_vesting_info("ARB")

        # Today is 2026-03-09, well past vesting start of 2023-03-23
        assert result["vesting_progress"] > 0.0

    @pytest.mark.asyncio
    async def test_returns_error_for_unknown_token(self, tmp_path):
        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path), patch(
            "src.mcp_servers.unlock_server._fetch_from_defillama",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await get_vesting_info("UNKNOWN")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_defillama_fallback_zero_progress(self, tmp_path):
        with patch("src.mcp_servers.unlock_server.TOKEN_DATA_DIR", tmp_path), patch(
            "src.mcp_servers.unlock_server._fetch_from_defillama",
            new_callable=AsyncMock,
            return_value=DEFILLAMA_RESPONSE,
        ):
            result = await get_vesting_info("ARB")

        assert result["data_source"] == "defillama"
        assert result["vesting_progress"] == 0.0
        assert result["vesting_start"] is None

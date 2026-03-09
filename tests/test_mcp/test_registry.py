"""Tests for the MCP tool registry module."""

import pytest

from src.mcp_servers.registry import (
    ToolInfo,
    _registry,
    _tokenize,
    discover_for_task,
    list_tools,
    register,
    register_all_servers,
)


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the registry before and after each test to avoid state leakage."""
    _registry.clear()
    yield
    _registry.clear()


class TestTokenize:
    def test_basic_tokenization(self):
        tokens = _tokenize("Get current price and market data")
        assert "current" in tokens
        assert "price" in tokens
        assert "market" in tokens
        assert "data" in tokens

    def test_stop_words_removed(self):
        tokens = _tokenize("Get the price for a coin")
        assert "the" not in tokens
        assert "for" not in tokens
        assert "a" not in tokens

    def test_short_words_removed(self):
        tokens = _tokenize("go to the API")
        # "go" is 2 chars, filtered; "to" stop word; "the" stop word; "api" kept
        assert "go" not in tokens
        assert "api" in tokens

    def test_non_alpha_stripped(self):
        tokens = _tokenize("price-change 24h!")
        assert "pricechange" in tokens or "price" in tokens
        # The "!" is stripped but "pricechange" depends on split; hyphens keep as separate word
        # Actually split() on "price-change" gives ["price-change"], then isalpha filter gives "pricechange"
        # Let's just confirm no punctuation in results
        for token in tokens:
            assert token.isalpha(), f"Non-alpha token found: {token}"

    def test_empty_string(self):
        assert _tokenize("") == set()

    def test_returns_set(self):
        result = _tokenize("price price price")
        assert isinstance(result, set)
        assert len(result) == 1


class TestRegister:
    def test_register_adds_to_registry(self):
        register("test-server", "my_tool", "Calculate RSI for a cryptocurrency coin", {})
        assert "test-server.my_tool" in _registry

    def test_register_creates_correct_tool_info(self):
        register(
            "test-server",
            "my_tool",
            "Calculate RSI for a cryptocurrency coin",
            {"coin_id": "Coin identifier"},
        )
        tool = _registry["test-server.my_tool"]
        assert tool.server_name == "test-server"
        assert tool.tool_name == "my_tool"
        assert tool.parameters == {"coin_id": "Coin identifier"}

    def test_register_generates_keywords(self):
        register("s", "t", "Calculate RSI for cryptocurrency analysis", {})
        tool = _registry["s.t"]
        assert "calculate" in tool.keywords
        assert "rsi" in tool.keywords
        assert "cryptocurrency" in tool.keywords
        assert "analysis" in tool.keywords
        # Stop word "for" should not appear
        assert "for" not in tool.keywords

    def test_register_overwrites_existing(self):
        register("s", "t", "First description", {})
        register("s", "t", "Second description updated", {})
        tool = _registry["s.t"]
        assert "second" in tool.keywords
        assert "first" not in tool.keywords


class TestListTools:
    def test_empty_registry(self):
        assert list_tools() == []

    def test_returns_all_tools(self):
        register("s1", "t1", "Get price data for coins", {})
        register("s2", "t2", "Fetch news articles", {})
        tools = list_tools()
        assert len(tools) == 2

    def test_returns_tool_info_instances(self):
        register("s", "t", "Some description of a tool", {})
        tools = list_tools()
        assert all(isinstance(t, ToolInfo) for t in tools)


class TestDiscoverForTask:
    def test_returns_matching_tools(self):
        register("market", "get_price", "Get current price for cryptocurrency", {})
        register("news", "get_news", "Fetch latest articles about crypto events", {})
        results = discover_for_task("what is the current price of bitcoin")
        names = [t.tool_name for t in results]
        assert "get_price" in names

    def test_returns_empty_for_no_match(self):
        register("market", "get_price", "Get current price for cryptocurrency", {})
        results = discover_for_task("weather forecast tomorrow rain")
        assert results == []

    def test_returns_at_most_5_results(self):
        for i in range(10):
            register(f"server{i}", f"tool{i}", f"Get price data market crypto coin {i}", {})
        results = discover_for_task("get crypto price market data coin")
        assert len(results) <= 5

    def test_sorted_by_score_descending(self):
        register("s1", "high", "Get cryptocurrency price market data analysis coin", {})
        register("s2", "low", "Get news articles", {})
        results = discover_for_task("cryptocurrency price market coin")
        assert results[0].tool_name == "high"

    def test_empty_task_returns_empty(self):
        register("s", "t", "Get price for cryptocurrency", {})
        results = discover_for_task("")
        assert results == []


class TestRegisterAllServers:
    def test_registers_ten_tools(self):
        register_all_servers()
        assert len(_registry) == 10

    def test_market_tools_registered(self):
        register_all_servers()
        assert "crypto-market.get_price" in _registry
        assert "crypto-market.get_price_history" in _registry
        assert "crypto-market.get_market_overview" in _registry
        assert "crypto-market.calculate_technical_indicators" in _registry

    def test_news_tools_registered(self):
        register_all_servers()
        assert "crypto-news.get_latest_news" in _registry
        assert "crypto-news.search_news" in _registry
        assert "crypto-news.analyze_sentiment" in _registry

    def test_unlock_tools_registered(self):
        register_all_servers()
        assert "token-unlock.get_unlock_schedule" in _registry
        assert "token-unlock.get_token_distribution" in _registry
        assert "token-unlock.get_vesting_info" in _registry

    def test_discover_works_after_register_all(self):
        register_all_servers()
        results = discover_for_task("get current price for bitcoin")
        tool_names = [t.tool_name for t in results]
        assert "get_price" in tool_names

    def test_discover_news_tools(self):
        register_all_servers()
        results = discover_for_task("latest cryptocurrency news articles sentiment")
        tool_names = [t.tool_name for t in results]
        assert any("news" in name or "sentiment" in name for name in tool_names)

    def test_discover_unlock_tools(self):
        register_all_servers()
        results = discover_for_task("token unlock vesting schedule")
        tool_names = [t.tool_name for t in results]
        assert any("unlock" in name or "vesting" in name for name in tool_names)

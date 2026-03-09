"""MCP tool registry for dynamic tool discovery and selection by agents."""

from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)

STOP_WORDS = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
              "have", "has", "had", "do", "does", "did", "will", "would", "could",
              "should", "may", "might", "shall", "can", "need", "dare", "ought",
              "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
              "as", "into", "through", "during", "before", "after", "above", "below",
              "between", "out", "off", "over", "under", "again", "further", "then",
              "once", "here", "there", "when", "where", "why", "how", "all", "each",
              "every", "both", "few", "more", "most", "other", "some", "such", "no",
              "nor", "not", "only", "own", "same", "so", "than", "too", "very",
              "just", "because", "but", "and", "or", "if", "while", "about", "what",
              "which", "who", "whom", "this", "that", "these", "those", "i", "me",
              "my", "myself", "we", "our", "get", "it", "its"}


@dataclass
class ToolInfo:
    """Metadata for a registered MCP tool.

    Attributes:
        server_name: Name of the MCP server that owns this tool.
        tool_name: Name of the tool function.
        description: Human-readable description used for keyword matching.
        parameters: Dict mapping parameter name to its description.
        keywords: Auto-generated keyword list extracted from description.
    """

    server_name: str
    tool_name: str
    description: str
    parameters: dict[str, str] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)


# Module-level registry keyed by "{server_name}.{tool_name}"
_registry: dict[str, ToolInfo] = {}


def _tokenize(text: str) -> set[str]:
    """Tokenize text into a set of meaningful keywords.

    Args:
        text: Raw text string to tokenize.

    Returns:
        Set of lowercase, alpha-only tokens with stop words and short words removed.
    """
    tokens = set()
    for word in text.split():
        cleaned = "".join(c for c in word.lower() if c.isalpha())
        if cleaned and cleaned not in STOP_WORDS and len(cleaned) > 2:
            tokens.add(cleaned)
    return tokens


def register(
    server_name: str,
    tool_name: str,
    description: str,
    parameters: dict[str, str],
) -> None:
    """Register an MCP tool in the registry.

    Automatically generates keywords from the description by tokenizing and
    filtering stop words. Stores the ToolInfo in the module-level registry
    keyed by "{server_name}.{tool_name}".

    Args:
        server_name: Name of the MCP server that owns this tool.
        tool_name: Name of the tool function.
        description: Human-readable description of what the tool does.
        parameters: Dict mapping parameter name to its description.
    """
    key = f"{server_name}.{tool_name}"
    keywords = sorted(_tokenize(description))
    tool_info = ToolInfo(
        server_name=server_name,
        tool_name=tool_name,
        description=description,
        parameters=parameters,
        keywords=keywords,
    )
    _registry[key] = tool_info
    logger.debug("tool_registered", key=key, keyword_count=len(keywords))


def list_tools() -> list[ToolInfo]:
    """Return a list of all registered ToolInfo objects.

    Returns:
        List of all ToolInfo instances currently in the registry.
    """
    return list(_registry.values())


def discover_for_task(task_description: str) -> list[ToolInfo]:
    """Discover relevant tools for a given task description.

    Tokenizes the task description and scores each registered tool by the
    number of keyword overlaps between the task and the tool's keyword list.
    Returns the top 5 tools with a score greater than zero, sorted by score
    in descending order.

    Args:
        task_description: Natural language description of the task to perform.

    Returns:
        List of up to 5 ToolInfo objects most relevant to the task, sorted
        by relevance score descending.
    """
    task_keywords = _tokenize(task_description)
    scored: list[tuple[int, ToolInfo]] = []

    for tool_info in _registry.values():
        tool_keywords = set(tool_info.keywords)
        score = len(task_keywords & tool_keywords)
        if score > 0:
            scored.append((score, tool_info))

    scored.sort(key=lambda x: x[0], reverse=True)
    top5 = [tool_info for _, tool_info in scored[:5]]
    logger.debug("tools_discovered", task_keywords=list(task_keywords), count=len(top5))
    return top5


def register_all_servers() -> None:
    """Register all tools from all three MCP servers in the registry.

    Pre-registers tools from crypto-market, crypto-news, and token-unlock
    servers so agents can discover them via discover_for_task.
    """
    # --- crypto-market ---
    register(
        server_name="crypto-market",
        tool_name="get_price",
        description="Get current price and market data for a cryptocurrency",
        parameters={
            "coin_id": "CoinGecko coin ID",
            "currency": "Target currency",
        },
    )
    register(
        server_name="crypto-market",
        tool_name="get_price_history",
        description="Get historical price data for a cryptocurrency",
        parameters={
            "coin_id": "CoinGecko coin ID",
            "days": "Number of days",
            "currency": "Target currency",
        },
    )
    register(
        server_name="crypto-market",
        tool_name="get_market_overview",
        description="Get overall crypto market overview including fear and greed index",
        parameters={},
    )
    register(
        server_name="crypto-market",
        tool_name="calculate_technical_indicators",
        description="Calculate technical indicators like SMA RSI and volatility for a coin",
        parameters={
            "coin_id": "CoinGecko coin ID",
            "days": "Number of days",
        },
    )

    # --- crypto-news ---
    register(
        server_name="crypto-news",
        tool_name="get_latest_news",
        description="Get latest cryptocurrency news articles with sentiment",
        parameters={
            "filter": "News filter type",
            "count": "Number of articles",
        },
    )
    register(
        server_name="crypto-news",
        tool_name="search_news",
        description="Search cryptocurrency news by keyword or coin name",
        parameters={
            "keyword": "Search keyword",
            "count": "Number of results",
        },
    )
    register(
        server_name="crypto-news",
        tool_name="analyze_sentiment",
        description="Analyze overall news sentiment for a specific cryptocurrency",
        parameters={
            "coin_id": "Coin identifier",
        },
    )

    # --- token-unlock ---
    register(
        server_name="token-unlock",
        tool_name="get_unlock_schedule",
        description="Get token unlock schedule and vesting timeline",
        parameters={
            "symbol": "Token symbol",
        },
    )
    register(
        server_name="token-unlock",
        tool_name="get_token_distribution",
        description="Get token distribution breakdown by category",
        parameters={
            "symbol": "Token symbol",
        },
    )
    register(
        server_name="token-unlock",
        tool_name="get_vesting_info",
        description="Get vesting period information for a token",
        parameters={
            "symbol": "Token symbol",
        },
    )

    logger.info("all_servers_registered", tool_count=len(_registry))

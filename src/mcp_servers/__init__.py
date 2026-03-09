"""MCP Server module providing real-time market, news, and tokenomics data tools."""

from src.mcp_servers.market_server import mcp as market_mcp
from src.mcp_servers.news_server import mcp as news_mcp
from src.mcp_servers.registry import (
    discover_for_task,
    list_tools,
    register,
    register_all_servers,
)
from src.mcp_servers.unlock_server import mcp as unlock_mcp

__all__ = [
    "market_mcp",
    "news_mcp",
    "unlock_mcp",
    "register",
    "list_tools",
    "discover_for_task",
    "register_all_servers",
]

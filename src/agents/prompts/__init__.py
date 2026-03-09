"""System prompts for each agent in the multi-agent workflow.

Exports all prompt constants for convenient import.
"""

from src.agents.prompts.analyst_prompt import ANALYST_SYSTEM_PROMPT
from src.agents.prompts.critic_prompt import CRITIC_SYSTEM_PROMPT
from src.agents.prompts.market_prompt import MARKET_SYSTEM_PROMPT
from src.agents.prompts.news_prompt import NEWS_SYSTEM_PROMPT
from src.agents.prompts.planner_prompt import PLANNER_SYSTEM_PROMPT
from src.agents.prompts.rag_prompt import RAG_SYSTEM_PROMPT
from src.agents.prompts.router_prompt import ROUTER_SYSTEM_PROMPT
from src.agents.prompts.tokenomics_prompt import TOKENOMICS_SYSTEM_PROMPT

__all__ = [
    "ANALYST_SYSTEM_PROMPT",
    "CRITIC_SYSTEM_PROMPT",
    "MARKET_SYSTEM_PROMPT",
    "NEWS_SYSTEM_PROMPT",
    "PLANNER_SYSTEM_PROMPT",
    "RAG_SYSTEM_PROMPT",
    "ROUTER_SYSTEM_PROMPT",
    "TOKENOMICS_SYSTEM_PROMPT",
]

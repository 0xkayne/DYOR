"""AgentState definition for the LangGraph workflow.

Defines the shared state TypedDict that flows through all nodes in the
multi-agent graph. Each agent reads from and writes to specific keys.
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared state for the multi-agent crypto research workflow.

    Each field is documented with which agent reads/writes it.
    Parallel fan-out agents only write their own key; the fan-in
    reducer merges results before the analyst runs.
    """

    # Chat message history, accumulated via add_messages reducer
    messages: Annotated[list, add_messages]

    # Original user query string (set once at entry)
    user_query: str

    # Workflow classification: deep_dive | compare | brief | qa
    # Written by: router
    workflow_type: str

    # Project/token names extracted from the query (English)
    # Written by: router
    target_entities: list[str]

    # Ordered list of agent names to invoke
    # Written by: planner  |  Read by: nodes dispatcher
    execution_plan: list[str]

    # RAG retrieval results with source citations
    # Written by: rag_agent  |  Read by: analyst
    rag_result: dict | None

    # Real-time market data (price, indicators, overview)
    # Written by: market_agent  |  Read by: analyst
    market_data: dict | None

    # News articles and sentiment analysis
    # Written by: news_agent  |  Read by: analyst
    news_data: dict | None

    # Token economics, unlock schedule, distribution
    # Written by: tokenomics_agent  |  Read by: analyst
    tokenomics_data: dict | None

    # Structured analysis report conforming to AnalysisReport schema
    # Written by: analyst  |  Read by: critic, output
    analysis_report: dict | None

    # Feedback from critic explaining required revisions
    # Written by: critic  |  Read by: analyst (on revision)
    critic_feedback: str | None

    # Whether the critic approved the report
    # Written by: critic  |  Read by: conditional edge
    critic_approved: bool

    # Number of revision cycles completed (max 2)
    # Written by: critic  |  Read by: conditional edge, analyst
    revision_count: int

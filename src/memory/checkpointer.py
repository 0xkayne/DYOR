"""LangGraph checkpoint persistence for conversation state.

Provides a singleton MemorySaver instance for use with LangGraph
workflows to enable conversation continuity and state recovery.
"""

from langgraph.checkpoint.memory import MemorySaver

_checkpointer: MemorySaver | None = None


def get_checkpointer() -> MemorySaver:
    """Return a singleton MemorySaver instance.

    Creates the instance on first call and returns the same
    instance on subsequent calls.

    Returns:
        A MemorySaver instance for LangGraph checkpointing.
    """
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MemorySaver()
    return _checkpointer

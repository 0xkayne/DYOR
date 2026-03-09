"""LangGraph workflow orchestration for multi-agent collaboration."""


def __getattr__(name: str):
    """Lazy imports to avoid circular dependency with src.agents."""
    if name in ("build_workflow", "compile_workflow", "create_initial_state"):
        from src.graph.workflow import build_workflow, compile_workflow, create_initial_state

        _exports = {
            "build_workflow": build_workflow,
            "compile_workflow": compile_workflow,
            "create_initial_state": create_initial_state,
        }
        return _exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "build_workflow",
    "compile_workflow",
    "create_initial_state",
]

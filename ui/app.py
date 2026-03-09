"""Streamlit application main entry point."""

import streamlit as st

# Page config MUST be first Streamlit call
st.set_page_config(
    page_title="DYOR - Crypto Research Assistant",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Constants
COLOR_PALETTE = {
    "primary": "#6C63FF",
    "secondary": "#2EC4B6",
    "accent": "#FF6B6B",
    "bg_dark": "#0E1117",
    "bg_card": "#1E1E2E",
    "text": "#FAFAFA",
}

AGENT_DISPLAY_NAMES = {
    "router": "Router",
    "planner": "Planner",
    "rag": "RAG Retriever",
    "market": "Market Analyst",
    "news": "News Analyst",
    "tokenomics": "Tokenomics Analyst",
    "analyst": "Lead Analyst",
    "critic": "Critic",
}


def init_session_state() -> None:
    """Initialize all session state keys with default values if not already set."""
    defaults: dict = {
        "chat_history": [],
        "thread_id": None,
        "current_report": None,
        "compare_reports": [],
        "api_base_url": "http://localhost:8000",
        "is_streaming": False,
        "active_agents": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def api_call(method: str, endpoint: str, **kwargs) -> dict | None:
    """Standardized API call with user-friendly error handling.

    Args:
        method: HTTP method string (GET, POST, etc.).
        endpoint: API endpoint path, e.g. "/api/analyze".
        **kwargs: Additional arguments forwarded to httpx.Client.request().

    Returns:
        Parsed JSON response dict on success, or None on error.
    """
    import httpx

    url = f"{st.session_state.api_base_url}{endpoint}"
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        st.error(
            "Cannot connect to backend. Please start the API server: "
            "`uv run uvicorn api.main:app --reload`"
        )
        return None
    except httpx.TimeoutException:
        st.error("Request timed out. Please try again.")
        return None
    except httpx.HTTPStatusError as e:
        st.error(f"API error {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)[:200]}")
        return None


def render_sidebar() -> str:
    """Render sidebar navigation and settings panel.

    Returns:
        Selected page name as a string: "Chat", "Dashboard", or "Compare".
    """
    with st.sidebar:
        st.title("DYOR")
        st.caption("Crypto Research Assistant")
        st.divider()

        page = st.radio(
            "Navigation",
            ["Chat", "Dashboard", "Compare"],
            label_visibility="collapsed",
        )

        st.divider()

        with st.expander("Settings"):
            new_url = st.text_input(
                "API URL",
                value=st.session_state.api_base_url,
                help="Base URL of the DYOR backend API",
            )
            if new_url != st.session_state.api_base_url:
                st.session_state.api_base_url = new_url

            if st.button("New Conversation", use_container_width=True):
                st.session_state.chat_history = []
                st.session_state.thread_id = None
                st.session_state.current_report = None
                st.session_state.active_agents = {}
                st.rerun()

        if st.session_state.current_report:
            st.divider()
            st.subheader("Current Report")
            report = st.session_state.current_report
            project_name = report.get("project_name", "Unknown")
            workflow_type = report.get("workflow_type", "")
            st.write(f"**{project_name}**")
            if workflow_type:
                st.caption(workflow_type.replace("_", " ").title())

            recommendation = report.get("investment_recommendation") or {}
            rating = recommendation.get("rating", "")
            if rating:
                from ui.components.report_card import RATING_COLORS, RATING_LABELS
                color = RATING_COLORS.get(rating, "#888888")
                label = RATING_LABELS.get(rating, rating)
                st.markdown(
                    f'<span style="color:{color};font-weight:bold">{label}</span>',
                    unsafe_allow_html=True,
                )

        if st.session_state.compare_reports:
            st.divider()
            st.subheader("Comparison")
            for r in st.session_state.compare_reports:
                st.caption(r.get("project_name", "Unknown"))

    return page


def main() -> None:
    """Application entry point: initialize state, render sidebar, route to page."""
    init_session_state()
    page = render_sidebar()

    if page == "Chat":
        from ui.pages.chat import render_chat_page
        render_chat_page()
    elif page == "Dashboard":
        from ui.pages.dashboard import render_dashboard_page
        render_dashboard_page()
    elif page == "Compare":
        from ui.pages.compare import render_compare_page
        render_compare_page()


if __name__ == "__main__":
    main()

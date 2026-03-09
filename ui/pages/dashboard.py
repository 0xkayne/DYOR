"""Dashboard page for market overview and portfolio tracking."""

import streamlit as st


def render_dashboard_page() -> None:
    """Render the full dashboard: market overview + current project report."""
    st.header("Analysis Dashboard")

    _render_market_overview()
    st.divider()

    if st.session_state.current_report:
        _render_report_section()
    else:
        st.info(
            "No analysis report yet. Go to the **Chat** page and ask about a "
            "crypto project to generate one."
        )
        _render_getting_started()


def _render_getting_started() -> None:
    """Render a helpful getting-started guide when no report is available."""
    st.markdown("### Getting Started")
    st.markdown(
        """
        1. Navigate to the **Chat** tab in the sidebar.
        2. Type a query such as: *"Analyze Bitcoin"* or *"Do a deep dive on Ethereum"*.
        3. The AI agents will run a full analysis and generate a structured report.
        4. Return here to see the full dashboard with charts and metrics.
        """
    )
    with st.expander("Example Queries"):
        examples = [
            "Analyze the fundamentals of Solana",
            "What is the investment outlook for Chainlink?",
            "Give me a brief overview of Avalanche",
            "Deep dive into Uniswap tokenomics",
        ]
        for ex in examples:
            st.code(ex, language=None)


def _render_market_overview() -> None:
    """Fetch and display global market overview metrics and Fear & Greed gauge."""
    st.subheader("Market Overview")

    @st.cache_data(ttl=300)
    def fetch_overview(api_url: str) -> dict | None:
        """Fetch market overview from backend, cached for 5 minutes.

        Args:
            api_url: Base URL of the DYOR API.

        Returns:
            Dict with market overview data, or None on failure.
        """
        import httpx

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(f"{api_url}/api/market/overview")
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError:
            return None
        except httpx.HTTPStatusError:
            return None
        except Exception:
            return None

    data = fetch_overview(st.session_state.api_base_url)

    if data:
        metric_col1, metric_col2, gauge_col = st.columns([2, 2, 3])

        with metric_col1:
            total_cap = data.get("total_market_cap", 0) or 0
            if total_cap >= 1e12:
                cap_str = f"${total_cap / 1e12:.2f}T"
            elif total_cap >= 1e9:
                cap_str = f"${total_cap / 1e9:.1f}B"
            else:
                cap_str = f"${total_cap:,.0f}"
            st.metric("Total Market Cap", cap_str)

        with metric_col2:
            btc_dom = data.get("btc_dominance", 0) or 0
            st.metric("BTC Dominance", f"{btc_dom:.1f}%")

        with gauge_col:
            from ui.components.charts import create_fear_greed_gauge

            fgi = data.get("fear_greed_index", 50) or 50
            fig = create_fear_greed_gauge(int(fgi))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption(
            "Market overview unavailable — backend is not connected or the endpoint "
            "does not exist yet."
        )


def _render_report_section() -> None:
    """Render the current analysis report with an interactive price chart."""
    report = st.session_state.current_report
    project_name = report.get("project_name", "Unknown")

    st.subheader(f"{project_name} Analysis")

    # Time range selector for price chart
    days_options = {"7D": 7, "30D": 30, "90D": 90, "1Y": 365}
    range_col, _ = st.columns([2, 5])
    with range_col:
        selected = st.radio(
            "Time Range",
            list(days_options.keys()),
            horizontal=True,
            label_visibility="collapsed",
        )
    days = days_options[selected]

    coin_id = project_name.lower().replace(" ", "-")
    _render_price_chart(coin_id, days)

    st.divider()

    from ui.components.report_card import render_full_report

    render_full_report(report)


def _render_price_chart(coin_id: str, days: int) -> None:
    """Fetch price history and render a price chart for the given coin.

    Shows a loading spinner during the fetch. Falls back to a caption if
    data is unavailable.

    Args:
        coin_id: Coin identifier string, e.g. "bitcoin".
        days: Number of days of history to retrieve.
    """

    @st.cache_data(ttl=300)
    def fetch_prices(api_url: str, cid: str, d: int) -> dict | None:
        """Fetch price history from backend, cached for 5 minutes.

        Args:
            api_url: Base URL of the DYOR API.
            cid: Coin identifier.
            d: Number of days of history.

        Returns:
            Dict with dates and prices lists, or None on failure.
        """
        import httpx

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    f"{api_url}/api/market/price-history",
                    params={"coin_id": cid, "days": d},
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError:
            return None
        except httpx.HTTPStatusError:
            return None
        except Exception:
            return None

    with st.spinner(f"Loading {days}D price history for {coin_id}..."):
        data = fetch_prices(st.session_state.api_base_url, coin_id, days)

    if data and data.get("dates") and data.get("prices"):
        from ui.components.charts import create_price_chart

        fig = create_price_chart(
            data["dates"],
            data["prices"],
            coin_id,
            data.get("currency", "usd"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption(
            f"Price history for **{coin_id}** is unavailable. "
            "The backend may not be connected or the coin ID may not be recognized."
        )

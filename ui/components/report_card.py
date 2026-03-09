"""Report card component for displaying analysis summaries."""

import streamlit as st

from ui.components.charts import (
    create_market_metrics_bar,
    create_score_radar,
    create_score_radar_compare,
    create_sentiment_gauge,
    create_supply_donut,
    create_unlock_timeline,
)

RATING_COLORS = {
    "strong_buy": "#00C853",
    "buy": "#69F0AE",
    "hold": "#FFD740",
    "sell": "#FF8A65",
    "strong_sell": "#FF1744",
}

RATING_LABELS = {
    "strong_buy": "Strong Buy",
    "buy": "Buy",
    "hold": "Hold",
    "sell": "Sell",
    "strong_sell": "Strong Sell",
}


def _format_large_number(value: float) -> str:
    """Format large numbers as $1.23T, $456.7B, $12.3M, etc.

    Args:
        value: Numeric value to format.

    Returns:
        Formatted string with currency prefix and magnitude suffix.
    """
    if value >= 1e12:
        return f"${value / 1e12:.2f}T"
    elif value >= 1e9:
        return f"${value / 1e9:.1f}B"
    elif value >= 1e6:
        return f"${value / 1e6:.1f}M"
    elif value >= 1e3:
        return f"${value / 1e3:.1f}K"
    return f"${value:.2f}"


def _rating_pill_html(rating: str) -> str:
    """Return an HTML span styled as a colored rating pill.

    Args:
        rating: One of the rating keys in RATING_COLORS.

    Returns:
        HTML string for the styled pill badge.
    """
    color = RATING_COLORS.get(rating, "#888888")
    label = RATING_LABELS.get(rating, rating.replace("_", " ").title())
    return (
        f'<span style="background-color:{color};color:#000;padding:4px 12px;'
        f'border-radius:12px;font-weight:bold;font-size:0.9em;">{label}</span>'
    )


def _workflow_badge_html(workflow_type: str) -> str:
    """Return an HTML span for the workflow type badge.

    Args:
        workflow_type: One of deep_dive, compare, brief, qa.

    Returns:
        HTML string for the styled badge.
    """
    labels = {
        "deep_dive": "Deep Dive",
        "compare": "Compare",
        "brief": "Brief",
        "qa": "Q&A",
    }
    colors = {
        "deep_dive": "#6C63FF",
        "compare": "#2EC4B6",
        "brief": "#FFD740",
        "qa": "#FF6B6B",
    }
    label = labels.get(workflow_type, workflow_type.replace("_", " ").title())
    color = colors.get(workflow_type, "#888888")
    return (
        f'<span style="background-color:{color}33;border:1px solid {color};'
        f'color:{color};padding:2px 8px;border-radius:8px;font-size:0.8em;">{label}</span>'
    )


def render_report_header(report: dict) -> None:
    """Render project name, analysis date, workflow badge, and rating pill.

    Args:
        report: AnalysisReport dict with project_name, analysis_date,
            workflow_type, and investment_recommendation fields.
    """
    project_name = report.get("project_name", "Unknown Project")
    analysis_date = report.get("analysis_date", "")
    workflow_type = report.get("workflow_type", "")
    recommendation = report.get("investment_recommendation") or {}
    rating = recommendation.get("rating", "")

    # Format the date if it exists
    if analysis_date:
        try:
            from datetime import datetime
            if isinstance(analysis_date, str):
                dt = datetime.fromisoformat(analysis_date.replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d %H:%M UTC")
            else:
                date_str = str(analysis_date)
        except Exception:
            date_str = str(analysis_date)[:10]
    else:
        date_str = ""

    col_name, col_meta, col_rating = st.columns([3, 2, 2])

    with col_name:
        st.markdown(f"## {project_name}")
        if date_str:
            st.caption(f"Analyzed: {date_str}")

    with col_meta:
        if workflow_type:
            st.markdown(_workflow_badge_html(workflow_type), unsafe_allow_html=True)

    with col_rating:
        if rating:
            st.markdown(_rating_pill_html(rating), unsafe_allow_html=True)


def render_recommendation_card(recommendation: dict) -> None:
    """Render a colored rating, confidence bar, reasons list, and risk list.

    Args:
        recommendation: InvestmentRecommendation dict with rating, confidence,
            key_reasons, risk_factors, and disclaimer fields.
    """
    if not recommendation:
        st.info("No investment recommendation available.")
        return

    rating = recommendation.get("rating", "hold")
    confidence = recommendation.get("confidence", 0.0)
    key_reasons = recommendation.get("key_reasons", [])
    risk_factors = recommendation.get("risk_factors", [])
    disclaimer = recommendation.get(
        "disclaimer",
        "This is not financial advice. Always do your own research.",
    )

    color = RATING_COLORS.get(rating, "#888888")
    label = RATING_LABELS.get(rating, rating.replace("_", " ").title())

    st.markdown(
        f'<div style="border-left:4px solid {color};padding:12px 16px;'
        f'background:rgba(30,30,46,0.8);border-radius:0 8px 8px 0;margin-bottom:12px;">'
        f'<span style="font-size:1.4em;font-weight:bold;color:{color}">{label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    conf_col, _ = st.columns([2, 3])
    with conf_col:
        st.caption(f"Confidence: {confidence * 100:.0f}%")
        st.progress(confidence)

    if key_reasons:
        st.markdown("**Key Reasons**")
        for reason in key_reasons:
            st.markdown(f"- {reason}")

    if risk_factors:
        st.markdown("**Risk Factors**")
        for risk in risk_factors:
            st.markdown(f"- :red[{risk}]")

    st.caption(f"_{disclaimer}_")


def render_fundamental_card(fundamental: dict, project_name: str = "") -> None:
    """Render radar chart, 4 score metrics, and fundamental summary.

    Args:
        fundamental: FundamentalAnalysis dict with team_score, product_score,
            track_score, tokenomics_score, summary, and sources fields.
        project_name: Used as the legend label in the radar chart.
    """
    if not fundamental:
        st.info("No fundamental analysis data available.")
        return

    team_score = fundamental.get("team_score", 0)
    product_score = fundamental.get("product_score", 0)
    track_score = fundamental.get("track_score", 0)
    tokenomics_score = fundamental.get("tokenomics_score", 0)
    summary = fundamental.get("summary", "")
    sources = fundamental.get("sources", [])

    chart_col, scores_col = st.columns([2, 3])

    with chart_col:
        fig = create_score_radar(team_score, product_score, track_score, tokenomics_score, project_name)
        st.plotly_chart(fig, use_container_width=True)

    with scores_col:
        s1, s2 = st.columns(2)
        s3, s4 = st.columns(2)
        with s1:
            st.metric("Team", f"{team_score:.1f}/10")
        with s2:
            st.metric("Product", f"{product_score:.1f}/10")
        with s3:
            st.metric("Track Record", f"{track_score:.1f}/10")
        with s4:
            st.metric("Tokenomics", f"{tokenomics_score:.1f}/10")

        if summary:
            st.markdown("**Summary**")
            st.write(summary)

    if sources:
        with st.expander(f"Sources ({len(sources)})"):
            for i, src in enumerate(sources, 1):
                st.caption(f"{i}. {src}")


def render_market_card(market_data: dict) -> None:
    """Render 4 metric columns: price, 24h change, 7d change, volume.

    Args:
        market_data: MarketData dict with current_price, price_change_24h,
            price_change_7d, market_cap, volume_24h, and technical_indicators.
    """
    if not market_data:
        st.info("No market data available.")
        return

    current_price = market_data.get("current_price", 0)
    change_24h = market_data.get("price_change_24h", 0) or 0
    change_7d = market_data.get("price_change_7d", 0) or 0
    market_cap = market_data.get("market_cap", 0) or 0
    volume_24h = market_data.get("volume_24h", 0) or 0

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        price_str = f"${current_price:,.4f}" if current_price < 1 else f"${current_price:,.2f}"
        st.metric("Current Price", price_str)

    with c2:
        delta_color = "normal"
        st.metric("24H Change", f"{change_24h:+.2f}%", delta=f"{change_24h:+.2f}%")

    with c3:
        st.metric("7D Change", f"{change_7d:+.2f}%", delta=f"{change_7d:+.2f}%")

    with c4:
        st.metric("24H Volume", _format_large_number(volume_24h))

    # Market cap row
    cap_col, _ = st.columns([1, 2])
    with cap_col:
        st.metric("Market Cap", _format_large_number(market_cap))

    # Technical indicators
    tech = market_data.get("technical_indicators") or {}
    if tech:
        with st.expander("Technical Indicators"):
            ti_cols = st.columns(min(len(tech), 4))
            for i, (key, val) in enumerate(tech.items()):
                with ti_cols[i % len(ti_cols)]:
                    label = key.replace("_", " ").upper()
                    if isinstance(val, float):
                        st.metric(label, f"{val:.2f}")
                    else:
                        st.metric(label, str(val))


def render_news_card(news_sentiment: dict) -> None:
    """Render sentiment gauge and a list of news items with color-coded dots.

    Args:
        news_sentiment: NewsSentiment dict with overall_sentiment, sentiment_score,
            and key_events list.
    """
    if not news_sentiment:
        st.info("No news sentiment data available.")
        return

    overall_sentiment = news_sentiment.get("overall_sentiment", "neutral")
    sentiment_score = news_sentiment.get("sentiment_score", 0.0) or 0.0
    key_events = news_sentiment.get("key_events", []) or []

    gauge_col, news_col = st.columns([1, 2])

    with gauge_col:
        fig = create_sentiment_gauge(sentiment_score, overall_sentiment)
        st.plotly_chart(fig, use_container_width=True)

    with news_col:
        if key_events:
            st.markdown("**Key News Events**")
            sentiment_dots = {
                "positive": ":green_circle:",
                "neutral": ":yellow_circle:",
                "negative": ":red_circle:",
            }
            for item in key_events:
                item_sentiment = item.get("sentiment", "neutral") if isinstance(item, dict) else "neutral"
                title = item.get("title", "Untitled") if isinstance(item, dict) else str(item)
                source = item.get("source", "") if isinstance(item, dict) else ""
                url = item.get("url", "") if isinstance(item, dict) else ""
                summary = item.get("summary", "") if isinstance(item, dict) else ""
                published_at = item.get("published_at", "") if isinstance(item, dict) else ""

                dot = sentiment_dots.get(item_sentiment, ":white_circle:")

                if url:
                    title_md = f"[{title}]({url})"
                else:
                    title_md = title

                source_str = f" — *{source}*" if source else ""
                date_str = f" ({str(published_at)[:10]})" if published_at else ""

                st.markdown(f"{dot} {title_md}{source_str}{date_str}")
                if summary:
                    st.caption(f"  {summary}")
        else:
            st.caption("No individual news items available.")


def render_tokenomics_card(tokenomics: dict) -> None:
    """Render supply donut, unlock timeline, and next unlock alert.

    Args:
        tokenomics: TokenomicsData dict with next_unlock, circulating_supply_ratio,
            top_holders_concentration, and unlock_schedule fields.
    """
    if not tokenomics:
        st.info("No tokenomics data available.")
        return

    next_unlock = tokenomics.get("next_unlock")
    circulating_supply_ratio = tokenomics.get("circulating_supply_ratio", 0.5) or 0.5
    top_holders_concentration = tokenomics.get("top_holders_concentration", 0.0) or 0.0
    unlock_schedule = tokenomics.get("unlock_schedule", []) or []

    # Next unlock warning
    if next_unlock:
        unlock_date = next_unlock.get("date", "")
        unlock_amount = next_unlock.get("amount", 0)
        unlock_pct = next_unlock.get("percentage", 0)
        token_name = next_unlock.get("token_name", "tokens")
        category = next_unlock.get("category", "")
        date_str = str(unlock_date)[:10] if unlock_date else "upcoming"
        st.warning(
            f"**Next Unlock:** {unlock_pct:.2f}% of supply ({unlock_amount:,.0f} {token_name}) "
            f"from *{category}* category on **{date_str}**"
        )

    # Metrics row
    m1, m2 = st.columns(2)
    with m1:
        st.metric("Circulating Supply", f"{circulating_supply_ratio * 100:.1f}%")
    with m2:
        st.metric("Top Holders Concentration", f"{top_holders_concentration * 100:.1f}%")

    # Charts
    donut_col, timeline_col = st.columns([1, 2])

    with donut_col:
        fig_donut = create_supply_donut(circulating_supply_ratio)
        st.plotly_chart(fig_donut, use_container_width=True)

    with timeline_col:
        if unlock_schedule:
            fig_timeline = create_unlock_timeline(unlock_schedule)
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.caption("No unlock schedule data available.")


def render_full_report(report: dict) -> None:
    """Render complete analysis report in a tabbed layout.

    Tabs: Overview | Market | News | Tokenomics. Each tab gracefully
    handles missing data by showing an informational message.

    Args:
        report: AnalysisReport dict with all analysis fields.
    """
    if not report:
        st.warning("No report data to display.")
        return

    render_report_header(report)
    st.divider()

    tab_overview, tab_market, tab_news, tab_tokenomics = st.tabs(
        ["Overview", "Market", "News", "Tokenomics"]
    )

    with tab_overview:
        recommendation = report.get("investment_recommendation")
        fundamental = report.get("fundamental_analysis")

        if recommendation:
            st.subheader("Investment Recommendation")
            render_recommendation_card(recommendation)
            st.divider()
        else:
            st.info("No investment recommendation in this report.")

        if fundamental:
            st.subheader("Fundamental Analysis")
            render_fundamental_card(fundamental, project_name=report.get("project_name", ""))
        else:
            st.info("No fundamental analysis in this report.")

    with tab_market:
        market_data = report.get("market_data")
        if market_data:
            st.subheader("Market Data")
            render_market_card(market_data)
            st.divider()
            st.subheader("Price Performance")
            fig = create_market_metrics_bar(market_data)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No market data in this report.")

    with tab_news:
        news_sentiment = report.get("news_sentiment")
        if news_sentiment:
            st.subheader("News Sentiment")
            render_news_card(news_sentiment)
        else:
            st.info("No news sentiment data in this report.")

    with tab_tokenomics:
        tokenomics = report.get("tokenomics")
        if tokenomics:
            st.subheader("Tokenomics")
            render_tokenomics_card(tokenomics)
        else:
            st.info("No tokenomics data in this report.")


def render_compare_table(reports: list[dict]) -> None:
    """Render side-by-side comparison columns, one per project.

    Displays: project name, rating pill, 4 fundamental scores, confidence.

    Args:
        reports: List of AnalysisReport dicts to compare.
    """
    if not reports:
        st.info("No reports to compare.")
        return

    st.subheader("Detailed Comparison")
    cols = st.columns(len(reports))

    for i, (col, report) in enumerate(zip(cols, reports)):
        with col:
            project_name = report.get("project_name", f"Project {i+1}")
            recommendation = report.get("investment_recommendation") or {}
            fundamental = report.get("fundamental_analysis") or {}
            rating = recommendation.get("rating", "")
            confidence = recommendation.get("confidence", 0.0)

            st.markdown(f"### {project_name}")

            if rating:
                st.markdown(_rating_pill_html(rating), unsafe_allow_html=True)
                st.write("")  # spacing

            if fundamental:
                team_score = fundamental.get("team_score", 0)
                product_score = fundamental.get("product_score", 0)
                track_score = fundamental.get("track_score", 0)
                tokenomics_score = fundamental.get("tokenomics_score", 0)

                st.metric("Team", f"{team_score:.1f}/10")
                st.metric("Product", f"{product_score:.1f}/10")
                st.metric("Track Record", f"{track_score:.1f}/10")
                st.metric("Tokenomics", f"{tokenomics_score:.1f}/10")

                avg = (team_score + product_score + track_score + tokenomics_score) / 4
                st.metric("Average Score", f"{avg:.1f}/10")
            else:
                st.caption("No fundamental scores available.")

            if confidence:
                st.caption(f"Confidence: {confidence * 100:.0f}%")
                st.progress(confidence)

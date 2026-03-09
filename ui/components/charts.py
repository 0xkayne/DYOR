"""Chart components for price history and market data visualization."""

import plotly.graph_objects as go

CHART_TEMPLATE = "plotly_dark"
CHART_BG = "rgba(0,0,0,0)"
CHART_HEIGHT = 350
CHART_MARGIN = dict(l=20, r=20, t=40, b=20)


def _base_layout(**kwargs) -> dict:
    """Return a base layout dict with dark theme and transparent background."""
    layout = dict(
        template=CHART_TEMPLATE,
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        height=CHART_HEIGHT,
        margin=CHART_MARGIN,
        font=dict(color="#FAFAFA"),
    )
    layout.update(kwargs)
    return layout


def create_price_chart(
    dates: list[str],
    prices: list[float],
    coin_id: str = "",
    currency: str = "USD",
) -> go.Figure:
    """Line chart with area fill for price history.

    Args:
        dates: List of date strings for the x-axis.
        prices: List of price values for the y-axis.
        coin_id: Coin identifier used in the chart title.
        currency: Currency label shown in the title.

    Returns:
        Plotly Figure with line + area fill.
    """
    title = f"{coin_id.title()} Price ({currency.upper()})" if coin_id else f"Price ({currency.upper()})"

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=prices,
            mode="lines",
            name="Price",
            line=dict(color="#6C63FF", width=2),
            fill="tozeroy",
            fillcolor="rgba(108, 99, 255, 0.1)",
            hovertemplate="%{x}<br>%{y:,.4f} " + currency.upper() + "<extra></extra>",
        )
    )

    # Add 20-period moving average if enough data
    if len(prices) >= 20:
        ma20 = []
        for i in range(len(prices)):
            if i < 19:
                ma20.append(None)
            else:
                ma20.append(sum(prices[i - 19 : i + 1]) / 20)

        fig.add_trace(
            go.Scatter(
                x=dates,
                y=ma20,
                mode="lines",
                name="MA20",
                line=dict(color="#2EC4B6", width=1, dash="dash"),
                hovertemplate="%{x}<br>MA20: %{y:,.4f}<extra></extra>",
            )
        )

    fig.update_layout(
        **_base_layout(
            title=dict(text=title, x=0.01, font=dict(size=14)),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title=currency.upper()),
            legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
            hovermode="x unified",
        )
    )

    return fig


def create_score_radar(
    team_score: float,
    product_score: float,
    track_score: float,
    tokenomics_score: float,
    project_name: str = "",
) -> go.Figure:
    """Spider/radar chart for fundamental scores, range [0, 10].

    Args:
        team_score: Team quality score (1-10).
        product_score: Product maturity score (1-10).
        track_score: Track/sector score (1-10).
        tokenomics_score: Tokenomics design score (1-10).
        project_name: Project name used in the trace label.

    Returns:
        Plotly Figure with filled radar/spider chart.
    """
    categories = ["Team", "Product", "Track Record", "Tokenomics"]
    values = [team_score, product_score, track_score, tokenomics_score]
    # Close the polygon
    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            fill="toself",
            fillcolor="rgba(108, 99, 255, 0.2)",
            line=dict(color="#6C63FF", width=2),
            name=project_name or "Scores",
            hovertemplate="%{theta}: %{r:.1f}/10<extra></extra>",
        )
    )

    fig.update_layout(
        **_base_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 10],
                    tickmode="array",
                    tickvals=[2, 4, 6, 8, 10],
                    ticktext=["2", "4", "6", "8", "10"],
                    gridcolor="rgba(255,255,255,0.1)",
                    linecolor="rgba(255,255,255,0.1)",
                ),
                angularaxis=dict(
                    gridcolor="rgba(255,255,255,0.1)",
                    linecolor="rgba(255,255,255,0.1)",
                ),
                bgcolor=CHART_BG,
            ),
            showlegend=bool(project_name),
            height=320,
        )
    )

    return fig


def create_score_radar_compare(projects: list[dict]) -> go.Figure:
    """Overlaid radar for multiple projects.

    Args:
        projects: List of dicts, each with keys: name, team_score,
            product_score, track_score, tokenomics_score.

    Returns:
        Plotly Figure with one radar trace per project.
    """
    colors = ["#6C63FF", "#2EC4B6", "#FF6B6B", "#FFD740", "#69F0AE"]
    categories = ["Team", "Product", "Track Record", "Tokenomics"]
    categories_closed = categories + [categories[0]]

    fig = go.Figure()

    for i, project in enumerate(projects):
        color = colors[i % len(colors)]
        values = [
            project.get("team_score", 0),
            project.get("product_score", 0),
            project.get("track_score", 0),
            project.get("tokenomics_score", 0),
        ]
        values_closed = values + [values[0]]

        fig.add_trace(
            go.Scatterpolar(
                r=values_closed,
                theta=categories_closed,
                fill="toself",
                fillcolor=f"rgba{tuple(int(color.lstrip('#')[j:j+2], 16) for j in (0, 2, 4)) + (0.15,)}",
                line=dict(color=color, width=2),
                name=project.get("name", f"Project {i+1}"),
                hovertemplate="%{theta}: %{r:.1f}/10<extra></extra>",
            )
        )

    fig.update_layout(
        **_base_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 10],
                    tickmode="array",
                    tickvals=[2, 4, 6, 8, 10],
                    ticktext=["2", "4", "6", "8", "10"],
                    gridcolor="rgba(255,255,255,0.1)",
                    linecolor="rgba(255,255,255,0.1)",
                ),
                angularaxis=dict(
                    gridcolor="rgba(255,255,255,0.1)",
                    linecolor="rgba(255,255,255,0.1)",
                ),
                bgcolor=CHART_BG,
            ),
            showlegend=True,
            legend=dict(orientation="h", y=-0.1),
            height=380,
            title=dict(text="Fundamental Score Comparison", x=0.01, font=dict(size=14)),
        )
    )

    return fig


def create_sentiment_gauge(sentiment_score: float, overall_sentiment: str = "") -> go.Figure:
    """Gauge chart for sentiment, range [-1, 1].

    Args:
        sentiment_score: Aggregated sentiment score from -1 (very negative) to 1 (very positive).
        overall_sentiment: Text label for the overall sentiment category.

    Returns:
        Plotly Figure with gauge indicator.
    """
    # Map -1..1 to 0..100 for display
    display_value = (sentiment_score + 1) * 50

    label = overall_sentiment.title() if overall_sentiment else (
        "Positive" if sentiment_score > 0.3 else
        "Negative" if sentiment_score < -0.3 else
        "Neutral"
    )

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=sentiment_score,
            number=dict(suffix="", valueformat=".2f", font=dict(size=24, color="#FAFAFA")),
            title=dict(text=f"News Sentiment<br><span style='font-size:14px'>{label}</span>", font=dict(color="#FAFAFA")),
            gauge=dict(
                axis=dict(
                    range=[-1, 1],
                    tickvals=[-1, -0.5, 0, 0.5, 1],
                    ticktext=["-1", "-0.5", "0", "0.5", "1"],
                    tickcolor="#FAFAFA",
                ),
                bar=dict(color="#6C63FF", thickness=0.3),
                bgcolor=CHART_BG,
                bordercolor="rgba(255,255,255,0.1)",
                steps=[
                    dict(range=[-1, -0.3], color="rgba(255, 71, 68, 0.3)"),
                    dict(range=[-0.3, 0.3], color="rgba(255, 215, 64, 0.3)"),
                    dict(range=[0.3, 1], color="rgba(0, 200, 83, 0.3)"),
                ],
                threshold=dict(
                    line=dict(color="white", width=2),
                    thickness=0.75,
                    value=sentiment_score,
                ),
            ),
        )
    )

    fig.update_layout(
        **_base_layout(height=280)
    )

    return fig


def create_fear_greed_gauge(value: int) -> go.Figure:
    """Fear and Greed gauge [0, 100] with color zones.

    Args:
        value: Fear and Greed Index value from 0 (Extreme Fear) to 100 (Extreme Greed).

    Returns:
        Plotly Figure with a gauge indicator.
    """
    if value <= 25:
        label = "Extreme Fear"
    elif value <= 45:
        label = "Fear"
    elif value <= 55:
        label = "Neutral"
    elif value <= 75:
        label = "Greed"
    else:
        label = "Extreme Greed"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number=dict(font=dict(size=22, color="#FAFAFA")),
            title=dict(
                text=f"Fear & Greed<br><span style='font-size:13px'>{label}</span>",
                font=dict(color="#FAFAFA", size=13),
            ),
            gauge=dict(
                axis=dict(
                    range=[0, 100],
                    tickvals=[0, 25, 45, 55, 75, 100],
                    ticktext=["0", "25", "45", "55", "75", "100"],
                    tickcolor="#FAFAFA",
                    tickfont=dict(size=9),
                ),
                bar=dict(color="#6C63FF", thickness=0.3),
                bgcolor=CHART_BG,
                bordercolor="rgba(255,255,255,0.1)",
                steps=[
                    dict(range=[0, 25], color="rgba(255, 71, 68, 0.4)"),
                    dict(range=[25, 45], color="rgba(255, 138, 101, 0.4)"),
                    dict(range=[45, 55], color="rgba(255, 215, 64, 0.4)"),
                    dict(range=[55, 75], color="rgba(144, 238, 144, 0.4)"),
                    dict(range=[75, 100], color="rgba(0, 200, 83, 0.4)"),
                ],
            ),
        )
    )

    fig.update_layout(
        **_base_layout(height=220, margin=dict(l=10, r=10, t=30, b=10))
    )

    return fig


def create_unlock_timeline(unlock_schedule: list[dict]) -> go.Figure:
    """Bar chart for token unlock schedule.

    Args:
        unlock_schedule: List of dicts, each with keys: date, amount,
            percentage, category (and optionally token_name).

    Returns:
        Plotly Figure with grouped bar chart by category.
    """
    if not unlock_schedule:
        fig = go.Figure()
        fig.update_layout(
            **_base_layout(
                title=dict(text="Token Unlock Schedule", x=0.01, font=dict(size=14)),
                annotations=[dict(text="No unlock data available", x=0.5, y=0.5, showarrow=False, font=dict(color="#FAFAFA"))],
            )
        )
        return fig

    # Group by category for coloring
    categories = list({e.get("category", "Unknown") for e in unlock_schedule})
    colors = ["#6C63FF", "#2EC4B6", "#FF6B6B", "#FFD740", "#69F0AE", "#FF8A65"]
    color_map = {cat: colors[i % len(colors)] for i, cat in enumerate(categories)}

    fig = go.Figure()

    for category in categories:
        events = [e for e in unlock_schedule if e.get("category", "Unknown") == category]
        dates = [e.get("date", "") for e in events]
        # Normalize date strings (strip time component if present)
        dates = [str(d)[:10] if d else "" for d in dates]
        amounts = [e.get("percentage", 0) for e in events]
        raw_amounts = [e.get("amount", 0) for e in events]

        fig.add_trace(
            go.Bar(
                x=dates,
                y=amounts,
                name=category,
                marker_color=color_map[category],
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    + category
                    + "<br>%{y:.2f}% of supply<br>"
                    + "Amount: %{customdata:,.0f}<extra></extra>"
                ),
                customdata=raw_amounts,
            )
        )

    fig.update_layout(
        **_base_layout(
            title=dict(text="Token Unlock Schedule", x=0.01, font=dict(size=14)),
            barmode="stack",
            xaxis=dict(title="Date", showgrid=False),
            yaxis=dict(title="% of Supply", showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
            legend=dict(orientation="h", y=1.05),
        )
    )

    return fig


def create_supply_donut(circulating_supply_ratio: float) -> go.Figure:
    """Donut chart showing circulating vs locked supply.

    Args:
        circulating_supply_ratio: Float from 0 to 1 representing the fraction
            of total supply currently in circulation.

    Returns:
        Plotly Figure with a donut pie chart.
    """
    circulating_pct = circulating_supply_ratio * 100
    locked_pct = 100 - circulating_pct

    fig = go.Figure(
        go.Pie(
            labels=["Circulating", "Locked"],
            values=[circulating_pct, locked_pct],
            hole=0.6,
            marker=dict(colors=["#6C63FF", "#2EC4B6"]),
            textinfo="label+percent",
            textfont=dict(color="#FAFAFA"),
            hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        **_base_layout(
            title=dict(text="Supply Distribution", x=0.01, font=dict(size=14)),
            showlegend=False,
            height=300,
            annotations=[
                dict(
                    text=f"{circulating_pct:.0f}%<br>Circulating",
                    x=0.5,
                    y=0.5,
                    font_size=13,
                    font_color="#FAFAFA",
                    showarrow=False,
                )
            ],
        )
    )

    return fig


def create_market_metrics_bar(market_data: dict) -> go.Figure:
    """Horizontal bar chart for 24h and 7d price changes.

    Args:
        market_data: Dict containing price_change_24h and price_change_7d fields.

    Returns:
        Plotly Figure with two horizontal bars colored by positive/negative.
    """
    change_24h = market_data.get("price_change_24h", 0) or 0
    change_7d = market_data.get("price_change_7d", 0) or 0

    labels = ["7D Change", "24H Change"]
    values = [change_7d, change_24h]
    colors = ["#00C853" if v >= 0 else "#FF1744" for v in values]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(color=colors),
            text=[f"{v:+.2f}%" for v in values],
            textposition="outside",
            textfont=dict(color="#FAFAFA"),
            hovertemplate="%{y}: %{x:+.2f}%<extra></extra>",
        )
    )

    fig.update_layout(
        **_base_layout(
            title=dict(text="Price Performance", x=0.01, font=dict(size=14)),
            xaxis=dict(
                title="Change (%)",
                showgrid=True,
                gridcolor="rgba(255,255,255,0.05)",
                zeroline=True,
                zerolinecolor="rgba(255,255,255,0.3)",
            ),
            yaxis=dict(showgrid=False),
            height=200,
            margin=dict(l=20, r=60, t=40, b=20),
        )
    )

    return fig

"""Comparison page for side-by-side project analysis."""

import streamlit as st


def render_compare_page() -> None:
    """Render the project comparison page with input fields, results, and charts."""
    st.header("Project Comparison")
    st.caption("Compare the fundamentals of two or three crypto projects side by side.")

    cols = st.columns(3)
    with cols[0]:
        project1 = st.text_input("Project 1", placeholder="e.g. Bitcoin")
    with cols[1]:
        project2 = st.text_input("Project 2", placeholder="e.g. Ethereum")
    with cols[2]:
        project3 = st.text_input("Project 3 (optional)", placeholder="e.g. Solana")

    projects = [p.strip() for p in [project1, project2, project3] if p.strip()]

    button_col, clear_col, _ = st.columns([2, 2, 5])
    with button_col:
        run_compare = st.button(
            "Compare",
            disabled=len(projects) < 2,
            type="primary",
            use_container_width=True,
        )
    with clear_col:
        if st.button("Clear Results", use_container_width=True):
            st.session_state.compare_reports = []
            st.rerun()

    if run_compare and len(projects) >= 2:
        _run_comparison(projects)

    if st.session_state.compare_reports:
        _render_comparison_results()
    elif not run_compare:
        _render_comparison_guide()


def _render_comparison_guide() -> None:
    """Render a brief guide on how to use the comparison feature."""
    st.info(
        "Enter at least two project names above and click **Compare** to start. "
        "Each project will be analyzed independently, then compared side by side."
    )
    st.markdown("**Tips:**")
    st.markdown(
        """
        - Use common names: *Bitcoin*, *Ethereum*, *Solana*, *Chainlink*, etc.
        - The comparison uses a lightweight *compare* workflow for speed.
        - You can use the result to quickly assess relative strengths and risks.
        """
    )


def _run_comparison(projects: list[str]) -> None:
    """Trigger analysis for each project and store results in session state.

    Sends a POST to /api/analyze for each project sequentially. Updates a
    progress bar during execution and shows warnings for failed analyses.

    Args:
        projects: List of project name strings to analyze.
    """
    from ui.app import api_call

    reports: list[dict] = []
    progress = st.progress(0, text="Starting comparison analysis...")

    for i, project in enumerate(projects):
        progress.progress(
            i / len(projects),
            text=f"Analyzing {project} ({i + 1}/{len(projects)})...",
        )

        with st.spinner(f"Fetching analysis for {project}..."):
            result = api_call(
                "POST",
                "/api/analyze",
                json={
                    "project_name": project,
                    "workflow_type": "compare",
                },
            )

        if result:
            reports.append(result)
        else:
            st.warning(
                f"Could not retrieve analysis for **{project}**. "
                "It will be excluded from the comparison."
            )

    progress.progress(1.0, text="Analysis complete!")

    if len(reports) >= 2:
        st.session_state.compare_reports = reports
        st.success(f"Successfully compared {len(reports)} projects.")
        st.rerun()
    elif len(reports) == 1:
        st.error(
            "Only one project was analyzed successfully. "
            "A comparison requires at least two projects."
        )
    else:
        st.error(
            "No projects could be analyzed. "
            "Please check that the backend is running and the project names are valid."
        )


def _render_comparison_results() -> None:
    """Render comparison results: overlaid radar chart + side-by-side columns."""
    reports = st.session_state.compare_reports

    if not reports:
        return

    project_names = [r.get("project_name", "Unknown") for r in reports]
    st.subheader(f"Comparing: {' vs '.join(project_names)}")
    st.divider()

    # Build radar data for projects that have fundamental analysis
    radar_data = []
    for r in reports:
        fa = r.get("fundamental_analysis")
        if fa:
            radar_data.append(
                {
                    "name": r.get("project_name", "Unknown"),
                    "team_score": fa.get("team_score", 0),
                    "product_score": fa.get("product_score", 0),
                    "track_score": fa.get("track_score", 0),
                    "tokenomics_score": fa.get("tokenomics_score", 0),
                }
            )

    if radar_data:
        from ui.components.charts import create_score_radar_compare

        fig = create_score_radar_compare(radar_data)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(
            "No fundamental analysis data available for radar chart comparison. "
            "Showing text comparison only."
        )

    st.divider()

    # Comparison table
    from ui.components.report_card import render_compare_table

    render_compare_table(reports)

    # Expandable full reports per project
    st.divider()
    st.subheader("Full Reports")

    tabs = st.tabs(project_names)
    for tab, report in zip(tabs, reports):
        with tab:
            from ui.components.report_card import render_full_report

            render_full_report(report)

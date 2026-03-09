"""Tests for the router agent that classifies user intent."""

from __future__ import annotations

import pytest


class TestRouterImport:
    def test_module_importable(self):
        """Verify that the router module can be imported."""
        from src.agents import router  # noqa: F401


class TestIntentClassification:
    @pytest.mark.skip(reason="stub: router agent not yet implemented")
    def test_deep_dive_intent(self):
        """Should classify '深度分析 Arbitrum' as deep_dive."""
        pass

    @pytest.mark.skip(reason="stub: router agent not yet implemented")
    def test_compare_intent(self):
        """Should classify 'ARB vs OP 对比' as compare."""
        pass

    @pytest.mark.skip(reason="stub: router agent not yet implemented")
    def test_qa_intent(self):
        """Should classify 'Arbitrum 团队是谁' as qa."""
        pass

    @pytest.mark.skip(reason="stub: router agent not yet implemented")
    def test_news_watch_intent(self):
        """Should classify 'ARB 最新新闻' as news_watch."""
        pass


class TestEntityExtraction:
    @pytest.mark.skip(reason="stub: router agent not yet implemented")
    def test_extract_project_name(self):
        """Should extract 'Arbitrum' from '分析一下 Arbitrum 项目'."""
        pass

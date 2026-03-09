"""Tests for user preferences storage."""

from __future__ import annotations

from pathlib import Path

from src.memory.user_preferences import PreferenceStore, UserPreferences


class TestUserPreferencesModel:
    def test_defaults(self):
        prefs = UserPreferences()
        assert prefs.risk_tolerance == "moderate"
        assert prefs.watchlist == []
        assert prefs.preferred_language == "zh"

    def test_custom_values(self):
        prefs = UserPreferences(risk_tolerance="aggressive", watchlist=["BTC", "ETH"], preferred_language="en")
        assert prefs.risk_tolerance == "aggressive"
        assert len(prefs.watchlist) == 2


class TestPreferenceStore:
    def test_get_default_prefs(self, tmp_path: Path):
        store = PreferenceStore(path=tmp_path / "prefs.json")
        prefs = store.get("user1")
        assert prefs.risk_tolerance == "moderate"

    def test_set_and_get(self, tmp_path: Path):
        store = PreferenceStore(path=tmp_path / "prefs.json")
        new_prefs = UserPreferences(risk_tolerance="aggressive", watchlist=["BTC"])
        store.set("user1", new_prefs)
        loaded = store.get("user1")
        assert loaded.risk_tolerance == "aggressive"
        assert loaded.watchlist == ["BTC"]

    def test_partial_update(self, tmp_path: Path):
        store = PreferenceStore(path=tmp_path / "prefs.json")
        store.set("user1", UserPreferences())
        updated = store.update("user1", risk_tolerance="conservative")
        assert updated.risk_tolerance == "conservative"
        assert updated.preferred_language == "zh"  # unchanged

    def test_corrupted_file_returns_default(self, tmp_path: Path):
        prefs_path = tmp_path / "prefs.json"
        prefs_path.write_text("not json!!!", encoding="utf-8")
        store = PreferenceStore(path=prefs_path)
        prefs = store.get("user1")
        assert prefs.risk_tolerance == "moderate"

    def test_update_unknown_field_ignored(self, tmp_path: Path):
        store = PreferenceStore(path=tmp_path / "prefs.json")
        store.set("user1", UserPreferences())
        updated = store.update("user1", nonexistent_field="value")
        assert not hasattr(updated, "nonexistent_field")

    def test_multiple_users(self, tmp_path: Path):
        store = PreferenceStore(path=tmp_path / "prefs.json")
        store.set("user1", UserPreferences(risk_tolerance="conservative"))
        store.set("user2", UserPreferences(risk_tolerance="aggressive"))
        assert store.get("user1").risk_tolerance == "conservative"
        assert store.get("user2").risk_tolerance == "aggressive"

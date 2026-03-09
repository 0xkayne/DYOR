"""User preference storage and retrieval for personalized analysis.

Stores user preferences (risk tolerance, watchlist, language) in a
JSON file for persistence across sessions.
"""

import json
from pathlib import Path
from typing import Literal

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

DEFAULT_PREFS_PATH = Path("data/user_preferences.json")


class UserPreferences(BaseModel):
    """User preference model for personalized analysis output.

    Attributes:
        risk_tolerance: User's risk appetite level.
        watchlist: List of project names the user is tracking.
        preferred_language: Preferred output language code.
    """

    risk_tolerance: Literal["conservative", "moderate", "aggressive"] = Field(
        default="moderate",
        description="User's risk appetite: conservative, moderate, or aggressive",
    )
    watchlist: list[str] = Field(
        default_factory=list,
        description="List of project names the user is tracking",
    )
    preferred_language: str = Field(
        default="zh",
        description="Preferred language for analysis output (e.g. 'zh', 'en')",
    )


class PreferenceStore:
    """JSON file-based storage for user preferences.

    Each user is identified by a string user_id. All preferences
    are stored in a single JSON file as a dict keyed by user_id.

    Args:
        path: Path to the JSON preferences file. Created if it does not exist.
    """

    def __init__(self, path: Path | None = None) -> None:
        """Initialize the preference store.

        Args:
            path: File path for the JSON store. Defaults to
                data/user_preferences.json.
        """
        self._path = path or DEFAULT_PREFS_PATH
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Create the preferences file and parent directories if they do not exist."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")
            logger.info("preferences_file_created", path=str(self._path))

    def _load_all(self) -> dict[str, dict]:
        """Load all user preferences from the JSON file.

        Returns:
            Dict mapping user_id to serialized preference dicts.
        """
        try:
            text = self._path.read_text(encoding="utf-8")
            data = json.loads(text)
            if not isinstance(data, dict):
                return {}
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("preferences_load_error", error=str(exc))
            return {}

    def _save_all(self, data: dict[str, dict]) -> None:
        """Write all user preferences to the JSON file.

        Args:
            data: Dict mapping user_id to serialized preference dicts.
        """
        try:
            self._path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error("preferences_save_error", error=str(exc))

    def get(self, user_id: str) -> UserPreferences:
        """Retrieve preferences for a user, returning defaults if not found.

        Args:
            user_id: Unique user identifier.

        Returns:
            UserPreferences instance (defaults if user has no stored prefs).
        """
        all_prefs = self._load_all()
        raw = all_prefs.get(user_id)
        if raw is None:
            logger.debug("preferences_not_found_using_defaults", user_id=user_id)
            return UserPreferences()
        try:
            return UserPreferences.model_validate(raw)
        except Exception as exc:
            logger.warning("preferences_parse_error", user_id=user_id, error=str(exc))
            return UserPreferences()

    def set(self, user_id: str, preferences: UserPreferences) -> None:
        """Store preferences for a user, overwriting any existing values.

        Args:
            user_id: Unique user identifier.
            preferences: The full preferences to store.
        """
        all_prefs = self._load_all()
        all_prefs[user_id] = preferences.model_dump()
        self._save_all(all_prefs)
        logger.info("preferences_saved", user_id=user_id)

    def update(self, user_id: str, **kwargs: object) -> UserPreferences:
        """Partially update preferences for a user.

        Only the provided keyword arguments are updated; other fields
        retain their current values.

        Args:
            user_id: Unique user identifier.
            **kwargs: Fields to update (must be valid UserPreferences fields).

        Returns:
            The updated UserPreferences instance.
        """
        current = self.get(user_id)
        updated_data = current.model_dump()
        for key, value in kwargs.items():
            if key in updated_data:
                updated_data[key] = value
            else:
                logger.warning("unknown_preference_field", field=key)
        updated = UserPreferences.model_validate(updated_data)
        self.set(user_id, updated)
        return updated

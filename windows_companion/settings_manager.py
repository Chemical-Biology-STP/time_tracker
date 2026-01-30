"""
Settings manager for persisting user preferences.
"""

import json
import os
from pathlib import Path
from typing import Optional


class SettingsManager:
    """Manages application settings with persistence."""
    
    def __init__(self):
        self._settings_dir = Path.home() / ".timetrackercompanion"
        self._settings_file = self._settings_dir / "settings.json"
        self._settings = self._load_settings()
    
    def _load_settings(self) -> dict:
        """Load settings from disk."""
        if self._settings_file.exists():
            try:
                with open(self._settings_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return self._default_settings()
    
    def _default_settings(self) -> dict:
        """Return default settings."""
        return {
            "backend_url": "http://localhost:5001",
            "prompt_interval_minutes": 30,
            "default_group_id": None,
            "launch_at_login": False,
            "server_port": 5001
        }
    
    def _save_settings(self):
        """Save settings to disk."""
        self._settings_dir.mkdir(parents=True, exist_ok=True)
        with open(self._settings_file, "w") as f:
            json.dump(self._settings, f, indent=2)
    
    @property
    def backend_url(self) -> str:
        return self._settings.get("backend_url", "http://localhost:5001")
    
    @backend_url.setter
    def backend_url(self, value: str):
        self._settings["backend_url"] = value
        self._save_settings()
    
    @property
    def prompt_interval_minutes(self) -> int:
        return self._settings.get("prompt_interval_minutes", 30)
    
    @prompt_interval_minutes.setter
    def prompt_interval_minutes(self, value: int):
        self._settings["prompt_interval_minutes"] = value
        self._save_settings()
    
    @property
    def default_group_id(self) -> Optional[int]:
        return self._settings.get("default_group_id")
    
    @default_group_id.setter
    def default_group_id(self, value: Optional[int]):
        self._settings["default_group_id"] = value
        self._save_settings()
    
    @property
    def launch_at_login(self) -> bool:
        return self._settings.get("launch_at_login", False)
    
    @launch_at_login.setter
    def launch_at_login(self, value: bool):
        self._settings["launch_at_login"] = value
        self._save_settings()
    
    @property
    def server_port(self) -> int:
        return self._settings.get("server_port", 5001)
    
    @server_port.setter
    def server_port(self, value: int):
        self._settings["server_port"] = value
        self._save_settings()

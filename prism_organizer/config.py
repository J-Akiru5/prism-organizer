"""Configuration loader for Prism Organizer.

Loads settings from ~/.prism-organizer/config.yaml with sensible defaults.
On first run, creates the config directory and copies the example config.
"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# ── Default Configuration ──────────────────────────────────────────

DEFAULT_CONFIG: Dict[str, Any] = {
    "default_paths": [
        "~/Downloads",
        "~/Desktop",
    ],
    "categories": {
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff", ".heic"],
        "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".pages", ".tex", ".md"],
        "Spreadsheets": [".xlsx", ".xls", ".csv", ".ods", ".numbers"],
        "Presentations": [".pptx", ".ppt", ".odp", ".key"],
        "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
        "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
        "Code": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rs", ".rb", ".php", ".html", ".css"],
        "Installers": [".exe", ".msi", ".dmg", ".deb", ".rpm", ".appimage"],
        "Databases": [".db", ".sqlite", ".accdb", ".mdb", ".sql"],
        "Design": [".psd", ".ai", ".fig", ".sketch", ".xd", ".blend"],
        "Fonts": [".ttf", ".otf", ".woff", ".woff2"],
        "Misc": [],
    },
    "junk_patterns": [
        "~$*",
        "*.crdownload",
        "*.tmp",
        "*.bak",
        "Thumbs.db",
        "desktop.ini",
        ".DS_Store",
    ],
    "cloud_drives": {
        "auto_detect": True,
        "known_paths": [
            "~/OneDrive",
            "~/Google Drive",
            "~/Dropbox",
            "~/iCloudDrive",
            "~/Box",
            "~/MEGA",
            "~/pCloudDrive",
            "~/WPS Cloud Files",
            "~/WPSDrive",
        ],
        "detect_from_registry": True,
    },
    "installer_detection": {
        "enabled": True,
        "extensions": [".exe", ".msi"],
        "min_size": "50MB",
        "action": "suggest",
        "archive_path": "~/Archive/Installers/",
    },
    "screenshot_rules": {
        "enabled": True,
        "source": "~/Pictures/Screenshots",
        "organize_by": "date",
        "date_format": "%Y/%B",
    },
    "duplicates": {
        "method": "hash",
        "keep": "oldest",
        "min_size": "1MB",
    },
    "date_format": "%Y/%B",
    "custom_rules": [],
    "ai": {
        "enabled": False,
        "provider": "openai",
        "model": "gpt-4o-mini",
        "api_key": "",
        "base_url": "",
        "features": {
            "classify_unknown": True,
            "smart_rename": False,
        },
        "min_confidence": 0.7,
    },
    "watcher": {
        "cooldown_seconds": 10,
        "min_file_age_seconds": 5,
    },
}


class Config:
    """Configuration manager for Prism Organizer.

    Handles loading, merging, and accessing all user-configurable settings.
    On instantiation, the config file (YAML) is read and deep-merged on top
    of ``DEFAULT_CONFIG`` so that any keys the user hasn't customised still
    carry sensible defaults.

    Typical usage::

        cfg = Config()                       # uses ~/.prism-organizer/config.yaml
        cfg = Config("/path/to/custom.yaml") # uses a specific file
        print(cfg.categories)                # typed accessor
        print(cfg.get("date_format"))        # generic accessor
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize config, loading from file or using defaults.

        Args:
            config_path: Optional path to a config YAML file.
                         If None, uses ~/.prism-organizer/config.yaml
        """
        self._data: Dict[str, Any] = dict(DEFAULT_CONFIG)  # start with defaults

        if config_path:
            self._config_path = Path(config_path)
        else:
            self._config_path = self._get_default_config_path()

        self._load()

    @staticmethod
    def _get_default_config_path() -> Path:
        """Get the default config file path.

        Returns:
            ``Path`` pointing to ``~/.prism-organizer/config.yaml``.
        """
        return Path.home() / ".prism-organizer" / "config.yaml"

    def _ensure_config_dir(self) -> None:
        """Ensure the config directory exists, creating it if necessary."""
        config_dir = self._config_path.parent
        config_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        """Load configuration from YAML file, merging with defaults.

        If the file does not exist, it is created from defaults.
        If the file cannot be parsed, the instance falls back to
        ``DEFAULT_CONFIG``.
        """
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    user_config = yaml.safe_load(f) or {}
                self._deep_merge(self._data, user_config)
            except (yaml.YAMLError, OSError) as e:
                print(f"Warning: Could not load config from {self._config_path}: {e}")
                print("Using default configuration.")
        else:
            self.init_config()

    def _deep_merge(self, base: dict, override: dict) -> None:
        """Deep merge *override* dict into *base* dict (in-place).

        For keys present in both dicts where both values are ``dict``,
        the merge recurses.  In all other cases the *override* value
        wins outright (including list replacement).

        Args:
            base: The dictionary to merge *into* (modified in-place).
            override: The dictionary whose values take precedence.
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def init_config(self, example_config_path: Optional[Path] = None) -> Path:
        """Initialize config file from example if it doesn't exist.

        If *example_config_path* is provided and exists, it is copied
        verbatim.  Otherwise the current (default-based) configuration
        is serialised to YAML.

        Args:
            example_config_path: Path to example config file to copy.

        Returns:
            Path to the config file (existing or newly created).
        """
        self._ensure_config_dir()

        if not self._config_path.exists():
            if example_config_path and example_config_path.exists():
                shutil.copy2(example_config_path, self._config_path)
            else:
                # Write defaults as YAML
                with open(self._config_path, "w", encoding="utf-8") as f:
                    yaml.dump(self._data, f, default_flow_style=False, sort_keys=False)

        return self._config_path

    # ── Property accessors ─────────────────────────────────────

    @property
    def default_paths(self) -> List[str]:
        """Default target directories to organise (e.g. ``~/Downloads``)."""
        return self._data.get("default_paths", [])

    @property
    def categories(self) -> Dict[str, List[str]]:
        """Mapping of category names to their associated file extensions."""
        return self._data.get("categories", {})

    @property
    def junk_patterns(self) -> List[str]:
        """Glob patterns identifying junk / temporary files."""
        return self._data.get("junk_patterns", [])

    @property
    def cloud_drives(self) -> Dict[str, Any]:
        """Cloud-drive detection settings (auto-detect flags and known paths)."""
        return self._data.get("cloud_drives", {})

    @property
    def installer_detection(self) -> Dict[str, Any]:
        """Installer-detection rules (extensions, size threshold, action)."""
        return self._data.get("installer_detection", {})

    @property
    def screenshot_rules(self) -> Dict[str, Any]:
        """Screenshot-organisation rules (source dir, grouping strategy)."""
        return self._data.get("screenshot_rules", {})

    @property
    def duplicates_config(self) -> Dict[str, Any]:
        """Duplicate-detection settings (method, keep strategy, min size)."""
        return self._data.get("duplicates", {})

    @property
    def date_format(self) -> str:
        """Default ``strftime`` format string for date-based sub-folders."""
        return self._data.get("date_format", "%Y/%B")

    @property
    def custom_rules(self) -> List[Dict[str, Any]]:
        """User-defined custom organisation rules."""
        return self._data.get("custom_rules", [])

    @property
    def ai_config(self) -> Dict[str, Any]:
        """AI integration settings (provider, model, features)."""
        return self._data.get("ai", {})

    def get(self, key: str, default: Any = None) -> Any:
        """Get a top-level config value by key.

        Args:
            key: The configuration key to look up.
            default: Fallback value if the key is absent.

        Returns:
            The configuration value, or *default*.
        """
        return self._data.get(key, default)

    def get_extension_category(self, extension: str) -> str:
        """Get the category for a file extension.

        Args:
            extension: File extension including dot (e.g., ``'.jpg'``).

        Returns:
            Category name, or ``'Misc'`` if no category claims the
            extension.
        """
        ext_lower = extension.lower()
        for category, extensions in self.categories.items():
            if ext_lower in extensions:
                return category
        return "Misc"

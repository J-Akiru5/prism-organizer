"""Auto-update checker for Prism Organizer."""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

from prism_organizer import __version__

CACHE_DIR = Path.home() / ".prism-organizer"
TIMESTAMP_FILE = CACHE_DIR / ".last_update_check"
CHECK_INTERVAL_SECONDS = 24 * 60 * 60  # 24 hours


def get_install_method() -> str:
    """Determine how Prism Organizer was installed.

    Returns:
        "npm", "standalone", or "pip"
    """
    if os.environ.get("PRISM_INSTALL_METHOD") == "npm":
        return "npm"
    if getattr(sys, "frozen", False):
        return "standalone"
    return "pip"


def parse_version(version_str: str) -> Tuple[int, ...]:
    """Parse a version string into a tuple of integers for comparison."""
    try:
        # Strip pre-release suffixes if any (e.g. -rc1)
        clean_ver = version_str.split("-")[0]
        return tuple(map(int, clean_ver.split(".")))
    except Exception:
        return (0, 0, 0)


def is_newer_version(remote_ver: str, local_ver: str) -> bool:
    """Compare remote and local versions. Return True if remote is newer."""
    return parse_version(remote_ver) > parse_version(local_ver)


def check_for_updates(force: bool = False) -> Optional[str]:
    """Check if a newer version of Prism Organizer is available.

    Args:
        force: If True, bypass the 24-hour cache check.

    Returns:
        The latest version string if a newer version is available, else None.
    """
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    if not force and TIMESTAMP_FILE.exists():
        try:
            mtime = TIMESTAMP_FILE.stat().st_mtime
            if time.time() - mtime < CHECK_INTERVAL_SECONDS:
                return None
        except Exception:
            pass

    # Touch timestamp file to prevent rapid retries on failure/offline
    try:
        TIMESTAMP_FILE.touch()
    except Exception:
        pass

    url = "https://registry.npmjs.org/prism-organizer/latest"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": f"prism-organizer/{__version__}"}
        )
        with urllib.request.urlopen(req, timeout=1.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                remote_version = data.get("version")
                if remote_version and is_newer_version(remote_version, __version__):
                    return remote_version
    except Exception:
        pass

    return None


def download_and_apply_update(version: str) -> bool:
    """Download the latest standalone executable from GitHub and overwrite current.

    Only called for standalone installations.
    """
    import tempfile
    import subprocess
    from prism_organizer.display import display_info, display_success, display_error

    url = f"https://github.com/J-Akiru5/prism-organizer/releases/download/v{version}/prism-organizer.exe"
    current_exe = sys.executable
    temp_dir = tempfile.gettempdir()
    temp_exe = os.path.join(temp_dir, f"prism-organizer-{version}.exe")

    try:
        display_info(f"Downloading update v{version}...")
        req = urllib.request.Request(
            url,
            headers={"User-Agent": f"prism-organizer/{__version__}"}
        )
        with urllib.request.urlopen(req, timeout=30.0) as response:
            with open(temp_exe, "wb") as f:
                f.write(response.read())

        display_success("Download complete.")
        display_info("Applying update and restarting...")

        bat_content = f"""@echo off
:loop
tasklist | find /i "{os.path.basename(current_exe)}" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto loop
)
copy /y "{temp_exe}" "{current_exe}" >nul
del "{temp_exe}" >nul
start "" "{current_exe}"
del "%~f0"
"""
        bat_path = os.path.join(temp_dir, "update_prism.bat")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        # Spawn the batch script detached so it continues running after we exit
        subprocess.Popen(
            [bat_path],
            shell=True,
            creationflags=0x00000008 | 0x00000010  # DETACHED_PROCESS | CREATE_NEW_CONSOLE
        )
        sys.exit(0)
    except Exception as e:
        display_error(f"Failed to apply update: {e}")
        return False

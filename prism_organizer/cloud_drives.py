"""Cloud and backup drive detection for Prism Organizer.

Auto-detects cloud sync directories on the system and prompts the user
to choose whether to skip or include them during file organization.

Detection methods:
1. Known paths — checks common install locations
2. Windows Registry — reads registry keys for custom paths
3. Running processes — detects sync agents
"""

import os
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from colorama import Fore, Style

from prism_organizer.config import Config
from prism_organizer.utils import expand_path, print_header


# Cloud service display names and their registry locations (Windows)
CLOUD_SERVICES = {
    "OneDrive": {
        "known_paths": ["~/OneDrive"],
        "registry_keys": [
            r"HKCU\Software\Microsoft\OneDrive",
        ],
        "registry_value": "UserFolder",
        "process_names": ["OneDrive.exe"],
    },
    "Google Drive": {
        "known_paths": ["~/Google Drive", "~/My Drive"],
        "registry_keys": [
            r"HKCU\Software\Google\DriveFS",
        ],
        "registry_value": "MountPoint",
        "process_names": ["GoogleDriveFS.exe", "googledrivesync.exe"],
    },
    "Dropbox": {
        "known_paths": ["~/Dropbox"],
        "registry_keys": [],
        "process_names": ["Dropbox.exe"],
    },
    "iCloud Drive": {
        "known_paths": ["~/iCloudDrive"],
        "registry_keys": [],
        "process_names": ["iCloudDrive.exe", "ApplePhotoStreams.exe"],
    },
    "Box": {
        "known_paths": ["~/Box"],
        "registry_keys": [],
        "process_names": ["Box.exe"],
    },
    "MEGA": {
        "known_paths": ["~/MEGA", "~/MEGAsync"],
        "registry_keys": [],
        "process_names": ["MEGAsync.exe"],
    },
    "pCloud": {
        "known_paths": ["~/pCloudDrive"],
        "registry_keys": [],
        "process_names": ["pCloud.exe"],
    },
    "WPS Cloud": {
        "known_paths": ["~/WPS Cloud Files", "~/WPSDrive"],
        "registry_keys": [],
        "process_names": ["wpscloudsvr.exe"],
    },
}


@dataclass
class DetectedDrive:
    """A detected cloud/backup drive."""
    name: str           # Service name (e.g., 'OneDrive')
    path: Path          # Resolved directory path
    skip: bool = True   # Whether to skip this drive (default: skip)
    detection_method: str = "known_path"  # How it was detected


class CloudDriveDetector:
    """Detects and manages cloud/backup drive exclusions."""

    def __init__(self, config: Config):
        self.config = config
        self._detected: List[DetectedDrive] = []

    def detect(self) -> List[DetectedDrive]:
        """Detect all cloud drives present on the system.

        Uses three detection methods in order:

        1. **Known paths** — expands well-known ``~/`` prefixed paths for
           each cloud service and checks whether the directory exists.
        2. **Windows Registry** — reads service-specific registry keys
           (e.g. OneDrive ``UserFolder``, Google Drive ``MountPoint``)
           to locate custom install directories.
        3. **Running processes** — queries ``tasklist`` to see if a sync
           agent is actively running.  This doesn't discover new paths
           but annotates already-detected drives with ``(syncing)``.

        Any additional paths listed under ``cloud_drives.known_paths`` in
        the user's config file are appended last, with the directory
        basename used as the service name.

        Returns:
            List of :class:`DetectedDrive` instances found on the system.
        """
        cloud_config = self.config.cloud_drives
        if not cloud_config.get("auto_detect", True):
            return []

        detected: List[DetectedDrive] = []
        seen_paths: Set[Path] = set()

        for service_name, service_info in CLOUD_SERVICES.items():
            # Method 1: Check known paths
            for path_str in service_info.get("known_paths", []):
                resolved = expand_path(path_str)
                if resolved.exists() and resolved.is_dir() and resolved not in seen_paths:
                    detected.append(DetectedDrive(
                        name=service_name,
                        path=resolved,
                        detection_method="known_path",
                    ))
                    seen_paths.add(resolved)

            # Method 2: Check Windows Registry
            if cloud_config.get("detect_from_registry", True):
                for reg_key in service_info.get("registry_keys", []):
                    reg_path = self._read_registry(
                        reg_key, service_info.get("registry_value", ""),
                    )
                    if reg_path:
                        resolved = Path(reg_path).resolve()
                        if resolved.exists() and resolved.is_dir() and resolved not in seen_paths:
                            detected.append(DetectedDrive(
                                name=service_name,
                                path=resolved,
                                detection_method="registry",
                            ))
                            seen_paths.add(resolved)

            # Method 3: Check running processes (just for awareness)
            # We don't add extra paths from processes, but note if sync is active
            for proc in service_info.get("process_names", []):
                if self._is_process_running(proc):
                    # Mark any detected drives for this service as "actively syncing"
                    for drive in detected:
                        if drive.name == service_name:
                            drive.detection_method += " (syncing)"

        # Also check user-configured known_paths from config
        for path_str in cloud_config.get("known_paths", []):
            resolved = expand_path(path_str)
            if resolved.exists() and resolved.is_dir() and resolved not in seen_paths:
                # Try to identify the service name
                name = resolved.name
                detected.append(DetectedDrive(
                    name=name,
                    path=resolved,
                    detection_method="config",
                ))
                seen_paths.add(resolved)

        self._detected = detected
        return detected

    def prompt_user(self, detected: Optional[List[DetectedDrive]] = None) -> Set[Path]:
        """Prompt the user to choose which cloud drives to skip.

        Displays a formatted table of detected cloud drives and offers
        three choices:

        * **S** — Skip all detected drives (default).
        * **A** — Include all drives, treating them as normal folders.
        * **E** — Edit selections individually via :meth:`_edit_selections`.

        Args:
            detected: List of detected drives.  If *None*, falls back to
                the result cached from the last :meth:`detect` call.

        Returns:
            A set of :class:`~pathlib.Path` objects representing
            directories the user chose to **skip**.
        """
        drives = detected or self._detected
        if not drives:
            return set()

        # Display detected drives
        print()
        print(f"{Fore.CYAN}{'═' * 62}")
        print(f"{Fore.CYAN}  ☁  CLOUD DRIVES DETECTED")
        print(f"{Fore.CYAN}{'═' * 62}{Style.RESET_ALL}")
        print()

        for i, drive in enumerate(drives, 1):
            status = (
                f"{Fore.YELLOW}[SKIP]{Style.RESET_ALL}"
                if drive.skip
                else f"{Fore.GREEN}[INCLUDE]{Style.RESET_ALL}"
            )
            print(f"  {Fore.WHITE}{i}. {drive.name:<15} {str(drive.path):<35} {status}")

        print()
        print(f"  {Fore.WHITE}These directories are synced to cloud services.")
        print(f"  Organizing files here may cause sync conflicts.{Style.RESET_ALL}")
        print()
        print(f"  {Fore.CYAN}{'─' * 62}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}[S] Skip all (default)    [E] Edit selections")
        print(f"  [A] Include all (treat as normal folders){Style.RESET_ALL}")
        print()

        try:
            choice = input(f"  {Fore.YELLOW}Choose [S/E/A]: {Style.RESET_ALL}").strip().upper()
        except (KeyboardInterrupt, EOFError):
            print()
            choice = "S"

        if choice == "A":
            for drive in drives:
                drive.skip = False
        elif choice == "E":
            self._edit_selections(drives)
        else:
            # Default: skip all
            for drive in drives:
                drive.skip = True

        # Return set of paths to skip
        return {drive.path for drive in drives if drive.skip}

    def _edit_selections(self, drives: List[DetectedDrive]) -> None:
        """Let the user toggle individual cloud drives.

        For each drive the user may press:

        * **S** — mark as *skip*
        * **I** — mark as *include*
        * **Enter** — keep the current setting

        A summary of the final selections is printed afterwards.
        """
        print()
        print(
            f"  {Fore.CYAN}Toggle each drive "
            f"(Enter = keep current, S = skip, I = include):{Style.RESET_ALL}"
        )
        print()

        for drive in drives:
            current = "SKIP" if drive.skip else "INCLUDE"
            try:
                choice = input(
                    f"  {Fore.WHITE}{drive.name:<15} [{current}] → {Style.RESET_ALL}"
                ).strip().upper()
            except (KeyboardInterrupt, EOFError):
                print()
                break

            if choice == "S":
                drive.skip = True
            elif choice == "I":
                drive.skip = False
            # else: keep current

        print()
        print(f"  {Fore.GREEN}Updated selections:{Style.RESET_ALL}")
        for drive in drives:
            status = (
                f"{Fore.YELLOW}SKIP{Style.RESET_ALL}"
                if drive.skip
                else f"{Fore.GREEN}INCLUDE{Style.RESET_ALL}"
            )
            print(f"    {drive.name:<15} → {status}")

    @staticmethod
    def _read_registry(key_path: str, value_name: str) -> Optional[str]:
        """Read a value from the Windows Registry.

        Parses the *key_path* into a hive (``HKCU`` or ``HKLM``) and a
        subkey, then attempts to open the key and query *value_name*.

        Args:
            key_path: Registry key path (e.g.
                ``'HKCU\\\\Software\\\\Microsoft\\\\OneDrive'``).
            value_name: Value name to read (e.g. ``'UserFolder'``).

        Returns:
            The value as a string, or *None* if the key/value does not
            exist or ``winreg`` is unavailable (non-Windows platforms).
        """
        try:
            import winreg
            # Parse hive and subkey
            hive_map = {
                "HKCU": winreg.HKEY_CURRENT_USER,
                "HKLM": winreg.HKEY_LOCAL_MACHINE,
            }
            parts = key_path.split("\\", 1)
            if len(parts) != 2 or parts[0] not in hive_map:
                return None

            hive = hive_map[parts[0]]
            subkey = parts[1]

            with winreg.OpenKey(hive, subkey) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
                return str(value)
        except (ImportError, OSError, FileNotFoundError):
            return None

    @staticmethod
    def _is_process_running(process_name: str) -> bool:
        """Check if a Windows process is currently running by name.

        Uses ``tasklist /FI`` with an ``IMAGENAME`` filter and scans the
        output for the process name (case-insensitive).

        Args:
            process_name: Executable name including extension
                (e.g. ``'OneDrive.exe'``).

        Returns:
            *True* if the process appears in the ``tasklist`` output.
        """
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if hasattr(subprocess, "CREATE_NO_WINDOW")
                    else 0
                ),
            )
            return process_name.lower() in result.stdout.lower()
        except (subprocess.SubprocessError, OSError):
            return False

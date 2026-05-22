"""Filesystem watcher and task scheduler for Prism Organizer.

Provides real-time directory monitoring and Windows Task Scheduler
integration so that file organization can run automatically on a
schedule or in response to filesystem events.
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from prism_organizer.config import Config
from prism_organizer.utils import expand_path, print_info, print_warning, print_success


class DirectoryWatcher:
    """Watches one or more directories for changes and triggers actions.

    Requires the ``watchdog`` package.  Installs with:
    ``pip install watchdog``.

    Typical usage::

        watcher = DirectoryWatcher(config)
        watcher.add_directory("~/Downloads", actions=["sort"])
        watcher.start()
    """

    def __init__(self, config: Config):
        self.config = config
        self._watch_paths: Dict[Path, List[str]] = {}
        self._cooldown: float = float(
            config.get("watcher", {}).get("cooldown_seconds", 10)
        )
        self._min_age: float = float(
            config.get("watcher", {}).get("min_file_age_seconds", 5)
        )
        self._callback: Optional[Callable] = None

    def add_directory(self, path: str, actions: Optional[List[str]] = None):
        """Register a directory to watch.

        Args:
            path: Directory path to monitor.
            actions: List of actions to trigger (``"sort"``, ``"clean"``).
                Defaults to ``["sort"]``.
        """
        resolved = expand_path(path)
        if not resolved.exists():
            print_warning(f"Watch path does not exist: {resolved}")
            return
        self._watch_paths[resolved] = actions or ["sort"]

    def set_callback(self, callback: Callable):
        """Set a function to call when changes are detected.

        The callback receives ``(path: Path, actions: List[str])``.
        """
        self._callback = callback

    def start(self) -> None:
        """Begin watching registered directories (blocking call).

        Uses ``watchdog`` if available; falls back to a simple polling
        loop if not.
        """
        if not self._watch_paths:
            print_warning("No directories registered for watching.")
            return

        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            print_info("Watching directories for changes (Ctrl+C to stop)...")
            for p, actions in self._watch_paths.items():
                print_info(f"  {p} -> {', '.join(actions)}")

            handler = _WatchdogHandler(self)
            observer = Observer()
            for path in self._watch_paths:
                observer.schedule(handler, str(path), recursive=False)
            observer.start()

            try:
                while observer.is_alive():
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
            observer.join()

        except ImportError:
            print_warning(
                "The 'watchdog' package is not installed.  "
                "Falling back to polling (every 10 seconds).  "
                "Install watchdog with: pip install watchdog"
            )
            self._poll_loop()

    def _poll_loop(self) -> None:
        """Simple polling-based watch loop (fallback when watchdog missing)."""
        print_info("Polling directories for changes (Ctrl+C to stop)...")
        known_files: Dict[Path, Set[Path]] = {}

        # Initial snapshot
        for path in self._watch_paths:
            known_files[path] = {
                f for f in path.iterdir() if f.is_file()
            }

        try:
            while True:
                time.sleep(self._cooldown)
                for watch_path, actions in self._watch_paths.items():
                    try:
                        current = {f for f in watch_path.iterdir() if f.is_file()}
                        new_files = current - known_files.get(watch_path, set())

                        # Filter by minimum age
                        now = time.time()
                        valid_new = {
                            f for f in new_files
                            if now - f.stat().st_mtime >= self._min_age
                        }

                        if valid_new:
                            self._trigger_actions(watch_path, actions, valid_new)

                        known_files[watch_path] = current
                    except (OSError, PermissionError):
                        continue
        except KeyboardInterrupt:
            print_info("Stopped watching.")

    def _trigger_actions(
        self,
        watch_path: Path,
        actions: List[str],
        new_files: Set[Path],
    ) -> None:
        """Called when new files are detected in a watched directory."""
        count = len(new_files)
        ts = datetime.now().strftime("%H:%M:%S")
        print_info(f"[{ts}] {count} new file(s) in {watch_path}")

        if self._callback:
            self._callback(watch_path, actions)


class _WatchdogHandler:
    """watchdog event handler that debounces and triggers actions."""

    def __init__(self, watcher: DirectoryWatcher):
        self._watcher = watcher
        self._pending: Dict[Path, float] = {}  # path -> first-seen timestamp
        self._min_age = watcher._min_age
        self._cooldown = watcher._cooldown

    def dispatch(self, event):
        from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileMovedEvent

        if event.is_directory:
            return

        src_path = Path(event.src_path)
        if src_path.name.startswith("."):
            return

        # Find which watch path this event belongs to
        for watch_path, actions in self._watcher._watch_paths.items():
            if src_path.parent == watch_path:
                now = time.time()

                if isinstance(event, FileMovedEvent):
                    dest_path = Path(event.dest_path)
                    if dest_path.parent == watch_path:
                        self._pending[dest_path] = now
                    if src_path in self._pending:
                        del self._pending[src_path]
                        # File moved out of watch dir; not our trigger
                    continue

                if isinstance(event, (FileCreatedEvent, FileModifiedEvent)):
                    if src_path not in self._pending:
                        self._pending[src_path] = now
                    break

        # Flush pending files that have been stable for long enough
        to_process: Set[Path] = set()
        now = time.time()
        for fpath, first_seen in list(self._pending.items()):
            # Wait for the file to stop being modified
            try:
                age = now - fpath.stat().st_mtime
            except OSError:
                del self._pending[fpath]
                continue

            if age >= self._min_age and (now - first_seen) >= self._cooldown * 0.5:
                to_process.add(fpath)
                del self._pending[fpath]

        if to_process:
            current_watch = None
            current_actions: List[str] = []
            for wp, acts in self._watcher._watch_paths.items():
                if any(f.parent == wp for f in to_process):
                    current_watch = wp
                    current_actions = acts
                    break

            if current_watch:
                self._watcher._trigger_actions(current_watch, current_actions, to_process)


# ── Windows Task Scheduler ────────────────────────────────────────────


class TaskScheduler:
    """Manage Windows Task Scheduler entries for periodic file organization.

    Uses ``schtasks.exe`` underneath to create, list, and remove tasks.
    """

    APP_NAME = "Prism Organizer"

    def add_task(
        self,
        path: str,
        command: str,
        interval: str = "daily",
        time_str: str = "09:00",
    ) -> bool:
        """Create a scheduled task to run a prism-organizer command.

        Args:
            path: Directory to operate on.
            command: Subcommand to run (``scan``, ``sort``, ``clean``, etc.).
            interval: ``"daily"``, ``"weekly"``, or ``"hourly"``.
            time_str: Start time in ``HH:MM`` format (24h).

        Returns:
            True if the task was created successfully.
        """
        resolved = expand_path(path)
        task_name = f"{self.APP_NAME} - {command} {resolved.name}"

        exe = sys.executable
        
        # Escape quotes inside the /TR command string to prevent argument-splitting vulnerabilities.
        exe_escaped = str(exe).replace('"', '\\"')
        resolved_escaped = str(resolved).replace('"', '\\"')
        task_run = f'\\"{exe_escaped}\\" -m prism_organizer {command} \\"{resolved_escaped}\\" --confirm'

        schedule_map = {
            "daily": "DAILY",
            "weekly": "WEEKLY",
            "hourly": "HOURLY",
        }
        sc = schedule_map.get(interval, "DAILY")

        cmd = [
            "schtasks", "/Create", "/SC", sc,
            "/TN", task_name,
            "/TR", task_run,
            "/ST", time_str,
            "/F",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print_success(f"Scheduled task created: {task_name}")
                print_info(f"  Runs {interval} at {time_str}: prism-organizer {command} {resolved}")
                return True
            else:
                print_warning(f"Failed to create task: {result.stderr.strip()}")
                return False
        except (subprocess.SubprocessError, OSError) as e:
            print_warning(f"Failed to create scheduled task: {e}")
            return False

    def list_tasks(self) -> List[Dict[str, str]]:
        """List all Prism Organizer scheduled tasks.

        Returns:
            List of task dicts with ``name``, ``next_run``, and ``status``.
        """
        try:
            result = subprocess.run(
                ["schtasks", "/Query", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=30,
            )
        except (subprocess.SubprocessError, OSError):
            return []

        tasks = []
        for line in result.stdout.strip().split("\n"):
            if self.APP_NAME not in line:
                continue
            parts = line.strip('"').split('","')
            if len(parts) >= 3:
                tasks.append({
                    "name": parts[0],
                    "next_run": parts[1] if len(parts) > 1 else "N/A",
                    "status": parts[2] if len(parts) > 2 else "Unknown",
                })

        return tasks

    def remove_task(self, task_name: str) -> bool:
        """Remove a scheduled task by name.

        Args:
            task_name: Full task name (as shown by :meth:`list_tasks`).

        Returns:
            True if the task was removed.
        """
        try:
            result = subprocess.run(
                ["schtasks", "/Delete", "/TN", task_name, "/F"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                print_success(f"Removed scheduled task: {task_name}")
                return True
            else:
                print_warning(f"Failed to remove task: {result.stderr.strip()}")
                return False
        except (subprocess.SubprocessError, OSError) as e:
            print_warning(f"Failed to remove scheduled task: {e}")
            return False

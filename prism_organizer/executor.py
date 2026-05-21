"""File operation executor for Prism Organizer.

Executes planned file operations (move, copy, delete, archive) and
logs every operation to a JSON file for undo support.
"""

import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from prism_organizer.sorter import SortPlan
from prism_organizer.duplicates import DuplicateResult
from prism_organizer.cleaner import CleanupPlan
from prism_organizer.rules import RulePlan
from prism_organizer.display import display_progress
from prism_organizer.utils import (
    get_logs_dir, get_backup_dir, format_size, expand_path,
    print_success, print_error, print_warning, print_info,
)


@dataclass
class Operation:
    """A single recorded file operation."""
    action: str         # 'move', 'copy', 'delete', 'archive'
    source: str         # Original file path
    destination: str = ""  # New file path (for move/copy)
    backup: str = ""    # Backup path (for delete)
    timestamp: str = ""
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "action": self.action,
            "source": self.source,
            "destination": self.destination,
            "backup": self.backup,
            "timestamp": self.timestamp,
        }


@dataclass
class ExecutionLog:
    """Log of all operations in a single execution."""
    timestamp: str = ""
    command: str = ""
    target_dir: str = ""
    operations: List[Operation] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "command": self.command,
            "target_dir": self.target_dir,
            "operations": [op.to_dict() for op in self.operations],
            "errors": self.errors,
        }


class Executor:
    """Executes file operations with logging and backup support."""

    def __init__(self, config: Optional[Any] = None):
        self.config = config
        self._log = ExecutionLog(
            timestamp=datetime.now().isoformat(),
        )

    def execute_sort(self, plan: SortPlan) -> ExecutionLog:
        """Execute a sort plan."""
        self._log.command = f"sort --by {plan.sort_by}"
        self._log.target_dir = str(plan.target_dir)
        
        print_info(f"Executing sort ({plan.total_files} files)...")
        
        for op in display_progress(plan.operations, desc="Moving files"):
            self._move_file(op.source, op.destination)
        
        self._save_log()
        
        succeeded = len(self._log.operations)
        failed = len(self._log.errors)
        print_success(f"Sorted {succeeded} files successfully.")
        if failed:
            print_warning(f"{failed} files failed.")
        
        return self._log

    def execute_cleanup(self, plan: CleanupPlan, target_dir: Path) -> ExecutionLog:
        """Execute a cleanup plan."""
        self._log.command = "clean"
        self._log.target_dir = str(target_dir)
        backup_dir = get_backup_dir(target_dir)
        
        installer_config = self.config.installer_detection if self.config else None
        archive_dir_parent = (
            expand_path(installer_config.get("archive_path", "~/Archive/Installers/"))
            if installer_config is not None
            else backup_dir
        )
        
        print_info(f"Executing cleanup ({plan.total_items} items)...")
        
        for item in display_progress(plan.items, desc="Cleaning"):
            if item.action == "suggest":
                # Suggestions are just informational, skip
                continue
            
            if item.action == "delete":
                self._delete_file(item.path, backup_dir)
            elif item.action == "archive":
                self._move_file(item.path, archive_dir_parent / item.path.name)
        
        self._save_log()
        
        succeeded = len(self._log.operations)
        print_success(f"Cleaned {succeeded} items.")
        
        return self._log

    def execute_duplicate_cleanup(self, result: DuplicateResult, target_dir: Path) -> ExecutionLog:
        """Execute duplicate file removal."""
        self._log.command = "dupes --clean"
        self._log.target_dir = str(target_dir)
        backup_dir = get_backup_dir(target_dir)
        
        total_removable = sum(len(g.removable) for g in result.groups)
        print_info(f"Removing {total_removable} duplicate files...")
        
        removable_files = [fi for g in result.groups for fi in g.removable]
        
        for fi in display_progress(removable_files, desc="Removing dupes"):
            self._delete_file(fi.path, backup_dir)
        
        self._save_log()
        
        succeeded = len(self._log.operations)
        print_success(f"Removed {succeeded} duplicate files.")
        print_info(f"Backups saved to: {backup_dir}")
        
        return self._log

    def execute_rules(self, plan: RulePlan, target_dir: Path) -> ExecutionLog:
        """Execute custom rule actions."""
        self._log.command = "rules"
        self._log.target_dir = str(target_dir)
        backup_dir = get_backup_dir(target_dir)
        
        print_info(f"Executing {plan.total_matches} rule actions...")
        
        for match in display_progress(plan.matches, desc="Applying rules"):
            try:
                if match.action == "move":
                    if match.destination:
                        self._move_file(match.file_info.path, match.destination)
                elif match.action == "copy":
                    if match.destination:
                        self._copy_file(match.file_info.path, match.destination)
                elif match.action == "delete":
                    self._delete_file(match.file_info.path, backup_dir)
                elif match.action == "rename":
                    if match.new_name:
                        new_path = match.file_info.path.parent / match.new_name
                        self._move_file(match.file_info.path, new_path)
                elif match.action == "archive":
                    self._archive_file(match.file_info.path, backup_dir)
            except Exception as e:
                self._log.errors.append(f"Failed to {match.action} {match.file_info.name}: {e}")
        
        self._save_log()
        
        succeeded = len(self._log.operations)
        failed = len(self._log.errors)
        print_success(f"Applied {succeeded} rule actions.")
        if failed:
            print_warning(f"{failed} actions failed.")
        
        return self._log

    # ── Internal file operations ──────────────────────────────────

    def _move_file(self, source: Path, destination: Path) -> None:
        """Move a file and log the operation."""
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            self._log.operations.append(Operation(
                action="move",
                source=str(source),
                destination=str(destination),
                timestamp=datetime.now().isoformat(),
            ))
        except (OSError, shutil.Error) as e:
            self._log.errors.append(f"Move failed: {source} -> {destination}: {e}")

    def _copy_file(self, source: Path, destination: Path) -> None:
        """Copy a file and log the operation."""
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(source), str(destination))
            self._log.operations.append(Operation(
                action="copy",
                source=str(source),
                destination=str(destination),
                timestamp=datetime.now().isoformat(),
            ))
        except (OSError, shutil.Error) as e:
            self._log.errors.append(f"Copy failed: {source} -> {destination}: {e}")

    def _delete_file(self, filepath: Path, backup_dir: Path) -> None:
        """Delete a file by moving it to the backup directory."""
        try:
            backup_path = backup_dir / filepath.name
            # Handle name conflicts in backup
            counter = 1
            while backup_path.exists():
                backup_path = backup_dir / f"{filepath.stem}_{counter}{filepath.suffix}"
                counter += 1
            
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(filepath), str(backup_path))
            self._log.operations.append(Operation(
                action="delete",
                source=str(filepath),
                backup=str(backup_path),
                timestamp=datetime.now().isoformat(),
            ))
        except (OSError, shutil.Error) as e:
            self._log.errors.append(f"Delete failed: {filepath}: {e}")

    def _archive_file(self, filepath: Path, archive_dir: Path) -> None:
        """Archive a file into a zip in the archive directory."""
        try:
            archive_dir.mkdir(parents=True, exist_ok=True)
            zip_path = archive_dir / f"{filepath.stem}.zip"
            
            # Handle name conflicts — don't overwrite existing archives
            counter = 1
            while zip_path.exists():
                zip_path = archive_dir / f"{filepath.stem}_{counter}.zip"
                counter += 1
            
            with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(str(filepath), filepath.name)
            
            # Remove original after archiving
            filepath.unlink()
            
            self._log.operations.append(Operation(
                action="archive",
                source=str(filepath),
                destination=str(zip_path),
                timestamp=datetime.now().isoformat(),
            ))
        except (OSError, zipfile.BadZipFile) as e:
            self._log.errors.append(f"Archive failed: {filepath}: {e}")

    def _save_log(self) -> None:
        """Save the execution log to a JSON file."""
        logs_dir = get_logs_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"operation_{timestamp}.json"
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(self._log.to_dict(), f, indent=2, ensure_ascii=False)
            print_info(f"Operation log saved: {log_file}")
        except OSError as e:
            print_error(f"Failed to save operation log: {e}")

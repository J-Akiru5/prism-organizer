"""Undo/rollback system for Prism Organizer.

Reads operation logs and reverses file moves, copies, and deletes.
"""

import json
import shutil
from pathlib import Path
from typing import List, Optional

from colorama import Fore, Style
from tqdm import tqdm

from prism_organizer.utils import (
    get_logs_dir, print_header, print_success, print_error,
    print_warning, print_info, confirm_action,
)


class UndoManager:
    """Manages undo operations from execution logs."""

    def __init__(self):
        self.logs_dir = get_logs_dir()

    def list_operations(self, limit: int = 10) -> List[dict]:
        """List recent operation logs.
        
        Args:
            limit: Maximum number of logs to return.
        
        Returns:
            List of operation log dicts, newest first.
        """
        log_files = sorted(
            self.logs_dir.glob("operation_*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        
        operations = []
        for log_file in log_files[:limit]:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data["_log_file"] = str(log_file)
                operations.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        
        return operations

    def undo_last(self) -> bool:
        """Undo the most recent operation.
        
        Returns:
            True if undo was successful.
        """
        operations = self.list_operations(limit=1)
        if not operations:
            print_warning("No operations to undo.")
            return False
        
        return self.undo_operation(operations[0])

    def undo_operation(self, log_data: dict) -> bool:
        """Undo a specific operation from its log data.
        
        Args:
            log_data: The operation log dictionary.
        
        Returns:
            True if undo was successful.
        """
        ops = log_data.get("operations", [])
        if not ops:
            print_warning("No operations found in log.")
            return False
        
        print_header("PRISM ORGANIZER \u2014 UNDO")
        print(f"\n  {Fore.WHITE}Operation:  {Fore.CYAN}{log_data.get('command', 'unknown')}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Timestamp:  {Fore.CYAN}{log_data.get('timestamp', 'unknown')}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Target:     {Fore.CYAN}{log_data.get('target_dir', 'unknown')}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Operations: {Fore.CYAN}{len(ops)} to reverse{Style.RESET_ALL}")
        print()
        
        if not confirm_action("Undo these operations?"):
            return False
        
        # Reverse operations in reverse order
        success_count = 0
        error_count = 0
        
        for op in tqdm(reversed(ops), total=len(ops), desc="  Undoing", unit="op",
                       bar_format="  {l_bar}{bar:30}{r_bar}"):
            try:
                action = op.get("action")
                
                if action == "move":
                    # Move back: destination -> source
                    src = Path(op["destination"])
                    dst = Path(op["source"])
                    if src.exists():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(src), str(dst))
                        success_count += 1
                    else:
                        error_count += 1
                
                elif action == "delete":
                    # Restore from backup
                    backup = Path(op.get("backup", ""))
                    original = Path(op["source"])
                    if backup.exists():
                        original.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(backup), str(original))
                        success_count += 1
                    else:
                        error_count += 1
                
                elif action == "copy":
                    # Remove the copy
                    copy_path = Path(op["destination"])
                    if copy_path.exists():
                        copy_path.unlink()
                        success_count += 1
                
                elif action == "archive":
                    # Cannot easily undo archive, warn user
                    print_warning(f"Cannot auto-undo archive: {op.get('source', '?')}")
                    error_count += 1
                    
            except (OSError, shutil.Error) as e:
                error_count += 1
        
        # Clean up empty directories that were created during the original operation
        target_dir = log_data.get("target_dir")
        if target_dir:
            self._cleanup_empty_dirs(Path(target_dir))
        
        # Remove the log file after successful undo
        log_file = log_data.get("_log_file")
        if log_file and success_count > 0:
            try:
                undo_log = Path(log_file).with_suffix(".undone")
                Path(log_file).rename(undo_log)
            except OSError:
                pass
        
        print()
        print_success(f"Undone {success_count} operations.")
        if error_count:
            print_warning(f"{error_count} operations could not be undone.")
        
        return error_count == 0

    @staticmethod
    def _cleanup_empty_dirs(target_dir: Path) -> None:
        """Remove empty directories created during organization."""
        if not target_dir.exists():
            return
        
        # Walk bottom-up to remove empty dirs
        for dirpath in sorted(target_dir.rglob("*"), reverse=True):
            if dirpath.is_dir():
                try:
                    if not any(dirpath.iterdir()):
                        dirpath.rmdir()
                except (OSError, PermissionError):
                    pass

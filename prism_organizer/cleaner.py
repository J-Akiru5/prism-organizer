"""Junk and temp file cleanup for Prism Organizer.

Detects and plans removal of:
- Word lock files (~$*.docx)
- Incomplete Chrome downloads (.crdownload)
- System junk (Thumbs.db, desktop.ini, .DS_Store)
- Empty directories (after organization)
- ZIP files where the extracted folder exists alongside
- Large installers likely already installed
"""


from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from prism_organizer.config import Config
from prism_organizer.scanner import FileInfo, ScanResult
from prism_organizer.utils import format_size, parse_size


@dataclass
class CleanupItem:
    """A single item to clean up."""
    path: Path
    reason: str           # Why this should be cleaned
    category: str         # Category: 'junk', 'temp', 'installer', 'empty_dir', 'zip_extracted'
    size: int = 0
    action: str = "delete"  # 'delete' or 'archive'
    

@dataclass
class CleanupPlan:
    """Plan for cleaning up files."""
    items: List[CleanupItem] = field(default_factory=list)
    
    @property
    def total_items(self) -> int:
        """Return the total number of items in the cleanup plan."""
        return len(self.items)
    
    @property
    def total_size(self) -> int:
        """Return the total size in bytes of all items in the cleanup plan."""
        return sum(item.size for item in self.items)
    
    @property
    def by_category(self) -> Dict[str, List[CleanupItem]]:
        """Group cleanup items by their category.

        Returns:
            Dictionary mapping category names to lists of CleanupItems.
        """
        groups: Dict[str, List[CleanupItem]] = {}
        for item in self.items:
            groups.setdefault(item.category, []).append(item)
        return groups


class Cleaner:
    """Detects and plans cleanup of junk/temp files.

    Examines scan results to identify files and directories that are
    candidates for removal or archival, including system junk files,
    temporary downloads, large installers, redundant archives, and
    empty directories.
    """

    def __init__(self, config: Config):
        self.config = config
        self._junk_patterns = config.junk_patterns
        self._installer_config = config.installer_detection

    def plan_cleanup(self, scan_result: ScanResult) -> CleanupPlan:
        """Create a cleanup plan for the scanned directory.

        Analyzes the scan results and builds a comprehensive plan covering
        junk/temp files, large installers, ZIP files with co-located
        extracted folders, and empty directories.

        Args:
            scan_result: Results from a directory scan.

        Returns:
            CleanupPlan with all items to clean.
        """
        plan = CleanupPlan()
        
        # 1. Junk/temp files
        for fi in scan_result.files:
            if fi.is_junk:
                plan.items.append(CleanupItem(
                    path=fi.path,
                    reason=f"Matches junk pattern",
                    category="junk",
                    size=fi.size,
                    action="delete",
                ))
        
        # 2. Large installers (likely already installed)
        if self._installer_config.get("enabled", True):
            min_size = parse_size(self._installer_config.get("min_size", "50MB"))
            inst_exts = set(self._installer_config.get("extensions", [".exe", ".msi"]))
            archive_path = self._installer_config.get("archive_path", "~/Archive/Installers/")
            action = self._installer_config.get("action", "suggest")
            
            for fi in scan_result.files:
                if (fi.extension.lower() in inst_exts 
                    and fi.size >= min_size 
                    and not fi.is_junk):
                    plan.items.append(CleanupItem(
                        path=fi.path,
                        reason=f"Large installer ({format_size(fi.size)}) - likely already installed",
                        category="installer",
                        size=fi.size,
                        action="archive" if action == "auto-archive" else "suggest",
                    ))
        
        # 3. ZIP files with extracted folder alongside
        self._detect_zip_extracted_pairs(scan_result, plan)
        
        # 4. Empty directories
        self._detect_empty_dirs(scan_result.target_dir, plan)
        
        return plan

    def _detect_zip_extracted_pairs(self, scan_result: ScanResult, plan: CleanupPlan) -> None:
        """Detect ZIP files where the extracted folder exists alongside.

        Checks each archive file (.zip, .rar, .7z, .tar) to see if a
        directory with the same stem name exists in the same parent
        directory, suggesting the archive has already been extracted.

        Args:
            scan_result: Results from a directory scan.
            plan: The cleanup plan to append detected items to.
        """
        # Build a set of directory names in the target
        dir_names: Set[str] = set()
        try:
            for item in scan_result.target_dir.iterdir():
                if item.is_dir():
                    dir_names.add(item.name.lower())
        except (OSError, PermissionError):
            return
        
        for fi in scan_result.files:
            if fi.extension.lower() in ('.zip', '.rar', '.7z', '.tar'):
                # Check if a folder with the same name (minus extension) exists
                stem = Path(fi.name).stem.lower()
                if stem in dir_names:
                    plan.items.append(CleanupItem(
                        path=fi.path,
                        reason=f"Archive with extracted folder '{Path(fi.name).stem}/' alongside",
                        category="zip_extracted",
                        size=fi.size,
                        action="suggest",  # Just suggest, don't auto-delete
                    ))

    def _detect_empty_dirs(self, target_dir: Path, plan: CleanupPlan) -> None:
        """Detect empty directories within the target directory tree.

        Recursively walks the target directory and flags any directories
        that contain no children (files or subdirectories). Permission
        errors are silently ignored.

        Args:
            target_dir: Root directory to search for empty subdirectories.
            plan: The cleanup plan to append detected items to.
        """
        try:
            for item in target_dir.rglob("*"):
                if item.is_dir():
                    try:
                        if not any(item.iterdir()):
                            plan.items.append(CleanupItem(
                                path=item,
                                reason="Empty directory",
                                category="empty_dir",
                                size=0,
                                action="delete",
                            ))
                    except (OSError, PermissionError):
                        pass
        except (OSError, PermissionError):
            pass

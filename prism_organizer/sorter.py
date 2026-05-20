"""File sorting engine for Prism Organizer.

Sorts files into organized directory structures by type or date.
Always generates a plan of operations first (for preview), then
executes only after confirmation.
"""

import os
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from prism_organizer.config import Config
from prism_organizer.scanner import FileInfo, ScanResult, Scanner
from prism_organizer.utils import expand_path, safe_filename


@dataclass
class SortOperation:
    """A single planned file move operation."""
    source: Path
    destination: Path
    file_info: FileInfo
    category: str  # Category or date bucket name


@dataclass
class SortPlan:
    """Complete plan for sorting files."""
    target_dir: Path
    sort_by: str  # 'type' or 'date'
    operations: List[SortOperation] = field(default_factory=list)
    skipped: List[FileInfo] = field(default_factory=list)  # Files in subdirs that are already sorted
    errors: List[str] = field(default_factory=list)
    
    @property
    def total_files(self) -> int:
        """Return the number of files to be moved."""
        return len(self.operations)
    
    @property
    def total_size(self) -> int:
        """Return the total size in bytes of files to be moved."""
        return sum(op.file_info.size for op in self.operations)
    
    @property
    def categories(self) -> Dict[str, List[SortOperation]]:
        """Group operations by category/bucket."""
        groups: Dict[str, List[SortOperation]] = {}
        for op in self.operations:
            groups.setdefault(op.category, []).append(op)
        return groups


class Sorter:
    """Sorts files by type or date.

    The sorter never moves files directly. Instead it produces a
    ``SortPlan`` describing every intended move so the caller can
    preview the changes (dry-run default) before committing.
    """

    def __init__(self, config: Config):
        self.config = config

    def plan_sort_by_type(self, scan_result: ScanResult,
                          skip_dirs: Optional[Set[Path]] = None) -> SortPlan:
        """Create a sort plan organizing files by their type/category.
        
        Files in the target directory root are moved into category subfolders.
        Files already in subdirectories are skipped (they may already be organized).
        
        Args:
            scan_result: Results from a directory scan.
            skip_dirs: Directories to skip.
        
        Returns:
            SortPlan with all planned operations.
        """
        plan = SortPlan(
            target_dir=scan_result.target_dir,
            sort_by="type",
        )
        skip_dirs = skip_dirs or set()
        
        for file_info in scan_result.files:
            # Only move files that are directly in the target directory (not subdirs)
            if file_info.path.parent != scan_result.target_dir:
                plan.skipped.append(file_info)
                continue
            
            # Skip junk files (handled by cleaner)
            if file_info.is_junk:
                continue
            
            # Determine category
            category = self.config.get_extension_category(file_info.extension)
            dest_dir = scan_result.target_dir / category
            dest_path = safe_filename(dest_dir, file_info.name)
            
            plan.operations.append(SortOperation(
                source=file_info.path,
                destination=dest_path,
                file_info=file_info,
                category=category,
            ))
        
        return plan

    def plan_sort_by_date(self, scan_result: ScanResult,
                          date_format: Optional[str] = None,
                          skip_dirs: Optional[Set[Path]] = None) -> SortPlan:
        """Create a sort plan organizing files by modification date.
        
        Files are moved into date-based subfolders (e.g., 2026/May/).
        
        Args:
            scan_result: Results from a directory scan.
            date_format: strftime format for folder structure. Default: '%Y/%B'
            skip_dirs: Directories to skip.
        
        Returns:
            SortPlan with all planned operations.
        """
        plan = SortPlan(
            target_dir=scan_result.target_dir,
            sort_by="date",
        )
        skip_dirs = skip_dirs or set()
        fmt = date_format or self.config.date_format
        
        for file_info in scan_result.files:
            if file_info.path.parent != scan_result.target_dir:
                plan.skipped.append(file_info)
                continue
            
            if file_info.is_junk:
                continue
            
            # Create date bucket
            date_bucket = file_info.modified.strftime(fmt)
            dest_dir = scan_result.target_dir / date_bucket
            dest_path = safe_filename(dest_dir, file_info.name)
            
            plan.operations.append(SortOperation(
                source=file_info.path,
                destination=dest_path,
                file_info=file_info,
                category=date_bucket,
            ))
        
        return plan

"""Duplicate file detection for Prism Organizer.

Three-phase detection for speed:
1. Size grouping - instant, eliminates ~90% of files
2. Partial hash - read first 8KB, eliminates ~99% of remaining
3. Full hash - SHA-256 only for final candidates
"""

import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from colorama import Fore, Style
from tqdm import tqdm

from prism_organizer.config import Config
from prism_organizer.scanner import FileInfo, ScanResult
from prism_organizer.utils import (
    format_size, parse_size,
    print_header, print_warning, print_info, print_success,
)


PARTIAL_HASH_SIZE = 8192  # 8KB for partial hashing


@dataclass
class DuplicateGroup:
    """A group of duplicate files.

    Stores all files that share the same content hash, along with metadata
    about the group such as file size and the computed keep/remove decisions
    based on the configured policy.

    Attributes:
        hash_value: The SHA-256 hash shared by all files in the group.
        files: List of FileInfo objects, sorted by keep policy (keeper first).
        file_size: Size of each file in bytes (identical across the group).
    """

    hash_value: str
    files: List[FileInfo] = field(default_factory=list)
    file_size: int = 0

    @property
    def count(self) -> int:
        """Return the total number of files in this duplicate group."""
        return len(self.files)

    @property
    def wasted_space(self) -> int:
        """Space that could be reclaimed (all but one copy).

        Returns:
            Total bytes reclaimable by removing duplicate copies.
        """
        return self.file_size * (self.count - 1)

    @property
    def keeper(self) -> Optional[FileInfo]:
        """The file to keep (first in list after sorting by policy).

        Returns:
            The FileInfo designated as the keeper, or None if the group
            is empty.
        """
        return self.files[0] if self.files else None

    @property
    def removable(self) -> List[FileInfo]:
        """Files that can be removed (all but the keeper).

        Returns:
            List of FileInfo objects that are candidates for removal.
        """
        return self.files[1:] if len(self.files) > 1 else []


@dataclass
class DuplicateResult:
    """Results of duplicate detection.

    Aggregates all duplicate groups found during a scan and provides
    summary statistics for reporting.

    Attributes:
        groups: List of DuplicateGroup instances, sorted by wasted space.
        total_files_checked: Number of files evaluated during detection.
        total_duplicates: Total number of duplicate copies (excluding keepers).
        total_wasted_space: Total bytes reclaimable across all groups.
    """

    groups: List[DuplicateGroup] = field(default_factory=list)
    total_files_checked: int = 0
    total_duplicates: int = 0
    total_wasted_space: int = 0

    @property
    def has_duplicates(self) -> bool:
        """Return True if any duplicate groups were found."""
        return len(self.groups) > 0


class DuplicateDetector:
    """Detects duplicate files using a 3-phase approach.

    The three phases progressively narrow the candidate set:

    1. **Size grouping** — Files with unique sizes cannot be duplicates.
       This eliminates the vast majority of files instantly.
    2. **Partial hash** — Read only the first 8 KB and compute a SHA-256
       digest.  Files that differ in their opening bytes are not duplicates.
    3. **Full hash** — Compute the SHA-256 digest over the entire file
       contents.  Only files that survive both prior phases are hashed
       fully, keeping I/O to a minimum.

    Args:
        config: The application Config instance, which supplies duplicate-
            detection settings (method, keep policy, minimum size).
    """

    def __init__(self, config: Config):
        self.config = config
        dup_config = config.duplicates_config
        self.method = dup_config.get("method", "hash")
        self.keep_policy = dup_config.get("keep", "oldest")
        self.min_size = parse_size(dup_config.get("min_size", "1MB"))

    def find_duplicates(self, scan_result: ScanResult) -> DuplicateResult:
        """Find duplicate files in scan results.

        Executes the three-phase detection pipeline and returns a
        ``DuplicateResult`` containing all discovered groups sorted by
        reclaimable space (largest first).

        Args:
            scan_result: Results from a directory scan.

        Returns:
            DuplicateResult with groups of duplicates.
        """
        result = DuplicateResult()

        # Phase 1: Group by file size
        print_info("Phase 1: Grouping by file size...")
        size_groups: Dict[int, List[FileInfo]] = {}
        for fi in scan_result.files:
            if fi.size < self.min_size:
                continue
            if fi.is_junk:
                continue
            size_groups.setdefault(fi.size, []).append(fi)
            result.total_files_checked += 1

        # Keep only groups with 2+ files
        candidates = {size: files for size, files in size_groups.items() if len(files) > 1}
        candidate_count = sum(len(f) for f in candidates.values())
        print_info(f"  {candidate_count} files in {len(candidates)} size groups")

        if not candidates:
            print_success("No duplicate candidates found.")
            return result

        # Phase 2: Partial hash (first 8KB)
        print_info("Phase 2: Partial hashing (first 8KB)...")
        partial_groups: Dict[str, List[FileInfo]] = {}

        all_candidates = [fi for files in candidates.values() for fi in files]
        for fi in tqdm(all_candidates, desc="  Partial hash", unit="file",
                       bar_format="  {l_bar}{bar:30}{r_bar}"):
            try:
                h = self._partial_hash(fi.path)
                key = f"{fi.size}:{h}"
                partial_groups.setdefault(key, []).append(fi)
            except (OSError, PermissionError):
                continue

        # Keep only groups with 2+ files
        partial_candidates = {k: v for k, v in partial_groups.items() if len(v) > 1}
        partial_count = sum(len(f) for f in partial_candidates.values())
        print_info(f"  {partial_count} files still match after partial hash")

        if not partial_candidates:
            print_success("No duplicates found after partial hashing.")
            return result

        # Phase 3: Full hash
        print_info("Phase 3: Full SHA-256 hashing...")
        full_groups: Dict[str, List[FileInfo]] = {}

        remaining = [fi for files in partial_candidates.values() for fi in files]
        for fi in tqdm(remaining, desc="  Full hash", unit="file",
                       bar_format="  {l_bar}{bar:30}{r_bar}"):
            try:
                h = self._full_hash(fi.path)
                full_groups.setdefault(h, []).append(fi)
            except (OSError, PermissionError):
                continue

        # Build final duplicate groups
        for hash_val, files in full_groups.items():
            if len(files) < 2:
                continue

            # Sort by keep policy
            sorted_files = self._sort_by_policy(files)

            group = DuplicateGroup(
                hash_value=hash_val,
                files=sorted_files,
                file_size=sorted_files[0].size,
            )
            result.groups.append(group)
            result.total_duplicates += group.count - 1
            result.total_wasted_space += group.wasted_space

        # Sort groups by wasted space (largest first)
        result.groups.sort(key=lambda g: g.wasted_space, reverse=True)

        return result

    def _sort_by_policy(self, files: List[FileInfo]) -> List[FileInfo]:
        """Sort files so the first one is the 'keeper' based on policy.

        The keeper is determined by the configured ``keep_policy``:

        - ``"newest"``  — keep the most recently modified file.
        - ``"largest"`` — keep the largest file (useful when sizes differ
          only due to filesystem block alignment, though in practice
          duplicates share the same size).
        - ``"oldest"``  — *(default)* keep the file with the earliest
          modification time, preserving the original.

        Args:
            files: Unsorted list of duplicate FileInfo objects.

        Returns:
            A new list with the keeper at index 0.
        """
        if self.keep_policy == "newest":
            return sorted(files, key=lambda f: f.modified, reverse=True)
        elif self.keep_policy == "largest":
            return sorted(files, key=lambda f: f.size, reverse=True)
        else:  # oldest (default)
            return sorted(files, key=lambda f: f.modified)

    @staticmethod
    def _partial_hash(filepath: Path) -> str:
        """Hash the first 8KB of a file.

        Args:
            filepath: Path to the file to partially hash.

        Returns:
            Hex-encoded SHA-256 digest of the first 8 KB.

        Raises:
            OSError: If the file cannot be read.
        """
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            data = f.read(PARTIAL_HASH_SIZE)
            hasher.update(data)
        return hasher.hexdigest()

    @staticmethod
    def _full_hash(filepath: Path) -> str:
        """Hash the entire file with SHA-256.

        Reads in 64 KB chunks to keep memory usage constant regardless
        of file size.

        Args:
            filepath: Path to the file to hash.

        Returns:
            Hex-encoded SHA-256 digest of the full file contents.

        Raises:
            OSError: If the file cannot be read.
        """
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while True:
                data = f.read(65536)  # 64KB chunks
                if not data:
                    break
                hasher.update(data)
        return hasher.hexdigest()

    def print_report(self, result: DuplicateResult) -> None:
        """Print a formatted duplicate report to the console.

        Displays summary statistics (group count, total duplicates,
        reclaimable space) followed by per-group detail showing which
        file is kept and which are duplicates.  Output is limited to the
        top 20 groups by wasted space to avoid overwhelming the terminal.

        Args:
            result: The DuplicateResult to report on.
        """
        print_header("DUPLICATE FILE REPORT")

        if not result.has_duplicates:
            print_success("No duplicate files found!")
            return

        print(f"\n  {Fore.WHITE}Duplicate groups:  {Fore.CYAN}{len(result.groups)}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Total duplicates:  {Fore.CYAN}{result.total_duplicates}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Reclaimable space: {Fore.YELLOW}{format_size(result.total_wasted_space)}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Keep policy:       {Fore.CYAN}{self.keep_policy}{Style.RESET_ALL}")

        for i, group in enumerate(result.groups[:20], 1):  # Show top 20 groups
            print(f"\n  {Fore.CYAN}── Group {i} ({group.count} copies, {format_size(group.file_size)} each) ──{Style.RESET_ALL}")
            for j, fi in enumerate(group.files):
                if j == 0:
                    print(f"    {Fore.GREEN}[KEEP] {fi.path}{Style.RESET_ALL}")
                else:
                    print(f"    {Fore.RED}[DUPE] {fi.path}{Style.RESET_ALL}")

        if len(result.groups) > 20:
            print(f"\n  {Fore.WHITE}... and {len(result.groups) - 20} more groups{Style.RESET_ALL}")

        print()

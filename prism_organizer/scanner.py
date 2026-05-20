"""Filesystem scanner and analyzer for Prism Organizer.

Scans directories and produces rich analysis reports including:
- File type breakdown (count and size per extension)
- Largest files (top 20)
- Duplicate candidates (same-size files)
- Age distribution
- Junk file detection
- UUID-named file detection
- Installer detection
"""

import os
import fnmatch
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from colorama import Fore, Style
from tqdm import tqdm

from prism_organizer.config import Config
from prism_organizer.utils import (
    format_size,
    is_uuid_filename,
    expand_path,
    parse_size,
    print_header,
    print_success,
    print_warning,
    print_info,
    print_error,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class FileInfo:
    """Information about a single file discovered during a scan.

    Attributes:
        path: Absolute path to the file.
        name: Filename component (stem + suffix).
        extension: Lowercased file extension including the leading dot,
            or empty string when no extension is present.
        size: File size in bytes.
        modified: Last-modified timestamp.
        created: Creation timestamp (``st_ctime`` on Windows).
        is_uuid_named: ``True`` when the stem looks like a UUID.
        is_junk: ``True`` when the name matches a configured junk pattern.
        is_installer: ``True`` when the file is a large installer/setup binary.
        category: Human-readable category derived from the extension map in
            the active :class:`Config`.
    """

    path: Path
    name: str
    extension: str
    size: int
    modified: datetime
    created: datetime
    is_uuid_named: bool = False
    is_junk: bool = False
    is_installer: bool = False
    category: str = "Misc"


@dataclass
class ScanResult:
    """Aggregated results of a directory scan.

    All per-key dictionaries (``by_extension``, ``by_category``, ``by_age``)
    use plain :class:`dict` instances with ``{"count": 0, "size": 0}`` values
    that are lazily initialised via :func:`_ensure_bucket` to avoid the
    pickling problems that ``defaultdict(lambda: …)`` would introduce.

    Attributes:
        target_dir: The root directory that was scanned.
        total_files: Number of files analysed successfully.
        total_size: Cumulative size of all analysed files in bytes.
        total_dirs: Number of subdirectories encountered.
        by_extension: ``{".ext": {"count": N, "size": N}}`` breakdown.
        by_category: ``{"Category": {"count": N, "size": N}}`` breakdown.
        largest_files: The 20 largest files, sorted descending by size.
        junk_files: Files whose names matched a junk pattern.
        uuid_files: Files whose stems look like UUIDs.
        installer_files: Files detected as large installers.
        size_groups: ``{size_in_bytes: [FileInfo, …]}`` — groups of files
            that share the same size (potential duplicate candidates).
        by_age: ``{"YYYY-MM": {"count": N, "size": N}}`` breakdown keyed
            by the file's last-modified month.
        files: Every :class:`FileInfo` collected during the scan.
        errors: Human-readable error strings for files that could not be
            accessed.
    """

    target_dir: Path
    total_files: int = 0
    total_size: int = 0
    total_dirs: int = 0

    # Breakdowns — plain dicts, lazily populated via _ensure_bucket
    by_extension: Dict[str, dict] = field(default_factory=dict)
    by_category: Dict[str, dict] = field(default_factory=dict)
    largest_files: List[FileInfo] = field(default_factory=list)

    # Special detections
    junk_files: List[FileInfo] = field(default_factory=list)
    uuid_files: List[FileInfo] = field(default_factory=list)
    installer_files: List[FileInfo] = field(default_factory=list)

    # Duplicate candidates (grouped by size)
    size_groups: Dict[int, List[FileInfo]] = field(default_factory=dict)

    # Age distribution
    by_age: Dict[str, dict] = field(default_factory=dict)

    # All files
    files: List[FileInfo] = field(default_factory=list)

    # Errors
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_bucket(mapping: dict, key) -> dict:
    """Return *mapping[key]*, creating a ``{"count": 0, "size": 0}`` entry
    if one does not already exist.

    This is a pickle-safe replacement for
    ``defaultdict(lambda: {"count": 0, "size": 0})``.
    """
    try:
        return mapping[key]
    except KeyError:
        bucket: dict = {"count": 0, "size": 0}
        mapping[key] = bucket
        return bucket


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


class Scanner:
    """Filesystem scanner and analyzer.

    The scanner walks a directory tree, collects metadata for every
    reachable file, and returns a :class:`ScanResult` containing
    aggregated statistics and special-file detections.

    Args:
        config: The active :class:`Config` instance that supplies junk
            patterns, installer-detection settings, and extension→category
            mappings.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self._junk_patterns: List[str] = config.junk_patterns
        self._installer_config: dict = config.installer_detection

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def scan(
        self,
        target: str,
        recursive: bool = True,
        skip_dirs: Optional[Set[Path]] = None,
    ) -> ScanResult:
        """Scan a directory and produce analysis results.

        The scan runs in two logical passes:

        1. **Discovery** — walk the tree (or list the directory) to build a
           flat list of file paths while respecting *skip_dirs*.
        2. **Analysis** — iterate over every discovered path with a
           :pypi:`tqdm` progress bar, ``stat()`` each file, classify it, and
           accumulate the results.

        Args:
            target: Directory path to scan.  Tildes and environment
                variables are expanded automatically.
            recursive: Whether to recurse into subdirectories.
            skip_dirs: Resolved :class:`Path` objects for directories that
                should be pruned from the walk (e.g. cloud-sync roots).

        Returns:
            A :class:`ScanResult` populated with the full analysis.

        Raises:
            FileNotFoundError: If *target* does not exist.
            NotADirectoryError: If *target* exists but is not a directory.
        """
        target_path = expand_path(target)
        if not target_path.exists():
            raise FileNotFoundError(f"Directory not found: {target_path}")
        if not target_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {target_path}")

        result = ScanResult(target_dir=target_path)
        skip_dirs = skip_dirs or set()

        # -- Pass 1: discover file paths -------------------------------- #
        print_info(f"Scanning {target_path}...")
        file_paths: List[Path] = []

        if recursive:
            for root, dirs, files in os.walk(target_path, topdown=True):
                root_path = Path(root)
                # Prune cloud drives, backup dirs, and our own metadata
                dirs[:] = [
                    d
                    for d in dirs
                    if (root_path / d).resolve() not in skip_dirs
                    and not d.startswith(".prism-organizer")
                ]
                result.total_dirs += len(dirs)
                for f in files:
                    file_paths.append(root_path / f)
        else:
            for item in target_path.iterdir():
                if item.is_file():
                    file_paths.append(item)
                elif item.is_dir():
                    result.total_dirs += 1

        # -- Precompute installer settings ------------------------------ #
        installer_enabled: bool = bool(self._installer_config.get("enabled"))
        installer_min_size: int = (
            parse_size(self._installer_config.get("min_size", "50MB"))
            if installer_enabled
            else 0
        )
        installer_exts: Set[str] = (
            set(self._installer_config.get("extensions", []))
            if installer_enabled
            else set()
        )

        # -- Pass 2: analyse each file --------------------------------- #
        for fpath in tqdm(
            file_paths,
            desc="  Analyzing files",
            unit="file",
            bar_format="  {l_bar}{bar:30}{r_bar}",
        ):
            try:
                stat = fpath.stat()
                ext = fpath.suffix.lower()

                file_info = FileInfo(
                    path=fpath,
                    name=fpath.name,
                    extension=ext,
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    created=datetime.fromtimestamp(stat.st_ctime),
                    is_uuid_named=is_uuid_filename(fpath.name),
                    is_junk=self._is_junk(fpath.name),
                    category=self.config.get_extension_category(ext),
                )

                # Installer detection
                if (
                    installer_enabled
                    and ext in installer_exts
                    and stat.st_size >= installer_min_size
                ):
                    file_info.is_installer = True
                    result.installer_files.append(file_info)

                # Totals
                result.total_files += 1
                result.total_size += stat.st_size

                # By extension
                ext_bucket = _ensure_bucket(result.by_extension, ext)
                ext_bucket["count"] += 1
                ext_bucket["size"] += stat.st_size

                # By category
                cat_bucket = _ensure_bucket(result.by_category, file_info.category)
                cat_bucket["count"] += 1
                cat_bucket["size"] += stat.st_size

                # Age bucket (YYYY-MM of last modification)
                age_key = file_info.modified.strftime("%Y-%m")
                age_bucket = _ensure_bucket(result.by_age, age_key)
                age_bucket["count"] += 1
                age_bucket["size"] += stat.st_size

                # Track for duplicate detection
                result.size_groups.setdefault(stat.st_size, []).append(file_info)

                # Special detections
                if file_info.is_junk:
                    result.junk_files.append(file_info)
                if file_info.is_uuid_named:
                    result.uuid_files.append(file_info)

                result.files.append(file_info)

            except (OSError, PermissionError) as e:
                result.errors.append(f"Could not access: {fpath} ({e})")

        # -- Post-processing ------------------------------------------- #
        result.largest_files = sorted(
            result.files, key=lambda f: f.size, reverse=True
        )[:20]

        return result

    # ------------------------------------------------------------------ #
    # Reporting
    # ------------------------------------------------------------------ #

    def print_report(self, result: ScanResult, verbose: bool = False) -> None:
        """Print a formatted scan report to the terminal.

        The report always includes:

        * High-level summary (file count, total size, directory count).
        * Category breakdown sorted by size descending.
        * Top 10 largest files.
        * Warnings / findings (duplicates, junk, UUID-named, installers).

        When *verbose* is ``True`` the report additionally shows the top 25
        file extensions by count.

        Args:
            result: A populated :class:`ScanResult` to render.
            verbose: Include the per-extension breakdown table.
        """
        print_header(f"SCAN REPORT: {result.target_dir}")

        # -- Summary --------------------------------------------------- #
        print(
            f"\n  {Fore.WHITE}Total files:  "
            f"{Fore.CYAN}{result.total_files:,}{Style.RESET_ALL}"
        )
        print(
            f"  {Fore.WHITE}Total size:   "
            f"{Fore.CYAN}{format_size(result.total_size)}{Style.RESET_ALL}"
        )
        print(
            f"  {Fore.WHITE}Directories:  "
            f"{Fore.CYAN}{result.total_dirs:,}{Style.RESET_ALL}"
        )

        # -- Category breakdown ---------------------------------------- #
        print(f"\n  {Fore.WHITE}{'─' * 50}")
        print(
            f"  {Fore.CYAN}{'Category':<20} {'Count':>8} {'Size':>12}"
            f"{Style.RESET_ALL}"
        )
        print(f"  {Fore.WHITE}{'─' * 50}")

        sorted_cats = sorted(
            result.by_category.items(),
            key=lambda x: x[1].get("size", 0),
            reverse=True,
        )
        for cat, info in sorted_cats:
            count = info.get("count", 0)
            size = info.get("size", 0)
            print(
                f"  {Fore.WHITE}{cat:<20} {count:>8,} "
                f"{format_size(size):>12}"
            )

        # -- Extension breakdown (verbose only) ------------------------ #
        if verbose:
            print(f"\n  {Fore.WHITE}{'─' * 50}")
            print(
                f"  {Fore.CYAN}{'Extension':<15} {'Count':>8} "
                f"{'Size':>12}{Style.RESET_ALL}"
            )
            print(f"  {Fore.WHITE}{'─' * 50}")

            sorted_exts = sorted(
                result.by_extension.items(),
                key=lambda x: x[1].get("count", 0),
                reverse=True,
            )[:25]
            for ext, info in sorted_exts:
                ext_display = ext if ext else "(none)"
                print(
                    f"  {Fore.WHITE}{ext_display:<15} "
                    f"{info.get('count', 0):>8,} "
                    f"{format_size(info.get('size', 0)):>12}"
                )

        # -- Largest files --------------------------------------------- #
        print(f"\n  {Fore.WHITE}{'─' * 50}")
        print(f"  {Fore.CYAN}Top 10 Largest Files{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}{'─' * 50}")

        for fi in result.largest_files[:10]:
            size_str = format_size(fi.size)
            name = fi.name[:40] + "..." if len(fi.name) > 40 else fi.name
            print(f"  {Fore.WHITE}{size_str:>12}  {name}")

        # -- Warnings / findings --------------------------------------- #
        warnings: List[str] = []

        # Duplicate candidates
        dupe_groups = {
            s: files
            for s, files in result.size_groups.items()
            if len(files) > 1 and s > 0
        }
        if dupe_groups:
            total_dupe_files = sum(
                len(files) - 1 for files in dupe_groups.values()
            )
            warnings.append(
                f"{total_dupe_files} potential duplicate files (same size) "
                f"across {len(dupe_groups)} groups"
            )

        if result.junk_files:
            junk_size = sum(f.size for f in result.junk_files)
            warnings.append(
                f"{len(result.junk_files)} junk/temp files "
                f"({format_size(junk_size)})"
            )

        if result.uuid_files:
            warnings.append(
                f"{len(result.uuid_files)} UUID-named files "
                f"(likely from social media/apps)"
            )

        if result.installer_files:
            inst_size = sum(f.size for f in result.installer_files)
            warnings.append(
                f"{len(result.installer_files)} large installers "
                f"({format_size(inst_size)}) — likely already installed"
            )

        if warnings:
            print(f"\n  {Fore.WHITE}{'─' * 50}")
            print(f"  {Fore.YELLOW}⚠  Findings{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}{'─' * 50}")
            for w in warnings:
                print_warning(w)

        # -- Errors ---------------------------------------------------- #
        if result.errors:
            print(
                f"\n  {Fore.RED}Errors: {len(result.errors)} files could "
                f"not be accessed{Style.RESET_ALL}"
            )
            if verbose:
                for err in result.errors[:10]:
                    print_error(err)

        print()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _is_junk(self, filename: str) -> bool:
        """Check if *filename* matches any configured junk pattern.

        Patterns are evaluated with :func:`fnmatch.fnmatch` (case-
        insensitive on Windows).

        Args:
            filename: The bare filename (no directory components).

        Returns:
            ``True`` if the name matches at least one junk pattern.
        """
        for pattern in self._junk_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False

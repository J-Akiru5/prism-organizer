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
from concurrent.futures import ThreadPoolExecutor, as_completed

from prism_organizer.display import display_progress

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
        workers: Optional[int] = None,
    ) -> ScanResult:
        """Scan a directory and produce analysis results.

        The scan runs in two logical passes:

        1. **Discovery** — walk the tree (or list the directory) to build a
           flat list of file paths while respecting *skip_dirs*.
        2. **Analysis** — analyse files in parallel using a thread pool
           with a Rich progress bar.

        Args:
            target: Directory path to scan.  Tildes and environment
                variables are expanded automatically.
            recursive: Whether to recurse into subdirectories.
            skip_dirs: Resolved :class:`Path` objects for directories that
                should be pruned from the walk (e.g. cloud-sync roots).
            workers: Number of worker threads. Defaults to
                ``min(32, os.cpu_count() + 4)``.

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

        # -- Pass 2: analyse each file (parallel) ----------------------- #
        if workers is None:
            workers = min(32, (os.cpu_count() or 1) + 4)

        file_infos: List[FileInfo] = []
        error_list: List[str] = []

        if workers > 1 and len(file_paths) > 100:
            # Parallel analysis for large sets
            chunk_size = max(1, len(file_paths) // workers)
            chunks = [
                file_paths[i : i + chunk_size]
                for i in range(0, len(file_paths), chunk_size)
            ]

            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(
                        self._analyze_chunk, chunk,
                        installer_enabled, installer_min_size, installer_exts,
                    ): chunk
                    for chunk in chunks
                }
                for future in display_progress(
                    as_completed(futures),
                    total=len(futures),
                    desc="Analyzing files",
                ):
                    try:
                        chunk_infos, chunk_errors = future.result()
                        file_infos.extend(chunk_infos)
                        error_list.extend(chunk_errors)
                    except Exception as e:
                        error_list.append(f"Chunk analysis failed: {e}")
        else:
            # Sequential for small sets
            for fpath in display_progress(
                file_paths,
                desc="Analyzing files",
            ):
                fi, err = self._analyze_one(
                    fpath, installer_enabled, installer_min_size, installer_exts,
                )
                if fi:
                    file_infos.append(fi)
                if err:
                    error_list.append(err)

        # -- Merge results ---------------------------------------------- #
        result.errors = error_list

        for fi in file_infos:
            result.total_files += 1
            result.total_size += fi.size

            ext_bucket = _ensure_bucket(result.by_extension, fi.extension)
            ext_bucket["count"] += 1
            ext_bucket["size"] += fi.size

            cat_bucket = _ensure_bucket(result.by_category, fi.category)
            cat_bucket["count"] += 1
            cat_bucket["size"] += fi.size

            age_key = fi.modified.strftime("%Y-%m")
            age_bucket = _ensure_bucket(result.by_age, age_key)
            age_bucket["count"] += 1
            age_bucket["size"] += fi.size

            result.size_groups.setdefault(fi.size, []).append(fi)

            if fi.is_junk:
                result.junk_files.append(fi)
            if fi.is_uuid_named:
                result.uuid_files.append(fi)
            if fi.is_installer:
                result.installer_files.append(fi)

            result.files.append(fi)

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

        Uses Rich tables when the ``rich`` library is installed, falling
        back to colorama-formatted output otherwise.
        """
        from prism_organizer.display import (
            display_header, display_success, display_warning, display_error,
            display_info, display_table, display_findings,
            display_scan_summary, display_category_table, display_top_files,
        )

        display_header(f"SCAN REPORT: {result.target_dir}")

        display_scan_summary(
            result.target_dir,
            result.total_files,
            result.total_size,
            result.total_dirs,
        )

        display_category_table(result.by_category)

        if verbose:
            sorted_exts = sorted(
                result.by_extension.items(),
                key=lambda x: x[1].get("count", 0),
                reverse=True,
            )[:25]
            display_table(
                title="Extension Breakdown (Top 25)",
                columns=[
                    {"header": "Extension", "width": 15},
                    {"header": "Count", "justify": "right", "width": 10},
                    {"header": "Size", "justify": "right", "width": 14},
                ],
                rows=[
                    (ext if ext else "(none)",
                     f"{info.get('count', 0):,}",
                     format_size(info.get("size", 0)))
                    for ext, info in sorted_exts
                ],
            )

        display_top_files(result.largest_files, limit=10)

        # Warnings / findings
        warnings: List[str] = []
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

        display_findings(warnings)

        if result.errors:
            display_error(
                f"{len(result.errors)} files could not be accessed"
            )
            if verbose:
                for err in result.errors[:10]:
                    display_error(err)

        if not warnings and not result.errors:
            print()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _analyze_one(
        self,
        fpath: Path,
        installer_enabled: bool,
        installer_min_size: int,
        installer_exts: Set[str],
    ) -> Tuple[Optional[FileInfo], Optional[str]]:
        """Analyse a single file and return a FileInfo or error.

        Args:
            fpath: Absolute path to the file.
            installer_enabled: Whether installer detection is active.
            installer_min_size: Minimum size in bytes for installer detection.
            installer_exts: Set of extensions that trigger installer detection.

        Returns:
            Tuple of ``(file_info, error_string)``.  Exactly one will
            be *None* for each call.
        """
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

            if (
                installer_enabled
                and ext in installer_exts
                and stat.st_size >= installer_min_size
            ):
                file_info.is_installer = True

            return file_info, None
        except (OSError, PermissionError) as e:
            return None, f"Could not access: {fpath} ({e})"

    def _analyze_chunk(
        self,
        chunk: List[Path],
        installer_enabled: bool,
        installer_min_size: int,
        installer_exts: Set[str],
    ) -> Tuple[List[FileInfo], List[str]]:
        """Analyse a chunk of file paths (called from worker threads).

        Args:
            chunk: List of file paths to analyse.
            installer_enabled: Whether installer detection is active.
            installer_min_size: Minimum size in bytes for installer detection.
            installer_exts: Set of extensions that trigger installer detection.

        Returns:
            Tuple of ``(file_infos, errors)`` for this chunk.
        """
        infos: List[FileInfo] = []
        errs: List[str] = []
        for fpath in chunk:
            fi, err = self._analyze_one(
                fpath, installer_enabled, installer_min_size, installer_exts,
            )
            if fi:
                infos.append(fi)
            if err:
                errs.append(err)
        return infos, errs

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

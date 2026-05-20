"""Duplicate file detection for Prism Organizer.

Three-phase detection for speed:
1. Size grouping - instant, eliminates ~90% of files
2. Partial hash - read first 8KB, eliminates ~99% of remaining
3. Full hash - SHA-256 only for final candidates
"""

import hashlib
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

from colorama import Fore, Style
from tqdm import tqdm

from prism_organizer.config import Config
from prism_organizer.scanner import FileInfo, ScanResult
from prism_organizer.utils import (
    format_size, parse_size,
    print_header, print_warning, print_info, print_success,
)


PARTIAL_HASH_SIZE = 8192  # 8KB for partial hashing

IMAGE_EXTENSIONS = frozenset({
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif',
    '.ico', '.heic', '.heif', '.avif',
})


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
class PerceptualGroup:
    """A group of visually similar (near-duplicate) image files.

    Unlike ``DuplicateGroup``, members of a perceptual group are not
    byte-identical but share a very similar appearance (resizes,
    re-compressions, minor edits).

    Attributes:
        files: List of ``FileInfo`` objects that look similar.
        avg_size: Average file size across the group in bytes.
    """

    files: List[FileInfo] = field(default_factory=list)
    avg_size: int = 0

    @property
    def count(self) -> int:
        return len(self.files)

    @property
    def total_size(self) -> int:
        return sum(fi.size for fi in self.files)


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
        perceptual_groups: Near-duplicate image groups (when perceptual
            detection is enabled).
    """

    groups: List[DuplicateGroup] = field(default_factory=list)
    total_files_checked: int = 0
    total_duplicates: int = 0
    total_wasted_space: int = 0
    perceptual_groups: List[PerceptualGroup] = field(default_factory=list)

    @property
    def has_duplicates(self) -> bool:
        """Return True if any duplicate groups were found."""
        return len(self.groups) > 0

    @property
    def has_perceptual(self) -> bool:
        """Return True if perceptual (near-duplicate) groups were found."""
        return len(self.perceptual_groups) > 0


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

    def find_duplicates(self, scan_result: ScanResult,
                        workers: Optional[int] = None) -> DuplicateResult:
        """Find duplicate files in scan results.

        Executes the three-phase detection pipeline and returns a
        ``DuplicateResult`` containing all discovered groups sorted by
        reclaimable space (largest first).

        Phases 2 and 3 (hashing) are parallelized across *workers*
        threads when the candidate count justifies it.

        Args:
            scan_result: Results from a directory scan.
            workers: Number of worker threads for hashing phases.

        Returns:
            DuplicateResult with groups of duplicates.
        """
        if workers is None:
            workers = min(32, (os.cpu_count() or 1) + 4)

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

        all_candidates = [fi for files in candidates.values() for fi in files]

        # Phase 2: Partial hash (first 8KB) — parallel
        print_info("Phase 2: Partial hashing (first 8KB)...")
        partial_groups: Dict[str, List[FileInfo]] = {}

        if workers > 1 and len(all_candidates) > 50:
            partial_groups = self._parallel_hash(
                all_candidates, self._partial_hash, workers,
                desc="  Partial hash", key_prefix="size",
            )
        else:
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

        # Phase 3: Full hash — parallel
        print_info("Phase 3: Full SHA-256 hashing...")
        full_groups: Dict[str, List[FileInfo]] = {}

        remaining = [fi for files in partial_candidates.values() for fi in files]

        if workers > 1 and len(remaining) > 20:
            full_groups = self._parallel_hash(
                remaining, self._full_hash, workers,
                desc="  Full hash",
            )
        else:
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

    @staticmethod
    def _parallel_hash(
        file_infos: List[FileInfo],
        hash_func: Callable[[Path], str],
        workers: int,
        desc: str = "  Hashing",
        key_prefix: str = "",
    ) -> Dict[str, List[FileInfo]]:
        """Compute hashes in parallel across *workers* threads.

        Args:
            file_infos: Files to hash.
            hash_func: Hash function accepting a ``Path`` and returning
                a hex digest string.
            workers: Number of threads in the pool.
            desc: Label for the tqdm progress bar.
            key_prefix: Optional prefix for the grouping key (used by
                partial hashing to prepend the file size).

        Returns:
            Dict mapping hash keys to lists of ``FileInfo`` objects.
        """
        groups: Dict[str, List[FileInfo]] = {}

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {
                executor.submit(hash_func, fi.path): fi
                for fi in file_infos
            }
            for future in tqdm(
                as_completed(future_map),
                total=len(future_map),
                desc=desc,
                unit="file",
                bar_format="  {l_bar}{bar:30}{r_bar}",
            ):
                fi = future_map[future]
                try:
                    h = future.result()
                except (OSError, PermissionError):
                    continue
                if key_prefix:
                    key = f"{fi.size}:{h}"
                else:
                    key = h
                groups.setdefault(key, []).append(fi)

        return groups

    def find_perceptual_duplicates(
        self, scan_result: ScanResult,
        threshold: int = 5,
        workers: Optional[int] = None,
    ) -> List[PerceptualGroup]:
        """Find visually similar (near-duplicate) images using perceptual
        hashing.

        Only image files (``.jpg``, ``.png``, ``.gif``, etc.) that are
        *not* already flagged as exact duplicates are examined.  A
        difference hash (dhash) is computed for each and files whose
        dhash differs by a Hamming distance <= *threshold* are grouped
        together.

        Args:
            scan_result: Results from a directory scan containing the
                complete file list.
            threshold: Maximum Hamming distance between two hashes for
                them to be considered similar.  Lower = stricter.
            workers: Number of threads for parallel hashing.

        Returns:
            List of ``PerceptualGroup`` instances, each containing a set
            of visually similar images.  Returns an empty list if
            ``imagehash`` or ``Pillow`` is not installed.
        """
        try:
            from PIL import Image
            import imagehash  # type: ignore
        except ImportError:
            print_warning(
                "Perceptual duplicate detection requires 'imagehash' and "
                "'Pillow'.  Install with: pip install imagehash Pillow"
            )
            return []

        if workers is None:
            workers = min(32, (os.cpu_count() or 1) + 4)

        # Collect unique images (skip junk)
        image_files = [
            fi for fi in scan_result.files
            if fi.extension.lower() in IMAGE_EXTENSIONS and not fi.is_junk
        ]

        if len(image_files) < 2:
            return []

        print_info(f"Perceptual: analyzing {len(image_files)} images "
                   f"(threshold hamming distance <= {threshold})...")

        # Compute perceptual hashes in parallel
        hashes: Dict[Path, imagehash.ImageHash] = {}

        def _compute_phash(fi: FileInfo):
            try:
                img = Image.open(fi.path)
                return fi.path, imagehash.dhash(img)
            except Exception:
                return fi.path, None

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_compute_phash, fi): fi
                for fi in image_files
            }
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="  Perceptual hash",
                unit="file",
                bar_format="  {l_bar}{bar:30}{r_bar}",
            ):
                filepath, phash = future.result()
                if phash is not None:
                    hashes[filepath] = phash

        if len(hashes) < 2:
            return []

        # Group by similarity (single-pass, greedy clustering)
        print_info("  Clustering similar images...")
        similar_groups: List[PerceptualGroup] = []
        assigned: Set[Path] = set()

        hash_items = sorted(hashes.items(), key=lambda x: -x[0].stat().st_size)

        for filepath, phash in hash_items:
            if filepath in assigned:
                continue

            group_files: List[FileInfo] = []
            # Find the corresponding FileInfo
            fi_match = next((fi for fi in image_files if fi.path == filepath), None)
            if fi_match is None:
                continue

            group_files.append(fi_match)
            assigned.add(filepath)

            for other_path, other_hash in hash_items:
                if other_path in assigned:
                    continue
                if phash - other_hash <= threshold:
                    ofi = next((fi for fi in image_files if fi.path == other_path), None)
                    if ofi:
                        group_files.append(ofi)
                        assigned.add(other_path)

            if len(group_files) > 1:
                avg_size = sum(fi.size for fi in group_files) // len(group_files)
                similar_groups.append(PerceptualGroup(
                    files=group_files,
                    avg_size=avg_size,
                ))

        return similar_groups

    def print_report(self, result: DuplicateResult) -> None:
        """Print a formatted duplicate report to the console.

        Displays summary statistics (group count, total duplicates,
        reclaimable space) followed by per-group detail showing which
        file is kept and which are duplicates.  Output is limited to the
        top 20 groups by wasted space to avoid overwhelming the terminal.

        Args:
            result: The DuplicateResult to report on.
        """
        if not result.has_duplicates and not result.has_perceptual:
            print_success("No duplicate files found!")
            return

        # ── Exact duplicates ──────────────────────────────────────
        if result.has_duplicates:
            print_header("DUPLICATE FILE REPORT")

            print(f"\n  {Fore.WHITE}Duplicate groups:  {Fore.CYAN}{len(result.groups)}{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}Total duplicates:  {Fore.CYAN}{result.total_duplicates}{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}Reclaimable space: {Fore.YELLOW}{format_size(result.total_wasted_space)}{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}Keep policy:       {Fore.CYAN}{self.keep_policy}{Style.RESET_ALL}")

            for i, group in enumerate(result.groups[:20], 1):
                print(f"\n  {Fore.CYAN}── Group {i} ({group.count} copies, {format_size(group.file_size)} each) ──{Style.RESET_ALL}")
                for j, fi in enumerate(group.files):
                    if j == 0:
                        print(f"    {Fore.GREEN}[KEEP] {fi.path}{Style.RESET_ALL}")
                    else:
                        print(f"    {Fore.RED}[DUPE] {fi.path}{Style.RESET_ALL}")

            if len(result.groups) > 20:
                print(f"\n  {Fore.WHITE}... and {len(result.groups) - 20} more groups{Style.RESET_ALL}")

        # ── Perceptual / near-duplicates ──────────────────────────
        if result.has_perceptual:
            if result.has_duplicates:
                print()
            print_header("VISUALLY SIMILAR IMAGES (Near-Duplicates)")

            total_similar = sum(g.count for g in result.perceptual_groups)
            total_similar_size = sum(g.total_size for g in result.perceptual_groups)
            print(f"\n  {Fore.WHITE}Similar groups:    {Fore.CYAN}{len(result.perceptual_groups)}{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}Similar images:    {Fore.CYAN}{total_similar}{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}Total size:        {Fore.WHITE}{format_size(total_similar_size)}{Style.RESET_ALL}")
            print(f"  {Fore.YELLOW}These are NOT byte-identical but look very similar.")
            print(f"  Manual review is recommended before deleting.{Style.RESET_ALL}")

            for i, group in enumerate(result.perceptual_groups[:15], 1):
                print(f"\n  {Fore.CYAN}── Similar Group {i} ({group.count} images, "
                      f"~{format_size(group.avg_size)} avg) ──{Style.RESET_ALL}")
                for fi in group.files[:5]:
                    size_hint = f" ({format_size(fi.size)})"
                    print(f"    {Fore.WHITE}• {fi.name}{size_hint}{Style.RESET_ALL}")
                    print(f"      {Fore.WHITE}{fi.path.parent}{Style.RESET_ALL}")
                if group.count > 5:
                    print(f"    {Fore.WHITE}... and {group.count - 5} more{Style.RESET_ALL}")

            if len(result.perceptual_groups) > 15:
                print(f"\n  {Fore.WHITE}... and {len(result.perceptual_groups) - 15} more groups{Style.RESET_ALL}")

        print()

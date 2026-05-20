"""Tests for the duplicates module."""

import pytest
from pathlib import Path

from prism_organizer.config import Config, DEFAULT_CONFIG
from prism_organizer.scanner import Scanner
from prism_organizer.duplicates import DuplicateDetector


def _make_config(min_size="100"):
    config = Config.__new__(Config)
    data = dict(DEFAULT_CONFIG)
    data["duplicates"] = dict(data["duplicates"])
    data["duplicates"]["min_size"] = min_size
    config._data = data
    config._config_path = Path("/nonexistent")
    return config


@pytest.fixture
def dupes_dir(tmp_path):
    """Directory with duplicate files."""
    content_a = b"This is the same content exactly" * 100  # ~3.1KB
    content_b = b"This is different content entirely" * 100

    (tmp_path / "original.txt").write_bytes(content_a)
    (tmp_path / "copy1.txt").write_bytes(content_a)       # Duplicate
    (tmp_path / "copy2.txt").write_bytes(content_a)       # Duplicate
    (tmp_path / "unique.txt").write_bytes(content_b)      # Not a duplicate
    (tmp_path / "small.txt").write_bytes(b"tiny")          # Too small

    return tmp_path


def test_find_duplicates(dupes_dir):
    config = _make_config(min_size="100")
    scanner = Scanner(config)
    result = scanner.scan(str(dupes_dir), recursive=True)

    detector = DuplicateDetector(config)
    dupes = detector.find_duplicates(result)

    assert dupes.has_duplicates
    assert len(dupes.groups) >= 1

    # Find the group with 3 copies
    big_group = [g for g in dupes.groups if g.count == 3]
    assert len(big_group) == 1
    assert big_group[0].wasted_space > 0


def test_no_duplicates(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"unique_a" * 100)
    (tmp_path / "b.txt").write_bytes(b"unique_b" * 100)

    config = _make_config(min_size="100")
    scanner = Scanner(config)
    result = scanner.scan(str(tmp_path), recursive=True)

    detector = DuplicateDetector(config)
    dupes = detector.find_duplicates(result)

    assert not dupes.has_duplicates


def test_keep_policy_oldest(dupes_dir):
    config = _make_config(min_size="100")
    scanner = Scanner(config)
    result = scanner.scan(str(dupes_dir), recursive=True)

    detector = DuplicateDetector(config)
    dupes = detector.find_duplicates(result)

    for group in dupes.groups:
        keeper = group.keeper
        for other in group.removable:
            assert keeper.modified <= other.modified or keeper.modified == other.modified


def test_min_size_filter(tmp_path):
    """Files smaller than min_size should be ignored."""
    content = b"same" * 10  # 40 bytes
    (tmp_path / "a.txt").write_bytes(content)
    (tmp_path / "b.txt").write_bytes(content)

    config = _make_config(min_size="1MB")  # 1MB min
    scanner = Scanner(config)
    result = scanner.scan(str(tmp_path), recursive=True)

    detector = DuplicateDetector(config)
    dupes = detector.find_duplicates(result)

    assert not dupes.has_duplicates  # Too small to check

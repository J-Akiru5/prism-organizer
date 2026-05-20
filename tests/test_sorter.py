"""Tests for the sorter module."""

import pytest
from pathlib import Path

from prism_organizer.config import Config, DEFAULT_CONFIG
from prism_organizer.scanner import Scanner
from prism_organizer.sorter import Sorter


def _make_config():
    config = Config.__new__(Config)
    config._data = dict(DEFAULT_CONFIG)
    config._config_path = Path("/nonexistent")
    return config


@pytest.fixture
def mixed_dir(tmp_path):
    """Directory with mixed file types."""
    (tmp_path / "photo.jpg").write_bytes(b"x" * 100)
    (tmp_path / "report.pdf").write_bytes(b"y" * 200)
    (tmp_path / "song.mp3").write_bytes(b"z" * 150)
    (tmp_path / "data.csv").write_bytes(b"d" * 80)
    (tmp_path / "script.py").write_bytes(b"p" * 50)
    return tmp_path


def test_sort_by_type_plan(mixed_dir):
    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(mixed_dir), recursive=False)

    sorter = Sorter(config)
    plan = sorter.plan_sort_by_type(result)

    assert plan.total_files == 5
    categories = plan.categories
    assert "Images" in categories
    assert "Documents" in categories
    assert "Audio" in categories


def test_sort_by_type_destinations(mixed_dir):
    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(mixed_dir), recursive=False)

    sorter = Sorter(config)
    plan = sorter.plan_sort_by_type(result)

    for op in plan.operations:
        assert op.destination.parent.name == op.category
        assert op.destination.parent.parent == mixed_dir


def test_sort_by_date_plan(mixed_dir):
    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(mixed_dir), recursive=False)

    sorter = Sorter(config)
    plan = sorter.plan_sort_by_date(result)

    assert plan.total_files == 5
    assert plan.sort_by == "date"


def test_sort_skips_subdirectory_files(mixed_dir):
    """Files in subdirectories should be skipped."""
    subdir = mixed_dir / "existing_folder"
    subdir.mkdir()
    (subdir / "nested.txt").write_bytes(b"n" * 50)

    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(mixed_dir), recursive=True)

    sorter = Sorter(config)
    plan = sorter.plan_sort_by_type(result)

    sorted_names = [op.file_info.name for op in plan.operations]
    assert "nested.txt" not in sorted_names


def test_sort_skips_junk(mixed_dir):
    (mixed_dir / "~$temp.docx").write_bytes(b"t" * 50)

    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(mixed_dir), recursive=False)

    sorter = Sorter(config)
    plan = sorter.plan_sort_by_type(result)

    sorted_names = [op.file_info.name for op in plan.operations]
    assert "~$temp.docx" not in sorted_names

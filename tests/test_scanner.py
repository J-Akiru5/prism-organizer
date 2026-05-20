"""Tests for the scanner module."""

import pytest
from pathlib import Path

from prism_organizer.config import Config, DEFAULT_CONFIG
from prism_organizer.scanner import Scanner


def _make_config():
    config = Config.__new__(Config)
    config._data = dict(DEFAULT_CONFIG)
    config._config_path = Path("/nonexistent")
    return config


@pytest.fixture
def test_dir(tmp_path):
    """Create a test directory with various files."""
    (tmp_path / "photo.jpg").write_bytes(b"x" * 1024)
    (tmp_path / "document.pdf").write_bytes(b"y" * 2048)
    (tmp_path / "spreadsheet.xlsx").write_bytes(b"z" * 512)
    (tmp_path / "video.mp4").write_bytes(b"v" * 4096)
    (tmp_path / "installer.exe").write_bytes(b"i" * (60 * 1024 * 1024))  # 60MB
    (tmp_path / "~$temp.docx").write_bytes(b"t" * 100)  # Junk
    (tmp_path / "Thumbs.db").write_bytes(b"" * 50)  # Junk
    (tmp_path / "008a644c-098c-47be-905c-38e6a982d2da.jpg").write_bytes(b"u" * 500)  # UUID

    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "nested.txt").write_bytes(b"n" * 256)

    return tmp_path


def test_scan_counts_files(test_dir):
    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(test_dir), recursive=True)

    assert result.total_files == 9  # 8 in root + 1 in subdir
    assert result.total_size > 0


def test_scan_detects_junk(test_dir):
    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(test_dir), recursive=True)

    junk_names = [f.name for f in result.junk_files]
    assert "~$temp.docx" in junk_names
    assert "Thumbs.db" in junk_names


def test_scan_detects_uuid_files(test_dir):
    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(test_dir), recursive=True)

    uuid_names = [f.name for f in result.uuid_files]
    assert "008a644c-098c-47be-905c-38e6a982d2da.jpg" in uuid_names


def test_scan_detects_installers(test_dir):
    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(test_dir), recursive=True)

    installer_names = [f.name for f in result.installer_files]
    assert "installer.exe" in installer_names


def test_scan_nonexistent_dir():
    config = _make_config()
    scanner = Scanner(config)
    with pytest.raises(FileNotFoundError):
        scanner.scan("/totally/fake/path")


def test_scan_categories(test_dir):
    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(test_dir), recursive=True)

    assert "Images" in result.by_category
    assert "Documents" in result.by_category


def test_scan_largest_files(test_dir):
    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(test_dir), recursive=True)

    assert len(result.largest_files) > 0
    # The installer (60MB) should be the largest
    assert result.largest_files[0].name == "installer.exe"

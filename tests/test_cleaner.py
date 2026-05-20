"""Tests for the cleaner module."""

import pytest
from pathlib import Path

from prism_organizer.config import Config, DEFAULT_CONFIG
from prism_organizer.scanner import Scanner
from prism_organizer.cleaner import Cleaner


def _make_config():
    config = Config.__new__(Config)
    config._data = dict(DEFAULT_CONFIG)
    config._config_path = Path("/nonexistent")
    return config


@pytest.fixture
def messy_dir(tmp_path):
    (tmp_path / "~$document.docx").write_bytes(b"t" * 100)
    (tmp_path / "download.crdownload").write_bytes(b"c" * 5000)
    (tmp_path / "Thumbs.db").write_bytes(b"" * 50)
    (tmp_path / "normal.txt").write_bytes(b"n" * 200)
    (tmp_path / "big_setup.exe").write_bytes(b"e" * (60 * 1024 * 1024))  # 60MB

    # ZIP with matching extracted folder
    archive_name = "project_files"
    (tmp_path / f"{archive_name}.zip").write_bytes(b"z" * 1000)
    extracted = tmp_path / archive_name
    extracted.mkdir()
    (extracted / "file.txt").write_bytes(b"f" * 50)

    # Empty directory
    empty = tmp_path / "empty_folder"
    empty.mkdir()

    return tmp_path


def test_detects_junk_files(messy_dir):
    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(messy_dir), recursive=True)

    cleaner = Cleaner(config)
    plan = cleaner.plan_cleanup(result)

    junk_paths = [item.path.name for item in plan.items if item.category == "junk"]
    assert "~$document.docx" in junk_paths
    assert "download.crdownload" in junk_paths
    assert "Thumbs.db" in junk_paths


def test_detects_installers(messy_dir):
    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(messy_dir), recursive=True)

    cleaner = Cleaner(config)
    plan = cleaner.plan_cleanup(result)

    installer_items = [item for item in plan.items if item.category == "installer"]
    assert len(installer_items) == 1
    assert installer_items[0].path.name == "big_setup.exe"


def test_detects_zip_extracted_pairs(messy_dir):
    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(messy_dir), recursive=False)

    cleaner = Cleaner(config)
    plan = cleaner.plan_cleanup(result)

    zip_items = [item for item in plan.items if item.category == "zip_extracted"]
    assert len(zip_items) == 1
    assert zip_items[0].path.name == "project_files.zip"


def test_detects_empty_dirs(messy_dir):
    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(messy_dir), recursive=True)

    cleaner = Cleaner(config)
    plan = cleaner.plan_cleanup(result)

    empty_items = [item for item in plan.items if item.category == "empty_dir"]
    assert len(empty_items) == 1
    assert "empty_folder" in str(empty_items[0].path)


def test_normal_files_not_cleaned(messy_dir):
    config = _make_config()
    scanner = Scanner(config)
    result = scanner.scan(str(messy_dir), recursive=True)

    cleaner = Cleaner(config)
    plan = cleaner.plan_cleanup(result)

    cleaned_names = [item.path.name for item in plan.items]
    assert "normal.txt" not in cleaned_names

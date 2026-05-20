"""Tests for the cloud drives module."""

import pytest
from pathlib import Path

from prism_organizer.config import Config, DEFAULT_CONFIG
from prism_organizer.cloud_drives import CloudDriveDetector, DetectedDrive


def _make_config():
    config = Config.__new__(Config)
    config._data = dict(DEFAULT_CONFIG)
    config._config_path = Path("/nonexistent")
    return config


def test_detected_drive_defaults():
    drive = DetectedDrive(
        name="OneDrive",
        path=Path("C:/Users/test/OneDrive"),
    )
    assert drive.skip is True
    assert drive.detection_method == "known_path"


def test_skip_set_to_skip():
    drives = [
        DetectedDrive(name="OneDrive", path=Path("/a")),
        DetectedDrive(name="Dropbox", path=Path("/b")),
    ]
    skip_paths = {d.path for d in drives if d.skip}
    assert len(skip_paths) == 2


def test_include_all():
    drives = [
        DetectedDrive(name="OneDrive", path=Path("/a")),
        DetectedDrive(name="Dropbox", path=Path("/b")),
    ]
    for d in drives:
        d.skip = False

    skip_paths = {d.path for d in drives if d.skip}
    assert len(skip_paths) == 0


def test_detector_init():
    config = _make_config()
    detector = CloudDriveDetector(config)
    assert detector.config is config


def test_detected_drive_path_resolve():
    """Paths should be stored as-is in DetectedDrive."""
    path = Path("C:/Users/test/Google Drive")
    drive = DetectedDrive(name="Google Drive", path=path)
    assert drive.path == path
    assert drive.name == "Google Drive"

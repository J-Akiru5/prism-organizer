"""Tests for the auto-update checker module."""

import os
import sys
import time
from pathlib import Path
from unittest import mock

import pytest

from prism_organizer import __version__
from prism_organizer.updater import (
    get_install_method,
    parse_version,
    is_newer_version,
    check_for_updates,
    TIMESTAMP_FILE,
)


def test_parse_version():
    assert parse_version("1.2.3") == (1, 2, 3)
    assert parse_version("1.2.16-rc1") == (1, 2, 16)
    assert parse_version("invalid") == (0, 0, 0)
    assert parse_version("") == (0, 0, 0)


def test_is_newer_version():
    assert is_newer_version("1.2.17", "1.2.16") is True
    assert is_newer_version("1.3.0", "1.2.16") is True
    assert is_newer_version("2.0.0", "1.2.16") is True
    assert is_newer_version("1.2.15", "1.2.16") is False
    assert is_newer_version("1.2.16", "1.2.16") is False


def test_get_install_method():
    # Test NPM method
    with mock.patch.dict(os.environ, {"PRISM_INSTALL_METHOD": "npm"}):
        assert get_install_method() == "npm"

    # Test Standalone method
    with mock.patch.dict(os.environ, {}, clear=True):
        with mock.patch.object(sys, "frozen", True, create=True):
            assert get_install_method() == "standalone"

    # Test Pip method
    with mock.patch.dict(os.environ, {}, clear=True):
        if hasattr(sys, "frozen"):
            with mock.patch.object(sys, "frozen", False, create=True):
                assert get_install_method() == "pip"
        else:
            assert get_install_method() == "pip"


@mock.patch("urllib.request.urlopen")
def test_check_for_updates_newer(mock_urlopen, tmp_path):
    # Set up mock registry response
    mock_response = mock.Mock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"version": "9.9.9"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    # Temporarily redirect cache timestamp file to a temp directory
    with mock.patch("prism_organizer.updater.TIMESTAMP_FILE", tmp_path / ".last_update_check"):
        result = check_for_updates(force=True)
        assert result == "9.9.9"


@mock.patch("urllib.request.urlopen")
def test_check_for_updates_older_or_same(mock_urlopen, tmp_path):
    # Set up mock registry response with same or older version
    mock_response = mock.Mock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"version": "1.0.0"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    with mock.patch("prism_organizer.updater.TIMESTAMP_FILE", tmp_path / ".last_update_check"):
        result = check_for_updates(force=True)
        assert result is None


@mock.patch("urllib.request.urlopen")
def test_check_for_updates_throttling(mock_urlopen, tmp_path):
    # Verify that updater doesn't make HTTP requests if checked recently
    mock_response = mock.Mock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"version": "9.9.9"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    temp_timestamp = tmp_path / ".last_update_check"
    with mock.patch("prism_organizer.updater.TIMESTAMP_FILE", temp_timestamp):
        # First check (force) creates the timestamp file
        check_for_updates(force=True)
        assert temp_timestamp.exists()

        # Reset mock call count
        mock_urlopen.reset_mock()

        # Subsequent check without force should hit throttle and NOT call urlopen
        result = check_for_updates(force=False)
        assert result is None
        mock_urlopen.assert_not_called()

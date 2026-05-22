"""Tests for the rules module."""

import pytest
from pathlib import Path

from prism_organizer.config import Config, DEFAULT_CONFIG
from prism_organizer.scanner import Scanner
from prism_organizer.rules import RuleEngine


def _make_config(rules=None):
    config = Config.__new__(Config)
    data = dict(DEFAULT_CONFIG)
    data["custom_rules"] = rules or []
    config._data = data
    config._config_path = Path("/nonexistent")
    return config


@pytest.fixture
def rule_dir(tmp_path):
    (tmp_path / "thesis.pdf").write_bytes(b"p" * 500)
    (tmp_path / "photo.jpg").write_bytes(b"j" * 300)
    (tmp_path / "random.xyz").write_bytes(b"x" * 100)
    return tmp_path


def test_extension_match(rule_dir):
    rules = [{
        "name": "Move PDFs",
        "match": {"extension": ".pdf"},
        "action": "move",
        "destination": str(rule_dir / "PDFs"),
    }]
    config = _make_config(rules)
    scanner = Scanner(config)
    result = scanner.scan(str(rule_dir), recursive=False)

    engine = RuleEngine(config)
    plan = engine.evaluate(result)

    assert plan.total_matches == 1
    assert plan.matches[0].file_info.name == "thesis.pdf"


def test_name_contains_match(rule_dir):
    rules = [{
        "name": "Match thesis",
        "match": {"name_contains": "thesis"},
        "action": "move",
        "destination": str(rule_dir / "Thesis"),
    }]
    config = _make_config(rules)
    scanner = Scanner(config)
    result = scanner.scan(str(rule_dir), recursive=False)

    engine = RuleEngine(config)
    plan = engine.evaluate(result)

    assert plan.total_matches == 1


def test_no_rules_returns_all_unmatched(rule_dir):
    config = _make_config(rules=[])
    scanner = Scanner(config)
    result = scanner.scan(str(rule_dir), recursive=False)

    engine = RuleEngine(config)
    plan = engine.evaluate(result)

    assert plan.total_matches == 0
    assert len(plan.unmatched) == 3


def test_first_rule_wins(rule_dir):
    rules = [
        {"name": "Rule 1", "match": {"extension": ".pdf"}, "action": "move", "destination": str(rule_dir / "A")},
        {"name": "Rule 2", "match": {"extension": ".pdf"}, "action": "move", "destination": str(rule_dir / "B")},
    ]
    config = _make_config(rules)
    scanner = Scanner(config)
    result = scanner.scan(str(rule_dir), recursive=False)

    engine = RuleEngine(config)
    plan = engine.evaluate(result)

    pdf_matches = [m for m in plan.matches if m.file_info.name == "thesis.pdf"]
    assert len(pdf_matches) == 1
    assert pdf_matches[0].rule_name == "Rule 1"


def test_multiple_extension_match(rule_dir):
    rules = [{
        "name": "Images and docs",
        "match": {"extension": [".pdf", ".jpg"]},
        "action": "move",
        "destination": str(rule_dir / "Both"),
    }]
    config = _make_config(rules)
    scanner = Scanner(config)
    result = scanner.scan(str(rule_dir), recursive=False)

    engine = RuleEngine(config)
    plan = engine.evaluate(result)

    assert plan.total_matches == 2


def test_sanitization():
    from prism_organizer.rules import sanitize_suggested_stem, sanitize_filename_traversal

    # Test stem sanitization
    assert sanitize_suggested_stem("clean-name") == "clean-name"
    assert sanitize_suggested_stem("../../evil-name") == "evil-name"
    assert sanitize_suggested_stem("foo/bar\\baz") == "foobarbaz"
    assert sanitize_suggested_stem("evil..name") == "evilname"
    assert sanitize_suggested_stem("name:with*restricted?chars\"<|>") == "namewithrestrictedchars"
    assert sanitize_suggested_stem("   ...   ") == "renamed_file"
    assert sanitize_suggested_stem("") == "renamed_file"

    # Test full filename sanitization
    assert sanitize_filename_traversal("../../evil.jpg") == "evil.jpg"
    assert sanitize_filename_traversal("foo/bar.txt") == "foobar.txt"
    assert sanitize_filename_traversal("test:file*name?.png") == "testfilename.png"
    assert sanitize_filename_traversal(".hidden") == "hidden"

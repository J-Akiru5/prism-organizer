"""Tests for the CLI argument parser."""

from datetime import datetime
from pathlib import Path

from prism_organizer.ai import AIClassification
from prism_organizer.cli import _build_classification_plan, create_parser
from prism_organizer.scanner import FileInfo


def _make_file_info(name="report.pdf", category="Misc"):
    now = datetime.now()
    return FileInfo(
        path=Path("/target") / name,
        name=name,
        extension=Path(name).suffix,
        size=1024,
        modified=now,
        created=now,
        category=category,
    )


def test_classification_plan_rejects_path_traversal_in_suggested_category():
    """An AI-suggested category outside the configured allow-list (e.g. a
    path-traversal payload like "../../../evil") must never be used as a
    raw path segment — the destination must stay under target_dir.
    """
    target_dir = Path("/target")
    file_info = _make_file_info(category="Misc")
    classification = AIClassification(
        file_info=file_info,
        suggested_category="../../../evil",
        confidence=0.95,
        reasoning="looks evil",
    )

    plan = _build_classification_plan(
        [classification], target_dir,
        valid_categories={"Images", "Documents", "Misc"},
    )

    dest = plan.matches[0].destination
    # The destination must stay directly under target_dir/<category> —
    # never escape target_dir via ".." segments from the AI payload.
    assert dest.parent.parent == target_dir
    # Falls back to the file's own (already-trusted) category.
    assert dest.parent.name == "Misc"
    assert ".." not in dest.parts


def test_classification_plan_accepts_known_category():
    target_dir = Path("/target")
    file_info = _make_file_info(category="Misc")
    classification = AIClassification(
        file_info=file_info,
        suggested_category="Documents",
        confidence=0.95,
        reasoning="it's a pdf",
    )

    plan = _build_classification_plan(
        [classification], target_dir,
        valid_categories={"Images", "Documents", "Misc"},
    )

    dest = plan.matches[0].destination
    assert dest.parent.name == "Documents"


def test_schedule_add_command_flag_does_not_collide_with_top_level_command():
    """Regression test: ``schedule add --command`` must not overwrite the
    top-level ``args.command`` (which drives subcommand dispatch in
    ``main()``). It should land in ``args.run_command`` instead.
    """
    parser = create_parser()
    args = parser.parse_args([
        "schedule", "add", "somepath",
        "--command", "sort",
        "--interval", "monthly",
        "--days", "1,15",
    ])

    assert args.command == "schedule"
    assert args.schedule_cmd == "add"
    assert args.run_command == "sort"
    assert args.interval == "monthly"
    assert args.days == "1,15"

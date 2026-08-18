"""Tests for the CLI argument parser."""

from prism_organizer.cli import create_parser


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

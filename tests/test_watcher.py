"""Tests for TaskScheduler (Windows Task Scheduler integration)."""

from unittest import mock

from prism_organizer.watcher import TaskScheduler


def _ok_result():
    result = mock.Mock()
    result.returncode = 0
    result.stderr = ""
    return result


def _fail_result(stderr="Invalid value for /D option"):
    result = mock.Mock()
    result.returncode = 1
    result.stderr = stderr
    return result


def test_monthly_schedule_creates_one_task_per_day():
    """schtasks /D rejects a comma-separated day list for /SC MONTHLY, so
    each day must become its own schtasks call with a single /D value.
    """
    sched = TaskScheduler()
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _ok_result()

    with mock.patch("subprocess.run", side_effect=fake_run):
        ok = sched.add_task(".", "sort", interval="monthly", days="1,15", time_str="09:00")

    assert ok is True
    assert len(calls) == 2

    for cmd in calls:
        d_index = cmd.index("/D")
        # Exactly one day value, never a joined "1,15" list.
        assert "," not in cmd[d_index + 1]

    tn_values = [cmd[cmd.index("/TN") + 1] for cmd in calls]
    assert any(name.endswith("(day 1)") for name in tn_values)
    assert any(name.endswith("(day 15)") for name in tn_values)


def test_monthly_schedule_continues_after_one_day_fails():
    """One failing day must not abort the rest of the batch, and overall
    success should be False since not every day succeeded.
    """
    sched = TaskScheduler()

    def fake_run(cmd, **kwargs):
        d_index = cmd.index("/D")
        if cmd[d_index + 1] == "15":
            return _fail_result()
        return _ok_result()

    with mock.patch("subprocess.run", side_effect=fake_run) as mocked:
        ok = sched.add_task(".", "sort", interval="monthly", days="1,15", time_str="09:00")

    assert ok is False
    # Both days were still attempted despite day 15 failing.
    assert mocked.call_count == 2


def test_monthly_schedule_rejects_invalid_days():
    sched = TaskScheduler()
    with mock.patch("subprocess.run") as mocked:
        assert sched.add_task(".", "sort", interval="monthly", days="0,40") is False
        assert sched.add_task(".", "sort", interval="monthly", days=None) is False
        assert sched.add_task(".", "sort", interval="monthly", days="1,abc") is False
    mocked.assert_not_called()


def test_group_base_name_detects_day_suffix():
    assert (
        TaskScheduler.group_base_name("Prism Organizer - sort Downloads (day 1)")
        == "Prism Organizer - sort Downloads"
    )
    assert TaskScheduler.group_base_name("Prism Organizer - sort Downloads") is None


def test_remove_task_by_base_name_removes_whole_monthly_group():
    """Removing the shared base name of a monthly schedule must remove
    every day-task, not just one of them.
    """
    sched = TaskScheduler()
    fake_tasks = [
        {"name": "Prism Organizer - sort Downloads (day 1)", "next_run": "N/A", "status": "Ready"},
        {"name": "Prism Organizer - sort Downloads (day 15)", "next_run": "N/A", "status": "Ready"},
        {"name": "Prism Organizer - clean Photos", "next_run": "N/A", "status": "Ready"},
    ]
    deleted = []

    def fake_run(cmd, **kwargs):
        deleted.append(cmd[cmd.index("/TN") + 1])
        return _ok_result()

    with mock.patch.object(TaskScheduler, "list_tasks", return_value=fake_tasks), \
            mock.patch("subprocess.run", side_effect=fake_run):
        ok = sched.remove_task("Prism Organizer - sort Downloads")

    assert ok is True
    assert set(deleted) == {
        "Prism Organizer - sort Downloads (day 1)",
        "Prism Organizer - sort Downloads (day 15)",
    }


def test_remove_task_exact_match_only_removes_that_task():
    sched = TaskScheduler()
    fake_tasks = [
        {"name": "Prism Organizer - sort Downloads (day 1)", "next_run": "N/A", "status": "Ready"},
        {"name": "Prism Organizer - sort Downloads (day 15)", "next_run": "N/A", "status": "Ready"},
    ]
    deleted = []

    def fake_run(cmd, **kwargs):
        deleted.append(cmd[cmd.index("/TN") + 1])
        return _ok_result()

    with mock.patch.object(TaskScheduler, "list_tasks", return_value=fake_tasks), \
            mock.patch("subprocess.run", side_effect=fake_run):
        ok = sched.remove_task("Prism Organizer - sort Downloads (day 1)")

    assert ok is True
    assert deleted == ["Prism Organizer - sort Downloads (day 1)"]

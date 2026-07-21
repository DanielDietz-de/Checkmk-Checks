from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import os

import pytest

MODULE_PATH = Path(__file__).parents[1] / "src" / "bin" / "clean_spoolfiles"
loader = SourceFileLoader("clean_spoolfiles_safety", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
loader.exec_module(module)


def write_record(path, *, what, notification_type, host="host1", service=None, mtime=1000):
    context = {
        "WHAT": what,
        "NOTIFICATIONTYPE": notification_type,
        "HOSTNAME": host,
    }
    if service is not None:
        context["SERVICEDESC"] = service
    path.write_text(repr({"context": context}), encoding="utf-8")
    os.utime(path, (mtime, mtime))


def test_plan_keeps_all_repeated_problems_until_recovery(tmp_path):
    write_record(tmp_path / "001", what="SERVICE", notification_type="PROBLEM", service="CPU", mtime=1000)
    write_record(tmp_path / "002", what="SERVICE", notification_type="PROBLEM", service="CPU", mtime=1001)
    write_record(tmp_path / "003", what="SERVICE", notification_type="RECOVERY", service="CPU", mtime=1002)

    groups, skipped = module.build_cleanup_plan(
        tmp_path,
        min_age_seconds=300,
        now=2000,
    )

    assert skipped == []
    assert len(groups) == 1
    assert [item.path.name for item in groups[0].files] == ["001", "002", "003"]


def test_service_downtime_pair_is_planned_without_key_error(tmp_path):
    write_record(tmp_path / "001", what="SERVICE", notification_type="DOWNTIMESTART", service="CPU", mtime=1000)
    write_record(tmp_path / "002", what="SERVICE", notification_type="DOWNTIMEEND", service="CPU", mtime=1001)

    groups, _ = module.build_cleanup_plan(tmp_path, min_age_seconds=0, now=2000)

    assert len(groups) == 1
    assert groups[0].category == "Services downtime"


def test_young_files_are_not_planned(tmp_path):
    write_record(tmp_path / "001", what="HOST", notification_type="PROBLEM", mtime=1900)
    write_record(tmp_path / "002", what="HOST", notification_type="RECOVERY", mtime=1901)

    groups, skipped = module.build_cleanup_plan(
        tmp_path,
        min_age_seconds=300,
        now=2000,
    )

    assert groups == []
    assert len(skipped) == 2


def test_changed_file_aborts_group_before_any_move(tmp_path):
    spool = tmp_path / "spool"
    quarantine = tmp_path / "quarantine"
    spool.mkdir()
    quarantine.mkdir()
    write_record(spool / "001", what="HOST", notification_type="PROBLEM", mtime=1000)
    write_record(spool / "002", what="HOST", notification_type="RECOVERY", mtime=1001)
    groups, _ = module.build_cleanup_plan(spool, min_age_seconds=0, now=2000)
    (spool / "001").write_text("changed", encoding="utf-8")

    with pytest.raises(module.CleanupSafetyError, match="changed after the scan"):
        module.quarantine_group(groups[0], quarantine)
    assert (spool / "001").exists()
    assert (spool / "002").exists()


def test_quarantine_moves_complete_group_atomically(tmp_path):
    spool = tmp_path / "spool"
    quarantine = tmp_path / "quarantine"
    spool.mkdir()
    quarantine.mkdir()
    write_record(spool / "001", what="HOST", notification_type="PROBLEM", mtime=1000)
    write_record(spool / "002", what="HOST", notification_type="RECOVERY", mtime=1001)
    groups, _ = module.build_cleanup_plan(spool, min_age_seconds=0, now=2000)

    moved = module.quarantine_group(groups[0], quarantine)

    assert sorted(path.name for path in moved) == ["001", "002"]
    assert list(spool.iterdir()) == []
    assert sorted(path.name for path in quarantine.iterdir()) == ["001", "002"]


def test_default_arguments_are_read_only():
    args = module.parse_args([])
    assert args.execute is False
    assert args.min_age_seconds == module.DEFAULT_MIN_AGE_SECONDS

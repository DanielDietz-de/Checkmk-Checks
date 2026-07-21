from __future__ import annotations

import getpass
import importlib.machinery
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

PLUGIN = Path(__file__).parents[1] / "src/agents/plugins/oxidized_backup"
loader = importlib.machinery.SourceFileLoader("oxidized_backup_agent", str(PLUGIN))
spec = importlib.util.spec_from_loader(loader.name, loader)
assert spec is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
loader.exec_module(module)


def policy() -> dict[str, int]:
    return {
        "collection_warning_age_seconds": 3600,
        "collection_critical_age_seconds": 7200,
        "remote_sync_grace_seconds": 300,
        "remote_verification_max_age_seconds": 3600,
        "fsck_interval_seconds": 300,
        "orphan_state": 1,
    }


def valid_config(tmp_path: Path) -> dict[str, Any]:
    user = "nobody"
    try:
        import pwd

        pwd.getpwnam(user)
    except KeyError:
        user = "daemon"
    return {
        "inventory": {
            "url": (tmp_path / "inventory.json").as_uri(),
            "max_response_bytes": 1048576,
        },
        "oxidized": {
            "url": "http://127.0.0.1:8888/nodes.json",
            "max_response_bytes": 1048576,
        },
        "state": {
            "hook_state_file": str(tmp_path / "hook.json"),
            "monitor_state_file": str(tmp_path / "monitor.json"),
        },
        "git": {
            "run_as_user": user,
            "repositories": [
                {
                    "id": "default",
                    "path": str(tmp_path / "oxidized.git"),
                    "groups": ["*"],
                    "single_repo": True,
                }
            ],
        },
        "policy": policy(),
    }


def git(*args: str, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        [shutil.which("git") or "/usr/bin/git", *args],
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def create_git_pair(tmp_path: Path) -> tuple[Path, Path, Path]:
    work = tmp_path / "work"
    local_bare = tmp_path / "local.git"
    remote_bare = tmp_path / "remote.git"
    work.mkdir()
    git("init", "-b", "main", cwd=work)
    git("config", "user.name", "Test", cwd=work)
    git("config", "user.email", "test@example.invalid", cwd=work)
    (work / "switch-1").write_text("hostname switch-1\n", encoding="utf-8")
    git("add", "switch-1", cwd=work)
    git("commit", "-m", "initial", cwd=work)
    git("clone", "--bare", str(work), str(local_bare), cwd=tmp_path)
    git("clone", "--bare", str(local_bare), str(remote_bare), cwd=tmp_path)
    git("remote", "set-url", "origin", str(remote_bare), cwd=local_bare)
    return work, local_bare, remote_bare


def test_validate_config_requires_explicit_cleartext_http_opt_in(tmp_path: Path) -> None:
    config = valid_config(tmp_path)
    config["inventory"] = {"url": "http://monitor.example/oxidized.json"}
    with pytest.raises(module.CollectorError, match="allow_insecure_http"):
        module.validate_config(config)
    config["inventory"]["allow_insecure_http"] = True
    module.validate_config(config)


def test_validate_config_rejects_root_git_execution(tmp_path: Path) -> None:
    config = valid_config(tmp_path)
    config["git"]["run_as_user"] = "root"
    with pytest.raises(module.CollectorError, match="unprivileged"):
        module.validate_config(config)


def test_validate_config_rejects_multiple_wildcard_repositories(tmp_path: Path) -> None:
    config = valid_config(tmp_path)
    second = dict(config["git"]["repositories"][0])
    second["id"] = "second"
    second["path"] = str(tmp_path / "second.git")
    config["git"]["repositories"].append(second)
    with pytest.raises(module.CollectorError, match="wildcard"):
        module.validate_config(config)


def test_inventory_parser_marks_duplicates_and_rejects_output_injection() -> None:
    records, errors = module.parse_inventory(
        [
            {"hostname": "switch-1", "os": "picos"},
            {"hostname": "switch-1", "os": "picos"},
            {"hostname": "bad\n<<<<host>>>>", "os": "ios"},
        ]
    )
    assert len(records) == 2
    assert all(record["duplicate"] for record in records)
    assert any("Duplicate inventory" in error for error in errors)
    assert any("forbidden" in error for error in errors)


def test_parse_oxidized_nodes_accepts_top_level_and_last_status() -> None:
    rows, errors = module.parse_oxidized_nodes(
        [
            {
                "name": "switch-1",
                "group": "switches",
                "status": "success",
                "time": "2026-07-21T20:00:00Z",
            },
            {
                "name": "switch-2",
                "last": {"status": "no_connection", "end": 1234},
            },
        ]
    )
    assert not errors
    assert rows[0]["group"] == "switches"
    assert rows[0]["status"] == "success"
    assert rows[0]["last_attempt_at"] is not None
    assert rows[1]["status"] == "no_connection"
    assert rows[1]["last_attempt_at"] == 1234


def test_hook_state_survives_multiple_events(tmp_path: Path) -> None:
    state_file = tmp_path / "hook-state.json"
    config = {"state": {"hook_state_file": str(state_file)}}
    common = {
        "OX_NODE_NAME": "switch-1",
        "OX_NODE_GROUP": "switches",
        "OX_NODE_MODEL": "picos",
    }
    module.record_hook(config, {**common, "OX_EVENT": "node_success"})
    module.record_hook(
        config,
        {
            **common,
            "OX_EVENT": "post_store",
            "OX_REPO_COMMITREF": "a" * 40,
        },
    )
    state = json.loads(state_file.read_text(encoding="utf-8"))
    record = next(iter(state["nodes"].values()))
    assert record["last_attempt_status"] == "success"
    assert record["last_success_at"] > 0
    assert record["ever_stored"] is True
    assert record["last_store_commit"] == "a" * 40
    assert oct(state_file.stat().st_mode & 0o777) == "0o600"


def test_hook_state_redacts_error_secrets(tmp_path: Path) -> None:
    state_file = tmp_path / "hook-state.json"
    config = {"state": {"hook_state_file": str(state_file)}}
    module.record_hook(
        config,
        {
            "OX_EVENT": "node_fail",
            "OX_NODE_NAME": "switch-1",
            "OX_JOB_STATUS": "no_connection",
            "OX_ERR_REASON": "https://user:secret@example.invalid token=abcdef",
        },
    )
    text = state_file.read_text(encoding="utf-8")
    assert "secret" not in text
    assert "abcdef" not in text
    assert "<redacted>" in text


def test_repository_inspection_confirms_file_and_remote_sync(tmp_path: Path) -> None:
    _work, local_bare, _remote = create_git_pair(tmp_path)
    result, monitor = module.inspect_repository(
        {
            "id": "default",
            "path": str(local_bare),
            "groups": ["*"],
            "single_repo": True,
            "remote": "origin",
            "branch": "main",
        },
        git_binary=shutil.which("git") or "/usr/bin/git",
        run_as_user=getpass.getuser(),
        expected_paths=["switch-1"],
        monitor_record={},
        policy=policy(),
        now=int(time.time()),
    )
    assert result["valid"] is True
    assert result["missing_files"] == []
    assert result["empty_files"] == []
    assert result["artifacts"]["switch-1"]["exists"] is True
    assert result["remote"]["status"] == "synced"
    assert result["remote"]["state_hint"] == 0
    assert monitor["last_synced_at"] > 0
    assert result["fsck"]["status"] == "ok"


def test_repository_inspection_detects_missing_file(tmp_path: Path) -> None:
    _work, local_bare, _remote = create_git_pair(tmp_path)
    result, _monitor = module.inspect_repository(
        {
            "id": "default",
            "path": str(local_bare),
            "groups": ["*"],
            "single_repo": True,
            "remote": "origin",
            "branch": "main",
        },
        git_binary=shutil.which("git") or "/usr/bin/git",
        run_as_user=getpass.getuser(),
        expected_paths=["missing-switch"],
        monitor_record={},
        policy=policy(),
        now=int(time.time()),
    )
    assert result["missing_files"] == ["missing-switch"]
    assert result["artifacts"]["missing-switch"]["exists"] is False


def test_repository_mismatch_uses_grace_then_critical(tmp_path: Path) -> None:
    work, local_bare, _remote = create_git_pair(tmp_path)
    (work / "switch-1").write_text("hostname switch-1\nchanged\n", encoding="utf-8")
    git("add", "switch-1", cwd=work)
    git("commit", "-m", "local only", cwd=work)
    git("push", str(local_bare), "main", cwd=work)
    now = int(time.time())
    result, monitor = module.inspect_repository(
        {
            "id": "default",
            "path": str(local_bare),
            "groups": ["*"],
            "single_repo": True,
            "remote": "origin",
            "branch": "main",
        },
        git_binary=shutil.which("git") or "/usr/bin/git",
        run_as_user=getpass.getuser(),
        expected_paths=["switch-1"],
        monitor_record={},
        policy=policy(),
        now=now,
    )
    assert result["remote"]["status"] == "mismatch"
    assert result["remote"]["state_hint"] == 1

    result_late, _ = module.inspect_repository(
        {
            "id": "default",
            "path": str(local_bare),
            "groups": ["*"],
            "single_repo": True,
            "remote": "origin",
            "branch": "main",
        },
        git_binary=shutil.which("git") or "/usr/bin/git",
        run_as_user=getpass.getuser(),
        expected_paths=["switch-1"],
        monitor_record={**monitor, "mismatch_since": now - 301},
        policy=policy(),
        now=now,
    )
    assert result_late["remote"]["state_hint"] == 2


def test_safe_git_tree_paths() -> None:
    assert module._safe_git_tree_path("switches", "switch-1", single_repo=True) == (
        "switches/switch-1"
    )
    assert module._safe_git_tree_path("switches", "switch-1", single_repo=False) == "switch-1"
    with pytest.raises(module.CollectorError):
        module._safe_git_tree_path("../outside", "switch-1", single_repo=True)


def test_emit_agent_output_has_balanced_piggyback_markers(capsys: pytest.CaptureFixture[str]) -> None:
    module.emit_agent_output(
        {"schema_version": 1, "kind": "central"},
        [{"schema_version": 1, "kind": "device", "host_name": "switch-1"}],
    )
    output = capsys.readouterr().out
    assert "<<<<switch-1>>>>" in output
    assert output.rstrip().endswith("<<<<>>>>")
    assert output.count("<<<oxidized_backup:sep(0)>>>" ) == 2

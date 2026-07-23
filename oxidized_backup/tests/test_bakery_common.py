from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

MODULE_PATH = (
    Path(__file__).parents[1]
    / "src"
    / "oxidized_backup"
    / "bakery_common.py"
)
spec = importlib.util.spec_from_file_location("oxidized_backup_bakery_common", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def bakery_conf(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "deployment": ("cached", 300.0),
        "inventory": {
            "url": "https://checkmk.example.invalid/site/open/oxidized.json",
            "timeout_seconds": 10,
            "max_response_bytes": 4194304,
            "ca_file": "/etc/ssl/certs/ca-certificates.crt",
            "allow_insecure_http": False,
            "auth": ("none", None),
        },
        "oxidized": {
            "url": "http://127.0.0.1:8888/nodes.json",
            "timeout_seconds": 10,
            "max_response_bytes": 4194304,
            "allow_insecure_http": False,
            "auth": ("none", None),
        },
        "state": {
            "hook_state_file": "/var/lib/oxidized/oxidized_backup/hook-state.json",
            "monitor_state_file": "/var/lib/check_mk_agent/oxidized_backup/monitor-state.json",
        },
        "git": {
            "run_as_user": "oxidized",
            "git_binary": "/usr/bin/git",
            "repositories": [
                {
                    "id": "default",
                    "path": "/var/lib/oxidized/oxidized.git",
                    "groups": [("wildcard", None)],
                    "single_repo": True,
                    "remote": "origin",
                    "branch": "main",
                    "command_timeout_seconds": 30,
                    "fsck_timeout_seconds": 120,
                }
            ],
        },
        "policy": {
            "collection_warning_age_seconds": 7200.0,
            "collection_critical_age_seconds": 14400.0,
            "remote_sync_grace_seconds": 300.0,
            "remote_verification_max_age_seconds": 3600.0,
            "fsck_interval_seconds": 3600.0,
            "orphan_state": "warn",
        },
    }
    value.update(overrides)
    return value


def test_normalizes_complete_bakery_configuration() -> None:
    mode, interval, config = module.normalize_rule(bakery_conf())
    assert mode == "cached"
    assert interval == 300
    assert config["inventory"]["url"].startswith("https://")
    assert "auth" not in config["inventory"]
    assert config["git"]["repositories"][0]["groups"] == ["*"]
    assert config["policy"]["orphan_state"] == 1
    assert json.loads("\n".join(module.config_lines(bakery_conf()))) == config


def test_supports_bearer_and_basic_secret_file_authentication() -> None:
    config = bakery_conf()
    config["inventory"]["auth"] = (
        "bearer",
        {"token_file": "/etc/check_mk/oxidized_inventory.token"},
    )
    config["oxidized"]["auth"] = (
        "basic",
        {
            "username": "monitor",
            "password_file": "/etc/check_mk/oxidized_api.password",
        },
    )
    normalized = module.copied_config(config)
    assert normalized["inventory"]["auth"]["type"] == "bearer"
    assert normalized["oxidized"]["auth"] == {
        "type": "basic",
        "username": "monitor",
        "password_file": "/etc/check_mk/oxidized_api.password",
    }


def test_group_choices_map_to_json_values() -> None:
    config = bakery_conf()
    config["git"]["repositories"][0]["groups"] = [
        ("ungrouped", None),
        ("named", "switches"),
    ]
    normalized = module.copied_config(config)
    assert normalized["git"]["repositories"][0]["groups"] == [None, "switches"]


def test_hook_uses_stable_package_managed_helper() -> None:
    text = "\n".join(module.hook_lines())
    assert "/usr/bin/oxidized_backup_hook" in text
    assert "--config /etc/check_mk/oxidized_backup.json" in text
    assert "node_success" in text
    assert "node_fail" in text
    assert "post_store" in text


def test_state_directories_are_derived_from_configured_files() -> None:
    assert module.state_directories(bakery_conf()) == (
        "/var/lib/oxidized/oxidized_backup",
        "/var/lib/check_mk_agent/oxidized_backup",
        "oxidized",
    )


def test_do_not_deploy_mode_is_preserved() -> None:
    mode, interval, _config = module.normalize_rule(
        bakery_conf(deployment=("do_not_deploy", None))
    )
    assert mode == "do_not_deploy"
    assert interval is None


@pytest.mark.parametrize(
    "mutator, message",
    [
        (
            lambda config: config["state"].update(
                hook_state_file="relative/state.json"
            ),
            "absolute path",
        ),
        (
            lambda config: config["git"].update(run_as_user="root"),
            "unprivileged",
        ),
        (
            lambda config: config["policy"].update(
                collection_warning_age_seconds=7200,
                collection_critical_age_seconds=3600,
            ),
            "greater than warning",
        ),
        (
            lambda config: config["git"]["repositories"].append(
                {
                    **config["git"]["repositories"][0],
                    "id": "second",
                    "path": "/var/lib/oxidized/second.git",
                }
            ),
            "Only one repository",
        ),
    ],
)
def test_rejects_unsafe_or_ambiguous_bakery_values(
    mutator: Any,
    message: str,
) -> None:
    config = bakery_conf()
    mutator(config)
    with pytest.raises(ValueError, match=message):
        module.normalize_rule(config)

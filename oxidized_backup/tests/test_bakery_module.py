from __future__ import annotations

import importlib.util
import shlex
import sys
import types
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
COMMON_PATH = ROOT / "src/oxidized_backup/bakery_common.py"
BAKERY_PATH = (
    ROOT
    / "src/lib/python3/cmk/base/cee/plugins/bakery/oxidized_backup.py"
)


class OS(Enum):
    """Represent os behavior and associated state."""
    LINUX = "linux"


class DebStep(Enum):
    """Represent debstep behavior and associated state."""
    POSTINST = "postinst"


class RpmStep(Enum):
    """Represent rpmstep behavior and associated state."""
    POST = "post"


@dataclass
class Plugin:
    """Represent plugin behavior and associated state."""
    base_os: OS
    source: Path
    target: Path | None = None
    interval: int | None = None


@dataclass
class SystemBinary:
    """Represent systembinary behavior and associated state."""
    base_os: OS
    source: Path
    target: Path | None = None


@dataclass
class PluginConfig:
    """Represent pluginconfig behavior and associated state."""
    base_os: OS
    lines: list[str]
    target: Path
    include_header: bool = False


@dataclass
class SystemConfig:
    """Represent systemconfig behavior and associated state."""
    base_os: OS
    lines: list[str]
    target: Path
    include_header: bool = False


@dataclass
class Scriptlet:
    """Represent scriptlet behavior and associated state."""
    step: DebStep | RpmStep
    lines: list[str]


class Register:
    """Represent register behavior and associated state."""
    def __init__(self) -> None:
        """Initialize the instance and its required state."""
        self.calls: list[dict[str, Any]] = []

    def bakery_plugin(self, **kwargs: Any) -> None:
        """Handle bakery plugin for this module's workflow."""
        self.calls.append(kwargs)


def _module(name: str) -> types.ModuleType:
    """Handle module for this module's workflow."""
    module = types.ModuleType(name)
    module.__path__ = []  # type: ignore[attr-defined]
    sys.modules[name] = module
    return module


def _load_module(name: str, path: Path) -> types.ModuleType:
    """Handle load module for this module's workflow."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _configuration() -> dict[str, Any]:
    """Handle configuration for this module's workflow."""
    return {
        "deployment": ("cached", 300.0),
        "inventory": {
            "url": "https://checkmk.example.invalid/site/open/oxidized.json",
            "timeout_seconds": 10,
            "max_response_bytes": 4194304,
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


def test_bakery_v1_contract_and_generated_artifacts() -> None:
    """Verify that bakery v1 contract and generated artifacts."""
    for name in (
        "cmk",
        "cmk.base",
        "cmk.base.cee",
        "cmk.base.cee.plugins",
        "cmk.base.cee.plugins.bakery",
        "cmk.base.cee.plugins.bakery.bakery_api",
        "cmk_addons",
        "cmk_addons.plugins",
        "cmk_addons.plugins.oxidized_backup",
    ):
        _module(name)

    common = _load_module(
        "cmk_addons.plugins.oxidized_backup.bakery_common",
        COMMON_PATH,
    )
    assert common.HOOK_HELPER_PATH == "/usr/bin/oxidized_backup_hook"
    assert common.CONFIG_PATH == "/etc/check_mk/oxidized_backup.json"

    register = Register()
    api = types.ModuleType("cmk.base.cee.plugins.bakery.bakery_api.v1")
    api.DebStep = DebStep
    api.FileGenerator = Any
    api.OS = OS
    api.Plugin = Plugin
    api.PluginConfig = PluginConfig
    api.RpmStep = RpmStep
    api.Scriptlet = Scriptlet
    api.ScriptletGenerator = Any
    api.SystemBinary = SystemBinary
    api.SystemConfig = SystemConfig
    api.quote_shell_string = shlex.quote
    api.register = register
    sys.modules[api.__name__] = api

    bakery = _load_module(
        "cmk.base.cee.plugins.bakery.oxidized_backup",
        BAKERY_PATH,
    )
    assert register.calls == [
        {
            "name": "oxidized_backup",
            "files_function": bakery.get_files,
            "scriptlets_function": bakery.get_scriptlets,
        }
    ]

    artifacts = list(bakery.get_files(_configuration()))
    assert [type(item) for item in artifacts] == [
        Plugin,
        SystemBinary,
        PluginConfig,
        SystemConfig,
    ]
    assert artifacts[0].interval == 300
    assert artifacts[1].source == Path("plugins/oxidized_backup")
    assert artifacts[1].target == Path("oxidized_backup_hook")
    assert artifacts[2].target == Path("oxidized_backup.json")
    assert artifacts[3].target == Path("check_mk/oxidized_backup-hook.yml")

    scriptlets = list(bakery.get_scriptlets(_configuration(), "agent-hash"))
    assert [item.step for item in scriptlets] == [DebStep.POSTINST, RpmStep.POST]
    text = "\n".join(line for item in scriptlets for line in item.lines)
    assert "/var/lib/oxidized/oxidized_backup" in text
    assert "/var/lib/check_mk_agent/oxidized_backup" in text
    assert "getent passwd oxidized" in text
    assert "oxidized_backup_group=$(id -gn oxidized)" in text
    assert (
        "if [ -f /etc/check_mk/oxidized_backup.json ] "
        "&& [ ! -L /etc/check_mk/oxidized_backup.json ]; then"
    ) in text
    assert (
        'chown root:"$oxidized_backup_group" '
        "/etc/check_mk/oxidized_backup.json"
    ) in text
    assert "chmod 0640 /etc/check_mk/oxidized_backup.json" in text
    assert "configuration ownership was not changed" in text
    assert "root:oxidized" not in text


def test_scriptlets_use_the_configured_service_account() -> None:
    """Verify that scriptlets use the configured service account."""
    bakery = sys.modules.get("cmk.base.cee.plugins.bakery.oxidized_backup")
    if bakery is None:
        test_bakery_v1_contract_and_generated_artifacts()
        bakery = sys.modules["cmk.base.cee.plugins.bakery.oxidized_backup"]

    config = _configuration()
    config["git"]["run_as_user"] = "oxidized_svc"
    scriptlets = list(bakery.get_scriptlets(config, "agent-hash"))
    text = "\n".join(line for item in scriptlets for line in item.lines)

    assert "getent passwd oxidized_svc" in text
    assert "oxidized_backup_group=$(id -gn oxidized_svc)" in text
    assert "-o oxidized_svc" in text
    assert "root:oxidized_svc" not in text


def test_do_not_deploy_yields_no_artifacts() -> None:
    # Reuse the module loaded by the previous test when tests run in normal order;
    # load it with the same stubs when this test is selected on its own.
    """Verify that do not deploy yields no artifacts."""
    bakery = sys.modules.get("cmk.base.cee.plugins.bakery.oxidized_backup")
    if bakery is None:
        test_bakery_v1_contract_and_generated_artifacts()
        bakery = sys.modules["cmk.base.cee.plugins.bakery.oxidized_backup"]
    config = _configuration()
    config["deployment"] = ("do_not_deploy", None)
    assert list(bakery.get_files(config)) == []
    assert list(bakery.get_scriptlets(config, "agent-hash")) == []

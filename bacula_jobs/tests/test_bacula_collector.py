import ast
import importlib.util
import json
import os
import sys
import types
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).parents[1]
MODULE_PATH = PACKAGE_ROOT / "src" / "agents" / "plugins" / "bacula_jobs"
BAKERY_PATH = (
    PACKAGE_ROOT
    / "src"
    / "lib"
    / "python3"
    / "cmk"
    / "base"
    / "cee"
    / "plugins"
    / "bakery"
    / "bacula_jobs.py"
)
RULESET_PATH = PACKAGE_ROOT / "src" / "bacula_jobs" / "rulesets" / "bakery.py"
loader = SourceFileLoader("bacula_jobs_collector", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)


def _load_bakery_module(monkeypatch):
    """Handle load bakery module for this module's workflow."""
    bakery_api = types.ModuleType("cmk.base.cee.plugins.bakery.bakery_api.v1")

    class OS:
        """Represent os behavior and associated state."""
        LINUX = "linux"

    class GeneratedFile:
        """Represent generatedfile behavior and associated state."""
        def __init__(self, **kwargs):
            """Initialize the instance and its required state."""
            self.kwargs = kwargs

    class Register:
        """Represent register behavior and associated state."""
        def __init__(self):
            """Initialize the instance and its required state."""
            self.calls = []

        def bakery_plugin(self, **kwargs):
            """Handle bakery plugin for this module's workflow."""
            self.calls.append(kwargs)

    register = Register()
    bakery_api.FileGenerator = object
    bakery_api.OS = OS
    bakery_api.Plugin = GeneratedFile
    bakery_api.PluginConfig = GeneratedFile
    bakery_api.register = register

    module_names = [
        "cmk",
        "cmk.base",
        "cmk.base.cee",
        "cmk.base.cee.plugins",
        "cmk.base.cee.plugins.bakery",
        "cmk.base.cee.plugins.bakery.bakery_api",
    ]
    for name in module_names:
        package = types.ModuleType(name)
        package.__path__ = []
        monkeypatch.setitem(sys.modules, name, package)
    monkeypatch.setitem(
        sys.modules,
        "cmk.base.cee.plugins.bakery.bakery_api.v1",
        bakery_api,
    )

    module_name = "cmk.base.cee.plugins.bakery.bacula_jobs"
    spec = importlib.util.spec_from_file_location(module_name, BAKERY_PATH)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = loaded
    spec.loader.exec_module(loaded)
    return loaded, register


def test_json_config_is_data_not_shell(tmp_path):
    """Verify that json config is data not shell."""
    config = tmp_path / "bacula_jobs.json"
    marker = tmp_path / "executed"
    config.write_text(
        json.dumps(
            {
                "backend": "mysql",
                "database": f"bacula;touch {marker}",
                "user": "bacula",
                "host": "localhost",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(module.BaculaConfigError, match="database"):
        module.load_config(config)
    assert not marker.exists()


def test_mysql_credentials_file_must_be_private(tmp_path):
    """Verify that mysql credentials file must be private."""
    credentials = tmp_path / "mysql.cnf"
    credentials.write_text("[client]\npassword=example\n", encoding="utf-8")
    os.chmod(credentials, 0o640)
    with pytest.raises(module.BaculaConfigError, match="group or others"):
        module.validate_private_file(str(credentials), "MySQL defaults file")
    os.chmod(credentials, 0o600)
    assert module.validate_private_file(str(credentials), "MySQL defaults file") == str(credentials)


def test_mysql_command_uses_argument_list_without_shell(monkeypatch, tmp_path):
    """Verify that mysql command uses argument list without shell."""
    credentials = tmp_path / "mysql.cnf"
    credentials.write_text("[client]\npassword=example\n", encoding="utf-8")
    os.chmod(credentials, 0o600)
    monkeypatch.setattr(module, "executable", lambda name: f"/usr/bin/{name}")
    config = module.validate_config(
        {
            "backend": "mysql",
            "database": "bacula",
            "user": "monitor",
            "host": "db.example",
            "port": 3306,
            "timeout": 15,
            "mysql_defaults_file": str(credentials),
        }
    )
    command, environment = module.mysql_command(config)
    assert command[0:2] == [
        "/usr/bin/mysql",
        f"--defaults-extra-file={credentials}",
    ]
    assert "--execute" in command
    assert "SHELL" not in environment


def test_postgresql_peer_auth_uses_runuser_without_shell(monkeypatch):
    """Verify that postgresql peer auth uses runuser without shell."""
    monkeypatch.setattr(module, "executable", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(module.pwd, "getpwnam", lambda name: object())
    config = module.validate_config(
        {
            "backend": "postgresql",
            "database": "bacula",
            "user": "bacula",
            "host": "localhost",
            "port": 5432,
            "timeout": 15,
            "postgres_os_user": "postgres",
        }
    )
    command, _ = module.postgresql_command(config)
    assert command[:4] == ["/usr/bin/runuser", "--user", "postgres", "--"]
    assert "/usr/bin/psql" in command


def test_legacy_deployment_sentinels_are_migrated_safely(monkeypatch):
    """Verify that legacy deployment sentinels are migrated safely."""
    bakery, register = _load_bakery_module(monkeypatch)

    disabled_mode, _ = bakery._normalize(
        (None, {"backend_type": "mysql", "dbname": "bacula"})
    )
    enabled_mode, normalized = bakery._normalize(
        ({}, {"backend_type": "pgsql", "dbname": "bareos"})
    )

    assert disabled_mode == "do_not_deploy"
    assert enabled_mode == "sync"
    assert normalized["settings"]["backend"] == "postgresql"
    assert normalized["settings"]["database"] == "bareos"
    assert register.calls[0]["name"] == "bacula"


def test_ruleset_keeps_historical_agent_config_name():
    """Verify that ruleset keeps historical agent config name."""
    source = RULESET_PATH.read_text(encoding="utf-8")
    assert 'name="bacula"' in source
    assert "_migrate_deployment" in source


def test_database_output_is_stopped_at_the_configured_cap(monkeypatch):
    """Verify that database output is stopped at the configured cap."""
    monkeypatch.setattr(module, "MAX_OUTPUT_BYTES", 1024)
    command = [
        sys.executable,
        "-c",
        "import sys; sys.stdout.buffer.write(b'x' * 4096); sys.stdout.flush()",
    ]
    with pytest.raises(module.BaculaConfigError, match="exceeds 10 MiB"):
        module._run_bounded(command, dict(os.environ), timeout=5)


def test_package_metadata_representations_match():
    """Verify that package metadata representations match."""
    python_info = ast.literal_eval(
        (PACKAGE_ROOT / "src" / "info").read_text(encoding="utf-8")
    )
    json_info = json.loads(
        (PACKAGE_ROOT / "src" / "info.json").read_text(encoding="utf-8")
    )
    assert python_info == json_info


def test_no_hardcoded_credential_or_config_paths():
    """Verify that no hardcoded credential or config paths."""
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "/root/.my.cnf" not in source
    assert 'MK_CONFDIR="/etc/check_mk"' not in source
    assert "capture_output=True" not in source
    assert "shell=True" not in source
    assert "os.system" not in source

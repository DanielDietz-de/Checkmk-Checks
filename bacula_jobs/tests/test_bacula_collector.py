import json
import os
import stat
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "src" / "agents" / "plugins" / "bacula_jobs"
loader = SourceFileLoader("bacula_jobs_collector", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)


def test_json_config_is_data_not_shell(tmp_path, monkeypatch):
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
    credentials = tmp_path / "mysql.cnf"
    credentials.write_text("[client]\npassword=secret\n", encoding="utf-8")
    os.chmod(credentials, 0o640)
    with pytest.raises(module.BaculaConfigError, match="group or others"):
        module.validate_private_file(str(credentials), "MySQL defaults file")
    os.chmod(credentials, 0o600)
    assert module.validate_private_file(str(credentials), "MySQL defaults file") == str(credentials)


def test_mysql_command_uses_argument_list_without_shell(monkeypatch, tmp_path):
    credentials = tmp_path / "mysql.cnf"
    credentials.write_text("[client]\npassword=secret\n", encoding="utf-8")
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


def test_no_hardcoded_root_or_etc_check_mk_paths():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "/root/.my.cnf" not in source
    assert 'MK_CONFDIR="/etc/check_mk"' not in source
    assert ". " not in source

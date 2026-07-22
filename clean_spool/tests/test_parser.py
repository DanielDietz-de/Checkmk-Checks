from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "src" / "bin" / "clean_spoolfiles"
loader = SourceFileLoader("clean_spoolfiles", str(MODULE_PATH))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
loader.exec_module(module)


def test_loads_valid_literal_context(tmp_path):
    spool_file = tmp_path / "notification"
    spool_file.write_text(
        repr(
            {
                "context": {
                    "WHAT": "SERVICE",
                    "NOTIFICATIONTYPE": "PROBLEM",
                    "HOSTNAME": "host1",
                    "SERVICEDESC": "CPU load",
                }
            }
        ),
        encoding="utf-8",
    )

    context = module.load_context(spool_file)
    assert context["HOSTNAME"] == "host1"


def test_rejects_executable_python_without_running_it(tmp_path):
    marker = tmp_path / "executed"
    spool_file = tmp_path / "notification"
    spool_file.write_text(
        f"__import__('pathlib').Path({str(marker)!r}).write_text('owned')",
        encoding="utf-8",
    )

    with pytest.raises(module.SpoolFormatError, match="valid Python literal"):
        module.load_context(spool_file)
    assert not marker.exists()


def test_rejects_oversized_spool_file(tmp_path, monkeypatch):
    spool_file = tmp_path / "notification"
    spool_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module, "MAX_SPOOL_FILE_SIZE", 1)

    with pytest.raises(module.SpoolFormatError, match="parser limit"):
        module.load_context(spool_file)


def test_rejects_missing_context_fields(tmp_path):
    spool_file = tmp_path / "notification"
    spool_file.write_text(repr({"context": {"WHAT": "HOST"}}), encoding="utf-8")

    with pytest.raises(module.SpoolFormatError, match="missing string field"):
        module.load_context(spool_file)

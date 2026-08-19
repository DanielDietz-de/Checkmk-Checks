import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "src" / "bin" / "sync_ec_events.py"
spec = spec_from_file_location("sync_ec_events", MODULE_PATH)
module = module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)


class FakeCheckmk(module.Checkmk):
    """Represent fakecheckmk behavior and associated state."""
    def __init__(self):
        """Initialize the instance and its required state."""
        self.closed = []

    def find_candidates(self):
        """Handle find candidates for this module's workflow."""
        return [module.EventCandidate(12, "cmk", "host1", "CPU load")]

    def close_event(self, event_id, site_id):
        """Handle close event for this module's workflow."""
        self.closed.append((event_id, site_id))


def test_dry_run_never_changes_events():
    """Verify that dry run never changes events."""
    client = FakeCheckmk()
    assert client.sync_ec_data(execute=False) == 0
    assert client.closed == []


def test_execute_requires_exact_confirmation():
    """Verify that execute requires exact confirmation."""
    client = FakeCheckmk()
    assert client.sync_ec_data(execute=True, input_fn=lambda _: "yes") == 1
    assert client.closed == []


def test_execute_with_exact_confirmation_archives_candidates():
    """Verify that execute with exact confirmation archives candidates."""
    client = FakeCheckmk()
    assert client.sync_ec_data(execute=True, input_fn=lambda _: "DELETE 1") == 0
    assert client.closed == [(12, "cmk")]


def test_local_automation_secret_accepts_loopback_site_url():
    """Verify that local automation secret accepts loopback site url."""
    module.validate_local_site_url("http://127.0.0.1:5000/cmk/", "cmk")


def test_local_automation_secret_rejects_remote_site_url():
    """Verify that local automation secret rejects remote site url."""
    with pytest.raises(RuntimeError, match="loopback"):
        module.validate_local_site_url("https://monitoring.example/cmk", "cmk")

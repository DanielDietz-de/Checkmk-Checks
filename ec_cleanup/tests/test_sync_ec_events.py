from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "src" / "bin" / "sync_ec_events.py"
spec = spec_from_file_location("sync_ec_events", MODULE_PATH)
module = module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class FakeCheckmk(module.Checkmk):
    def __init__(self):
        self.closed = []

    def find_candidates(self):
        return [module.EventCandidate(12, "cmk", "host1", "CPU load")]

    def close_event(self, event_id, site_id):
        self.closed.append((event_id, site_id))


def test_dry_run_never_changes_events():
    client = FakeCheckmk()
    assert client.sync_ec_data(execute=False) == 0
    assert client.closed == []


def test_execute_requires_exact_confirmation():
    client = FakeCheckmk()
    assert client.sync_ec_data(execute=True, input_fn=lambda _: "yes") == 1
    assert client.closed == []


def test_execute_with_exact_confirmation_archives_candidates():
    client = FakeCheckmk()
    assert client.sync_ec_data(execute=True, input_fn=lambda _: "DELETE 1") == 0
    assert client.closed == [(12, "cmk")]

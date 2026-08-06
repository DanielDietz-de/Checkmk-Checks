"""Focused parser and state-mapping tests for cluster and storage services."""

from conftest import Metric, Result, State, load_plugin


fast = load_plugin("src/cmk_addons_plugins/s2d_hci/agent_based/s2d_hci_fast.py")
storage = load_plugin("src/cmk_addons_plugins/s2d_hci/agent_based/s2d_hci_storage.py")
jobs = load_plugin("src/cmk_addons_plugins/s2d_hci/agent_based/s2d_hci_jobs.py")
health = load_plugin("src/cmk_addons_plugins/s2d_hci/agent_based/s2d_hci_health.py")


def test_node_down_is_critical():
    section = fast.parse_s2d_hci_nodes([["{\"name\":\"NODE02\",\"state\":\"Down\",\"drain_status\":\"NotInitiated\"}"]])
    results = list(fast.check_s2d_hci_nodes("NODE02", section))
    assert any(isinstance(entry, Result) and entry.state == State.CRIT for entry in results)


def test_draining_node_warns():
    section = fast.parse_s2d_hci_nodes([["{\"name\":\"NODE01\",\"state\":\"Up\",\"drain_status\":\"InProgress\"}"]])
    results = list(fast.check_s2d_hci_nodes("NODE01", section))
    assert any(isinstance(entry, Result) and entry.state == State.WARN for entry in results)


def test_csv_emits_free_metric():
    section = storage.parse_s2d_hci_csv([["{\"name\":\"CSV1\",\"state\":\"Online\",\"percent_free\":25.0}"]])
    results = list(storage.check_s2d_hci_csv("CSV1", {"levels_lower_free": ("fixed", (15.0, 10.0))}, section))
    assert any(isinstance(entry, Metric) and entry.name == "s2d_hci_percent_free" for entry in results)


def test_detached_virtual_disk_is_critical():
    section = storage.parse_s2d_hci_virtual_disks(
        [["{\"friendly_name\":\"VD01\",\"health_status\":\"Healthy\",\"operational_status\":\"OK\",\"detached_reason\":\"Lost Communication\"}"]]
    )
    results = list(storage.check_s2d_hci_virtual_disks("VD01", section))
    assert any(isinstance(entry, Result) and entry.state == State.CRIT for entry in results)


def test_running_storage_job_warns_and_emits_progress():
    section = jobs.parse_s2d_hci_storage_jobs([["{\"name\":\"Repair\",\"job_state\":\"Running\",\"percent_complete\":50}"]])
    results = list(jobs.check_s2d_hci_storage_jobs("Repair", section))
    assert any(isinstance(entry, Result) and entry.state == State.WARN for entry in results)
    assert any(isinstance(entry, Metric) and entry.name == "s2d_hci_storage_job_percent" for entry in results)


def test_malformed_storage_job_percentage_does_not_abort_section():
    section = jobs.parse_s2d_hci_storage_jobs([["{\"name\":\"Repair\",\"job_state\":\"Running\",\"percent_complete\":\"n/a\"}"]])
    assert section["Repair"].percent_complete is None


def test_unavailable_health_cmdlet_is_unknown():
    section = health.parse_s2d_hci_s2d_state([["{\"available\":false,\"reason\":\"Command unavailable\"}"]])
    results = list(health.check_s2d_hci_s2d_state(section))
    assert any(isinstance(entry, Result) and entry.state == State.UNKNOWN for entry in results)

"""Focused Hyper-V host and workload behavior tests."""

from conftest import Metric, Result, State, load_plugin


virtualization = load_plugin("src/s2d_hci/agent_based/s2d_hci_virtualization.py")


def test_host_missing_module_is_critical():
    section = virtualization.parse_s2d_hci_virtualization_host(
        [["{\"name\":\"NODE01\",\"service_status\":\"Running\",\"module_available\":false}"]]
    )
    results = list(virtualization.check_s2d_hci_virtualization_host("NODE01", section))
    assert any(isinstance(entry, Result) and entry.state == State.CRIT for entry in results)


def test_workload_off_is_critical():
    section = virtualization.parse_s2d_hci_virtualization_workloads(
        [["{\"name\":\"VM01\",\"state\":\"Off\",\"cpu_usage\":0}"]]
    )
    params = {"levels_upper_cpu": ("fixed", (80.0, 95.0)), "levels_upper_memory_pressure": ("fixed", (100.0, 120.0))}
    results = list(virtualization.check_s2d_hci_virtualization_workloads("VM01", params, section))
    assert any(isinstance(entry, Result) and entry.state == State.CRIT for entry in results)


def test_workload_emits_cpu_and_memory_metrics():
    section = virtualization.parse_s2d_hci_virtualization_workloads(
        [["{\"name\":\"VM01\",\"state\":\"Running\",\"cpu_usage\":25,\"memory_assigned\":100,\"memory_demand\":80}"]]
    )
    params = {"levels_upper_cpu": ("fixed", (80.0, 95.0)), "levels_upper_memory_pressure": ("fixed", (100.0, 120.0))}
    results = list(virtualization.check_s2d_hci_virtualization_workloads("VM01", params, section))
    names = {entry.name for entry in results if isinstance(entry, Metric)}
    assert "s2d_hci_virtualization_workload_cpu_usage" in names
    assert "s2d_hci_virtualization_workload_memory_pressure" in names


def test_enabled_integration_service_without_contact_warns():
    section = virtualization.parse_s2d_hci_virtualization_services(
        [["{\"name\":\"VM01 / Heartbeat\",\"enabled\":true,\"primary_status_description\":\"No Contact\"}"]]
    )
    results = list(virtualization.check_s2d_hci_virtualization_services("VM01 / Heartbeat", section))
    assert any(isinstance(entry, Result) and entry.state == State.WARN for entry in results)


def test_unavailable_replication_is_unknown():
    section = virtualization.parse_s2d_hci_virtualization_replication(
        [["{\"name\":\"replication\",\"available\":false,\"reason\":\"Not installed\"}"]]
    )
    results = list(virtualization.check_s2d_hci_virtualization_replication("replication", section))
    assert any(isinstance(entry, Result) and entry.state == State.UNKNOWN for entry in results)


def test_network_adapter_without_switch_is_critical():
    section = virtualization.parse_s2d_hci_virtualization_network_adapters(
        [["{\"name\":\"VM01 / Network Adapter\",\"connected\":true,\"switch_name\":\"\"}"]]
    )
    results = list(virtualization.check_s2d_hci_virtualization_network_adapters("VM01 / Network Adapter", section))
    assert any(isinstance(entry, Result) and entry.state == State.CRIT for entry in results)


def test_differencing_disk_warns():
    section = virtualization.parse_s2d_hci_virtualization_hard_disks(
        [["{\"name\":\"VM01 / SCSI0:0\",\"path\":\"C:/VMs/disk.avhdx\",\"parent_path\":\"C:/VMs/disk.vhdx\"}"]]
    )
    results = list(virtualization.check_s2d_hci_virtualization_hard_disks("VM01 / SCSI0:0", section))
    assert any(isinstance(entry, Result) and entry.state == State.WARN for entry in results)

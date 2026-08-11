"""Static safety contracts for Windows PowerShell collectors and gMSA tooling."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    """Read one package file as UTF-8 text with normalized line endings so static PowerShell assertions remain platform independent."""

    return (ROOT / relative).read_text(encoding="utf-8")


def test_common_module_enforces_bounds_and_protocol() -> None:
    """Shared collection must enforce protocol, runtime, record, and output limits."""

    text = _read("src/agents/bin/s2d_hci_common.psm1")
    for token in ("protocol_version", "run_id", "max_runtime_seconds", "max_records", "max_output_bytes", "s2d_hci_collector_health"):
        assert token in text
    assert "Get-S2DHciClusterContext" in text
    assert "<<<<$HostName>>>>" in text


def test_sensitive_fields_and_virtualization_default_off() -> None:
    """The committed configuration must minimize sensitive telemetry and disable custom VM collection."""

    text = _read("src/agents/config/s2d_hci.json").lower()
    for key in ("include_addresses", "include_paths", "include_serials", "include_locations", "virtualization_enabled"):
        assert f'"{key}": false' in text


def test_gmsa_task_is_non_elevated_and_bounded() -> None:
    """The scheduled task must avoid elevation and overlapping/unbounded runs."""

    text = _read("tools/windows/Install-S2DHciVirtualizationCollectorTask.ps1")
    assert "-RunLevel Limited" in text
    assert "-RunLevel Highest" not in text
    assert "MultipleInstances IgnoreNew" in text
    assert "ExecutionTimeLimit" in text
    assert "Test-ADServiceAccount" in text
    assert "icacls.exe" in text
    assert "ExecutionPolicy Bypass" not in text


def test_spool_wrapper_preserves_last_good_output() -> None:
    """The spool wrapper must validate process and protocol success before atomic replacement."""

    text = _read("src/agents/scripts/s2d_hci_virtualization_spool.ps1")
    assert "$collectorExitCode = $LASTEXITCODE" in text
    assert "Test-S2DHciCollectorOutput" in text
    assert "unsupported or missing protocol version" in text.lower()
    assert "mixes multiple run identifiers" in text
    assert "File]::Replace" in text
    assert "Assert-S2DHciNoReparsePoint" in text
    assert "ExecutionPolicy Bypass" not in text


def test_cluster_and_vm_piggyback_contracts_exist() -> None:
    """Collectors must use stable logical cluster and VM GUID piggyback identities."""

    fast = _read("src/agents/plugins/s2d_hci_fast.ps1")
    virt = _read("src/agents/plugins/s2d_hci_virtualization.ps1")
    assert "Get-S2DHciClusterContext" in fast
    assert "Start-S2DHciPiggyback" in fast
    assert '"s2d-vm-" + $VmId.Guid' in virt
    assert "virtualization_enabled" in virt


def test_virtualization_vhd_errors_respect_path_privacy_and_preserve_parent_state() -> None:
    """Hyper-V VHD failures must redact path-bearing exception text by default while emitting a non-sensitive differencing-disk flag."""

    text = _read("src/agents/plugins/s2d_hci_virtualization.ps1")
    assert "$record.has_parent" in text
    assert "VHD metadata query failed; path details are redacted by policy." in text
    assert "if ($CollectorConfig.include_paths)" in text
    assert "$record.vhd_error = $_.Exception.Message" not in text

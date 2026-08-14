"""Static safety contracts for Windows PowerShell collectors and gMSA tooling."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    """Read one package file as UTF-8 text with normalized line endings so static PowerShell assertions remain platform independent."""

    return (ROOT / relative).read_text(encoding="utf-8")


def test_common_module_enforces_bounds_and_protocol() -> None:
    """Shared collection must enforce protocol, runtime, record, output, and health-error limits."""

    text = _read("src/agents/bin/s2d_hci_common.psm1")
    for token in (
        "protocol_version",
        "run_id",
        "max_runtime_seconds",
        "max_records",
        "max_output_bytes",
        "s2d_hci_collector_health",
        "$script:S2DHciMaximumHealthErrors = 20",
        "ErrorsOmitted",
        "errors_omitted",
    ):
        assert token in text
    assert "Get-S2DHciClusterContext" in text
    assert "<<<<$HostName>>>>" in text


def test_invalid_config_is_fail_visible_with_safe_defaults() -> None:
    """Malformed or invalid shared config must preserve health output and never leave a partially applied configuration."""

    text = _read("src/agents/bin/s2d_hci_common.psm1")
    assert "$resolved = [ordered]@{}" in text
    assert "configuration_error" in text
    assert "Collector configuration is invalid; safe defaults are active." in text
    assert "$errorMessages.Add([string]$configurationError.Value)" in text
    assert "$complete = $false" in text


def test_sections_stream_without_dynamic_scriptblocks() -> None:
    """Collector sections must stream records through bounded serialization rather than materializing dynamic scriptblock results."""

    common = _read("src/agents/bin/s2d_hci_common.psm1")
    assert "ValueFromPipeline = $true" in common
    assert "Write-S2DHciSectionError" in common
    for relative in (
        "src/agents/plugins/s2d_hci_fast.ps1",
        "src/agents/plugins/s2d_hci_storage.ps1",
        "src/agents/plugins/s2d_hci_jobs.ps1",
        "src/agents/plugins/s2d_hci_health.ps1",
        "src/agents/plugins/s2d_hci_virtualization.ps1",
    ):
        assert "-ScriptBlock" not in _read(relative)


def test_sensitive_fields_and_virtualization_default_off() -> None:
    """The committed configuration must minimize sensitive telemetry and disable custom VM collection."""

    text = _read("src/agents/config/s2d_hci.json").read_text(encoding="utf-8").lower() if False else _read("src/agents/config/s2d_hci.json").lower()
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


def test_gmsa_task_derives_spool_lifetime_from_interval() -> None:
    """The default and custom spool lifetimes must cover at least two scheduled collection intervals."""

    text = _read("tools/windows/Install-S2DHciVirtualizationCollectorTask.ps1")
    for token in (
        "function Get-S2DHciSpoolLifetimeSeconds",
        "[Math]::Max([int64]600, $intervalSeconds * 2)",
        "function Assert-S2DHciSpoolLifetime",
        "$minimumSeconds = [int64]$IntervalMinutes * 120",
        '"{0}_s2d_hci_virtualization.txt" -f $spoolLifetimeSeconds',
        "SpoolLifetimeSeconds=$spoolLifetimeSeconds",
    ):
        assert token in text
    assert "Join-Path $spoolRoot '600_s2d_hci_virtualization.txt'" not in text


def test_gmsa_task_normalizes_and_confines_runtime_paths() -> None:
    """Custom task paths must be canonicalized and remain under the directories whose traversal rights are granted."""

    text = _read("tools/windows/Install-S2DHciVirtualizationCollectorTask.ps1")
    for token in (
        "$CollectorPath = [System.IO.Path]::GetFullPath($CollectorPath)",
        "$WrapperPath = [System.IO.Path]::GetFullPath($WrapperPath)",
        "$ConfigPath = [System.IO.Path]::GetFullPath($ConfigPath)",
        "$SpoolFile = [System.IO.Path]::GetFullPath($SpoolFile)",
        "Spool configuration must be deployed below the Checkmk config directory.",
        "Spool file must remain below the Checkmk spool directory.",
    ):
        assert token in text


def test_gmsa_task_retires_previous_and_removes_derived_spool_state() -> None:
    """Changing lifetime/path and later uninstalling must not leave multiple package spool snapshots active."""

    installer = _read("tools/windows/Install-S2DHciVirtualizationCollectorTask.ps1")
    for token in (
        "function Read-S2DHciPreviousSpoolFile",
        "$previousSpoolFile = Read-S2DHciPreviousSpoolFile",
        "Retire previously configured virtualization spool snapshot",
        "Remove stale target virtualization spool snapshot before reconfiguration",
        "Remove-S2DHciGeneratedFileIfPresent",
        "PreviousSpoolFile=$previousSpoolFile",
    ):
        assert token in installer

    remover = _read("tools/windows/Remove-S2DHciVirtualizationCollectorTask.ps1")
    for token in (
        "function Read-S2DHciConfiguredSpoolFile",
        "$configuredSpoolFile = Read-S2DHciConfiguredSpoolFile",
        "Get-ChildItem -LiteralPath $spoolRoot -File",
        "^\\d+_s2d_hci_virtualization\\.txt$",
        "Remove generated virtualization spool snapshot",
        "Remove generated spool configuration",
    ):
        assert token in remover
    assert "spool\\600_s2d_hci_virtualization.txt" not in remover


def test_gmsa_task_grants_and_verifies_every_runtime_dependency() -> None:
    """The gMSA installer and validator must explicitly cover shared code, configuration, and hardened parent-directory traversal."""

    installer = _read("tools/windows/Install-S2DHciVirtualizationCollectorTask.ps1")
    for token in (
        "$commonModulePath = Join-Path $binRoot 's2d_hci_common.psm1'",
        "$collectorConfigPath = Join-Path $configRoot 's2d_hci.json'",
        "$aclTargets = @(",
        "Path=$AgentRoot",
        "Path=$binRoot",
        "Path=$configRoot",
        "Path=$commonModulePath",
        "Path=$collectorConfigPath",
        "Path=$spoolRoot",
        "FileSystemRights]::ReadAndExecute",
        "FileSystemRights]::Read",
        "FileSystemRights]::Modify",
        "required rights: $RequiredRights",
    ):
        assert token in installer

    validator = _read("tools/windows/Test-S2DHciVirtualizationCollectorIdentity.ps1")
    for token in (
        "AgentRootTraversePresent",
        "BinTraversePresent",
        "ConfigTraversePresent",
        "CommonModuleReadExecutePresent",
        "CollectorConfigReadPresent",
        "SpoolConfigReadPresent",
        "SpoolModifyPresent",
        "Test-S2DHciAclRights",
    ):
        assert token in validator


def test_gmsa_task_honors_should_process_for_acl_mutation() -> None:
    """WhatIf must skip every ACL mutation and the matching post-change verification."""

    text = _read("tools/windows/Install-S2DHciVirtualizationCollectorTask.ps1")
    assert "[CmdletBinding(SupportsShouldProcess = $true)]" in text
    assert "foreach ($target in $aclTargets)" in text
    assert 'if ($PSCmdlet.ShouldProcess($target.Path, "Grant $($target.Permission) NTFS rights to $ServiceAccount"))' in text
    assert "Grant-S2DHciAcl -Path $target.Path" in text
    assert "Assert-S2DHciAclPresent -Path $target.Path" in text
    assert "$status = if ($WhatIfPreference) { 'WhatIf' } else { 'InstalledOrUpdated' }" in text


def test_spool_wrapper_preserves_last_good_output_and_recomputes_bounds() -> None:
    """The spool wrapper must validate native success, exact record accounting, bounded framing, and atomic replacement."""

    text = _read("src/agents/scripts/s2d_hci_virtualization_spool.ps1")
    for token in (
        "$collectorExitCode = $LASTEXITCODE",
        "Test-S2DHciCollectorOutput",
        "unsupported or missing protocol version",
        "mixes multiple run identifiers",
        "$recordBytes -gt $MaximumBytes",
        "$health.output_bytes -ne $recordBytes",
        "$health.record_count -ne $recordCount",
        "$maximumFramingBytes = ([int64]$recordCount + 2) * 1024",
        "$healthBytes -gt 16384",
        "File]::Replace",
        "Assert-S2DHciNoReparsePoint",
    ):
        assert token.lower() in text.lower()
    assert "MaximumBytes + 32768" not in text
    assert "ExecutionPolicy Bypass" not in text


def test_cluster_and_vm_piggyback_contracts_exist() -> None:
    """Collectors must use stable logical cluster and VM GUID piggyback identities."""

    fast = _read("src/agents/plugins/s2d_hci_fast.ps1")
    virt = _read("src/agents/plugins/s2d_hci_virtualization.ps1")
    assert "Get-S2DHciClusterContext" in fast
    assert "Start-S2DHciPiggyback" in fast
    assert '"s2d-vm-" + $VmId.Guid' in virt
    assert "virtualization_enabled" in virt


def test_virtualization_stops_framing_after_truncation() -> None:
    """Direct-mode truncation must prevent later VM, section, and error framing from bypassing configured data bounds."""

    text = _read("src/agents/plugins/s2d_hci_virtualization.ps1")
    assert text.count("if ($RunContext.Truncated) { return }") >= 6
    first_guard = text.index("if ($RunContext.Truncated) { return }")
    first_piggyback = text.index("Start-S2DHciPiggyback -HostName $vmHost")
    assert first_guard < first_piggyback
    assert text.count("if (-not $RunContext.Truncated) { Write-S2DHciSectionError") >= 6
    assert "if (-not $context.Truncated) { Write-S2DHciSectionError" in text
    assert "if (-not $context.Truncated)" in text


def test_virtualization_vhd_errors_respect_path_privacy_and_pass_through_disks() -> None:
    """VHD failures must redact paths while pathless pass-through disks must bypass Get-VHD without a synthetic metadata error."""

    text = _read("src/agents/plugins/s2d_hci_virtualization.ps1")
    assert "$record.has_parent" in text
    assert "VHD metadata query failed; path details are redacted by policy." in text
    assert "$isPassThrough" in text
    assert "$attachmentType = 'pass_through'" in text
    assert "attachment_type = $attachmentType" in text
    assert "if (-not [string]::IsNullOrWhiteSpace($drivePath) -and (Test-S2DHciCommandAvailable -Name 'Get-VHD'))" in text
    assert "$record.vhd_error = $_.Exception.Message" not in text

"""Static contracts for PowerShell deployment and collector behavior."""

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
COLLECTOR_PATHS = (
    "src/agents/plugins/s2d_hci_fast.ps1",
    "src/agents/plugins/s2d_hci_storage.ps1",
    "src/agents/plugins/s2d_hci_health.ps1",
    "src/agents/plugins/s2d_hci_jobs.ps1",
    "src/agents/plugins/s2d_hci_perf.ps1",
)


def test_s2d_collector_normalizes_native_cmdlet_output():
    text = (PACKAGE_ROOT / "src/agents/plugins/s2d_hci_health.ps1").read_text(encoding="utf-8")
    assert "ConvertTo-S2DStateRecord" in text
    assert "source_command" in text
    assert "state =" in text
    assert "Get-ClusterStorageSpacesDirect | Write-JsonLine" not in text
    assert "Get-ClusterS2D | Write-JsonLine" not in text


def test_spool_wrapper_accepts_the_installer_agent_root():
    wrapper = (PACKAGE_ROOT / "src/agents/scripts/s2d_hci_virtualization_spool.ps1").read_text(encoding="utf-8")
    installer_path = PACKAGE_ROOT / "tools/windows/Install-S2DHciVirtualizationCollectorTask.ps1"
    if installer_path.exists():
        installer = installer_path.read_text(encoding="utf-8")
        assert '-AgentRoot `"$AgentRoot`"' in installer
    assert "[string]$AgentRoot" in wrapper
    assert "GetFullPath($AgentRoot)" in wrapper


def test_spool_wrapper_preserves_last_good_data_on_native_failure():
    wrapper = (PACKAGE_ROOT / "src/agents/scripts/s2d_hci_virtualization_spool.ps1").read_text(encoding="utf-8")
    exit_check = wrapper.index("$collectorExitCode = $LASTEXITCODE")
    replacement = wrapper.index("[System.IO.File]::WriteAllLines")
    assert exit_check < replacement
    assert "if ($collectorExitCode -ne 0)" in wrapper
    assert "the last valid spool file was preserved" in wrapper


def test_collectors_emit_structured_required_module_failures():
    for relative_path in COLLECTOR_PATHS:
        text = (PACKAGE_ROOT / relative_path).read_text(encoding="utf-8")
        assert "function Import-CollectorModules" in text
        assert "Import-Module $module -ErrorAction Stop" in text
        assert "Required module import failed:" in text
        assert "success = $false" in text
        assert "exit 0" in text

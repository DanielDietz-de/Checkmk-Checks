"""Static contracts for PowerShell deployment and collector behavior."""

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


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

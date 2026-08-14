"""Static contract tests for the Windows PowerShell collector.

The repository CI environment is Linux and does not execute Windows PowerShell.
These tests pin security- and behavior-critical source invariants; live Windows
acceptance remains documented separately.
"""

from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = (PACKAGE / "src/agents/windows/plugins/aruba_central_aps.ps1").read_text(
    encoding="utf-8"
)
ASYNC_CONFIG = (
    PACKAGE
    / "src/agents/windows/cfg_examples/check_mk.user.aruba_central_aps.yml"
).read_text(encoding="utf-8")


def test_captures_stdout_and_stderr_without_shell_execution():
    assert "$startInfo.UseShellExecute = $false" in SCRIPT
    assert "$startInfo.RedirectStandardOutput = $true" in SCRIPT
    assert "$startInfo.RedirectStandardError = $true" in SCRIPT
    assert "$process.StandardOutput.ReadToEndAsync()" in SCRIPT
    assert "$process.StandardError.ReadToEndAsync()" in SCRIPT
    assert "Invoke-Expression" not in SCRIPT


def test_detects_json_and_diagnostics_streams():
    assert "$jsonStream = 'stdout'" in SCRIPT
    assert "$jsonStream = 'stderr'" in SCRIPT
    assert "$jsonStream = 'combined'" in SCRIPT
    assert "function Find-DiagnosticMatch" in SCRIPT
    assert "counts_stream" in SCRIPT
    assert "rate_limit_stream" in SCRIPT
    assert "Stream = 'both'" in SCRIPT
    assert "$countResult.Stream = 'derived'" in SCRIPT


def test_requested_host_naming_rule_is_implemented():
    assert "$nameIsMac" in SCRIPT
    assert '"AP_$Serial"' in SCRIPT
    assert '"AP_$compactMac"' in SCRIPT
    assert "[^A-Za-z0-9_.-]+" in SCRIPT


def test_piggyback_host_name_collisions_fail_closed_before_cache_write():
    assert "function Assert-UniqueHostNames" in SCRIPT
    assert "$seen.ContainsKey($hostName)" in SCRIPT
    assert "Duplicate Aruba AP piggyback host name" in SCRIPT
    check = SCRIPT.index("Assert-UniqueHostNames -AccessPoints $accessPoints")
    cache_write = SCRIPT.index("Write-AtomicJson -Path")
    output = SCRIPT.index("Write-MonitoringOutput -Collector $collector")
    assert check < cache_write < output


def test_authoritative_ap_count_mismatch_fails_before_cache_write():
    assert "$diagnostics.counts_stream -ne 'derived'" in SCRIPT
    assert "cencli AP count mismatch" in SCRIPT
    validation = SCRIPT.index("cencli AP count mismatch")
    cache_write = SCRIPT.index("Write-AtomicJson -Path")
    output = SCRIPT.index("Write-MonitoringOutput -Collector $collector")
    assert validation < cache_write < output


def test_configuration_failures_enter_monitoring_failure_handler():
    default_config = SCRIPT.index("$config = Get-DefaultConfig")
    try_block = SCRIPT.index("try {", default_config)
    config_read = SCRIPT.index("$config = Read-Configuration -Path $ConfigFile", try_block)
    invocation = SCRIPT.index("$execution = Invoke-Cencli -Config $config", config_read)
    assert default_config < try_block < config_read < invocation


def test_last_good_cache_is_not_replaced_in_failure_handler():
    success, failure = SCRIPT.rsplit("\ncatch {", 1)
    assert "Write-AtomicJson" in success
    assert "Write-AtomicJson" not in failure
    assert "using last-known-good AP data" in failure
    assert "MaxStaleSeconds" in SCRIPT


def test_agent_execution_is_explicitly_asynchronous():
    assert "async: yes" in ASYNC_CONFIG
    assert "timeout: 90" in ASYNC_CONFIG
    assert "cache_age: 300" in ASYNC_CONFIG

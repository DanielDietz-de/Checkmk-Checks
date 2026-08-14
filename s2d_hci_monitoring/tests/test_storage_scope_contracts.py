"""Regression contracts that keep logical S2D storage monitoring strictly cluster-scoped."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _storage_collector() -> str:
    """Return the Windows storage collector source used for static scope validation."""

    return (ROOT / "src/agents/plugins/s2d_hci_storage.ps1").read_text(encoding="utf-8")


def test_pool_derived_sections_are_restricted_to_clustered_non_primordial_pools() -> None:
    """Logical cluster storage must exclude node-local pools and OS/recovery storage."""

    text = _storage_collector()
    clustered_filter = "Where-Object { -not $_.IsPrimordial -and [bool]$_.IsClustered }"
    assert text.count(clustered_filter) >= 4
    assert "Get-StoragePool -ErrorAction Stop | Where-Object { -not $_.IsPrimordial }" not in text


def test_volume_services_are_resolved_from_clustered_storage_pools_only() -> None:
    """Volume discovery must not call unfiltered Get-Volume on the elected physical node."""

    text = _storage_collector()
    assert "Get-Volume -StoragePool $pool -ErrorAction Stop" in text
    assert "Get-Volume -ErrorAction Stop" not in text
    assert 'identity = "vol-$(Get-S2DHciStableHash -Value $stableSource)"' in text
    assert "$stableSource = if ($_.UniqueId)" in text


def test_virtual_and_physical_disk_services_follow_the_same_cluster_pool_scope() -> None:
    """Related Storage Spaces objects must stay bound to the same clustered pool boundary."""

    text = _storage_collector()
    assert "Get-VirtualDisk -StoragePool $pool -ErrorAction Stop" in text
    assert "Get-PhysicalDisk -StoragePool $pool -ErrorAction Stop" in text
    assert "Get-VirtualDisk -ErrorAction Stop" not in text
    assert "Get-PhysicalDisk -ErrorAction Stop" not in text

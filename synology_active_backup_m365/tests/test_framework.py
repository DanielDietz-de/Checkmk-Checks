from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_inventory_exists() -> None:
    manifest = ast.literal_eval((ROOT / "src" / "info").read_text(encoding="utf-8"))
    assert manifest["name"] == "synology_active_backup_m365"
    assert manifest["version.min_required"] == "2.5.0"

    files = manifest["files"]["cmk_addons_plugins"]
    assert files
    for relative_path in files:
        assert (ROOT / "src" / relative_path).is_file(), relative_path


def test_status_fixtures_match_required_contract() -> None:
    fixtures = sorted((ROOT / "tests" / "fixtures").glob("status_*.json"))
    assert fixtures

    for fixture in fixtures:
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        assert isinstance(payload["health"], dict)
        assert isinstance(payload["jobs"], list)
        assert isinstance(payload["sources"], list)


def test_task_id_is_the_discovery_identity() -> None:
    source = (
        ROOT
        / "src"
        / "synology_active_backup_m365"
        / "agent_based"
        / "synology_active_backup_m365.py"
    ).read_text(encoding="utf-8")

    assert 'job.get("task_id"' in source
    assert 'Service(item="Health")' in source
    assert 'service_name="Synology M365 Backup %s"' in source

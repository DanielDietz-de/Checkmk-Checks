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


def test_live_fixture_proves_global_health_is_not_product_health() -> None:
    payload = json.loads(
        (
            ROOT
            / "tests"
            / "fixtures"
            / "status_live_warning_unrelated_abb_missing.json"
        ).read_text(encoding="utf-8")
    )

    assert payload["health"]["ok"] is False
    assert payload["health"]["db_missing"] == ["abb"]

    m365_sources = [
        source for source in payload["sources"] if source.get("product") == "m365"
    ]
    assert len(m365_sources) == 1
    assert m365_sources[0]["found"] is True

    m365_jobs = [job for job in payload["jobs"] if job.get("product") == "m365"]
    assert len(m365_jobs) == 1
    assert m365_jobs[0]["status"] == 2
    assert m365_jobs[0]["raw_status"] == "6"
    assert m365_jobs[0]["last_success_age_seconds"] > 48 * 3600


def test_m365_health_logic_ignores_unrelated_missing_products() -> None:
    source = (
        ROOT
        / "src"
        / "synology_active_backup_m365"
        / "agent_based"
        / "synology_active_backup_m365.py"
    ).read_text(encoding="utf-8")

    assert 'product.lower() == "m365"' in source
    assert 'product.lower() != "m365"' in source
    assert 'if health.get("ok") is not True:' not in source
    assert "_m365_collection_errors" in source


def test_default_last_success_levels_are_30h_and_48h() -> None:
    agent_source = (
        ROOT
        / "src"
        / "synology_active_backup_m365"
        / "agent_based"
        / "synology_active_backup_m365.py"
    ).read_text(encoding="utf-8")
    rules_source = (
        ROOT
        / "src"
        / "synology_active_backup_m365"
        / "rulesets"
        / "check_parameters.py"
    ).read_text(encoding="utf-8")

    assert "30.0 * 3600.0" in agent_source
    assert "48.0 * 3600.0" in agent_source
    assert "108000.0" in rules_source
    assert "172800.0" in rules_source

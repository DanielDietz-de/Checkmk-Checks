"""Tests for dry-run-first Checkmk host synchronization."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path
import re
import stat
import sys
from typing import Any

import pytest

PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE / "src/aruba_central/libexec/sync_aruba_central_hosts"
FIXTURE = PACKAGE / "tests/fixtures/sample_agent_output.txt"
MAPPING = PACKAGE / "src/aruba_central/deployment/group_site_map.example.json"


def _load():
    loader = importlib.machinery.SourceFileLoader(
        "aruba_central_host_sync_test",
        str(SCRIPT),
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


def test_extract_and_plan_exact_folder_hierarchy():
    sync = _load()
    access_points = sync._extract_access_points(FIXTURE.read_text(encoding="utf-8"))
    assert [ap["host_name"] for ap in access_points] == [
        "AP_CNRPKV30C2",
        "B200-AP-01",
    ]
    planned = sync._plan(access_points, sync._load_mapping(MAPPING))
    by_name = {host.host_name: host for host in planned}
    bornheim = by_name["AP_CNRPKV30C2"]
    b200 = by_name["B200-AP-01"]
    assert bornheim.folder_path == "/campus_bornheim/accesspoint"
    assert bornheim.folder_id == "~campus_bornheim~accesspoint"
    assert b200.folder_path == "/b200/accesspoint"
    assert b200.folder_id == "~b200~accesspoint"


def test_mapping_fails_closed_for_unknown_site():
    sync = _load()
    access_points = sync._extract_access_points(FIXTURE.read_text(encoding="utf-8"))
    access_points[0]["site"] = "Campus Bornheim - UNKNOWN"
    with pytest.raises(ValueError, match="synchronization plan validation failed"):
        sync._plan(access_points, sync._load_mapping(MAPPING))


def test_extract_fails_closed_on_malformed_ap_json():
    sync = _load()
    output = "\n".join(
        [
            "<<<<AP-BROKEN>>>>",
            sync.SECTION,
            '{"schema":1,"kind":"ap","ap":',
            "<<<<>>>>",
        ]
    )
    with pytest.raises(ValueError, match="invalid Aruba AP JSON"):
        sync._extract_access_points(output)


def test_extract_fails_closed_on_truncated_ap_section():
    sync = _load()
    output = "\n".join(["<<<<AP-BROKEN>>>>", sync.SECTION])
    with pytest.raises(ValueError, match="section is truncated"):
        sync._extract_access_points(output)


def test_extract_rejects_duplicate_piggyback_host_names():
    sync = _load()
    payload = json.dumps(
        {
            "schema": 1,
            "kind": "ap",
            "ap": {
                "host_name": "AP_DUP",
                "group": "B200",
                "site": "B200",
            },
        }
    )
    output = "\n".join(
        [
            "<<<<AP_DUP>>>>",
            sync.SECTION,
            payload,
            "<<<<>>>>",
            "<<<<ap_dup>>>>",
            sync.SECTION,
            payload,
            "<<<<>>>>",
        ]
    )
    with pytest.raises(ValueError, match="duplicate Aruba AP piggyback host names"):
        sync._extract_access_points(output)


def test_plan_rejects_colliding_normalized_group_ids():
    sync = _load()
    mapping = {
        "Campus A": [re.compile(r"^Site A$")],
        "Campus_A": [re.compile(r"^Site B$")],
    }
    access_points = [
        {"host_name": "AP-1", "group": "Campus A", "site": "Site A"},
        {"host_name": "AP-2", "group": "Campus_A", "site": "Site B"},
    ]
    with pytest.raises(ValueError, match="normalizes to folder ID 'campus_a'"):
        sync._plan(access_points, mapping)


def test_default_execution_is_dry_run(capsys):
    sync = _load()
    result = sync.main(
        [
            "--agent-output-file",
            str(FIXTURE),
            "--mapping",
            str(MAPPING),
        ]
    )
    captured = capsys.readouterr()
    assert result == 0
    assert "FOLDER /campus_bornheim/accesspoint title='Accesspoint'" in captured.out
    assert "DRY-RUN no Checkmk configuration was changed" in captured.out


def test_apply_requires_separate_credentials(capsys):
    sync = _load()
    result = sync.main(
        [
            "--agent-output-file",
            str(FIXTURE),
            "--mapping",
            str(MAPPING),
            "--apply",
        ]
    )
    captured = capsys.readouterr()
    assert result == 2
    assert "--apply requires --api-url, --username, and --secret-file" in captured.err


def test_secret_file_permissions_are_restricted(tmp_path):
    sync = _load()
    secret = tmp_path / "secret"
    secret.write_text("not-a-real-secret\n", encoding="utf-8")
    secret.chmod(0o644)
    if sys.platform != "win32":
        with pytest.raises(PermissionError):
            sync._read_secret(secret)
    secret.chmod(stat.S_IRUSR | stat.S_IWUSR)
    assert sync._read_secret(secret) == "not-a-real-secret"


def test_rest_client_has_secure_defaults():
    sync = _load()
    client = sync.CheckmkApi(
        "https://checkmk.example/site/check_mk/api/v1",
        "automation",
        "secret",
        None,
        30,
    )
    assert client.session.trust_env is False
    assert client.verify is True
    assert client.base_url.endswith("/api/v1")
    assert client.session.headers["Authorization"] == "Bearer automation secret"


def test_rest_client_rejects_wrong_api_path():
    sync = _load()
    with pytest.raises(ValueError, match="must end with /check_mk/api/v1"):
        sync.CheckmkApi(
            "https://checkmk.example/site/check_mk/api/1.0",
            "automation",
            "secret",
            None,
            30,
        )


def test_rest_client_rejects_plain_http_for_remote_hosts():
    sync = _load()
    with pytest.raises(ValueError, match="must use HTTPS"):
        sync.CheckmkApi(
            "http://checkmk.example/site/check_mk/api/v1",
            "automation",
            "secret",
            None,
            30,
        )


def test_rest_client_allows_loopback_http_for_local_site_access():
    sync = _load()
    client = sync.CheckmkApi(
        "http://127.0.0.1/site/check_mk/api/v1",
        "automation",
        "secret",
        None,
        30,
    )
    assert client.base_url.startswith("http://127.0.0.1/")


class _Response:
    def __init__(
        self,
        status_code: int,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}
        self.text = text

    def json(self):
        if self._body is None:
            raise ValueError("no JSON")
        return self._body


class _Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return next(self.responses)


def test_duplicate_classification_requires_explicit_already_exists():
    sync = _load()
    assert sync.CheckmkApi._already_exists(
        _Response(409, text="Object already exists")
    )
    assert sync.CheckmkApi._already_exists(
        _Response(422, {"detail": "Host already exists"}, text="validation failed")
    )
    assert not sync.CheckmkApi._already_exists(
        _Response(409, text="Parent folder does not exist")
    )
    assert not sync.CheckmkApi._already_exists(
        _Response(422, text="Folder does not exist")
    )


def test_non_duplicate_creation_error_is_not_suppressed():
    sync = _load()
    client = sync.CheckmkApi(
        "https://checkmk.example/site/check_mk/api/v1",
        "automation",
        "secret",
        None,
        30,
    )
    client.session = _Session([_Response(409, text="Parent folder does not exist")])
    with pytest.raises(RuntimeError, match="folder creation failed"):
        client.create_folder("accesspoint", "Accesspoint", "~missing")


def test_folder_and_host_requests_use_checkmk_object_ids():
    sync = _load()
    client = sync.CheckmkApi(
        "https://checkmk.example/site/check_mk/api/v1",
        "automation",
        "secret",
        None,
        30,
    )
    fake = _Session([_Response(201), _Response(201), _Response(201)])
    client.session = fake
    host = sync.PlannedHost(
        host_name="AP-01",
        group_title="Campus Bornheim",
        group_id="campus_bornheim",
        folder_id="~campus_bornheim~accesspoint",
        folder_path="/campus_bornheim/accesspoint",
        site="Campus Bornheim - ABS5",
        serial="SERIAL",
        mac="00:11:22:33:44:55",
    )
    assert client.create_folder("campus_bornheim", "Campus Bornheim", "~") == "created"
    assert (
        client.create_folder("accesspoint", "Accesspoint", "~campus_bornheim")
        == "created"
    )
    assert client.create_host(host) == "created"
    assert fake.calls[0][2]["json"]["parent"] == "~"
    assert fake.calls[1][2]["json"]["parent"] == "~campus_bornheim"
    assert fake.calls[2][2]["json"]["folder"] == "~campus_bornheim~accesspoint"


def test_activation_reads_pending_etag_and_sends_if_match():
    sync = _load()
    client = sync.CheckmkApi(
        "https://checkmk.example/site/check_mk/api/v1",
        "automation",
        "secret",
        None,
        30,
    )
    fake = _Session(
        [
            _Response(
                200,
                {"value": [{"id": "change"}]},
                {"ETag": '"etag-value"'},
            ),
            _Response(202, {"id": "activation"}),
        ]
    )
    client.session = fake
    assert client.activate("site") == "submitted"
    assert fake.calls[0][0] == "GET"
    assert fake.calls[0][1].endswith(
        "/domain-types/activation_run/collections/pending_changes"
    )
    assert fake.calls[1][2]["headers"] == {"If-Match": '"etag-value"'}


def test_activation_skips_when_no_changes_are_pending():
    sync = _load()
    client = sync.CheckmkApi(
        "https://checkmk.example/site/check_mk/api/v1",
        "automation",
        "secret",
        None,
        30,
    )
    fake = _Session([_Response(200, {"value": []}, {"ETag": '"etag-value"'})])
    client.session = fake
    assert client.activate("site") == "no-pending-changes"
    assert len(fake.calls) == 1

from __future__ import annotations

import json
from pathlib import Path


DEPLOYMENT_DIR = Path(__file__).parents[1] / "src/oxidized_backup/deployment"


def test_example_configuration_is_valid_json_and_has_no_real_credentials() -> None:
    path = DEPLOYMENT_DIR / "oxidized_backup.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    assert config["git"]["run_as_user"] == "oxidized"
    serialized = json.dumps(config).lower()
    assert "password" not in serialized
    assert "token" not in serialized
    assert "rkg" not in serialized
    assert "rau" not in serialized


def test_hook_example_references_packaged_paths() -> None:
    text = (DEPLOYMENT_DIR / "oxidized_backup-hook.yml").read_text(
        encoding="utf-8"
    )
    assert "/usr/lib/check_mk_agent/plugins/300/oxidized_backup" in text
    assert "--config /etc/check_mk/oxidized_backup.json" in text
    assert "node_success" in text
    assert "node_fail" in text
    assert "post_store" in text

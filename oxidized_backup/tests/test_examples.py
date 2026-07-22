from __future__ import annotations

import json
from pathlib import Path


def test_example_configuration_is_valid_json_and_has_no_real_credentials() -> None:
    path = Path(__file__).parents[1] / "examples/oxidized_backup.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    assert config["git"]["run_as_user"] == "oxidized"
    serialized = json.dumps(config).lower()
    assert "password" not in serialized
    assert "token" not in serialized
    assert "rkg" not in serialized
    assert "rau" not in serialized

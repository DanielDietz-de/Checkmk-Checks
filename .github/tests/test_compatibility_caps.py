from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_release_preparation_preserves_explicit_cap() -> None:
    prepare = _load(
        "prepare_repository_mkp_release_cap_test",
        REPOSITORY / ".github/scripts/prepare_repository_mkp_release.py",
    )

    assert (
        prepare._release_usable_until(
            {"version.usable_until": "2.2.99"},
            "2.5.99",
        )
        == "2.2.99"
    )
    assert prepare._release_usable_until({}, "2.5.99") == "2.5.99"

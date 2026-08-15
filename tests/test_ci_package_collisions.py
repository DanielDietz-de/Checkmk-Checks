from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools/ci/check_package_collisions.py"


def _load():
    """Handle load for this module's workflow."""
    spec = importlib.util.spec_from_file_location("check_package_collisions", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _package(
    root: Path,
    directory: str,
    *,
    name: str | None = None,
    files: dict[str, list[str]] | None = None,
    source: str = "",
) -> None:
    """Handle package for this module's workflow."""
    package = root / directory
    (package / "src").mkdir(parents=True)
    manifest = {
        "name": name or directory,
        "title": directory,
        "author": "test",
        "description": "test",
        "version": "1.0.0",
        "version.min_required": "2.4.0",
        "files": files or {},
    }
    (package / "src/info").write_text(repr(manifest), encoding="utf-8")
    if source:
        plugin = package / "src/plugin.py"
        plugin.write_text(source, encoding="utf-8")


class PackageCollisionTests(unittest.TestCase):
    """Represent packagecollisiontests behavior and associated state."""
    def setUp(self) -> None:
        """Handle setup for this module's workflow."""
        self.module = _load()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        """Handle teardown for this module's workflow."""
        self.tempdir.cleanup()

    def test_distinct_packages_have_no_collisions(self) -> None:
        """Verify that distinct packages have no collisions."""
        _package(
            self.root,
            "alpha",
            files={"cmk_addons_plugins": ["alpha/agent_based/alpha.py"]},
            source='CheckPlugin(name="alpha")\n',
        )
        _package(
            self.root,
            "beta",
            files={"cmk_addons_plugins": ["beta/agent_based/beta.py"]},
            source='CheckPlugin(name="beta")\n',
        )
        self.assertEqual(self.module.find_collisions(self.root), [])

    def test_duplicate_package_name_is_reported(self) -> None:
        """Verify that duplicate package name is reported."""
        _package(self.root, "alpha", name="same")
        _package(self.root, "beta", name="same")
        collisions = self.module.find_collisions(self.root)
        self.assertEqual(collisions[0].kind, "package_name")
        self.assertEqual(collisions[0].packages, ("alpha", "beta"))

    def test_duplicate_packaged_destination_is_reported(self) -> None:
        """Verify that duplicate packaged destination is reported."""
        files = {"agents": ["plugins/shared"]}
        _package(self.root, "alpha", files=files)
        _package(self.root, "beta", files=files)
        collisions = self.module.find_collisions(self.root)
        self.assertEqual(collisions[0].kind, "packaged_path:agents")
        self.assertEqual(collisions[0].identity, "plugins/shared")

    def test_duplicate_static_check_registration_is_reported(self) -> None:
        """Verify that duplicate static check registration is reported."""
        source = 'CheckPlugin(\n    name="shared_check",\n)\n'
        _package(self.root, "alpha", source=source)
        _package(self.root, "beta", source=source)
        collisions = self.module.find_collisions(self.root)
        self.assertEqual(collisions[0].kind, "check_plugin")
        self.assertEqual(collisions[0].identity, "shared_check")

    def test_unsafe_manifest_path_is_rejected(self) -> None:
        """Verify that unsafe manifest path is rejected."""
        _package(self.root, "alpha", files={"agents": ["../escape"]})
        with self.assertRaisesRegex(ValueError, "unsafe agents package path"):
            self.module.find_collisions(self.root)


if __name__ == "__main__":
    unittest.main()

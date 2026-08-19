from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools/ci/normalize_package_sources.py"


def _load():
    """Handle load for this module's workflow."""
    spec = importlib.util.spec_from_file_location("normalize_package_sources", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PackageSourceNormalizationTests(unittest.TestCase):
    """Represent packagesourcenormalizationtests behavior and associated state."""
    def setUp(self) -> None:
        """Handle setup for this module's workflow."""
        self.module = _load()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        """Handle teardown for this module's workflow."""
        self.tempdir.cleanup()

    def _legacy_bakery_package(self, name: str = "example") -> Path:
        """Handle legacy bakery package for this module's workflow."""
        package = self.root / name
        legacy = package / "src" / name / "agent_based" / "bakery.py"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(
            "from cmk.base.cee.plugins.bakery.bakery_api.v1 import register\n",
            encoding="utf-8",
        )
        manifest = {
            "name": name,
            "version": "1.0.0",
            "files": {"cmk_addons_plugins": [f"{name}/agent_based/bakery.py"]},
        }
        (package / "src/info").write_text(repr(manifest), encoding="utf-8")
        (package / "README.md").write_text(
            "# Example\n\n"
            "| Path | Purpose |\n"
            "| --- | --- |\n"
            f"| `src/{name}/agent_based/bakery.py` | Bakery hook. |\n"
            f"| `src/agents/bakery/{name}` | Historical Bakery hook. |\n",
            encoding="utf-8",
        )
        return package

    def test_check_mode_reports_pending_migration_without_writing(self) -> None:
        """Verify that check mode reports pending migration without writing."""
        package = self._legacy_bakery_package()
        changes = self.module.normalize_repository(self.root, write=False)
        self.assertTrue(changes)
        self.assertTrue((package / "src/example/agent_based/bakery.py").is_file())
        self.assertFalse(
            (package / "src/lib/python3/cmk/base/cee/plugins/bakery/example.py").exists()
        )

    def test_write_mode_moves_bakery_updates_manifest_and_readme(self) -> None:
        """Verify that write mode moves bakery updates manifest and readme."""
        package = self._legacy_bakery_package()
        changes = self.module.normalize_repository(self.root, write=True)
        self.assertTrue(changes)
        target = package / "src/lib/python3/cmk/base/cee/plugins/bakery/example.py"
        self.assertTrue(target.is_file())
        self.assertIn("from .bakery_api.v1 import", target.read_text(encoding="utf-8"))
        self.assertFalse((package / "src/example/agent_based/bakery.py").exists())
        manifest = (package / "src/info").read_text(encoding="utf-8")
        self.assertIn("python3/cmk/base/cee/plugins/bakery/example.py", manifest)
        self.assertNotIn("example/agent_based/bakery.py", manifest)
        readme = (package / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "`src/lib/python3/cmk/base/cee/plugins/bakery/example.py`",
            readme,
        )
        self.assertNotIn("agent_based/bakery.py", readme)
        self.assertNotIn("src/agents/bakery/", readme)
        self.assertEqual(self.module.normalize_repository(self.root, write=False), [])

    def test_stale_readme_is_detected_after_source_is_normalized(self) -> None:
        """Verify that stale readme is detected after source is normalized."""
        package = self._legacy_bakery_package()
        self.module.normalize_repository(self.root, write=True)
        (package / "README.md").write_text(
            "`src/example/agent_based/bakery.py`\n",
            encoding="utf-8",
        )
        changes = self.module.normalize_repository(self.root, write=False)
        self.assertIn(
            self.module.SourceChange("write", "example/README.md"),
            changes,
        )

    def test_unsupported_bakery_import_fails_closed(self) -> None:
        """Verify that unsupported bakery import fails closed."""
        package = self._legacy_bakery_package()
        legacy = package / "src/example/agent_based/bakery.py"
        legacy.write_text("from unsupported import register\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unsupported Bakery API import"):
            self.module.normalize_repository(self.root, write=False)


if __name__ == "__main__":
    unittest.main()

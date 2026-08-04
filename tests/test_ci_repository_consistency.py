"""Tests for deterministic metadata, documentation, docstring, and syntax gates."""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).parents[1]
metadata_sync = load_module(ROOT / "tools" / "ci" / "sync_package_metadata.py", "metadata_sync_test")
reference = load_module(ROOT / "tools" / "ci" / "generate_package_reference.py", "reference_test")
docstrings = load_module(ROOT / "tools" / "ci" / "manage_module_docstrings.py", "docstrings_test")
syntax = load_module(ROOT / "tools" / "ci" / "check_python_syntax.py", "syntax_test")


class RepositoryConsistencyTests(unittest.TestCase):
    def make_package(self, temporary: str) -> Path:
        root = Path(temporary)
        package = root / "example"
        source = package / "src" / "example" / "agent_based"
        source.mkdir(parents=True)
        data = {
            "name": "example",
            "title": "Example",
            "description": "Example integration",
            "version": "1.0.0",
            "version.min_required": "2.4.0",
            "version.packaged": "2.5.0",
            "version.usable_until": None,
            "files": {"cmk_addons_plugins": ["example/agent_based/plugin.py"]},
        }
        (package / "src" / "info").write_text(repr(data), encoding="utf-8")
        (package / "src" / "info.json").write_text("{}\n", encoding="utf-8")
        (package / "README.md").write_text("# Example\n", encoding="utf-8")
        (source / "plugin.py").write_text("VALUE = 1\n", encoding="utf-8")
        return root

    def test_metadata_mirror_is_exactly_regenerated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_package(temporary)
            self.assertTrue(metadata_sync.run(root, write=False))
            self.assertEqual(metadata_sync.run(root, write=True), [])
            canonical = ast.literal_eval((root / "example/src/info").read_text(encoding="utf-8"))
            mirrored = json.loads((root / "example/src/info.json").read_text(encoding="utf-8"))
            self.assertEqual(mirrored, canonical)
            self.assertEqual(metadata_sync.run(root, write=False), [])

    def test_code_derived_reference_detects_and_repairs_staleness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_package(temporary)
            self.assertTrue(reference.run(root, write=False))
            self.assertEqual(reference.run(root, write=True), [])
            self.assertEqual(reference.run(root, write=False), [])
            readme = root / "example/README.md"
            self.assertIn(reference.START, readme.read_text(encoding="utf-8"))

    def test_module_docstring_gate_repairs_missing_docstring(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_package(temporary)
            self.assertTrue(docstrings.run(root, write=False))
            self.assertEqual(docstrings.run(root, write=True), [])
            self.assertEqual(docstrings.run(root, write=False), [])
            module = root / "example/src/example/agent_based/plugin.py"
            self.assertIsNotNone(ast.get_docstring(ast.parse(module.read_text(encoding="utf-8"))))

    def test_repository_syntax_gate_covers_legacy_extensionless_checks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checks = root / "archiv" / "legacy" / "src" / "checks"
            checks.mkdir(parents=True)
            broken = checks / "legacy_check"
            broken.write_text("def broken(:\n", encoding="utf-8")
            errors = syntax.validate(root)
            self.assertTrue(any("legacy_check" in error for error in errors))
            broken.write_text("def valid():\n    return True\n", encoding="utf-8")
            self.assertEqual(syntax.validate(root), [])


if __name__ == "__main__":
    unittest.main()

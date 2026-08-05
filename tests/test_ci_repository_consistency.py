"""Tests for deterministic metadata, documentation, packaging, and audit gates."""

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
metadata_sync = load_module(
    ROOT / "tools" / "ci" / "sync_package_metadata.py",
    "metadata_sync_test",
)
reference = load_module(
    ROOT / "tools" / "ci" / "generate_package_reference.py",
    "reference_test",
)
facts = load_module(
    ROOT / "tools" / "ci" / "sync_repository_facts.py",
    "facts_test",
)
docstrings = load_module(
    ROOT / "tools" / "ci" / "manage_module_docstrings.py",
    "docstrings_test",
)
syntax = load_module(
    ROOT / "tools" / "ci" / "check_python_syntax.py",
    "syntax_test",
)
full_audit = load_module(
    ROOT / "tools" / "ci" / "full_repository_audit.py",
    "full_repository_audit_test",
)
builder = load_module(
    ROOT / ".github" / "scripts" / "build_repository_mkps.py",
    "builder_test",
)


class RepositoryConsistencyTests(unittest.TestCase):
    """Exercise code-derived repository consistency mechanisms."""

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
            "files": {
                "cmk_addons_plugins": ["example/agent_based/plugin.py"]
            },
        }
        (package / "src" / "info").write_text(
            repr(data),
            encoding="utf-8",
        )
        (package / "src" / "info.json").write_text("{}\n", encoding="utf-8")
        (package / "README.md").write_text("# Example\n", encoding="utf-8")
        (source / "plugin.py").write_text("VALUE = 1\n", encoding="utf-8")
        return root

    def test_metadata_mirror_is_exactly_regenerated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_package(temporary)
            self.assertTrue(metadata_sync.run(root, write=False))
            self.assertEqual(metadata_sync.run(root, write=True), [])
            canonical = ast.literal_eval(
                (root / "example/src/info").read_text(encoding="utf-8")
            )
            mirrored = json.loads(
                (root / "example/src/info.json").read_text(encoding="utf-8")
            )
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

    def test_reference_detects_non_python_network_clients(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_package(temporary)
            source = root / "example/src/example/agent_based"
            (source / "probe.php").write_text(
                "<?php $body = file_get_contents('https://example.invalid');\n",
                encoding="utf-8",
            )
            (source / "probe.sh").write_text(
                "#!/bin/sh\ncurl --fail https://example.invalid/status\n",
                encoding="utf-8",
            )
            package = root / "example"
            block = reference.derive_reference(
                root,
                package,
                reference.manifest(package / "src/info"),
            )
            self.assertIn(
                "The source performs network or remote-system access.",
                block,
            )
            self.assertNotIn("No direct remote-network client", block)

    def test_reference_qualifies_negative_network_detection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_package(temporary)
            package = root / "example"
            block = reference.derive_reference(
                root,
                package,
                reference.manifest(package / "src/info"),
            )
            self.assertIn(
                "This is not proof of network isolation",
                block,
            )

    def test_repository_facts_are_derived_from_manifests(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            for name in ("one", "two"):
                (root / name / "src").mkdir(parents=True)
                (root / name / "src" / "info").write_text(
                    "{}",
                    encoding="utf-8",
                )
            (root / "README.md").write_text(
                "The repository-wide release workflow currently discovers "
                "**0 active packages**.\n",
                encoding="utf-8",
            )
            (root / "docs/REPOSITORY_AUDIT.md").write_text(
                "The report covers **0 active packages**.\n",
                encoding="utf-8",
            )
            self.assertTrue(facts.run(root, write=False))
            self.assertEqual(facts.run(root, write=True), [])
            self.assertEqual(facts.run(root, write=False), [])
            self.assertIn(
                "**2 active packages**",
                (root / "README.md").read_text(encoding="utf-8"),
            )

    def test_module_docstring_gate_repairs_missing_docstring(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_package(temporary)
            self.assertTrue(docstrings.run(root, write=False))
            self.assertEqual(docstrings.run(root, write=True), [])
            self.assertEqual(docstrings.run(root, write=False), [])
            module = root / "example/src/example/agent_based/plugin.py"
            self.assertIsNotNone(
                ast.get_docstring(
                    ast.parse(module.read_text(encoding="utf-8"))
                )
            )

    def test_repository_syntax_gate_covers_legacy_extensionless_checks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checks = root / "archiv" / "legacy" / "src" / "checks"
            checks.mkdir(parents=True)
            broken = checks / "legacy_check"
            broken.write_text("def broken(:\n", encoding="utf-8")
            errors = syntax.validate(root)
            self.assertTrue(any("legacy_check" in error for error in errors))
            broken.write_text(
                "def valid():\n    return True\n",
                encoding="utf-8",
            )
            self.assertEqual(syntax.validate(root), [])

    def test_audit_includes_platform_suffix_and_shebang_scripts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "package/src/package/agents/plugins"
            scripts.mkdir(parents=True)
            linux = scripts / "discover_os_labels.linux"
            aix = scripts / "discover_os_labels.aix"
            solaris = scripts / "discover_os_labels.solaris"
            windows = scripts / "check_ping.cmd"
            linux.write_text("#!/bin/sh\necho linux\n", encoding="utf-8")
            aix.write_text("#!/usr/bin/ksh\necho aix\n", encoding="utf-8")
            solaris.write_text(
                "#!/usr/bin/perl\nprint 'solaris';\n",
                encoding="utf-8",
            )
            windows.write_text(
                "@echo off\r\necho windows\r\n",
                encoding="utf-8",
            )

            discovered = set(full_audit.source_files(root, []))
            self.assertEqual(discovered, {linux, aix, solaris, windows})

    def test_audit_applies_python_rules_to_unknown_suffix_shebangs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "agent.linux"
            script.write_text(
                "#!/usr/bin/env python3\nAPI_TOKEN = 'actual-secret-value'\n",
                encoding="utf-8",
            )
            findings = full_audit.audit_source(root, script)
            self.assertTrue(
                any(
                    item.rule_id == "security.hardcoded-credential"
                    for item in findings
                )
            )

    def test_all_manifest_sources_resolve(self):
        for package in builder.discover_package_dirs(ROOT, []):
            manifest = builder.read_manifest(package, "2.5.0")
            for component, entries in manifest["files"].items():
                for entry in entries:
                    source = builder._source_path(package, component, entry)
                    self.assertTrue(source.exists(), source)

    def test_package_lib_directories_are_not_globally_ignored(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertNotIn("\nlib/\n", "\n" + ignore)
        self.assertTrue(
            (
                ROOT
                / "cisco_ucs_detect/src/cmk/plugins/lib/cisco_ucs.py"
            ).is_file()
        )


if __name__ == "__main__":
    unittest.main()

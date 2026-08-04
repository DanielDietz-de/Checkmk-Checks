import contextlib
import importlib.util
import io
import json
import tempfile
import sys
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
MODULE_PATH = ROOT / "tools" / "ci" / "full_repository_audit.py"
audit = load_module(MODULE_PATH, "full_repository_audit_test")


class FullRepositoryAuditTests(unittest.TestCase):
    def make_root(self, temporary: str) -> Path:
        root = Path(temporary)
        for document in audit.REQUIRED_ROOT_DOCUMENTS:
            (root / document).write_text(
                "# Document\n\nSecurity installation compatibility support.\n",
                encoding="utf-8",
            )
        package = root / "example"
        (package / "src" / "example").mkdir(parents=True)
        metadata = {
            "name": "example",
            "title": "Example",
            "description": "Example package",
            "version": "1.0.0",
            "version.min_required": "2.4.0",
            "version.packaged": "2.5.0",
            "version.usable_until": "2.5.99",
            "files": {"cmk_addons_plugins": ["example/plugin.py"]},
        }
        (package / "src" / "info").write_text(repr(metadata), encoding="utf-8")
        (package / "README.md").write_text(
            "# Example\n\nInstallation setup configuration rule parameters. "
            "Validation tests verify behavior. Troubleshooting diagnostics and known limitations. "
            "Security credentials permissions and TLS.\n" * 3,
            encoding="utf-8",
        )
        (package / "src" / "example" / "plugin.py").write_text(
            '"""Example plug-in."""\n\nVALUE = 1\n', encoding="utf-8"
        )
        return root

    def test_clean_repository_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            report = audit.build_report(root, set())
            self.assertEqual(report["active_packages"], 1)
            self.assertEqual(report["summary"]["all"]["high"], 0)
            self.assertEqual(report["summary"]["all"]["critical"], 0)

    def test_detects_dynamic_execution_tls_and_private_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            source = root / "example" / "src" / "example" / "plugin.py"
            source.write_text(
                '"""Unsafe example."""\n'
                "import requests\n"
                "eval('1')\n"
                "requests.get('https://example.invalid', verify=False)\n"
                "KEY = '-----BEGIN PRIVATE KEY-----'\n",
                encoding="utf-8",
            )
            report = audit.build_report(root, set())
            rules = {item["rule_id"] for item in report["findings"]}
            self.assertIn("security.dynamic-code-execution", rules)
            self.assertIn("security.tls-verification-disabled", rules)
            self.assertIn("security.private-key-material", rules)

    def test_baseline_marks_existing_findings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            source = root / "example" / "src" / "example" / "plugin.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            initial = audit.build_report(root, set())
            fingerprints = {item["fingerprint"] for item in initial["findings"]}
            report = audit.build_report(root, fingerprints)
            self.assertTrue(report["findings"])
            self.assertTrue(all(item["baseline"] for item in report["findings"]))
            self.assertEqual(sum(report["summary"]["new"].values()), 0)

    def test_main_fails_only_for_new_threshold_findings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            source = root / "example" / "src" / "example" / "plugin.py"
            source.write_text('"""Unsafe."""\neval("1")\n', encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(audit.main(["--root", str(root), "--fail-on", "high"]), 1)
            report = audit.build_report(root, set())
            baseline = root / "baseline.json"
            baseline.write_text(
                json.dumps(
                    {
                        "schema_version": audit.SCHEMA_VERSION,
                        "fingerprints": [item["fingerprint"] for item in report["findings"]],
                    }
                ),
                encoding="utf-8",
            )
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    audit.main(
                        [
                            "--root",
                            str(root),
                            "--baseline",
                            str(baseline),
                            "--fail-on",
                            "high",
                        ]
                    ),
                    0,
                )


if __name__ == "__main__":
    unittest.main()

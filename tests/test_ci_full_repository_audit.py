import contextlib
import importlib.util
import io
import json
import tempfile
import sys
import unittest
from pathlib import Path


def load_module(path: Path, name: str):
    """Load module from its configured source."""
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
    """Represent fullrepositoryaudittests behavior and associated state."""
    def make_root(self, temporary: str) -> Path:
        """Handle make root for this module's workflow."""
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
        """Verify that clean repository report."""
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            report = audit.build_report(root, set())
            self.assertEqual(report["active_packages"], 1)
            self.assertEqual(report["summary"]["all"]["high"], 0)
            self.assertEqual(report["summary"]["all"]["critical"], 0)

    def test_detects_dynamic_execution_tls_and_private_key(self):
        """Verify that detects dynamic execution tls and private key."""
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            source = root / "example" / "src" / "example" / "plugin.py"
            marker = "-----BEGIN " + "PRIVATE KEY-----"
            source.write_text(
                '"""Unsafe example."""\n'
                "import requests\n"
                "eval('1')\n"
                "requests.get('https://example.invalid', verify=False)\n"
                f"KEY = {marker!r}\n",
                encoding="utf-8",
            )
            report = audit.build_report(root, set())
            rules = {item["rule_id"] for item in report["findings"]}
            self.assertIn("security.dynamic-code-execution", rules)
            self.assertIn("security.tls-verification-disabled", rules)
            self.assertIn("security.private-key-material", rules)

    def test_scans_non_script_files_for_credentials(self):
        """Verify that scans non script files for credentials."""
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            certificate = root / "certificates" / "server.pem"
            certificate.parent.mkdir(parents=True)
            certificate.write_text(
                "-----BEGIN " + "PRIVATE KEY-----\nredacted\n",
                encoding="utf-8",
            )
            workflow = root / ".github" / "workflows" / "deploy.yml"
            workflow.parent.mkdir(parents=True)
            token = "ghp_" + ("A" * 30)
            workflow.write_text(f"token: {token}\n", encoding="utf-8")

            report = audit.build_report(root, set())
            credential_findings = {
                (item["path"], item["rule_id"])
                for item in report["findings"]
            }
            self.assertIn(
                ("certificates/server.pem", "security.private-key-material"),
                credential_findings,
            )
            self.assertIn(
                (".github/workflows/deploy.yml", "security.token-material"),
                credential_findings,
            )
            self.assertGreater(report["credential_files"], report["source_files"])

    def test_detects_encrypted_and_dsa_private_key_headers(self):
        """Verify that detects encrypted and dsa private key headers."""
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            key_directory = root / "certificates"
            key_directory.mkdir(parents=True)
            encrypted = key_directory / "encrypted.pem"
            encrypted.write_text(
                "-----BEGIN " + "ENCRYPTED PRIVATE KEY-----\nredacted\n",
                encoding="utf-8",
            )
            dsa = key_directory / "legacy-dsa.key"
            dsa.write_text(
                "-----BEGIN " + "DSA PRIVATE KEY-----\nredacted\n",
                encoding="utf-8",
            )

            report = audit.build_report(root, set())
            credential_findings = {
                (item["path"], item["rule_id"])
                for item in report["findings"]
            }
            self.assertIn(
                ("certificates/encrypted.pem", "security.private-key-material"),
                credential_findings,
            )
            self.assertIn(
                ("certificates/legacy-dsa.key", "security.private-key-material"),
                credential_findings,
            )

    def test_benign_binary_file_is_scanned_without_false_positive(self):
        """Verify that benign binary file is scanned without false positive."""
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            binary = root / "assets" / "image.bin"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b"\x00\xff\x10benign-data")
            report = audit.build_report(root, set())
            matching = [
                item for item in report["findings"]
                if item["path"] == "assets/image.bin"
            ]
            self.assertEqual(matching, [])

    def test_baseline_marks_existing_findings(self):
        """Verify that baseline marks existing findings."""
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
        """Verify that main fails only for new threshold findings."""
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


    def test_nullable_upper_compatibility_is_valid(self):
        """Verify that nullable upper compatibility is valid."""
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            info = root / "example" / "src" / "info"
            metadata = audit.metadata(info)
            metadata["version.usable_until"] = None
            info.write_text(repr(metadata), encoding="utf-8")
            report = audit.build_report(root, set())
            incomplete = [
                item for item in report["findings"]
                if item["rule_id"] == "docs.metadata-incomplete"
                and "version.usable_until" in item["message"]
            ]
            self.assertEqual(incomplete, [])

    def test_detects_unbounded_network_call(self):
        """Verify that detects unbounded network call."""
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            source = root / "example" / "src" / "example" / "plugin.py"
            source.write_text(
                '"""Network client."""\nimport requests\nrequests.get("https://example.invalid")\n',
                encoding="utf-8",
            )
            report = audit.build_report(root, set())
            rules = {item["rule_id"] for item in report["findings"]}
            self.assertIn("security.network-timeout-missing", rules)

    def test_detects_unbounded_urllib_calls(self):
        """Verify that detects unbounded urllib calls."""
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            source = root / "example" / "src" / "example" / "plugin.py"
            source.write_text(
                '"""Urllib client."""\n'
                'from urllib import request as urllib_request\n'
                'class Client:\n'
                '    def __init__(self):\n'
                '        self.op = urllib_request.build_opener()\n'
                '    def fetch(self, req):\n'
                '        opener = self.op\n'
                '        return opener.open(req)\n'
                'urllib_request.urlopen("https://example.invalid")\n',
                encoding="utf-8",
            )
            report = audit.build_report(root, set())
            findings = [
                item for item in report["findings"]
                if item["rule_id"] == "security.network-timeout-missing"
            ]
            self.assertEqual(len(findings), 2)

    def test_accepts_bounded_urllib_calls(self):
        """Verify that accepts bounded urllib calls."""
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            source = root / "example" / "src" / "example" / "plugin.py"
            source.write_text(
                '"""Bounded urllib client."""\n'
                'from urllib.request import Request, build_opener, urlopen\n'
                'opener = build_opener()\n'
                'req = Request("https://example.invalid")\n'
                'opener.open(req, None, 5.0)\n'
                'urlopen(req, timeout=5.0)\n',
                encoding="utf-8",
            )
            report = audit.build_report(root, set())
            rules = {item["rule_id"] for item in report["findings"]}
            self.assertNotIn("security.network-timeout-missing", rules)

    def test_safe_secret_requires_agent_side_resolution(self):
        """Verify that safe secret requires agent side resolution."""
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            package = root / "example"
            server = package / "src" / "example" / "server_side_calls" / "agent.py"
            server.parent.mkdir(parents=True)
            server.write_text(
                '"""Command builder."""\nfrom cmk.server_side_calls.v1 import Secret\nVALUE: Secret\nARGS = [Secret(1)]\n',
                encoding="utf-8",
            )
            executable = package / "src" / "example" / "libexec" / "agent_example"
            executable.parent.mkdir(parents=True)
            executable.write_text(
                '#!/usr/bin/env python3\n"""Agent."""\nprint("ok")\n',
                encoding="utf-8",
            )
            report = audit.build_report(root, set())
            rules = {item["rule_id"] for item in report["findings"]}
            self.assertIn("security.secret-reference-unresolved", rules)
            executable.write_text(
                '#!/usr/bin/env python3\n"""Agent."""\nfrom cmk.utils import password_store\npassword_store.lookup(None, "id")\n',
                encoding="utf-8",
            )
            report = audit.build_report(root, set())
            rules = {item["rule_id"] for item in report["findings"]}
            self.assertNotIn("security.secret-reference-unresolved", rules)

    def test_scans_standalone_source_and_detects_literal_credentials(self):
        """Verify that scans standalone source and detects literal credentials."""
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            utility = root / "stuff" / "utility.py"
            utility.parent.mkdir(parents=True)
            utility.write_text(
                '"""Standalone utility."""\nSECRET = "01234567-89ab-cdef-0123-456789abcdef"\n',
                encoding="utf-8",
            )
            report = audit.build_report(root, set())
            rules = {item["rule_id"] for item in report["findings"]}
            self.assertIn("security.hardcoded-credential", rules)
            self.assertGreaterEqual(report["source_files"], 2)

    def test_detects_unqualified_tls_warning_suppression(self):
        """Verify that detects unqualified tls warning suppression."""
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            source = root / "example" / "src" / "example" / "plugin.py"
            source.write_text(
                '"""Unsafe warning policy."""\n'
                'from urllib3 import disable_warnings\n'
                'disable_warnings()\n',
                encoding="utf-8",
            )
            report = audit.build_report(root, set())
            rules = {item["rule_id"] for item in report["findings"]}
            self.assertIn("security.tls-warning-suppression", rules)


if __name__ == "__main__":
    unittest.main()

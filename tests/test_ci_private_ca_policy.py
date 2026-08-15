from __future__ import annotations

import ast
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
AGENTS = [
    "dell_pmax/src/dell_pmax/libexec/agent_dellpmax",
    "semu/src/semu/libexec/agent_semu",
    "spring_boot_actuator/src/spring_boot_actuator/libexec/agent_spring_boot_actuator",
    "unisphere_powermax/src/unisphere_powermax/libexec/agent_unisphere_powermax",
    "veritas_flex/src/veritas_flex/libexec/agent_veritas",
    "notify_sms_eagle/src/notifications/sms_eagle",
    "alarms/src/notifications/alarms",
    "hitachi_hnas_rest/src/hitachi_hnas_rest/libexec/agent_hitachi_hnas_rest",
    "quobyte/src/quobyte/libexec/agent_quobyte",
]
CONFIGS = [
    "dell_pmax/src/dell_pmax/rulesets/agent_dellpmax.py",
    "semu/src/semu/rulesets/ruleset.py",
    "spring_boot_actuator/src/spring_boot_actuator/rulesets/spring_boot_actuator.py",
    "unisphere_powermax/src/unisphere_powermax/rulesets/rulesets.py",
    "veritas_flex/src/veritas_flex/rulesets/agent.py",
    "notify_sms_eagle/src/sms_eagle/rulesets/notification_parameter.py",
    "alarms/src/alarms/rulesets/alarms.py",
    "hitachi_hnas_rest/src/hitachi_hnas_rest/rulesets/agent.py",
    "quobyte/src/quobyte/rulesets/agent.py",
]

def helper(path: Path):
    """Handle helper for this module's workflow."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_ca_bundle")
    namespace = {"os": os, "Path": Path}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["_resolve_ca_bundle"]

class PrivateCaPolicyTests(unittest.TestCase):
    """Represent privatecapolicytests behavior and associated state."""
    def test_all_external_sessions_preserve_ca_fallbacks(self):
        """Verify that all external sessions preserve ca fallbacks."""
        for relative in AGENTS:
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(relative=relative):
                self.assertIn("trust_env = False", text)
                self.assertIn("REQUESTS_CA_BUNDLE", text)
                self.assertIn("CURL_CA_BUNDLE", text)
                self.assertIn("def _resolve_ca_bundle", text)

    def test_rules_expose_custom_ca_bundle(self):
        """Verify that rules expose custom ca bundle."""
        for relative in CONFIGS:
            with self.subTest(relative=relative):
                self.assertIn("ca_file", (ROOT / relative).read_text(encoding="utf-8"))

    def test_helper_precedence_and_failure_modes(self):
        """Verify that helper precedence and failure modes."""
        old_requests = os.environ.pop("REQUESTS_CA_BUNDLE", None)
        old_curl = os.environ.pop("CURL_CA_BUNDLE", None)
        try:
            for relative in AGENTS:
                resolve = helper(ROOT / relative)
                self.assertIs(resolve(None, False), True)
                self.assertIs(resolve(None, True), False)
                with self.assertRaises(ValueError): resolve("/tmp/ca.pem", True)
                with tempfile.TemporaryDirectory() as directory:
                    base = Path(directory)
                    explicit, requests, curl = base / "explicit.pem", base / "requests.pem", base / "curl.pem"
                    for item in (explicit, requests, curl): item.write_text("test", encoding="utf-8")
                    os.environ["REQUESTS_CA_BUNDLE"] = str(requests)
                    os.environ["CURL_CA_BUNDLE"] = str(curl)
                    self.assertEqual(resolve(str(explicit), False), str(explicit.resolve()))
                    self.assertEqual(resolve(None, False), str(requests.resolve()))
                    del os.environ["REQUESTS_CA_BUNDLE"]
                    self.assertEqual(resolve(None, False), str(curl.resolve()))
                    del os.environ["CURL_CA_BUNDLE"]
                with self.assertRaises(ValueError): resolve("/definitely/missing/private-ca.pem", False)
        finally:
            if old_requests is not None: os.environ["REQUESTS_CA_BUNDLE"] = old_requests
            else: os.environ.pop("REQUESTS_CA_BUNDLE", None)
            if old_curl is not None: os.environ["CURL_CA_BUNDLE"] = old_curl
            else: os.environ.pop("CURL_CA_BUNDLE", None)

if __name__ == "__main__": unittest.main()

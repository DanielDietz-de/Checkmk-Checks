from __future__ import annotations

import ast
import os
from pathlib import Path
from urllib.parse import urlsplit
import unittest

ROOT = Path(__file__).resolve().parents[1]


def functions(path: Path, names: set[str]) -> dict[str, object]:
    """Handle functions for this module's workflow."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    namespace = {"os": os, "Path": Path, "urlsplit": urlsplit}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


class PrivateCaHttpBehaviorTests(unittest.TestCase):
    """Represent privatecahttpbehaviortests behavior and associated state."""
    def setUp(self) -> None:
        """Handle setup for this module's workflow."""
        self.previous = os.environ.get("REQUESTS_CA_BUNDLE")
        os.environ["REQUESTS_CA_BUNDLE"] = "/definitely/missing/site-ca.pem"

    def tearDown(self) -> None:
        """Handle teardown for this module's workflow."""
        if self.previous is None:
            os.environ.pop("REQUESTS_CA_BUNDLE", None)
        else:
            os.environ["REQUESTS_CA_BUNDLE"] = self.previous

    def test_spring_http_ignores_ca_configuration(self) -> None:
        """Verify that spring http ignores ca configuration."""
        namespace = functions(
            ROOT / "spring_boot_actuator/src/spring_boot_actuator/libexec/agent_spring_boot_actuator",
            {"_resolve_ca_bundle", "_verification_for_url"},
        )
        self.assertIs(namespace["_verification_for_url"]("http://app/actuator/health", None, False), True)

    def test_sms_http_ignores_ca_configuration(self) -> None:
        """Verify that sms http ignores ca configuration."""
        namespace = functions(
            ROOT / "notify_sms_eagle/src/notifications/sms_eagle",
            {"_resolve_ca_bundle", "_verification_for_api_host"},
        )
        self.assertIs(namespace["_verification_for_api_host"]("http://localhost", None, True), True)

    def test_alarm_http_uses_system_default_without_resolving_bundle(self) -> None:
        """Verify that alarm http uses system default without resolving bundle."""
        source = (ROOT / "alarms/src/notifications/alarms").read_text(encoding="utf-8")
        self.assertIn(
            'verify = _resolve_ca_bundle(API_CA_FILE, False) if API_PROTO == "https" else True',
            source,
        )

    def test_quobyte_http_does_not_resolve_bundle(self) -> None:
        """Verify that quobyte http does not resolve bundle."""
        source = (
            ROOT / "quobyte/src/quobyte/libexec/agent_quobyte"
        ).read_text(encoding="utf-8")
        self.assertIn('if urlsplit(api_host).scheme.lower() == "https"', source)
        self.assertIn("else True", source)


if __name__ == "__main__":
    unittest.main()

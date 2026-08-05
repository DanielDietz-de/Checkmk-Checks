#!/usr/bin/env python3
"""Keep HTTP endpoints independent from TLS CA-bundle configuration."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Expected content missing from {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


quobyte = ROOT / "quobyte/src/quobyte/libexec/agent_quobyte"
replace_once(
    quobyte,
    "from pathlib import Path\n",
    "from pathlib import Path\nfrom urllib.parse import urlsplit\n",
)
replace_once(
    quobyte,
    "        self.session.verify = _resolve_ca_bundle(ca_file)\n",
    "        self.session.verify = (\n"
    "            _resolve_ca_bundle(ca_file)\n"
    "            if urlsplit(api_host).scheme.lower() == \"https\"\n"
    "            else True\n"
    "        )\n",
)

documentation_sentence = (
    " For HTTP endpoints, CA bundle settings and CA environment variables are not "
    "evaluated because no TLS trust chain exists."
)
for relative in (
    "alarms/README.md",
    "notify_sms_eagle/README.md",
    "quobyte/README.md",
    "spring_boot_actuator/README.md",
):
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    if documentation_sentence.strip() not in text:
        marker = (
            "Environment CA variables are read deliberately even though proxy and "
            "`.netrc` inheritance remain disabled."
        )
        if marker not in text:
            raise RuntimeError(f"TLS documentation marker missing from {relative}")
        text = text.replace(marker, marker + documentation_sentence, 1)
        path.write_text(text, encoding="utf-8")

(ROOT / "tests/test_ci_private_ca_http_behavior.py").write_text(
    '''from __future__ import annotations

import ast
import os
from pathlib import Path
from urllib.parse import urlsplit
import unittest

ROOT = Path(__file__).resolve().parents[1]


def functions(path: Path, names: set[str]) -> dict[str, object]:
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
    def setUp(self) -> None:
        self.previous = os.environ.get("REQUESTS_CA_BUNDLE")
        os.environ["REQUESTS_CA_BUNDLE"] = "/definitely/missing/site-ca.pem"

    def tearDown(self) -> None:
        if self.previous is None:
            os.environ.pop("REQUESTS_CA_BUNDLE", None)
        else:
            os.environ["REQUESTS_CA_BUNDLE"] = self.previous

    def test_spring_http_ignores_ca_configuration(self) -> None:
        namespace = functions(
            ROOT / "spring_boot_actuator/src/spring_boot_actuator/libexec/agent_spring_boot_actuator",
            {"_resolve_ca_bundle", "_verification_for_url"},
        )
        self.assertIs(namespace["_verification_for_url"]("http://app/actuator/health", None, False), True)

    def test_sms_http_ignores_ca_configuration(self) -> None:
        namespace = functions(
            ROOT / "notify_sms_eagle/src/notifications/sms_eagle",
            {"_resolve_ca_bundle", "_verification_for_api_host"},
        )
        self.assertIs(namespace["_verification_for_api_host"]("http://localhost", None, True), True)

    def test_alarm_http_uses_system_default_without_resolving_bundle(self) -> None:
        source = (ROOT / "alarms/src/notifications/alarms").read_text(encoding="utf-8")
        self.assertIn(
            'verify = _resolve_ca_bundle(API_CA_FILE, False) if API_PROTO == "https" else True',
            source,
        )

    def test_quobyte_http_does_not_resolve_bundle(self) -> None:
        source = (
            ROOT / "quobyte/src/quobyte/libexec/agent_quobyte"
        ).read_text(encoding="utf-8")
        self.assertIn('if urlsplit(api_host).scheme.lower() == "https"', source)
        self.assertIn("else True", source)


if __name__ == "__main__":
    unittest.main()
''',
    encoding="utf-8",
)

print("Applied HTTP/private-CA compatibility edge handling")

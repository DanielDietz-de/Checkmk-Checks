"""Regression tests for standalone repository utility security boundaries."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
ACTIVATE = ROOT / "cmk_api_scripts" / "activate_changes.py"


def load_activate_module():
    spec = importlib.util.spec_from_file_location("activate_changes_test", ACTIVATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class StandaloneUtilityTests(unittest.TestCase):
    def test_activate_changes_rejects_remote_cleartext_by_default(self):
        module = load_activate_module()
        with self.assertRaisesRegex(ValueError, "requires HTTPS"):
            module.validate_site_url("http://checkmk.example/mysite")

    def test_activate_changes_accepts_https_and_derives_site(self):
        module = load_activate_module()
        self.assertEqual(
            module.validate_site_url("https://checkmk.example/mysite"),
            ("https://checkmk.example/mysite", "mysite"),
        )

    def test_removed_legacy_web_api_examples_are_absent(self):
        self.assertFalse((ROOT / "stuff" / "api.py").exists())
        self.assertFalse((ROOT / "stuff" / "edit_label.py").exists())


if __name__ == "__main__":
    unittest.main()

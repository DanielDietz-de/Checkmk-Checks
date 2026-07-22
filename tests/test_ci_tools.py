import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).parents[1]
PIN_MODULE_PATH = ROOT / "tools" / "ci" / "pin_supply_chain_corrected.py"
GUARD_MODULE_PATH = ROOT / "tools" / "ci" / "repository_guard_corrected.py"
pinning = load_module(PIN_MODULE_PATH, "pin_supply_chain_test")
guard = load_module(GUARD_MODULE_PATH, "repository_guard_test")


class SupplyChainPinningTests(unittest.TestCase):
    def test_pinning_is_idempotent_and_retains_source_tags(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workflow_dir = root / ".github" / "workflows"
            workflow_dir.mkdir(parents=True)
            workflow = workflow_dir / "ci.yml"
            workflow.write_text(
                "steps:\n"
                "  - uses: actions/checkout@v6\n"
                "env:\n"
                "  IMAGE: checkmk/check-mk-community:2.5.0p9\n",
                encoding="utf-8",
            )
            action_sha = "a" * 40
            image_digest = "sha256:" + "b" * 64
            with mock.patch.object(pinning, "resolve_action", return_value=action_sha), mock.patch.object(
                pinning, "resolve_image", return_value=image_digest
            ):
                first_lock, first_changed = pinning.pin_workflow(workflow, write=True)
            self.assertTrue(first_changed)
            self.assertEqual(
                first_lock["actions"]["actions/checkout@v6"]["commit"], action_sha
            )
            self.assertEqual(
                first_lock["images"]["checkmk/check-mk-community:2.5.0p9"]["digest"],
                image_digest,
            )

            second_lock, second_changed = pinning.pin_workflow(workflow, write=False)
            self.assertFalse(second_changed)
            self.assertIn("actions/checkout@v6", second_lock["actions"])
            self.assertIn(
                "checkmk/check-mk-community:2.5.0p9", second_lock["images"]
            )

    def test_mutable_dependencies_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workflow_dir = root / ".github" / "workflows"
            workflow_dir.mkdir(parents=True)
            (workflow_dir / "ci.yml").write_text(
                "steps:\n  - uses: actions/checkout@v6\n"
                "env:\n  IMAGE: checkmk/check-mk-raw:2.4.0p34\n",
                encoding="utf-8",
            )
            errors = pinning.validate_locked_workflows(root)
            self.assertEqual(len(errors), 2)
            self.assertTrue(any("mutable action" in error for error in errors))
            self.assertTrue(any("mutable image" in error for error in errors))


class RepositoryGuardTests(unittest.TestCase):
    def test_changed_source_rejects_eval_shell_and_verify_false(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "package" / "src" / "plugin.py"
            source.parent.mkdir(parents=True)
            source.write_text(
                "import requests, subprocess\n"
                "eval('1')\n"
                "subprocess.run(['true'], shell=True)\n"
                "requests.get('https://example', verify=False)\n",
                encoding="utf-8",
            )
            errors = guard.validate_changed_source(root, [source])
            self.assertTrue(any("eval" in error for error in errors))
            self.assertTrue(any("shell=True" in error for error in errors))
            self.assertTrue(any("verify=False" in error for error in errors))

    def test_changed_package_source_requires_tests(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "example"
            source = package / "src" / "example" / "agent_based" / "check.py"
            source.parent.mkdir(parents=True)
            source.write_text("VALUE = 1\n", encoding="utf-8")
            (package / "src" / "info").write_text(
                repr(
                    {
                        "name": "example",
                        "version": "1.0.0",
                        "files": {"cmk_addons_plugins": ["example/agent_based/check.py"]},
                    }
                ),
                encoding="utf-8",
            )
            errors = guard.validate_changed_packages_have_tests(root, [source])
            self.assertEqual(len(errors), 1)
            tests = package / "tests"
            tests.mkdir()
            (tests / "test_check.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
            self.assertEqual(
                guard.validate_changed_packages_have_tests(root, [source]), []
            )

    def test_metadata_consistency_is_enforced_only_for_touched_packages(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "example"
            (package / "src").mkdir(parents=True)
            base = {
                "name": "example",
                "version": "1.0.0",
                "files": {"cmk_addons_plugins": []},
            }
            (package / "src" / "info").write_text(repr(base), encoding="utf-8")
            conflicting = dict(base, version="2.0.0")
            (package / "src" / "info.json").write_text(
                json.dumps(conflicting), encoding="utf-8"
            )
            self.assertEqual(guard.validate_metadata(root, set()), [])
            errors = guard.validate_metadata(root, {package})
            self.assertTrue(any("version differs" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

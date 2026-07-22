import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def load_pinner():
    root = Path(__file__).parents[1]
    path = root / "tools" / "ci" / "pin_supply_chain.py"
    spec = importlib.util.spec_from_file_location("pin_supply_chain_paths", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NestedActionPathTests(unittest.TestCase):
    def test_nested_action_path_is_preserved_and_pinned(self):
        pinner = load_pinner()
        with tempfile.TemporaryDirectory() as temporary:
            workflow = Path(temporary) / "workflow.yml"
            workflow.write_text(
                "steps:\n  - uses: github/codeql-action/upload-sarif@v3\n",
                encoding="utf-8",
            )
            sha = "c" * 40
            with mock.patch.object(pinner, "resolve_action", return_value=sha):
                locks, changed = pinner.pin_workflow(workflow, write=True)
            self.assertTrue(changed)
            text = workflow.read_text(encoding="utf-8")
            self.assertIn(f"github/codeql-action/upload-sarif@{sha} # v3", text)
            entry = locks["actions"]["github/codeql-action/upload-sarif@v3"]
            self.assertEqual(entry["repository"], "github/codeql-action")
            self.assertEqual(entry["action_path"], "/upload-sarif")


if __name__ == "__main__":
    unittest.main()

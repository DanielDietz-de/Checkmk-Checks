"""Tests for the repository GitHub Actions runner-selection policy."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "tools/ci/check_workflow_runners.py"
SPEC = importlib.util.spec_from_file_location("check_workflow_runners", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_workflow(root: Path, body: str, filename: str = "ci.yml") -> None:
    """Create one minimal workflow below a temporary repository root."""

    workflow_dir = root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    (workflow_dir / filename).write_text(body, encoding="utf-8")


class WorkflowRunnerPolicyTests(unittest.TestCase):
    """Exercise normal and explicitly excepted runner selectors through CI."""

    def _validate(self, body: str, filename: str = "ci.yml") -> list[str]:
        """Validate one temporary workflow and return runner-policy errors."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_workflow(root, body, filename)
            return MODULE.validate_workflow_runners(root)

    def test_accepts_explicit_self_hosted_runner_labels(self) -> None:
        """Accept the standard self-hosted Linux runner selector."""

        self.assertEqual(
            self._validate("jobs:\n  test:\n    runs-on: [self-hosted, linux]\n"),
            [],
        )

    def test_accepts_multiline_self_hosted_runner_labels(self) -> None:
        """Accept a multiline selector that still includes self-hosted."""

        self.assertEqual(
            self._validate(
                "jobs:\n  test:\n    runs-on:\n      labels: [self-hosted, linux]\n"
            ),
            [],
        )

    def test_rejects_github_hosted_runner_labels(self) -> None:
        """Reject hosted Linux runners outside the exact exception inventory."""

        errors = self._validate("jobs:\n  test:\n    runs-on: ubuntu-24.04\n")
        self.assertTrue(any("not an approved exception" in error for error in errors))

    def test_rejects_implicit_local_label_without_self_hosted(self) -> None:
        """Reject ambiguous local labels that omit the self-hosted boundary."""

        self.assertEqual(
            self._validate("jobs:\n  test:\n    runs-on: linux\n"),
            [
                ".github/workflows/ci.yml:3: runs-on must explicitly include "
                "the self-hosted label"
            ],
        )

    def test_rejects_mixed_hosted_and_self_hosted_labels(self) -> None:
        """Reject selectors that combine hosted and self-hosted execution."""

        errors = self._validate(
            "jobs:\n  test:\n    runs-on: [self-hosted, ubuntu-latest]\n"
        )
        self.assertTrue(any("not an approved exception" in error for error in errors))
        self.assertTrue(any("must not be mixed" in error for error in errors))

    def test_accepts_exact_windows_validation_exception(self) -> None:
        """Allow the pinned Windows runner only for the S2D PowerShell workflow."""

        self.assertEqual(
            self._validate(
                "jobs:\n  test:\n    runs-on: windows-2025\n",
                "s2d-hci-windows-ci.yml",
            ),
            [],
        )

    def test_accepts_exact_final_audit_exception(self) -> None:
        """Allow the pinned ephemeral Linux runner for the final-audit bootstrap."""

        self.assertEqual(
            self._validate(
                "jobs:\n  test:\n    runs-on: ubuntu-24.04\n",
                "final-audit-runner.yml",
            ),
            [],
        )

    def test_rejects_hosted_exception_on_wrong_workflow(self) -> None:
        """Prevent an allowlisted runner label from leaking to another workflow."""

        errors = self._validate(
            "jobs:\n  test:\n    runs-on: windows-2025\n",
            "unrelated.yml",
        )
        self.assertTrue(any("not an approved exception" in error for error in errors))

    def test_rejects_unapproved_label_for_exception_workflow(self) -> None:
        """Keep an exception pinned to its exact hosted runner image."""

        errors = self._validate(
            "jobs:\n  test:\n    runs-on: windows-latest\n",
            "s2d-hci-windows-ci.yml",
        )
        self.assertTrue(any("not an approved exception" in error for error in errors))
        self.assertTrue(any("exception was not matched" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

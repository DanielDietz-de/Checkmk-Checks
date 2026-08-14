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
        """Accept a mapping selector that includes both required labels."""

        self.assertEqual(
            self._validate(
                "jobs:\n  test:\n    runs-on:\n      labels: [self-hosted, linux]\n"
            ),
            [],
        )

    def test_accepts_group_plus_static_linux_labels(self) -> None:
        """Accept the documented group-plus-labels object with static routing."""

        self.assertEqual(
            self._validate(
                "jobs:\n  test:\n    runs-on:\n      group: private\n      labels: [self-hosted, linux]\n"
            ),
            [],
        )

    def test_rejects_github_hosted_runner_labels(self) -> None:
        """Reject hosted Linux runners outside the exact exception inventory."""

        errors = self._validate("jobs:\n  test:\n    runs-on: ubuntu-24.04\n")
        self.assertTrue(any("not an approved exact exception" in error for error in errors))

    def test_rejects_implicit_local_label_without_self_hosted(self) -> None:
        """Reject ambiguous local labels that omit the self-hosted boundary."""

        errors = self._validate("jobs:\n  test:\n    runs-on: linux\n")
        self.assertTrue(any("missing self-hosted" in error for error in errors))

    def test_rejects_self_hosted_selector_without_linux(self) -> None:
        """Require the Linux label even when self-hosted is present."""

        errors = self._validate("jobs:\n  test:\n    runs-on: self-hosted\n")
        self.assertTrue(any("missing linux" in error for error in errors))

    def test_rejects_self_hosted_windows_selector_for_ordinary_job(self) -> None:
        """Prevent ordinary jobs from selecting a non-Linux self-hosted runner."""

        errors = self._validate("jobs:\n  test:\n    runs-on: [self-hosted, windows]\n")
        self.assertTrue(any("missing linux" in error for error in errors))

    def test_rejects_mixed_hosted_and_self_hosted_labels(self) -> None:
        """Reject arrays that combine hosted and self-hosted execution."""

        errors = self._validate(
            "jobs:\n  test:\n    runs-on: [self-hosted, linux, ubuntu-latest]\n"
        )
        self.assertTrue(any("not an approved exact exception" in error for error in errors))

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
        self.assertTrue(any("not an approved exact exception" in error for error in errors))

    def test_rejects_unapproved_label_for_exception_workflow(self) -> None:
        """Keep an exception pinned to its exact hosted runner image."""

        errors = self._validate(
            "jobs:\n  test:\n    runs-on: windows-latest\n",
            "s2d-hci-windows-ci.yml",
        )
        self.assertTrue(any("not an approved exact exception" in error for error in errors))
        self.assertTrue(any("exception was not matched" in error for error in errors))

    def test_rejects_dynamic_selector_with_approved_label_in_comment(self) -> None:
        """Do not let comments spoof an exact hosted-runner exception."""

        errors = self._validate(
            "jobs:\n  test:\n    runs-on: ${{ matrix.runner }} # windows-2025\n",
            "s2d-hci-windows-ci.yml",
        )
        self.assertTrue(any("dynamic runs-on expressions" in error for error in errors))
        self.assertTrue(any("exception was not matched" in error for error in errors))

    def test_rejects_dynamic_ordinary_selector(self) -> None:
        """Keep ordinary runner selection static and reviewable."""

        errors = self._validate(
            "jobs:\n  test:\n    runs-on: ${{ fromJSON('[\"self-hosted\",\"linux\"]') }}\n"
        )
        self.assertTrue(any("dynamic runs-on expressions" in error for error in errors))

    def test_structurally_parses_quoted_runs_on_key(self) -> None:
        """Decode a quoted key and still reject its unapproved hosted selector."""

        errors = self._validate('jobs:\n  test:\n    "runs-on": ubuntu-latest\n')
        self.assertTrue(any("not an approved exact exception" in error for error in errors))

    def test_structurally_parses_unicode_escaped_runs_on_key(self) -> None:
        """Decode escaped key text before runner-policy evaluation."""

        errors = self._validate('jobs:\n  test:\n    "runs\\u002Don": ubuntu-latest\n')
        self.assertTrue(any("not an approved exact exception" in error for error in errors))

    def test_structurally_parses_anchored_runs_on_key(self) -> None:
        """Decode an anchored key instead of relying on raw source spelling."""

        errors = self._validate("jobs:\n  test:\n    &runner_key runs-on: ubuntu-latest\n")
        self.assertTrue(any("not an approved exact exception" in error for error in errors))

    def test_structurally_parses_explicit_runs_on_key(self) -> None:
        """Decode YAML explicit-key syntax before evaluating the selector."""

        errors = self._validate("jobs:\n  test:\n    ? runs-on\n    : ubuntu-latest\n")
        self.assertTrue(any("not an approved exact exception" in error for error in errors))

    def test_structurally_parses_flow_mapping_runs_on_key(self) -> None:
        """Decode flow-style mappings and enforce hosted-runner policy."""

        errors = self._validate(
            "jobs: {test: {runs-on: ubuntu-latest, steps: []}}\n"
        )
        self.assertTrue(any("not an approved exact exception" in error for error in errors))

    def test_rejects_dynamic_group_mapping(self) -> None:
        """Keep runner-group selection static as well as runner labels."""

        errors = self._validate(
            "jobs:\n  test:\n    runs-on:\n      group: ${{ matrix.group }}\n      labels: [self-hosted, linux]\n"
        )
        self.assertTrue(any("runs-on group must be one static" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

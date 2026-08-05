from __future__ import annotations

from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
VALIDATION = REPOSITORY / ".github/workflows/repository-mkp-ci.yml"
PUBLICATION = REPOSITORY / ".github/workflows/repository-mkp-publication.yml"


def test_validation_workflow_is_read_only() -> None:
    workflow = VALIDATION.read_text(encoding="utf-8")
    assert "\n  persist:\n" not in workflow
    assert "HEAD:master" not in workflow
    assert "contents: write" not in workflow


def test_full_pull_requests_exercise_publication_transaction() -> None:
    workflow = VALIDATION.read_text(encoding="utf-8")
    dry_run = workflow.split("\n  publication-dry-run:\n", maxsplit=1)[1]
    ordered = (
        "prepare_repository_mkp_release.py --repository . --complete",
        "stage_repository_release.py --repository . --dist",
        "sync_package_metadata.py --write",
        "update_readmes.py",
        "generate_package_reference.py --write",
        "create_mkp_index.py",
        "verify_repository_release.py",
    )
    positions = [dry_run.index(command) for command in ordered]
    assert positions == sorted(positions)
    assert "needs.select.outputs.mode == 'full'" in dry_run


def test_publication_uses_release_branch_and_pull_request() -> None:
    workflow = PUBLICATION.read_text(encoding="utf-8")
    assert "workflow_run:" in workflow
    assert "RELEASE_BRANCH: automation/repository-mkp-release" in workflow
    assert "HEAD:refs/heads/$RELEASE_BRANCH" in workflow
    assert "gh pr create" in workflow
    assert "HEAD:master" not in workflow
    assert "pull-requests: write" in workflow


def test_publication_aborts_stale_source_without_failing_or_pushing() -> None:
    workflow = PUBLICATION.read_text(encoding="utf-8")
    current = workflow.split("- name: Verify source commit is still current", maxsplit=1)[1].split(
        "- name: Stage complete release", maxsplit=1
    )[0]
    assert 'echo "current=false"' in current
    assert "exit 78" not in current
    assert "if: steps.source.outputs.current == 'true'" in workflow


def test_master_and_manual_runs_force_full_selection() -> None:
    workflow = VALIDATION.read_text(encoding="utf-8")
    assert "--event-name \"$EVENT_NAME\"" in workflow
    selector = (
        REPOSITORY / ".github/scripts/detect_affected_packages.py"
    ).read_text(encoding="utf-8")
    assert 'if event_name != "pull_request"' in selector

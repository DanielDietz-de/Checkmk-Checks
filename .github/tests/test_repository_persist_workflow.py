from __future__ import annotations

from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
VALIDATION = REPOSITORY / ".github/workflows/repository-mkp-ci.yml"
PUBLICATION = REPOSITORY / ".github/workflows/repository-mkp-publication.yml"
SCHEDULE = REPOSITORY / ".github/workflows/repository-mkp-schedule.yml"
GUARD = REPOSITORY / ".github/workflows/repository-guard.yml"
PREPARE = REPOSITORY / ".github/scripts/prepare_repository_mkp_release.py"
NORMALIZER = REPOSITORY / "tools/ci/normalize_package_sources.py"


def test_validation_workflow_is_read_only() -> None:
    workflow = VALIDATION.read_text(encoding="utf-8")
    assert "\n  persist:\n" not in workflow
    assert "HEAD:master" not in workflow
    assert "contents: write" not in workflow


def test_documentation_only_scope_preserves_required_check_names() -> None:
    workflow = VALIDATION.read_text(encoding="utf-8")
    tests_job = workflow.split("\n  tests:\n", maxsplit=1)[1].split("\n  build:\n", maxsplit=1)[0]
    build_job = workflow.split("\n  build:\n", maxsplit=1)[1].split("\n  validate:\n", maxsplit=1)[0]
    validate_job = workflow.split("\n  validate:\n", maxsplit=1)[1].split(
        "\n  publication-dry-run:\n", maxsplit=1
    )[0]
    for job in (tests_job, build_job, validate_job):
        header = job.split("\n    steps:\n", maxsplit=1)[0]
        assert "needs.select.outputs.mode != 'none'" not in header
        assert "Record documentation-only scope" in job
    assert "matrix:" in validate_job


def test_targeted_builds_use_release_manifest_preparation() -> None:
    workflow = VALIDATION.read_text(encoding="utf-8")
    build_job = workflow.split("\n  build:\n", maxsplit=1)[1].split("\n  validate:\n", maxsplit=1)[0]
    preparation = build_job.split(
        "      - name: Prepare repository-wide release manifests\n",
        maxsplit=1,
    )[1].split(
        "      - name: Build deterministic MKPs\n",
        maxsplit=1,
    )[0]
    assert "if: needs.select.outputs.mode != 'none'" in preparation
    assert "prepare_repository_mkp_release.py" in preparation
    assert build_job.index("prepare_repository_mkp_release.py") < build_job.index(
        "build_repository_mkps.py"
    )


def test_release_preparation_cannot_modify_package_source_layout() -> None:
    preparation = PREPARE.read_text(encoding="utf-8")
    normalizer = NORMALIZER.read_text(encoding="utf-8")
    assert "normalize_bakery" not in preparation
    assert "normalize_alertmanager" not in preparation
    assert ".unlink()" not in preparation
    assert "_desired_bakery_state" in normalizer
    assert "_desired_alertmanager_state" in normalizer


def test_guard_rejects_pending_source_normalization() -> None:
    workflow = GUARD.read_text(encoding="utf-8")
    assert "Verify package source normalization" in workflow
    assert "python3 tools/ci/normalize_package_sources.py" in workflow


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


def test_validation_and_guard_concurrency_are_isolated_by_event() -> None:
    assert "${{ github.event_name }}" in VALIDATION.read_text(encoding="utf-8").split(
        "\nconcurrency:\n", maxsplit=1
    )[1].split("\nenv:\n", maxsplit=1)[0]
    assert "${{ github.event_name }}" in GUARD.read_text(encoding="utf-8").split(
        "\nconcurrency:\n", maxsplit=1
    )[1].split("\njobs:\n", maxsplit=1)[0]


def test_publication_uses_release_branch_and_pull_request() -> None:
    workflow = PUBLICATION.read_text(encoding="utf-8")
    assert "workflow_run:" in workflow
    assert "RELEASE_BRANCH: automation/repository-mkp-release" in workflow
    assert "HEAD:refs/heads/$RELEASE_BRANCH" in workflow
    assert "gh pr create" in workflow
    assert "HEAD:master" not in workflow
    assert "pull-requests: write" in workflow


def test_publication_requires_exact_source_security_guard() -> None:
    workflow = PUBLICATION.read_text(encoding="utf-8")
    guard_step = workflow.split("- name: Require exact source security guard", maxsplit=1)[1].split(
        "- name: Download exact validated MKP artifacts", maxsplit=1
    )[0]
    assert "--workflow repository-guard.yml" in guard_step
    assert '--commit "$SOURCE_SHA"' in guard_step
    assert "--event push" in guard_step
    assert 'if [[ "$conclusion" == "success" ]]' in guard_step
    assert "Exact source security guard did not complete successfully" in guard_step


def test_publication_aborts_stale_source_without_failing_or_pushing() -> None:
    workflow = PUBLICATION.read_text(encoding="utf-8")
    current = workflow.split("- name: Verify source commit is still current", maxsplit=1)[1].split(
        "- name: Stage complete release", maxsplit=1
    )[0]
    assert 'echo "current=false"' in current
    assert "exit 78" not in current
    assert "if: steps.source.outputs.current == 'true'" in workflow


def test_second_stale_check_gates_pr_and_dispatch_steps() -> None:
    workflow = PUBLICATION.read_text(encoding="utf-8")
    branch_step = workflow.split("- name: Update automation release branch", maxsplit=1)[1].split(
        "- name: Open or update release pull request", maxsplit=1
    )[0]
    assert "id: branch" in branch_step
    assert 'echo "published=false"' in branch_step
    assert 'echo "published=true"' in branch_step
    assert workflow.count("if: steps.branch.outputs.published == 'true'") == 2


def test_workflow_created_release_pr_gets_explicit_exact_head_checks() -> None:
    workflow = PUBLICATION.read_text(encoding="utf-8")
    assert "actions: write" in workflow
    dispatch = workflow.split("- name: Dispatch exact-head release validation", maxsplit=1)[1]
    assert "gh workflow run repository-guard.yml" in dispatch
    assert "gh workflow run repository-mkp-ci.yml" in dispatch
    assert '--ref "$RELEASE_BRANCH"' in dispatch


def test_guard_supports_release_branch_workflow_dispatch() -> None:
    workflow = GUARD.read_text(encoding="utf-8")
    range_step = workflow.split("- name: Resolve comparison range", maxsplit=1)[1].split(
        "- name: Enforce changed-code policy", maxsplit=1
    )[0]
    assert 'elif [[ "$EVENT_NAME" == "push"' in range_step
    assert 'git fetch origin master' in range_step
    assert 'git merge-base origin/master "$CURRENT_SHA"' in range_step


def test_weekly_schedule_reuses_manual_full_validation_path() -> None:
    workflow = SCHEDULE.read_text(encoding="utf-8")
    assert 'cron: "17 3 * * 0"' in workflow
    assert "actions: write" in workflow
    assert "gh workflow run repository-mkp-ci.yml" in workflow
    assert "--ref master" in workflow
    assert "checkmk/check-mk" not in workflow


def test_master_and_manual_runs_force_full_selection() -> None:
    workflow = VALIDATION.read_text(encoding="utf-8")
    assert "--event-name \"$EVENT_NAME\"" in workflow
    selector = (
        REPOSITORY / ".github/scripts/detect_affected_packages.py"
    ).read_text(encoding="utf-8")
    assert 'if event_name != "pull_request"' in selector

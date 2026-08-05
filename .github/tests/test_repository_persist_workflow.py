from __future__ import annotations

from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
WORKFLOW = REPOSITORY / ".github/workflows/repository-mkp-ci.yml"


def test_persist_job_regenerates_code_derived_outputs_after_manifest_staging() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    persist = workflow.split("\n  persist:\n", maxsplit=1)[1]
    staging = persist.split(
        "      - name: Verify and stage complete package set\n",
        maxsplit=1,
    )[1].split(
        "      - name: Commit package set if source is still current\n",
        maxsplit=1,
    )[0]

    ordered_commands = (
        "(target_dir / \"src\" / \"info\").write_bytes(info_file.read())",
        "python tools/ci/sync_package_metadata.py --write",
        "python update_readmes.py",
        "python tools/ci/generate_package_reference.py --write",
        "python create_mkp_index.py",
    )
    positions = [staging.index(command) for command in ordered_commands]

    assert positions == sorted(positions)

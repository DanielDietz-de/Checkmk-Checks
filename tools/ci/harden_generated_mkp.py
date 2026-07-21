#!/usr/bin/env python3
"""Add provenance and stale-source protection to the shared MKP workflow."""

from __future__ import annotations

import sys
from pathlib import Path

WORKFLOW = Path(".github/workflows/generated-mkp-ci.yml")


class PatchError(RuntimeError):
    pass


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise PatchError(f"expected one {label} block, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    try:
        text = WORKFLOW.read_text(encoding="utf-8")

        text = replace_once(
            text,
            '''          (\n            cd "$PACKAGE_DIR"\n            sha256sum "$PACKAGE_FILENAME" >"${PACKAGE_FILENAME}.sha256"\n          )\n''',
            '''          (\n            cd "$PACKAGE_DIR"\n            sha256sum "$PACKAGE_FILENAME" >"${PACKAGE_FILENAME}.sha256"\n          )\n          python3 - <<'PY'\n          import hashlib\n          import json\n          import os\n          from pathlib import Path\n\n          source = Path(os.environ["PACKAGE_SOURCE"])\n          digest = hashlib.sha256()\n          files = []\n          for path in sorted(item for item in source.rglob("*") if item.is_file()):\n              relative = path.relative_to(source).as_posix()\n              content = path.read_bytes()\n              digest.update(relative.encode("utf-8") + b"\\0")\n              digest.update(hashlib.sha256(content).digest())\n              files.append(relative)\n          provenance = {\n              "schema_version": 1,\n              "package_name": os.environ["PACKAGE_NAME"],\n              "package_version": os.environ["PACKAGE_VERSION"],\n              "source_commit": os.environ["GITHUB_SHA"],\n              "source_tree_sha256": digest.hexdigest(),\n              "source_file_count": len(files),\n              "builder_image": os.environ["PACKAGING_IMAGE"],\n              "packaged_version": os.environ["PACKAGED_VERSION"],\n              "usable_until": os.environ["USABLE_UNTIL"],\n          }\n          output = Path(os.environ["PACKAGE_DIR"]) / (\n              os.environ["PACKAGE_FILENAME"] + ".provenance.json"\n          )\n          output.write_text(\n              json.dumps(provenance, indent=2, sort_keys=True) + "\\n",\n              encoding="utf-8",\n          )\n          PY\n''',
            "provenance generation",
        )

        text = replace_once(
            text,
            '''            ${{ env.PACKAGE_DIR }}/${{ steps.metadata.outputs.filename }}\n            ${{ env.PACKAGE_DIR }}/${{ steps.metadata.outputs.filename }}.sha256\n''',
            '''            ${{ env.PACKAGE_DIR }}/${{ steps.metadata.outputs.filename }}\n            ${{ env.PACKAGE_DIR }}/${{ steps.metadata.outputs.filename }}.sha256\n            ${{ env.PACKAGE_DIR }}/${{ steps.metadata.outputs.filename }}.provenance.json\n''',
            "artifact upload",
        )

        text = replace_once(
            text,
            '''          package_path="${PACKAGE_DIR}/${PACKAGE_FILENAME}"\n          checksum_path="${package_path}.sha256"\n          test -f "$package_path"\n          test -f "$checksum_path"\n          (\n            cd "$PACKAGE_DIR"\n            sha256sum --check "${PACKAGE_FILENAME}.sha256"\n          )\n          remote_url="https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"\n          git config user.name "github-actions[bot]"\n          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"\n          git add -- "$package_path" "$checksum_path"\n          if git diff --cached --quiet; then\n            echo "Generated MKP is unchanged; nothing to commit."\n            exit 0\n          fi\n          git commit -m "build(${PACKAGE_NAME}): update MKP ${PACKAGE_VERSION} [skip ci]"\n          git fetch "$remote_url" "$GITHUB_REF_NAME"\n          git rebase FETCH_HEAD\n          git push "$remote_url" "HEAD:${GITHUB_REF_NAME}"\n''',
            '''          package_path="${PACKAGE_DIR}/${PACKAGE_FILENAME}"\n          checksum_path="${package_path}.sha256"\n          provenance_path="${package_path}.provenance.json"\n          test -f "$package_path"\n          test -f "$checksum_path"\n          test -f "$provenance_path"\n          (\n            cd "$PACKAGE_DIR"\n            sha256sum --check "${PACKAGE_FILENAME}.sha256"\n          )\n          python3 - <<'PY'\n          import json\n          import os\n          from pathlib import Path\n\n          path = Path(os.environ["PACKAGE_DIR"]) / (\n              os.environ["PACKAGE_FILENAME"] + ".provenance.json"\n          )\n          data = json.loads(path.read_text(encoding="utf-8"))\n          if data.get("source_commit") != os.environ["GITHUB_SHA"]:\n              raise SystemExit("provenance source commit does not match workflow commit")\n          if data.get("package_name") != os.environ["PACKAGE_NAME"]:\n              raise SystemExit("provenance package name does not match")\n          if data.get("package_version") != os.environ["PACKAGE_VERSION"]:\n              raise SystemExit("provenance package version does not match")\n          PY\n          remote_url="https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"\n          git fetch "$remote_url" "$GITHUB_REF_NAME"\n          if [[ "$(git rev-parse FETCH_HEAD)" != "$GITHUB_SHA" ]]; then\n            echo "::warning::Master moved after this build started; refusing to commit a stale MKP artifact."\n            exit 0\n          fi\n          git config user.name "github-actions[bot]"\n          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"\n          git add -- "$package_path" "$checksum_path" "$provenance_path"\n          if git diff --cached --quiet; then\n            echo "Generated MKP is unchanged; nothing to commit."\n            exit 0\n          fi\n          git commit -m "build(${PACKAGE_NAME}): update MKP ${PACKAGE_VERSION} [skip ci]"\n          git push "$remote_url" "HEAD:${GITHUB_REF_NAME}"\n''',
            "artifact persistence",
        )

        WORKFLOW.write_text(text, encoding="utf-8")
    except (OSError, PatchError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Hardened {WORKFLOW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

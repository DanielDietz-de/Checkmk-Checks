# MKP CI and publication architecture

This document defines the authoritative behavior of repository-wide Checkmk package validation and publication. The workflows and scripts are the executable source of truth; this document explains their security and operational model.

## Objectives

The CI design has two distinct responsibilities:

1. validate source changes with the smallest safe package scope; and
2. publish generated MKP release state without writing directly to the protected default branch.

These responsibilities are deliberately separated. Validation workflows are read-only. Publication starts only after a successful full validation on `master`, writes to a fixed automation branch, and opens or updates a normal pull request.

## Validation modes

`.github/scripts/detect_affected_packages.py` classifies each pull request into one of three modes.

### `targeted`

Use targeted validation when every relevant change maps unambiguously to one or more active package directories and is confined to that package's `src/` or `tests/` tree.

For each selected package, CI:

- runs its tests together with other selected packages to detect collection collisions;
- reruns each selected test directory independently for attributable failures;
- builds only its deterministic MKP archive and checksum; and
- installs and validates only the selected MKPs on the supported Checkmk 2.4 and 2.5 images.

Repository security, metadata, generated-documentation, syntax, and supply-chain guards remain repository-wide and run in the separate repository guard workflow.

### `full`

Full validation is mandatory when a change can affect more than one package or the selector cannot prove a narrower scope. Full mode runs all package tests, builds all active MKPs, validates every compatible package and manual on both supported Checkmk versions, and exercises the complete publication transaction as a dry run on pull requests.

Full mode is selected for:

- changes to workflows, repository packaging scripts, release tests, shared CI tooling, generators, or release configuration;
- generated MKP artifacts or the repository package index;
- renames, copies, deletions, unknown Git statuses, malformed paths, or incomplete comparison data;
- changes outside a known active package or an approved documentation-only path;
- every push to `master`; and
- every manual workflow run.

The selector fails safe: uncertainty expands validation to the full repository rather than skipping checks.

### `none`

Documentation-only changes can skip the expensive package build and Checkmk matrix. The repository guard still validates immutable dependencies, generated facts, metadata mirrors, code-derived documentation, syntax, audit policy, and CI-tool tests.

## Selector trust model

Active packages are discovered only from canonical top-level `*/src/info` manifests. User-controlled paths are treated as POSIX repository paths and rejected if they are absolute, contain `..`, do not map to a known package, or fall outside an explicitly understood path class.

Rename, copy, and delete operations deliberately force full validation. This avoids under-validating cross-package moves or removals when only one side of the operation appears package-local.

The selector emits structured outputs:

- `mode`: `none`, `targeted`, or `full`;
- `packages`: a JSON array of selected package directories;
- `package-count`; and
- a human-readable reason recorded in the workflow summary.

## Read-only validation workflow

`.github/workflows/repository-mkp-ci.yml` has repository read permission only. It never commits or pushes source or generated output.

The workflow preserves the existing required job names while changing their internal scope. This avoids silently invalidating branch-protection configuration or downstream reporting.

For full pull requests and manual runs, the `publication-dry-run` job executes the same release transaction used after merge:

1. finalize canonical release metadata;
2. stage the complete validated artifact set into package directories;
3. regenerate metadata mirrors, README content, package references, and `mkp_index.json`;
4. rebuild the staged repository state;
5. byte-compare every rebuilt MKP with the already validated artifact;
6. require the release configuration to be finalized; and
7. reject any changed path outside the documented generated-output allowlist.

The dry-run patch is retained as workflow evidence but is never committed from the validation workflow.

## Publication workflow

`.github/workflows/repository-mkp-publication.yml` is triggered by a successful `Repository MKP validation` workflow run for a push to `master`.

It uses the exact source SHA and artifact run that passed validation. Before and immediately before publishing, it verifies that `master` still points to that SHA. If `master` has advanced, the job exits without publishing; the newer validation run becomes authoritative.

Publication then:

1. downloads the exact validated full-repository artifact;
2. verifies checksums, package names, versions, archive manifests, safe paths, and complete package coverage;
3. stages and regenerates the release state;
4. rebuilds and byte-compares every package;
5. rejects unexpected source or workflow changes;
6. commits only generated release paths;
7. updates `automation/repository-mkp-release` with `--force-with-lease`; and
8. opens or updates a pull request targeting `master`.

The workflow never pushes to `master`.

## Permission model

The validation workflow has only `contents: read`.

The publication job has the minimum permissions needed for its isolated responsibility:

- `actions: read` to download artifacts from the validated run;
- `contents: write` to update the dedicated automation branch; and
- `pull-requests: write` to create or update the release PR.

The workflow uses `persist-credentials: false`. A short-lived `GITHUB_TOKEN` is supplied only to the explicit branch push and GitHub CLI pull-request operations. Third-party actions remain pinned to immutable commit SHAs, and Checkmk images remain pinned by digest.

## Release-staging safeguards

`.github/scripts/stage_repository_release.py` does not extract archives into the working tree. It reads exactly one `info` member from each archive and rejects archives with missing or duplicate manifests.

It also rejects:

- path traversal or paths escaping the artifact directory;
- unsafe package directory or package names;
- duplicate package directories;
- checksum mismatches;
- package-index and manifest name/version mismatches;
- symlinked package targets; and
- partial or unexpected package sets.

Publication requires the artifact package-directory set to equal the active canonical manifest set exactly.

## Determinism and bounded output

`.github/scripts/verify_repository_release.py` requires the staged repository to rebuild to the same package index and identical MKP SHA-256 values as the validated artifact set.

Only these generated path classes may change during publication:

- `.github/repository-mkp-release.json`;
- root `README.md` and `mkp_index.json`;
- package `README.md`;
- package `src/info` and retained `src/info.json` mirrors; and
- top-level package `.mkp` and `.mkp.sha256` files.

A release preparation step that attempts to modify executable source, tests, workflows, or other hand-written files fails and must be introduced through a normal reviewed source PR.

## Concurrency and recursion

Validation uses per-ref concurrency and cancels superseded runs. Publication uses a repository-wide serial concurrency group and does not cancel an in-flight publication transaction.

The publication workflow only responds to successful push-triggered validation runs on `master`. Pull-request validation runs and changes to the automation release branch cannot recursively start publication.

After the generated release PR is merged, `master` is fully validated again. Publication then finds no generated diff and exits without creating another release PR.

## Troubleshooting

### Selector unexpectedly chooses `full`

Read the `MKP validation scope` workflow summary. Full mode is expected for shared tooling, generated artifacts, renames/deletions, unknown top-level paths, and any comparison failure.

### Selector chooses `none`

Confirm that the change is documentation-only. Repository-wide guards still run. A source or test path under an active package must result in targeted mode.

### Publication does not create a PR

Check, in order:

1. the source `Repository MKP validation` run completed successfully;
2. it was a push run on `master`;
3. the validated source SHA was still current when publication ran; and
4. the staged generated state actually differs from `master`.

A no-change result after the generated release PR has already been merged is expected.

### Publication rejects the artifact set

Do not bypass the check. Investigate missing or extra package directories, mismatched `packages.json` metadata, archive checksums, or a non-deterministic build. The full artifact set must be regenerated from the same source SHA.

### Publication reports an unexpected changed path

The release preparation attempted to modify hand-written content. Move that source change into a normal PR, add focused tests and documentation, and allow publication to remain generated-output-only.

## Changing this architecture

Any change to the selector, packaging scripts, workflows, release configuration, or publication tests automatically selects full validation. The change must include focused regression tests and keep this document synchronized with executable behavior.

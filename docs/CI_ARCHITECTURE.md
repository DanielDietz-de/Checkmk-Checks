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
- every push to `master`;
- every manual workflow run; and
- every scheduled repository validation.

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

## Scheduled full validation

`.github/workflows/repository-mkp-schedule.yml` runs weekly at `03:17 UTC` on Sunday and can also be started manually. It contains no duplicate package or Checkmk logic. With only `actions: write` and `contents: read`, it dispatches `repository-mkp-ci.yml` on `master`.

The resulting `workflow_dispatch` run is classified as `full`, so the complete package tests, 97-package build, supported Checkmk matrix, and publication dry-run execute from the same authoritative workflow used by reviewed changes. Scheduled validation never publishes release state because the publication workflow accepts only successful push-triggered validation runs on `master`.

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
7. updates `automation/repository-mkp-release` with `--force-with-lease`;
8. opens or updates a pull request targeting `master`; and
9. explicitly dispatches the repository guard and full MKP validation workflows against the exact automation-branch head.

The workflow never pushes to `master`.

## Exact-head checks for workflow-created PRs

GitHub suppresses most workflow events created with a repository's own `GITHUB_TOKEN`. A release PR opened by the publication workflow therefore cannot rely on the ordinary `pull_request` event to start its required checks.

The publication job explicitly invokes `workflow_dispatch` for:

- `.github/workflows/repository-guard.yml`; and
- `.github/workflows/repository-mkp-ci.yml`.

Both dispatches target `automation/repository-mkp-release`. The MKP selector treats every manual run as full validation. The repository guard resolves a manual-run comparison range from the merge base of `origin/master` and the dispatched head SHA, so changed-code policy is evaluated against the generated release diff rather than an empty event field.

`workflow_dispatch` is an intentional GitHub exception to token-created-event suppression. The resulting check runs are attached to the release branch's exact head commit and must be green before merge.

## Permission model

The validation workflow has only `contents: read`.

The scheduled dispatcher has `actions: write` only to create the authoritative manual validation run and `contents: read` for repository metadata.

The publication job has the minimum permissions needed for its isolated responsibility:

- `actions: write` to download the validated artifact and explicitly dispatch exact-head release checks;
- `contents: write` to update the dedicated automation branch; and
- `pull-requests: write` to create or update the release PR.

The workflows use `persist-credentials: false` whenever repository content is checked out. A short-lived `GITHUB_TOKEN` is supplied only to explicit automation-branch pushes, pull-request operations, and workflow dispatches. Third-party actions remain pinned to immutable commit SHAs, and Checkmk images remain pinned by digest.

The repository or organization must permit GitHub Actions to create pull requests. If that setting is disabled, publication fails closed at PR creation; do not replace the workflow token with an unmanaged personal token merely to bypass policy.

## Release-staging safeguards

`.github/scripts/stage_repository_release.py` does not extract archives into the working tree. It reads exactly one bounded `info` member from each archive and rejects archives with missing, duplicate, or oversized manifests. The exact validated manifest bytes are written back to the canonical `src/info` path; the staging helper does not reformat or reinterpret the release manifest when publishing it.

It also rejects:

- path traversal or paths escaping the artifact directory;
- artifact paths that do not exactly match package directory, name, and version;
- unsafe package directory, package name, or version tokens;
- duplicate package directories;
- malformed checksum records or checksum mismatches;
- package-index and manifest name/version mismatches;
- symlinked artifacts, package targets, source targets, or manifest targets; and
- partial or unexpected package sets.

Publication requires the artifact package-directory set to equal the active canonical manifest set exactly.

## Determinism and bounded output

`.github/scripts/verify_repository_release.py` requires the staged repository to rebuild to the same validated package identities and identical MKP SHA-256 values. It validates artifact containment independently, rejects unsafe or duplicate index identities, and reads changed Git paths with NUL delimiters so unusual filenames cannot bypass the allowlist.

Only these generated path classes may change during publication, and package-scoped paths must belong to an active canonical package:

- `.github/repository-mkp-release.json`;
- root `README.md` and `mkp_index.json`;
- package `README.md`;
- package `src/info` and retained `src/info.json` mirrors; and
- top-level package `.mkp` and `.mkp.sha256` files.

A release preparation step that attempts to modify executable source, tests, workflows, unknown package directories, or other hand-written files fails and must be introduced through a normal reviewed source PR.

## Concurrency and recursion

Validation uses per-ref concurrency and cancels superseded runs. Scheduled dispatch and publication each use a repository-wide serial concurrency group and do not cancel an in-flight transaction.

The publication workflow only performs work for successful push-triggered validation runs on `master`. Pull-request, scheduled, and manually dispatched validation runs may produce a `workflow_run` event, but the publication job rejects them because their event is not `push` on `master`.

After the generated release PR is merged, `master` is fully validated again. Publication then finds no generated diff and exits without creating another release PR.

## Troubleshooting

### Selector unexpectedly chooses `full`

Read the `MKP validation scope` workflow summary. Full mode is expected for shared tooling, generated artifacts, renames/deletions, unknown top-level paths, scheduled/manual events, and any comparison failure.

### Selector chooses `none`

Confirm that the change is documentation-only. Repository-wide guards still run. A source or test path under an active package must result in targeted mode.

### Scheduled validation did not start

Check the `Schedule repository MKP validation` workflow and its `Dispatch weekly full validation` job. It must have `actions: write`, and `repository-mkp-ci.yml` must expose `workflow_dispatch`. The dispatcher does not itself run package tests; a separate full `Repository MKP validation` run on `master` is the expected result.

### Publication does not create a PR

Check, in order:

1. the source `Repository MKP validation` run completed successfully;
2. it was a push run on `master`;
3. the validated source SHA was still current when publication ran;
4. the staged generated state actually differs from `master`; and
5. repository Actions policy permits `GITHUB_TOKEN` to create pull requests.

A no-change result after the generated release PR has already been merged is expected.

### Release PR exists but checks are absent

The publication job must finish its `Dispatch exact-head release validation` step. Confirm that it has `actions: write` and that both workflow files expose `workflow_dispatch`. Do not merge a release PR without the dispatched repository guard and full MKP checks on its current head.

### Publication rejects the artifact set

Do not bypass the check. Investigate missing or extra package directories, mismatched `packages.json` metadata, archive checksums, unsafe paths, oversized manifests, or a non-deterministic build. The full artifact set must be regenerated from the same source SHA.

### Publication reports an unexpected changed path

The release preparation attempted to modify hand-written content or an unknown package directory. Move that source change into a normal PR, add focused tests and documentation, and allow publication to remain generated-output-only.

## Changing this architecture

Any change to the selector, packaging scripts, workflows, release configuration, scheduled dispatcher, or publication tests automatically selects full validation. The change must include focused regression tests and keep this document synchronized with executable behavior.

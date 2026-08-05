# Repository maintenance and assurance levels

This repository contains extensions from multiple Checkmk generations. Source code, canonical `*/src/info` manifests, tests, and generated workflow evidence are authoritative. Narrative documentation is a derived operational view and must never override conflicting implementation facts.

## Assurance levels

### Runtime-validated

A package reaches this level only when the repository workflow loads the plug-in in the declared Checkmk releases, runs its tests, validates manuals and configuration where applicable, and builds or inspects its MKP with the declared packaging release.

### Source-tested

The package has focused parser, discovery, check, notification, agent, or security tests, but may not have representative device or application fixtures. Its README and metadata must not claim a broader runtime range than the available evidence supports.

### Structurally validated

Every active package has a package-local integrity suite covering its canonical manifest, retained JSON mirror, generated documentation marker, and Python syntax. This proves repository structure, not vendor behavior. A package remains structurally validated until representative fixtures or live-system evidence justify a higher assurance level.

## Code-first documentation model

The maintenance order is mandatory:

1. inspect or change executable code, rulesets, manifests, tests, and packaged file lists;
2. validate the actual runtime and compatibility consequences;
3. update manuals and human-written rationale;
4. regenerate package operational references with `tools/ci/generate_package_reference.py --write`;
5. run the consistency and audit gates.

The generated README block inventories actual source components, registrations, emitted sections, credentials, transport behavior, tests, and artifacts. CI rejects a stale block. Compatibility fields are evidence claims: `version.usable_until = None` means that no upper release has been asserted, not that all later releases are supported.

## Changed-code policy

The repository guard applies strict rules whenever package source changes:

- changed Python must parse;
- built-in `eval`, `shell=True`, plaintext `Secret.unsafe()`, global TLS-warning suppression, and literal `verify=False` calls are rejected;
- a changed package must contain at least one `tests/test_*.py` file;
- touched package metadata must be complete and consistent between `src/info` and any retained `src/info.json`;
- reviewed exceptions require an inline rationale and focused evidence.

These changed-code checks are complemented by full-tree gates; untouched code is not exempt from repository-wide security and documentation enforcement.

## Full-repository enforcement

`tools/ci/full_repository_audit.py` inventories every active package and every top-level packaged source tree for high-signal security patterns, metadata defects, documentation coverage, and inline-documentation gaps. The repository currently requires zero findings at every defined severity by running `--fail-on low`. No residual-finding baseline is used.

Additional deterministic gates verify:

- exact canonical metadata mirrors;
- code-derived README references;
- module docstrings for packaged Python entry points;
- Python syntax across active source, tools, templates, and archived legacy checks;
- package-local integrity tests;
- immutable workflow dependencies; and
- unique package names, packaged destination paths, and statically declared Checkmk registrations across active packages.

The cross-package collision gate is intentionally lightweight and repository-wide. It uses Python AST inspection for static registrations so comments and documentation examples cannot create false collisions. Dynamically constructed registrations remain a reason to retain full clean-site validation for shared changes, package-manifest changes, pushes, schedules, and manual runs.

The policy and limitations are documented in [`docs/REPOSITORY_AUDIT.md`](docs/REPOSITORY_AUDIT.md) and [`docs/CI_ARCHITECTURE.md`](docs/CI_ARCHITECTURE.md).

## Workflow supply chain

All third-party GitHub Actions must use full commit SHAs. Checkmk container images used by CI must use registry manifest digests. Human-readable action tags are retained as comments and the resolved references are recorded in `.github/supply-chain-lock.json`.

To intentionally update dependencies:

```bash
GH_TOKEN=... python3 tools/ci/pin_supply_chain.py --write
python3 tools/ci/pin_supply_chain.py --check
```

Review the resulting workflow and lock-file diff. A dependency update is a source change and must be reviewed like code.

## Change-aware MKP validation

Pull requests are classified as `targeted`, `full`, or `none` by `.github/scripts/detect_affected_packages.py`.

- Non-manifest package-local changes under an active package's `src/` or `tests/` tree select only that package and any other unambiguously affected packages.
- Canonical manifest and retained metadata-mirror changes force full validation because they can alter the active package universe, package identity, compatibility, or global file map.
- Shared tooling, workflows, release configuration, generated artifacts, unknown paths, renames, copies, deletions, malformed comparisons, and output-control characters force full validation.
- Documentation-only changes skip expensive execution, while the existing package/build/Checkmk check names complete successful no-op steps and repository-wide guards still run.
- Every push to `master`, manual run, and scheduled run is full validation.

Selection fails safe. Git paths are read with NUL delimiters, CR/LF are rejected in selector paths, and line-based GitHub outputs are encoded so filenames cannot inject a later `mode` value. A change is never treated as targeted merely because one path appears package-local when the complete operation cannot be mapped with confidence.

Validation and guard concurrency groups are separated by event type. A weekly/manual run on `master` cannot cancel the push-triggered run required for publication.

The selector, trust model, global collision guard, required-check behavior, and troubleshooting procedure are documented in [`docs/CI_ARCHITECTURE.md`](docs/CI_ARCHITECTURE.md).

## Scheduled validation

The weekly dispatcher starts the authoritative `Repository MKP validation` workflow on `master` through `workflow_dispatch`. It does not duplicate package or Checkmk logic. The dispatched run is full and includes all package tests, deterministic builds, both supported Checkmk images, and the publication dry-run.

Scheduled or manually dispatched validation never publishes generated release state. Publication accepts only a successful push-triggered MKP run on `master` and separately requires a successful push-triggered repository guard for the exact same source SHA.

## Generated MKP publication

The repository MKP validation workflow is read-only. It builds deterministic archives, verifies their component inventory and checksums, installs supported packages in clean Checkmk sites, validates packaged manuals, reloads the Checkmk core, and never commits or pushes generated output.

Full pull requests and manual runs execute the complete publication transaction as a dry run. The dry run finalizes release metadata, stages the complete validated artifact set, regenerates code-derived files, rebuilds every staged package, byte-compares the rebuild with the validated artifacts, and rejects any changed path outside the generated-output allowlist.

After a successful full push validation on `master`, the separate publication workflow waits for the exact source commit's push-triggered repository guard to complete successfully. It then uses the exact validated source SHA and workflow artifact, verifies that `master` is still current, repeats the deterministic staging and rebuild checks, updates `automation/repository-mkp-release` with a lease-protected branch update, and opens or refreshes a normal pull request. It never pushes directly to `master`.

The workflow checks `master` both before staging and immediately before the automation-branch update. The second check emits an explicit publication result; PR updates and exact-head workflow dispatches run only after the lease-protected branch push succeeds. A stale transaction therefore cannot advertise or validate an older automation branch.

Because GitHub suppresses ordinary pull-request workflow events created with `GITHUB_TOKEN`, the publication workflow explicitly dispatches the repository guard and full MKP workflow on the release branch's exact head. The generated release PR must pass those checks before merge.

If `master` advances during publication, the stale transaction exits without publishing and the newer validation run becomes authoritative.

## Adding or updating a package

1. Add focused tests for the behavior being changed; the generic integrity test is not a substitute for protocol or state-logic tests.
2. Keep credentials in Checkmk `Secret` objects and resolve password-store references only inside the executable.
3. Bound network timeouts, response sizes, parser inputs, caches, and output fields.
4. Fail closed on incomplete collection rather than publishing partial trusted output.
5. Edit canonical `src/info` first and regenerate retained JSON mirrors. Expect full repository validation for any manifest change.
6. Keep package names, packaged destinations, and Checkmk registration names globally unique.
7. State compatibility based on tested Checkmk releases, not source importability.
8. Add representative fixtures when a vendor integration requires behavior beyond load and registration checks.
9. Update source comments and manuals, then regenerate package README references from code.

## Security exceptions

A narrowly justified exception may use `# security-reviewed: <reason>` only when the risk cannot be removed without breaking a required protocol or supported deployment. The reason must state the constrained trust boundary, and tests must demonstrate that the exception cannot broaden silently. An exception marker does not suppress the full-tree audit unless the corresponding audit rule explicitly models it.

## What “ready to use” means

A package is ready for production consideration only when:

- its compatibility metadata covers the target Checkmk version with evidence;
- its code-derived README reference and human guidance match the source;
- relevant structural and focused behavior tests pass;
- the repository MKP workflow validates it on the target Checkmk generation;
- representative vendor data or live-system validation covers behavior that clean-site loading cannot prove;
- no unresolved repository-audit or cross-package collision finding remains;
- the operator validates it in a non-production site before broad deployment.

Repository-level green status is necessary but not sufficient for every vendor, firmware, and environment combination.

## Test collection

Full validation first executes all package tests in one pytest collection, then executes every package test directory independently so module-name collisions are caught and failures remain attributable to a package. Targeted validation applies the same two-stage model to the selected package set. Repository release, selector, staging, workflow-structure, publication-verification, and collision-guard tests run for every non-documentation MKP validation.

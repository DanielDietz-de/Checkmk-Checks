# Repository audit and residual-risk model

## Purpose

The repository contains active packages from multiple Checkmk generations. A single clean build does not establish that every legacy vendor integration is secure, fully documented, and behaviorally validated. This audit model separates facts that can be checked deterministically from claims that require representative fixtures or live systems.

## Current controls

The repository uses four complementary layers:

1. **Package tests** exercise package-specific behavior where tests exist.
2. **Repository MKP validation** builds deterministic archives, verifies manifests and checksums, installs supported packages in clean Checkmk sites, validates manuals, and reloads Checkmk.
3. **Changed-code guardrails** reject newly introduced high-risk patterns and require tests for changed package source.
4. **Full-tree audit** inventories documentation and high-signal security findings across all active source, including untouched legacy packages.

## Full-tree audit

`tools/ci/full_repository_audit.py` produces deterministic JSON containing:

- active package and source-file counts;
- missing or thin root/package documentation;
- incomplete metadata and documentation coverage indicators;
- missing Python module docstrings;
- dynamic code execution;
- shell invocation;
- disabled TLS verification and warning suppression;
- plaintext Checkmk secret flattening;
- unsafe deserialization;
- likely committed private keys or common token formats;
- tracked bytecode and sensitive file names.

The checks are intentionally high-signal and do not claim to replace manual code review, dependency analysis, live vendor testing, or deployment-specific threat modeling.

## Baseline policy

Existing findings are not hidden. Reviewed legacy findings are recorded by deterministic fingerprint in `.github/repository-audit-baseline.json`. CI still publishes the complete report, but fails when a new non-baselined finding reaches the configured severity threshold.

A baseline entry is not an approval or a declaration of safety. It means only that the finding existed when the baseline was reviewed. Remove fingerprints as findings are fixed. Never add a fingerprint merely to make CI green without validating the code and documenting residual risk.

## Severity and remediation

- **Critical:** credible credential material or direct dynamic-code execution. Remediate before release unless conclusively proven to be a non-production fixture.
- **High:** shell execution, disabled TLS verification, unsafe deserialization, secret flattening, unreadable source, or missing required security documentation. Prioritize package isolation and focused remediation.
- **Medium:** incomplete metadata, thin documentation, stale generated files, or repository hygiene defects.
- **Low:** documentation coverage and inline-documentation gaps that reduce maintainability but are not direct vulnerabilities.

## What “ready to use” means

A package is ready for production consideration only when:

- its compatibility metadata covers the target Checkmk version;
- its README explains deployment and security boundaries;
- relevant package tests pass;
- the repository MKP workflow validates it on the target Checkmk generation;
- representative vendor data or live-system validation covers behavior that clean-site loading cannot prove;
- no unresolved critical or applicable high-risk finding remains;
- the operator validates it in a non-production site before broad deployment.

Repository-level green status is necessary but not sufficient for every package and every environment.

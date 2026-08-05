# Repository audit and residual-risk model

## Purpose

The repository contains active packages from multiple Checkmk generations. The audit establishes deterministic facts about the checked-in implementation. It does not infer correctness from historical README text and does not turn clean static analysis into proof of every vendor response, firmware version, or production topology.

## Authority order

When sources disagree, use this order:

1. executable source and registered Checkmk objects;
2. canonical `*/src/info` manifests and their packaged file lists;
3. tests, sanitized fixtures, and workflow artifacts;
4. generated package README reference blocks;
5. manually maintained narrative documentation.

Documentation must be corrected to match code unless the code itself is defective, in which case the code and tests are fixed first.

## Enforced controls

The repository uses complementary layers:

1. **Package tests** provide a structural suite for every active package and focused behavior tests where they exist.
2. **Repository MKP validation** builds deterministic archives, verifies manifests and checksums, installs supported packages in clean Checkmk sites, validates manuals, and reloads Checkmk.
3. **Changed-code guardrails** reject high-risk patterns and require package tests for changed source.
4. **Full-tree audit** scans all active packages and every top-level packaged source tree, including untouched legacy code.
5. **Consistency generators** prove that JSON metadata mirrors, package operational references, and module documentation match current source.
6. **Repository syntax validation** parses active code, CI tooling, templates, and archived legacy Python checks without importing Checkmk.

## Full-tree audit

`tools/ci/full_repository_audit.py` produces deterministic JSON containing:

- active package and source-file counts;
- required root and package documentation coverage;
- canonical metadata completeness and representation mismatches;
- missing packaged Python module docstrings;
- unresolved Checkmk password-store reference boundaries;
- dynamic code execution and shell invocation;
- disabled TLS verification and global warning suppression;
- network calls without explicit bounded timeouts;
- plaintext Checkmk secret flattening;
- unsafe deserialization;
- likely committed private keys or common token formats;
- repository hygiene defects.

CI runs the audit with `--fail-on low`. The accepted repository state is therefore zero findings across critical, high, medium, and low severities. No audit baseline file is used to suppress legacy findings.

## Generated documentation and metadata

- `tools/ci/sync_repository_facts.py` derives repository-level package counts from canonical manifests.
- `tools/ci/sync_package_metadata.py` treats `src/info` as canonical and requires any existing `src/info.json` to be an exact deterministic rendering.
- `tools/ci/generate_package_reference.py` derives package README operational blocks from manifests, source paths, registrations, emitted sections, transport and credential patterns, tests, and artifacts.
- `tools/ci/manage_module_docstrings.py` requires concise role-specific module descriptions for packaged Python source.
- `tools/ci/check_python_syntax.py` validates Python syntax across the repository, including extensionless legacy Checkmk checks.

The package-reference network detector covers recognized Python, PHP, shell, PowerShell, Perl, Ruby, and Java client patterns. A negative static result is deliberately qualified and is never documented as proof that a package cannot perform remote access.

These tools detect staleness; they do not manufacture unsupported compatibility or behavioral claims. `version.usable_until = None` explicitly records that no upper Checkmk version is asserted.

## Severity and remediation

- **Critical:** credible credential material or direct dynamic-code execution. Release is blocked.
- **High:** shell execution, disabled TLS verification, unsafe deserialization, secret flattening, unresolved password-store references, unreadable source, or missing required security documentation. Release is blocked.
- **Medium:** unbounded network calls, incomplete metadata, thin documentation, stale generated representations, or significant hygiene defects. Release is blocked.
- **Low:** package documentation coverage and module-documentation gaps. Release is blocked.

A zero-finding audit means only that the defined deterministic rules found no violation in the audited tree. Manual review and representative runtime testing remain required where static evidence cannot establish behavior.

## Current audited state

At the completion of this repository-wide remediation, the local deterministic report covers **97 active packages** and reports **0 critical, 0 high, 0 medium, and 0 low findings**. CI regenerates this evidence for every pull request and publishes the JSON report with the exact audited source snapshot.

## What “ready to use” means

A package is ready for production consideration only when:

- its compatibility metadata includes the target Checkmk version based on evidence;
- its generated and manual documentation match actual code and rules;
- package structural tests and relevant focused tests pass;
- the repository MKP workflow validates it on the target Checkmk generation;
- representative vendor data or live-system validation covers behavior that clean-site loading cannot prove;
- no repository-audit finding remains;
- the operator validates it in a non-production site before broad deployment.

Repository-level green status is necessary but not sufficient for every package and environment.

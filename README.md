# Checkmk Checks and Extensions

Community-maintained Checkmk extensions, special agents, agent plug-ins, notification integrations, Bakery plug-ins, rulesets, check plug-ins, manuals, and installable MKP packages.

The repository is maintained under the `DanielDietz-de` organization and contains code from several generations of Checkmk. Executable source and canonical `*/src/info` manifests are authoritative. The generated [`mkp_index.json`](mkp_index.json), README reference blocks, and MKP archives are derived outputs and must be regenerated when source or metadata changes. Historical copyright and license terms remain in [`LICENSE`](LICENSE).

## Repository status

The repository-wide release workflow currently discovers **97 active packages** from their canonical `*/src/info` manifests. It runs package tests, builds deterministic MKP archives, verifies checksums and package inventories, and validates supported packages in clean Checkmk 2.4 and 2.5 sites before publication.

A package being present does **not** automatically mean that every device-specific behavior has been validated against live hardware. Use the compatibility fields and documentation in each package directory, and review the assurance model in [`MAINTENANCE.md`](MAINTENANCE.md).

## Find a package

Use [`mkp_index.json`](mkp_index.json) to search by package name, title, description, version, required Checkmk version, and MKP path. Each active package lives in a top-level directory and normally contains:

```text
<package>/
├── README.md              Narrative guidance plus a generated source inventory
├── src/                   Canonical source and package manifest
├── tests/                 Structural and focused behavior tests
├── <package>-<version>.mkp         Current validated artifact on master
└── <package>-<version>.mkp.sha256  Matching checksum on master
```

Generated MKP files are release artifacts. Pull-request branches may not contain the next current archive yet: CI builds and validates the complete set first, and the post-merge persistence job replaces historical package archives with one validated current MKP and checksum per package. Source under `src/` remains authoritative throughout. Package operational reference blocks are generated from the canonical manifest and current source tree; change code or metadata first and then regenerate documentation.

## Installation

1. Select a package whose `version.min_required` and evidence-based compatibility range cover the target Checkmk release. A null `version.usable_until` means no upper release is asserted; it is not an unlimited-support claim.
2. Read the package README completely, including prerequisites, migration notes, security boundaries, and known limitations.
3. On `master`, download the current `.mkp` and matching `.sha256` from the package directory. For an unmerged pull request, use only the MKP artifact produced by that pull request's successful repository validation workflow. Do not substitute an older same-name archive.
4. Verify the checksum before installation:

   ```bash
   sha256sum --check <package>-<version>.mkp.sha256
   ```

5. Install and enable the MKP through Checkmk Setup or as the site user with the supported `mkp` command for the target Checkmk release.
6. Configure the documented rule, credentials, agent deployment, or device-side prerequisite. Installing an MKP alone does not necessarily activate an integration.
7. Run service discovery on a test host and verify expected services and states before broad deployment.

Do not install an MKP with an unsupported compatibility range merely because it imports or can be added to a site. Registration success is not equivalent to correct runtime behavior.

## Compatibility and assurance

Packages are classified conceptually as:

- **Runtime-validated:** loaded and validated in the declared Checkmk releases, with package tests and MKP inspection.
- **Source-tested:** focused behavior tests exist, but representative vendor fixtures or live-system evidence may still be limited.
- **Legacy or unverified:** retained for existing users, with conservative compatibility claims and a requirement that future source changes add tests.

Every active package has structural metadata, documentation, and syntax tests. Focused behavior coverage still varies by integration and is reported by each code-derived package reference. The full-tree audit is enforced at every severity with no legacy-finding baseline. See [`MAINTENANCE.md`](MAINTENANCE.md) and [`docs/REPOSITORY_AUDIT.md`](docs/REPOSITORY_AUDIT.md).

## Security

Review [`SECURITY.md`](SECURITY.md) before reporting a vulnerability. Do not publish credentials, production hostnames, private IP inventories, proprietary SNMP walks, customer data, or exploit details in a public issue.

Repository controls include:

- immutable commit pins for third-party GitHub Actions;
- digest-pinned Checkmk validation images;
- deterministic MKP construction and checksum verification;
- clean-site validation on supported Checkmk versions;
- changed-code rejection for dynamic execution, shell invocation, secret flattening, disabled TLS verification, and global TLS-warning suppression;
- a full-tree security and documentation audit that requires zero findings at every defined severity;
- deterministic metadata, code-derived documentation, module-docstring, and repository syntax gates.

These controls reduce risk but do not replace deployment-specific review. Many plug-ins run with Checkmk site-user or agent privileges and may handle infrastructure credentials.

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`docs/DOCUMENTATION_STANDARD.md`](docs/DOCUMENTATION_STANDARD.md) before changing code or documentation. Every behavioral change must include focused tests, accurate compatibility metadata, operational documentation, and a security review proportionate to the privileges and data handled by the integration.

Useful repository checks include:

```bash
python3 tools/ci/pin_supply_chain.py --check
python3 tools/ci/sync_repository_facts.py
python3 tools/ci/sync_package_metadata.py
python3 tools/ci/generate_package_reference.py
python3 tools/ci/manage_module_docstrings.py
python3 tools/ci/check_python_syntax.py
python3 tools/ci/repository_guard.py --base <base-sha> --head <head-sha>
python3 tools/ci/full_repository_audit.py --fail-on low
python3 -m unittest discover -s tests -p 'test_ci_*.py' -v
```

Package tests must also collect successfully together with `pytest -q */tests`; CI then reruns each package directory independently for attributable failures.

## Support

Operational questions and reproducible defects belong in GitHub issues. Read [`SUPPORT.md`](SUPPORT.md) for the information required in a useful report and the distinction between support requests and security reports.

## License and provenance

The repository is distributed under the license text in [`LICENSE`](LICENSE). Individual files may retain additional authorship or provenance notices. Preserve those notices when modifying or redistributing code.

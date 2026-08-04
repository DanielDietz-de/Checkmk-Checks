# Checkmk Checks and Extensions

Community-maintained Checkmk extensions, special agents, agent plug-ins, notification integrations, Bakery plug-ins, rulesets, check plug-ins, manuals, and installable MKP packages.

The repository is maintained under the `DanielDietz-de` organization and contains code from several generations of Checkmk. Package metadata and the generated [`mkp_index.json`](mkp_index.json) are the authoritative package catalog. Historical copyright and license terms remain in [`LICENSE`](LICENSE).

## Repository status

The repository-wide release workflow currently discovers **95 active packages** from their canonical `*/src/info` manifests. It runs package tests, builds deterministic MKP archives, verifies checksums and package inventories, and validates supported packages in clean Checkmk 2.4 and 2.5 sites before publication.

A package being present does **not** automatically mean that every device-specific behavior has been validated against live hardware. Use the compatibility fields and documentation in each package directory, and review the assurance model in [`MAINTENANCE.md`](MAINTENANCE.md).

## Find a package

Use [`mkp_index.json`](mkp_index.json) to search by package name, title, description, version, required Checkmk version, and MKP path. Each active package lives in a top-level directory and normally contains:

```text
<package>/
├── README.md              Package-specific operation and migration guidance
├── <package>-<version>.mkp
├── <package>-<version>.mkp.sha256
├── src/                   Canonical source and package manifest
└── tests/                 Focused tests, when available
```

Generated MKP files are release artifacts. Source under `src/` is authoritative for review and maintenance.

## Installation

1. Select a package whose `version.min_required`, `version.packaged`, and `version.usable_until` metadata matches the target Checkmk release.
2. Read the package README completely, including prerequisites, migration notes, security boundaries, and known limitations.
3. Download the `.mkp` and matching `.sha256` file from the package directory.
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

The repository uses a ratchet model: changed package code must meet the current security and test baseline, while existing legacy findings remain explicitly inventoried instead of being silently treated as safe. See [`MAINTENANCE.md`](MAINTENANCE.md) and [`docs/REPOSITORY_AUDIT.md`](docs/REPOSITORY_AUDIT.md).

## Security

Review [`SECURITY.md`](SECURITY.md) before reporting a vulnerability. Do not publish credentials, production hostnames, private IP inventories, proprietary SNMP walks, customer data, or exploit details in a public issue.

Repository controls include:

- immutable commit pins for third-party GitHub Actions;
- digest-pinned Checkmk validation images;
- deterministic MKP construction and checksum verification;
- clean-site validation on supported Checkmk versions;
- changed-code rejection for dynamic execution, shell invocation, secret flattening, disabled TLS verification, and global TLS-warning suppression;
- a full-tree security and documentation audit that keeps reviewed legacy findings visible and rejects new high-risk findings.

These controls reduce risk but do not replace deployment-specific review. Many plug-ins run with Checkmk site-user or agent privileges and may handle infrastructure credentials.

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`docs/DOCUMENTATION_STANDARD.md`](docs/DOCUMENTATION_STANDARD.md) before changing code or documentation. Every behavioral change must include focused tests, accurate compatibility metadata, operational documentation, and a security review proportionate to the privileges and data handled by the integration.

Useful repository checks include:

```bash
python3 tools/ci/pin_supply_chain.py --check
python3 tools/ci/repository_guard.py --base <base-sha> --head <head-sha>
python3 tools/ci/full_repository_audit.py \
  --baseline .github/repository-audit-baseline.json \
  --fail-on high
python3 -m unittest discover -s tests -p 'test_ci_*.py' -v
```

Package-specific tests normally run with `pytest -q <package>/tests`.

## Support

Operational questions and reproducible defects belong in GitHub issues. Read [`SUPPORT.md`](SUPPORT.md) for the information required in a useful report and the distinction between support requests and security reports.

## License and provenance

The repository is distributed under the license text in [`LICENSE`](LICENSE). Individual files may retain additional authorship or provenance notices. Preserve those notices when modifying or redistributing code.

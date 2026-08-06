# Upstream provenance and migration record

## Source

The package was migrated from:

- repository: `Daniel-Dietz/S2D-Monitoring`;
- source branch: `main`;
- source commit: `c6aa39d8fa62c1a550c07308f99e75c94ba5a7c2`;
- source package name: `s2d_hci_monitoring`;
- source package version: `1.0.0`.

The source commit is the immutable baseline for provenance comparisons. Future changes are maintained in `DanielDietz-de/Checkmk-Checks/s2d_hci_monitoring` under the target repository’s code-first documentation and release process.

## Migrated functional content

The migration includes the complete S2D/HCI package declared by the source manifest:

- six Windows collectors;
- the virtualization spool wrapper and non-secret configuration;
- six Check API V2 modules;
- two Rulesets API V1 modules;
- Graphing API V1 definitions;
- the Checkmk manual;
- package manifest, focused tests, operational tools, and documentation;
- the original package-specific license.

The two source operational PowerShell tools for installing and validating the gMSA scheduled task were retained under `tools/windows/` and hardened for the monorepo package.

## Deliberately not imported as package content

The source repository also contained standalone-repository scaffolding, a generic example check, root-level CI workflows, generic development helpers, and repository-level contribution/security files. These were not copied into the package because the target monorepo already supplies authoritative equivalents and its package contract requires source under `<package>/src/`.

Importing duplicate root workflows or generic examples inside the package would create conflicting CI, package discovery, licensing, and documentation authority. This exclusion does not remove any file declared by the source `s2d_hci_monitoring` MKP manifest.

## Adaptations made during migration

- Mapped `local/share/check_mk/agents/` to `src/agents/`.
- Mapped `local/lib/python3/cmk_addons/plugins/` to `src/cmk_addons_plugins/`.
- Replaced the standalone manifest template with canonical `src/info` metadata used by Checkmk-Checks.
- Set the evidence-based compatibility range to Checkmk 2.5.0 through 2.5.99.
- Corrected the check manual’s license field to PolyForm Internal Use 1.0.0.
- Added module and contract docstrings required by the target documentation standard.
- Hardened storage-job numeric parsing so malformed values do not abort a section.
- Restricted the scheduled-task installer to gMSAs and the `ServiceAccount` logon type.
- Removed execution-policy bypasses from the spool execution path.
- Replaced cmdlet-based temporary-file mutation in the runtime wrapper with explicit .NET file operations and atomic replacement.
- Added manifest, parser, state, metric, malformed-input, and workload tests.
- Added package-specific architecture, installation, operations, security, validation, and removal documentation.

## License

The source repository changed from MIT to the PolyForm Internal Use License 1.0.0 before the migration baseline. The complete license is preserved in `s2d_hci_monitoring/LICENSE` and applies specifically to this package.

## Verification

To compare a future revision with the migration baseline:

1. inspect the immutable source commit;
2. compare every source-manifest path with the target `src/info` inventory;
3. account for the path mappings and adaptations above;
4. confirm the package-specific license remains present;
5. run package tests and the target repository’s affected-package validation workflow.

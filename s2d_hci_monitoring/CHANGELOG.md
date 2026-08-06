# Changelog

All notable package changes are documented here. The canonical package version remains defined in `src/info`.

## 1.0.0 — 2026-08-06

- Migrated the complete S2D/HCI package from `Daniel-Dietz/S2D-Monitoring` at commit `c6aa39d8fa62c1a550c07308f99e75c94ba5a7c2`.
- Adopted the Checkmk-Checks canonical package structure and repository validation process.
- Preserved all manifest-declared Windows collectors and Checkmk server-side components.
- Added focused manifest, parser, state, metric, malformed-input, and Hyper-V workload tests.
- Added complete architecture, installation, operations, gMSA, security, validation, upgrade, rollback, removal, and provenance documentation.
- Preserved the PolyForm Internal Use License 1.0.0 as the package-specific license.
- Hardened storage-job numeric parsing, gMSA task registration, execution-policy handling, path confinement, and atomic spool replacement.

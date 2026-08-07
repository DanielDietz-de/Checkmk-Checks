# Changelog

## 1.1.0 — 2026-08-07

- Reimplemented the source production-hardening intent directly in the monorepo.
- Added protocol version 1, per-run IDs, explicit collector-health services, fail-visible parser errors, and duplicate detection.
- Added deterministic one-node cluster collection and stable logical cluster piggyback identity.
- Made custom Hyper-V monitoring opt-in and moved VM telemetry to stable VM-GUID piggyback hosts.
- Removed the unbounded performance-history collector.
- Added runtime, record-count, output-size, and concurrency boundaries.
- Hardened gMSA spool mode with native exit checks, protocol validation, reparse/path confinement, scoped ACLs, local gMSA validation, non-elevated task execution, and atomic last-good preservation.
- Added privacy-minimizing defaults for paths, addresses, serials, IDs, and physical locations.
- Added operational-state policy rules and Agent Bakery deployment.
- Added API-contract, protocol, PowerShell safety, manifest, and documentation tests.
- Expanded architecture, protocol, installation, operations, security, release, validation, and production-acceptance documentation.

## 1.0.0 — 2026-08-06

- Migrated the baseline package from upstream commit `c6aa39d8fa62c1a550c07308f99e75c94ba5a7c2`.

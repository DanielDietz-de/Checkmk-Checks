# Security model

## Privilege and mutation boundary

Collectors are read-only. They query Microsoft management cmdlets and emit Checkmk agent text only. No collector writes cluster, storage, Hyper-V, network, registry, firewall, or service configuration.

Use the least privileged account that can read required cmdlets. Do not grant local administrator or domain administrator solely for monitoring.

## Data minimization

The default configuration excludes:

- cluster/network addresses;
- filesystem, VM configuration, VHD, and parent paths;
- physical disk serial numbers and unique IDs;
- physical hardware locations.

Stable service identity does not require enabling these fields. Sensitive raw identifiers are hashed where necessary. VHD query failures also use a path-free error message while path collection is disabled; enabling paths permits a bounded vendor error message for troubleshooting. A non-sensitive `has_parent` Boolean preserves differencing-disk alerting without exposing the parent VHD path. Enable optional fields only for a documented operational need and restrict Checkmk access accordingly.

## Bounds and denial-of-service resistance

Collector runtime, records, and output bytes are bounded. Values loaded from JSON are range checked. Boolean configuration accepts only explicit booleans/true/false text. Agent Bakery also sets a Windows plug-in timeout.

## gMSA spool workflow

The scheduled-task installer:

- requires `DOMAIN\account$` syntax;
- requires `Test-ADServiceAccount` and a locally usable gMSA;
- accepts no password;
- confines collector, wrapper, configuration, and spool paths below the Checkmk agent root;
- grants read/execute only to binaries/config and modify only to the spool directory;
- verifies the resulting ACL contains the gMSA identity;
- registers `RunLevel Limited`, not elevated;
- uses `ServiceAccount` logon, `MultipleInstances IgnoreNew`, and `ExecutionTimeLimit`;
- does not use `ExecutionPolicy Bypass`.

The spool wrapper rejects path escapes and reparse points, checks the native PowerShell exit code, validates protocol framing and a single successful run, and atomically replaces the live spool only after all validation passes. Failure preserves the previous valid output.

## Supply chain

The repository release pipeline is responsible for deterministic MKP creation, SHA-256 checksums, SPDX SBOMs, and provenance. Package source does not embed credentials or download executable code at runtime.

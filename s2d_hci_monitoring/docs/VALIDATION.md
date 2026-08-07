# Validation

## Repository gates

The package must pass the repository security/supply-chain guard and MKP validation workflows. Those gates cover source normalization, documentation synchronization, Python syntax, package tests, deterministic MKP creation, checksums/evidence, and clean Checkmk plug-in registration/runtime validation.

Package tests specifically enforce:

- protocol version and run ID handling;
- malformed/non-object/missing-identity visibility;
- duplicate identity visibility;
- collector-health failure semantics;
- finite numeric parsing;
- volume/VM stable identity contracts;
- removed performance-history collector;
- no `ExecutionPolicy Bypass` or elevated gMSA task;
- fail-safe spool exit-code/protocol validation;
- bounded configuration and data-minimization defaults;
- Bakery deployment/timeout/config contracts;
- function/class documentation coverage.

## Windows PowerShell validation

The dedicated **S2D HCI Windows validation** workflow is a required package gate. It runs on `windows-2025`, parses every package `.ps1` and `.psm1` file with Windows PowerShell 5.1, and runs PSScriptAnalyzer 1.25.0 with error-severity findings treated as failures. This supplements the package's static safety-contract tests; it is not optional for merge acceptance.

## Environmental acceptance

Repository CI cannot prove Microsoft cmdlet behavior, permissions, or performance for a specific cluster. Before production promotion complete `PRODUCTION_ACCEPTANCE.md` against representative infrastructure and preserve the evidence with the release/change record.

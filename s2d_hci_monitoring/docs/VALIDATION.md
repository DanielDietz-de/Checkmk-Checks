# Validation

## Repository gates

The package is expected to pass the repository security/supply-chain guard and MKP validation workflows. Those gates cover source normalization, documentation synchronization, Python syntax, package tests, deterministic MKP creation, checksums/evidence, and clean Checkmk plug-in registration/runtime validation.

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

## Windows static validation

Where Windows runners are available, validate Windows PowerShell 5.1 parsing and PSScriptAnalyzer against the PowerShell source. Static contract tests remain in the package so critical safety properties are still reviewed when a Windows runner is temporarily unavailable.

## Environmental acceptance

Repository CI cannot prove Microsoft cmdlet behavior, permissions, or performance for a specific cluster. Before production promotion complete `PRODUCTION_ACCEPTANCE.md` against representative infrastructure and preserve the evidence with the release/change record.

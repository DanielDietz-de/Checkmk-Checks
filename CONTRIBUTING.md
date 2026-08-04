# Contributing

Contributions are welcome when they are scoped, testable, secure, and maintainable across the declared Checkmk compatibility range.

## Before changing code

1. Identify the canonical package directory and inspect its executable source, registrations, tests, and `src/info` manifest before relying on its README.
2. Confirm whether the package is runtime-validated, source-tested, or legacy/unverified.
3. Define the behavioral and security boundary before implementation.
4. Remove production-specific names, addresses, credentials, IDs, logs, walks, and customer data from examples and fixtures.
5. Prefer a focused package change over an unrelated repository-wide rewrite.

## Package structure

Active packages are discovered from a top-level `*/src/info` manifest. Use the established Checkmk add-on layout for the target version. Keep the package directory, manifest name, namespace, rule names, manuals, tests, and generated artifact name consistent.

Do not hand-edit generated `.mkp` archives or checksums. The repository-wide release workflow builds and publishes deterministic artifacts after tests and clean-site validation pass.

## Code requirements

- Use supported public Checkmk APIs for the declared compatibility range.
- Add type hints where they materially improve contracts and reviewability.
- Keep functions focused and make trust-boundary validation explicit.
- Use module, class, and public-function docstrings for non-obvious behavior, inputs, outputs, exceptions, state, and side effects.
- Use comments to explain **why**, protocol quirks, compatibility constraints, or security invariants. Do not narrate obvious syntax or leave stale commented-out code.
- Preserve existing service names, rule identifiers, value-store keys, metrics, and item formats unless a documented migration is intentional.
- Treat agent and site-user code as privileged code.

The documentation standard is defined in [`docs/DOCUMENTATION_STANDARD.md`](docs/DOCUMENTATION_STANDARD.md).

## Security requirements

New or changed code must not introduce:

- dynamic code execution through `eval` or `exec`;
- shell invocation or unvalidated command construction;
- plaintext secret flattening;
- disabled TLS verification or global warning suppression;
- credential-bearing URLs or logs;
- unbounded remote responses, parsers, caches, loops, or output;
- unsafe deserialization;
- predictable or non-atomic sensitive state files;
- broad exception handling that converts failed collection into an OK result.

A `# security-reviewed:` exception is allowed only when the risk cannot be removed, the operational boundary is documented, and focused tests prove the intended constraint.

## Tests

Every changed package source file requires at least one focused `tests/test_*.py` file in that package. Tests should cover:

- normal parsing, discovery, and check behavior;
- malformed, missing, duplicate, oversized, and adversarial input;
- authentication and TLS boundaries;
- output escaping and injection resistance;
- timeout and failure propagation;
- migration compatibility where saved rules or service identities are affected;
- metadata consistency when both `src/info` and `src/info.json` exist.

Use representative sanitized fixtures where behavior depends on a vendor payload or SNMP walk. A source import alone is not runtime evidence.

## Documentation requirements

Update the package README whenever installation, configuration, permissions, credentials, service discovery, output, compatibility, failure behavior, or removal changes. Include exact host context for commands and distinguish Checkmk-server, monitored-host, and network-device steps.

Code and canonical metadata drive documentation. Fix or change implementation and tests first, update human-written manuals and rationale second, then regenerate the package operational reference. Do not preserve documentation that conflicts with executable behavior, and do not claim compatibility beyond tested evidence.

## Local validation

Run the relevant checks before opening a pull request:

```bash
python3 tools/ci/pin_supply_chain.py --check
python3 tools/ci/sync_repository_facts.py
python3 tools/ci/sync_package_metadata.py
python3 tools/ci/generate_package_reference.py
python3 tools/ci/manage_module_docstrings.py
python3 tools/ci/check_python_syntax.py
python3 -m unittest discover -s tests -p 'test_ci_*.py' -v
pytest -q <package>/tests
```

For a branch comparison, also run:

```bash
python3 tools/ci/repository_guard.py --base <base-sha> --head <head-sha>
python3 tools/ci/full_repository_audit.py --fail-on low
```

The authoritative workflow additionally builds all active MKPs and validates supported packages in clean Checkmk sites.

## Pull requests

A pull request should explain:

- root cause and user impact;
- exact scope and changed behavior;
- security and compatibility implications;
- migration or rollback steps;
- validation evidence;
- remaining live-system validation, if any.

Keep review threads current and resolve findings only after the corresponding change and regression test are present.

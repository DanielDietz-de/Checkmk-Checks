# Documentation standard

Documentation is part of the package contract. A change is incomplete when users cannot determine what the integration does, where it runs, what privileges it needs, how to configure it, how it fails, and how to remove it.

## Root documentation

The repository must maintain:

- `README.md`: scope, installation, package discovery, compatibility, security, contribution, and support entry points;
- `SECURITY.md`: private reporting and secure-development expectations;
- `CONTRIBUTING.md`: implementation, testing, metadata, and review requirements;
- `MAINTENANCE.md`: assurance model, release controls, and legacy policy;
- `SUPPORT.md`: operational support scope and required diagnostics;
- `LICENSE`: applicable license and provenance.

## Package README

Every active package requires a package-specific `README.md`. Cover the following where applicable:

1. **Purpose and scope** — monitored system, protocol, services, metrics, notifications, and explicit non-goals.
2. **Compatibility** — minimum, packaged, and maximum validated Checkmk versions plus vendor or operating-system prerequisites.
3. **Architecture** — where each component runs, data flow, privilege boundaries, external dependencies, and generated files.
4. **Installation** — exact MKP verification and installation steps.
5. **Configuration** — rule location, every relevant field, safe defaults, credentials, certificate trust, and examples without production values.
6. **Discovery and validation** — direct collector commands, expected sections/services, discovery workflow, and acceptance checks.
7. **Security** — privileges, secret handling, network destinations, TLS, file permissions, output redaction, and known trust assumptions.
8. **Failure behavior** — UNKNOWN/CRIT behavior, partial collection policy, caching, stale data, retries, and timeouts.
9. **Troubleshooting** — likely failures, diagnostic commands, logs, and sanitization guidance.
10. **Upgrade and migration** — saved-rule compatibility, renamed services/metrics, credential changes, and rollback.
11. **Removal** — MKP removal plus host-side files, rules, schedules, accounts, and permissions to remove.
12. **Limitations and validation evidence** — tests performed and remaining live-system validation.

State explicitly when a section is not applicable rather than silently omitting an operational boundary.

## Check manuals and rule help

Check manuals must accurately describe itemization, state logic, metrics, parameters, discovery behavior, and prerequisites. Rule help must explain units, ranges, defaults, security implications, and migration behavior.

Do not use manuals or rule help as the only installation documentation.

## Inline documentation

### Module docstrings

Non-trivial Python modules should state:

- purpose and execution context;
- trusted and untrusted inputs;
- emitted output or registered Checkmk objects;
- important state, side effects, and security constraints;
- compatibility-specific behavior that is not obvious from imports.

### Function and class docstrings

Document public functions, classes, parsers, transport clients, state stores, and normalization helpers when the contract is not self-evident. Describe accepted structures, return values, exceptions, bounds, and mutation.

### Comments

Comments should explain rationale and invariants, for example:

- why a vendor value maps to a state;
- why a timeout or size limit exists;
- why redirects or proxies are disabled;
- why a Checkmk compatibility fallback is required;
- why state must be written atomically;
- why an identifier or service name must remain stable.

Avoid comments that repeat syntax, stale TODOs without an issue, commented-out code, credentials, customer names, or production topology.

## Examples and fixtures

Examples must be generic and safe to publish. Fixtures must be minimized and sanitized while preserving protocol behavior. Never include secrets, private keys, customer data, proprietary configuration content, or production host inventories.

## Review checklist

A reviewer should be able to answer:

- Can a new operator install, configure, validate, troubleshoot, upgrade, and remove the package from the documentation alone?
- Do the docs match actual paths, fields, defaults, service names, and state behavior?
- Are privilege and credential boundaries explicit?
- Are compatibility claims supported by tests or live evidence?
- Do comments and docstrings clarify non-obvious behavior without becoming stale duplication?

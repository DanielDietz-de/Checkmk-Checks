# Icinga Connector

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0p1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p18-blue)
<!-- compatibility-badges:end -->

Special agent that connects to an Icinga 2 instance over the REST API and mirrors every service check as a Checkmk `local` check via piggyback. States, outputs, and performance data are preserved. When a service's plain-text output contains an HTML `<table>`, the connector splits the table rows into multiple Checkmk sub-services.

## How it works

1. The special agent `agent_icinga` calls `GET https://<host>/v1/objects/services` with HTTP Basic authentication.
2. For every result it emits a piggyback block for the Icinga `host_name` containing a `<<<local>>>` section.
3. For each service it prints a local check line `<state> "<service_name>" <perfdata> <output>`.
4. Performance data from Icinga (`label=value;warn;crit;min;max`) is converted to the Checkmk local check perfdata format.
5. Multi-row table outputs are parsed with `ElementTree`; a column called `status` / `state` determines the per-row Checkmk state. The status text is mapped to a full state — `ok`/`up` → OK, `warning`/`warn` → WARN, `critical`/`crit`/`down` → CRIT, `unknown` (or any unrecognised text) → UNKNOWN, empty → OK.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/cmk_addons_plugins/icinga/libexec/agent_icinga` | Special agent script (runs on the Checkmk server). |
| `src/cmk_addons_plugins/icinga/rulesets/agent.py` | WATO ruleset `SpecialAgent` definition. |
| `src/cmk_addons_plugins/icinga/server_side_calls/agent.py` | Server-side call that builds the CLI for the special agent. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create a Checkmk host that will represent the Icinga connection (the hostname is only used to attach the rule to).
3. Configure the special agent rule (see below). The connector produces piggyback data, so the actual Icinga hosts must also exist in Checkmk to receive their services.
4. Run service discovery on the piggyback hosts.

## Configuration

WATO rule: **Setup -> Agents -> Other integrations -> Icinga Connector**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `host_name` | String | Hostname (and port) of the Icinga API endpoint. |
| `username` | String | API user. |
| `password` | Password | API password (stored as a `Secret`, passed via `--password`). |
| `ssl_verify` | BooleanChoice | Verify SSL certificates. When disabled, the agent passes `--no-verify` and suppresses urllib3 `InsecureRequestWarning`. |

CLI invocation:

```text
agent_icinga --hostname <host> --username <user> --password <pw> [--no-verify]
```

## Services & metrics

- **Services:** one Checkmk local service per Icinga service, named exactly like the Icinga service.
- **State:** taken verbatim from Icinga (`attrs['state']`).
- **Metrics:** all Icinga performance data is forwarded.
- **Sub-services:** if an output contains a `<table>`, the rows are split out. With grouping (default) the rows are folded into the parent service, whose state is the **worst** of its own state and all row states (severity order OK < WARN < UNKNOWN < CRIT, so CRIT outranks UNKNOWN). With `--no-group` each row becomes its own service `<service> <row-label>`.
- **Row state:** derived from the `status` / `state` column via a full mapping — `ok`/`up` → OK, `warning`/`warn` → WARN, `critical`/`crit`/`down` → CRIT, `unknown` or any unrecognised text → UNKNOWN, empty → OK.

## Known limitations

- Only the `/v1/objects/services` endpoint is consumed; host-only objects from Icinga are not mirrored separately, they are implied through the piggyback host header.
- Table parsing is best-effort and falls back to a single-line output on any XML parse error.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `icinga` version `1.4.1`; minimum Checkmk version `2.4.0p1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `icinga/src/info`; it declares 3 packaged files.
- Repository MKP artifacts present: `icinga-1.0.0.mkp`, `icinga-1.0.1.mkp`, `icinga-1.1.2.mkp`, `icinga-1.2.0.mkp`, `icinga-1.3.0.mkp`, `icinga-1.4.0.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Server-side calls:** `src/icinga/server_side_calls/agent.py`.
- **Rulesets:** `src/icinga/rulesets/agent.py`.
- **Executables:** `src/icinga/libexec/agent_icinga`.
- Registered special-agent names: `icinga`.

### Validation

- Package-specific tests: `tests/test_icinga_secret_command_arguments.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- Server-side calls preserve Checkmk password-store references and the executable resolves them at runtime; direct plaintext options, where present, are limited to isolated command-line diagnostics.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.
- An explicit TLS-verification opt-out is present. Verification remains the secure default; use the opt-out only as a documented temporary exception and prefer a private CA bundle.

### Troubleshooting

- Emitted Checkmk sections detected in source: `local`.
- For special agents, inspect the generated command without exposing secrets, run it as the site user, and verify that every emitted section has a matching parser/check registration.
<!-- code-derived-reference:end -->

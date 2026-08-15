# Aruba Central Access Point Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.5.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

Checkmk 2.5 package for monitoring Aruba Central access points through the Central API CLI (`cencli`). A PowerShell agent plug-in runs `cencli show aps -v --json` on a Windows collector, evaluates stdout and stderr independently, and emits a collector service plus piggyback data for every AP.

## Scope

The package provides:

- collector health, AP counts, client totals, API-rate-limit headroom, runtime, last-success age, and observed output streams;
- one AP service per generated piggyback host;
- one itemized service per radio;
- configurable thresholds and graphing;
- asynchronous Windows-agent execution for the approximately 30-second CLI query;
- a separate, dry-run-first Checkmk REST synchronizer for `<Group>/Accesspoint/<Host>`.

The monitoring collector never mutates Checkmk configuration. Host and folder creation is a separate explicit operation.

## Installation

Build and install the MKP from `src/` using the repository release workflow. The package targets Checkmk 2.5 and requires a Windows collector with PowerShell 5.1 or newer, the Checkmk Windows agent, and an authenticated `cencli` installation.

Deploy the bundled files to their Checkmk paths. On the Windows collector, copy the PowerShell plug-in and JSON configuration into the Checkmk agent directories and merge the supplied asynchronous execution fragment into `check_mk.user.yml`.

```yaml
plugins:
  enabled: yes
  execution:
    - pattern: $CUSTOM_PLUGINS_PATH$\aruba_central_aps.ps1
      async: yes
      timeout: 90
      cache_age: 300
      retry_count: 2
```

Keep the agent timeout above the observed worst-case `cencli` duration.

## Configuration

The collector executes:

```powershell
cencli show aps -v --json
```

The example JSON configuration controls the executable path, optional native CLI prefix/suffix arguments, process timeout, bounded last-known-good cache path, maximum stale age, and piggyback emission.

### Stream handling

`cencli` output is deliberately not tied to one stream:

1. JSON is searched in stdout.
2. If absent, JSON is searched in stderr.
3. A combined-stream search is used only as a compatibility fallback for JSON.
4. Counts and rate-limit diagnostics are searched in stdout and stderr independently; `both` is recorded when the same diagnostic appears on both streams.
5. If no Counts line exists, AP and client counts are derived from normalized JSON and `counts_stream` is set to `derived`.
6. The summary service reports `json_stream`, `counts_stream`, and `rate_limit_stream`. Values are `stdout`, `stderr`, `both`, `combined`, `derived`, or `none` as applicable.

Raw CLI output is not included in service data. Error details are bounded, normalized, and redacted for common secret assignments.

## Monitored fields

The AP service processes status, client count, MAC, serial, uptime, CPU utilization, total/free memory, firmware version, SSID count, model, IP, group, site, and sleep status. Each radio service processes radio name/type, band, channel, status, transmit power, utilization, spatial stream, and radio MAC.

The collector service processes lines such as:

```text
Counts: ap: 393 (386:7), clients: 242
API Rate Limit: 11964 of 11970 remaining.
```

## Host naming and folders

The piggyback host name follows the requested rule:

```text
name differs from MAC -> sanitized name
name equals MAC       -> AP_<serial>
```

If no serial exists, the final fallback is `AP_<compact-mac>`.

The separate synchronizer validates every AP against the Group→Site allow-list and creates this hierarchy:

```text
/<Group>/Accesspoint/<Host>
```

The bundled policy contains:

| Group | Accepted Site |
| --- | --- |
| B200 | `B200` |
| Bad Godesberg | `Bad Godesberg` |
| Campus Bornheim | `Campus Bornheim - ABS5` or `Campus Bornheim - MAS3` |

Unknown groups or sites fail the complete run before any REST request. The default execution is a dry run. `--apply` is required to create objects. Existing hosts or folders are not moved, overwritten, or deleted.

## Host synchronization example

```bash
sync_aruba_central_hosts \
  --source-host <collector-host> \
  --mapping /path/to/group_site_map.json
```

After reviewing the plan:

```bash
sync_aruba_central_hosts \
  --source-host <collector-host> \
  --mapping /path/to/group_site_map.json \
  --apply \
  --api-url https://checkmk.example/site/check_mk/api/v1 \
  --username automation-aruba-central \
  --secret-file /omd/sites/site/var/check_mk/aruba-central.secret \
  --activate-site site
```

Remote API endpoints require HTTPS with certificate verification. A private CA bundle can be supplied. Loopback HTTP is accepted only for a local site API. The secret file must be a regular file and mode `0600` on Unix.

## Validation

From this package directory:

```bash
python3 -m compileall -q src tests
pytest -q
```

The focused suite covers JSON parsing, discovery and check states, exact folder planning, Group→Site fail-closed behavior, REST safety defaults, host naming/source contracts, asynchronous configuration, manifest completeness, and last-known-good behavior. PowerShell execution itself requires a Windows acceptance host; Linux CI pins the security- and behavior-critical source contract statically.

Recommended deployment checks:

```bash
cmk -d <collector-host>
cmk --detect-plugins=aruba_central_summary -v <collector-host>
cmk -IIv <collector-host>
cmk -R
```

Confirm that the collector service reports the correct three stream fields, every AP is represented by one piggyback host, and each AP host receives one AP service plus one service per radio.

## Security

- Aruba credentials stay in the native `cencli` authentication profile under the Checkmk agent service identity.
- The collector starts the executable without shell execution and uses a bounded timeout.
- Failed collections never replace the last-known-good cache and never report a healthy collector state.
- Checkmk automation credentials are read from a protected file, never from documentation or agent output.
- REST environment-proxy inheritance and authenticated redirects are disabled.
- Remote REST endpoints require verified HTTPS; loopback HTTP is limited to local site access.
- Synchronization is non-mutating by default and implements no delete or move operation.

See [docs/security.md](docs/security.md) for the trust model and [docs/operations.md](docs/operations.md) for deployment and troubleshooting.

## Troubleshooting

- Run `cencli show aps -v --json` under the same identity as the Checkmk agent service.
- Capture stdout and stderr separately; do not assume the JSON or diagnostics stream.
- Inspect collector details for `json_stream`, `counts_stream`, `rate_limit_stream`, runtime, stale state, and last-success age.
- Inspect `cmk -d <collector-host>` for both the collector section and AP piggyback markers.
- Run synchronization without `--apply` and resolve every Group/Site validation error first.
- Sanitize AP names, serials, MACs, IPs, tenant information, URLs, and credentials before sharing diagnostics.

## Upgrade, rollback, and removal

Review the changelog before upgrades because service, metric, and schema names are persistence boundaries. To roll back, disable the asynchronous plug-in entry, restore the previous package, rediscover affected services, and retain the last-known-good file only for diagnostics. Removal requires disabling the collector, removing package files and rules, and manually reviewing generated hosts/folders before deleting them.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `aruba_central_monitoring` version `1.3.0`; minimum Checkmk version `2.5.0`; maximum asserted version: 2.5.99.
- Canonical manifest: `aruba_central_monitoring/src/info`; it declares 11 packaged files.
- No committed MKP artifact is present; build and validate the package from `src/` before installation.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/aruba_central/agent_based/aruba_central_aps.py`.
- **Rulesets:** `src/aruba_central/rulesets/aruba_central_aps.py`.
- **Executables:** `src/aruba_central/libexec/sync_aruba_central_hosts`.
- **Graphing:** `src/aruba_central/graphing/aruba_central_aps.py`.
- **Check manuals:** `src/aruba_central/checkman/aruba_central_ap`, `src/aruba_central/checkman/aruba_central_radio`, `src/aruba_central/checkman/aruba_central_summary`.
- **Other packaged source:** `src/agents/windows/cfg_examples/aruba_central_aps.json`, `src/agents/windows/cfg_examples/check_mk.user.aruba_central_aps.yml`, `src/agents/windows/plugins/aruba_central_aps.ps1`, `src/aruba_central/deployment/group_site_map.example.json`.
- Registered check plug-in names: `aruba_central_ap`, `aruba_central_radio`, `aruba_central_summary`.

### Validation

- Package-specific tests: `tests/test_agent_based.py`, `tests/test_host_sync.py`, `tests/test_manifest.py`, `tests/test_windows_agent_contract.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.

### Troubleshooting

- Emitted Checkmk sections detected in source: `aruba_central_aps`.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->

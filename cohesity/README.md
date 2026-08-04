# Cohesity checks

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p4-blue)
<!-- compatibility-badges:end -->

Special agent based monitoring for a Cohesity cluster. It queries the Iris REST API on the cluster VIP and produces services for cluster-wide alerts, per-node service health, storage and metadata usage, and counts of unprotected objects.

## How it works

The special agent `agent_cohesity` authenticates against `https://<vip>/irisservices/api/v1/public/accessTokens` and then calls:

- `/nexus/cluster/status` -> `<<<cohesity_node_status>>>` — one line per node reporting `ok` and `failed` service names.
- `/public/stats/storage` -> `<<<cohesity_storage_usage>>>` — `localUsageBytes`, `totalCapacityBytes`, etc.
- `/public/cluster` -> `<<<cohesity_metadata_usage>>>` — numeric fields including `usedMetadataSpacePct` and `availableMetadataSpace`.
- `/public/stats/alerts?startTimeUsecs=...&endTimeUsecs=...` (last 24h) -> `<<<cohesity_alerts>>>` — counts per severity.
- `/public/stats/protectionSummary` -> `<<<cohesity_unprotected>>>` — `numObjectsUnprotected`, `protectedSizeBytes`, etc.

Check plugins in `agent_based/` parse each section and create one service per result (nodes are keyed by hostname).

## Package contents

| Path | Purpose |
| --- | --- |
| `src/cohesity/libexec/agent_cohesity` | Special agent (REST client). |
| `src/cohesity/agent_based/cohesity_alerts.py` | `Alert Status` service from `/public/stats/alerts`. |
| `src/cohesity/agent_based/cohesity_node_status.py` | `Node Status <host>` per cluster node. |
| `src/cohesity/agent_based/cohesity_storage.py` | `Storage Status` with absolute and percent levels. |
| `src/cohesity/agent_based/cohesity_metadata.py` | `Metadata Status` with percent levels. |
| `src/cohesity/agent_based/cohesity_unprotected.py` | `Unproteced Status` (sic) for unprotected object count. |
| `src/cohesity/rulesets/cohesity_agent.py` | Special agent rule (user, password, domain, verify cert). |
| `src/cohesity/rulesets/cohesity_storage.py` | Check parameters for storage usage (absolute + percent). |
| `src/cohesity/rulesets/cohesity_metadata.py` | Check parameters for metadata usage (percent). |
| `src/cohesity/rulesets/cohesity_node_status.py` | Ignore-list for services in node status. |
| `src/cohesity/server_side_calls/cohesity_agent.py` | Command line generation for the special agent. |
| `src/cohesity/graphing/metrics.py` | Metric definitions. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create a Checkmk host for the cluster VIP.
3. Configure the special agent rule and run service discovery.

## Configuration

Rule: **Setup -> Agents -> Other integrations -> Cohesity via WebAPI**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `user` | String | API username. |
| `password` | Password | Password for the user. |
| `domain` | String | Auth domain, default `LOCAL`. |
| `verify_cert` | BooleanChoice | Verify the cluster TLS certificate. |

Additional check parameter rules:

- **Cohesity storage** — absolute and percentage WARN/CRIT on used storage.
- **Cohesity metadata** — percentage WARN/CRIT on metadata usage.
- **Cohesity node status ignored services** — list of service names to exclude from the `ok` / `failed` summary.

## Services & metrics

- **Services:** `Alert Status`, `Node Status <host>`, `Storage Status`, `Metadata Status`, `Unproteced Status`.
- **Metrics:** `used_storage`, `percent_used`, `used_metadata_space_pct`, `avail_metadata_space`, `unprotected_objects`.

## Known limitations

- The unprotected service is spelled `Unproteced Status` in the source and kept that way for compatibility.
- Alerts are fetched for a fixed 24 hour window.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `cohesity` version `1.5.2`; minimum Checkmk version `2.4.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `cohesity/src/info`; it declares 12 packaged files.
- Repository MKP artifacts present: `cohesity-1.0.mkp`, `cohesity-1.1.mkp`, `cohesity-1.2.mkp`, `cohesity-1.3.1.mkp`, `cohesity-1.3.2.mkp`, `cohesity-1.3.3.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/cohesity/agent_based/cohesity_alerts.py`, `src/cohesity/agent_based/cohesity_metadata.py`, `src/cohesity/agent_based/cohesity_node_status.py`, `src/cohesity/agent_based/cohesity_storage.py`, `src/cohesity/agent_based/cohesity_unprotected.py`.
- **Server-side calls:** `src/cohesity/server_side_calls/cohesity_agent.py`.
- **Rulesets:** `src/cohesity/rulesets/cohesity_agent.py`, `src/cohesity/rulesets/cohesity_metadata.py`, `src/cohesity/rulesets/cohesity_node_status.py`, `src/cohesity/rulesets/cohesity_storage.py`.
- **Executables:** `src/cohesity/libexec/agent_cohesity`.
- **Graphing:** `src/cohesity/graphing/metrics.py`.
- Registered special-agent names: `cohesity`.
- Registered check plug-in names: `cohesity_alerts`, `cohesity_metadata_usage`, `cohesity_node_status`, `cohesity_storage_usage`, `cohesity_unprotected`.

### Validation

- Package-specific tests: `tests/test_transport_security.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- Server-side calls preserve Checkmk password-store references and the executable resolves them at runtime; direct plaintext options, where present, are limited to isolated command-line diagnostics.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.

### Troubleshooting

- Emitted Checkmk sections detected in source: `cohesity_alerts`, `cohesity_metadata_usage`, `cohesity_node_status`, `cohesity_storage_usage`, `cohesity_unprotected`.
- For special agents, inspect the generated command without exposing secrets, run it as the site user, and verify that every emitted section has a matching parser/check registration.
<!-- code-derived-reference:end -->

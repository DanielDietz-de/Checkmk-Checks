# SAP Alm Cloud Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0p8-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p13-blue)
<!-- compatibility-badges:end -->

Special agent that pulls metrics from the SAP Cloud ALM (Application Lifecycle Management) Analytics OData API and turns each returned metric into a Checkmk service. Users configure an OData `$filter` expression to select which metrics the host should monitor.

## How it works

1. The special agent requests an OAuth2 client-credentials token from
   `https://<instance>.authentication.eu10.hana.ondemand.com/oauth/token`.
2. It then queries
   `https://<instance>.eu10.alm.cloud.sap/api/calm-analytics/v1/odata/v4/analytics/Metrics?$filter=<filter>`
   with a `Bearer` token.
3. For every metric in the response it emits a block under the agent section:

   ```text
   <<<sap_cloud_alm_metrics:sep(0)>>>
   [[[<metricName>]]]
   {'valueAvg': ..., 'warningStratus': ..., 'criticalStatus': ...}
   ```

4. The check plugin `sap_cloud_alm_metrics` discovers one service `Metric <metricName>` per block. It yields a `Metric(valueAvg)`, raises WARN when `warningStratus != 0` and CRIT when `criticalStatus != 0`, and otherwise reports OK with the raw field values.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/sap_cloud_alm/libexec/agent_sap_cloud_alm` | Special agent that talks to SAP Cloud ALM. |
| `src/sap_cloud_alm/server_side_calls/agent_sap_alm.py` | Server-side call wiring (`instance`, `client_id`, `client_secret`, `filter`, optional `proxy`). |
| `src/sap_cloud_alm/rulesets/ruleset.py` | WATO special agent rule. |
| `src/sap_cloud_alm/agent_based/metrics.py` | Section parser and check plugin. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create an OAuth2 client (ID + secret) in your SAP Cloud ALM tenant with read access to the Analytics API.
3. Add a Checkmk host for the tenant and configure the *SAP Cloud Alm* special agent rule.
4. Run service discovery.

## Configuration

Rule: **Setup -> Agents -> Other integrations -> SAP Cloud Alm**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `instance` | String | Instance subdomain, taken from the tenant URL. |
| `client_id` | String | OAuth2 client ID. |
| `client_secret` | Password | OAuth2 client secret. |
| `metric_filter` | String | OData `$filter` (URL-encoded), e.g. `serviceId%20eq%20'53d0eade-85dc-4863-bc20-528954f52a23'`. |
| `proxy` | String | Optional HTTPS proxy. |

## Services & metrics

- **Service:** `Metric <metricName>` — one per metric returned by the filter.
- **State:** CRIT if `criticalStatus != 0`, WARN if `warningStratus != 0`, otherwise OK.
- **Metric:** `valueAvg` (raw numeric value as returned by SAP).

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `sap_cloud_alm` version `1.0.1`; minimum Checkmk version `2.4.0p8`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `sap_cloud_alm/src/info`; it declares 4 packaged files.
- Repository MKP artifacts present: `sap_alm_cloud-1.0.0-dev1.mkp`, `sap_cloud_alm-1.0.0-dev2.mkp`, `sap_cloud_alm-1.0.0-dev3.mkp`, `sap_cloud_alm-1.0.0-dev4.mkp`, `sap_cloud_alm-1.0.0.mkp`, `sap_cloud_alm-1.0.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/sap_cloud_alm/agent_based/metrics.py`.
- **Server-side calls:** `src/sap_cloud_alm/server_side_calls/agent_sap_alm.py`.
- **Rulesets:** `src/sap_cloud_alm/rulesets/ruleset.py`.
- **Executables:** `src/sap_cloud_alm/libexec/agent_sap_cloud_alm`.
- Registered special-agent names: `sap_cloud_alm`.
- Registered check plug-in names: `sap_cloud_alm_metrics`.

### Validation

- Package-specific tests: `tests/test_sap_cloud_alm_secret_command_arguments.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- Server-side calls preserve Checkmk password-store references and the executable resolves them at runtime; direct plaintext options, where present, are limited to isolated command-line diagnostics.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.

### Troubleshooting

- Emitted Checkmk sections detected in source: `sap_cloud_alm_metrics`.
- For special agents, inspect the generated command without exposing secrets, run it as the site user, and verify that every emitted section has a matching parser/check registration.
<!-- code-derived-reference:end -->

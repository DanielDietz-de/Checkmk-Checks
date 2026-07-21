# Count the Value of Service Perfdata Metrics

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0p1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.3.0p25-blue)
<!-- compatibility-badges:end -->

Special agent that sums a named performance-data metric across Checkmk services matched by a Livestatus-style filter and exposes the total as its own Checkmk service.

## Security model

The special agent reads the executing site's local `automation` secret. The configured Checkmk URL must therefore identify the same `OMD_SITE` through `localhost`, `127.0.0.0/8`, or `::1`. Remote hosts, another local site path, URLs containing credentials, queries, or fragments, and unsupported schemes are rejected before the secret is read.

Proxy-environment handling is disabled for the local API session so the Authorization header cannot be redirected through a system proxy.

Remote aggregation is intentionally not supported with the local automation credential. A remote implementation must use an explicitly configured credential scoped to that remote site.

## How it works

1. Validate the configured site URL against the current `OMD_SITE` and require a loopback target.
2. Read the local automation secret.
3. For each configured entry, query the local Checkmk REST API with the configured service filter.
4. Sum the selected performance-data metric.
5. Emit one line per entry under `<<<service_metric_counter:sep(58)>>>`.
6. Emit an UNKNOWN local service if configuration or API access fails.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/service_metric_counter/libexec/agent_service_metric_counter` | Local-only REST aggregation special agent. |
| `src/service_metric_counter/server_side_calls/service_counter.py` | Server-side command generation. |
| `src/service_metric_counter/rulesets/ruleset.py` | Special-agent and check-parameter rules. |
| `src/service_metric_counter/agent_based/service.py` | Section parser and check plug-in. |
| `tests/test_local_site_url.py` | Credential-boundary regression tests. |

## Installation

1. Install the MKP on the Checkmk site.
2. Pick a monitoring host on the same site to carry the aggregated services.
3. Configure *Setup -> Agents -> Other integrations -> Service Metric counter*.
4. Use the local site URL, for example `http://localhost/cmk/`.
5. Run service discovery.

## Configuration

| Parameter | Meaning |
| --- | --- |
| `path` | Current site URL through localhost or a loopback address. The path must match `/<OMD_SITE>`. |
| `timeout` | REST API request timeout. |
| `service_filters` | Aggregated service definitions. |
| `service_name` | Item of the resulting service. |
| `ls_pattern` | Livestatus filter, for example `description~Users;host_labels='env' 'prod'`. |
| `metric` | Performance metric to sum. |
| `metric_label` | Human-readable label. |

The check-parameter rule *Service Metric Count* can apply optional upper WARN/CRIT levels to the total.

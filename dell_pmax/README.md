# Dell EMC PowerMax

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0-blue)
<!-- compatibility-badges:end -->

Special agent for Dell EMC PowerMax arrays through the Unisphere REST API.

## Collection safety

- HTTPS certificate verification is mandatory.
- A private CA bundle may be configured; disabling verification is not supported.
- Every request has a configurable timeout and rejects redirects.
- Proxy environment variables are ignored.
- Responses are streamed and capped at 10 MiB.
- Every response must be a successful JSON object with the expected fields.
- The complete output is built in memory and written only after all collection and validation steps succeed. Failed collections therefore cannot leave a partial Checkmk agent stream.
- API responses and host configuration are never printed for debugging.
- Values used in `sep(124)` sections have pipes and physical newlines normalized.
- The Unisphere REST API namespace is configurable rather than fixed to version `92`.

## API requests

The agent collects:

- `version`;
- `management/RuntimeUsage/read`;
- `<api_version>/vvol/symmetrix` and local-array details;
- `<api_version>/system/alert_summary`;
- `<api_version>/sloprovisioning/symmetrix/<id>/srp` and pool details.

The configured account should have only the read-only monitoring role.

## Configuration

Rule: **Setup → Agents → Other integrations → Dell PowerMax**

| Parameter | Default | Meaning |
| --- | --- | --- |
| `username` | required | Read-only Unisphere monitoring user. |
| `password` | required | Checkmk-managed secret. |
| `port` | `8443` | Unisphere HTTPS port. |
| `api_version` | `100` | REST namespace supported by the target Unisphere release. |
| `timeout` | `15s` | Per-request timeout, constrained to 0.5–120 seconds. |
| `ca_bundle` | system trust | Optional absolute private CA bundle. |

## Services

The existing services remain unchanged: version, JVM/CPU/memory statistics, server and array alerts, and storage resource pool capacity services.

## Failure behavior

Transport errors, non-2xx responses, redirects, oversized responses, invalid JSON, missing required fields, a missing local array, or incomplete alert data cause a non-zero special-agent result without publishing partial sections.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/dell_pmax/libexec/agent_dellpmax` | Verified HTTPS client and atomic output builder. |
| `src/dell_pmax/server_side_calls/agent_pmax.py` | Secret-aware command generation and secure parameters. |
| `src/dell_pmax/rulesets/agent_dellpmax.py` | Setup rule. |
| `src/dell_pmax/agent_based/` | Existing check plug-ins. |
| `tests/test_agent_dellpmax.py` | TLS, timeout, API-version and output regression tests. |

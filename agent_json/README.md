# Agent JSON

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.3.0p9-blue)
<!-- compatibility-badges:end -->

Special agent that queries one or more application-health endpoints and converts a strictly validated JSON document into safely escaped Checkmk local checks.

## Endpoint security

- Endpoints must use absolute HTTPS URLs.
- Embedded URL credentials and URL fragments are rejected.
- TLS certificate verification is mandatory and uses the Checkmk server's system trust store.
- Redirects are rejected, preventing credentials from being forwarded to another origin.
- Proxy environment variables are ignored for requests.
- Each request has a 15-second timeout.
- Responses are streamed and capped at 1 MiB.
- HTTP status must be in the 2xx range.
- Failure messages contain only the endpoint hostname and error class; response bodies are never copied into monitoring output.

Existing rules using cleartext HTTP will produce a visible UNKNOWN service until migrated to HTTPS.

## JSON schema

The response root must be an object containing a `checks` list:

```json
{
  "checks": [
    {
      "name": "Application health",
      "status": "OK",
      "summary": "All components operational",
      "data": {
        "database": "UP",
        "queue": "UP"
      }
    }
  ]
}
```

Limits and validation:

- at most 1,000 checks per endpoint;
- every check must be an object;
- `name` must be a non-empty string of at most 256 characters;
- `status` must be a string;
- `summary` may be a scalar value;
- `data` must be an object with at most 100 fields.

A schema violation rejects the complete endpoint response instead of emitting a partially trusted set of services.

## Local-check output safety

Service names, summaries, keys and values are normalized and bounded before emission. Control characters, physical newlines, quotes and backslashes cannot create additional local-check lines, sections or services.

Duplicate service names are numbered across all configured endpoints. Unknown status strings map to UNKNOWN.

## Status mapping

| Input | Checkmk state |
| --- | --- |
| `OK`, `UP` | OK |
| `WARN`, `WARNING` | WARN |
| `CRIT`, `CRITICAL`, `DOWN` | CRIT |
| `UNKN`, `UNKNOWN`, anything else | UNKNOWN |

## Configuration

Rule: **Setup → Agents → Other integrations → Agent JSON**

Each endpoint contains:

| Parameter | Meaning |
| --- | --- |
| `api_url` | Absolute HTTPS URL. |
| `method` | `POST` (default) or `GET`. |
| `username` | Optional HTTP Basic user. |
| `password` | Optional HTTP Basic password stored as a Checkmk secret. |

Rules saved with the historical single-endpoint format are migrated into the endpoint list automatically.

## Failure behavior

Every failed endpoint produces one sanitized UNKNOWN service named `JSON agent <hostname>`. The special agent returns non-zero when at least one endpoint fails, while still emitting valid services from other configured endpoints.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/agent_json/libexec/agent_json` | HTTPS client, schema validator and safe local-check renderer. |
| `src/agent_json/server_side_calls/agent_json.py` | Secret-aware special-agent command generation. |
| `src/agent_json/rulesets/agent_json.py` | Endpoint configuration form and legacy migration. |
| `tests/test_agent_json_security.py` | Endpoint, schema, failure and output-injection regression tests. |

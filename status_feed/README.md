# Public status RSS/Atom feed monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0-blue)
<!-- compatibility-badges:end -->

Monitors public HTTPS RSS and Atom status feeds, including AWS service feeds and Statuspage-style incident-history feeds.

## Security boundary

- Feed URLs must be absolute HTTPS URLs.
- URL credentials and fragments are rejected.
- DNS is resolved before the request and all returned addresses must be globally routable.
- Private, loopback, link-local, reserved and multicast destinations are rejected.
- Redirects are not followed.
- Environment proxies and rule-configured proxies are not used.
- TLS verification is mandatory.
- Responses are streamed and capped at 2 MiB.
- At most 100 feeds and 1,000 parsed items per feed are accepted.
- DTD and entity declarations are rejected before XML parsing.
- Titles, summaries, dates, names and error details are normalized and bounded.

This prevents a delegated Setup rule from turning the monitoring site into an internal-network request proxy or from feeding unbounded XML into the parser.

## Evaluation

For each feed the agent reports reachability, item count, latest title/date/summary, latest-event age and a lifecycle classification:

- **Age mode:** useful for AWS feeds that publish entries only while an event is active.
- **Incident mode:** useful for history feeds where a newest `resolved` item should be OK and an active item should raise the configured state.

Transport, status, size or XML failures cause the service to fail rather than producing partial feed data.

## Configuration

Rule: **Setup → Agents → Other integrations → Public status RSS/Atom feeds**

| Parameter | Meaning |
| --- | --- |
| `feeds` | List of public HTTPS feed names and URLs, maximum 100. |
| `timeout` | Per-feed timeout, 0.5–60 seconds. |
| `user_agent` | Bounded User-Agent string. |

Proxy configuration was removed. Requests always connect directly with the monitoring server's verified HTTPS trust policy.

The service monitoring rule configures age/incident mode and thresholds.

## Examples

```text
Amazon CloudFront  = https://status.aws.amazon.com/rss/cloudfront.rss
AWS Lambda         = https://status.aws.amazon.com/rss/lambda-eu-central-1.rss
Scrivito           = https://status.scrivito.com/incidents.atom
```

## Migration from 1.0.0

- HTTP feed URLs must be changed to HTTPS.
- Internal or private feeds are no longer supported.
- Saved proxy settings are ignored and the proxy field has been removed from Setup.
- Feeds that redirect must be configured with their final public HTTPS URL.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/status_feed/libexec/agent_status_feed` | Public HTTPS client and bounded RSS/Atom parser. |
| `src/status_feed/server_side_calls/agent.py` | Bounded command generation without proxy delegation. |
| `src/status_feed/rulesets/agent.py` | Public-HTTPS-only feed rule. |
| `src/status_feed/rulesets/status_feed.py` | Incident-mode and threshold configuration. |
| `src/status_feed/agent_based/status_feed.py` | Parser, discovery and check. |
| `tests/test_http_boundary.py` | SSRF, XML and parser-limit regression tests. |

Existing `aws_status_rss` rules and services still do not migrate automatically; configure `status_feed` and rediscover when replacing that legacy package.

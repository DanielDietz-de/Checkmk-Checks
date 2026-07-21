# Monitor Failed Notifications

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p8-blue)
<!-- compatibility-badges:end -->

A special agent that queries the local Checkmk notification log via the built-in `failed_notifications` view and raises a Checkmk service if any notification command matching a configurable regex has failed in the last 15 minutes.

## Security model

The agent reads the executing site's `automation` secret from disk. That credential is strictly confined to the same Checkmk site through `localhost`, `127.0.0.0/8`, or `::1`. Remote hosts, another local site path, URLs containing credentials, queries, or fragments, and unsupported URL schemes are rejected before the secret is read.

The agent disables proxy-environment handling for this local request so a system-wide proxy cannot receive the Authorization header.

Remote-site monitoring is intentionally not supported by this credential model. A future remote mode must use explicitly configured credentials rather than reusing the local site automation secret.

## How it works

1. Validate the configured site URL against the executing `OMD_SITE` and require a loopback target.
2. Read the local automation secret.
3. Query `check_mk/view.py?view_name=failed_notifications` using URL-encoded request parameters.
4. Count failed notification results matching the configured command regex.
5. Emit a `<<<local>>>` service named `Failed Notifications`.
6. Emit UNKNOWN instead of contacting an unsafe target or silently failing.

```text
<<<local>>>
0 "Failed Notifications" count=0 0 failed
```

## Package contents

| Path | Purpose |
| --- | --- |
| `src/notification_monitor/libexec/agent_notification_monitor` | Special agent with local-site credential confinement. |
| `src/notification_monitor/server_side_calls/special_agent.py` | Passes timeout, local site URL, and command regex. |
| `src/notification_monitor/rulesets/sepcial_agent.py` | Special-agent rule definition. |
| `tests/test_local_site_url.py` | Regression tests for the credential boundary. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create a host carrying the check, normally the Checkmk server itself.
3. Configure *Setup -> Agents -> Other integrations -> Notification Monitor*.
4. Use the current local site URL, for example `http://localhost/cmk/`.
5. Discover the `Failed Notifications` service.

## Configuration

| Parameter | Meaning |
| --- | --- |
| `path` | URL of the current site through localhost or a loopback address. The path must match `/<OMD_SITE>`. |
| `command_regex` | Regex matched against the notification command name. |
| `timeout` | HTTP request timeout. |

## Limitations

- The check only inspects the current local site.
- The look-back window remains 15 minutes.
- The local `automation` user and secret file must exist.

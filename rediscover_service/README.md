# Rediscover service

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p5-blue)
<!-- compatibility-badges:end -->

Notification plug-in that refreshes the stored discovery parameters of one Checkmk service after a matching service problem notification.

## Execution conditions

The plug-in runs only when all of the following are true:

- `NOTIFY_WHAT=SERVICE`;
- `NOTIFY_NOTIFICATIONTYPE=PROBLEM`;
- the current service state is non-OK.

Recovery, acknowledgement, downtime, host, and OK notifications do not trigger rediscovery.

## Credential boundary

The notification reads the executing site's local `automation` secret. The configured protocol, hostname, and site name are validated before that secret is read:

- only HTTP or HTTPS is accepted;
- the hostname must be `localhost`, a `127.0.0.0/8` address, or `::1`;
- the configured site name must equal the current `OMD_SITE`;
- proxy-environment handling is disabled for API requests.

The local automation credential cannot be sent to a remote host or another local Checkmk site.

## Safe activation flow

The script does not force activation of foreign changes and does not activate an unexamined pending-change set.

1. Acquire a non-blocking site-local lock so two rediscovery notifications cannot run concurrently.
2. Read the pending-change snapshot and its ETag.
3. Refuse to start when the `automation` user already owns pending changes. This avoids activating an older automation change along with the rediscovery.
4. Look up the affected service and move it to `undecided`, then back to `monitored` using the discovery API's returned body parameters.
5. Read a second pending-change snapshot.
6. Require all pre-existing change IDs to remain present.
7. Require at least one new change, owned by `automation`, whose description refers to the affected host.
8. Refuse activation if a concurrent foreign change or an unrelated same-user change appeared.
9. Activate with the second snapshot's exact ETag, `sites=[<current site>]`, and `force_foreign_changes=false`.
10. Do not follow activation redirects implicitly and accept only documented success/redirect status codes.

The ETag prevents activation if the pending-change set changes after the final verification. If a safety check fails after the discovery update, the generated change remains pending for manual review rather than being activated automatically.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/notifications/rediscover_service` | Notification script with notification gating, local credential confinement, pending-change verification, and scoped activation. |
| `src/redis_service/rulesets/redis_service.py` | Notification parameter form. |
| `tests/test_local_target.py` | Regression tests for URL confinement, notification gating, change ownership, concurrency detection, and activation payload. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create a notification rule and select *Rediscover service*.
3. Configure the current site, normally with protocol `http`, hostname `localhost`, and the current site name.
4. Restrict the notification rule to the specific services whose discovery parameters may legitimately change.
5. Ensure the notification is sent for problem states only; the script also enforces this internally.

## Configuration

| Parameter | Meaning |
| --- | --- |
| `proto` | HTTP or HTTPS for the local REST API. |
| `hostname` | `localhost` or a numeric loopback address. |
| `sitename` | Must match the executing `OMD_SITE`. |

## Operational behavior

The plug-in deliberately fails closed. It does not activate changes when:

- the automation user has older pending changes;
- the pending-change response has no ETag;
- no new change was created;
- another change appears concurrently;
- a new change belongs to another user or another host;
- the activation API rejects the ETag or request.

Resolve or activate existing automation changes before retrying the notification-driven rediscovery.

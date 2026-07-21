# Rediscover service

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p5-blue)
<!-- compatibility-badges:end -->

Notification plug-in that triggers a service rediscovery through the Checkmk REST API when a matching service notification fires.

## Security model

The notification reads the executing site's local `automation` secret. The configured protocol, hostname, and site name are validated before that secret is read:

- only HTTP or HTTPS is accepted;
- the hostname must be `localhost`, a `127.0.0.0/8` address, or `::1`;
- the configured site name must equal the current `OMD_SITE`;
- proxy-environment handling is disabled for API requests.

The local automation credential can therefore never be sent to a remote host or another local Checkmk site. Distributed or remote-site rediscovery requires a different design with explicitly configured, scoped credentials.

## How it works

1. Validate that the target is the executing site through a loopback address.
2. Read the local automation secret.
3. Look up the affected service in the discovery table.
4. Move the service to `undecided` and then back to `monitored` using the returned discovery parameters.
5. Activate the resulting change.

The plug-in only runs for service notifications. Host notifications are ignored.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/notifications/rediscover_service` | Notification script with local-site credential confinement. |
| `src/redis_service/rulesets/redis_service.py` | Notification parameter form. |
| `tests/test_local_target.py` | Regression tests for the local credential boundary. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create a notification rule and select *Rediscover service*.
3. Configure the current site, normally with protocol `http`, hostname `localhost`, and the current site name.
4. Restrict the notification rule to the specific services that should be rediscovered.

## Configuration

| Parameter | Meaning |
| --- | --- |
| `proto` | HTTP or HTTPS for the local REST API. |
| `hostname` | `localhost` or a numeric loopback address. |
| `sitename` | Must match the executing `OMD_SITE`. |

## Remaining limitation

The current activation implementation still forces activation of pending changes. That behavior is addressed separately so the credential-boundary fix remains isolated.

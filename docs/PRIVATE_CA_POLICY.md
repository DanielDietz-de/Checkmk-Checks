# Private CA and TLS trust policy

This repository uses one TLS trust policy for Checkmk special agents and notification integrations that create isolated `requests.Session` objects.

## Security objective

External integrations disable Requests environment inheritance with `session.trust_env = False`. This prevents an agent or notification from unexpectedly inheriting proxy settings or `.netrc` credentials from the Checkmk site process. Certificate trust is then supplied explicitly so proxy isolation does not remove legitimate private-CA support.

## Trust precedence

For HTTPS endpoints, certificate verification uses the first available source in this order:

1. The integration rule's `ca_file` value.
2. `REQUESTS_CA_BUNDLE` from the Checkmk site environment.
3. `CURL_CA_BUNDLE` from the Checkmk site environment.
4. The operating-system and Requests default trust store.

An explicit verification opt-out, where the integration supports one, resolves to `verify=False`. It is mutually exclusive with `ca_file` and should be used only as a temporary diagnostic or compatibility measure.

## HTTP behavior

CA files and CA environment variables apply only to HTTPS. Integrations that intentionally support HTTP do not inspect or validate CA-bundle paths for an HTTP URL. This preserves existing HTTP behavior and prevents a stale or invalid site-level CA variable from breaking a non-TLS endpoint. Existing controls that restrict remote clear-text HTTP remain in force.

## Validation and fallback behavior

A selected CA bundle must exist as a regular file readable by the Checkmk site user. Missing or invalid files fail before the request with a clear configuration error; the code does not silently disable verification.

Removing an explicit `ca_file` falls back automatically to `REQUESTS_CA_BUNDLE`, then `CURL_CA_BUNDLE`, and finally the default system trust store. Removing an environment variable similarly advances to the next source. No proxy or `.netrc` fallback is enabled.

## Checkmk configuration guidance

Prefer an explicit `ca_file` in the affected rule when the trust requirement is specific to one endpoint. Use a site-level CA environment variable when several integrations intentionally share the same trust bundle. The path is evaluated on the Checkmk server or site where the special agent or notification executes, not on the monitored appliance.

After changing the rule or CA file:

1. Confirm the endpoint hostname is present in the certificate SAN.
2. Confirm the PEM file contains the complete issuing chain required by the endpoint.
3. Confirm the site user can read the file.
4. Run the special agent or notification as the site user without exposing credentials.
5. Use the verification opt-out only to distinguish a trust-chain problem from another transport problem, then re-enable verification.

## Covered integrations

The repository-level regression gate currently covers:

- Alarms notification
- Dell PowerMax
- Hitachi HNAS REST
- Quobyte
- SEMU
- SMS Eagle notification
- Spring Boot Actuator
- Unisphere PowerMax
- Veritas Flex

The local-only Service Counter session is intentionally excluded because it calls the Checkmk site's local HTTP API and has no TLS certificate trust boundary.

## Regression requirements

Any new external integration that sets `trust_env = False` must either implement this policy or document why no TLS trust boundary exists. Tests must cover explicit bundle precedence, both supported site environment variables, system-trust fallback, invalid paths, verification opt-out behavior where available, and continued proxy/`.netrc` isolation.

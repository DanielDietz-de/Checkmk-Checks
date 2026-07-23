# Kentix SMS Gateway notification

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

Bulk-capable Checkmk notification plug-in that sends SMS messages through a Kentix AlarmManager's legacy SMS gateway.

## Request security

The plug-in sends one HTTPS POST to:

```text
https://<gateway>/php/sms_gateway.php
```

The gateway password, recipient and message are form fields in the POST body. They are not embedded in the URL and therefore do not appear in normal URL access logs, browser histories or proxy request-line logs.

Additional safeguards:

- HTTPS is mandatory;
- redirects and proxy-environment variables are disabled;
- TLS uses system trust or an optional private CA bundle;
- requests have a configurable timeout;
- pager numbers are validated after separator removal;
- messages are normalized and limited to 320 characters;
- normal successful 2xx responses are accepted;
- SMS submission is attempted exactly once after a transport failure because the gateway may already have accepted it.

The legacy endpoint must support `application/x-www-form-urlencoded` POST fields named `key`, `recipients`, and `message`. Verify this on the deployed Kentix firmware before enabling the updated rule.

## Error mapping

| Code | Meaning |
| --- | --- |
| `403` | wrong SMS gateway password |
| `404` | SMS gateway not active |
| `900` | SIM card not recognized |
| `901` | GSM modem not detected |
| `902` | SIM card locked |

Bulk mode remains supported and sends one subject covering the bulk contexts to the first context's pager number.

## Configuration

| Parameter | Meaning |
| --- | --- |
| `ipaddress` | Gateway hostname with optional port; an `https://` prefix is accepted. |
| `password` | SMS gateway password stored in Checkmk's password store. |
| `template_text` | Message template with Checkmk context substitutions. |
| `timeout` | Per-request timeout, constrained to 0.5–120 seconds. |
| `ca_bundle` | Optional absolute private CA bundle. |

Contact pager numbers must contain 6–20 digits with an optional leading `+`; spaces, parentheses, dots, slashes and hyphens are removed.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/notifications/kentix` | Single and bulk POST delivery. |
| `src/kentix_sms_gateway/rulesets/kentix.py` | Notification parameters. |
| `tests/test_kentix.py` | URL-confidentiality, retry and validation tests. |

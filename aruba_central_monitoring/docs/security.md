# Security model

## Trust boundaries

The Aruba Central JSON, stdout, and stderr are untrusted vendor input. The collector limits displayed error text, normalizes line breaks, and redacts common secret assignments. It extracts only documented fields and emits compressed JSON rather than executable syntax.

The collector validates the complete normalized AP set before writing the last-known-good cache or emitting piggyback data. If two APs normalize to the same piggyback host name, the refresh fails explicitly rather than combining devices under one target.

The Group/Site mapping is an administrative allow-list. Unknown groups or sites fail the complete synchronization before any REST request is made. Distinct group names that normalize to the same Checkmk folder ID are also rejected before mutation.

## Credentials

The PowerShell plug-in does not accept or store Aruba credentials. Configure authentication with the native `cencli` profile or credential mechanism under the Checkmk agent service identity. Do not put tokens in command suffix arguments, agent output, fixtures, or the repository.

The REST synchronizer reads the Checkmk automation secret from a separate file. On Unix, group or other access is rejected. The secret is placed only in the authorization header and never printed.

## Network and TLS

- The collector delegates remote access to `cencli` and applies a bounded process timeout.
- Remote Checkmk REST endpoints require HTTPS with normal certificate verification. A private CA bundle can be supplied with `--ca-file`; there is no insecure verification switch. Loopback HTTP is accepted only for a local site API.
- Environment proxy inheritance is disabled for the authenticated REST session.
- Authenticated HTTP redirects are rejected.

## Files and privileges

Run the collector with the least-privileged Windows service account capable of reading the `cencli` profile and writing only its cache path. Protect the agent configuration and native CLI profile with Windows ACLs.

Run the synchronizer as the Checkmk site user or another restricted account. Grant the automation user only the permissions required to create folders and hosts and, when selected, activate changes.

## Safe failure behavior

- Failed collections do not replace the last-known-good file.
- Stale AP data is never represented as a successful collection.
- Piggyback host-name collisions abort the fresh collection before cache replacement or piggyback emission.
- The synchronizer rejects malformed or truncated AP sections and duplicate piggyback targets rather than provisioning from a partial or ambiguous inventory.
- Folder-ID collisions are rejected before REST mutations.
- Only explicit `already exists` responses are treated as idempotent create results; other HTTP errors remain failures.
- The synchronizer is non-mutating by default and performs no delete or move operation.
- Redirects, unexpected HTTP errors, malformed JSON, and mapping mismatches stop processing with a nonzero exit code.

## Reporting

Sanitize production AP names, serials, MAC addresses, IP addresses, tenant identifiers, URLs, tokens, and complete vendor payloads before attaching diagnostics to a public issue.

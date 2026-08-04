# Security policy

## Reporting a vulnerability

Use GitHub's **private security advisory** feature for this repository whenever possible. Do not open a public issue containing exploit instructions, credentials, sensitive logs, production addresses, customer information, or an unpatched vulnerability.

A useful private report includes:

- affected package, version, file, and Checkmk version;
- deployment model and privilege boundary;
- prerequisite access or configuration;
- reproducible steps or a minimal sanitized proof of concept;
- security impact and realistic attack path;
- suggested remediation, when known;
- whether credentials, tokens, or private data may already have been exposed.

If private advisories are unavailable, open a public issue containing only a request for a private contact channel. Do not disclose the vulnerability details publicly.

## Supported versions

Support is determined per package by these canonical metadata fields:

- `version.min_required`
- `version.packaged`
- `version.usable_until`

A repository-wide Checkmk validation run confirms package loading, registration, manuals, packaging, and core reload behavior for the configured Checkmk targets. It does not prove every vendor API response, SNMP firmware variant, permission model, or production topology.

Legacy or unverified packages may remain available for existing deployments. Their presence is not a security certification. Review the package README, [`MAINTENANCE.md`](MAINTENANCE.md), and the current repository audit before deployment.

## Security expectations

Contributions must follow these boundaries unless a narrowly scoped, documented, and tested exception is unavoidable:

- never commit secrets, private keys, production credentials, or unsanitized customer data;
- do not flatten Checkmk `Secret` objects into ordinary strings in server-side command construction;
- do not use `eval`, `exec`, `os.system`, `shell=True`, or executable configuration formats;
- require verified TLS for credential-bearing network traffic and support a deliberate private CA path where appropriate;
- reject redirects and inherited proxy settings where they could leak credentials or cross a trust boundary;
- use bounded timeouts, response sizes, parser inputs, item counts, caches, and emitted output;
- validate all untrusted structures before use;
- use atomic, permission-controlled, symlink-resistant writes for state and credential-adjacent files;
- fail closed instead of publishing partial output as trustworthy;
- avoid logging secrets, complete payloads, authorization headers, sensitive URLs, or unbounded response bodies;
- use least-privilege GitHub Actions permissions and immutable external dependency references.

## Coordinated remediation

Validated vulnerabilities should be fixed in the smallest safe scope, with regression tests and migration guidance. Affected credentials must be rotated independently of code remediation. Removing a secret from the latest commit does not remove it from Git history.

Public disclosure should occur only after a fix or effective mitigation is available and users have had a reasonable opportunity to update.

## Out of scope

The following are normally support or hardening questions rather than repository vulnerabilities:

- unsupported Checkmk or vendor versions;
- insecure deployment choices that contradict package documentation;
- findings that require already-authorized administrative access and do not cross an additional trust boundary;
- generic dependency reports without a reachable vulnerable code path;
- scanner output without validation against the repository's actual implementation.

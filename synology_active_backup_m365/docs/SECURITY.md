# Security

## Trust model

The Checkmk integration retrieves monitoring data from the token-protected API of the independently installed Synology collector. Neither the Checkmk special agent nor this repository writes to Synology Active Backup databases.

## API transport

The upstream collector exposes HTTP on TCP/9876 by default. HTTP protects neither the Bearer token nor the returned monitoring data against interception.

For the initial acceptance test:

- never expose TCP/9876 to the Internet;
- restrict access with the DSM firewall to the Checkmk server or a single temporary test host;
- use a dedicated management network where possible;
- remove temporary broad firewall rules after testing;
- keep `privacy.redact_names: true` unless identifiable M365 object names are explicitly required.

Production hardening must select and test one of these patterns before the integration is declared production-ready:

1. verified HTTPS in front of the collector API, for example through a controlled reverse proxy; or
2. another equivalently protected management transport with strict source filtering and documented trust assumptions.

Certificate verification must remain enabled for remote HTTPS. An `insecure` certificate mode will not be the production default.

## API token handling in Checkmk

The package targets Checkmk 2.5 for secure Password Store integration.

The Setup rule uses the `Password` form specification. The server-side-call plug-in passes a Password Store **reference** with `--token-id`; it does not expand the secret into the generated command line. The special agent resolves that reference at runtime through `cmk.password_store.v1_unstable`.

For direct manual execution only, the special agent also supports the explicit `--token` option provided by the same Checkmk password-store helper. Avoid using explicit tokens in shell history.

The special agent must never:

- print the token;
- include the token in errors;
- store the token in fixtures or cache files;
- send the token through an environment-configured HTTP proxy;
- follow an authenticated HTTP redirect to another origin.

The initial special-agent implementation therefore disables environment proxy inheritance and rejects redirects.

## Data minimization

The upstream collector can redact Microsoft 365 job/user names. Keep that feature enabled during acceptance unless the human-readable task name is required to distinguish real backup jobs.

Sanitized fixtures in this repository contain no real tenant IDs, email addresses, credentials, NAS names, public addresses, or production paths.

## Third-party updates

The DSM collector is outside this repository's release boundary. Before changing the supported upstream baseline:

- review the upstream release and source changes;
- verify release artifact hashes from the upstream release metadata;
- compare `/api/v1/status` against the fixtures and parser expectations;
- confirm read-only database behavior and package-user execution remain unchanged;
- run live acceptance before production rollout.

## Reporting diagnostics

Before attaching `/api/v1/status` output to an issue, remove or replace:

- API tokens;
- tenant identifiers;
- usernames and email addresses;
- backup names if sensitive;
- internal hostnames/IPs if sensitive;
- source database paths if they reveal internal structure.

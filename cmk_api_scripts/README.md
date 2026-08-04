# Checkmk API scripts

These scripts are standalone repository utilities, not MKP payloads. Their code
and tests define behavior; this document summarizes the current implementation.

## `activate_changes.py`

Activates pending changes through the supported Checkmk REST API.

Credentials are never stored in the script or accepted as a command-line
argument. Set them at runtime:

```bash
export CHECKMK_SITE_URL='https://checkmk.example.com/mysite'
export CHECKMK_USER='automation'
export CHECKMK_SECRET='read-from-a-secret-store'
python3 activate_changes.py
```

`CHECKMK_SECRET` may be omitted for an interactive hidden prompt. The script:

- requires HTTPS for remote servers unless `--allow-http` is deliberately set;
- verifies TLS by default and supports `--ca-file` for a private CA;
- rejects redirects and URL-embedded credentials;
- uses bounded request timeouts and response diagnostics;
- obtains the pending-change ETag before activation;
- waits for the activation run to complete;
- supports `--no-verify` only as an explicit diagnostic opt-out.

Run `python3 activate_changes.py --help` for the complete current interface.

## `exchange_publish.py`

Publishes new plugin versions to the Checkmk Exchange. It compares the newest
local `<plugin>/<plugin>-<version>.mkp` with the published version and uploads
packages that are behind.

Credentials come from `EXCHANGE_USER` and `EXCHANGE_PASSWORD`. If
`EXCHANGE_PASSWORD` is unset, the script prompts with `getpass`.

```bash
EXCHANGE_USER=you@example.com python3 exchange_publish.py \
  --repo /path/to/Checkmk-Checks --dry-run
```

Relevant flags include `--dry-run`, `--only`, `--exclude`, `--limit`, and
`--description`. Inspect `python3 exchange_publish.py --help` for the executable
contract.

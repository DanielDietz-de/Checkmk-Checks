# oxidized_backup

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p34-blue)
<!-- compatibility-badges:end -->

`oxidized_backup` is a Checkmk 2.4 extension that verifies the complete Oxidized backup chain for every device already exported by Checkmk to Oxidized.

The existing Checkmk Oxidized export remains the only source of truth. A device is expected to have a backup when it appears in that JSON export, for example because the Checkmk host tag `For_Oxidized` is set. The package does not implement a second tag filter, host list, folder rule, or hostname pattern.

The collector runs as a **Checkmk Linux agent plug-in on the Oxidized host**. It is not a server-side special agent. This placement gives it controlled local access to the Oxidized Git repository while it still emits piggyback data for all exported network devices.

## What is verified

For every device in the Checkmk export, the check verifies that:

1. the node is loaded by Oxidized;
2. the latest completed collection succeeded and is recent enough;
3. a non-empty configuration blob exists at the expected path in the local Oxidized Git repository.

On the Oxidized host, central services additionally verify that:

1. the Checkmk export and Oxidized inventory reconcile without missing or duplicate nodes;
2. all configured local Git repositories are valid and contain every expected device artifact;
3. periodic `git fsck --connectivity-only --no-dangling` checks succeed;
4. every local repository `HEAD` equals the configured remote branch `HEAD` returned by `git ls-remote`.

A recent successful collection is not inferred from Git commit age. Oxidized does not create a new Git commit when a device configuration is unchanged. Collection freshness and configuration-change history are therefore treated as separate facts.

## Services

Each device from the Checkmk Oxidized export receives:

- **Oxidized backup**

The Oxidized host receives:

- **Oxidized backup inventory**
- **Oxidized Git repository**
- **Oxidized Git remote synchronization**

Remote synchronization is intentionally a central service. One unavailable Git remote must not create the same alert on every switch.

## State model

### Per-device service

| Condition | State |
| --- | --- |
| Recent successful collection and non-empty local Git blob | OK |
| Successful collection older than warning age | WARN |
| Successful collection older than critical age | CRIT |
| Node missing from Oxidized | CRIT |
| Oxidized status `never`, `no_connection`, `timelimit`, or failed | CRIT |
| Local Git artifact missing or empty | CRIT |
| Oxidized API unavailable | UNKNOWN, while local Git verification is still reported |
| Duplicate or ambiguous node identity | UNKNOWN |
| No unique Git repository mapping | UNKNOWN |

### Central repository services

| Condition | State |
| --- | --- |
| Repository valid, all artifacts present, fsck successful | OK |
| Local and remote `HEAD` identical | OK |
| Local and remote `HEAD` differ within the configured grace period | WARN |
| Local and remote `HEAD` differ beyond the grace period | CRIT |
| Remote authentication rejected, remote missing, or branch missing | CRIT |
| Remote temporarily unreachable with a recently verified synchronization | WARN |
| Remote unreachable beyond the maximum verification age | CRIT |
| Remote unavailable without any prior verification | UNKNOWN |
| Local repository missing, invalid, or unreadable | CRIT |
| Monitor state cannot be read or persisted | UNKNOWN |

## Architecture

```text
Checkmk hosts with For_Oxidized
             │
             ▼
existing Checkmk oxidized.json
             │
             ├──────────────► Oxidized node source
             │
             └──────────────► oxidized_backup agent plug-in
                                  │
                                  ├── Oxidized /nodes.json
                                  ├── persistent Oxidized hook state
                                  ├── local Git object database
                                  └── remote Git branch HEAD
                                           │
                                           ▼
                                central + piggyback sections
```

The agent plug-in emits standard Checkmk piggyback markers. One section remains on the Oxidized host and one section is assigned to each exported Checkmk hostname.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/agents/plugins/oxidized_backup` | Standalone Linux agent plug-in and Oxidized hook-state recorder. |
| `src/oxidized_backup/agent_based/oxidized_backup.py` | Parses central and piggyback data, discovers services, and evaluates states. |
| `src/oxidized_backup/checkman/oxidized_backup` | Checkmk manual page. |
| `examples/oxidized_backup.json` | Generic, non-production example configuration. |
| `examples/oxidized-hook.yml` | Generic Oxidized exec-hook example. |
| `tests/` | Parser, security, Git, hook-state, discovery, and state-matrix tests. |

The MKP contains both the Checkmk plug-in family and the Linux agent plug-in under the standard `agents` package component.

## Requirements

- Checkmk 2.4
- Linux Checkmk agent on the Oxidized host
- Python 3.11 or newer on the Oxidized host
- Git command-line client
- `runuser` when the Checkmk agent executes as root and Git must run as the unprivileged Oxidized account
- Oxidized web API available locally or over a trusted management network
- Oxidized Git output
- a Git remote that can be queried non-interactively by the Oxidized service account

The collector uses only Python's standard library. It does not require PyYAML, Requests, Rugged, or direct access to the backed-up configuration contents.

## Installation

### 1. Install the MKP on Checkmk

Install the generated `oxidized_backup-*.mkp` package through **Setup > Maintenance > Extension packages**, or as the site user:

```bash
mkp add /path/to/oxidized_backup-1.0.0.mkp
mkp enable oxidized_backup 1.0.0
cmk -R
```

After installation, the Linux agent plug-in is available on the Checkmk site at:

```text
$OMD_ROOT/local/share/check_mk/agents/plugins/oxidized_backup
```

### 2. Install the agent plug-in on the Oxidized host

Run the collector at a cached interval. Five minutes is recommended for the Git and network operations performed by this plug-in:

```bash
install -d -m 0755 /usr/lib/check_mk_agent/plugins/300
install -m 0755 \
  /path/to/oxidized_backup \
  /usr/lib/check_mk_agent/plugins/300/oxidized_backup
```

The same installed file is also called by the Oxidized exec hook.

### 3. Create state directories

Use separate ownership for Oxidized hook state and Checkmk monitor state:

```bash
install -d -m 0750 -o oxidized -g oxidized \
  /var/lib/oxidized/oxidized_backup

install -d -m 0700 -o root -g root \
  /var/lib/check_mk_agent/oxidized_backup
```

Replace the account and paths when the Oxidized service uses different values.

### 4. Create the configuration

Copy `examples/oxidized_backup.json` to:

```text
/etc/check_mk/oxidized_backup.json
```

Then replace every example value with the actual environment values. The package intentionally ships no production URL, repository path, branch, site name, hostname, or threshold default.

The Checkmk agent runs as root, while the Oxidized hook runs as the Oxidized service account. Make the configuration readable by both but not by unrelated users:

```bash
chown root:oxidized /etc/check_mk/oxidized_backup.json
chmod 0640 /etc/check_mk/oxidized_backup.json
```

Validate it as both execution identities:

```bash
/usr/lib/check_mk_agent/plugins/300/oxidized_backup \
  --check-config \
  --config /etc/check_mk/oxidized_backup.json

runuser -u oxidized -- \
  /usr/lib/check_mk_agent/plugins/300/oxidized_backup \
  --check-config \
  --config /etc/check_mk/oxidized_backup.json
```

### 5. Configure the Oxidized hook

Merge the supplied hook into the existing Oxidized configuration. Do not replace the complete `hooks` section when other hooks are already configured.

```yaml
hooks:
  checkmk_oxidized_backup_state:
    type: exec
    events:
      - node_success
      - node_fail
      - post_store
    cmd: >-
      /usr/lib/check_mk_agent/plugins/300/oxidized_backup
      --record-hook
      --config /etc/check_mk/oxidized_backup.json
    timeout: 10
    async: false
```

`node_success` records every successful configuration retrieval, including unchanged configurations. `node_fail` records a failed collection after Oxidized exhausts its retries. `post_store` records actual Git storage events, which occur only when Oxidized stores a changed configuration.

Restart Oxidized after changing its hook configuration and verify that the hook-state file is updated after the next node job.

### 6. Discover services

1. Run the Checkmk agent on the Oxidized host.
2. Rediscover services on the Oxidized host and accept the three central services.
3. Let Checkmk process the piggyback data.
4. Rediscover services on the devices contained in the Oxidized export and accept **Oxidized backup**.

For SNMP-only switches, keep SNMP enabled and allow piggyback data from the Oxidized host. No Checkmk agent needs to run on the switches themselves.

## Configuration reference

### `inventory`

The existing Checkmk-generated JSON source. The expected schema is the schema already produced by the repository's `oxidized` exporter:

```json
[
  {"hostname": "switch-1", "os": "picos"},
  {"hostname": "switch-2", "os": "aoscx"}
]
```

Required:

- `url`: `https://`, `http://`, or `file://` URL

Optional bounded transport values:

- `timeout_seconds`: 0.1 to 120 seconds
- `max_response_bytes`: 1 KiB to 64 MiB
- `ca_file`: absolute CA bundle path for HTTPS
- `allow_insecure_http`: must be explicitly `true` for non-loopback cleartext HTTP
- `auth`: optional bearer or basic authentication using a secret file

Credentials embedded in a URL are rejected.

### `oxidized`

The Oxidized node API, normally the local `/nodes.json` endpoint. The same transport and authentication options as `inventory` are supported, except `file://` is not accepted.

A loopback HTTP URL is allowed without the non-loopback cleartext opt-in.

### `state`

- `hook_state_file`: persistent state written by the Oxidized service account
- `monitor_state_file`: remote mismatch, last synchronization, and fsck state written by the Checkmk agent

Both must be absolute paths. State updates use file locks, temporary files, `fsync`, and atomic replacement. Existing state-file symlinks are refused.

### `git`

- `run_as_user`: required unprivileged account used for all Git operations
- `git_binary`: optional absolute Git executable path; default `/usr/bin/git`
- `repositories`: one or more repository definitions

Repository definition:

- `id`: unique display and state key
- `path`: absolute local Git repository path, bare or non-bare
- `groups`: Oxidized groups handled by this repository
  - `null` handles ungrouped/default nodes
  - a group name handles exactly that group
  - `"*"` is one optional fallback and may be used by only one repository
- `single_repo`:
  - `true`: grouped node path is `group/name`
  - `false`: each group repository stores the node at `name`
- `remote`: optional Git remote name; default `origin`
- `branch`: optional explicit branch; when omitted, the current symbolic `HEAD` branch is used
- `command_timeout_seconds`: optional, 1 to 300 seconds
- `fsck_timeout_seconds`: optional integrity-check timeout, 1 to 3600 seconds

The remote is queried as `git.run_as_user` with `GIT_TERMINAL_PROMPT=0`. Configure SSH keys, `known_hosts`, or a non-interactive Git credential helper for that account. Do not place tokens or passwords in this JSON file.

### `policy`

All policy values are required:

- `collection_warning_age_seconds`
- `collection_critical_age_seconds`
- `remote_sync_grace_seconds`
- `remote_verification_max_age_seconds`
- `fsck_interval_seconds`, minimum 300
- `orphan_state`
  - `0`: OK
  - `1`: WARN
  - `2`: CRIT

The critical collection age must be greater than the warning age.

Choose collection thresholds based on the complete Oxidized cycle duration, including thread count, node count, retries, device timeouts, and the configured Oxidized interval.

## Multiple Git repositories and groups

For a single repository containing grouped devices:

```json
{
  "id": "all-devices",
  "path": "/var/lib/oxidized/oxidized.git",
  "groups": ["*"],
  "single_repo": true
}
```

Expected paths are:

```text
switch-1
switches/switch-2
routers/router-1
```

For separate repositories per group:

```json
[
  {
    "id": "switches",
    "path": "/var/lib/oxidized/switches.git",
    "groups": ["switches"],
    "single_repo": false
  },
  {
    "id": "routers",
    "path": "/var/lib/oxidized/routers.git",
    "groups": ["routers"],
    "single_repo": false
  },
  {
    "id": "default",
    "path": "/var/lib/oxidized/default.git",
    "groups": [null],
    "single_repo": false
  }
]
```

Ambiguous mappings are not guessed. The affected device becomes UNKNOWN and the central repository service explains the mapping problem.

## Validation and troubleshooting

Validate the installed configuration:

```bash
/usr/lib/check_mk_agent/plugins/300/oxidized_backup \
  --check-config \
  --config /etc/check_mk/oxidized_backup.json
```

Run the collector directly:

```bash
/usr/lib/check_mk_agent/plugins/300/oxidized_backup \
  --config /etc/check_mk/oxidized_backup.json
```

Check the complete agent output:

```bash
check_mk_agent | sed -n '/<<<oxidized_backup/,/<<<<>>>>/p'
```

Verify the Oxidized hook state:

```bash
stat /var/lib/oxidized/oxidized_backup/hook-state.json
```

Verify the local Git branch and a device path without reading configuration content:

```bash
runuser -u oxidized -- \
  git -C /var/lib/oxidized/oxidized.git rev-parse HEAD

runuser -u oxidized -- \
  git -C /var/lib/oxidized/oxidized.git cat-file -e 'HEAD:switch-1'
```

Verify remote access under the same identity:

```bash
runuser -u oxidized -- \
  env GIT_TERMINAL_PROMPT=0 \
  git -C /var/lib/oxidized/oxidized.git \
  ls-remote --exit-code origin refs/heads/main
```

On the Checkmk site:

```bash
cmk-validate-plugins
cmk -d oxidized-host
cmk-piggyback list sources
cmk -IIv oxidized-host switch-1
cmk -nv oxidized-host switch-1
```

## Security properties

- no shell execution; subprocesses use explicit argument arrays;
- Git operations run as the configured unprivileged Oxidized account;
- `GIT_TERMINAL_PROMPT=0` prevents blocked password prompts;
- no configuration blob contents are read or returned;
- only Git object type, size, object ID, repository `HEAD`, and remote `HEAD` are inspected;
- HTTPS certificate verification is mandatory and supports a custom CA bundle;
- cross-origin and HTTPS-to-HTTP redirects are refused;
- non-loopback cleartext HTTP requires explicit opt-in;
- HTTP responses and configuration files have hard size limits;
- secret files must be regular files with no group or other permissions;
- credentials embedded in URLs are rejected;
- errors are bounded and redact URL user information, tokens, and password-like values;
- node names are validated before being used in piggyback markers or Git tree paths;
- state files use locking and atomic replacement;
- repository checks do not modify the local branch, working tree, or remote-tracking refs.

## Operational notes

- The collector intentionally uses `git ls-remote`, not a local remote-tracking branch, to verify the actual remote branch.
- A short mismatch grace period prevents alerts while the Oxidized `post_store` hook is still pushing a new commit.
- The full connectivity fsck runs only at the configured interval. Its result is persisted between agent runs.
- Removing `For_Oxidized` removes the device from the authoritative export. Its piggyback section then stops, and the service becomes vanished through normal Checkmk discovery handling.
- A node left in Oxidized after removal from the export appears as an orphan in the central inventory service.
- The collector never triggers a backup, changes a Git repository, fetches a remote into local refs, or repairs a repository. It is monitoring-only.

## Removal

Disable and remove the MKP from Checkmk:

```bash
mkp disable oxidized_backup 1.0.0
mkp remove oxidized_backup 1.0.0
cmk -R
```

Remove the agent-side files only after disabling the Oxidized hook:

```bash
rm -f /usr/lib/check_mk_agent/plugins/300/oxidized_backup
rm -f /etc/check_mk/oxidized_backup.json
rm -rf /var/lib/check_mk_agent/oxidized_backup
rm -rf /var/lib/oxidized/oxidized_backup
```

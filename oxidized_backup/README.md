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

## Deployment model

There are three distinct systems. No installation files are copied to the network devices.

| System | What happens there |
| --- | --- |
| **Checkmk server** | Install and enable the MKP. The MKP installs the Checkmk check plug-in and places all files required for the Oxidized host in the site's agent-download directory. Service discovery and activation also happen here. |
| **Oxidized host** | Install the packaged Linux agent plug-in, create its configuration and state directories, merge the Oxidized hook, and run all local validation commands. |
| **Network devices** | Nothing is installed. They receive the piggyback service because they are present in the existing Checkmk Oxidized export. |

```text
Checkmk server
  ├── Checkmk check plug-in
  ├── packaged Linux agent plug-in ─────────────┐
  ├── packaged JSON configuration template ────┤ copied once to
  └── packaged Oxidized hook template ─────────┤ the Oxidized host
                                                ▼
Oxidized host
  ├── Checkmk Linux agent
  ├── oxidized_backup agent plug-in
  ├── /etc/check_mk/oxidized_backup.json
  ├── Oxidized exec hook
  ├── persistent state directories
  ├── local Oxidized Git repository
  └── access to the configured Git remote
                                                │
                                                ▼
                                   central + piggyback sections
```

## Files delivered by the MKP

After the MKP is enabled, the following files exist on the **Checkmk server** below the site directory:

| File on the Checkmk server | Purpose | Destination on the Oxidized host |
| --- | --- | --- |
| `$OMD_ROOT/local/share/check_mk/agents/plugins/oxidized_backup` | Executable Linux agent plug-in and Oxidized hook-state recorder | `/usr/lib/check_mk_agent/plugins/300/oxidized_backup` |
| `$OMD_ROOT/local/share/check_mk/agents/cfg_examples/oxidized_backup.json` | Configuration template | `/etc/check_mk/oxidized_backup.json` |
| `$OMD_ROOT/local/share/check_mk/agents/cfg_examples/oxidized_backup-hook.yml` | Oxidized hook snippet; reference file only | Merge into the active Oxidized configuration |

The repository source files under `src/agents/` are for development. For a normal installation, use the files installed by the MKP so the Checkmk check plug-in, agent plug-in, and templates are all from the same package version.

## Requirements

### Checkmk server

- Checkmk 2.4
- permission to install and enable an MKP
- shell access as the Checkmk site user for the CLI method

### Oxidized host

- Linux Checkmk agent
- Python 3.11 or newer
- Git command-line client
- `runuser` when the Checkmk agent executes as root and Git must run as the unprivileged Oxidized account
- Oxidized web API available locally or over a trusted management network
- Oxidized Git output
- a Git remote that can be queried non-interactively by the Oxidized service account

The collector uses only Python's standard library. It does not require PyYAML, Requests, Rugged, or direct access to the backed-up configuration contents.

## Installation

Each step states exactly where it must be performed.

### 1. Download and verify the MKP — administrator workstation or Checkmk server

For a released package, download the MKP and its checksum from the `oxidized_backup/` directory on the repository's `master` branch. Pull-request workflow artifacts are test builds and are not the normal production installation source.

```bash
PACKAGE_VERSION=1.0.1
REPOSITORY_RAW=https://raw.githubusercontent.com/DanielDietz-de/Checkmk-Checks/master

curl --fail --location --remote-name \
  "${REPOSITORY_RAW}/oxidized_backup/oxidized_backup-${PACKAGE_VERSION}.mkp"
curl --fail --location --remote-name \
  "${REPOSITORY_RAW}/oxidized_backup/oxidized_backup-${PACKAGE_VERSION}.mkp.sha256"

sha256sum --check "oxidized_backup-${PACKAGE_VERSION}.mkp.sha256"
```

When the download is performed on an administrator workstation, copy the verified MKP to the Checkmk server:

```bash
scp "oxidized_backup-${PACKAGE_VERSION}.mkp" root@checkmk.example:/tmp/
```

Replace `checkmk.example` with the Checkmk server name.

### 2. Install and enable the MKP — Checkmk server

Use the Checkmk GUI under **Setup > Maintenance > Extension packages**, or switch to the site user and use the CLI:

```bash
sudo --login --user cmk
PACKAGE_VERSION=1.0.1

mkp add "/tmp/oxidized_backup-${PACKAGE_VERSION}.mkp"
mkp enable oxidized_backup "${PACKAGE_VERSION}"
cmk -R
```

Replace `cmk` with the actual Checkmk site name.

Confirm that all three deployment files were installed:

```bash
test -x "$OMD_ROOT/local/share/check_mk/agents/plugins/oxidized_backup"
test -r "$OMD_ROOT/local/share/check_mk/agents/cfg_examples/oxidized_backup.json"
test -r "$OMD_ROOT/local/share/check_mk/agents/cfg_examples/oxidized_backup-hook.yml"
```

At this point the Checkmk check plug-in is installed, but nothing has yet been installed on the Oxidized host.

### 3. Copy the packaged files — Checkmk server to Oxidized host

Run this on the **Checkmk server** as a user that can read the site files:

```bash
CHECKMK_SITE=cmk
OXIDIZED_HOST=oxidized.example
SITE_ROOT="/omd/sites/${CHECKMK_SITE}"

scp \
  "${SITE_ROOT}/local/share/check_mk/agents/plugins/oxidized_backup" \
  "${SITE_ROOT}/local/share/check_mk/agents/cfg_examples/oxidized_backup.json" \
  "${SITE_ROOT}/local/share/check_mk/agents/cfg_examples/oxidized_backup-hook.yml" \
  "root@${OXIDIZED_HOST}:/tmp/"
```

Replace `cmk` and `oxidized.example` with the actual site and host names.

Do not download an unrelated copy of the agent plug-in directly from a different branch or commit. Copying the files installed by the MKP keeps both sides on the same version.

### 4. Install files and create state directories — Oxidized host

All commands in this step run as `root` on the **Oxidized host**.

Install the executable:

```bash
install -d -m 0755 /usr/lib/check_mk_agent/plugins/300
install -m 0755 \
  /tmp/oxidized_backup \
  /usr/lib/check_mk_agent/plugins/300/oxidized_backup
```

Install the configuration template and retain the hook template as an administrative reference:

```bash
install -d -m 0755 /etc/check_mk
install -m 0640 -o root -g oxidized \
  /tmp/oxidized_backup.json \
  /etc/check_mk/oxidized_backup.json
install -m 0644 -o root -g root \
  /tmp/oxidized_backup-hook.yml \
  /etc/check_mk/oxidized_backup-hook.yml
```

Create both state directories on the **Oxidized host**:

```bash
install -d -m 0750 -o oxidized -g oxidized \
  /var/lib/oxidized/oxidized_backup

install -d -m 0700 -o root -g root \
  /var/lib/check_mk_agent/oxidized_backup
```

The directories have different owners because they are written by different processes:

| Directory | Writer | Stored data |
| --- | --- | --- |
| `/var/lib/oxidized/oxidized_backup` | Oxidized service account | Persistent `node_success`, `node_fail`, and `post_store` hook state |
| `/var/lib/check_mk_agent/oxidized_backup` | Checkmk agent process, normally `root` | Remote mismatch history, last successful remote verification, and cached Git fsck state |

If the Oxidized service account or Checkmk agent execution user differs, change the ownership accordingly. The JSON configuration must remain readable by both identities.

### 5. Configure the collector — Oxidized host

Edit the installed file:

```bash
editor /etc/check_mk/oxidized_backup.json
```

The template is deliberately non-functional until these environment-specific values are set:

| Setting | What to enter |
| --- | --- |
| `inventory.url` | URL or local file URI of the existing Checkmk-generated `oxidized.json`. The request originates from the Oxidized host. |
| `oxidized.url` | Oxidized node API. `http://127.0.0.1:8888/nodes.json` is appropriate only when the API listens on that loopback address and port. |
| `state.hook_state_file` | Normally `/var/lib/oxidized/oxidized_backup/hook-state.json`. |
| `state.monitor_state_file` | Normally `/var/lib/check_mk_agent/oxidized_backup/monitor-state.json`. |
| `git.run_as_user` | Unprivileged account that owns or can read the Oxidized Git repository and authenticate to its remote. |
| `git.repositories[].path` | Actual local bare or non-bare Oxidized Git repository. |
| `git.repositories[].remote` | Git remote name, normally `origin`. |
| `git.repositories[].branch` | Remote branch to verify, for example `main`. |
| `policy.*` | Thresholds appropriate for the complete Oxidized polling cycle and acceptable remote-verification age. |

Do not use the example URL, repository path, branch, or thresholds without validating them for the actual environment.

Keep the configuration protected but readable by the Oxidized service account:

```bash
chown root:oxidized /etc/check_mk/oxidized_backup.json
chmod 0640 /etc/check_mk/oxidized_backup.json
```

### 6. Merge the Oxidized hook — Oxidized host

The file `/etc/check_mk/oxidized_backup-hook.yml` is a **snippet**, not a second Oxidized configuration file. Open the active Oxidized configuration and merge the `checkmk_oxidized_backup_state` entry into its existing `hooks:` mapping.

A typical service-account installation uses:

```text
/home/oxidized/.config/oxidized/config
```

The actual path depends on the service unit and deployment. Confirm it before editing:

```bash
systemctl cat oxidized
```

Review the packaged snippet:

```bash
cat /etc/check_mk/oxidized_backup-hook.yml
```

Important:

- if the active configuration already contains `hooks:`, add only the nested `checkmk_oxidized_backup_state` entry;
- do not create a second top-level `hooks:` key;
- keep the executable and configuration paths exactly aligned with the files installed in steps 4 and 5.

Restart Oxidized and inspect its log:

```bash
systemctl restart oxidized
systemctl --no-pager --full status oxidized
journalctl --unit oxidized --since "-5 minutes" --no-pager
```

### 7. Validate the local installation — Oxidized host

Validate the JSON configuration as both execution identities:

```bash
/usr/lib/check_mk_agent/plugins/300/oxidized_backup \
  --check-config \
  --config /etc/check_mk/oxidized_backup.json

runuser -u oxidized -- \
  /usr/lib/check_mk_agent/plugins/300/oxidized_backup \
  --check-config \
  --config /etc/check_mk/oxidized_backup.json
```

Run the collector directly:

```bash
/usr/lib/check_mk_agent/plugins/300/oxidized_backup \
  --config /etc/check_mk/oxidized_backup.json
```

Confirm that the normal Checkmk agent includes the section:

```bash
check_mk_agent | sed -n '/<<<oxidized_backup/,/<<<<>>>>/p'
```

After Oxidized has completed at least one node job, confirm that the hook state exists:

```bash
stat /var/lib/oxidized/oxidized_backup/hook-state.json
```

### 8. Discover services — Checkmk server

On the Checkmk server or in the GUI:

1. Rediscover services on the Oxidized host and accept:
   - **Oxidized backup inventory**
   - **Oxidized Git repository**
   - **Oxidized Git remote synchronization**
2. Allow Checkmk to process the piggyback data.
3. Rediscover services on the devices contained in the Oxidized export and accept **Oxidized backup**.

CLI examples as the Checkmk site user:

```bash
cmk-validate-plugins
cmk -d oxidized-host
cmk-piggyback list sources
cmk -IIv oxidized-host switch-1
cmk -nv oxidized-host switch-1
```

Replace `oxidized-host` and `switch-1` with actual Checkmk host names. For SNMP-only switches, keep SNMP enabled and allow piggyback data from the Oxidized host. No Checkmk agent needs to run on the switches themselves.

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

Both must be absolute paths on the Oxidized host. State updates use file locks, temporary files, `fsync`, and atomic replacement. Existing state-file symlinks are refused.

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

## Troubleshooting by system

### Oxidized host

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

Check file ownership and state:

```bash
namei -l /etc/check_mk/oxidized_backup.json
namei -l /var/lib/oxidized/oxidized_backup
namei -l /var/lib/check_mk_agent/oxidized_backup
```

### Checkmk server

Confirm that the package files are installed:

```bash
find "$OMD_ROOT/local/share/check_mk/agents" \
  -maxdepth 2 -type f -name 'oxidized_backup*' -ls
```

Confirm piggyback sources and run the checks:

```bash
cmk-piggyback list sources
cmk -nv oxidized-host switch-1
```

## Upgrade

An MKP upgrade updates the Checkmk server only. Re-copy the packaged deployment files to the Oxidized host after enabling a newer package version.

Recommended sequence:

1. download and verify the new MKP;
2. install and enable it on the Checkmk server;
3. copy the new executable and both new templates to `/tmp/` on the Oxidized host;
4. replace the executable;
5. compare the current JSON configuration and active Oxidized hook with the new templates;
6. preserve environment-specific values instead of overwriting the live configuration;
7. rerun the validation commands;
8. restart Oxidized only when the hook changed.

Example comparison on the Oxidized host:

```bash
diff --unified \
  /etc/check_mk/oxidized_backup.json \
  /tmp/oxidized_backup.json || true

diff --unified \
  /etc/check_mk/oxidized_backup-hook.yml \
  /tmp/oxidized_backup-hook.yml || true
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

### Checkmk server

Disable and remove the MKP as the site user:

```bash
PACKAGE_VERSION=1.0.1
mkp disable oxidized_backup "${PACKAGE_VERSION}"
mkp remove oxidized_backup "${PACKAGE_VERSION}"
cmk -R
```

### Oxidized host

First remove the `checkmk_oxidized_backup_state` hook from the active Oxidized configuration and restart Oxidized. Then remove the deployed files and state:

```bash
rm -f /usr/lib/check_mk_agent/plugins/300/oxidized_backup
rm -f /etc/check_mk/oxidized_backup.json
rm -f /etc/check_mk/oxidized_backup-hook.yml
rm -rf /var/lib/check_mk_agent/oxidized_backup
rm -rf /var/lib/oxidized/oxidized_backup
```

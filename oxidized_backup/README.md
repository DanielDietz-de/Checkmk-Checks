# oxidized_backup

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p34-blue)
<!-- compatibility-badges:end -->

`oxidized_backup` is a Checkmk 2.4 extension that verifies the complete Oxidized backup chain for every device already exported by Checkmk to Oxidized.

The existing Checkmk Oxidized export remains the only source of truth. A device is expected to have a backup when it appears in that JSON export, for example because the Checkmk host tag `For_Oxidized` is set. The package does not implement a second tag filter, host list, folder rule, or hostname pattern.

The collector runs as a **Checkmk Linux agent plug-in on the Oxidized host**. It is not a server-side special agent. This placement gives it local, read-only access to the Oxidized Git repository while it emits central and piggyback sections for Checkmk.

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

A successful collection is not inferred from Git commit age. Oxidized does not create a new Git commit when a configuration is unchanged, so collection freshness and configuration-change history are treated separately.

## Services

Each device from the Checkmk Oxidized export receives:

- **Oxidized backup**

The Oxidized host receives:

- **Oxidized backup inventory**
- **Oxidized Git repository**
- **Oxidized Git remote synchronization**

Remote synchronization is intentionally a central service. A single unavailable Git remote must not create the same alert on every switch.

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

There are three distinct systems. Nothing is installed on the network devices.

| System | Responsibilities |
| --- | --- |
| **Checkmk server** | Install and enable the MKP. The MKP installs the Checkmk check plug-in, the Linux agent plug-in, and the two deployment templates. Service discovery and activation also happen here. |
| **Oxidized host** | Install the Linux agent plug-in copied from Checkmk, create and edit its configuration, create both state directories, merge the Oxidized hook, and run local validation. |
| **Network devices** | No files are installed. Devices receive piggyback services because they are present in the existing Checkmk Oxidized export. |

```text
Checkmk server
  ├── Checkmk check plug-in
  ├── Linux agent plug-in ────────────────────┐
  ├── JSON configuration template ────────────┤ copied once to
  └── Oxidized hook template ─────────────────┤ the Oxidized host
                                               ▼
Oxidized host
  ├── Checkmk Linux agent
  ├── oxidized_backup agent plug-in
  ├── /etc/check_mk/oxidized_backup.json
  ├── Oxidized exec hook
  ├── two persistent state directories
  ├── local Oxidized Git repository
  └── access to the configured Git remote
                                               │
                                               ▼
                                  central + piggyback sections
```

## Files delivered by the MKP

After the MKP is enabled, these files exist on the **Checkmk server** below the site directory:

| Source on the Checkmk server | Purpose | Destination on the Oxidized host |
| --- | --- | --- |
| `$OMD_ROOT/local/share/check_mk/agents/plugins/oxidized_backup` | Executable Linux agent plug-in and Oxidized hook-state recorder | `/usr/lib/check_mk_agent/plugins/300/oxidized_backup` |
| `$OMD_ROOT/local/lib/python3/cmk_addons/plugins/oxidized_backup/deployment/oxidized_backup.json` | Configuration template | `/etc/check_mk/oxidized_backup.json` |
| `$OMD_ROOT/local/lib/python3/cmk_addons/plugins/oxidized_backup/deployment/oxidized_backup-hook.yml` | Oxidized hook snippet; reference file only | Merge into the active Oxidized configuration |

The templates are deliberately packaged inside the Checkmk plug-in component rather than the MKP `agents` component. Checkmk's agent component is used only for the executable; the templates are still part of the same versioned MKP and are installed automatically with it.

Repository paths under `oxidized_backup/src/` are development sources. For a normal installation, use the files installed by the MKP so the server-side check, agent plug-in, and templates are all from the same package version.

## Requirements

### Checkmk server

- Checkmk 2.4
- permission to install and enable an MKP
- shell access as the Checkmk site user for command-line installation

The graphical MKP manager under **Setup > Maintenance > Extension packages** is available in Checkmk commercial editions. Checkmk Community users install the MKP with the `mkp` command.

### Oxidized host

- Linux Checkmk agent
- Python 3.11 or newer
- Git command-line client
- `runuser` when the Checkmk agent executes as root and Git must run as the unprivileged Oxidized account
- Oxidized web API available locally or over a trusted management network
- Oxidized Git output
- a Git remote that can be queried non-interactively by the Oxidized service account

The collector uses only Python's standard library. It does not require PyYAML, Requests, Rugged, or access to configuration file contents.

## Installation

Every step below states where it must be performed.

### 1. Download and verify the MKP — administrator workstation or Checkmk server

For a released package, download the MKP and checksum from the `oxidized_backup/` directory on the repository's `master` branch. Pull-request workflow artifacts are test builds, not the normal production source.

```bash
PACKAGE_VERSION=1.0.1
REPOSITORY_RAW=https://raw.githubusercontent.com/DanielDietz-de/Checkmk-Checks/master

curl --fail --location --remote-name \
  "${REPOSITORY_RAW}/oxidized_backup/oxidized_backup-${PACKAGE_VERSION}.mkp"
curl --fail --location --remote-name \
  "${REPOSITORY_RAW}/oxidized_backup/oxidized_backup-${PACKAGE_VERSION}.mkp.sha256"

sha256sum --check "oxidized_backup-${PACKAGE_VERSION}.mkp.sha256"
```

When downloading on an administrator workstation, copy the verified MKP to the Checkmk server:

```bash
scp "oxidized_backup-${PACKAGE_VERSION}.mkp" root@checkmk.example:/tmp/
```

Replace `checkmk.example` with the actual Checkmk server name.

### 2. Install and enable the MKP — Checkmk server

Use the graphical MKP manager in a commercial edition, or switch to the site user and use the CLI:

```bash
sudo --login --user cmk
PACKAGE_VERSION=1.0.1

mkp add "/tmp/oxidized_backup-${PACKAGE_VERSION}.mkp"
mkp enable oxidized_backup "${PACKAGE_VERSION}"
cmk -R
```

Replace `cmk` with the actual site name.

Confirm that the package installed all three deployment files:

```bash
test -x "$OMD_ROOT/local/share/check_mk/agents/plugins/oxidized_backup"
test -r "$OMD_ROOT/local/lib/python3/cmk_addons/plugins/oxidized_backup/deployment/oxidized_backup.json"
test -r "$OMD_ROOT/local/lib/python3/cmk_addons/plugins/oxidized_backup/deployment/oxidized_backup-hook.yml"
```

At this point the Checkmk check is installed, but the Oxidized host has not yet been changed.

### 3. Copy the packaged files — Checkmk server to Oxidized host

Run this on the **Checkmk server** as a user that can read the site files:

```bash
CHECKMK_SITE=cmk
OXIDIZED_HOST=oxidized.example
SITE_ROOT="/omd/sites/${CHECKMK_SITE}"
DEPLOYMENT_ROOT="${SITE_ROOT}/local/lib/python3/cmk_addons/plugins/oxidized_backup/deployment"

scp \
  "${SITE_ROOT}/local/share/check_mk/agents/plugins/oxidized_backup" \
  "${DEPLOYMENT_ROOT}/oxidized_backup.json" \
  "${DEPLOYMENT_ROOT}/oxidized_backup-hook.yml" \
  "root@${OXIDIZED_HOST}:/tmp/"
```

Replace `cmk` and `oxidized.example` with the actual site and host names.

Do not download an unrelated agent copy directly from another branch or commit. Copying the files installed by the MKP keeps both systems on the same version.

### 4. Install files and create state directories — Oxidized host

All commands in this step run as `root` on the **Oxidized host**.

Install the executable:

```bash
install -d -m 0755 /usr/lib/check_mk_agent/plugins/300
install -m 0755 \
  /tmp/oxidized_backup \
  /usr/lib/check_mk_agent/plugins/300/oxidized_backup
```

Install the configuration template and keep the hook template as an administrative reference:

```bash
install -d -m 0755 /etc/check_mk
install -m 0640 -o root -g oxidized \
  /tmp/oxidized_backup.json \
  /etc/check_mk/oxidized_backup.json
install -m 0644 -o root -g root \
  /tmp/oxidized_backup-hook.yml \
  /etc/check_mk/oxidized_backup-hook.yml
```

Create **both state directories on the Oxidized host**:

```bash
install -d -m 0750 -o oxidized -g oxidized \
  /var/lib/oxidized/oxidized_backup

install -d -m 0700 -o root -g root \
  /var/lib/check_mk_agent/oxidized_backup
```

The directories have different owners because different processes write them:

| Directory | Writer | Stored data |
| --- | --- | --- |
| `/var/lib/oxidized/oxidized_backup` | Oxidized service account | Persistent `node_success`, `node_fail`, and `post_store` hook state |
| `/var/lib/check_mk_agent/oxidized_backup` | Checkmk agent process, normally `root` | Remote mismatch history, last successful remote verification, and cached Git fsck state |

When the Oxidized service account or Checkmk agent execution user differs, adjust ownership accordingly. The JSON configuration must remain readable by both identities.

### 5. Configure the collector — Oxidized host

Edit the installed configuration:

```bash
editor /etc/check_mk/oxidized_backup.json
```

The template is deliberately non-functional until environment-specific values are confirmed:

| Setting | Required value |
| --- | --- |
| `inventory.url` | URL or local file URI of the existing Checkmk-generated `oxidized.json`. The request originates from the Oxidized host. |
| `oxidized.url` | Oxidized node API. `http://127.0.0.1:8888/nodes.json` is valid only when Oxidized Web listens there. |
| `state.hook_state_file` | Normally `/var/lib/oxidized/oxidized_backup/hook-state.json`. |
| `state.monitor_state_file` | Normally `/var/lib/check_mk_agent/oxidized_backup/monitor-state.json`. |
| `git.run_as_user` | Unprivileged account that can read the Oxidized repository and authenticate to its remote. |
| `git.repositories[].path` | Actual local bare or non-bare Oxidized Git repository. |
| `git.repositories[].groups` | Oxidized groups handled by that repository. |
| `git.repositories[].single_repo` | `true` when grouped nodes are stored as `group/name`; otherwise `false`. |
| `git.repositories[].remote` | Git remote name, normally `origin`. |
| `git.repositories[].branch` | Remote branch to verify, for example `main`. |
| `policy.*` | Thresholds suitable for the complete Oxidized polling cycle and acceptable remote-verification age. |

Do not retain the example URL, repository path, branch, or thresholds without validating them.

Protect the configuration while keeping it readable by the Oxidized service account:

```bash
chown root:oxidized /etc/check_mk/oxidized_backup.json
chmod 0640 /etc/check_mk/oxidized_backup.json
```

### 6. Merge the Oxidized hook — Oxidized host

`/etc/check_mk/oxidized_backup-hook.yml` is a **snippet**, not a second Oxidized configuration file.

A typical service-account installation uses this active Oxidized configuration:

```text
/home/oxidized/.config/oxidized/config
```

The actual path depends on the service unit. Confirm it before editing:

```bash
systemctl cat oxidized
```

Review the packaged snippet:

```bash
cat /etc/check_mk/oxidized_backup-hook.yml
```

Merge the nested `checkmk_oxidized_backup_state` entry into the existing `hooks:` mapping of the active Oxidized configuration.

Important:

- when `hooks:` already exists, add only the nested hook entry;
- do not create a second top-level `hooks:` key;
- keep the executable and configuration paths aligned with the files installed above;
- preserve unrelated existing hooks.

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

After Oxidized completes at least one node job, confirm that hook state exists:

```bash
stat /var/lib/oxidized/oxidized_backup/hook-state.json
```

### 8. Discover services — Checkmk server

On the Checkmk server or in the GUI:

1. rediscover services on the Oxidized host and accept:
   - **Oxidized backup inventory**
   - **Oxidized Git repository**
   - **Oxidized Git remote synchronization**
2. allow Checkmk to process the piggyback data;
3. rediscover services on devices contained in the Oxidized export and accept **Oxidized backup**.

CLI examples as the Checkmk site user:

```bash
cmk-validate-plugins
cmk -d oxidized-host
cmk-piggyback list sources
cmk -IIv oxidized-host switch-1
cmk -nv oxidized-host switch-1
```

Replace `oxidized-host` and `switch-1` with actual Checkmk host names. For SNMP-only switches, keep SNMP enabled and permit piggyback data from the Oxidized host. No Checkmk agent runs on the switches.

## Configuration reference

### `inventory`

The existing Checkmk-generated JSON source. The expected schema is the schema already supplied to Oxidized:

```json
[
  {"hostname": "switch-1", "os": "picos"},
  {"hostname": "switch-2", "os": "aoscx"}
]
```

Required:

- `url`: `https://`, `http://`, or `file://` URL

Optional bounded transport settings:

- `timeout_seconds`: 0.1 to 120 seconds
- `max_response_bytes`: 1 KiB to 64 MiB
- `ca_file`: absolute CA bundle path for HTTPS
- `allow_insecure_http`: must be explicitly `true` for non-loopback cleartext HTTP
- `auth`: optional bearer or basic authentication using a secret file

Credentials embedded in a URL are rejected.

### `oxidized`

The Oxidized node API, normally the local `/nodes.json` endpoint. The same transport and authentication settings as `inventory` are supported, except `file://` is not accepted.

Loopback HTTP is allowed without the non-loopback cleartext opt-in.

### `state`

- `hook_state_file`: persistent state written by the Oxidized service account
- `monitor_state_file`: remote mismatch, last synchronization, and fsck state written by the Checkmk agent

Both are absolute paths on the Oxidized host. State updates use file locks, temporary files, `fsync`, and atomic replacement. Existing state-file symlinks are refused.

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
- `fsck_timeout_seconds`: optional, 1 to 3600 seconds

The remote is queried as `git.run_as_user` with `GIT_TERMINAL_PROMPT=0`. Configure SSH keys, `known_hosts`, or a non-interactive credential helper for that account. Do not put tokens or passwords in this JSON file.

### `policy`

All values are required:

- `collection_warning_age_seconds`
- `collection_critical_age_seconds`
- `remote_sync_grace_seconds`
- `remote_verification_max_age_seconds`
- `fsck_interval_seconds`, minimum 300
- `orphan_state`
  - `0`: OK
  - `1`: WARN
  - `2`: CRIT

The critical collection age must be greater than the warning age. Choose thresholds based on the complete Oxidized cycle duration, including node count, thread count, retries, device timeouts, and polling interval.

## Multiple Git repositories and groups

### One repository for all groups

```json
{
  "id": "all-devices",
  "path": "/var/lib/oxidized/oxidized.git",
  "groups": ["*"],
  "single_repo": true
}
```

Expected tree paths:

```text
switch-1
switches/switch-2
routers/router-1
```

### Separate repository per group

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

## Troubleshooting

### Oxidized host

Verify the local Git branch and a device path without reading configuration contents:

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

Check ownership and path traversal:

```bash
namei -l /etc/check_mk/oxidized_backup.json
namei -l /var/lib/oxidized/oxidized_backup
namei -l /var/lib/check_mk_agent/oxidized_backup
```

### Checkmk server

Confirm all package files:

```bash
mkp files oxidized_backup 1.0.1

test -x "$OMD_ROOT/local/share/check_mk/agents/plugins/oxidized_backup"
test -r "$OMD_ROOT/local/lib/python3/cmk_addons/plugins/oxidized_backup/deployment/oxidized_backup.json"
test -r "$OMD_ROOT/local/lib/python3/cmk_addons/plugins/oxidized_backup/deployment/oxidized_backup-hook.yml"
```

Confirm piggyback sources and execute checks:

```bash
cmk-piggyback list sources
cmk -nv oxidized-host switch-1
```

## Upgrade

An MKP upgrade changes the Checkmk server only. Re-copy the agent executable and compare the two newly installed templates with the live Oxidized-host files after enabling a newer package.

Recommended sequence:

1. download and verify the new MKP;
2. install and enable it on Checkmk;
3. copy the new executable and templates from the new MKP installation to `/tmp/` on the Oxidized host;
4. replace the executable;
5. compare the current JSON configuration and active hook with the new templates;
6. preserve environment-specific values instead of overwriting the live configuration;
7. rerun validation;
8. restart Oxidized only when the hook changed.

Example comparisons on the Oxidized host:

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
- node names are validated before use in piggyback markers or Git tree paths;
- state files use locking and atomic replacement;
- repository checks do not modify the local branch, working tree, or remote-tracking refs.

## Operational notes

- The collector uses `git ls-remote`, not a local remote-tracking branch, to verify the actual remote branch.
- A short mismatch grace period prevents alerts while the Oxidized `post_store` hook is still pushing a commit.
- The full connectivity fsck runs only at the configured interval and persists its result between agent runs.
- Removing `For_Oxidized` removes the device from the authoritative export. Its piggyback section stops and the service becomes vanished through normal Checkmk discovery handling.
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

First remove `checkmk_oxidized_backup_state` from the active Oxidized configuration and restart Oxidized. Then remove the deployed files and state:

```bash
rm -f /usr/lib/check_mk_agent/plugins/300/oxidized_backup
rm -f /etc/check_mk/oxidized_backup.json
rm -f /etc/check_mk/oxidized_backup-hook.yml
rm -rf /var/lib/check_mk_agent/oxidized_backup
rm -rf /var/lib/oxidized/oxidized_backup
```

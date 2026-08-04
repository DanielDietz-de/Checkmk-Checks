# oxidized_backup

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p34-blue)
<!-- compatibility-badges:end -->

`oxidized_backup` is a Checkmk 2.4 extension that verifies the complete Oxidized backup chain for every device already exported by Checkmk to Oxidized.

The existing Checkmk-generated Oxidized JSON remains the sole device inventory. A device is expected to have a backup when it appears in that export, for example because the Checkmk host tag `For_Oxidized` is set. The package does not implement a second device list, folder rule, naming pattern, or tag condition.

The collector runs as a Linux Checkmk agent plug-in on the Oxidized host and emits:

- central services for the Oxidized host;
- one piggyback section for every unique device in the existing Oxidized export.

## What is verified

For every expected device:

1. the node is loaded by Oxidized;
2. the latest completed collection succeeded and is recent enough;
3. a non-empty configuration blob exists at the expected path in the local Oxidized Git repository.

On the Oxidized host:

1. Checkmk's expected inventory reconciles with the nodes loaded by Oxidized;
2. configured local Git repositories are valid and contain every expected artifact;
3. periodic `git fsck --connectivity-only --no-dangling` checks succeed;
4. every local repository `HEAD` equals the configured remote branch `HEAD` returned by `git ls-remote`.

Collection freshness is not inferred from Git commit age. Oxidized creates no new Git commit when a configuration is unchanged, so collection success and configuration changes are tracked separately.

## Services

Each exported device receives:

- **Oxidized backup**

The Oxidized host receives:

- **Oxidized backup inventory**
- **Oxidized Git repository**
- **Oxidized Git remote synchronization**

Remote synchronization is deliberately central. One unavailable Git remote must not create the same alert on every switch.

## State model

### Per-device service

| Condition | State |
| --- | --- |
| Recent successful collection and non-empty local Git blob | OK |
| Successful collection older than the warning age | WARN |
| Successful collection older than the critical age | CRIT |
| Node missing from Oxidized | CRIT |
| Latest collection is `never`, `no_connection`, `timelimit`, or failed | CRIT |
| Local Git artifact missing or empty | CRIT |
| Oxidized API unavailable | UNKNOWN; local Git verification is still reported |
| Duplicate or ambiguous identity | UNKNOWN |
| No unique repository mapping | UNKNOWN |

### Central repository services

| Condition | State |
| --- | --- |
| Repository valid, all artifacts present, fsck successful | OK |
| Local and remote `HEAD` identical | OK |
| Different `HEAD` values within the synchronization grace period | WARN |
| Different `HEAD` values beyond the grace period | CRIT |
| Authentication rejected, remote missing, or branch missing | CRIT |
| Temporary remote outage with a recent successful verification | WARN |
| Remote outage beyond the maximum verification age | CRIT |
| Remote unavailable without any prior verification | UNKNOWN |
| Local repository missing, invalid, or unreadable | CRIT |
| Monitor state cannot be read or persisted | UNKNOWN |

## Deployment choices

| Environment | Recommended deployment |
| --- | --- |
| Checkmk commercial edition with Agent Updater | Configure the Bakery rule, bake an agent, and let Agent Updater transfer and install it automatically. |
| Checkmk commercial edition without Agent Updater | Configure the Bakery rule, bake the host-specific DEB/RPM package, then download and install that package manually on the Oxidized host. |
| Checkmk Raw/Community | Install the MKP server-side and use the manual deployment procedure in this document. |

Agent Bakery is the primary path because it keeps the executable, generated configuration, execution interval, permissions, state-directory scriptlets, and upgrades in one host-specific agent package.

The active Oxidized YAML configuration is never rewritten automatically. Bakery deploys a hook reference file, but an administrator must merge the hook into the active Oxidized configuration once and review future hook changes deliberately.

## Files managed by Agent Bakery

With the standard Linux agent paths, a baked DEB/RPM package installs:

| File | Purpose | Access model |
| --- | --- | --- |
| `/usr/lib/check_mk_agent/plugins/<interval>/oxidized_backup` | Cached or synchronous Checkmk agent plug-in | Executable by the Checkmk agent. A 300-second rule produces `plugins/300/oxidized_backup`. |
| `/usr/bin/oxidized_backup_hook` | Stable executable used by the Oxidized exec hook | Executable by the Oxidized service account. |
| `/etc/check_mk/oxidized_backup.json` | JSON generated from the Bakery rule | `root:<Oxidized primary group>`, mode `0640`. Read by the root-run Checkmk agent and the unprivileged Oxidized hook. |
| `/etc/check_mk/oxidized_backup-hook.yml` | Reference hook snippet generated by Bakery | Administrative reference only; it is not the active Oxidized configuration. |
| configured hook-state directory | Persistent Oxidized collection state | Written by the Oxidized service account. |
| configured monitor-state directory | Remote and repository verification state | Written by the Checkmk agent, normally as root. |

The DEB and RPM post-install scriptlets resolve the primary group of the account configured as **Oxidized service account** and reapply the JSON ownership and mode after every installation or upgrade. The scriptlet refuses to change a missing or symbolic-link configuration path. If the configured account does not exist during installation, the package emits a warning and leaves the configuration unchanged.

The system binary directory can be customized in Checkmk. When it is not `/usr/bin`, adapt the executable path in the active Oxidized hook to the actual Bakery-managed binary location.

## Requirements

### Checkmk server

- Checkmk 2.4;
- permission to install and enable an MKP;
- a commercial edition for Agent Bakery and Agent Updater deployment;
- a configured signing key when signed agent packages are required.

### Oxidized host

- Linux Checkmk agent;
- Python 3.11 or newer;
- Git command-line client;
- `runuser` when the agent executes as root and Git must run as the unprivileged Oxidized account;
- Oxidized web API available locally or over a trusted management network;
- Oxidized Git output;
- non-interactive Git remote access for the Oxidized service account.

The collector uses only Python's standard library. It does not require Requests, PyYAML, or Rugged and never reads configuration blob contents.

# Installation with Agent Bakery

## 1. Install the MKP — Checkmk server

Download the released package and checksum from the `oxidized_backup/` directory on `master`:

```bash
PACKAGE_VERSION=1.1.1
REPOSITORY_RAW=https://raw.githubusercontent.com/DanielDietz-de/Checkmk-Checks/master

curl --fail --location --remote-name \
  "${REPOSITORY_RAW}/oxidized_backup/oxidized_backup-${PACKAGE_VERSION}.mkp"
curl --fail --location --remote-name \
  "${REPOSITORY_RAW}/oxidized_backup/oxidized_backup-${PACKAGE_VERSION}.mkp.sha256"

sha256sum --check "oxidized_backup-${PACKAGE_VERSION}.mkp.sha256"
```

Install the MKP through **Setup > Maintenance > Extension packages**, or as the Checkmk site user:

```bash
mkp add "/path/to/oxidized_backup-${PACKAGE_VERSION}.mkp"
mkp enable oxidized_backup "${PACKAGE_VERSION}"
cmk -R
```

The MKP installs:

- the agent-based check and manual;
- the Bakery rule;
- the Bakery implementation;
- the Linux agent source;
- generic JSON and hook templates used by the manual fallback.

## 2. Create the Bakery rule — Checkmk server

Open:

**Setup > Agents > Agent rules > Oxidized backup verification**

Create a rule that applies **only to the Checkmk host representing the Oxidized server**.

Configure:

| Rule section | Required values |
| --- | --- |
| Deployment | Prefer cached execution. Five minutes is the recommended starting interval. |
| Existing Checkmk Oxidized export | URL or local file URI of the existing generated `oxidized.json`. The request originates on the Oxidized host. |
| Oxidized node API | Normally a loopback `/nodes.json` endpoint such as `http://127.0.0.1:8888/nodes.json`. |
| Persistent state | Absolute paths for hook state and monitor state. |
| Oxidized Git storage | Oxidized account, Git executable, local repositories, groups, remote, branch, and timeouts. |
| Monitoring policy | Collection ages, remote synchronization grace, maximum verification age, fsck interval, and orphan state. |

The configured **Oxidized service account** serves two purposes:

- all Git commands run under that unprivileged identity;
- its primary group receives read access to `/etc/check_mk/oxidized_backup.json` during DEB/RPM installation.

Authentication values reference existing secret files on the Oxidized host. Passwords and bearer tokens are not stored in the Bakery rule or generated JSON.

Repository group mappings have the following meanings:

- **Ungrouped/default nodes** produces `null` in the collector configuration;
- **Named Oxidized group** maps exactly one group;
- **Fallback for all other groups** produces `"*"` and may be used by only one repository.

## 3. Bake the agent — Checkmk server

In the GUI, open **Setup > Agents > Windows, Linux, Solaris, AIX > Agent Bakery**, then bake and sign the agent packages.

A host-specific command-line bake can also be triggered as the site user:

```bash
cmk -Av oxidized-host
```

Replace `oxidized-host` with the Checkmk host name of the Oxidized server.

## 4. Transfer and install the baked package

### With Agent Updater

Register the Agent Updater on the Oxidized host and assign the normal Agent Updater rules. It downloads and installs the applicable baked package when its agent configuration hash changes.

### Without Agent Updater

Download the host-specific DEB or RPM from the Agent Bakery and install it with the operating-system package manager:

```bash
# Debian or Ubuntu
dpkg -i check-mk-agent_*.deb

# RHEL-family systems
rpm -U check-mk-agent-*.rpm
```

Use the package generated for the Oxidized host so its Bakery rule is included.

## 5. Verify Bakery-managed files and permissions — Oxidized host

```bash
for file in \
  /usr/bin/oxidized_backup_hook \
  /etc/check_mk/oxidized_backup.json \
  /etc/check_mk/oxidized_backup-hook.yml
do
  if [ -e "$file" ]; then
    stat -c 'OK: %A %a %U:%G %n' "$file"
  else
    echo "MISSING: $file"
  fi
done

find /usr/lib/check_mk_agent/plugins -type f -name oxidized_backup -ls
namei -l /var/lib/oxidized/oxidized_backup
namei -l /var/lib/check_mk_agent/oxidized_backup
```

Expected defaults:

| Path | Writer or reader | Ownership and mode |
| --- | --- | --- |
| `/etc/check_mk/oxidized_backup.json` | root-run Checkmk agent and Oxidized hook | `root:<Oxidized primary group>`, `0640` |
| `/var/lib/oxidized/oxidized_backup` | Oxidized exec hook | `<Oxidized user>:<primary group>`, `0750` |
| `/var/lib/check_mk_agent/oxidized_backup` | Checkmk agent plug-in | `root:root`, `0700` |

A configuration owned by `root:root` with mode `0640` is incorrect for the hook: the Oxidized service account cannot read it. Reinstalling or upgrading package version 1.1.1 or newer reapplies the correct group automatically.

Tarball-based or manual installations do not execute DEB/RPM scriptlets; use the manual permission commands below.

## 6. Merge the Oxidized hook — Oxidized host

Review the Bakery-managed reference:

```bash
cat /etc/check_mk/oxidized_backup-hook.yml
```

A typical generated snippet is:

```yaml
hooks:
  checkmk_oxidized_backup_state:
    type: exec
    events:
      - node_success
      - node_fail
      - post_store
    cmd: >-
      /usr/bin/oxidized_backup_hook
      --record-hook
      --config /etc/check_mk/oxidized_backup.json
    timeout: 10
    async: false
```

Find the active Oxidized configuration from the service definition:

```bash
systemctl cat oxidized
```

Merge only `checkmk_oxidized_backup_state` into the existing `hooks:` mapping. Do not create a second top-level `hooks:` key and do not replace other hooks.

Restart and inspect Oxidized:

```bash
systemctl restart oxidized
systemctl --no-pager --full status oxidized
journalctl --unit oxidized --since "-5 minutes" --no-pager
```

## 7. Validate the Oxidized host

Validate the Bakery-generated configuration as root and as the configured Oxidized account:

```bash
/usr/bin/oxidized_backup_hook \
  --check-config \
  --config /etc/check_mk/oxidized_backup.json

runuser -u oxidized -- \
  /usr/bin/oxidized_backup_hook \
  --check-config \
  --config /etc/check_mk/oxidized_backup.json
```

Both commands must succeed. A permission error from the second command means the generated JSON does not have the required group ownership or a parent directory blocks traversal.

Run the collector directly:

```bash
/usr/bin/oxidized_backup_hook \
  --config /etc/check_mk/oxidized_backup.json
```

Confirm that the normal Checkmk agent contains the section:

```bash
check_mk_agent | sed -n '/<<<oxidized_backup/,/<<<<>>>>/p'
```

After Oxidized completes at least one node job:

```bash
stat /var/lib/oxidized/oxidized_backup/hook-state.json
```

## 8. Discover services — Checkmk server

Rediscover the Oxidized host and accept:

- **Oxidized backup inventory**
- **Oxidized Git repository**
- **Oxidized Git remote synchronization**

Then let Checkmk process the piggyback data and rediscover each device in the existing Oxidized export to accept **Oxidized backup**.

CLI examples:

```bash
cmk-validate-plugins
cmk -d oxidized-host
cmk-piggyback list sources
cmk -IIv oxidized-host switch-1
cmk -nv oxidized-host switch-1
```

No Checkmk agent is installed on the switches. Existing SNMP monitoring remains unchanged.

# Manual fallback for Raw/Community or tarball agents

The enabled MKP places version-matched source files on the Checkmk server:

```text
$OMD_ROOT/local/share/check_mk/agents/plugins/oxidized_backup
$OMD_ROOT/local/lib/python3/cmk_addons/plugins/oxidized_backup/deployment/oxidized_backup.json
$OMD_ROOT/local/lib/python3/cmk_addons/plugins/oxidized_backup/deployment/oxidized_backup-hook.yml
```

Copy them to `/tmp/` on the Oxidized host. Then run as root, replacing `oxidized` when a different service account is configured:

```bash
OXIDIZED_USER=oxidized
OXIDIZED_GROUP=$(id -gn "$OXIDIZED_USER")

install -d -m 0755 /usr/lib/check_mk_agent/plugins/300
install -m 0755 /tmp/oxidized_backup \
  /usr/lib/check_mk_agent/plugins/300/oxidized_backup
install -m 0755 /tmp/oxidized_backup \
  /usr/bin/oxidized_backup_hook

install -d -m 0755 /etc/check_mk
install -m 0640 -o root -g "$OXIDIZED_GROUP" \
  /tmp/oxidized_backup.json \
  /etc/check_mk/oxidized_backup.json
install -m 0644 -o root -g root \
  /tmp/oxidized_backup-hook.yml \
  /etc/check_mk/oxidized_backup-hook.yml

install -d -m 0750 -o "$OXIDIZED_USER" -g "$OXIDIZED_GROUP" \
  /var/lib/oxidized/oxidized_backup
install -d -m 0700 -o root -g root \
  /var/lib/check_mk_agent/oxidized_backup
```

Edit `/etc/check_mk/oxidized_backup.json`, merge the hook, and use the same validation and discovery steps described above.

The manual JSON is only a template. Replace all example URLs, paths, branch names, and thresholds with real environment values.

# Configuration reference

## `inventory` and `oxidized`

Both support bounded HTTP requests with:

- `url`;
- `timeout_seconds`;
- `max_response_bytes`;
- optional `ca_file`;
- optional explicit `allow_insecure_http`;
- optional bearer or basic authentication through protected secret files.

The inventory source additionally supports `file://`. Credentials embedded in URLs are rejected.

## `state`

- `hook_state_file` is written by the Oxidized service account;
- `monitor_state_file` is written by the Checkmk agent process.

Both must be absolute paths on the Oxidized host. Updates use locking, temporary files, `fsync`, and atomic replacement. Existing state-file symlinks are refused.

## `git`

- `run_as_user`: required unprivileged account used for Git operations and for deriving the group that may read the generated JSON;
- `git_binary`: absolute Git executable;
- `repositories`: one or more repository mappings.

Repository fields:

- `id`: stable identifier;
- `path`: local bare or non-bare Git repository;
- `groups`: ungrouped, named, or one wildcard fallback;
- `single_repo`: whether grouped files use `group/name` paths;
- `remote`: normally `origin`;
- `branch`: explicit branch or the repository's symbolic `HEAD` when omitted;
- command and fsck timeouts.

Git is executed as `run_as_user` with `GIT_TERMINAL_PROMPT=0`. Configure SSH keys, `known_hosts`, TLS trust, or a non-interactive credential helper for that account. Do not store Git passwords or tokens in the Bakery rule.

## `policy`

- collection warning and critical ages;
- remote synchronization grace period;
- maximum age of a previously successful remote verification;
- Git fsck interval, minimum 300 seconds;
- state for orphaned Oxidized nodes.

The critical collection age must be greater than the warning age. Set both according to the full Oxidized polling cycle, including node count, threads, retries, and device timeouts.

# Troubleshooting

## Oxidized host

Check the generated files and permissions:

```bash
stat -c '%A %a %U:%G %n' \
  /usr/bin/oxidized_backup_hook \
  /etc/check_mk/oxidized_backup.json \
  /etc/check_mk/oxidized_backup-hook.yml

namei -l /etc/check_mk/oxidized_backup.json
```

Confirm that the configured account can read and validate the JSON:

```bash
runuser -u oxidized -- \
  /usr/bin/oxidized_backup_hook \
  --check-config \
  --config /etc/check_mk/oxidized_backup.json
```

For a one-time repair before package 1.1.1 is deployed:

```bash
OXIDIZED_USER=oxidized
OXIDIZED_GROUP=$(id -gn "$OXIDIZED_USER")
chown root:"$OXIDIZED_GROUP" /etc/check_mk/oxidized_backup.json
chmod 0640 /etc/check_mk/oxidized_backup.json
```

Verify the local Git repository without reading configuration contents:

```bash
runuser -u oxidized -- \
  git -C /var/lib/oxidized/oxidized.git rev-parse HEAD
runuser -u oxidized -- \
  git -C /var/lib/oxidized/oxidized.git cat-file -e 'HEAD:switch-1'
```

Verify actual remote access under the same identity:

```bash
runuser -u oxidized -- \
  env GIT_TERMINAL_PROMPT=0 \
  git -C /var/lib/oxidized/oxidized.git \
  ls-remote --exit-code origin refs/heads/main
```

## Checkmk server

Confirm the MKP contents:

```bash
mkp show oxidized_backup
cmk-validate-plugins
```

Force a rebake after changing the rule:

```bash
cmk -Av oxidized-host
```

Inspect piggyback data and check results:

```bash
cmk-piggyback list sources
cmk -nv oxidized-host switch-1
```

# Upgrade

For Bakery-managed installations:

1. install and enable the newer MKP;
2. review changes to the Bakery rule and reference hook;
3. bake a new agent package;
4. let Agent Updater install it, or install the baked package manually;
5. verify that `/etc/check_mk/oxidized_backup.json` is `root:<Oxidized primary group>` with mode `0640`;
6. merge the hook only when its generated content changed;
7. repeat local validation and service checks.

The generated JSON is replaced by the baked agent package. Store all environment-specific collector settings in the Bakery rule, not by editing the generated file.

# Removal

Remove the `checkmk_oxidized_backup_state` hook from the active Oxidized configuration first and restart Oxidized.

Disable or delete the Bakery rule, bake a new agent, and deploy it so the Bakery-managed files are removed from the host. Persistent state directories are intentionally not deleted automatically.

After confirming they are no longer needed:

```bash
rm -rf /var/lib/check_mk_agent/oxidized_backup
rm -rf /var/lib/oxidized/oxidized_backup
```

Disable and remove the MKP on the Checkmk server:

```bash
mkp disable oxidized_backup 1.1.1
mkp remove oxidized_backup 1.1.1
cmk -R
```

# Security properties

- subprocesses use explicit argument arrays; no shell is invoked by the collector;
- Git runs as the configured unprivileged Oxidized account;
- `GIT_TERMINAL_PROMPT=0` prevents blocked prompts;
- configuration blob contents are never read or returned;
- HTTPS certificate verification is enabled and supports a custom CA bundle;
- cross-origin redirects and HTTPS downgrade redirects are refused;
- non-loopback cleartext HTTP requires explicit opt-in;
- HTTP responses, files, and command execution have explicit limits;
- secret files must be regular files without group or other permissions;
- credentials embedded in URLs are rejected;
- errors are bounded and redact credential-like values;
- node names are validated before piggyback and Git-path use;
- state files use locks and atomic replacement;
- Bakery scriptlets refuse to change a symbolic-link configuration path;
- repository checks do not fetch, merge, push, repair, or modify local refs.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `oxidized_backup` version `1.1.1`; minimum Checkmk version `2.4.0b1`; maximum asserted version: 2.5.99.
- Canonical manifest: `oxidized_backup/src/info`; it declares 8 packaged files.
- Repository MKP artifacts present: `oxidized_backup-1.0.0.mkp`, `oxidized_backup-1.0.1.mkp`, `oxidized_backup-1.1.0.mkp`, `oxidized_backup-1.1.1.mkp`.
- Checksum files present: `oxidized_backup-1.0.0.mkp.sha256`, `oxidized_backup-1.0.1.mkp.sha256`, `oxidized_backup-1.1.0.mkp.sha256`, `oxidized_backup-1.1.1.mkp.sha256`.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/oxidized_backup/agent_based/oxidized_backup.py`.
- **Rulesets:** `src/oxidized_backup/rulesets/ruleset_oxidized_backup_bakery.py`.
- **Bakery:** `src/lib/python3/cmk/base/cee/plugins/bakery/oxidized_backup.py`.
- **Check manuals:** `src/oxidized_backup/checkman/oxidized_backup`.
- **Other packaged source:** `src/agents/plugins/oxidized_backup`, `src/oxidized_backup/bakery_common.py`, `src/oxidized_backup/deployment/oxidized_backup-hook.yml`, `src/oxidized_backup/deployment/oxidized_backup.json`.
- Registered check plug-in names: `oxidized_backup`.

### Validation

- Package-specific tests: `tests/test_agent_oxidized_backup.py`, `tests/test_bakery_common.py`, `tests/test_bakery_module.py`, `tests/test_examples.py`, `tests/test_mkp_builder.py`, `tests/test_oxidized_backup_check_plugin.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.

### Troubleshooting

- Emitted Checkmk sections detected in source: `oxidized_backup`.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->

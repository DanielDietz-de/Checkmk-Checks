# Net Backup Checks

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

Monitors the status of tape drives / devices managed by Veritas
NetBackup on the media server by parsing `vmoprcmd` output. One service
per NetBackup device is created and goes CRIT if any drive on that
device reports a status other than `SCAN-TLD`, `TLD` or `ACTIVE`.

## How it works

The agent plugin runs `/usr/openv/volmgr/bin/vmoprcmd` on the media
server and prints its output under the `<<<net_backup>>>` section. The
legacy check plugin parses the `Host / DrivePath / Status` table,
groups rows by device, and reports client, path and status for each
drive.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/agents/plugins/net_backup.sh` | Bash agent plugin (runs `vmoprcmd`). |
| `src/agents/bakery/net_backup` | Agent Bakery hook. |
| `src/checks/net_backup` | Legacy check plugin (`check_info["net_backup"]`). |
| `src/web/plugins/wato/net_backup.py` | WATO rule `agent_config:net_backup` for the Bakery. |

## Installation

1. Install the MKP on the Checkmk site.
2. Deploy the agent plugin:
   - **With Bakery:** enable the rule *Netbackup Monitoring (Linux)*
     and bake the agent.
   - **Manually:** copy `src/agents/plugins/net_backup.sh` to
     `/usr/lib/check_mk_agent/plugins/` on the NetBackup media server
     and make it executable. `/usr/openv/volmgr/bin/vmoprcmd` must be
     runnable by the Checkmk agent user.
3. Run service discovery.

## Services & metrics

- **Service:** `Device <device>` (one per NetBackup device).
- **State logic:** CRIT if any drive on the device has a status other
  than `SCAN-TLD`, `TLD` or `ACTIVE`, otherwise OK. No metrics.

## Known limitations

- Uses the legacy `check_info` API and the legacy `register_rule` WATO
  API. Functional on Checkmk 2.x as long as the legacy APIs are
  available.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `net_backup` version `2.0.1`; minimum Checkmk version `2.4.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `net_backup/src/info`; it declares 4 packaged files.
- Repository MKP artifacts present: `net_backup-1.0.0.mkp`, `net_backup-1.0.1.mkp`, `net_backup-1.0.2.mkp`, `net_backup-1.0.mkp`, `net_backup-2.0.0.mkp`, `net_backup-2.0.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/net_backup/agent_based/net_backup.py`.
- **Bakery:** `src/agents/bakery/net_backup`.
- **Check manuals:** `src/net_backup/checkman/net_backup`.
- **Other packaged source:** `src/agents/plugins/net_backup.sh`.
- Registered check plug-in names: `net_backup`.

### Validation

- Package-specific tests: `tests/test_net_backup_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- No direct remote-network client was detected in the current source.

### Troubleshooting

- Emitted Checkmk sections detected in source: `net_backup`.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->

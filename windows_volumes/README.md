# Windows Volumes (folder mount points)

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.3.0p1-blue)
<!-- compatibility-badges:end -->

Monitors Windows volumes that are mounted into a **folder** instead of a drive letter — for example data/log/backup volumes of a database server that are mounted under `C:\Mounts\...`.

## How it works

The agent plug-in (`agents/plugins/windows_volumes.ps1`) runs `Get-Partition` / `Get-Volume` and emits one line per folder mounted volume under the `<<<windows_volumes:sep(124)>>>` section. Filtered out are:

- plain drive letter roots (`C:\`, `D:\`),
- raw volume GUID paths (`\\?\Volume{...}\`),
- volumes without a usable filesystem or size (Recovery, EFI, …).

The plug-in can be rolled out through the **agent bakery** (synchronous, asynchronous/cached, or not deployed).

For every reported volume the check creates one service:

- **Health:** `HealthStatus` and `OperationalStatus` are evaluated — anything that is not `Healthy` / `OK` becomes `CRIT`.
- **Usage:** filesystem fill level is checked against upper levels in percent, configurable via the dedicated rule **Windows Volumes (folder mount points)** (default WARN/CRIT at 80%/90%).
- **Graph:** used space, total size and used percentage are exported as metrics and rendered as a graph and perfometer.

The service item is the volume label (FriendlyName). If a label appears more than once (a volume mounted into several folders), the repeated items are numbered (`<label>`, `<label> 2`, …).

## Package contents

| Path | Purpose |
| --- | --- |
| `src/agents/plugins/windows_volumes.ps1` | Windows agent plug-in (PowerShell). |
| `src/windows_volumes/agent_based/windows_volumes.py` | Section parser and check plug-in. |
| `src/windows_volumes/agent_based/bakery.py` | Agent bakery plug-in (deploys the PowerShell script). |
| `src/windows_volumes/rulesets/bakery.py` | Agent bakery rule (deployment type). |
| `src/windows_volumes/rulesets/check_parameters.py` | Check parameter rule (usage levels). |
| `src/windows_volumes/graphing/metrics.py` | Metrics, perfometer and graph definitions. |
| `src/windows_volumes/checkman/windows_volumes` | Check manual page. |

## Configuration

- **Deployment:** Setup → Agents → Windows, Linux, … → *Windows Volumes (folder mount points)*
- **Levels:** Setup → Service monitoring rules → *Windows Volumes (folder mount points)* (default WARN/CRIT at 80%/90%).

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `windows_volumes` version `1.0.0`; minimum Checkmk version `2.3.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `windows_volumes/src/info`; it declares 7 packaged files.
- Repository MKP artifacts present: `windows_volumes-1.0.0.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/windows_volumes/agent_based/bakery.py`, `src/windows_volumes/agent_based/windows_volumes.py`.
- **Rulesets:** `src/windows_volumes/rulesets/bakery.py`, `src/windows_volumes/rulesets/check_parameters.py`.
- **Graphing:** `src/windows_volumes/graphing/metrics.py`.
- **Check manuals:** `src/windows_volumes/checkman/windows_volumes`.
- **Other packaged source:** `src/agents/plugins/windows_volumes.ps1`.
- Registered check plug-in names: `windows_volumes`.

### Validation

- Package-specific tests: `tests/test_windows_volumes_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- No direct remote-network client was detected in the current source.

### Troubleshooting

- Emitted Checkmk sections detected in source: `windows_volumes`.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->

# NFS Filesystem Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p7-blue)
<!-- compatibility-badges:end -->

Adds NFS mount points to Checkmk filesystem monitoring on Linux hosts.
The stock Linux agent ignores NFS mounts for `df`; this plugin ships a
tiny agent-side script that enumerates NFS mounts with `df -PTk` and
re-emits them as a `df` section so they are picked up by the regular
filesystem check.

## How it works

1. The agent plugin `nfs_df` runs `df -PTk` (wrapped in `waitmax -s 9
   2` to avoid hangs on stuck NFS mounts), filters for the `nfs` fs
   type, and prints the result under `<<<df>>>` with the type rewritten
   to `NFS` so that the standard Checkmk filesystem check picks it up.
2. Deployment is driven by a Bakery rule with three modes: sync,
   cached (async with a configurable interval), or not at all.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/agents/plugins/nfs_df` | Bash agent plugin shipped to Linux hosts. |
| `src/lib/python3/cmk/base/cee/plugins/bakery/nfs_df.py` | Bakery registration (`register.bakery_plugin`). |
| `src/nfs_df/rulesets/backery.py` | `AgentConfig` ruleset `nfs_df`. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create a rule *Agent rules -> Operating system -> Filesystemmonitoring
   of NFS Mounts via Plugin (Linux)* and bake the agent, or copy
   `src/agents/plugins/nfs_df` to `/usr/lib/check_mk_agent/plugins/`
   manually.
3. Discovered mount points show up as regular Filesystem services.

## Configuration

| Parameter | Type | Meaning |
| --- | --- | --- |
| `deployment` | `sync` / `cached <TimeSpan>` / `do_not_deploy` | How the Bakery deploys the plugin on the target host. |

## Known limitations

- The plugin only emits output if `waitmax` is available on the target
  host.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `nfs_df` version `1.0.2`; minimum Checkmk version `2.3.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `nfs_df/src/info`; it declares 3 packaged files.
- Repository MKP artifacts present: `nfs_df-1.0.0.mkp`, `nfs_df-1.0.1.mkp`, `nfs_df-1.0.2.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Rulesets:** `src/nfs_df/rulesets/backery.py`.
- **Bakery:** `src/lib/python3/cmk/base/cee/plugins/bakery/nfs_df.py`.
- **Other packaged source:** `src/agents/plugins/nfs_df`.
- No special-agent or agent-based check registration was detected; use the component paths above to identify the package entry point.

### Validation

- Package-specific tests: `tests/test_nfs_df_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- Emitted Checkmk sections detected in source: `df`.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->

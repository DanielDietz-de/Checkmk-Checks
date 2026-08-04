# CIFS Filesystem Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p7-blue)
<!-- compatibility-badges:end -->

Agent side plugin that makes CIFS / SMB mounts visible to the standard Checkmk `df` filesystem check. The default Linux agent skips CIFS because `df` on a stuck CIFS mount can hang; this plugin wraps `df` in `waitmax` and re-emits the output so existing Filesystem services pick it up.

## How it works

The Bash plugin [`plugins/cifs_df`](src/agents/plugins/cifs_df) runs `waitmax -s 9 2 df -PTk`, filters for filesystem type `cifs`, rewrites the type to `CIFS` (so it does not collide with the default `df` section), and prints the result under the standard `<<<df>>>` section header. The existing `df` check plugin then discovers and monitors each CIFS mount point like any other filesystem. `waitmax` kills the `df` call after 2 s with `SIGKILL` to protect the agent against hanging mounts.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/agents/plugins/cifs_df` | Linux agent plugin. |
| `src/cifs_df/agent_based/bakery.py` | Agent Bakery plugin emitting the `cifs_df` file (sync or cached deployment). |
| `src/cifs_df/rulesets/bakery.py` | WATO Agent Bakery rule (`cmk.rulesets.v1`) with a cascading deployment choice. |

## Installation

1. Install the MKP on the Checkmk site.
2. Deploy the agent plugin:
   - **With Bakery:** configure *Filesystemmonitoring of CIFS_FS via Plugin (Linux)* under *Setup -> Agents -> Agent rules* and bake the agent.
   - **Without Bakery:** copy `src/agents/plugins/cifs_df` to `/usr/lib/check_mk_agent/plugins/` and `chmod +x` it. The host must have `waitmax` available (ships with the Checkmk agent).
3. Run service discovery; CIFS mounts show up as standard *Filesystem* services.

## Configuration

Rule: **Setup -> Agents -> Agent rules -> Filesystemmonitoring of CIFS_FS via Plugin (Linux)**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `deployment` | Cascading choice | `sync` (run synchronously), `cached` (run asynchronously with a configurable interval), or `do_not_deploy`. |

## Known limitations

- Hard timeout of 2 seconds on the `df` call — on very busy or slow CIFS shares the section may be empty.
- CIFS mounts share their items with the normal `df` check; the plugin relabels the type to `CIFS` to avoid duplicate items, but mount points are still parsed by the standard `df` check plugin.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `cifs_df` version `1.0.2`; minimum Checkmk version `2.3.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `cifs_df/src/info`; it declares 3 packaged files.
- Repository MKP artifacts present: `cifs_df-1.0.0.mkp`, `cifs_df-1.0.1.mkp`, `cifs_df-1.0.2.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/cifs_df/agent_based/bakery.py`.
- **Rulesets:** `src/cifs_df/rulesets/bakery.py`.
- **Other packaged source:** `src/agents/plugins/cifs_df`.
- No special-agent or agent-based check registration was detected; use the component paths above to identify the package entry point.

### Validation

- Package-specific tests: `tests/test_cifs_df_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- No direct remote-network client was detected in the current source.

### Troubleshooting

- Emitted Checkmk sections detected in source: `df`.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->

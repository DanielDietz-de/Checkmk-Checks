# HP OpenView Agent Version Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p7-blue)
<!-- compatibility-badges:end -->

Ships an agent-side script that detects whether an HP OpenView /
Operations Agent ("OVO") is installed on Linux, Solaris or AIX hosts
and publishes its version as Checkmk host labels. Useful for
inventorying OVO agent rollouts alongside Checkmk.

## How it works

The agent plugin runs `/opt/OV/bin/ovdeploy -inv` (wrapped in `waitmax
-s 9 2`) and greps for the `Operations-agent` and `HPOvSecCo`
component versions. The result is emitted as a `<<<labels:sep(0)>>>`
section, so the values become host labels in Checkmk:

```text
<<<labels:sep(0)>>>
{"HP_OVO_Vers_Detect": "in_Place"}
{"HP_OVO_OA_Installed": "Yes"}
{"HP_OVO_OA_Vers_gen": "12.12.010"}
{"HP_OVO_OA_Vers_HPOvSecCo": "12.12.010"}
```

If `ovdeploy` is not installed, only `HP_OVO_OA_Installed: No` is
emitted.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/agents/plugins/ovo_agent_linux.sh` | Linux agent plugin. |
| `src/agents/plugins/ovo_agent_solaris.sh` | Solaris agent plugin. |
| `src/agents/plugins/ovo_agent_aix.sh` | AIX agent plugin. |
| `src/lib/python3/cmk/base/cee/plugins/bakery/ovo_agent.py` | Bakery registration, deploys the matching script for Linux, Solaris and AIX. |
| `src/ovo_agent/rulesets/bakery.py` | `AgentConfig` ruleset `ovo_agent`. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create a rule *Agent rules -> Operating system -> Monitoring the
   Agents of HP Openview* and bake the agent. The Bakery picks the
   matching script per OS automatically.
3. After the next agent run the new host labels appear and can be used
   in rules or dashboards.

## Configuration

| Parameter | Type | Meaning |
| --- | --- | --- |
| `deployment` | `sync` / `cached <TimeSpan>` / `do_not_deploy` | How the Bakery deploys the plugin on the target host. |

## Known limitations

- The plugin is only effective on hosts that have `waitmax` available;
  otherwise it exits silently.
- Reports host labels only — no services or metrics are generated.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `ovo_agent` version `1.0.1`; minimum Checkmk version `2.3.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `ovo_agent/src/info`; it declares 5 packaged files.
- Repository MKP artifacts present: `ovo_agent-1.0.0.mkp`, `ovo_agent-1.0.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Rulesets:** `src/ovo_agent/rulesets/bakery.py`.
- **Bakery:** `src/lib/python3/cmk/base/cee/plugins/bakery/ovo_agent.py`.
- **Other packaged source:** `src/agents/plugins/ovo_agent_aix.sh`, `src/agents/plugins/ovo_agent_linux.sh`, `src/agents/plugins/ovo_agent_solaris.sh`.
- No special-agent or agent-based check registration was detected; use the component paths above to identify the package entry point.

### Validation

- Package-specific tests: `tests/test_ovo_agent_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- Emitted Checkmk sections detected in source: `labels`.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->

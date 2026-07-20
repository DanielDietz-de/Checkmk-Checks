# Switchboard Syncs

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p34-blue)
<!-- compatibility-badges:end -->

Checkmk 2.4 extension for monitoring one-to-one interface synchronization across a pair of switches. The technical package and plug-in name is `switch_port_sync`.

The default rule values are prefilled for the transit-switch pair:

- `041-Transit-001`
- `041-Transit-002`

No second SNMP poll is performed. The special agent reads the current results of the existing Checkmk `Interface ...` services through the local Livestatus socket and exposes the comparison as services on **both** switch hosts.

## State and discovery logic

A port pair becomes a monitored synchronization service when **at least one member is confirmed up during service discovery**. This catches an asymmetric pair immediately while excluding ports that are down on both switches and therefore normally unused.

| State on switch A | State on switch B | Discovered initially | Check state after discovery |
| --- | --- | --- | --- |
| up | up | yes | OK |
| up | down | yes | CRIT |
| down | up | yes | CRIT |
| up | missing/stale/unknown | yes | UNKNOWN |
| missing/stale/unknown | up | yes | UNKNOWN |
| down | down | no | CRIT if the service was previously discovered while at least one side was up |
| missing/stale/unknown | any non-up state | no | UNKNOWN if an already accepted service later reaches this state |

The existence of the accepted Checkmk service is the discovery baseline. A later link-down does not remove the service during normal checks, so one down or both down remains CRIT.

> A full service rediscovery while both links are down can mark the synchronization service as vanished. Do not accept its removal unless the intention is to reset that port's discovery baseline.

A separate `Switch port sync Pair status` service reports configuration, regex and Livestatus query problems. It remains OK when data acquisition is healthy; operational failures are reported by the individual port services.

## One-to-one mapping

The rule contains a regular expression for existing Checkmk interface service descriptions. The default is:

```regex
^Interface (?P<item>.+)$
```

The captured `item` becomes the mapping key:

```text
Interface 01       <-> Interface 01
Interface Gi0/1    <-> Interface Gi0/1
Interface te-1/1/1 <-> Interface te-1/1/1
```

Both switches must use the same interface item representation. Configure **Network interface and switch port discovery** consistently on both hosts, especially the item appearance (`ifIndex`, `ifDescr`, `ifAlias`, or `ifName`). Duplicate service descriptions that resolve to the same item are rejected as UNKNOWN rather than being compared ambiguously.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/switch_port_sync/agent_based/switch_port_sync.py` | Parses special-agent data, discovers pair and port services, and implements the state matrix. |
| `src/switch_port_sync/libexec/agent_switch_port_sync` | Queries both hosts' existing interface services through Livestatus. |
| `src/switch_port_sync/rulesets/special_agent.py` | Setup rule for pair name, host names and interface mapping regex. |
| `src/switch_port_sync/server_side_calls/special_agent.py` | Builds the special-agent command for each member of the pair. |
| `src/switch_port_sync/checkman/switch_port_sync` | Checkmk manual page. |
| `tests/` | Standalone parser, mapping, discovery and state-matrix tests. |

## Installation

### MKP

1. Download the `switch_port_sync-*.mkp` artifact produced by the GitHub Actions workflow.
2. In Checkmk, open **Setup > Maintenance > Extension packages**.
3. Upload and enable the package.
4. Activate changes.

Command-line equivalent as the site user:

```bash
mkp add /path/to/switch_port_sync-1.0.0.mkp
mkp enable switch_port_sync 1.0.0
cmk -R
```

### Source installation

As the Checkmk site user:

```bash
install -d "$OMD_ROOT/local/lib/python3/cmk_addons/plugins/switch_port_sync"
cp -a src/switch_port_sync/. \
  "$OMD_ROOT/local/lib/python3/cmk_addons/plugins/switch_port_sync/"
chmod 0755 \
  "$OMD_ROOT/local/lib/python3/cmk_addons/plugins/switch_port_sync/libexec/agent_switch_port_sync"
cmk-validate-plugins
cmk -R
```

## Configuration

1. Open **Setup > Agents > Other integrations > Switch port synchronization**.
2. Create one rule with:
   - Pair name: `041 Transit pair`
   - Switch A: `041-Transit-001`
   - Switch B: `041-Transit-002`
   - Interface service regex: `^Interface (?P<item>.+)$`
3. In the rule conditions, explicitly select both switch hosts and no unrelated hosts.
4. For SNMP-only switches, set **Checkmk agent / API integrations** to **Configured API integrations, no Checkmk agent** while keeping SNMP enabled.
5. Activate changes.
6. Run service discovery on both switches and accept the new services.

The server-side call also refuses to run on a host that is not one of the two configured pair members, providing a second safeguard against an overly broad rule condition.

## Validation

Run as the Checkmk site user:

```bash
cmk-validate-plugins
cmk-validate-config
cmk -D 041-Transit-001
cmk -D 041-Transit-002

cmk -d 041-Transit-001 | sed -n '/<<<switch_port_sync/,/^<<</p'

cmk -IIv 041-Transit-001 041-Transit-002
cmk -nv 041-Transit-001 041-Transit-002
```

Inspect the source interface services directly:

```bash
lq 'GET services
Columns: host_name description state plugin_output long_plugin_output is_stale
Filter: host_name = 041-Transit-001
Filter: description ~ ^Interface '
```

Expected services include:

```text
Switch port sync Pair status
Switch port sync 01
Switch port sync 02
...
```

## Operational behavior

The special agent evaluates the latest interface results already held by the Checkmk core. A change can therefore appear in the synchronization service up to one regular check interval after it appears in the underlying interface service.

Missing interface services, stale data, unchecked services, a down host, malformed Livestatus rows, invalid regular expressions and inaccessible Livestatus sockets produce UNKNOWN. Only confirmed interface operational-state failures produce CRIT.

The extension contains no device credentials and does not contact the switches directly.

## Removal

```bash
mkp disable switch_port_sync 1.0.0
mkp remove switch_port_sync 1.0.0
cmk -R
```

For a source installation:

```bash
rm -rf "$OMD_ROOT/local/lib/python3/cmk_addons/plugins/switch_port_sync"
cmk -R
```

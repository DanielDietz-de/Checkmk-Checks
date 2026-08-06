# Architecture

## Purpose

`s2d_hci_monitoring` separates inexpensive cluster state from slower storage, health, performance, and Hyper-V workload collection. This prevents one expensive Microsoft cmdlet from delaying all monitoring data and permits independent cache intervals.

## Data flow

```text
Windows cluster node
  ├─ cached Checkmk agent plug-ins
  │    ├─ fast cluster state
  │    ├─ storage inventory and capacity
  │    ├─ storage jobs
  │    ├─ S2D and storage health
  │    └─ optional performance history
  └─ optional gMSA scheduled task
       └─ Hyper-V collector -> temporary file -> atomic spool replacement

Checkmk agent output
  -> JSON-lines agent sections
  -> Check API V2 parsers
  -> discovered services, state results, and metrics
  -> ruleset thresholds and graphing definitions
```

## Component boundaries

### Windows collectors

The six collectors under `src/agents/plugins/` query only local Microsoft management cmdlets. They emit named sections and compact JSON lines. Each section invocation catches its own exception and emits a structured error row so an unavailable feature does not suppress unrelated sections in the same script.

### Spool wrapper

`src/agents/scripts/s2d_hci_virtualization_spool.ps1` exists for environments where the Checkmk agent service identity must not receive Hyper-V access. It:

1. reads a non-secret JSON configuration;
2. canonicalizes and constrains paths to the Checkmk agent and spool roots;
3. executes the read-only virtualization collector without an execution-policy bypass;
4. writes the complete output to a same-directory temporary file;
5. atomically replaces the live spool file;
6. deletes a leftover temporary file on failure.

The wrapper does not provision accounts, alter Hyper-V, or grant permissions.

### Checkmk plug-ins

Server-side code is below `src/cmk_addons_plugins/s2d_hci/`:

- `agent_based/`: parsers, discovery, state logic, and metrics;
- `rulesets/`: free-space, CPU, memory-pressure, and checkpoint-age thresholds;
- `graphing/`: metric units, graphs, and perfometers;
- `checkman/`: Checkmk service manual.

All Python code uses `cmk.agent_based.v2`, Rulesets API V1, and Graphing API V1.

## Stable contracts

The following identifiers are compatibility contracts and must not be renamed without a migration plan:

- `s2d_hci_*` agent section names;
- CheckPlugin names and service names;
- ruleset names and parameter keys;
- metric names;
- spool configuration keys;
- the numeric spool-file lifetime prefix.

## Error isolation

Malformed JSON rows are skipped individually. Unsupported optional cmdlets emit an explicit `available: false` record and become UNKNOWN. Known unhealthy Microsoft states become WARN or CRIT according to the service contract. No parser treats missing telemetry as OK.

## Performance model

Cache expensive collectors independently. The health and performance scripts may be significantly slower on large clusters. Runtime must be measured on representative nodes before production rollout, and the configured Checkmk agent timeout must exceed the measured worst case with margin.

## Trust boundaries

Collector output can contain infrastructure-sensitive names, serial numbers, paths, addresses, and topology. It is trusted only after local collection but remains untrusted parser input on the Checkmk server. Parsers therefore validate JSON and numeric conversion and avoid evaluating data as code.

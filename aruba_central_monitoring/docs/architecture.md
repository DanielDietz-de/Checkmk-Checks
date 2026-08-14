# Architecture

## Components

1. **Windows collector plug-in** — `aruba_central_aps.ps1` runs on a Windows host where `cencli` is installed and authenticated. Checkmk executes it asynchronously.
2. **Check API plug-in** — parses one JSON document from the collector section and one document from every AP piggyback section.
3. **Rulesets and graphing** — expose service thresholds and metric definitions in Setup.
4. **Host synchronizer** — reads captured agent output or `cmk -d <collector>`, validates Group→Site policy, and plans or applies folders and hosts via the Checkmk REST API.

## Data flow

```text
Aruba Central API
      |
    cencli
      |
PowerShell collector (stdout + stderr captured separately)
      |
      +-- collector section --> Aruba Central summary
      |
      +-- AP piggyback sections --> AP host --> AP service + radio services
                                      |
                                      +-- optional REST host synchronization
```

The diagnostic lines and JSON may be emitted on different streams. The collector searches stdout first, stderr second, and their combined text only as a compatibility fallback for JSON. Counts and rate-limit diagnostics are searched in stdout and stderr independently. The collector records `json_stream`, `counts_stream`, and `rate_limit_stream`; counts derived from JSON are explicitly marked `derived`.

## State and cache boundaries

Checkmk's Windows agent asynchronous execution provides the normal scheduling cache. The plug-in additionally maintains a bounded last-known-good file solely for failure continuity. A successful run replaces this file atomically. A failed run never overwrites it. When the file remains within `MaxStaleSeconds`, AP data is emitted with a collector `ERROR` state and last-success age; otherwise only a collector error is emitted.

## Configuration mutation boundary

Monitoring never creates, moves, or deletes Checkmk objects. `sync_aruba_central_hosts` is a separate executable, is dry-run-only unless `--apply` is given, and does not delete or move existing hosts. This boundary prevents a transient vendor response or malformed mapping from silently changing monitoring configuration.

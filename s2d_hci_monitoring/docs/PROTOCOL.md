# Collector protocol version 1

Every JSON data record emitted by an S2D/HCI collector has these fields:

- `protocol_version`: integer `1`;
- `run_id`: UUID shared by all records from that collector invocation;
- object-specific fields documented by the corresponding check.

A section-level failure is represented as a JSON object with `success=false`, `section`, and a bounded `error` message. Server-side parsing treats it as monitoring data and returns UNKNOWN rather than dropping the section.

## Collector health

`<<<s2d_hci_collector_health>>>` contains exactly one final row per collector invocation:

- `collector`, `run_id`, `protocol_version`;
- `success`, `complete`, `truncated`;
- `record_count`, `output_bytes`, configured bounds, and `elapsed_ms`;
- `role` (`leader`, `standby`, `local`, or `disabled`);
- source/cluster/logical-host context where applicable;
- up to 20 bounded `errors`, `errors_omitted`, and UTC start/finish timestamps.

`output_bytes` counts compact JSON data records only, using the same one-byte line accounting enforced by `Write-S2DHciJsonLine`; Checkmk section headers, piggyback markers, and the final collector-health row are protocol framing rather than data-record bytes. The gMSA spool wrapper recomputes the data-record count and bytes and requires them to match the health envelope, while independently bounding framing and collector-health size. This avoids both under-counting unbounded framing and rejecting valid high-record runs with a fixed overhead allowance.

In direct Hyper-V mode, a record, byte, or runtime truncation is also a framing stop condition. After the first bounded writer marks the run truncated, the current VM closes its already-open piggyback block and no later section headers or VM piggyback blocks are emitted. This keeps uncounted protocol framing bounded even when the host has many additional VMs after the data limit is reached.

A failed/incomplete/truncated run is CRIT. Invalid/malformed health envelopes are UNKNOWN. An intentionally disabled virtualization collector is OK only when the health envelope confirms a successful, complete, non-truncated invocation.

## Parser invariants

Server-side parsing is fail-visible and treats each section as one coherent collector snapshot:

- malformed JSON => synthetic UNKNOWN service;
- non-object JSON => synthetic UNKNOWN service;
- unsupported/missing protocol version => synthetic UNKNOWN service;
- missing `run_id` => synthetic UNKNOWN service;
- a `run_id` that differs from the first valid row in the section => mismatching row rejected plus synthetic UNKNOWN mixed-run service;
- missing stable identity => synthetic UNKNOWN service;
- duplicate stable identity => first object retained plus synthetic UNKNOWN duplicate service;
- `success=false` => UNKNOWN with collector error text.

The first valid `run_id` establishes the section snapshot. Rows from another collector invocation are never merged into that snapshot, which prevents direct/spool overlap, stale piggyback data, or overlapping runs from being interpreted as one coherent state.

Storage state checks normalize Microsoft sentinel values rather than relying on string truthiness. In particular, virtual-disk `DetachedReason=None`/zero means attached normally; only a substantive detach reason produces a detached-disk CRIT.

These invariants prevent malformed, partial, mixed-run, duplicate, failed, or sentinel-only collection data from being interpreted incorrectly.

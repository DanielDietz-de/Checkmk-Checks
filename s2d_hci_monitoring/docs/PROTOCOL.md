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
- bounded `errors` array and UTC start/finish timestamps.

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

These invariants prevent malformed, partial, mixed-run, duplicate, or failed collection from being interpreted as healthy empty monitoring.

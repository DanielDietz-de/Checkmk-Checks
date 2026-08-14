# Changelog

## 1.3.0 - 2026-08-06

- Add a PowerShell 5.1 Windows agent plug-in that executes `cencli show aps -v --json` with independent stdout and stderr capture.
- Add collector, access-point, and radio services with configurable thresholds and graphing definitions.
- Add bounded last-known-good fallback data without reporting a failed collection as healthy.
- Add deterministic piggyback host naming and fail closed before cache/output if normalized AP host names collide.
- Add a dry-run-first Checkmk REST host synchronizer for `<Group>/Accesspoint/<Host>`.
- Reject malformed or truncated AP piggyback sections instead of applying a partial inventory.
- Reject Group names that collide after Checkmk folder-ID normalization before any REST mutation.
- Treat only explicit `already exists` REST errors as idempotent duplicates; unrelated 400/409/422 errors remain failures.
- Use Checkmk folder object IDs for nested folder and host creation.
- Fetch the pending-changes ETag and send it with `If-Match` during activation.
- Validate the Checkmk 2.5 REST v1 base path before authenticated requests.
- Add sanitized fixtures, focused tests, operational documentation, and security guidance.

# Production acceptance checklist

Record date, operator, Windows build, cluster functional level, Checkmk version, package version/checksum, and target topology.

## Collector behavior

- [ ] All physical nodes show explicit collector-health services.
- [ ] One and only one `Up` node emits cluster-wide piggyback data.
- [ ] Leader failover changes the source node but not the logical cluster host.
- [ ] Representative CSV, pool, virtual disk, volume, disk, job, S2D, subsystem, and health-report services discover correctly.
- [ ] Module/cmdlet permission failure produces UNKNOWN/CRIT collector visibility rather than empty discovery.
- [ ] Runtime, record, and output accounting stay comfortably below configured bounds.

## Hyper-V, when enabled

- [ ] Explicit opt-in was approved and does not duplicate another monitoring mechanism.
- [ ] VM piggyback host is derived from VM GUID and stays stable during live migration.
- [ ] CPU, memory pressure, integration service, replication, checkpoint, NIC, and disk services behave as expected.
- [ ] Sensitive paths/addresses remain absent unless specifically enabled.

## gMSA spool mode, when used

- [ ] `Test-ADServiceAccount` succeeds.
- [ ] Identity validation reports expected ACLs.
- [ ] Task uses `RunLevel Limited`, ServiceAccount logon, IgnoreNew, and a bounded execution limit.
- [ ] A deliberately failed collector preserves the last valid spool.
- [ ] Reparse/path escape tests fail closed.

## Checkmk

- [ ] Service discovery has no unexplained vanished or duplicate services.
- [ ] State-policy and threshold rules are scoped correctly.
- [ ] Representative OK/WARN/CRIT/UNKNOWN conditions have been exercised.
- [ ] Alert routing and notification escalation are verified.
- [ ] Upgrade and rollback procedures have been exercised on a test node/site.

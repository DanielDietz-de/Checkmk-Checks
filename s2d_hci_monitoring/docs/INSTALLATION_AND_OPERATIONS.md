# Installation and operations

## Preferred deployment: Agent Bakery

1. Install and enable the validated `s2d_hci_monitoring` MKP on Checkmk 2.5.
2. Create an `S2D/HCI monitoring collectors` Agent Bakery rule scoped only to intended Windows cluster nodes.
3. Keep sensitive fields and custom Hyper-V collection disabled unless operationally required.
4. Bake/sign/deploy the Windows agent according to the site's normal change process.
5. Inspect raw agent output and verify `s2d_hci_collector_health` on every target node.
6. Create/discover the logical `s2d-cluster-*` piggyback host and, if Hyper-V collection is enabled, the `s2d-vm-<guid>` piggyback hosts according to site policy.
7. Rediscover services and validate expected state transitions.

## Manual deployment

Use only when Bakery is unavailable. Copy the manifest-owned agent files from `src/agents` to the matching Checkmk agent directories. Direct plug-ins require `bin/s2d_hci_common.psm1`. Place a reviewed `config/s2d_hci.json` in the agent configuration directory. Do not copy files outside the package manifest or use broad synchronization with delete semantics.

## Operational checks

For every physical node, verify collector-health services. For cluster-wide data, verify only the elected node emits the `s2d-cluster-*` piggyback block. During failover, the elected source may change but the logical piggyback host must remain unchanged.

When a collector approaches configured limits, investigate object counts and cmdlet latency before increasing limits. Do not make limits unbounded.

## Hyper-V

Custom Hyper-V monitoring is opt-in because Checkmk may already monitor VMs through other mechanisms. Choose either direct Bakery deployment or gMSA spool mode. Never run both for the same node because duplicate sections are ambiguous.

## Upgrade

1. Review CHANGELOG and manifest changes.
2. Build/verify the new MKP and evidence.
3. Test on representative non-production nodes.
4. Update the package and rebake agents.
5. Verify protocol health, discovery, thresholds, and piggyback identity.
6. Record production acceptance evidence.

## Rollback

Reinstall the previously validated MKP and rebake/redeploy its agent package. If gMSA spool mode changed, restore the previous reviewed binaries/configuration and verify the task identity. Never reuse an MKP whose checksum or provenance cannot be verified.

## Removal

Remove the Bakery rule, rebake/redeploy agents, remove the Checkmk package, and rediscover services. For manually installed gMSA tasks use `tools/windows/Remove-S2DHciVirtualizationCollectorTask.ps1`; generated spool/config state is removed only with the explicit `-RemoveGeneratedState` switch.

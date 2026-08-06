# Installation and operations

## Pre-deployment checklist

- Use a Checkmk 2.5 site covered by the manifest compatibility range.
- Validate the MKP and checksum produced by repository CI.
- Identify which roles exist on each Windows node and deploy only applicable collectors.
- Measure collector runtime on a representative node.
- Decide whether virtualization collection runs directly or through a dedicated gMSA spool task.
- Create rollback copies of the existing MKP, agent files, rules, and scheduled-task configuration.

## Install the MKP

Install through **Setup > Maintenance > Extension packages** or as the Checkmk site user:

```bash
sha256sum --check s2d_hci_monitoring-1.0.0.mkp.sha256
mkp add /path/to/s2d_hci_monitoring-1.0.0.mkp
mkp enable s2d_hci_monitoring 1.0.0
cmk -R
cmk-validate-plugins
```

Use only the exact artifact and checksum from a successful release or pull-request validation run.

## Deploy collectors

The MKP contains agent files in the Checkmk agent download area. Copy the selected scripts to the Windows agent root using the site’s normal controlled deployment process.

Recommended intervals:

| Script | Interval |
| --- | ---: |
| `s2d_hci_fast.ps1` | 120 seconds |
| `s2d_hci_storage.ps1` | 300 seconds |
| `s2d_hci_jobs.ps1` | 300 seconds |
| `s2d_hci_health.ps1` | 600 seconds |
| `s2d_hci_perf.ps1` | 900 seconds |
| `s2d_hci_virtualization.ps1` | 300 seconds or gMSA spool mode |

Use Checkmk’s Windows agent plug-in cache directories for the deployed agent version. Do not rename scripts without updating deployment automation and troubleshooting procedures.

## Direct validation on Windows

Run each collector under the effective monitoring identity:

```powershell
powershell.exe -NoProfile -NonInteractive -File .\s2d_hci_fast.ps1
powershell.exe -NoProfile -NonInteractive -File .\s2d_hci_storage.ps1
powershell.exe -NoProfile -NonInteractive -File .\s2d_hci_jobs.ps1
powershell.exe -NoProfile -NonInteractive -File .\s2d_hci_health.ps1
powershell.exe -NoProfile -NonInteractive -File .\s2d_hci_perf.ps1
powershell.exe -NoProfile -NonInteractive -File .\s2d_hci_virtualization.ps1
```

Acceptance criteria:

- every emitted section header is complete;
- every non-empty data line is valid JSON;
- errors are structured JSON and contain no credentials;
- runtime fits the configured cache and timeout budget;
- no collector changes cluster or workload state.

## Validate through Checkmk

```bash
cmk -d hci-node > /tmp/hci-node.agent
sed -n '/<<<s2d_hci_/,/^<<<.*>>>/p' /tmp/hci-node.agent
cmk -IIv hci-node
cmk -nv hci-node
```

Then verify:

- expected services are discovered exactly once;
- thresholds apply to the intended items;
- metrics appear with correct units;
- an intentional test condition maps to the documented state;
- optional unavailable cmdlets produce UNKNOWN, not CRIT or OK.

Delete sanitized temporary agent output after troubleshooting because it may contain topology and workload details.

## Routine operations

### Daily

- Confirm cluster, storage, and workload services are current.
- Investigate UNKNOWN services that indicate missing telemetry or permissions.
- Check active storage jobs and retained checkpoints.

### After Windows or role updates

- Re-run each applicable collector interactively.
- Compare section keys and representative JSON fields.
- Run service rediscovery without automatically accepting unexplained changes.

### After Checkmk updates

- Confirm the target release remains within the manifest range.
- Validate the MKP in a test site before upgrading production.
- Run `cmk-validate-plugins`, discovery, and representative checks.

## Troubleshooting matrix

| Symptom | Likely cause | Action |
| --- | --- | --- |
| No `s2d_hci_*` sections | Agent file absent, wrong cache path, execution blocked | Inspect agent plug-in path, file ACL, and direct PowerShell execution |
| Structured error row | Missing module, insufficient read access, unsupported cmdlet | Read the section error, verify role/module and effective identity |
| Services missing | Section name mismatch, parser not loaded, empty valid data | Compare raw header to `AgentSection` name and run `cmk-validate-plugins` |
| Duplicate services/data | Direct and spool collection both active | Select one virtualization collection path |
| Workload data becomes stale | Scheduled task failure or spool write failure | Inspect task history, last result, gMSA rights, and spool timestamp |
| UNKNOWN optional performance/health service | Cmdlet not present on that OS/role | Disable unnecessary collector or accept the documented limitation |
| Unexpected CRIT for a new Microsoft state | Vendor output changed | Capture sanitized JSON, add fixture/test, then update mapping deliberately |
| Long agent runtime | Expensive uncached collector | Move to an interval cache or spool execution and measure again |

## Upgrade

1. Validate the new source and MKP in CI.
2. Test-install the package on a non-production Checkmk site.
3. Compare manifests, section names, services, rules, and metrics.
4. Update server-side MKP and host-side scripts in a controlled window.
5. Reload Checkmk and rediscover affected hosts.
6. Confirm scheduled-task and spool freshness when applicable.

## Rollback

1. Restore the previous MKP and checksum-verified agent files.
2. Restore the previous JSON and scheduled-task definition when used.
3. Reload Checkmk.
4. Rediscover and validate representative hosts.
5. Record the failed version and sanitized evidence before retrying.

## Removal

Remove the MKP, Windows collector files, gMSA task, wrapper, configuration, and spool data separately. Removing only the MKP does not alter Windows nodes. Review and remove permissions or the gMSA only after confirming there are no other consumers.

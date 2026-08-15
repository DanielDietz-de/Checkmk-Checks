# Operations runbook

## Collector prerequisites

- Windows PowerShell 5.1 or newer.
- Checkmk Windows agent 2.5.
- `cencli` installed and authenticated under the identity used by the Checkmk agent service.
- Permission to create the configured last-known-good cache directory.

Validate the command interactively under the same account:

```powershell
cencli show aps -v --json
```

Capture both streams during diagnostics because the JSON, counts, and rate-limit lines are not assumed to use a fixed stream:

```powershell
$out = Join-Path $env:TEMP 'cencli.stdout.txt'
$err = Join-Path $env:TEMP 'cencli.stderr.txt'
& cencli show aps -v --json 1> $out 2> $err
Get-Content $out
Get-Content $err
```

## Deploy the collector

Copy:

- `aruba_central_aps.ps1` to `C:\ProgramData\checkmk\agent\plugins\`.
- `aruba_central_aps.json` to `C:\ProgramData\checkmk\agent\config\`.
- Merge the supplied `check_mk.user.aruba_central_aps.yml` fragment into the agent configuration.

The asynchronous example uses a 90-second timeout and a 300-second cache age. Keep the timeout above the observed worst-case `cencli` duration.

## Validate agent output

Run the agent test command and inspect the section:

```powershell
& 'C:\Program Files (x86)\checkmk\service\check_mk_agent.exe' test
```

Expected structural markers:

```text
<<<aruba_central_aps:sep(0)>>>
{"schema":1,"kind":"collector",...}
<<<<AP_SERIAL_OR_NAME>>>>
<<<aruba_central_aps:sep(0)>>>
{"schema":1,"kind":"ap",...}
<<<<>>>>
```

On the Checkmk server:

```bash
cmk -d <collector-host>
cmk --detect-plugins=aruba_central_summary -v <collector-host>
cmk -IIv <collector-host>
cmk -R
```

## Host synchronization

Start with a captured output and the supplied mapping:

```bash
sync_aruba_central_hosts \
  --agent-output-file /tmp/collector-output.txt \
  --mapping /path/to/group_site_map.json
```

Or read current data from Checkmk:

```bash
sync_aruba_central_hosts \
  --source-host <collector-host> \
  --mapping /path/to/group_site_map.json
```

The default output is a plan only. After review, create folders and hosts:

```bash
sync_aruba_central_hosts \
  --source-host <collector-host> \
  --mapping /path/to/group_site_map.json \
  --apply \
  --api-url https://checkmk.example/site/check_mk/api/v1 \
  --username automation-aruba-central \
  --secret-file /omd/sites/site/var/check_mk/aruba-central.secret \
  --activate-site site
```

The secret file must be mode `0600` on Unix. The synchronizer creates:

```text
/<Group>/Accesspoint/<Host>
```

It configures hosts for piggyback-only monitoring without SNMP or an IP address. Run the dry-run from a scheduler first and alert on a nonzero exit code. Add `--apply` only after the mapping and permissions have been accepted.

## Group and site policy

The example policy implements:

| Group | Accepted site |
| --- | --- |
| B200 | `B200` |
| Bad Godesberg | `Bad Godesberg` |
| Campus Bornheim | `Campus Bornheim - ABS5` or `Campus Bornheim - MAS3` |

Every discovered AP must match a configured Group and one full Site regular expression. The complete run fails closed if any AP violates the policy.

## Failure handling

- **cencli returns nonzero:** collector CRIT; bounded last-known-good AP data may remain available.
- **No JSON on either stream:** collector CRIT with sanitized diagnostics.
- **Timeout:** collector CRIT; increase only after investigating API or network latency.
- **Cache too old:** no AP piggyback data is emitted.
- **Unknown Group/Site:** host synchronization exits 2 and applies nothing.
- **REST redirect:** refused to avoid forwarding credentials to a different endpoint.
- **Existing folder or host:** reported as existing; no move, overwrite, or delete is attempted.

## Upgrade and rollback

Version 1.3.0 introduces all service and metric names. Before later upgrades, review the changelog for naming or schema changes. To roll back, disable the asynchronous plug-in entry, restore the earlier MKP, rediscover affected hosts, and retain the last-known-good file only for diagnostics.

## Removal

1. Disable or remove the asynchronous plug-in entry from `check_mk.user.yml`.
2. Remove the PowerShell plug-in and JSON configuration.
3. Remove the last-known-good cache after retaining any required diagnostics.
4. Remove Checkmk rules and the MKP.
5. Remove generated AP hosts and folders manually after confirming no other piggyback source uses them.
6. Remove the automation user/secret and any scheduler entry for host synchronization.

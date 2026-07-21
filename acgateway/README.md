# AudioCode Gateway

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0p9-blue) ![usable until](https://img.shields.io/badge/usable%20until-2.5.99-green)
<!-- compatibility-badges:end -->

SNMP checks for AudioCodes SIP gateways and SBCs. Adds services for active alarms, SBC call and user statistics, retained call peaks, SBC license headroom, HA health, SIP TLS connections and certificate alarms, SIP interface and IP group configuration, and Tel2IP / IP2Tel performance counters. Based on earlier work by Robert Sander.

## How it works

All sections detect the device via `sysObjectID` containing `.1.3.6.1.4.1.5003.8.1.1` and query the AudioCodes private MIB tree under `.1.3.6.1.4.1.5003`:

- `acgateway_alarms` — reads active alarms and history sequence numbers from `acAlarm` (`.11.1.1.1.1` / `.11.1.2.1.1`). Severity `major/critical` maps to CRIT, `warning/minor` to WARN. Service `SIP Alarms` also exposes `active_alarms` and `archived_alarms` metrics.
- `acgateway_calls` — legacy SBC active calls, ASR, ACD and call rate from `acPMSIPSBC*` and `acPMSBC*`. Service `SBC Calls`.
- `acgateway_call_capacity` — current `Active Calls In`, `Active Calls Out` and `Active Sessions`, plus the highest `Active Calls In Max`, `Active Calls Out Max` and `Active Sessions Max` found in the retained 15-minute KPI intervals. Service `SBC Call Capacity`.
- `acgateway_license` — current and retained-maximum SBC media/signaling license utilization. Also calculates idle licensed capacity as `100 - max(media usage, signaling usage)`. Service `SBC License Usage`.
- `acgateway_ha` — aggregate module operational/presence/HA state from `acSysModuleTable`, current and retained HA keepalive packet loss, and HA fault/configuration-mismatch/switchover/synchronization alarms from the active alarm table. Service `SBC HA Health`.
- `acgateway_tls` — current and retained SIP TLS connection KPIs, connection-attempt/rejection rates, certificate-expiry alarms and TLS socket-limit alarms. Service `SBC TLS Health`.
- `acgateway_users` — SBC registered users and SIP transaction rates. Service `SBC Users`.
- `acgateway_sipperf` — Tel2IP and IP2Tel counters from `acPerfH323SIPGateway` (attempted / established / busy / no-answer / no-route / fail / fax / duration), reported as rates. Service `SIP Performance`.
- `acgateway_sipinterface` — joins SIP interface, system interface and ethernet device rows; service per interface named `<index> <name>`, discovered row status becomes part of the service parameters and deviations go CRIT.
- `acgateway_ipgroup` — IP group row status, type and description; service per `<index> <name>`.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/acgateway/agent_based/alarms.py` | Active and archived alarms section and check. |
| `src/acgateway/agent_based/calls.py` | Legacy SBC established calls, ASR and ACD. |
| `src/acgateway/agent_based/call_capacity.py` | Current and retained-maximum SBC calls and sessions. |
| `src/acgateway/agent_based/license.py` | SBC media/signaling license usage and remaining headroom. |
| `src/acgateway/agent_based/ha.py` | HA module state, keepalive packet loss and HA/synchronization alarms. |
| `src/acgateway/agent_based/tls.py` | SIP TLS connection KPIs and TLS/certificate alarms. |
| `src/acgateway/agent_based/users.py` | SBC registered users and SIP transactions per second. |
| `src/acgateway/agent_based/sipperf.py` | Tel2IP / IP2Tel performance counters. |
| `src/acgateway/agent_based/sipinterface.py` | SIP interface + underlying system interface and ethernet device. |
| `src/acgateway/agent_based/ipgroup.py` | IP group status, type and description. |
| `src/acgateway/checkman/acgateway_*` | Check manual pages. |
| `src/acgateway/graphing/acgateway.py` | Existing metric definitions for performance counters. |
| `src/acgateway/graphing/acgateway_extended.py` | Metrics and graphs for capacity, licensing, HA and TLS. |

## Installation

1. Install the MKP on the Checkmk site.
2. Add the AudioCodes gateway as an SNMP host.
3. Ensure the SNMP credentials have read access to the AudioCodes enterprise tree `.1.3.6.1.4.1.5003`.
4. Run a full service discovery.

The package uses the Checkmk agent-based v2 and graphing v1 APIs. CI loads and validates the source on Checkmk 2.4.0p34 and 2.5.0p9, and the repository MKP is built by Checkmk 2.5.0p9 with `version.usable_until` set to `2.5.99` only after both validation jobs pass.

## AudioCodes prerequisites

### Active Sessions and Active Sessions Max

`Active Calls In/Out` work without SDR. AudioCodes returns `null` for `Active Sessions` and `Active Sessions Max` when both SDR Syslog and SDR Local Storage are disabled. Enabling local SDR storage is sufficient; an external Syslog server is not required.

Web interface:

1. Open **Troubleshoot > Troubleshoot > Session Detail Record > Session Detail Record Settings**.
2. In the SDR local-storage settings, set **Local Storage** to **Enabled**.
3. Keep bounded storage settings appropriate for the appliance, for example the platform defaults for file size, number of files, rotation and compression.
4. Apply and save the configuration.

CLI equivalent:

```text
configure troubleshoot
sdr
local-storage 1
```

Only sessions started after SDR generation is enabled are counted. Verify the device before rediscovery:

```text
show kpi current sbc callstats global activesessions
show kpi interval all sbc callstats global activesessionsmax
```

The current value should become numeric as soon as newly started sessions are present. A maximum value is available after a completed 15-minute KPI interval. AudioCodes retains four intervals for the call/session maximum KPIs, so the check reports the peak of approximately the latest hour rather than a lifetime maximum.

### TLS certificate expiry monitoring

The TLS check obtains certificate state from `acCertificateExpiryAlarm`. Configure the SBC to periodically validate every TLS Context certificate and raise the alarm before expiration.

Web interface:

1. Open **Setup > IP Network > Security > Security Settings**.
2. Set **TLS Expiry Check Start** to the required warning horizon. AudioCodes defaults to 60 days.
3. Set **TLS Expiry Check Period** to the required check interval. AudioCodes defaults to 7 days.
4. Apply and save the configuration.

CLI example using the defaults:

```text
configure network
security-settings
tls-expiry-check-start 60
tls-expiry-check-period 7
```

Correct NTP configuration is required for meaningful X.509 validity checks. The SNMP user must also be able to read the active alarm table under `.1.3.6.1.4.1.5003.11.1.1.1.1`.

### HA and synchronization monitoring

No additional KPI switch is required for the HA module-state or keepalive packet-loss objects. The check evaluates:

- module operational state, presence and HA role/status from `acSysModuleTable`;
- active and redundant HA keepalive packet loss;
- `acHASystemFaultAlarm`, `acHASystemConfigMismatchAlarm` and `acHASystemSwitchOverAlarm`;
- active alarm text indicating synchronization or redundant-unit problems.

The synchronization result is alarm-based because the AudioCodes SNMP HA module table exposes HA role/status but not the CLI's textual `Last HA sync action/state` value. Validate the pair directly on the SBC with:

```text
show high-availability status
```

A healthy active node normally reports `Active`, `Connected` and `Sync. ended !`. Checkmk also ships the official per-module services `AudioCodes: Operational State` and `AudioCodes: Operational State Redundant`; these can remain enabled. `SBC HA Health` adds an aggregate view, HA packet-loss metrics and synchronization-related alarm correlation.

### Interpreting “Idles of”

AudioCodes does not document a performance KPI named `Idles of`. This implementation treats the requested value as **idle licensed SBC capacity**:

```text
100% - max(SBC media license usage, SBC signaling license usage)
```

The service reports both the current idle percentage and the minimum idle percentage calculated from the retained maximum utilization. It deliberately does not infer an absolute number of free calls because the installed absolute `SBC=<sessions>` license value is not exposed by these KPI objects.

## Services and metrics

| Service | Notes |
| --- | --- |
| `SIP Alarms` | State driven by active alarm severity. Metrics: `active_alarms`, `archived_alarms`. |
| `SBC Calls` | Existing metrics: `active_calls`, `calls_per_sec`, `average_success_ratio`, `average_call_duration`. |
| `SBC Call Capacity` | `active_calls_in`, `active_calls_out`, `active_sessions`, `active_calls_in_max`, `active_calls_out_max`, `active_sessions_max`. |
| `SBC License Usage` | `sbc_media_license_usage`, `sbc_signaling_license_usage`, retained maxima, current idle capacity and retained minimum idle capacity. |
| `SBC HA Health` | Aggregate module HA status, synchronization/fault alarms, current and retained active/redundant keepalive packet loss. |
| `SBC TLS Health` | Active and retained-maximum SIP TLS connections, attempt/rejection rates and retained interval values, certificate-expiry and socket-limit alarms. |
| `SBC Users` | Metrics: `rx_trans`, `tx_trans`, `num_user`. |
| `SIP Performance` | Metrics: `tel2ip_*` and `ip2tel_*` counters (attempted, established, busy, no_answer, no_route, no_capability, failed, fax_attempted, fax_success, total_duration). |
| `SIP Interface <index> <name>` | Discovery saves row status; any later change goes CRIT. |
| `IP Group <index> <name>` | Discovery saves row status; any later change goes CRIT. |

## Device-side verification

Use numeric OIDs to confirm that the monitored objects are visible to the same SNMP credentials used by Checkmk:

```bash
snmpget -v2c -c '<community>' '<sbc>' \
  .1.3.6.1.4.1.5003.15.3.1.1.1.2.0 \
  .1.3.6.1.4.1.5003.15.3.1.1.1.3.0 \
  .1.3.6.1.4.1.5003.15.3.1.1.1.43.0

snmpwalk -v2c -c '<community>' '<sbc>' \
  .1.3.6.1.4.1.5003.9.10.10.4.21.1

snmpget -v2c -c '<community>' '<sbc>' \
  .1.3.6.1.4.1.5003.15.6.4.1.2.1.0 \
  .1.3.6.1.4.1.5003.15.6.4.1.2.2.0 \
  .1.3.6.1.4.1.5003.15.6.4.1.2.3.0
```

Adapt the command for SNMPv3 where applicable. `No Such Object` indicates firmware/MIB support or SNMP-view restrictions; a literal `null` on the Active Sessions objects normally indicates that SDR generation is disabled or that no post-enable session has yet been observed.

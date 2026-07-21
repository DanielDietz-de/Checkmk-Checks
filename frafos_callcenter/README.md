# Frafos Callcenter Metric — legacy

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.0.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.0.0p20-blue) ![usable until](https://img.shields.io/badge/usable%20until-2.2.99-green)
<!-- compatibility-badges:end -->

> **Legacy package:** this extension is explicitly limited to Checkmk 2.0–2.2. Do not install it on Checkmk 2.3, 2.4 or 2.5. It must be migrated to the current `cmk.agent_based.v2` API and tested with representative Frafos SNMP data before its compatibility cap can be raised.

SNMP monitoring for Frafos SBC call-center systems. Provides a global `Call Statistics` service with total and per-minute call counts and one `Call Agent <name>` service per configured call agent with current, per-minute and traffic metrics in both directions.

## Why compatibility is capped

The source imports the legacy relative `.agent_based_api.v1` namespace and registers sections/checks through `register.check_plugin` and `register.snmp_section`. The package was built with Checkmk 2.0.0p20 and has no runtime validation for newer Checkmk releases. Importing or compiling source on a newer Python interpreter is not sufficient evidence that discovery, value-store behavior, SNMP parsing, service creation and metrics work correctly.

`version.usable_until` is therefore set to `2.2.99`. Raising it requires:

1. porting both plug-ins to `cmk.agent_based.v2`;
2. tightening the generic Net-SNMP detection;
3. adding parser, discovery, rate and rollover tests;
4. loading the plug-ins in the target Checkmk release;
5. validating against representative Frafos SNMP walks.

## How it works

Both sections detect the device via the generic Net-SNMP enterprise ID `.1.3.6.1.4.1.8072` and walk the Frafos SBC MIB under `.1.3.6.1.4.1.39695.2`.

- [`frafos_calls.py`](src/base/plugins/agent_based/frafos_calls.py) fetches `fSBCCallStarts` and `fSBCCalls` and emits `Call Statistics`. Calls per minute are derived from the monotonic counter through the legacy value store.
- [`frafos_callagents.py`](src/base/plugins/agent_based/frafos_callagents.py) creates one `Call Agent <name>` service per row with realm, calls, call-start rates and traffic in both directions.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/base/plugins/agent_based/frafos_calls.py` | Global call statistics section/check. |
| `src/base/plugins/agent_based/frafos_callagents.py` | Per-call-agent section/check. |

## Installation

Install only on a supported Checkmk 2.0–2.2 site:

1. Install the MKP.
2. Add the Frafos SBC as an SNMP host.
3. Confirm that the generic Net-SNMP detection does not discover the services on unrelated devices.
4. Run service discovery.

## Services and metrics

- **`Call Statistics`** — `calls_current`, `calls_minute`.
- **`Call Agent <name>`** — `current_to`, `current_from`, `to_per_minute`, `from_per_minute`, `current_bytes_to`, `current_bytes_from`.

## Known functional risk

The device detection matches many non-Frafos Net-SNMP systems. This package should be treated as legacy and isolated until the detection rule is tied to an unambiguous Frafos identifier or additional OID checks.

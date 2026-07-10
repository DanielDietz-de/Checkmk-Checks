# Cisco UCS: detect standalone CIMC / C-series servers

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p19-blue)
<!-- compatibility-badges:end -->

Broadens the discovery of the built-in cisco_ucs_* checks.
Upstream detection (cmk.plugins.lib.cisco_ucs.DETECT) only matches a
fixed whitelist of sysObjectIDs, so standalone Cisco IMC (CIMC)
appliance servers and newer UCS C-series -- e.g. SNS-8355-K9 /
UCS C225 M8 -- discover no services even though they fully serve the
CISCO-UNIFIED-COMPUTING-MIB (.1.3.6.1.4.1.9.9.719).

This package shadows cmk.plugins.lib.cisco_ucs, loads the genuine
upstream module dynamically, re-exports it unchanged, and only
broadens DETECT to additionally match any device exposing the UCS
compute rack-unit table (.1.3.6.1.4.1.9.9.719.1.9.35.1.43). This
affects all cisco_ucs_* checks (system, cpu, mem, fan, psu, hdd,
raid, lun, temp_cpu, temp_env, faults).

Note: a stored SNMP walk must contain the MIB-2 system OIDs
(.1.3.6.1.2.1.1.1.0 / .2.0); a walk restricted to the .9.9.719
subtree makes the Checkmk SNMP scan abort before detection runs.

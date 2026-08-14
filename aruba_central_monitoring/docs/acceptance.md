# Live acceptance checklist

Repository CI validates package structure, Python behavior, Checkmk registration, documentation, security controls, and deterministic MKP construction. The following checks require a representative Windows collector, Aruba Central tenant, and non-production Checkmk 2.5 site.

## Windows collector

1. Install and authenticate `cencli` under the exact Windows service identity used by the Checkmk agent.
2. Run `cencli show aps -v --json` and capture stdout and stderr separately.
3. Confirm the PowerShell plug-in completes inside the configured 90-second agent timeout.
4. Confirm the collector service reports the actual `json_stream`, `counts_stream`, and `rate_limit_stream` values.
5. Stop or block `cencli` temporarily and verify that the collector becomes CRIT while bounded last-known-good AP data remains available only until `MaxStaleSeconds`.
6. Restore collection and verify that a successful run atomically replaces the last-known-good cache.

## Access points and radios

1. Compare AP totals, Up/non-Up counts, and client totals with Aruba Central.
2. Validate at least one AP whose name differs from its MAC and one AP whose name equals or is absent relative to its MAC.
3. Confirm the resulting host names follow `name` or `AP_<serial>` as documented.
4. Compare status, serial, MAC, uptime, CPU, memory, firmware, SSID count, group, and site for representative AP models.
5. Compare radio name/type, channel, status, transmit power, utilization, spatial stream, and radio MAC.
6. Exercise an AP-down state and a radio-down state and confirm the configured Checkmk state mapping.

## Host synchronization

1. Capture `cmk -d <collector-host>` and run `sync_aruba_central_hosts` without `--apply`.
2. Verify every planned path is `/<Group>/Accesspoint/<Host>` and every Group/Site combination matches the approved mapping.
3. Add an invalid site to a sanitized fixture and confirm the complete plan fails before any REST request.
4. Apply against a non-production site with a least-privileged automation user and a mode-`0600` secret file.
5. Confirm created hosts use piggyback-only, no-agent, no-SNMP, and no-IP attributes.
6. Run the apply command a second time and confirm existing folders and hosts are treated idempotently without moves, deletes, or overwrites.
7. Activate changes and run service discovery on the generated AP hosts.

## Acceptance evidence

Record the Checkmk version, Windows version, PowerShell version, `cencli` version, representative AP models/firmware, elapsed collection time, sanitized stream placement, service-discovery result, and any deviations from the expected field schema. Do not attach tenant credentials, production payloads, private addresses, serial inventories, or complete MAC inventories to public issues.

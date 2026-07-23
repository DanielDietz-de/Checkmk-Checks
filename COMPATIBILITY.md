# Checkmk compatibility policy

Compatibility in this repository is **package-specific and evidence-based**. There is no repository-wide statement that every Checkmk 2.4 extension works on Checkmk 2.5 or that source importability proves runtime compatibility.

## Metadata meaning

| Field | Meaning |
| --- | --- |
| `version.min_required` | Oldest Checkmk release the maintainer explicitly supports. |
| `version.packaged` | Checkmk release that created the current MKP metadata/archive. It is not by itself a compatibility guarantee. |
| `version.usable_until` | Newest release family explicitly supported by the package. Omission means no upper claim is rendered; it does **not** mean unlimited compatibility. |

README badges are generated only from these explicit fields. `update_readmes.py` never derives `version.usable_until` from the minimum version, Python syntax, source importability, package layout, or another extension's test result.

## Evidence required to raise an upper bound

A compatibility claim should cover the behavior actually used by the package:

1. source compiles with the target Checkmk/Python release;
2. plug-ins load through the target Checkmk APIs;
3. `cmk-validate-plugins` and relevant configuration validation pass;
4. parsers, discovery and checks have focused tests;
5. special agents or agent plug-ins are exercised with representative responses;
6. an MKP is built and inspected by the target Checkmk release;
7. device/vendor integrations are tested with representative SNMP walks, API payloads or agent output where practical.

An import-only test is insufficient for runtime behavior, especially for discovery semantics, value stores, inventory, graphing, bakery, notifications and external APIs.

## Legacy packages

Packages using legacy top-level MKP categories such as `agent_based`, `checkman`, `web`, or `lib` should declare `version.usable_until` until they are migrated and tested. `update_readmes.py --strict-legacy-caps` can be used during focused cleanup to fail on uncapped legacy packages.

The repository may retain old extensions for historical users, but their README and metadata must state the supported Checkmk range clearly. A legacy package must not inherit a newer repository-wide compatibility claim.

## Updating badges

```bash
python3 update_readmes.py
python3 update_readmes.py --check
```

The updater scans both `src/info` and `src/info.json`. When both exist, their core compatibility fields must match or the command fails. This prevents the README, Python metadata and JSON metadata from presenting different support ranges.

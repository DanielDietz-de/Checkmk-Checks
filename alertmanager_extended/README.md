# Alertmanager with Severity Mapping

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0-blue)
<!-- compatibility-badges:end -->

Drop-in replacement for the built-in Checkmk Alertmanager check that adds severity remapping and lets you drive service state from the alert severity instead of only the `firing` state. Works for both alert rules and alert groups from version 1.4 of the plugin onwards.

## How it works

The plugin ships a replacement `collection/agent_based/alertmanager.py` and an extended ruleset under `kr_alertmanager/rulesets/alertmanager.py`. The ruleset exposes the normal Alertmanager discovery options (grouping rules into group services, minimum rule count, etc.) and adds a severity mapping so that arbitrary custom severities coming from Prometheus Alertmanager can be mapped to the Checkmk states OK / WARN / CRIT / UNKNOWN.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/kr_alertmanager/rulesets/alertmanager.py` | Extended WATO ruleset with severity remapping. |
| `src/cmk_plugins/collection/agent_based/alertmanager.py` | Replacement check plugin that overrides the shipped one. |

## Installation

1. Install the MKP on the Checkmk site.
2. Enable the Alertmanager special agent rule as usual and configure severity mapping in the extended ruleset.

### Checkmk 2.3

The shipped Alertmanager plugin must be removed manually, because the package only overrides one of the two files. Example Ansible task:

```yaml
- hosts: all
  gather_facts: false
  tasks:
    - name: Delete shipped Alertmanager check
      ansible.builtin.file:
        path: "{{ item }}"
        state: absent
      loop:
        - /opt/omd/versions/{{ cmk_version }}.cee/lib/python3/cmk/base/plugins/agent_based/alertmanager.py
        - /opt/omd/versions/{{ cmk_version }}.cee/lib/python3/cmk/plugins/collection/agent_based/alertmanager.py
      become: true
```

### Checkmk 2.4

No manual cleanup required. The overrides from the MKP take precedence out of the box.

## Known limitations

- Overrides a built-in Checkmk plugin. A Checkmk upgrade that changes the shipped Alertmanager plugin may require updating this package.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `alertmanager_extended` version `1.4.3`; minimum Checkmk version `2.3.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `alertmanager_extended/src/info`; it declares 2 packaged files.
- Repository MKP artifacts present: `alertmanager_extended-1.3.0.mkp`, `alertmanager_extended-1.3.1.mkp`, `alertmanager_extended-1.4.0.mkp`, `alertmanager_extended-1.4.1.mkp`, `alertmanager_extended-1.4.2.mkp`, `alertmanager_extended-1.4.3.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/cmk_plugins/collection/agent_based/alertmanager.py`.
- **Rulesets:** `src/kr_alertmanager/rulesets/alertmanager.py`.
- Registered check plug-in names: `alertmanager_groups`, `alertmanager_rules`, `alertmanager_summary`.

### Validation

- Package-specific tests: `tests/test_alertmanager_extended_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->

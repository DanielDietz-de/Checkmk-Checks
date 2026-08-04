# Filesystem Inventory

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

Adds filesystem ownership data to the Checkmk HW/SW inventory by looking up the owner of each mount point in `/etc/passwd` and collecting their email address. A wrapper for the built-in `mail` notification script then redirects Filesystem service notifications to that owner instead of the normal contact.

## How it works

Shell plugins for Linux, AIX and Solaris are deployed to the agent host. Each iterates over local mount points from `df -lP` (skipping `tmpfs`), resolves the directory owner via `ls -od`, looks the user up in `/etc/passwd`, extracts email and full name, and prints one CSV line per mount that has a mail address:

```text
<<<inventorize_df:sep(59)>>>
/;root;root;root@example.com
/var;webuser;Web User;web@example.com
```

The inventory plugin `inventorize_df` parses the section and writes rows under `software -> filesystem_owners` with columns `filesystem`, `owner`, `owner_name`, `owner_email`.

The notification script `df_mail` wraps Checkmk's built-in mail plugin. For services whose name starts with `Filesystem `, it reads `var/check_mk/inventory/<host>`, finds the matching `filesystem_owners` row and overwrites `NOTIFY_CONTACTEMAIL` with the owner address before handing off to `cmk.notification_plugins.mail.main()`.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/agents/plugins/df_inventory_linux.sh` | Linux agent plugin. |
| `src/agents/plugins/df_inventory_aix.sh` | AIX agent plugin. |
| `src/agents/plugins/df_inventory_solaris.sh` | Solaris agent plugin. |
| `src/df_inventory/agent_based/inventorize_df.py` | Section parser and HW/SW inventory plugin. |
| `src/df_inventory/agent_based/bakery.py` | Bakery hook for deployment of the agent plugin. |
| `src/df_inventory/rulesets/df_inventory.py` | `AgentConfig` rule controlling deployment (sync / cached / off). |
| `src/df_inventory/rulesets/notification_parameter.py` | Registers the `df_mail` notification parameter set by subclassing the built-in mail parameter. |
| `src/notifications/df_mail` | Notification script that rewrites the contact email from inventory. |

## Installation

1. Install the MKP on the Checkmk site.
2. Enable **DF Inventory: Filesystem Ownership Data** in the Bakery for the target hosts and bake / deploy agents. Without Bakery, copy the matching plugin from `src/agents/plugins/` into the agent plugins directory.
3. Create a **Notifications** rule that uses the `df_mail` script for Filesystem services; pick the owner via inventory by routing through this script.

## Configuration

Rule: **Setup -> Agents -> Agent rules -> DF Inventory: Filesystem Ownership Data**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `deployment` | CascadingSingleChoice | `sync` (deploy and run), `cached` (deploy and run every N minutes), or `do_not_deploy`. |

## Known limitations

- Linux plugin uses `cut -d ";"` while `/etc/passwd` uses `:` as the delimiter — the shipped Linux plugin as committed will only emit a row if `$MAIL` already contains an `@`, so behaviour depends on whether the `cut` output lines up on your distribution.
- `notification_parameter.py` takes a "risky path" into `cmk.gui.wato._notification_parameter._mail` and subclasses the private `NotificationParameterMail`. A comment flags that this can break across Checkmk updates.
- The `df_mail` wrapper depends on the inventory file existing; if it is missing for a host the wrapper falls through to the default mail script without overriding the contact.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `df_inventory` version `2.1.1`; minimum Checkmk version `2.4.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `df_inventory/src/info`; it declares 8 packaged files.
- Repository MKP artifacts present: `df_inventory-1.0.0.mkp`, `df_inventory-1.0.1.mkp`, `df_inventory-1.0.2.mkp`, `df_inventory-2.0.0.mkp`, `df_inventory-2.0.1.mkp`, `df_inventory-2.0.2.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/df_inventory/agent_based/bakery.py`, `src/df_inventory/agent_based/inventorize_df.py`.
- **Rulesets:** `src/df_inventory/rulesets/df_inventory.py`, `src/df_inventory/rulesets/notification_parameter.py`.
- **Notifications:** `src/notifications/df_mail`.
- **Other packaged source:** `src/agents/plugins/df_inventory_aix.sh`, `src/agents/plugins/df_inventory_linux.sh`, `src/agents/plugins/df_inventory_solaris.sh`.
- No special-agent or agent-based check registration was detected; use the component paths above to identify the package entry point.

### Validation

- Package-specific tests: `tests/test_df_inventory_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- No direct remote-network client was detected in the current source.

### Troubleshooting

- Emitted Checkmk sections detected in source: `inventorize_df`.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->

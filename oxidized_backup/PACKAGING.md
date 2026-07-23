# MKP packaging

The generated package and checksum belong directly in this folder:

- `oxidized_backup-<version>.mkp`
- `oxidized_backup-<version>.mkp.sha256`

## What the MKP contains

Version 1.1.0 contains three Checkmk package components.

### Additional Checkmk plug-ins

Installed below:

```text
$OMD_ROOT/local/lib/python3/cmk_addons/plugins/oxidized_backup/
```

This component contains:

- the Checkmk agent-based check;
- the Checkmk manual page;
- the Agent Bakery rule;
- pure configuration-normalization helpers shared by Bakery and tests;
- generic JSON and hook templates for Raw/Community and manual fallback deployments.

The Bakery rule is host-scoped and must be assigned only to the Checkmk host representing the Oxidized server. It does not select switches and does not replace the existing Checkmk-generated Oxidized inventory.

### Agents

Installed below:

```text
$OMD_ROOT/local/share/check_mk/agents/plugins/oxidized_backup
```

This is the Linux agent source consumed by Agent Bakery and by the documented manual fallback.

### Libraries

Checkmk 2.4 loads the Bakery implementation from the physical Python namespace:

```text
$OMD_ROOT/local/lib/python3/cmk/base/cee/plugins/bakery/oxidized_backup.py
```

For MKP packaging, Checkmk 2.4 exposes the same namespace through the compatibility symlink:

```text
$OMD_ROOT/local/lib/check_mk -> $OMD_ROOT/local/lib/python3/cmk
```

The `lib` component is rooted at `$OMD_ROOT/local/lib`, so its manifest entry is:

```text
check_mk/base/cee/plugins/bakery/oxidized_backup.py
```

The workflow verifies both the physical path and the compatibility path before calling `mkp package`. The package command dereferences the compatibility symlink while creating `lib.tar`.

The Bakery implementation describes the host-specific artifacts:

- cached or synchronous `Plugin` execution;
- a stable `SystemBinary` for the Oxidized exec hook;
- generated `PluginConfig` JSON;
- generated `SystemConfig` hook reference;
- DEB and RPM post-install scriptlets for the configured state directories.

The active Oxidized YAML configuration is deliberately not modified by package installation or Bakery scriptlets.

## Build and persistence workflow

The `oxidized_backup checks` workflow:

1. runs Python and security-focused tests;
2. validates the check and rule registration on Checkmk 2.4.0p5 and 2.4.0p34;
3. validates the commercial Bakery API v1 callbacks through an isolated contract test because Raw does not ship the commercial Bakery runtime;
4. verifies the Checkmk 2.4 `check_mk` compatibility symlink used for Bakery MKP packaging;
5. builds the MKP with Checkmk;
6. verifies the `agents`, `cmk_addons_plugins`, and `lib` component archives;
7. creates the SHA-256 checksum;
8. uploads the package and checksum as a workflow artifact.

After a successful push build on `master`, the `Persist oxidized_backup MKP` workflow downloads that exact artifact, verifies its checksum, and commits both files into `oxidized_backup/`.

Pull-request and manually dispatched builds remain read-only. Stale artifacts are rejected when package sources or the build workflow changed after the originating build started.

## Versioning rule

Any change to the check, agent plug-in, Bakery rule, Bakery implementation, generated configuration model, hook reference, deployment templates, or package layout requires a new `PACKAGE_VERSION` in `.github/workflows/oxidized_backup-ci.yml`.

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

Installed below:

```text
$OMD_ROOT/local/lib/python3/cmk/base/cee/plugins/bakery/oxidized_backup.py
```

The `lib` component archive contains:

```text
python3/cmk/base/cee/plugins/bakery/oxidized_backup.py
```

The Bakery implementation describes the host-specific artifacts:

- cached or synchronous `Plugin` execution;
- a stable `SystemBinary` for the Oxidized exec hook;
- generated `PluginConfig` JSON;
- generated `SystemConfig` hook reference;
- DEB and RPM post-install scriptlets for the configured state directories.

The active Oxidized YAML configuration is deliberately not modified by package installation or Bakery scriptlets.

## Deterministic package builder

The package is built by:

```text
oxidized_backup/tools/build_mkp.py
```

Checkmk's `mkp package` command rejects local files inside the Checkmk Python namespace as file conflicts, although Agent Bakery extensions must be installed in that namespace. The package-local builder therefore creates the standard MKP archive structure directly:

- `info`;
- `info.json`;
- `agents.tar`;
- `cmk_addons_plugins.tar`;
- `lib.tar`.

The builder:

- selects files only from the three version-controlled source roots;
- rejects unsafe archive paths and invalid metadata;
- excludes bytecode and `__pycache__` files;
- normalizes archive ownership and timestamps;
- produces reproducible gzip and tar output;
- validates both metadata files and every component member;
- writes a SHA-256 checksum beside the MKP.

CI does not treat successful archive creation as sufficient. It also uses Checkmk to:

1. run `mkp inspect`;
2. add and enable the MKP in a clean Checkmk 2.4.0p34 site;
3. verify every installed component path;
4. compile the installed Python files;
5. run `cmk-validate-plugins`, the manual lookup, and `cmk -R`.

## Build and persistence workflow

The `oxidized_backup checks` workflow:

1. runs Python, security, Bakery-contract, and deterministic-package tests;
2. validates the check and rule registration on Checkmk 2.4.0p5 and 2.4.0p34;
3. validates the commercial Bakery API v1 callbacks through an isolated contract test because Raw does not ship the commercial Bakery runtime;
4. builds the deterministic MKP and checksum;
5. performs the clean Checkmk inspection, installation, activation, and registration checks;
6. independently verifies the `agents`, `cmk_addons_plugins`, and `lib` component archives;
7. uploads the package and checksum as a workflow artifact.

After a successful push build on `master`, the `Persist oxidized_backup MKP` workflow downloads that exact artifact, verifies its checksum, and commits both files into `oxidized_backup/`.

Pull-request and manually dispatched builds remain read-only. Stale artifacts are rejected when package sources or the build workflow changed after the originating build started.

## Versioning rule

Any change to the check, agent plug-in, Bakery rule, Bakery implementation, generated configuration model, hook reference, deployment templates, package builder, or package layout requires a new `PACKAGE_VERSION` in `.github/workflows/oxidized_backup-ci.yml`.

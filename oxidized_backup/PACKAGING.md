# MKP packaging

The generated package and checksum belong directly in this folder:

- `oxidized_backup-<version>.mkp`
- `oxidized_backup-<version>.mkp.sha256`

## What the MKP contains

The MKP installs two package components on the Checkmk server.

### Checkmk plug-in component

Installed below:

```text
$OMD_ROOT/local/lib/python3/cmk_addons/plugins/oxidized_backup/
```

This component contains:

- the Checkmk agent-based plug-in;
- the Checkmk manual page;
- the version-matched deployment templates:
  - `deployment/oxidized_backup.json`
  - `deployment/oxidized_backup-hook.yml`

The templates are administrative files copied from the Checkmk server to the Oxidized host. They are intentionally stored in the Checkmk plug-in component because Checkmk's MKP `agents` component is reserved for files that belong to the agent distribution tree. Packaging the templates as additional `agents/cfg_examples` files caused a Checkmk file-conflict failure during `mkp package`.

### Agents component

Installed below:

```text
$OMD_ROOT/local/share/check_mk/agents/plugins/oxidized_backup
```

This component contains only the executable Linux agent plug-in. The administrator copies this executable and the two deployment templates from the enabled MKP installation to the Oxidized host.

## Build and persistence workflow

The `oxidized_backup checks` workflow:

1. runs Python and security-focused tests;
2. validates the plug-in and deployment templates on the supported Checkmk versions;
3. builds the MKP with Checkmk;
4. verifies the MKP manifest and every component archive;
5. explicitly checks that both deployment templates are present in `cmk_addons_plugins.tar`;
6. creates the SHA-256 checksum;
7. uploads the package and checksum as a workflow artifact.

After a successful push build on `master`, the `Persist oxidized_backup MKP` workflow downloads that exact artifact, verifies its checksum, and commits both files into `oxidized_backup/`.

Pull-request and manually dispatched builds remain read-only. Stale artifacts are rejected when package sources or the build workflow changed after the originating build started.

## Versioning rule

Any change to the Checkmk plug-in, Linux agent plug-in, configuration template, hook template, or package layout requires a new `PACKAGE_VERSION` in `.github/workflows/oxidized_backup-ci.yml`.

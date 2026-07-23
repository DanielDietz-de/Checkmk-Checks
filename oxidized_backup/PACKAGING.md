# MKP packaging

The generated package and checksum belong directly in this folder:

- `oxidized_backup-<version>.mkp`
- `oxidized_backup-<version>.mkp.sha256`

## What the MKP contains

The MKP installs two classes of files on the Checkmk server.

### Checkmk plug-in files

These are installed below:

```text
$OMD_ROOT/local/lib/python3/cmk_addons/plugins/oxidized_backup/
```

They parse the agent and piggyback data, discover services, evaluate states, and provide the Checkmk manual page.

### Oxidized-host deployment files

These are installed below the Checkmk site's agent-download directory:

```text
$OMD_ROOT/local/share/check_mk/agents/plugins/oxidized_backup
$OMD_ROOT/local/share/check_mk/agents/cfg_examples/oxidized_backup.json
$OMD_ROOT/local/share/check_mk/agents/cfg_examples/oxidized_backup-hook.yml
```

The administrator copies these three version-matched files from the Checkmk server to the Oxidized host. The JSON and hook files under `src/agents/cfg_examples/` are therefore package inputs, not separate repository-only examples.

## Build and persistence workflow

The `oxidized_backup checks` workflow:

1. runs Python and security-focused tests;
2. validates the plug-in on the supported Checkmk versions;
3. builds the MKP with Checkmk;
4. verifies the MKP manifest and every component archive;
5. creates the SHA-256 checksum;
6. uploads both files as a workflow artifact.

After a successful push build on `master`, the `Persist oxidized_backup MKP` workflow downloads that exact artifact, verifies its checksum, and commits both files into `oxidized_backup/`.

Pull-request and manually dispatched builds remain read-only and do not write generated binaries to the repository. Stale artifacts are rejected when the package source or its build workflow changed after the originating build started.

## Versioning rule

Any change to the Checkmk plug-in, the Linux agent plug-in, the packaged configuration template, or the packaged Oxidized hook template requires a new `PACKAGE_VERSION` in `.github/workflows/oxidized_backup-ci.yml`.

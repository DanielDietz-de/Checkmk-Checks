# MKP packaging

The generated repository package belongs directly in this folder:

- `switch_port_sync-<version>.mkp`
- `switch_port_sync-<version>.mkp.sha256`

The `switch_port_sync checks` workflow builds, inspects, verifies, and uploads the MKP as a GitHub Actions artifact. After a successful push build on `master`, the `Persist switch_port_sync MKP` workflow downloads that exact artifact, verifies its checksum, and commits both files into `switch_port_sync/`.

Pull-request and manually dispatched builds remain read-only and do not write generated binaries to the repository. Stale artifacts are rejected when the package source or its build workflow changed after the originating build started.

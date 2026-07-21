# MKP packaging

The generated repository package belongs directly in this folder:

- `oxidized_backup-<version>.mkp`
- `oxidized_backup-<version>.mkp.sha256`

The `oxidized_backup checks` workflow builds, inspects, verifies, and uploads the MKP as a GitHub Actions artifact. After a successful push build on `master`, the `Persist oxidized_backup MKP` workflow downloads that exact artifact, verifies its checksum, and commits both files into `oxidized_backup/`.

Pull-request and manually dispatched builds remain read-only and do not write generated binaries to the repository. Stale artifacts are rejected when the package source or its build workflow changed after the originating build started.

# MKP packaging

The generated repository package belongs directly in this folder:

- `switch_port_sync-<version>.mkp`
- `switch_port_sync-<version>.mkp.sha256`

The `switch_port_sync checks` workflow calls the shared generated-MKP workflow. It:

1. runs the standalone test suite;
2. loads and validates the plug-in on Checkmk 2.4.0p34;
3. loads and validates the plug-in on Checkmk 2.5.0p9;
4. builds and inspects the MKP inside Checkmk 2.5.0p9;
5. generates metadata with `version.packaged: 2.5.0p9` and `version.usable_until: 2.5.99`;
6. uploads the MKP and SHA-256 checksum as one workflow artifact.

After a successful push build on `master`, the same workflow downloads the exact artifact from that run, verifies its checksum, and commits both files into `switch_port_sync/`.

Pull-request and manually dispatched builds remain read-only and do not write generated binaries to the repository. A previously checked-in MKP is removed whenever its metadata does not reflect the currently validated Checkmk versions; it is regenerated only by a successful master build.

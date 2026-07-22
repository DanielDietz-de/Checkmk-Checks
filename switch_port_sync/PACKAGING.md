# MKP packaging

The generated repository package belongs directly in this folder:

- `switch_port_sync-<version>.mkp`
- `switch_port_sync-<version>.mkp.sha256`

The `switch_port_sync checks` workflow calls the shared generated-MKP workflow. It:

1. runs the standalone test suite and check-manual validation;
2. loads and validates the plug-in on Checkmk 2.4.0p5;
3. loads and validates the plug-in on Checkmk 2.4.0p34;
4. loads and validates the plug-in on Checkmk 2.5.0p9;
5. runs the special agent's `--help` smoke test in every Checkmk container;
6. rejects duplicate Checkmk plug-in registrations;
7. builds and inspects the MKP inside Checkmk 2.5.0p9;
8. verifies every manifest entry against the generated component archive;
9. generates metadata with `version.packaged: 2.5.0p9` and `version.usable_until: 2.5.99`;
10. uploads the MKP and SHA-256 checksum as one workflow artifact.

After a successful push build on `master`, the same workflow downloads the exact artifact from that run and verifies its checksum. Before publishing, it fetches the current `master` branch and compares the package directory, caller workflow, and shared packaging workflow against the source commit. If any package input changed while the run was executing, the stale artifact is discarded rather than rebased over newer source.

Pull-request and manually dispatched builds remain read-only and do not write generated binaries to the repository. A previously checked-in MKP is removed whenever its metadata does not reflect the currently validated Checkmk versions; it is regenerated only by a successful master build.

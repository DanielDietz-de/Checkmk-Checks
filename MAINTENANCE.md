# Repository maintenance and assurance levels

This repository contains extensions from multiple generations of Checkmk. A package's presence in the repository does not by itself mean it has current runtime validation.

## Assurance levels

### Runtime-validated

A package reaches this level only when the repository workflow loads the plug-in in the supported Checkmk releases, runs package tests, validates manuals and configuration where applicable, and builds or inspects its MKP with the declared packaging release.

### Source-tested

The package has focused parser, discovery, check, notification, agent, or security tests, but may not have representative device or application fixtures. Its README and metadata must not claim a broader runtime range than the available evidence supports.

### Legacy or unverified

The package has no focused tests or still uses legacy Checkmk APIs. It may remain for existing deployments, but changes to its source must add tests. Compatibility must be stated explicitly and conservatively.

## Changed-code baseline

The repository guard applies stricter rules whenever package source changes:

- changed Python must parse;
- built-in `eval`, `shell=True`, plaintext `Secret.unsafe()`, global TLS-warning suppression, and new `verify=False` calls are rejected;
- a changed package must contain at least one `tests/test_*.py` file;
- touched package metadata must be complete and consistent between `src/info` and `src/info.json`;
- existing untouched legacy debt is inventoried rather than causing unrelated pull requests to fail.

This ratchet model improves the repository without forcing an unsafe bulk rewrite of untested vendor integrations.

## Workflow supply chain

All third-party GitHub Actions must use full commit SHAs. Checkmk container images used by CI must use registry manifest digests. Human-readable action tags are retained as comments and the resolved references are recorded in `.github/supply-chain-lock.json`.

To intentionally update dependencies:

```bash
GH_TOKEN=... python3 tools/ci/pin_supply_chain.py --write
python3 tools/ci/pin_supply_chain.py --check
```

Review the resulting workflow and lock-file diff. A dependency update is a source change and must be reviewed like code.

## Generated MKP publication

The repository-wide MKP workflow builds deterministic archives, verifies their component inventory and checksums, installs supported packages in clean Checkmk sites, validates packaged manuals, and reloads the Checkmk core. Publication is allowed only after those gates pass and only while the source branch remains current; stale artifacts are not rebased over newer source.

## Adding or updating a package

1. Add focused tests for the behavior being changed.
2. Keep credentials in Checkmk `Secret` objects or protected host-side files.
3. Bound network timeouts, response sizes, parser inputs, caches, and output fields.
4. Fail closed on incomplete collection rather than publishing partial trusted output.
5. Update both metadata formats when both exist.
6. State compatibility based on tested Checkmk releases, not source importability.
7. Add representative fixtures when a vendor integration requires behavior beyond load and registration checks.

## Security exceptions

A narrowly justified exception may use an inline `# security-reviewed:` comment, but only when the risk cannot be removed and the package documentation explains the operational boundary. Exceptions should be rare, local, and covered by tests.

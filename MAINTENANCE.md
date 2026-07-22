# Repository maintenance and assurance levels

This repository contains extensions from multiple generations of Checkmk. A package's presence in the repository does not by itself mean it has current runtime validation.

## Assurance levels

### Runtime-validated

A package reaches this level only when its workflow loads the plug-in in the supported Checkmk releases, runs package tests, validates manuals/configuration where applicable, and builds or inspects its MKP with the declared packaging release.

### Source-tested

The package has focused parser, discovery, check, notification, agent, or security tests, but no dedicated Checkmk container matrix. Its README and metadata must not claim a broader runtime range than the available evidence supports.

### Legacy or unverified

The package has no focused tests or still uses legacy Checkmk APIs. It may remain for existing deployments, but changes to its source must add tests. Compatibility must be stated explicitly and conservatively.

## Changed-code baseline

The repository guard applies stricter rules whenever package source changes:

- changed Python must parse;
- built-in `eval`, `shell=True`, plaintext `Secret.unsafe()`, global TLS-warning suppression, and new `verify=False` calls are rejected;
- a changed package must contain at least one `tests/test_*.py` file;
- touched package metadata must be complete and consistent between `src/info` and `src/info.json`;
- existing untouched legacy debt is inventoried rather than causing unrelated PRs to fail.

This ratchet model improves the repository without forcing an unsafe bulk rewrite of untested vendor integrations.

## Workflow supply chain

All third-party GitHub Actions must use full commit SHAs. Checkmk container images used by CI must use registry manifest digests. Human-readable source tags are retained as comments and in `.github/supply-chain-lock.json`.

To intentionally update dependencies:

```bash
GH_TOKEN=... python3 tools/ci/pin_supply_chain.py --write
python3 tools/ci/pin_supply_chain.py --check
```

Review the resulting workflow and lock-file diff. A dependency update is a source change and must be reviewed like code.

## Generated MKP provenance

The shared generated-MKP workflow records:

- package name and version;
- exact source commit;
- deterministic source-tree SHA-256;
- source file count;
- digest-pinned builder image;
- packaged Checkmk version;
- declared `usable_until` value.

The MKP, checksum, and provenance JSON are one artifact set. The persistence job verifies the checksum and provenance and commits the files only when `master` still equals the source commit that produced them. It never rebases an older build over newer source.

## Adding or updating a package

1. Add focused tests for the behavior being changed.
2. Keep credentials in Checkmk `Secret` objects or protected host-side files.
3. Bound network timeouts, response sizes, parser inputs, caches, and output fields.
4. Fail closed on incomplete collection rather than publishing partial trusted output.
5. Update both metadata formats when both exist.
6. State compatibility based on tested Checkmk releases, not source importability.
7. Add a dedicated workflow when the package has sufficient fixtures for meaningful Checkmk runtime validation.

## Security exceptions

A narrowly justified exception may use an inline `# security-reviewed:` comment, but only when the risk cannot be removed and the package documentation explains the operational boundary. Exceptions should be rare, local, and covered by tests.

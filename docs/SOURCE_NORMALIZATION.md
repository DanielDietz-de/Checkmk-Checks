# Package source normalization

Package source normalization is a reviewed source-maintenance operation. It is deliberately separate from MKP release preparation and generated-artifact publication.

## Security and reproducibility objective

A release workflow must not silently rewrite executable package source after the source pull request has been reviewed. Generated release pull requests are therefore restricted to release metadata, code-derived documentation and indexes, canonical manifest versions, MKP archives, and checksums.

Legacy source-layout migrations must be committed through an ordinary source pull request before release publication. This ensures that:

- the repository source tree exactly represents the code packaged into an MKP;
- source moves and import changes receive normal review, tests, and security auditing;
- targeted package validation and full release validation build from the same committed source layout;
- deterministic rebuilds do not depend on uncommitted workspace mutations; and
- the publication allowlist can remain narrow and fail closed on executable-source changes.

## Authoritative tool

Use:

```bash
python3 tools/ci/normalize_package_sources.py
```

The default mode is read-only. It exits nonzero and lists every pending source change when normalization is required.

To apply reviewed migrations on a development branch:

```bash
python3 tools/ci/normalize_package_sources.py --write
python3 tools/ci/sync_package_metadata.py --write
python3 update_readmes.py
python3 tools/ci/generate_package_reference.py --write
python3 create_mkp_index.py
python3 tools/ci/normalize_package_sources.py
```

Review all resulting source, manifest, metadata-mirror, and documentation changes before committing them.

## Current normalization rules

### Legacy Bakery modules

Older packages may place a Bakery module below an add-on family's `agent_based` namespace and import:

```python
from cmk.base.cee.plugins.bakery.bakery_api.v1 import ...
```

Checkmk Raw/Community can scan such a file as a check plug-in even though the CEE Bakery API is unavailable there. The normalizer moves the module into:

```text
<package>/src/lib/python3/cmk/base/cee/plugins/bakery/<package>.py
```

It also:

- changes the import to the relative `.bakery_api.v1` form expected in the Bakery library package;
- removes the legacy `cmk_addons_plugins` manifest entry;
- adds the corresponding `files.lib` entry; and
- removes the obsolete source path.

The transformation fails closed when there is more than one legacy Bakery candidate, the source is missing, manifest structures are malformed, or the import form is unsupported.

### Alertmanager extension cleanup

The `alertmanager_extended` package must retain its isolated custom rule namespace and matching check references. The normalizer validates those invariants and removes only the explicitly enumerated historical debug-print statements from the check plug-in.

It fails rather than rewriting when the required ruleset or plug-in is missing, a custom declaration/reference is absent, or a built-in rule identifier is redeclared.

## CI enforcement

`Repository security and supply-chain guard` runs the normalizer in read-only mode for every pull request, push to `master`, and exact-head release-branch dispatch.

A pending migration is therefore a CI failure. Release preparation does not repair it automatically.

`.github/scripts/prepare_repository_mkp_release.py` is limited to release-manifest operations:

- evidence-preserving package version updates;
- packaged Checkmk version updates;
- download URL normalization;
- release-completion state; and
- preservation of evidence-based upper compatibility bounds.

It contains no source-file move, deletion, Bakery normalization, or Alertmanager source-edit behavior.

## Adding a new normalization rule

A new rule must include:

1. a concrete compatibility or security rationale;
2. deterministic behavior based only on tracked repository state;
3. read-only detection and explicit `--write` application;
4. focused positive, idempotence, and fail-closed tests;
5. updates to this document and relevant package documentation;
6. committed source migrations in the same reviewed pull request; and
7. confirmation that release preparation and publication remain source-code-free.

Do not expand the publication generated-path allowlist merely to accommodate a source migration. Move the migration into this reviewed maintenance path instead.

## Troubleshooting

### Guard reports pending normalization

Run the tool without `--write` locally and inspect the listed paths. Apply the migration only on a development branch, regenerate mirrors and documentation, and review the complete diff.

### Normalizer reports an unsupported import or manifest layout

Do not bypass the check. Update the normalization implementation and tests to model the actual legacy layout safely, or migrate that package manually in a dedicated source PR.

### Release dry-run reports an executable source change

This is not a generated release artifact. Stop the publication change, identify the pending source migration, and commit it through the normal source-review path.

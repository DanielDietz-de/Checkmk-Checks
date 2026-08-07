# Release and rollback

A production release consists of the reviewed source commit plus repository-generated deterministic MKP, SHA-256 checksum, SPDX 2.3 SBOM, and provenance evidence. Treat those files as one release unit.

Do not publish an MKP built from an uncommitted or dirty source tree. Verify the checksum before installation. Keep the prior validated release unit until production acceptance completes.

For rollback, reinstall the prior release unit, rebake/redeploy the corresponding agent package, and verify collector protocol/health and piggyback identity before closing the incident or change.

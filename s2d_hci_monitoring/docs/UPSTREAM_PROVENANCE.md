# Upstream provenance

The package was initially migrated from `Daniel-Dietz/S2D-Monitoring` branch `main` at commit `c6aa39d8fa62c1a550c07308f99e75c94ba5a7c2`.

Source PR #8 (`production-hardening`, head `8542a142e9349639fae89ff98448d840152d65b3`) documented the production-hardening intent: bounded/versioned collectors, explicit health, leader election, logical/VM piggyback, data minimization, least-privilege gMSA handling, Bakery integration, deterministic release evidence, and production acceptance. Its encoded materialization bundle was not used as authoritative source because its review identified an invalid archive transport. The hardening requirements were reimplemented and tested directly in this repository.

Repository code and `src/info` are authoritative for the current package. Documentation must follow code rather than upstream prose.
